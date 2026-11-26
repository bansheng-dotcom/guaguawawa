# -*- coding: utf-8 -*-
"""core.charts.chart_shapes —— 从数字里推图型（不是从柱子里换柱子）。

2026-11-21：用户质问"我有数据，为什么只会柱状图"。查下来是**形状**问题：
契约里每张图只有 `{label, value}` 一维名单，70 种图型里能吃的只有 7 种。
但证据包里的数字其实带 `period`、上下限、正负号——足够推成：

    同一指标多个 period      → line（时间线）
    「下限 / 上限」成对       → range（区间图）
    百分比且有正有负          → diverging（正负条）
    百分比且加起来≈100        → treemap（构成）

推不出来就返回 None，交回原来的图/柱状兜底，不硬凑。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

AGG = ("其他", "其它", "其余", "合计", "总计", "长尾", "剩余")


def _nums(pack: Dict[str, Any], refs: List[str]) -> List[Dict[str, Any]]:
    idx = {str(n.get("id")): n for n in (pack.get("numbers") or [])}
    out = []
    for r in refs or []:
        n = idx.get(str(r))
        if not n or n.get("value") in (None, ""):
            continue
        try:
            v = float(n["value"])
        except (TypeError, ValueError):
            continue
        out.append({**n, "_v": v})
    return out


def _series(nums: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """同一指标名、不同 period → 时间线。"""
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for n in nums:
        per = str(n.get("period") or "").strip()
        if not per:
            continue
        key = (str(n.get("name") or ""), str(n.get("unit") or ""))
        groups.setdefault(key, []).append(n)
    for (name, unit), arr in groups.items():
        periods = {str(n["period"]) for n in arr}
        if len(periods) >= 2:
            arr = sorted(arr, key=lambda n: str(n["period"]))
            return {"type": "line",
                    "points": [{"label": str(n["period"]), "value": n["_v"]}
                               for n in arr],
                    "unit_meta": unit, "label": name}
    return None


def _range(nums: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """「下限/上限」成对 → 区间图。

    只有**整节都是上下限对**时才用：混着 456mm 这种单点的节（降水 vs 蒸发），
    区间图会把单点丢掉，读者反而看不到"3.73 倍"从哪来。
    """
    lows = [n for n in nums if "下限" in str(n.get("name") or "")]
    highs = [n for n in nums if "上限" in str(n.get("name") or "")]
    if not lows or not highs:
        return None
    if len(lows) + len(highs) != len(nums):
        return None
    rows = []
    for lo in lows:
        base = str(lo["name"]).replace("下限", "")
        hi = next((h for h in highs
                   if str(h["name"]).replace("上限", "") == base), None)
        if hi:
            rows.append({"label": base, "low": lo["_v"], "high": hi["_v"]})
    return {"type": "range", "rows": rows,
            "unit_meta": str(rows and lows[0].get("unit") or "")} if rows else None


def _signed(nums: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """百分比且有正有负 → 正负条（增速对比最合适）。

    必须**整节都是百分比**：混着"亿元"的节（比如四城社零 + 增速），
    强行画正负条会把标题说的事和图上画的事对不上。
    """
    pct = [n for n in nums if str(n.get("unit") or "") == "%"]
    if len(pct) != len(nums) or len(pct) < 2:
        return None
    vals = [n["_v"] for n in pct]
    if any(v < 0 for v in vals) and any(v > 0 for v in vals):
        return {"type": "diverging",
                "items": [{"label": str(n["name"]), "value": n["_v"]}
                          for n in pct],
                "unit_meta": "%"}
    return None


def _compose(nums: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """百分比且加起来≈100 → 构成（树图）。

    允许节里还有"总额/规模"这类非同单位数字（它们本来就是分母），
    只要百分比子集 ≥4 且加总≈100，就说明这节讲的是构成。
    """
    pct = [n for n in nums if str(n.get("unit") or "") == "%"]
    if not (4 <= len(pct) <= 8):
        return None
    vals = [n["_v"] for n in pct]
    if not (88 <= sum(vals) <= 112):
        return None
    if any(v <= 0 for v in vals):
        return None
    return {"type": "treemap",
            "items": [{"label": str(n["name"]), "value": n["_v"]} for n in pct],
            "unit_meta": "%"}


def from_numbers(section: Dict[str, Any], pack: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    nums = _nums(pack, list(section.get("refs") or []))
    if len(nums) < 2:
        return None
    for fn in (_series, _range, _signed, _compose):
        try:
            got = fn(nums)
        except Exception:  # noqa: BLE001
            got = None
        if got:
            return got
    return None

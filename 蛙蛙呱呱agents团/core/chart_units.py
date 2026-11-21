# -*- coding: utf-8 -*-
"""core.chart_units —— 一张图只能有一个单位族。

为什么需要它：自动配图会从本节 refs 里抓数字，常把「月营收 12.4 万元」和
「门店 9.6 万家」画进同一张图。图型再漂亮，单位混了就是错图。

规则：
1. 每个数据点尽量带 `ref`，用 ref 回查数字的 unit；
2. 以「出现次数最多的 unit」为主单位，丢掉其它单位的点；
3. 主单位点少于 2 个 → 不画图（返回 None）；
4. `unit_meta` 强制写成主单位。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _num_unit(n: Dict[str, Any]) -> str:
    return str(n.get("unit") or "").strip()


def _items_of(chart: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("bars", "items", "points", "steps", "stages"):
        v = chart.get(key)
        if isinstance(v, list) and v:
            return v
    return []


def _set_items(chart: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
    out = dict(chart)
    for key in ("bars", "items", "points", "steps", "stages"):
        if key in out:
            out[key] = items
            return out
    out["items"] = items
    return out


def sanitize(chart: Optional[Dict[str, Any]], pack: Dict[str, Any],
             refs: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """按单位分组，保留主单位；混单位的点直接丢掉。"""
    if not chart:
        return None
    nums = {str(n.get("id") or ""): n for n in (pack.get("numbers") or [])}
    # 本节 refs 用来给「没写 ref 的图点」回查单位：按数值相等匹配
    local = [nums[str(r)] for r in (refs or []) if str(r) in nums]
    items = _items_of(chart)
    if not items:
        return chart
    # 给每个点补 unit：优先 ref，其次按数值在本节 refs 里找，最后图级 unit_meta
    enriched = []
    for it in items:
        if not isinstance(it, dict):
            continue
        unit = str(it.get("unit") or "").strip()
        ref = str(it.get("ref") or "")
        if not unit and ref:
            n = nums.get(ref) or {}
            unit = _num_unit(n)
        if not unit:
            try:
                v = float(it.get("value"))
            except (TypeError, ValueError):
                v = None
            if v is not None:
                for n in local:
                    try:
                        if abs(float(n.get("value")) - v) <= max(1e-9, abs(v) * 1e-6):
                            unit = _num_unit(n)
                            ref = ref or str(n.get("id") or "")
                            break
                    except (TypeError, ValueError):
                        continue
        if not unit:
            unit = str(chart.get("unit_meta") or "").strip()
        enriched.append(dict(it, _unit=unit, _ref=ref))
    # 按 unit 计数；同数取先出现
    counts: Dict[str, int] = {}
    order: List[str] = []
    for it in enriched:
        u = it.get("_unit") or ""
        if not u:
            continue
        if u not in counts:
            order.append(u)
        counts[u] = counts.get(u, 0) + 1
    if not counts:
        return chart
    unit = max(order, key=lambda u: (counts[u], -order.index(u)))
    keep = [it for it in enriched if (it.get("_unit") or "") == unit]
    if len(keep) < 2:
        return None
    # refs 只保留主单位点的 ref，避免下游再抽回混单位数字
    refs_keep = [str(it.get("_ref")) for it in keep if it.get("_ref")]
    keep = [{**{k: v for k, v in it.items() if k not in ("_unit", "_ref")},
             "unit": it.get("_unit")} for it in keep][:12]
    out = _set_items(chart, keep)
    out["unit_meta"] = unit
    if refs_keep:
        out["refs"] = refs_keep
    return out

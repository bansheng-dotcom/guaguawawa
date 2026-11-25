# -*- coding: utf-8 -*-
"""core.chart_fit —— 数据画像 → 候选图型（P4-1）。

方向反过来：**先看数据长什么样，再决定能画什么**。
旧做法（`collector-lab/chart_matrix.py`）是先读图型必填字段再反推造数据，
结果是 70 型里 24 型只能占位。

输入：`data_standard.Dataset`（或它的 profile + observations）
输出：候选列表，每项带 `preconditions`（缺什么）与 `fallback`（降级到哪型）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core import data_standard as ds


def _cand(typ: str, why: str, ok: bool = True,
          missing: Optional[List[str]] = None,
          fallback: str = "") -> Dict[str, Any]:
    return {"type": typ, "why": why,
            "preconditions": {"ok": bool(ok), "missing": list(missing or [])},
            "fallback": fallback}


def fit_profile(profile: Dict[str, Any], rows: int = 0) -> Dict[str, Any]:
    """画像 → 候选图型（纯函数，不读盘）。"""
    n = int(rows or profile.get("rows") or 0)
    cols = profile.get("columns") or {}
    v = profile.get("value") or {}
    if n <= 0 or not v:
        return {"ok": True, "rows": n, "recommended": "text",
                "candidates": [_cand("text", "没有可画的数值", fallback="table"),
                               _cand("table", "原始行表", fallback="text")]}

    periods = int((cols.get("period") or {}).get("distinct") or 0)
    entities = int((cols.get("entity") or {}).get("distinct") or 0)
    metrics = int((cols.get("metric_id") or {}).get("distinct") or 0)
    neg = float(v.get("neg_rate") or 0)
    zero = float(v.get("zero_rate") or 0)
    flat = float(v.get("max") or 0) == float(v.get("min") or 0)
    unit_vals = (cols.get("unit") or {}).get("values") or [""]
    unit = str(unit_vals[0])

    cands: List[Dict[str, Any]] = []
    if flat or zero >= 0.999:
        cands.append(_cand("text", "数值无差异（全 0 或常数），画图会误导",
                           fallback="table"))
        return {"ok": True, "rows": n, "recommended": "text", "candidates": cands}

    if neg > 0:
        cands.append(_cand("diverging", f"含负值 {neg:.0%}，需要零基线",
                           fallback="hbar"))

    if periods >= 3:
        if 2 <= entities <= 8 and metrics >= 1:
            cands.append(_cand("multi_line", f"{entities} 个主体 × {periods} 期",
                               fallback="line"))
        cands.append(_cand("line", f"{periods} 期时间序列", fallback="table"))
        cands.append(_cand("area", "时间序列且强调累计", ok=periods >= 4,
                           missing=[] if periods >= 4 else ["期数 < 4"],
                           fallback="line"))
    if entities >= 2:
        if unit == "%" or metrics >= 2:
            cands.append(_cand("stacked", "结构随时间变化",
                               ok=periods >= 2, missing=[] if periods >= 2 else ["期数 < 2"],
                               fallback="grouped"))
        cands.append(_cand("hbar", f"{entities} 个类别比较", fallback="table"))
        if 2 <= entities <= 8 and unit == "%":
            cands.append(_cand("pie", "占比且类别 ≤8", fallback="donut"))
            cands.append(_cand("donut", "占比且类别 ≤8", fallback="pie"))
        if entities > 20:
            cands.append(_cand("pareto", "类别多，先看头部贡献",
                               ok=False, missing=[f"类别 {entities} > 20（先取 TopN）"],
                               fallback="hbar"))
    # 双类别 + 数值 → 热力
    cat_dims = profile.get("categorical") or []
    if len(cat_dims) >= 2:
        a, b = cat_dims[0], cat_dims[1]
        na = int((cols.get(a) or {}).get("distinct") or 0)
        nb = int((cols.get(b) or {}).get("distinct") or 0)
        cands.append(_cand("heatmap", f"{a}({na}) × {b}({nb}) 交叉",
                           ok=2 <= na <= 12 and 2 <= nb <= 12,
                           missing=[] if 2 <= na <= 12 and 2 <= nb <= 12
                           else ["交叉维度超过 12 档，热力会糊"],
                           fallback="table"))
    cands.append(_cand("table", "原始行表（最稳的降级）", fallback="text"))
    rec = next((c["type"] for c in cands if c["preconditions"]["ok"]), "table")
    return {"ok": True, "rows": n, "recommended": rec, "candidates": cands}


def fit(dataset: ds.Dataset | Dict[str, Any]) -> Dict[str, Any]:
    """Dataset → 候选图型；缺画像时现算。"""
    d = dataset if isinstance(dataset, ds.Dataset) else ds.Dataset.from_dict(dataset)
    prof = d.profile or ds.profile_observations(d.observations)
    return fit_profile(prof, rows=len(d.observations))

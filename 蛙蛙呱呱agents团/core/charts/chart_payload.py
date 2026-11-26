# -*- coding: utf-8 -*-
"""core.charts.chart_payload —— 图表 payload 构建器（SOP v3.0 S5b「治疗」）。

把 facts（语义 IR 的事实行）组织成某图型渲染所需的 payload 形状。
这是「改型」的关键：光改 type 不改 payload 会让渲染器回退成表格。

payload 形状以 charts_pro/spec.py 的 REQUIRED 为单一出处：
  - items 类（hbar/vbar/treemap/pie/…）→ {"items": [{label, value}]}
  - histogram → {"values": [n, …]}
  - box/violin/ridge → {"groups": [{label, values:[…]}]}（按 entity 分组）
  - stacked/pct_stacked → {"categories": […], "series": [{name, values:[…]}]}
  - line → {"points": [{label, value}]}
"""
from __future__ import annotations

from typing import Any, Dict, List

ITEMS_TYPES = {"hbar", "vbar", "dot", "lollipop", "treemap", "pie", "donut",
               "waffle", "rose", "sunburst", "pareto", "share_bar", "diverging"}
GROUP_TYPES = {"box", "violin", "ridge", "hist_multi"}


def _v(f: Dict[str, Any], mixed: bool = False) -> float:
    """取数：同一张图里单位不一致时读 `value_base`（D-4 / P3-3）。

    单位一致时保留原值——否则「亿元」的图会被放大成「元」，可读性崩掉。
    """
    if mixed and f.get("unit_base"):
        try:
            return float(f.get("value_base") or 0)
        except (TypeError, ValueError):
            pass
    try:
        return float(f.get("value") or 0)
    except (TypeError, ValueError):
        return 0.0


def _mixed_units(facts: List[Dict[str, Any]]) -> bool:
    units = {str(f.get("unit") or "") for f in facts if f.get("unit")}
    return len(units) > 1


def _label(f: Dict[str, Any]) -> str:
    return str(f.get("entity") or f.get("metric") or f.get("name") or f.get("id") or "")


def build_payload(typ: str, facts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """facts → 指定图型的 payload。facts 同时容忍 IR 的 metric/entity 与
    evidence_pack 的 name/region 两种键名。"""
    typ = str(typ or "")
    mixed = _mixed_units(facts)
    if typ in ITEMS_TYPES:
        return {"items": [{"label": _label(f), "value": _v(f, mixed)} for f in facts]}
    if typ == "histogram":
        return {"values": [_v(f, mixed) for f in facts]}
    if typ in GROUP_TYPES:
        groups: Dict[str, List[float]] = {}
        for f in facts:
            k = str(f.get("entity") or f.get("region") or f.get("metric")
                    or f.get("name") or "全部")
            groups.setdefault(k, []).append(_v(f, mixed))
        return {"groups": [{"label": k, "values": v} for k, v in groups.items()]}
    if typ in ("stacked", "pct_stacked"):
        cats: List[str] = []
        metrics: List[str] = []
        for f in facts:
            c = str(f.get("entity") or f.get("region") or "")
            m = str(f.get("metric") or f.get("name") or "")
            if c and c not in cats:
                cats.append(c)
            if m and m not in metrics:
                metrics.append(m)
        series = []
        for m in metrics:
            vals = []
            for c in cats:
                v = next((_v(f, mixed) for f in facts
                          if str(f.get("metric") or f.get("name") or "") == m
                          and str(f.get("entity") or f.get("region") or "") == c), 0.0)
                vals.append(v)
            series.append({"name": m, "values": vals})
        return {"categories": cats, "series": series}
    if typ == "line":
        return {"points": [{"label": str(f.get("period") or _label(f)),
                            "value": _v(f, mixed)} for f in facts]}
    return {}

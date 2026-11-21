# -*- coding: utf-8 -*-
"""charts_pro.compat —— 把旧版 v2 chart dict 映射到 spec，供 report_renderer 使用。

映射不了的图型返回 None，由调用方回退 v1（不让报告因一张图失败）。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from . import spec


def _items(bars):
    return [{"label": str(b.get("label", "")), "value": float(b.get("value", 0))} for b in bars or []]


def _design(chart: Dict[str, Any], items) -> Dict[str, Any]:
    """把旧 chart dict 里的设计参数带过去：重点色、上限、小数位、注释指向。

    2026-11-21：以前只传了 items，于是升级引擎后所有柱子同色、刻度乱跳——
    看起来比旧引擎还差。设计参数不是新的数据，不能丢。
    """
    out: Dict[str, Any] = {}
    for k in ("max", "min", "decimals", "label", "unit"):
        if chart.get(k) is not None:
            out[k] = chart[k]
    # 旧 dict 的 ref 可能是数字，也可能是 {"value","label"} / {"min","max"}
    ref = chart.get("ref")
    if isinstance(ref, dict):
        if ref.get("value") is not None:
            out["ref"] = float(ref["value"])
            out["ref_label"] = str(ref.get("label") or "参照")
        elif ref.get("min") is not None and ref.get("max") is not None:
            out["ref"] = (float(ref["min"]) + float(ref["max"])) / 2
            out["ref_label"] = str(ref.get("label") or "区间中值")
    elif isinstance(ref, (int, float)):
        out["ref"] = float(ref)
        out["ref_label"] = str(chart.get("ref_label") or "参照")
    ann = chart.get("annotate") or []
    if isinstance(ann, str):
        out["accent_note"] = ann
    elif ann and isinstance(ann[0], dict):
        at = str(ann[0].get("at") or "").strip()
        if at:
            out["accent"] = at  # 用标签而不是下标：排序后下标会错位
            out["accent_note"] = str(ann[0].get("text") or "")
    # 基线：数值画参考线；{min,max} 画参考带（点图/带图支持 band）
    base = chart.get("baseline")
    if isinstance(base, (int, float)):
        out["ref"] = float(base)
        out["ref_label"] = str(chart.get("baseline_label") or "基线")
    elif isinstance(base, dict):
        if base.get("value") is not None:
            out["ref"] = float(base["value"])
            out["ref_label"] = str(base.get("label") or "基线")
        elif base.get("min") is not None and base.get("max") is not None:
            out["band"] = [float(base["min"]), float(base["max"])]
            out["ref"] = (float(base["min"]) + float(base["max"])) / 2
            out["ref_label"] = str(base.get("label") or "基线区间")
    return out


_ITEMS_TYPES = {"hbar", "vbar", "lollipop", "pareto", "share_bar",
                "treemap", "diverging", "waffle", "sunburst", "rose"}
_POINTS_TYPES = {"dot"}


def to_spec(chart: Dict[str, Any]) -> Optional[dict]:
    t = str(chart.get("type") or "")
    # 新形状（2026-11-21）：已经按 spec 结构写好的，直接透传
    if t == "line" and chart.get("points"):
        return {"type": "line", "points": chart["points"], **_design(chart, chart["points"])}
    if t == "range" and chart.get("rows"):
        return {"type": "range", "rows": chart["rows"], **_design(chart, chart["rows"])}
    bars = (chart.get("bars") or chart.get("vbars")
            or chart.get("items") or chart.get("points"))
    if t in _ITEMS_TYPES:
        if not bars:
            return None
        return {"type": t, "items": _items(bars), **_design(chart, bars)}
    if t in _POINTS_TYPES:
        if not bars:
            return None
        # 契约里 dot 用 items；charts_pro 的 dot 要 points。
        # 少于 5 条时不画中位线（两三个点谈中位数没意义）。
        return {"type": t, "points": _items(bars), "median": len(bars) >= 5,
                **_design(chart, bars)}
    if t == "line":
        xs = chart.get("xlabels") or []
        series = chart.get("series") or []
        if not series:
            return None
        pts = [{"label": (xs[i] if i < len(xs) else str(i)), "value": v}
               for i, v in enumerate(series[0].get("values") or [])]
        return {"type": "line", "points": pts}
    if t == "area":
        base = to_spec({**chart, "type": "line"})
        return {**base, "type": "area"} if base else None
    if t == "scatter":
        pts = chart.get("points") or []
        if not pts:
            return None
        return {"type": "scatter",
                "points": [{"x": float(p.get("x", 0)), "y": float(p.get("y", 0))} for p in pts]}
    if t in ("pie", "donut"):
        items = _items(chart.get("bars") or chart.get("items"))
        if not items:
            return None
        return {"type": t, "items": items}
    if t == "funnel":
        stages = chart.get("stages") or []
        if not stages:
            return None
        return {"type": "funnel",
                "stages": [{"label": str(s.get("label", "")), "value": float(s.get("value", 0))}
                           for s in stages]}
    if t == "heatmap":
        rows, cols, m = chart.get("rows"), chart.get("cols"), chart.get("matrix")
        if not (rows and cols and m):
            return None
        return {"type": "heatmap", "rows": rows, "cols": cols, "matrix": m}
    return None


def render_chart(chart: Dict[str, Any], theme: str = "paper") -> Optional[str]:
    s = to_spec(chart)
    if not s:
        return None
    try:
        return spec.render(s)
    except Exception:  # noqa: BLE001
        return None

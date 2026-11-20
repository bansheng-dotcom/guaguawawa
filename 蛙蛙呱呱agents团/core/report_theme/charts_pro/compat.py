# -*- coding: utf-8 -*-
"""charts_pro.compat —— 把旧版 v2 chart dict 映射到 spec，供 report_renderer 使用。

映射不了的图型返回 None，由调用方回退 v1（不让报告因一张图失败）。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from . import spec


def _items(bars):
    return [{"label": str(b.get("label", "")), "value": float(b.get("value", 0))} for b in bars or []]


def to_spec(chart: Dict[str, Any]) -> Optional[dict]:
    t = str(chart.get("type") or "")
    if t in ("hbar", "vbar"):
        bars = chart.get("bars") or chart.get("vbars")
        if not bars:
            return None
        return {"type": t, "items": _items(bars)}
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

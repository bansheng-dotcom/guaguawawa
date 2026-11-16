# -*- coding: utf-8 -*-
"""core.charts.v2.types_part —— 构成类：环形、饼、树图。

构成图只在“加起来等于 100%”时使用；标签直接写百分比，不画图例。
注意：环形/饼必须一次 pie() 画完所有扇区，逐块调用会被后画的整圆覆盖。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

from matplotlib.patches import Rectangle

from . import base as _base
from .base import canvas, fmt_num, svg_of


def _items(chart: Dict[str, Any]) -> List[Dict[str, Any]]:
    return sorted([i for i in (chart.get("items") or []) if i.get("value") is not None],
                  key=lambda i: -float(i["value"]))


def _colors(items: List[Dict[str, Any]], T: Dict[str, Any]) -> List[str]:
    return [T["accent"] if it.get("accent") else T["cat"][i % len(T["cat"])]
            for i, it in enumerate(items)]


def donut(chart: Dict[str, Any], theme: str) -> str:
    items = _items(chart)
    total = sum(float(i["value"]) for i in items) or 1.0
    fig, ax, T = canvas(320, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""), subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""), pad_l=10, pad_r=10, pad_b=36)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-1.62, 1.62)
    ax.set_ylim(-1.30, 1.30)
    fracs = [float(i["value"]) / total for i in items]
    ax.pie(fracs, colors=_colors(items, T), radius=1.0, center=(0, 0), startangle=90,
           counterclock=False, normalize=True,
           wedgeprops=dict(width=0.40, edgecolor=T["paper"], linewidth=1.6))
    start = 90.0
    for idx, it in enumerate(items):
        frac = fracs[idx]
        mid = math.radians(start - frac * 180.0) if frac < 1 else math.radians(90)
        if frac >= 0.999:      # 只有一类：标签放正上方
            mid = math.radians(90)
        lx, ly = 1.34 * math.cos(mid), 1.34 * math.sin(mid)
        ha = "left" if math.cos(mid) >= 0 else "right"
        ax.annotate(f"{it.get('label', '')} {frac:.1%}",
                    xy=(1.0 * math.cos(mid), 1.0 * math.sin(mid)), xytext=(lx, ly),
                    ha=ha, va="center", fontsize=9.6, color=T["ink"],
                    arrowprops=dict(arrowstyle="-", color=T["line_strong"], linewidth=0.7,
                                    shrinkA=0, shrinkB=3))
        start -= frac * 360.0
    center = chart.get("center") or {"label": "合计", "value": total}
    ax.text(0, 0.07, fmt_num(float(center.get("value", total))), ha="center", va="center",
            fontsize=25, fontweight="bold", color=T["ink"])
    ax.text(0, -0.23, str(center.get("label", "合计")), ha="center", va="center",
            fontsize=9.6, color=T["muted"])
    if items:
        ax.text(0, -1.19, f"最大项：{str(items[0].get('label', ''))[:8]} {fracs[0]:.1%}",
                ha="center", va="center", fontsize=8.4, color=T["accent"])
    return svg_of(fig)


def pie(chart: Dict[str, Any], theme: str) -> str:
    items = _items(chart)
    total = sum(float(i["value"]) for i in items) or 1.0
    fig, ax, T = canvas(300, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""), subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""), pad_l=10, pad_r=10, pad_b=36)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-1.30, 2.55)
    ax.set_ylim(-1.15, 1.15)
    fracs = [float(i["value"]) / total for i in items]
    colors = _colors(items, T)
    ax.pie(fracs, colors=colors, radius=1.0, center=(0, 0), startangle=90,
           counterclock=False, normalize=True,
           wedgeprops=dict(edgecolor=T["paper"], linewidth=1.4))
    start = 90.0
    for idx, frac in enumerate(fracs):
        if frac >= 0.07:
            mid = math.radians(start - frac * 180.0)
            ax.text(0.62 * math.cos(mid), 0.62 * math.sin(mid), f"{frac:.0%}",
                    ha="center", va="center", fontsize=9.8, fontweight="bold", color="#FFFFFF")
        start -= frac * 360.0
    for idx, it in enumerate(items[:6]):
        frac = fracs[idx]
        y = 0.92 - idx * 0.30
        ax.add_patch(Rectangle((1.20, y - 0.045), 0.09, 0.09, color=colors[idx], clip_on=False))
        ax.text(1.34, y, f"{it.get('label', '')} {frac:.1%}", ha="left", va="center",
                fontsize=9.4, color=T["ink"], clip_on=False)
    if items:
        ax.text(1.20, -0.98, f"最大项：{str(items[0].get('label', ''))[:8]} {fracs[0]:.1%}",
                ha="left", va="center", fontsize=8.4, color=T["accent"], clip_on=False)
    return svg_of(fig)


def treemap(chart: Dict[str, Any], theme: str) -> str:
    items = _items(chart)
    total = sum(float(i["value"]) for i in items) or 1.0
    fig, ax, T = canvas(320, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""), subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""), pad_l=10, pad_r=10, pad_b=36)
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    rects: List[Tuple[float, float, float, float]] = []
    _squarify([float(i["value"]) / total for i in items], [0.0, 0.0, 1.0, 1.0], rects)
    colors = _colors(items, T)
    for idx, (it, r) in enumerate(zip(items, rects)):
        x, y, w, h = r
        ax.add_patch(Rectangle((x + 0.002, y + 0.002), max(w - 0.004, 0), max(h - 0.004, 0),
                               facecolor=colors[idx], edgecolor=T["paper"], linewidth=1.4))
        frac = float(it["value"]) / total
        if w * h > 0.035:
            ax.text(x + w / 2, y + h / 2 + 0.02, str(it.get("label", "")), ha="center",
                    va="center", fontsize=9.6, color="#FFFFFF", fontweight="bold")
            ax.text(x + w / 2, y + h / 2 - 0.05, f"{frac:.0%}", ha="center", va="center",
                    fontsize=9.0, color="#FFFFFF")
    if items and not _base.EMBED:
        h = fig.get_size_inches()[1] * 100.0
        fig.text(0.5, 18.0 / h,
                 f"最大项：{str(items[0].get('label', ''))[:10]} "
                 f"{float(items[0]['value']) / total:.1%}",
                 ha="center", va="bottom", fontsize=8.4, color=T["accent"])
    return svg_of(fig)


def _squarify(values: List[float], rect: List[float],
              out: List[Tuple[float, float, float, float]]) -> None:
    if not values:
        return
    if len(values) == 1:
        out.append((rect[0], rect[1], rect[2], rect[3]))
        return
    total = sum(values) or 1.0
    best_i, best_score = 1, float("inf")
    for i in range(1, len(values)):
        a = sum(values[:i]) / total
        b = 1.0 - a
        score = max(a / max(b, 1e-9), b / max(a, 1e-9))
        if score < best_score:
            best_i, best_score = i, score
    a = sum(values[:best_i]) / total
    x, y, w, h = rect
    if w >= h:
        _squarify(values[:best_i], [x, y, w * a, h], out)
        _squarify(values[best_i:], [x + w * a, y, w * (1 - a), h], out)
    else:
        _squarify(values[:best_i], [x, y, w, h * a], out)
        _squarify(values[best_i:], [x, y + h * a, w, h * (1 - a)], out)

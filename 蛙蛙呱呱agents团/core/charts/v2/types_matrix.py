# -*- coding: utf-8 -*-
"""core.charts.v2.types_matrix —— 矩阵类：热力图。

规则：单色阶（浅→深 = 低→高），格内直接写数值，缺失格用斜纹而不是 0；
行列标签贴着网格，网格铺满画布（v1 的 viewBox 最小 760 导致右侧一片空白）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle

from .base import canvas, fmt_num, svg_of


def _mix(c1: str, c2: str, t: float) -> tuple:
    """两色线性插值（#rrggbb），t=0 取 c1。"""
    a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
    return tuple((a[i] + (b[i] - a[i]) * t) / 255 for i in range(3))


def heatmap(chart: Dict[str, Any], theme: str) -> str:
    rows: List[str] = [str(r) for r in (chart.get("rows") or [])]
    cols: List[str] = [str(c) for c in (chart.get("cols") or [])]
    cells: List[List[Any]] = chart.get("cells") or []
    if not rows or not cols or len(cells) != len(rows):
        return None

    vals = [c for r in cells for c in r if c is not None]
    vmin = min(vals) if vals else 0.0
    vmax = max(vals) if vals else 1.0
    span = (vmax - vmin) or 1.0

    fig, ax, T = canvas(300, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""), subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""), pad_l=132, pad_r=24, pad_b=58, pad_t=64)
    ax.axis("off")
    ax.set_xlim(0, len(cols))
    ax.set_ylim(0, len(rows))

    base = T["paper"]
    for i, row in enumerate(cells):
        for j, v in enumerate(row):
            y = len(rows) - 1 - i
            if v is None:
                ax.add_patch(Rectangle((j + 0.03, y + 0.05), 0.94, 0.90,
                                       facecolor=T["surface"], edgecolor="none",
                                       hatch="///", linewidth=0))
                continue
            t = (float(v) - vmin) / span
            color = _mix(base, T["accent"], 0.12 + 0.78 * t)
            ax.add_patch(Rectangle((j + 0.03, y + 0.05), 0.94, 0.90,
                                   facecolor=color, edgecolor="none"))
            ink = "#FFFFFF" if t > 0.55 else T["ink"]
            ax.text(j + 0.5, y + 0.5, fmt_num(v), ha="center", va="center",
                    fontsize=11.5, fontweight="bold", color=ink)

    for j, c in enumerate(cols):
        ax.text(j + 0.5, len(rows) + 0.10, c, ha="center", va="bottom",
                fontsize=9.8, color=T["ink"])
    for i, r in enumerate(rows):
        ax.text(-0.10, len(rows) - 0.5 - i, r, ha="right", va="center",
                fontsize=10.2, color=T["ink"])

    # 色阶图例（右下，浅→深 = 低→高）
    ax.text(len(cols) - 1.10, -0.20, f"低 {fmt_num(vmin)}", ha="left", va="top",
            fontsize=8.6, color=T["muted"])
    ax.text(len(cols), -0.20, f"高 {fmt_num(vmax)}", ha="right", va="top",
            fontsize=8.6, color=T["muted"])
    for k in range(10):
        ax.add_patch(Rectangle((len(cols) - 1.05 + k * 0.05, -0.08), 0.05, 0.035,
                               facecolor=_mix(base, T["accent"], 0.12 + 0.078 * k),
                               edgecolor="none"))
    peak = next(((i, j) for i, row in enumerate(cells) for j, v in enumerate(row)
                 if v is not None and float(v) == float(vmax)), None)
    if peak is not None:
        # 放在轴下方左端：贴列标签上方会压住最后一列的列名
        ax.text(-0.10, -0.62,
                f"最大格：{rows[peak[0]]} × {cols[peak[1]]} {fmt_num(vmax)}",
                ha="left", va="top", fontsize=8.4, color=T["accent"], clip_on=False)
    return svg_of(fig)

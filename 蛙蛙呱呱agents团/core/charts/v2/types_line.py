# -*- coding: utf-8 -*-
"""core.charts.v2.types_line —— 趋势类：折线、面积、斜率、小倍数。

趋势图保留纵轴（读者要读量级），但只留 4 档、只画横网格；
线末端直接标系列名 + 末值，不用图例。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import base as _base
from .base import bare_axes, canvas, fmt_num, svg_of


def _xlabels(chart: Dict[str, Any]) -> List[str]:
    return [str(x) for x in (chart.get("xlabels") or [])]


def _series(chart: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [s for s in (chart.get("series") or []) if s.get("values")]


def _ylim_from(ss, ax, pad: float = 0.12) -> None:
    vals = [float(v) for s in ss for v in s.get("values") or []]
    if not vals:
        ax.set_ylim(0, 1)
        return
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or abs(hi) * 0.1 or 1.0
    ax.set_ylim(lo - span * pad, hi + span * pad)


def _trend_axes(ax, T: Dict[str, Any], n: int) -> None:
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(T["line_strong"])
    ax.spines["bottom"].set_linewidth(0.9)
    ax.grid(axis="y", color=T["line"], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, labelsize=9.0, colors=T["muted"], labelleft=True)
    ax.tick_params(axis="x", length=0, labelsize=9.4, colors=T["muted"])
    ax.set_xlim(-0.25, max(n - 1, 1) + 0.25)


def _yticks(ax) -> None:
    """4 档整数刻度，带千分位；保证折线有量级可读。"""
    from matplotlib.ticker import MaxNLocator

    ax.yaxis.set_major_locator(MaxNLocator(4, steps=[1, 2, 2.5, 5, 10], integer=True))
    ax.yaxis.set_major_formatter(
        __import__("matplotlib").ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.tick_params(axis="y", labelleft=True, length=0, labelsize=9.0)


def line(chart: Dict[str, Any], theme: str) -> str:
    xl, ss = _xlabels(chart), _series(chart)
    n = max(len(xl), 2)
    fig, ax, T = canvas(340, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""), subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""), pad_l=64, pad_r=132, pad_b=70)
    _trend_axes(ax, T, n)
    _ylim_from(ss, ax)
    _yticks(ax)
    for j, s in enumerate(ss):
        vals = [float(v) for v in s["values"]]
        color = T["accent"] if s.get("accent") or j == 0 else T["cat"][(j + 1) % len(T["cat"])]
        ax.plot(range(len(vals)), vals, color=color, linewidth=2.2, zorder=3,
                solid_capstyle="round")
        if len(vals) <= 7:
            ax.plot(range(len(vals)), vals, "o", markersize=4.4, color=color,
                    markeredgecolor=T["paper"], markeredgewidth=1.0, zorder=4)
        ax.annotate(f"{s.get('name', '')} {fmt_num(vals[-1])}".strip(),
                    xy=(len(vals) - 1, vals[-1]), xytext=(9, 0), textcoords="offset points",
                    va="center", ha="left", fontsize=9.6, fontweight="bold", color=color)
    ref = chart.get("ref") if isinstance(chart.get("ref"), dict) else None
    ref_v = float(ref["value"]) if ref and ref.get("value") is not None else None
    if ref_v is not None:
        ax.axhline(ref_v, color=T["reference"], linewidth=1.0, linestyle=(0, (4, 3)),
                   zorder=2, clip_on=False)
        ax.text(0, ref_v, f" {ref.get('label', '')}", ha="left", va="bottom",
                fontsize=8.2, color=T["reference"], zorder=5)
    if ss and xl and not _base.EMBED:
        first = [float(v) for v in ss[0]["values"]]
        k = max(range(len(first)), key=lambda i: first[i])
        fig.text(1.0, 1.0 - 33.0 / (fig.get_size_inches()[1] * 100.0),
                 f"峰值 {fmt_num(first[k])}（{str(xl[k])[:8]}）",
                 ha="right", va="top", fontsize=8.4, color=T["accent"])
    n_pt = len(xl)
    step = max(1, (n_pt + 7) // 8) if n_pt > 9 else 1
    idx = list(range(0, n_pt, step))
    ax.set_xticks(idx)
    ax.set_xticklabels([xl[i] for i in idx], fontsize=9.4, color=T["muted"])
    return svg_of(fig)


def area(chart: Dict[str, Any], theme: str) -> str:
    xl, ss = _xlabels(chart), _series(chart)
    n = max(len(xl), 2)
    fig, ax, T = canvas(340, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""), subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""), pad_l=64, pad_r=118, pad_b=70)
    _trend_axes(ax, T, n)
    _ylim_from(ss, ax)
    _yticks(ax)
    ax.set_ylim(bottom=0)
    for j, s in enumerate(ss):
        vals = [float(v) for v in s["values"]]
        color = T["accent"] if s.get("accent") or j == 0 else T["cat"][(j + 1) % len(T["cat"])]
        ax.fill_between(range(len(vals)), vals, color=color, alpha=0.14, zorder=2)
        ax.plot(range(len(vals)), vals, color=color, linewidth=2.0, zorder=3)
        ax.annotate(f"{s.get('name', '')} {fmt_num(vals[-1])}".strip(),
                    xy=(len(vals) - 1, vals[-1]), xytext=(9, 0), textcoords="offset points",
                    va="center", ha="left", fontsize=9.6, fontweight="bold", color=color)
    ref = chart.get("ref") if isinstance(chart.get("ref"), dict) else None
    ref_v = float(ref["value"]) if ref and ref.get("value") is not None else None
    if ref_v is not None:
        ax.axhline(ref_v, color=T["reference"], linewidth=1.0, linestyle=(0, (4, 3)),
                   zorder=2, clip_on=False)
        ax.text(0, ref_v, f" {ref.get('label', '')}", ha="left", va="bottom",
                fontsize=8.2, color=T["reference"], zorder=5)
    if ss and xl and not _base.EMBED:
        first = [float(v) for v in ss[0]["values"]]
        k = max(range(len(first)), key=lambda i: first[i])
        fig.text(1.0, 1.0 - 33.0 / (fig.get_size_inches()[1] * 100.0),
                 f"峰值 {fmt_num(first[k])}（{str(xl[k])[:8]}）",
                 ha="right", va="top", fontsize=8.4, color=T["accent"])
    n_pt = len(xl)
    step = max(1, (n_pt + 7) // 8) if n_pt > 9 else 1
    idx = list(range(0, n_pt, step))
    ax.set_xticks(idx)
    ax.set_xticklabels([xl[i] for i in idx], fontsize=9.4, color=T["muted"])
    return svg_of(fig)


def slope(chart: Dict[str, Any], theme: str) -> str:
    items = [i for i in (chart.get("items") or [])
             if i.get("a") is not None and i.get("b") is not None]
    a_lab = str(chart.get("a_label") or "前")
    b_lab = str(chart.get("b_label") or "后")
    fig, ax, T = canvas(360, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""), subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""), pad_l=150, pad_r=150, pad_b=48)
    bare_axes(ax, T)
    ax.set_xlim(-0.02, 1.02)
    allv = [float(v) for i in items for v in (i["a"], i["b"])]
    if allv:
        lo, hi = min(allv), max(allv)
        pad = (hi - lo) * 0.18 or 1.0
        ax.set_ylim(lo - pad, hi + pad)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([a_lab, b_lab], fontsize=10, color=T["ink"])
    ax.tick_params(axis="x", length=0, pad=10, labelbottom=True)
    ax.set_yticks([])
    if allv:
        med = sorted(allv)[len(allv) // 2]
        ax.axhline(med, color=T["reference"], linewidth=1.0, linestyle=(0, (4, 3)),
                   zorder=2, clip_on=False)
        ax.text(0.5, med, f"中位 {fmt_num(med)}", ha="center", va="bottom",
                fontsize=8.2, color=T["reference"], zorder=5)
    for it in sorted(items, key=lambda x: -abs(float(x["b"]) - float(x["a"]))):
        a, b = float(it["a"]), float(it["b"])
        color = T["healthy"] if b >= a else T["critical"]
        ax.plot([0, 1], [a, b], color=color, linewidth=1.8, alpha=0.9, zorder=3,
                solid_capstyle="round")
        ax.plot([0, 1], [a, b], "o", markersize=4.8, color=color, zorder=4)
        ax.annotate(f"{it.get('label', '')} {fmt_num(a)}", xy=(0, a), xytext=(-10, 0),
                    textcoords="offset points", ha="right", va="center",
                    fontsize=9.4, color=T["muted"], annotation_clip=False)
        ax.annotate(fmt_num(b), xy=(1, b), xytext=(10, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=9.8, fontweight="bold",
                    color=T["ink"], annotation_clip=False)
    if items and not _base.EMBED:
        top = max(items, key=lambda it: abs(float(it["b"]) - float(it["a"])))
        d = float(top["b"]) - float(top["a"])
        fig.text(1.0, 1.0 - 33.0 / (fig.get_size_inches()[1] * 100.0),
                 f"变化最大：{str(top.get('label', ''))[:8]} "
                 f"{'+' if d >= 0 else '−'}{fmt_num(abs(d))}",
                 ha="right", va="top", fontsize=8.4, color=T["accent"])
    return svg_of(fig)


def small_mult(chart: Dict[str, Any], theme: str) -> str:
    panels = chart.get("panels") or []
    k = max(len(panels), 1)
    cols = min(k, 3)
    rows = (k + cols - 1) // cols
    h = 96.0 + rows * 132.0
    fig, _ax, T = canvas(h, theme, "", "", chart.get("source", ""),
                         subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                         pad_t=10, pad_b=28, pad_l=10, pad_r=10)
    # canvas 会建一张满幅底轴；小倍数图自己排版，底轴必须关掉，
    # 否则 0—1.0 的默认刻度会压在每个面板下面（旧版重叠的根因）。
    _ax.set_axis_off()
    if not _base.EMBED:
        fig.text(0.0, 1.0 - 12.0 / h, str(chart.get("title", "")), fontsize=13.0,
                 fontweight="bold", color=T["ink"], va="top")
        if chart.get("unit_meta"):
            fig.text(1.0, 1.0 - 15.0 / h, str(chart["unit_meta"]), ha="right", va="top",
                     fontsize=10.0, color=T["muted"])
    grid_top = 1.0 if _base.EMBED else 1.0 - (58.0 if chart.get("subtitle") else 40.0) / h
    grid_bot = 28.0 / h
    cell_h = (grid_top - grid_bot) / rows
    cell_w = 0.98 / cols
    for idx, p in enumerate(panels):
        vals = [float(v) for v in (p.get("values") or [])]
        if not vals:
            continue
        row, col = idx // cols, idx % cols
        ax = fig.add_axes([0.01 + col * cell_w, grid_bot + (rows - 1 - row) * cell_h + 0.03,
                           cell_w - 0.045, cell_h - 0.09])
        color = T["accent"]
        ax.plot(range(len(vals)), vals, color=color, linewidth=1.6, zorder=3)
        ax.fill_between(range(len(vals)), vals, color=color, alpha=0.10, zorder=2)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(T["line"])
        ax.tick_params(axis="both", length=0, labelleft=False, labelsize=7.6, colors=T["muted"])
        ax.set_yticks([])
        lo, hi = min(vals), max(vals)
        pad = (hi - lo) * 0.25 or 1.0
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_title(str(p.get("label", "")), fontsize=9.4, color=T["ink"], loc="left", pad=4)
        mid = sum(vals) / len(vals)
        ax.axhline(mid, color=T["reference"], linewidth=0.8, linestyle=(0, (4, 3)),
                   zorder=2)
        ax.annotate(fmt_num(vals[-1]), xy=(len(vals) - 1, vals[-1]), xytext=(4, 0),
                    textcoords="offset points", fontsize=8.6, fontweight="bold",
                    color=T["ink"], va="center")
    best, best_d = None, None
    for p in panels:
        pv = [float(v) for v in (p.get("values") or [])]
        if len(pv) >= 2:
            d = pv[-1] - pv[0]
            if best_d is None or d > best_d:
                best, best_d = p, d
    if best is not None and best_d is not None and not _base.EMBED:
        fig.text(1.0, 1.0 - 33.0 / h,
                 f"涨幅最大：{str(best.get('label', ''))[:8]} "
                 f"{'+' if best_d >= 0 else '−'}{fmt_num(abs(best_d))}",
                 ha="right", va="top", fontsize=8.4, color=T["accent"])
    return svg_of(fig)

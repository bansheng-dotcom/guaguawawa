# -*- coding: utf-8 -*-
"""core.charts.v2.types_bar —— 比较类：条形、点图、帕累托、瀑布、哑铃、分组/堆叠。

规则：
- 基准条一律灰，只有“重点/好坏”才上语义色；
- 数值直接标在末端；类目标签右对齐、超长截断；
- 瀑布图遇到“总量远大于变化量”时用断轴（zigzag），不让增量变成一条线。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .base import bar_width, canvas, fmt_num, label_of, nice_height, style_ylabels, svg_of

_MAX_LABEL = 14


def _short(s: Any, n: int = _MAX_LABEL) -> str:
    t = str(s or "")
    return t if len(t) <= n else t[: n - 1] + "…"


def _tone(weight: str, T: Dict[str, Any]) -> str:
    return {
        "accent": T["accent"], "critical": T["critical"], "healthy": T["healthy"],
        "watch": T["watch"], "context": T["context"], "reference": T["reference"],
    }.get(str(weight or "context"), T["context"])


def _sorted_bars(chart: Dict[str, Any]) -> List[Dict[str, Any]]:
    bars = [b for b in (chart.get("bars") or chart.get("vbars") or []) if b.get("value") is not None]
    order = str(chart.get("sort") or "desc")
    if order == "asc":
        return sorted(bars, key=lambda b: float(b["value"]))
    if order == "none":
        return bars
    return sorted(bars, key=lambda b: -float(b["value"]))


# --------------------------------------------------------------------------- #
def hbar(chart: Dict[str, Any], theme: str) -> str:
    bars = _sorted_bars(chart)
    n = max(len(bars), 1)
    fig, ax, T = canvas(nice_height(n, row=44), theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        pad_b=34, pad_r=96)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color=T["line"], linewidth=0.8)
    ax.set_axisbelow(True)
    ys = list(range(n))[::-1]
    vals = [float(b["value"]) for b in bars]
    ref = chart.get("ref") if isinstance(chart.get("ref"), dict) else None
    ref_v = float(ref["value"]) if ref and ref.get("value") is not None else None
    vmax = max(vals + ([ref_v] if ref_v is not None else []) + [0.0]) if vals else 1.0
    vmin = min(vals + [0.0]) if vals else 0.0
    span = (vmax - vmin) or 1.0
    pad = span * 0.10
    ax.set_xlim(vmin - pad, vmax + pad)
    ax.set_ylim(-0.5, n - 0.5)
    if vmin < 0:
        ax.axvline(0, color=T["muted"], linewidth=0.9, zorder=2)
    for y, b in zip(ys, bars):
        v = float(b["value"])
        ax.barh(y, v, height=0.64, color=_tone(b.get("weight"), T), edgecolor="none", zorder=3)
        off = span * 0.015
        if v >= 0:
            ax.text(v + off, y, label_of(b), va="center", ha="left",
                    fontsize=11.0, fontweight="bold", color=T["ink"], zorder=4)
        else:
            ax.text(v - off, y, label_of(b), va="center", ha="right",
                    fontsize=11.0, fontweight="bold", color=T["ink"], zorder=4)
    ax.set_yticks(ys)
    ax.set_yticklabels([_short(b.get("label")) for b in bars])
    style_ylabels(ax, T)
    ax.set_xticks([])
    if ref_v is not None:
        # 目标/停止线画进图里（SOP v3 P1-1），不只在正文里写一句
        ax.axvline(ref_v, color=T["muted"], linewidth=1.0, linestyle=(0, (4, 3)),
                   zorder=5, clip_on=False)
        ax.text(ref_v, n - 0.52, f" {ref.get('label', '')}", ha="right", va="bottom",
                fontsize=8.8, color=T["muted"], zorder=6)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
def vbar(chart: Dict[str, Any], theme: str) -> str:
    bars = [b for b in (chart.get("bars") or chart.get("vbars") or []) if b.get("value") is not None]
    n = max(len(bars), 1)
    fig, ax, T = canvas(300, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""), pad_l=40, pad_r=40, pad_b=58)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color=T["line"], linewidth=0.8)
    ax.set_axisbelow(True)
    vals = [float(b["value"]) for b in bars]
    vmax = max(vals + [0.0]) if vals else 1.0
    vmin = min(vals + [0.0]) if vals else 0.0
    span = (vmax - vmin) or 1.0
    ax.set_ylim(vmin - span * (0.24 if vmin < 0 else 0.06), vmax + span * 0.18)
    ax.set_xlim(-0.62, n - 0.38)
    if vmin < 0:
        ax.axhline(0, color=T["muted"], linewidth=0.9, zorder=2)
    w = 0.52 if n <= 4 else 0.42
    for x, b in enumerate(bars):
        v = float(b["value"])
        ax.bar(x, v, width=w, color=_tone(b.get("weight"), T), edgecolor="none", zorder=3)
        if v >= 0:
            ax.text(x, v + span * 0.03, label_of(b), ha="center", va="bottom",
                    fontsize=10.4, fontweight="bold", color=T["ink"], zorder=4)
        else:
            ax.text(x, v - span * 0.03, label_of(b), ha="center", va="top",
                    fontsize=10.4, fontweight="bold", color=T["ink"], zorder=4)
    ax.set_xticks(range(n))
    ax.set_xticklabels([_short(b.get("label"), 10) for b in bars], fontsize=9.8, color=T["ink"])
    ax.tick_params(axis="x", length=0, pad=8, labelbottom=True)
    ax.set_yticks([])
    return svg_of(fig)


# --------------------------------------------------------------------------- #
def dot(chart: Dict[str, Any], theme: str) -> str:
    items = sorted([i for i in (chart.get("items") or []) if i.get("value") is not None],
                   key=lambda i: -float(i["value"]))
    n = max(len(items), 1)
    fig, ax, T = canvas(nice_height(n, row=40), theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        pad_b=34, pad_r=96)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color=T["line"], linewidth=0.8)
    ax.set_axisbelow(True)
    ys = list(range(n))[::-1]
    vmax = max(float(i["value"]) for i in items) if items else 1.0
    ax.set_xlim(0, vmax * 1.30)
    ax.set_ylim(-0.5, n - 0.5)
    for y, it in zip(ys, items):
        v = float(it["value"])
        ax.plot([0, v], [y, y], color=T["line"], linewidth=1.4, zorder=2, solid_capstyle="round")
        ax.plot([v], [y], marker="o", markersize=8.0, color=_tone(it.get("weight"), T),
                zorder=3, markeredgecolor=T["paper"], markeredgewidth=1.2)
        ax.text(v + vmax * 0.025, y, label_of(it), va="center", ha="left",
                fontsize=10.8, fontweight="bold", color=T["ink"], zorder=4)
    ax.set_yticks(ys)
    ax.set_yticklabels([_short(i.get("label")) for i in items])
    style_ylabels(ax, T)
    ax.set_xticks([])
    return svg_of(fig)


# --------------------------------------------------------------------------- #
def pareto(chart: Dict[str, Any], theme: str) -> str:
    items = sorted([i for i in (chart.get("items") or []) if i.get("value") is not None],
                   key=lambda i: -float(i["value"]))
    n = max(len(items), 1)
    fig, ax, T = canvas(320, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""), pad_l=40, pad_r=58, pad_b=72)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color=T["line"], linewidth=0.8)
    ax.set_axisbelow(True)
    vals = [float(i["value"]) for i in items]
    total = sum(vals) or 1.0
    vmax = max(vals) or 1.0
    ax.set_ylim(0, vmax * 1.24)
    ax.set_xlim(-0.62, n - 0.38)
    for x, it in enumerate(items):
        v = float(it["value"])
        ax.bar(x, v, width=0.5, color=T["accent"] if x == 0 else T["context"],
               edgecolor="none", zorder=3)
        ax.text(x, v + vmax * 0.03, fmt_num(v), ha="center", va="bottom",
                fontsize=9.8, color=T["ink"], zorder=4)
    cum, acc = [], 0.0
    for v in vals:
        acc += v
        cum.append(acc / total * 100)
    ax2 = ax.twinx()
    ax2.set_ylim(0, 108)
    ax2.plot(range(n), cum, color=T["accent2"], linewidth=1.8, marker="o", markersize=3.4, zorder=5)
    thr = float(chart.get("threshold") or 80)
    ax2.axhline(thr, color=T["muted"], linewidth=0.9, linestyle=(0, (4, 3)), zorder=2)
    ax2.text(n - 0.42, thr + 2, f"{thr:.0f}%", ha="right", va="bottom",
             fontsize=8.8, color=T["muted"])
    for side in ("top", "right", "left", "bottom"):
        ax2.spines[side].set_visible(False)
    ax2.set_yticks([])
    ax.set_xticks(range(n))
    ax.set_xticklabels([_short(i.get("label"), 8) for i in items], fontsize=9.4, color=T["ink"])
    ax.tick_params(axis="x", length=0, pad=8, labelbottom=True)
    ax.set_yticks([])
    return svg_of(fig)


# --------------------------------------------------------------------------- #
def waterfall(chart: Dict[str, Any], theme: str) -> str:
    steps = [s for s in (chart.get("steps") or []) if s.get("value") is not None]
    n = max(len(steps), 1)
    fig, ax, T = canvas(320, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""), pad_l=40, pad_b=72)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    run = 0.0
    bars = []          # (bot, top, is_total)
    for s in steps:
        v = float(s["value"])
        is_total = str(s.get("type") or "") == "total" or bool(s.get("total"))
        if is_total:
            bars.append((0.0, v, True))
            run = v
        else:
            bars.append((min(run, run + v), max(run, run + v), False))
            run += v

    totals = [b[1] for b in bars if b[2]]
    deltas = [abs(b[1] - b[0]) for b in bars if not b[2]]
    big = max(totals) if totals else 0.0
    span = max([b[1] for b in bars] + [0.0]) - min([b[0] for b in bars] + [0.0])
    # 断轴：增量总和相对总量很小（<25%），纵轴不从 0 起，否则增量只剩一条线
    cut = bool(deltas) and big > 0 and sum(deltas) < big * 0.25
    base = (min(totals) - max(deltas) * 0.9) if cut else 0.0
    hi = max(b[1] for b in bars)
    head = (hi - base) * 0.16 or 1.0
    ax.set_ylim(base, hi + head)
    ax.set_xlim(-0.62, n - 0.38)

    for i, (bot, top, is_total) in enumerate(bars):
        s = steps[i]
        v = float(s["value"])
        color = T["accent"] if is_total else (T["healthy"] if v >= 0 else T["critical"])
        b = base if is_total else bot
        ax.bar(i, top - b, bottom=b, width=0.5, color=color, edgecolor="none", zorder=3)
        lab = fmt_num(top if is_total else v)
        if not is_total and v > 0:
            lab = "+" + lab
        ax.text(i, top, lab, ha="center", va="bottom", fontsize=10.0, fontweight="bold",
                color=T["ink"], zorder=4)
        if cut and is_total:
            # 断轴标记：柱底两条白斜线
            ax.plot([i - 0.15, i + 0.15], [base + (hi - base) * 0.010] * 2,
                    color=T["paper"], linewidth=2.2, zorder=5)
            ax.plot([i - 0.15, i + 0.15], [base + (hi - base) * 0.020] * 2,
                    color=T["paper"], linewidth=2.2, zorder=5)
        if i < len(bars) - 1:
            ax.plot([i + 0.25, i + 0.75], [top, top], color=T["line_strong"],
                    linewidth=0.9, zorder=2)

    ax.set_xticks(range(n))
    ax.set_xticklabels([_short(s.get("label"), 9) for s in steps], fontsize=9.4, color=T["ink"])
    ax.tick_params(axis="x", length=0, pad=8, labelbottom=True)
    ax.set_yticks([])
    return svg_of(fig)


def dumbbell(chart: Dict[str, Any], theme: str) -> str:
    items = [i for i in (chart.get("items") or [])
             if i.get("a") is not None and i.get("b") is not None]
    items = sorted(items, key=lambda i: -abs(float(i["b"]) - float(i["a"])))
    n = max(len(items), 1)
    fig, ax, T = canvas(nice_height(n, row=44), theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        pad_b=44, pad_r=104)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ys = list(range(n))[::-1]
    allv = [float(v) for i in items for v in (i["a"], i["b"])] or [0, 1]
    lo, hi = min(allv), max(allv)
    span = (hi - lo) or 1.0
    ax.set_xlim(lo - span * 0.10, hi + span * 0.26)
    ax.set_ylim(-0.5, n - 0.5)
    for y, it in zip(ys, items):
        a, b = float(it["a"]), float(it["b"])
        ax.plot([a, b], [y, y], color=T["line_strong"], linewidth=2.2,
                solid_capstyle="round", zorder=2)
        ax.plot([a], [y], marker="o", markersize=8, color=T["context"], zorder=3,
                markeredgecolor=T["paper"], markeredgewidth=1)
        ax.plot([b], [y], marker="o", markersize=8, color=T["accent"], zorder=3,
                markeredgecolor=T["paper"], markeredgewidth=1)
        d = b - a
        sign = "+" if d > 0 else ("−" if d < 0 else "±")
        ax.text(max(a, b) + span * 0.05, y, f"{sign}{fmt_num(abs(d))}", va="center",
                ha="left", fontsize=10.2, fontweight="bold", color=T["ink"], zorder=4)
    ax.set_yticks(ys)
    ax.set_yticklabels([_short(i.get("label")) for i in items])
    style_ylabels(ax, T)
    ax.set_xticks([])
    h = fig.get_size_inches()[1] * 100
    fig.text(1.0, 1.0 - (34.0 if chart.get("unit_meta") else 15.0) / h,
             f"● {chart.get('a_label') or 'A'}（灰）　● {chart.get('b_label') or 'B'}（强调）",
             ha="right", va="top", fontsize=8.8, color=T["muted"])
    return svg_of(fig)


# --------------------------------------------------------------------------- #
def grouped_bar(chart: Dict[str, Any], theme: str) -> str:
    cats = [str(c.get("label") if isinstance(c, dict) else c) for c in (chart.get("categories") or [])]
    series = [s for s in (chart.get("series") or []) if s.get("values")]
    n = max(len(cats), 1)
    m = max(len(series), 1)
    fig, ax, T = canvas(320, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""), pad_l=40, pad_b=72)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color=T["line"], linewidth=0.8)
    ax.set_axisbelow(True)
    vals = [float(v) for s in series for v in (s.get("values") or [])]
    vmax = max(vals) if vals else 1.0
    vmin = min(0.0, min(vals) if vals else 0.0)
    ax.set_ylim(vmin - (vmax - vmin) * 0.08, vmax * 1.22 if vmax else 1)
    ax.set_xlim(-0.62, n - 0.38)
    bw = 0.66 / m
    for j, s in enumerate(series):
        color = T["cat"][j % len(T["cat"])]
        xs = [i - 0.33 + bw * (j + 0.5) for i in range(n)]
        vs = [float(v) for v in (s.get("values") or [])][:n]
        ax.bar(xs, vs, width=bw * 0.86, color=color, edgecolor="none", zorder=3,
               label=str(s.get("name") or f"系列{j+1}"))
        if n * m <= 12:
            for x, v in zip(xs, vs):
                ax.text(x, v + (vmax - vmin) * 0.02, fmt_num(v), ha="center", va="bottom",
                        fontsize=8.4, color=T["muted"], zorder=4)
    ax.set_xticks(range(n))
    ax.set_xticklabels([_short(c, 9) for c in cats], fontsize=9.4, color=T["ink"])
    ax.tick_params(axis="x", length=0, pad=8, labelbottom=True)
    ax.set_yticks([])
    if m > 1:
        leg = ax.legend(loc="upper right", frameon=False, fontsize=8.8, ncol=m,
                        handlelength=0.9, columnspacing=1.1, handletextpad=0.4,
                        bbox_to_anchor=(1.0, 1.12))
        for t in leg.get_texts():
            t.set_color(T["muted"])
    return svg_of(fig)


# --------------------------------------------------------------------------- #
def stacked_bar(chart: Dict[str, Any], theme: str) -> str:
    cats = [str(c.get("label") if isinstance(c, dict) else c) for c in (chart.get("categories") or [])]
    segs = [s for s in (chart.get("segments") or []) if s.get("values")]
    n = max(len(cats), 1)
    fig, ax, T = canvas(320, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""), pad_l=40, pad_b=72)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color=T["line"], linewidth=0.8)
    ax.set_axisbelow(True)
    bottoms = [0.0] * n
    for j, seg in enumerate(segs):
        vs = [float(v) for v in (seg.get("values") or [])][:n]
        color = T["cat"][j % len(T["cat"])]
        ax.bar(range(n), vs, bottom=bottoms, width=0.44, color=color, edgecolor="none",
               zorder=3, label=str(seg.get("name") or f"段{j+1}"))
        bottoms = [b + v for b, v in zip(bottoms, vs)]
    ax.set_xlim(-0.62, n - 0.38)
    ax.set_ylim(0, max(bottoms or [1]) * 1.18)
    ax.set_xticks(range(n))
    ax.set_xticklabels([_short(c, 9) for c in cats], fontsize=9.4, color=T["ink"])
    ax.tick_params(axis="x", length=0, pad=8, labelbottom=True)
    ax.set_yticks([])
    for x, total in enumerate(bottoms):
        ax.text(x, total, fmt_num(total), ha="center", va="bottom", fontsize=9.6,
                fontweight="bold", color=T["ink"], zorder=4)
    if len(segs) > 1:
        leg = ax.legend(loc="upper right", frameon=False, fontsize=8.8, ncol=min(len(segs), 4),
                        handlelength=0.9, columnspacing=1.1, handletextpad=0.4,
                        bbox_to_anchor=(1.0, 1.12))
        for t in leg.get_texts():
            t.set_color(T["muted"])
    return svg_of(fig)

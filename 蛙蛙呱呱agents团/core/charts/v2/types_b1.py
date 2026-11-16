# -*- coding: utf-8 -*-
"""core.charts.v2.types_b1 —— 分布与关系类（8 型）。

覆盖：pct_stacked / histogram / box / violin / ridgeline / scatter / bubble / parallel。

工艺约束（与 types_b2 一致）：
- 六要素：结论式标题、口径副标题、直接标注、参考线、异常归因、来源+图注；
- 单一强调色 + 灰阶，语义色只表达好坏；不画图例框、不用 3D / 渐变；
- 颜色一律取主题令牌；数据不足返回 None，由上层回退 v1。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from matplotlib.patches import Polygon

from . import base as _base
from .base import canvas, fmt_num, style_ylabels, svg_of


# --------------------------------------------------------------------------- #
# 通用小工具
# --------------------------------------------------------------------------- #
def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _short(s: Any, n: int = 14) -> str:
    t = str(s if s is not None else "")
    return t if len(t) <= n else t[: max(n - 1, 1)] + "…"


def _clean(ax, T: Dict[str, Any]) -> None:
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.grid(False)


def _footer(fig, text: str, T: Dict[str, Any],
            color: Optional[str] = None) -> None:
    # 嵌入报告图卡时，口径/来源/图注由卡框统一给，图内不再重复底注
    if _base.EMBED:
        return
    h = fig.get_size_inches()[1] * 100.0
    fig.text(0.5, 15.0 / h, text, ha="center", va="bottom",
             fontsize=8.6, color=color or T["muted"])


def _pctl(values: List[float], p: float) -> float:
    """线性插值分位数（type-7），确定性。"""
    vs = sorted(values)
    if len(vs) == 1:
        return vs[0]
    k = (len(vs) - 1) * p
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return float(vs[int(k)])
    return float(vs[f] + (vs[c] - vs[f]) * (k - f))


def _density(values: List[float], bins: int = 22) -> List[Tuple[float, float]]:
    """等宽分箱 + 相邻平滑，返回 [(值, 归一密度)]，最大密度=1。"""
    lo, hi = min(values), max(values)
    if hi - lo < 1e-12:
        return [(lo, 1.0)] * bins
    bw = (hi - lo) / bins
    cnt = [0] * bins
    for v in values:
        cnt[min(bins - 1, int((v - lo) / bw))] += 1
    sm: List[float] = []
    for i in range(bins):
        left = cnt[i - 1] if i > 0 else cnt[0]
        right = cnt[i + 1] if i < bins - 1 else cnt[-1]
        sm.append((left + 2.0 * cnt[i] + right) / 4.0)
    mx = max(sm) or 1.0
    return [(lo + bw * (i + 0.5), sm[i] / mx) for i in range(bins)]


def _nice_ticks(lo: float, hi: float, n: int = 4) -> List[float]:
    return [lo + (hi - lo) * i / n for i in range(n + 1)]


# --------------------------------------------------------------------------- #
# viz-05 百分比堆叠条形图
# --------------------------------------------------------------------------- #
def pct_stacked(chart: Dict[str, Any], theme: str) -> Optional[str]:
    cats = [str(c) for c in (chart.get("categories") or [])]
    segs: List[Dict[str, Any]] = []
    for s in chart.get("segments") or []:
        vals = [_num(v) for v in (s.get("values") or [])]
        if any(v is None for v in vals) or len(vals) != len(cats):
            return None
        segs.append({"name": str(s.get("name") or ""), "values": vals,
                     "accent": bool(s.get("accent"))})
    # 允许单条 100% 堆叠（如「全部评价」的评分构成），只要段数够
    if len(cats) < 1 or len(segs) < 2:
        return None

    totals = [sum(s["values"][i] for s in segs) for i in range(len(cats))]
    if any(t <= 0 for t in totals):
        return None

    # 占比实算
    shares = [[s["values"][i] / totals[i] * 100.0 for i in range(len(cats))] for s in segs]
    top_cat = max(range(len(cats)), key=lambda i: max(shares[k][i] for k in range(len(segs))))
    top_seg = max(range(len(segs)), key=lambda k: shares[k][top_cat])
    top_val = shares[top_seg][top_cat]

    n = len(cats)
    fig, ax, T = canvas(390, theme, chart.get("title", ""), chart.get("unit_meta", "%"),
                        chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=64, pad_r=118, pad_b=86, pad_t=54)
    _clean(ax, T)
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(0, 104)

    for v in (0, 25, 50, 75, 100):
        ax.axhline(v, color=T["line"], linewidth=0.7, zorder=1)
        ax.text(-0.52, v, f"{v}%", ha="right", va="center", fontsize=8.2,
                color=T["muted"], clip_on=False)

    width = 0.52 if n <= 8 else 0.44
    tones = [T["context"], T["line_strong"], T["reference"], T["muted"]]
    for i, cat in enumerate(cats):
        bottom = 0.0
        for k, seg in enumerate(segs):
            p = shares[k][i]
            col = T["accent"] if (seg["accent"] or k == 0) else tones[min(k - 1, len(tones) - 1)]
            alpha = 0.95 if (seg["accent"] or k == 0) else 0.62 - 0.08 * min(k, 2)
            ax.bar(i, p, width=width, bottom=bottom, color=col, edgecolor="none",
                   alpha=alpha, zorder=3)
            if p >= 8:
                ax.text(i, bottom + p / 2, f"{p:.1f}%", ha="center", va="center",
                        fontsize=8.6, color=T["paper"] if k == 0 or seg["accent"] else T["ink"],
                        fontweight="bold" if seg["accent"] else "normal", zorder=6)
            bottom += p
        ax.text(i, -2.4, cat, ha="center", va="top", fontsize=9.4, color=T["ink"],
                clip_on=False)
        ax.text(i, -9.2, f"n={totals[i]:,.0f}", ha="center", va="top", fontsize=8.0,
                color=T["muted"], clip_on=False)

    ax.text(0.995, 0.985, f"占比最高：{_short(segs[top_seg]['name'], 10)} "
                          f"{top_val:.1f}%（{cats[top_cat]}）",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.4,
            color=T["accent"], zorder=6)

    ax.set_yticks([])
    ax.set_xticks([])
    _footer(fig, "各条由原始值实算占比（分母=该条合计，合计 100%）· 标注<8% 的段已省略",
            T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-10 直方图
# --------------------------------------------------------------------------- #
def histogram(chart: Dict[str, Any], theme: str) -> Optional[str]:
    raws = [_num(v) for v in (chart.get("values") or [])]
    vals = [v for v in raws if v is not None]
    if len(vals) < 8:
        return None
    n_bins = int(_num(chart.get("bins")) or 8)
    n_bins = max(4, min(14, n_bins))
    lo, hi = min(vals), max(vals)
    span = hi - lo
    if span < 1e-12:
        return None
    bw = span / n_bins
    counts = [0] * n_bins
    for v in vals:
        counts[min(n_bins - 1, int((v - lo) / bw))] += 1
    mean = sum(vals) / len(vals)
    med = _pctl(vals, 0.5)
    cmax = max(counts) or 1
    modal = max(range(n_bins), key=lambda i: counts[i])

    fig, ax, T = canvas(380, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=52, pad_r=58, pad_b=82, pad_t=58)
    _clean(ax, T)
    ax.set_xlim(lo, hi)
    ax.set_ylim(0, cmax * 1.24)

    for v in _nice_ticks(0, cmax * 1.24, 4):
        ax.axhline(v, color=T["line"], linewidth=0.7, zorder=1)
        ax.text(lo, v, f"{v:,.0f}", ha="right", va="center", fontsize=8.2,
                color=T["muted"], clip_on=False)

    for i, cnt in enumerate(counts):
        x0 = lo + bw * i
        col = T["accent"] if i == modal else T["context"]
        ax.bar(x0 + bw * 0.5, cnt, width=bw * 0.90, color=col,
               edgecolor="none", alpha=0.95 if i == modal else 0.62, zorder=3)
        if cnt:
            ax.text(x0 + bw * 0.5, cnt + cmax * 0.03, f"{cnt}", ha="center",
                    va="bottom", fontsize=8.6, color=T["ink"],
                    fontweight="bold" if i == modal else "normal", zorder=5)
    # 均值/中位两条线挨得近时，标签纵向错开，避免叠成一句
    near = abs(mean - med) <= span * 0.14
    for x, label, col, dash, ylab, ha in (
            (mean, f"均值 {fmt_num(mean, digits=1)}", T["accent"], (0, (4, 3)),
             cmax * 1.18, "left"),
            (med, f"中位 {fmt_num(med, digits=1)}", T["muted"], (0, (2, 2)),
             cmax * (1.02 if near else 1.18), "right" if near else "left")):
        ax.axvline(x, color=col, linewidth=1.1, linestyle=dash, zorder=4)
        ax.text(x, ylab, label, ha=ha, va="top", fontsize=8.2, color=col,
                clip_on=False)

    xt = _nice_ticks(lo, hi, 4)
    ax.set_xticks(xt)
    ax.set_xticklabels([fmt_num(v, digits=1) for v in xt], fontsize=8.2, color=T["muted"])
    ax.tick_params(axis="x", length=0, pad=6)
    ax.set_yticks([])

    ax.text(0.995, 0.985,
            f"峰值区间 {fmt_num(lo + bw * modal, digits=1)}–{fmt_num(lo + bw * (modal + 1), digits=1)}"
            f"（{counts[modal]} 个，占 {counts[modal] / len(vals):.0%}）",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.4, color=T["accent"],
            zorder=6)
    _footer(fig, f"等宽分箱（{n_bins} 箱）· 样本 n={len(vals):,} · 分位数线性插值", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-16 箱线图
# --------------------------------------------------------------------------- #
def box(chart: Dict[str, Any], theme: str) -> Optional[str]:
    groups: List[Dict[str, Any]] = []
    for g in chart.get("groups") or []:
        vals = [_num(v) for v in (g.get("values") or [])]
        vals = [v for v in vals if v is not None]
        if len(vals) < 3:
            continue
        groups.append({"label": str(g.get("label") or ""), "values": vals,
                       "accent": bool(g.get("accent"))})
    if len(groups) < 2:
        return None

    stats: List[Dict[str, Any]] = []
    iqrs: List[float] = []
    all_vals: List[float] = []
    for g in groups:
        q1, med, q3 = _pctl(g["values"], 0.25), _pctl(g["values"], 0.5), _pctl(g["values"], 0.75)
        iqr = q3 - q1
        iqrs.append(iqr)
        lo, hi = min(g["values"]), max(g["values"])
        whislo, whishi = q1, q3
        fliers: List[float] = []
        for v in sorted(g["values"]):
            if v < q1 - 1.5 * iqr:
                fliers.append(v)
            elif v > q3 + 1.5 * iqr:
                fliers.append(v)
        inner = [v for v in g["values"] if q1 - 1.5 * iqr <= v <= q3 + 1.5 * iqr]
        if inner:
            whislo, whishi = min(inner), max(inner)
        stats.append({"label": g["label"], "med": med, "q1": q1, "q3": q3,
                      "whislo": whislo, "whishi": whishi, "fliers": fliers})
        all_vals.extend(g["values"])

    n = len(groups)
    lo_all, hi_all = min(all_vals), max(all_vals)
    span = (hi_all - lo_all) or abs(hi_all) * 0.2 or 1.0
    xlo, xhi = lo_all - span * 0.10, hi_all + span * 0.10
    focus = max(range(n), key=lambda i: iqrs[i])
    overall_med = _pctl(all_vals, 0.5)

    fig, ax, T = canvas(96 + 52 * n, theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=120, pad_r=118, pad_b=62, pad_t=58)
    _clean(ax, T)
    ax.set_xlim(xlo, xhi)
    ax.set_ylim(0.3, n + 0.9)

    for v in _nice_ticks(xlo, xhi, 4):
        ax.axvline(v, color=T["line"], linewidth=0.7, zorder=1)
        ax.text(v, 0.36, fmt_num(v), ha="center", va="bottom", fontsize=8.2,
                color=T["muted"], clip_on=False)

    bxp = ax.bxp(stats, positions=list(range(n, 0, -1)), vert=False, widths=0.52,
                 patch_artist=True, showfliers=True, zorder=4,
                 medianprops=dict(color=T["paper"], linewidth=1.6),
                 whiskerprops=dict(color=T["context"], linewidth=1.0),
                 capprops=dict(color=T["context"], linewidth=1.0),
                 flierprops=dict(marker="o", markersize=3.0, markerfacecolor="none",
                                 markeredgecolor=T["reference"], markeredgewidth=0.8))
    for i, patch in enumerate(bxp["boxes"]):
        accent = groups[n - 1 - i]["accent"] if n else False
        patch.set_facecolor(T["accent"] if accent else T["context"])
        patch.set_edgecolor(T["accent"] if accent else T["reference"])
        patch.set_alpha(0.88 if accent else 0.45)
        patch.set_linewidth(0.9)

    ax.axvline(overall_med, color=T["reference"], linewidth=1.0, linestyle=(0, (4, 3)),
               zorder=2)
    ax.text(overall_med, n + 0.82, f"全体中位 {fmt_num(overall_med, digits=1)}",
            ha="center", va="top", fontsize=8.2, color=T["reference"], clip_on=False)

    ys = list(range(n, 0, -1))
    ax.set_yticks(ys)
    ax.set_yticklabels([_short(g["label"], 12) for g in groups])
    style_ylabels(ax, T, size=9.6)
    ax.set_xticks([])

    for i, g in enumerate(groups):
        y = n - i
        ax.text(xhi, y, f"中位 {fmt_num(stats[i]['med'], digits=1)}", ha="right",
                va="center", fontsize=8.4, color=T["accent"] if g["accent"] else T["muted"],
                clip_on=False)

    ax.annotate(f"离散最大：{_short(groups[focus]['label'], 10)}"
                f"（P75−P25={fmt_num(iqrs[focus], digits=1)}）",
                xy=(stats[focus]["q3"], n - focus),
                xytext=(xhi, n + 0.45), fontsize=8.4, color=T["accent"],
                ha="right", va="center", zorder=8,
                arrowprops=dict(arrowstyle="-", color=T["reference"], linewidth=0.7,
                                shrinkA=2, shrinkB=3, connectionstyle="arc3,rad=0.12"))
    _footer(fig, "箱体 P25–P75，须线 1.5 IQR，点为离群值 · 共享横轴尺度", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-21 小提琴图
# --------------------------------------------------------------------------- #
def violin(chart: Dict[str, Any], theme: str) -> Optional[str]:
    groups: List[Dict[str, Any]] = []
    for g in chart.get("groups") or []:
        vals = [_num(v) for v in (g.get("values") or [])]
        vals = [v for v in vals if v is not None]
        if len(vals) < 4:
            continue
        groups.append({"label": str(g.get("label") or ""), "sub": str(g.get("sub") or ""),
                       "values": vals, "accent": bool(g.get("accent"))})
    if len(groups) < 2:
        return None

    all_vals = [v for g in groups for v in g["values"]]
    lo, hi = min(all_vals), max(all_vals)
    span = (hi - lo) or abs(hi) * 0.2 or 1.0
    xlo, xhi = lo - span * 0.08, hi + span * 0.08
    n = len(groups)
    halfw = 0.34

    fig, ax, T = canvas(max(300, 96 + 86 * n), theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=130, pad_r=92, pad_b=68, pad_t=56)
    _clean(ax, T)
    ax.set_xlim(xlo, xhi)
    ax.set_ylim(0.26, n + 0.74)

    for v in _nice_ticks(xlo, xhi, 4):
        ax.axvline(v, color=T["line"], linewidth=0.7, zorder=1)
        ax.text(v, 0.30, fmt_num(v, digits=1), ha="center", va="bottom", fontsize=8.2,
                color=T["muted"], clip_on=False)

    widest = max(range(n), key=lambda i: _pctl(groups[i]["values"], 0.75)
                 - _pctl(groups[i]["values"], 0.25))
    for i, g in enumerate(groups):
        cy = n - i
        curve = _density(g["values"])
        vg_lo, vg_hi = curve[0][0], curve[-1][0]
        xs = [p[0] for p in curve]
        top = [cy + halfw * d for _, d in curve]
        bot = [cy - halfw * d for _, d in curve]
        col = T["accent"] if g["accent"] else T["context"]
        poly_pts = [(x, y) for x, y in zip(xs, top)] + [(x, y) for x, y in zip(reversed(xs), reversed(bot))]
        ax.add_patch(Polygon(poly_pts, closed=True, facecolor=col, edgecolor=col,
                             linewidth=1.1, alpha=0.30 if g["accent"] else 0.18, zorder=3))
        ax.plot(xs, top, color=col, linewidth=1.2, zorder=4)
        ax.plot(xs, bot, color=col, linewidth=1.2, zorder=4)
        med = _pctl(g["values"], 0.5)
        ax.plot([med, med], [cy - halfw * 0.78, cy + halfw * 0.78], color=T["ink"],
                linewidth=2.2, solid_capstyle="butt", zorder=5)
        ax.text(xlo, cy, _short(g["label"], 12), ha="right", va="center",
                fontsize=9.4, color=T["ink"], fontweight="bold" if g["accent"] else "normal",
                clip_on=False)
        ax.text(xhi, cy, f"n={len(g['values'])} · 中位 {fmt_num(med, digits=1)}",
                ha="right", va="center", fontsize=8.4,
                color=T["accent"] if g["accent"] else T["muted"], clip_on=False)

    ax.annotate(f"跨度最大：{_short(groups[widest]['label'], 10)}"
                f"（P25–P75 跨 {fmt_num(_pctl(groups[widest]['values'], 0.75) - _pctl(groups[widest]['values'], 0.25), digits=1)}）",
                xy=(_pctl(groups[widest]["values"], 0.75), n - widest),
                xytext=(xlo, n + 0.55), fontsize=8.4, color=T["accent"],
                ha="left", va="center", zorder=8,
                arrowprops=dict(arrowstyle="-", color=T["reference"], linewidth=0.7,
                                shrinkA=2, shrinkB=3, connectionstyle="arc3,rad=-0.12"))
    ax.set_yticks([])
    ax.set_xticks([])
    _footer(fig, "共享横轴 · 密度为等宽分箱频数平滑 · 竖线为中位数 · 样本少时不宜作分布解释", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-22 山脊图
# --------------------------------------------------------------------------- #
def ridgeline(chart: Dict[str, Any], theme: str) -> Optional[str]:
    groups: List[Dict[str, Any]] = []
    for g in chart.get("groups") or []:
        vals = [_num(v) for v in (g.get("values") or [])]
        vals = [v for v in vals if v is not None]
        if len(vals) < 4:
            continue
        groups.append({"label": str(g.get("label") or ""), "values": vals,
                       "accent": bool(g.get("accent"))})
    if len(groups) < 2:
        return None

    all_vals = [v for g in groups for v in g["values"]]
    lo, hi = min(all_vals), max(all_vals)
    span = (hi - lo) or abs(hi) * 0.2 or 1.0
    xlo, xhi = lo - span * 0.06, hi + span * 0.06
    n = len(groups)

    fig, ax, T = canvas(112 + 62 * n, theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=120, pad_r=64, pad_b=66, pad_t=62)
    _clean(ax, T)
    ax.set_xlim(xlo, xhi)
    ax.set_ylim(0, n + 1.35)

    for v in _nice_ticks(xlo, xhi, 4):
        ax.axvline(v, color=T["line"], linewidth=0.7, zorder=1)
        ax.text(v, 0.22, fmt_num(v, digits=1), ha="center", va="bottom", fontsize=8.2,
                color=T["muted"], clip_on=False)

    overall_med = _pctl(all_vals, 0.5)
    ax.axvline(overall_med, color=T["reference"], linewidth=1.0, linestyle=(0, (4, 3)),
               zorder=2)

    peak_labels: List[str] = []
    for i in range(n - 1, -1, -1):
        g = groups[i]
        base = n - i
        curve = _density(g["values"], bins=26)
        xs = [p[0] for p in curve]
        ys = [base + 0.86 * p[1] for p in curve]
        col = T["accent"] if g["accent"] else T["context"]
        ax.add_patch(Polygon([(x, y) for x, y in zip(xs, ys)] +
                             [(x, base) for x in reversed(xs)], closed=True,
                     facecolor=col, edgecolor=T["paper"], linewidth=0.9,
                     alpha=0.55 if g["accent"] else 0.28, zorder=3 + i))
        ax.plot(xs, ys, color=T["accent"] if g["accent"] else T["reference"],
                linewidth=1.5 if g["accent"] else 1.0, zorder=4 + i)
        # 两行标签间距按 0.20 单位给足（约 11px），否则组名会压住 n=
        ax.text(xlo, base + 0.30, _short(g["label"], 12), ha="right", va="center",
                fontsize=9.2, color=T["ink"], fontweight="bold" if g["accent"] else "normal",
                clip_on=False)
        ax.text(xlo, base + 0.08, f"n={len(g['values'])}", ha="right", va="center",
                fontsize=7.7, color=T["muted"], clip_on=False)
        peak_v = max(curve, key=lambda p: p[1])[0]
        if g["accent"]:
            ax.text(peak_v, base + 0.92, f"峰 {fmt_num(peak_v, digits=1)}", ha="center",
                    va="bottom", fontsize=8.6, color=T["accent"], fontweight="bold",
                    zorder=6 + i)
        peak_labels.append(f"{_short(g['label'], 8)} 峰 {fmt_num(peak_v, digits=1)}")

    ax.text(xhi, n + 1.24, f"全体中位 {fmt_num(overall_med, digits=1)}", ha="right",
            va="top", fontsize=8.2, color=T["reference"], clip_on=False)
    top_g = max(groups, key=lambda g: max(g["values"]))
    if not _base.EMBED:
        fig.text(1.0, 1.0 - 33.0 / (fig.get_size_inches()[1] * 100.0),
                 f"最高值：{_short(top_g['label'], 8)} {fmt_num(max(top_g['values']), digits=1)}",
                 ha="right", va="top", fontsize=8.4, color=T["accent"])
    ax.set_yticks([])
    ax.set_xticks([])
    _footer(fig, "所有组共享横轴 · 峰位按分箱中值标注 · 组序即给定顺序（自上而下）", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-17 散点图
# --------------------------------------------------------------------------- #
def scatter(chart: Dict[str, Any], theme: str) -> Optional[str]:
    pts: List[Dict[str, Any]] = []
    for p in chart.get("points") or []:
        x, y = _num(p.get("x")), _num(p.get("y"))
        if x is None or y is None:
            continue
        pts.append({"x": x, "y": y, "label": str(p.get("label") or ""),
                    "accent": bool(p.get("accent"))})
    if len(pts) < 3:
        return None

    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    if xmax - xmin < 1e-12 or ymax - ymin < 1e-12:
        return None
    padx = (xmax - xmin) * 0.08
    pady = (ymax - ymin) * 0.10
    xlo, xhi = xmin - padx, xmax + padx
    ylo, yhi = ymin - pady, ymax + pady

    n = len(pts)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    slope = sxy / sxx if sxx else 0.0
    r = sxy / math.sqrt(sxx * syy) if sxx and syy else 0.0
    intercept = my - slope * mx

    resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    dev = max(range(n), key=lambda i: abs(resid[i]))

    fig, ax, T = canvas(400, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=64, pad_r=96, pad_b=76, pad_t=60)
    _clean(ax, T)
    ax.set_xlim(xlo, xhi)
    ax.set_ylim(ylo, yhi)

    for v in _nice_ticks(ylo, yhi, 4):
        ax.axhline(v, color=T["line"], linewidth=0.7, zorder=1)
        ax.text(xlo, v, fmt_num(v, digits=1), ha="right", va="center", fontsize=8.2,
                color=T["muted"], clip_on=False)
    for v in _nice_ticks(xlo, xhi, 4):
        ax.axvline(v, color=T["line"], linewidth=0.7, zorder=1)
    ax.axhline(my, color=T["reference"], linewidth=0.9, linestyle=(0, (4, 3)), zorder=2)
    ax.text(xhi, my, f"均值 {fmt_num(my, digits=1)} ", ha="right", va="bottom",
            fontsize=8.0, color=T["reference"], zorder=5)

    if chart.get("trend", True) and sxx:
        ax.plot([xlo, xhi], [intercept + slope * xlo, intercept + slope * xhi],
                color=T["accent"], linewidth=1.6, zorder=4)

    for p in pts:
        col = T["accent"] if p["accent"] else T["context"]
        ax.scatter([p["x"]], [p["y"]], s=46 if p["accent"] else 26, color=col,
                   edgecolors=T["paper"], linewidths=0.9, alpha=0.95 if p["accent"] else 0.75,
                   zorder=5)
        if p["label"]:
            ax.annotate(_short(p["label"], 10), xy=(p["x"], p["y"]),
                        xytext=(6, 6), textcoords="offset points", fontsize=8.2,
                        color=T["ink"], zorder=7)

    dev_label = (_short(pts[dev]["label"], 10) if pts[dev]["label"]
                 else f"({fmt_num(xs[dev])}, {fmt_num(ys[dev])})")
    ax.annotate(f"偏离拟合最大：{dev_label}",
                xy=(xs[dev], ys[dev]), xytext=(28, -24),
                textcoords="offset points", fontsize=8.4, color=T["critical"],
                zorder=8,
                arrowprops=dict(arrowstyle="-", color=T["critical"], linewidth=0.7,
                                connectionstyle="arc3,rad=0.16"))

    xt = _nice_ticks(xlo, xhi, 4)
    ax.set_xticks(xt)
    ax.set_xticklabels([fmt_num(v, digits=1) for v in xt], fontsize=8.2, color=T["muted"])
    ax.tick_params(axis="x", length=0, pad=6)
    ax.set_yticks([])

    ax.text(0.995, 0.985, f"n={n} · r={r:.2f}", transform=ax.transAxes, ha="right",
            va="top", fontsize=8.4, color=T["muted"], zorder=6)
    ax.text(0.995, 0.012, str(chart.get("xlabel") or "x"), transform=ax.transAxes,
            ha="right", va="bottom", fontsize=8.4, color=T["muted"], zorder=6)
    _footer(fig, "趋势线为 OLS 拟合，相关系数不等于因果 · 剔除离群点前先核实口径", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-18 气泡图
# --------------------------------------------------------------------------- #
def bubble(chart: Dict[str, Any], theme: str) -> Optional[str]:
    pts: List[Dict[str, Any]] = []
    for p in chart.get("points") or []:
        x, y, s = _num(p.get("x")), _num(p.get("y")), _num(p.get("size"))
        if x is None or y is None or s is None or s <= 0:
            continue
        pts.append({"x": x, "y": y, "size": s, "label": str(p.get("label") or ""),
                    "accent": bool(p.get("accent"))})
    if len(pts) < 3:
        return None

    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    spanx = (xmax - xmin) or abs(xmax) * 0.2 or 1.0
    spany = (ymax - ymin) or abs(ymax) * 0.2 or 1.0
    xlo, xhi = xmin - spanx * 0.12, xmax + spanx * 0.12
    ylo, yhi = ymin - spany * 0.12, ymax + spany * 0.12
    smax = max(p["size"] for p in pts)
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    biggest = max(pts, key=lambda p: p["size"])

    fig, ax, T = canvas(410, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=64, pad_r=122, pad_b=74, pad_t=58)
    _clean(ax, T)
    ax.set_xlim(xlo, xhi)
    ax.set_ylim(ylo, yhi)

    ax.axhline(mean_y, color=T["line_strong"], linewidth=0.9, linestyle=(0, (4, 3)), zorder=2)
    ax.axvline(mean_x, color=T["line_strong"], linewidth=0.9, linestyle=(0, (4, 3)), zorder=2)

    for v in _nice_ticks(ylo, yhi, 4):
        ax.axhline(v, color=T["line"], linewidth=0.6, zorder=1)
        ax.text(xlo, v, fmt_num(v, digits=1), ha="right", va="center", fontsize=8.2,
                color=T["muted"], clip_on=False)

    for p in sorted(pts, key=lambda q: -q["size"]):
        rad = math.sqrt(p["size"] / smax) * 0.30
        col = T["accent"] if p["accent"] else T["context"]
        ax.add_patch(Polygon(_circle(p["x"], p["y"], rad, 40), closed=True,
                             facecolor=col, edgecolor=T["accent"] if p["accent"] else "none",
                             linewidth=1.0, alpha=0.55 if p["accent"] else 0.34, zorder=4))
        if p["label"]:
            ax.text(p["x"], p["y"] + rad + spany * 0.05, _short(p["label"], 8),
                    ha="center", va="bottom", fontsize=8.2,
                    color=T["ink"] if p["accent"] else T["muted"],
                    fontweight="bold" if p["accent"] else "normal", zorder=6)

    ax.annotate(f"最大气泡：{_short(biggest['label'] or '未命名', 10)}（{fmt_num(biggest['size'])}）",
                xy=(biggest["x"], biggest["y"]),
                xytext=(0.995, 0.10), textcoords="axes fraction", ha="right", va="bottom",
                fontsize=8.4, color=T["accent"], zorder=8,
                arrowprops=dict(arrowstyle="-", color=T["reference"], linewidth=0.7,
                               shrinkA=2, shrinkB=6, connectionstyle="arc3,rad=-0.15"))

    xt = _nice_ticks(xlo, xhi, 4)
    ax.set_xticks(xt)
    ax.set_xticklabels([fmt_num(v, digits=1) for v in xt], fontsize=8.2, color=T["muted"])
    ax.tick_params(axis="x", length=0, pad=6)
    ax.set_yticks([])
    ax.text(0.995, 0.985, "气泡面积∝规模 · 虚线为均值", transform=ax.transAxes,
            ha="right", va="top", fontsize=8.2, color=T["muted"], zorder=6)
    _footer(fig, "半径按 √ 映射（面积而非半径）· 象限以均值为界 · 大泡先画避免遮挡", T)
    return svg_of(fig)


def _circle(cx: float, cy: float, r: float, n: int) -> List[Tuple[float, float]]:
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
            for i in range(n)]


# --------------------------------------------------------------------------- #
# viz-23 平行坐标图
# --------------------------------------------------------------------------- #
def parallel(chart: Dict[str, Any], theme: str) -> Optional[str]:
    axes_names = [str(a) for a in (chart.get("axes") or [])]
    items: List[Dict[str, Any]] = []
    for it in chart.get("items") or []:
        vals = [_num(v) for v in (it.get("values") or [])]
        if any(v is None for v in vals) or len(vals) != len(axes_names):
            continue
        items.append({"name": str(it.get("name") or ""), "values": vals,
                      "accent": bool(it.get("accent"))})
    if len(axes_names) < 3 or len(items) < 2:
        return None

    norms: List[Tuple[float, float]] = []
    for ai in range(len(axes_names)):
        col_v = [it["values"][ai] for it in items]
        lo, hi = min(col_v), max(col_v)
        norms.append((lo, hi if hi > lo else lo + 1.0))

    n = len(axes_names)
    fig, ax, T = canvas(390, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=60, pad_r=110, pad_b=64, pad_t=72)
    _clean(ax, T)
    ax.set_xlim(-0.35, n - 1 + 0.75)
    ax.set_ylim(-0.02, 1.18)

    for ai, name in enumerate(axes_names):
        ax.axvline(ai, color=T["line_strong"], linewidth=1.0, zorder=1)
        ax.text(ai, 1.14, _short(name, 8), ha="center", va="bottom", fontsize=8.4,
                color=T["ink"], fontweight="bold", clip_on=False)
        lo, hi = norms[ai]
        ax.text(ai, 0.02, fmt_num(lo), ha="center", va="bottom", fontsize=7.5,
                color=T["muted"], clip_on=False)
        ax.text(ai, 0.94, fmt_num(hi), ha="center", va="top", fontsize=7.5,
                color=T["muted"], clip_on=False)

    def _vy(ai: int, v: float) -> float:
        lo, hi = norms[ai]
        return 0.10 + 0.78 * ((v - lo) / (hi - lo))

    regular = [it for it in items if not it["accent"]]
    accent = [it for it in items if it["accent"]]
    for it in regular:
        xs = list(range(n))
        ax.plot(xs, [_vy(i, v) for i, v in enumerate(it["values"])], color=T["context"],
                linewidth=1.0, alpha=0.30, zorder=2)
    for it in accent:
        ax.plot(list(range(n)), [_vy(i, v) for i, v in enumerate(it["values"])],
                color=T["accent"], linewidth=2.2, zorder=4)
        ax.text(n - 1 + 0.10, _vy(n - 1, it["values"][-1]), _short(it["name"], 10),
                ha="left", va="center", fontsize=8.6, color=T["accent"],
                fontweight="bold", clip_on=False)

    if not accent:
        best = max(items, key=lambda q: _vy(n - 1, q["values"][-1]))
        ax.text(n - 1 + 0.10, _vy(n - 1, best["values"][-1]), _short(best["name"], 10),
                ha="left", va="center", fontsize=8.6, color=T["accent"],
                fontweight="bold", clip_on=False)

    widest = max(range(n), key=lambda i: norms[i][1] - norms[i][0])
    if not _base.EMBED:
        # 放标题行右侧：原来贴左轴顶，会盖住第一个轴名
        fig.text(1.0, 1.0 - 33.0 / (fig.get_size_inches()[1] * 100.0),
                 f"差异最大轴：{_short(axes_names[widest], 8)}"
                 f"（{fmt_num(norms[widest][0])}–{fmt_num(norms[widest][1])}）",
                 ha="right", va="top", fontsize=8.2, color=T["accent"])
    ax.set_xticks([])
    ax.set_yticks([])
    _footer(fig, f"共 {len(items)} 条记录 · 灰色常规线弱化，仅重点路径加粗 · 轴顺序即分析依据", T)
    return svg_of(fig)

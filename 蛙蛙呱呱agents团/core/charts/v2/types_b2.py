# -*- coding: utf-8 -*-
"""core.charts.v2.types_b2 —— 不确定性、监控与目标类图表（9 型）。

本模块只负责“把已经合规的数据画对”：
- 每张图都有直接标注、参考线（均值/基线/目标/0 线/控制限/目标带/刻度圈），
  以及一处异常或重点归因；
- 颜色一律取主题令牌，没有十六进制字面量；白底、极细网格、单一强调色；
- 不用图例框，不画 3D / 渐变 / 阴影 / 彩虹色；
- 数据不满足契约时返回 None，由上层回退 v1，不画空白图。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from matplotlib.patches import Rectangle, Wedge

from . import base as _base
from .base import bare_axes, canvas, fmt_num, style_ylabels, svg_of

_ERR_TYPES = ("SD", "SE", "CI")


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


def _rng(lo: float, hi: float, frac: float = 0.10) -> float:
    """返回安全的数据跨度；全等时退回量级或 1，避免除零。"""
    span = hi - lo
    if span <= 1e-12:
        span = abs(hi) * 0.2 or 1.0
    return span


def _footer(fig, h: float, text: str, T: Dict[str, Any],
            color: Optional[str] = None) -> None:
    # 嵌入报告图卡时，底注由卡框统一给
    if _base.EMBED:
        return
    fig.text(0.5, 16.0 / h, text, ha="center", va="bottom",
             fontsize=8.6, color=color or T["muted"])


def _y_grid(ax, T: Dict[str, Any], lo: float, hi: float, n: int = 4) -> None:
    ticks = [lo + (hi - lo) * i / n for i in range(n + 1)]
    ax.set_yticks(ticks)
    ax.set_yticklabels([fmt_num(v) for v in ticks], fontsize=8.2)
    ax.tick_params(axis="y", length=0, labelleft=True, labelsize=8.2,
                   colors=T["muted"])
    ax.grid(axis="y", color=T["line"], linewidth=0.7)
    ax.set_axisbelow(True)


def _x_slice(n: int, cap: int) -> List[int]:
    step = max(1, int(math.ceil(n / float(cap))))
    return list(range(0, n, step))


# --------------------------------------------------------------------------- #
# viz-24 误差条图
# --------------------------------------------------------------------------- #
def error_bar(chart: Dict[str, Any], theme: str) -> Optional[str]:
    et = str(chart.get("err_type") or "").strip().upper()
    if et not in _ERR_TYPES:
        return None

    items: List[Dict[str, Any]] = []
    for it in chart.get("items") or []:
        v, e = _num(it.get("value")), _num(it.get("err"))
        if v is None or e is None or e < 0:
            return None
        items.append({"label": str(it.get("label") or ""), "value": v, "err": e})
    if len(items) < 2:
        return None

    n = len(items)
    vals = [it["value"] for it in items]
    mean_v = sum(vals) / n
    max_err = max(it["err"] for it in items)
    mean_err = sum(it["err"] for it in items) / n
    focus = max(items, key=lambda it: it["err"])

    lo = min([0.0] + [it["value"] - it["err"] for it in items])
    hi = max([0.0] + [it["value"] + it["err"] for it in items])
    span = _rng(lo, hi)

    fig, ax, T = canvas(400, theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""),
                        pad_l=52, pad_r=42, pad_b=62, pad_t=54)
    _clean(ax, T)
    ax.set_xlim(-0.62, n - 0.38)
    ax.set_ylim(lo - span * 0.08, hi + span * 0.24)
    ylo, yhi = lo - span * 0.08, hi + span * 0.24

    _y_grid(ax, T, ylo, yhi, 4)
    ax.axhline(0, color=T["line_strong"], linewidth=0.9, zorder=2)

    width = 0.50 if n <= 6 else 0.38
    cap = 0.11 if n <= 6 else 0.085
    for i, it in enumerate(items):
        v, e = it["value"], it["err"]
        col = T["accent"] if it is focus else T["context"]
        ax.bar(i, v, width=width, bottom=0, color=col, edgecolor="none",
               alpha=0.92, zorder=3)
        # 误差线 + 端帽
        ax.plot([i, i], [v - e, v + e], color=T["ink"], linewidth=1.15,
                solid_capstyle="butt", zorder=4)
        for yy in (v - e, v + e):
            ax.plot([i - cap, i + cap], [yy, yy], color=T["ink"],
                    linewidth=1.15, solid_capstyle="butt", zorder=4)
        ax.text(i, v + e + span * 0.025, f"{fmt_num(v)}±{fmt_num(e)}",
                ha="center", va="bottom", fontsize=9.0, fontweight="bold",
                color=T["ink"], zorder=5)

    # 全区均值参考线（右侧小标签）
    ax.axhline(mean_v, color=T["reference"], linewidth=0.95,
               linestyle=(0, (4, 3)), zorder=2)
    ax.text(n - 0.40, mean_v + span * 0.012, f"均值 {fmt_num(mean_v)}",
            ha="right", va="bottom", fontsize=8.4, color=T["reference"],
            zorder=5)

    ax.text(0.995, 0.985, f"误差口径：{et}（全图唯一）",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.5,
            color=T["muted"], zorder=6)
    focus_color = T["critical"] if max_err > mean_err * 1.5 else T["accent"]
    ax.text(0.005, 0.985,
            f"波动最大：{_short(focus['label'], 10)}（±{fmt_num(max_err)}）",
            transform=ax.transAxes, ha="left", va="top", fontsize=8.4,
            color=focus_color, zorder=6)

    ax.set_xticks(range(n))
    ax.set_xticklabels([_short(it["label"], 8) for it in items],
                       fontsize=8.8 if n > 6 else 9.2, color=T["ink"])
    ax.tick_params(axis="x", length=0, pad=7, labelbottom=True)

    h = fig.get_size_inches()[1] * 100.0
    _footer(fig, h, "区间重叠不等于显著（需检验）", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-25 森林图
# --------------------------------------------------------------------------- #
def forest(chart: Dict[str, Any], theme: str) -> Optional[str]:
    items: List[Dict[str, Any]] = []
    for it in chart.get("items") or []:
        est, lo, hi = (_num(it.get("est")), _num(it.get("lo")), _num(it.get("hi")))
        if est is None or lo is None or hi is None or lo > hi:
            continue
        items.append({"label": str(it.get("label") or ""), "est": est,
                      "lo": lo, "hi": hi, "accent": bool(it.get("accent"))})
    if not items:
        return None

    baseline = _num(chart.get("baseline"))
    if baseline is None:
        baseline = 0.0
    ci_level = str(chart.get("ci_level") or "95% CI")
    n = len(items)
    h = 92.0 + 46.0 * n

    fig, ax, T = canvas(h, theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""),
                        pad_l=300, pad_r=300, pad_b=52, pad_t=62)
    _clean(ax, T)

    allv = [baseline] + [v for it in items for v in (it["lo"], it["hi"], it["est"])]
    lo_v, hi_v = min(allv), max(allv)
    span = _rng(lo_v, hi_v)
    xlo, xhi = lo_v - span * 0.10, hi_v + span * 0.10
    ax.set_xlim(xlo, xhi)
    ax.set_ylim(-0.62, n - 0.26)

    ticks = [xlo + (xhi - xlo) * i / 4 for i in range(5)]
    ax.set_xticks(ticks)
    ax.set_xticklabels([fmt_num(v, digits=2) for v in ticks], fontsize=8.2,
                       color=T["muted"])
    ax.tick_params(axis="x", length=0, pad=8, labelbottom=True, colors=T["muted"])
    ax.grid(axis="x", color=T["line"], linewidth=0.7)
    ax.set_axisbelow(True)

    ax.axvline(baseline, color=T["watch"], linewidth=1.1,
               linestyle=(0, (5, 4)), zorder=2)
    xb = baseline
    ha = "left" if xb < xlo + span * 0.12 else (
        "right" if xb > xhi - span * 0.12 else "center")
    ax.text(xb, n - 0.34, f"无效应基线 {fmt_num(baseline)}", ha=ha,
            va="bottom", fontsize=8.6, fontweight="bold", color=T["watch"],
            clip_on=False, zorder=5)
    ax.text(0.995, 0.99, ci_level, transform=ax.transAxes, ha="right",
            va="top", fontsize=8.5, color=T["muted"], zorder=6)
    hi_item = max(items, key=lambda it: float(it["est"]))
    if not _base.EMBED:
        fig.text(1.0, 1.0 - 33.0 / (fig.get_size_inches()[1] * 100.0),
                 f"最高效应：{_short(hi_item.get('label'), 8)} "
                 f"{'+' if float(hi_item['est']) >= 0 else '−'}"
                 f"{fmt_num(abs(float(hi_item['est'])))}",
                 ha="right", va="top", fontsize=8.4, color=T["accent"])

    ys = [float(n - 1 - i) for i in range(n)]
    crossing: List[str] = []
    eps = max(abs(baseline) * 1e-6, 1e-9)
    for y, it in zip(ys, items):
        sig = it["lo"] > baseline + eps or it["hi"] < baseline - eps
        if not sig:
            crossing.append(_short(it["label"], 8))
        col = T["accent"] if (sig or it["accent"]) else T["context"]
        ax.plot([it["lo"], it["hi"]], [y, y], color=col,
                linewidth=1.7, solid_capstyle="butt", zorder=3)
        for xx in (it["lo"], it["hi"]):
            ax.plot([xx, xx], [y - 0.16, y + 0.16], color=col,
                    linewidth=1.7, solid_capstyle="butt", zorder=3)
        ax.plot([it["est"]], [y], marker="s",
                markersize=6.4 if sig else 5.2,
                color=col, markeredgecolor=T["paper"], markeredgewidth=1.0,
                zorder=4)
        ax.text(xhi + span * 0.02, y,
                f"{fmt_num(it['est'], digits=2)} [{fmt_num(it['lo'], digits=2)}, "
                f"{fmt_num(it['hi'], digits=2)}]",
                ha="left", va="center", fontsize=8.6,
                fontweight="bold" if sig else "normal",
                color=T["ink"] if sig else T["muted"],
                clip_on=False, zorder=5)

    ax.set_yticks(ys)
    ax.set_yticklabels([_short(it["label"], 20) for it in items])
    style_ylabels(ax, T, size=9.4)
    ax.set_xticks(ticks)
    ax.set_xticklabels([fmt_num(v, digits=2) for v in ticks], fontsize=8.2,
                       color=T["muted"])
    ax.tick_params(axis="x", length=0, pad=8, labelbottom=True)

    widths = [it["hi"] - it["lo"] for it in items]
    widest = items[widths.index(max(widths))]
    if crossing:
        focus = "跨基线（不显著）：" + "、".join(crossing[:3])
    else:
        focus = f"最宽 CI：{_short(widest['label'], 10)}（{fmt_num(max(widths), digits=2)}）"
    h_px = fig.get_size_inches()[1] * 100.0
    _footer(fig, h_px, f"{focus} · 跨基线=不显著 · 关联非因果", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-26 控制图
# --------------------------------------------------------------------------- #
def control(chart: Dict[str, Any], theme: str) -> Optional[str]:
    series = chart.get("series") or []
    if not series:
        return None
    s = series[0]
    vals: List[float] = []
    for v in s.get("values") or []:
        f = _num(v)
        if f is None:
            return None
        vals.append(f)
    xl = [str(x) for x in chart.get("xlabels") or []]
    center = _num(chart.get("center"))
    band = _num(chart.get("band"))
    if center is None or band is None or band <= 0:
        return None
    if len(vals) < 3 or len(vals) != len(xl):
        return None

    ucl, lcl = center + band, center - band
    n = len(vals)
    lo = min([lcl] + vals)
    hi = max([ucl] + vals)
    span = _rng(lo, hi)

    fig, ax, T = canvas(340, theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""),
                        pad_l=58, pad_r=98, pad_b=64, pad_t=56)
    _clean(ax, T)
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(lo - span * 0.14, hi + span * 0.18)
    ylo, yhi = lo - span * 0.14, hi + span * 0.18

    # 控制带（正常波动区）
    ax.add_patch(Rectangle((-0.5, lcl), n, ucl - lcl,
                           facecolor=T["surface"], edgecolor="none", zorder=1))
    _y_grid(ax, T, ylo, yhi, 4)

    for val, lab, col, dash in ((ucl, f"UCL {fmt_num(ucl)}", T["watch"], (0, (5, 4))),
                                (center, f"均值 {fmt_num(center)}", T["muted"], None),
                                (lcl, f"LCL {fmt_num(lcl)}", T["watch"], (0, (5, 4)))):
        ax.axhline(val, color=col, linewidth=1.0,
                   linestyle=dash if dash else "solid", zorder=3)
        ax.annotate(lab, xy=(n - 1, val), xytext=(10, 0),
                    textcoords="offset points", ha="left", va="center",
                    fontsize=8.3, color=col, annotation_clip=False, zorder=6)

    ax.plot(range(n), vals, color=T["accent"], linewidth=1.8,
            solid_capstyle="round", zorder=4)
    ax.plot(range(n), vals, "o", markersize=3.2, color=T["accent"],
            markeredgecolor=T["paper"], markeredgewidth=0.8, zorder=5)

    ooc_x: List[int] = []
    for i, v in enumerate(vals):
        if v > ucl + 1e-9 or v < lcl - 1e-9:
            ooc_x.append(i)
            ax.plot([i], [v], marker="D", markersize=6.8,
                    color=T["critical"], markeredgecolor=T["paper"],
                    markeredgewidth=1.0, zorder=7)
            up = v > ucl
            ax.annotate(f"{fmt_num(v)}（越限）", xy=(i, v),
                        xytext=(0, 12 if up else -14),
                        textcoords="offset points", ha="center",
                        va="bottom" if up else "top", fontsize=8.2,
                        fontweight="bold", color=T["critical"],
                        clip_on=False, zorder=8)

    name = str(s.get("name") or "监测值")
    ax.text(0.005, 0.985, f"● {name}（末值 {fmt_num(vals[-1])}）",
            transform=ax.transAxes, ha="left", va="top", fontsize=8.6,
            fontweight="bold", color=T["accent"], zorder=6)

    idx = _x_slice(n, 12)
    ax.set_xticks(idx)
    ax.set_xticklabels([_short(xl[i], 7) for i in idx], fontsize=8.4,
                       color=T["muted"])
    ax.tick_params(axis="x", length=0, pad=7, labelbottom=True)

    anns = chart.get("annotations")
    ann = ""
    if isinstance(anns, str):
        ann = anns
    elif isinstance(anns, (list, tuple)) and anns:
        ann = str(anns[0])
    if ann:
        note = f"越限归因：{ann}"
    elif ooc_x:
        note = (f"越限归因：{len(ooc_x)} 点越限，首现 {_short(xl[ooc_x[0]], 7)}"
                f"（{fmt_num(vals[ooc_x[0]])}），先核查口径/事件")
    else:
        note = f"越限归因：无越限点，过程落在 {fmt_num(center)}±{fmt_num(band)} 内"
    h_px = fig.get_size_inches()[1] * 100.0
    _footer(fig, h_px, note, T, color=T["critical"] if ooc_x and not ann else T["muted"])
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-29 漏斗图
# --------------------------------------------------------------------------- #
def funnel(chart: Dict[str, Any], theme: str) -> Optional[str]:
    stages: List[Dict[str, Any]] = []
    for s in chart.get("stages") or []:
        v = _num(s.get("value"))
        if v is None or v < 0:
            return None
        stages.append({"label": str(s.get("label") or ""), "value": v})
    if len(stages) < 2:
        return None
    if any(stages[i - 1]["value"] <= 0 for i in range(1, len(stages))):
        return None

    n = len(stages)
    h = 110.0 + 54.0 * n
    fig, ax, T = canvas(h, theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""),
                        pad_l=230, pad_r=230, pad_b=44, pad_t=56)
    bare_axes(ax, T)
    ax.set_xlim(-1.0, 1.0)
    ax.set_ylim(-0.55, n - 0.35)

    # 中轴参考线
    ax.plot([0, 0], [-0.55, n - 0.35], color=T["line_strong"], linewidth=0.7,
            linestyle=(0, (3, 4)), zorder=1)

    vmax = max(s["value"] for s in stages) or 1.0
    half = [0.92 * s["value"] / vmax for s in stages]
    conv = [None] + [stages[i]["value"] / stages[i - 1]["value"] * 100.0
                     for i in range(1, n)]
    drops = [None] + [100.0 - conv[i] for i in range(1, n)]
    valid_drops = [(drops[i], i) for i in range(1, n)]
    worst = max(valid_drops)[1] if valid_drops and max(valid_drops)[0] > 0 else -1

    for i, s in enumerate(stages):
        yc = float(n - 1 - i)
        hw = max(half[i], 0.16)
        if i > 0:
            hp = max(half[i - 1], 0.16)
            is_worst = (i - 1) == worst
            ax.fill([-hp, hp, hw, -hw],
                    [yc + 0.70, yc + 0.70, yc + 0.30, yc + 0.30],
                    color=T["critical"] if is_worst else T["line"],
                    alpha=0.18 if is_worst else 0.75, linewidth=0, zorder=2)
        col = T["accent"] if i == 0 else T["context"]
        ax.add_patch(Rectangle((-hw, yc - 0.30), 2 * hw, 0.60,
                               facecolor=col, edgecolor="none", alpha=0.92,
                               zorder=3))
        tc = T["paper"] if i == 0 else T["ink"]
        if hw < 0.30:
            ax.text(0, yc + 0.06, _short(s["label"], 10), ha="center",
                    va="bottom", fontsize=8.8, fontweight="bold", color=tc,
                    zorder=4)
            ax.text(0, yc - 0.07, fmt_num(s["value"]), ha="center",
                    va="top", fontsize=8.6, color=tc, zorder=4)
        else:
            ax.text(0, yc, f"{_short(s['label'], 12)}  {fmt_num(s['value'])}",
                    ha="center", va="center", fontsize=9.2, fontweight="bold",
                    color=tc, zorder=4)

        if i > 0:
            is_worst = (i - 1) == worst
            ax.text(1.04, yc, f"转化 {conv[i]:.1f}%\n流失 {drops[i]:.1f}%",
                    ha="left", va="center", fontsize=8.3,
                    fontweight="bold" if is_worst else "normal",
                    color=T["critical"] if is_worst else T["muted"],
                    linespacing=1.35, clip_on=False, zorder=5)

    if worst >= 0:
        focus = (f"最大流失：{_short(stages[worst]['label'], 9)}→"
                 f"{_short(stages[worst + 1]['label'], 9)}（{drops[worst]:.1f}%）"
                 " · 优先排查该环节交接/口径")
        fcol = T["critical"]
    else:
        focus = "各级均无流失 · 转化率以相邻上一级为分母"
        fcol = T["muted"]
    h_px = fig.get_size_inches()[1] * 100.0
    _footer(fig, h_px, focus, T, color=fcol)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-30 子弹图
# --------------------------------------------------------------------------- #
def bullet(chart: Dict[str, Any], theme: str) -> Optional[str]:
    value, target = _num(chart.get("value")), _num(chart.get("target"))
    if value is None or target is None or value < 0 or target < 0:
        return None
    bands: List[Dict[str, Any]] = []
    for b in chart.get("bands") or []:
        to = _num(b.get("to"))
        if to is None or to < 0:
            return None
        bands.append({"to": to, "label": str(b.get("label") or "")})
    if bands:
        bands = sorted(bands, key=lambda b: b["to"])
    last_to = bands[-1]["to"] if bands else 0.0
    hi = max(value, target, last_to)
    if hi <= 0:
        return None
    xmax = hi * 1.28

    label = str(chart.get("label") or "指标")
    unit = str(chart.get("unit") or "")
    src = str(chart.get("target_source") or "未注明")

    fig, ax, T = canvas(220, theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""),
                        pad_l=44, pad_r=44, pad_b=36, pad_t=54)
    _clean(ax, T)
    ax.set_xlim(0, xmax)
    ax.set_ylim(-0.28, 1.04)

    px_per_unit = 820.0 / xmax
    prev = 0.0
    for k, b in enumerate(bands):
        w = b["to"] - prev
        if w < 0:
            return None
        ax.add_patch(Rectangle((prev, 0.38), w, 0.44,
                               facecolor=T["accent"], alpha=0.08 + 0.06 * k,
                               edgecolor="none", zorder=1))
        if w * px_per_unit > 74:
            ax.text((prev + b["to"]) / 2.0, 0.355, f"{b['label']}≤{fmt_num(b['to'])}",
                    ha="center", va="top", fontsize=8.0, color=T["muted"],
                    zorder=2)
        prev = b["to"]

    ax.axhline(0.24, color=T["line"], linewidth=0.8, zorder=1)
    ax.axvline(0, color=T["line_strong"], linewidth=0.9, zorder=2)
    ax.add_patch(Rectangle((0, 0.49), value, 0.18, facecolor=T["accent"],
                           edgecolor="none", alpha=0.94, zorder=4))

    ax.axvline(target, ymin=0.44, ymax=0.76, color=T["critical"],
               linewidth=2.2, zorder=10)
    ax.text(target, 0.865, f"目标 {fmt_num(target)}", ha="center", va="bottom",
            fontsize=8.9, fontweight="bold", color=T["critical"], zorder=11)

    achieved = (value / target * 100.0) if target else 0.0
    tx = value + xmax * 0.012
    ha = "left" if tx < xmax * 0.97 else "right"
    ax.text(tx, 0.58, f"实际 {fmt_num(value)}{unit}（{achieved:.1f}% 达成）",
            ha=ha, va="center", fontsize=9.4, fontweight="bold",
            color=T["ink"], zorder=6)

    ax.text(0, 0.965, label, ha="left", va="top", fontsize=11.0,
            fontweight="bold", color=T["ink"])
    diff = value - target
    state = "达标" if diff >= 0 else "未达标"
    st = (f"{state}：超 +{fmt_num(abs(diff))}{unit}" if diff >= 0
          else f"{state}：缺 −{fmt_num(abs(diff))}{unit}")
    ax.text(1.0, 0.965, st, transform=ax.transAxes, ha="right", va="top",
            fontsize=8.8, fontweight="bold",
            color=T["healthy"] if diff >= 0 else T["critical"])

    ax.set_xticks([])
    ax.set_yticks([])
    h_px = fig.get_size_inches()[1] * 100.0
    _footer(fig, h_px, f"目标来源：{src} · 背景=绩效区间（由浅到深）· 不展示时间趋势", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-31 半圆仪表盘
# --------------------------------------------------------------------------- #
def gauge(chart: Dict[str, Any], theme: str) -> Optional[str]:
    value = _num(chart.get("value"))
    vmin = _num(chart.get("min"))
    vmax = _num(chart.get("max"))
    target = _num(chart.get("target"))
    if value is None:
        return None
    vmin = 0.0 if vmin is None else vmin
    vmax = 100.0 if vmax is None else vmax
    if vmax <= vmin or value < vmin or value > vmax:
        return None
    if target is not None and (target < vmin or target > vmax):
        return None
    unit = str(chart.get("unit") or "")

    fig, ax, T = canvas(430, theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""),
                        pad_l=10, pad_r=10, pad_b=52, pad_t=54)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_xlim(-1.52, 1.52)
    ax.set_ylim(-0.62, 1.55)

    frac = (value - vmin) / (vmax - vmin)

    def ang(v: float) -> float:
        return math.radians(180.0 - 180.0 * (v - vmin) / (vmax - vmin))

    def pt(v: float, r: float):
        a = ang(v)
        return r * math.cos(a), r * math.sin(a)

    # 底轨与值弧（上半圆：左=min，右=max）
    ax.add_patch(Wedge((0, 0), 1.0, theta1=0, theta2=180, width=0.28,
                       facecolor=T["surface"], edgecolor=T["paper"],
                       linewidth=0.8, zorder=1))
    if target is None:
        arc_col, state = T["accent"], "未设目标"
    else:
        arc_col = T["healthy"] if value >= target else T["watch"]
        state = "达标" if value >= target else "未达标"
    if frac > 0:
        ax.add_patch(Wedge((0, 0), 1.0, theta1=180.0 - 180.0 * frac,
                           theta2=180, width=0.28, facecolor=arc_col,
                           edgecolor="none", zorder=2))

    # 5 档刻度与刻度值
    for k in range(5):
        v = vmin + (vmax - vmin) * k / 4.0
        a = ang(v)
        ax.plot([1.02 * math.cos(a), 1.09 * math.cos(a)],
                [1.02 * math.sin(a), 1.09 * math.sin(a)],
                color=T["line_strong"], linewidth=0.9, zorder=3)
        lx, ly = pt(v, 1.17)
        ax.text(lx, ly, fmt_num(v), ha="center", va="center", fontsize=8.2,
                color=T["muted"], zorder=4)

    # 目标刻度（critical 竖线 + 文字）
    if target is not None:
        a = ang(target)
        ax.plot([1.00 * math.cos(a), 1.11 * math.cos(a)],
                [1.00 * math.sin(a), 1.11 * math.sin(a)],
                color=T["critical"], linewidth=1.8, zorder=5)
        lx, ly = pt(target, 1.30)
        ax.text(lx, ly, f"目标 {fmt_num(target)}", ha="center", va="center",
                fontsize=8.6, fontweight="bold", color=T["critical"], zorder=6)

    # 中心大数字 + 单位
    ax.text(0, 0.24, fmt_num(value), ha="center", va="center", fontsize=30.0,
            fontweight="bold", color=T["ink"], zorder=7)
    ax.text(0, 0.06, unit or "—", ha="center", va="center", fontsize=10.0,
            color=T["muted"], zorder=7)

    # 距目标差 + 文字状态（颜色不是唯一状态表达）
    if target is not None:
        d = value - target
        sign = "+" if d >= 0 else "−"
        line = (f"距目标 {sign}{fmt_num(abs(d))}{unit} / "
                f"文字状态：{state}")
        s_col = T["healthy"] if d >= 0 else T["watch"]
    else:
        line = f"未设目标 / 文字状态：按区间读取"
        s_col = T["muted"]
    ax.text(0, -0.29, line, ha="center", va="center", fontsize=9.2,
            fontweight="bold", color=s_col, zorder=7)
    ax.text(0, -0.46, f"范围 {fmt_num(vmin)}~{fmt_num(vmax)}{unit} · 目标刻度见红线",
            ha="center", va="center", fontsize=8.3, color=T["muted"], zorder=7)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-44 目标带柱线图
# --------------------------------------------------------------------------- #
def target_band(chart: Dict[str, Any], theme: str) -> Optional[str]:
    xl = [str(x) for x in chart.get("xlabels") or []]
    series = chart.get("series") or []
    if not series or len(xl) < 2:
        return None
    vals: List[float] = []
    for v in series[0].get("values") or []:
        f = _num(v)
        if f is None:
            return None
        vals.append(f)
    if len(vals) != len(xl):
        return None
    band = chart.get("band") or {}
    blo, bhi = _num(band.get("lo")), _num(band.get("hi"))
    if blo is None or bhi is None or bhi < blo:
        return None
    blabel = str(band.get("label") or "目标区间")

    n = len(vals)
    lo = min([0.0, blo] + vals)
    hi = max([bhi] + vals)
    span = _rng(lo, hi)

    fig, ax, T = canvas(360, theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""),
                        pad_l=48, pad_r=48, pad_b=70, pad_t=54)
    _clean(ax, T)
    ax.set_xlim(-0.62, n - 0.38)
    ax.set_ylim(lo - span * 0.10, hi + span * 0.20)
    ylo, yhi = lo - span * 0.10, hi + span * 0.20

    _y_grid(ax, T, ylo, yhi, 4)
    if lo <= 0 <= yhi:
        ax.axhline(0, color=T["line_strong"], linewidth=0.9, zorder=2)

    # 目标带先画：在柱、标注之下，不遮挡
    ax.add_patch(Rectangle((-0.62, blo), n, max(bhi - blo, 1e-9),
                           facecolor=T["watch"], alpha=0.13,
                           edgecolor="none", zorder=1))
    for edge, lab in ((bhi, "上沿"), (blo, "下沿")):
        ax.axhline(edge, color=T["watch"], linewidth=0.9,
                   linestyle=(0, (4, 3)), zorder=2)
    ax.text(0.995, 0.985, f"目标带 {blabel}：{fmt_num(blo)}~{fmt_num(bhi)}",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.5,
            fontweight="bold", color=T["watch"], zorder=6)

    width = 0.54 if n <= 8 else 0.42
    outside: List[int] = []
    for i, v in enumerate(vals):
        in_band = blo <= v <= bhi
        if not in_band:
            outside.append(i)
        ax.bar(i, v, width=width, bottom=0,
               color=T["accent"] if not in_band else T["context"],
               edgecolor="none", alpha=0.94 if not in_band else 0.72, zorder=3)
        ax.text(i, v + span * 0.024, fmt_num(v), ha="center", va="bottom",
                fontsize=8.5, fontweight="bold" if not in_band else "normal",
                color=T["ink"], zorder=4)

    if outside:
        k = max(outside, key=lambda i: max(blo - vals[i], vals[i] - bhi))
        dev = max(blo - vals[k], vals[k] - bhi)
        ax.annotate(f"最大偏离 +{fmt_num(dev)}", xy=(k, vals[k]),
                    xytext=(0, 17), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8.2, fontweight="bold",
                    color=T["critical"], zorder=6)
    else:
        k = max(range(n), key=lambda i: vals[i])
        ax.annotate(f"峰值 {fmt_num(vals[k])}", xy=(k, vals[k]),
                    xytext=(0, 17), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8.2, fontweight="bold",
                    color=T["accent"], zorder=6)

    ax.set_xticks(range(n))
    ax.set_xticklabels([_short(x, 7) for x in xl],
                       fontsize=8.4 if n > 8 else 9.0, color=T["ink"])
    ax.tick_params(axis="x", length=0, pad=8, labelbottom=True)

    word = "个月" if chart.get("monthly") or str(chart.get("period") or "") in ("month", "月") else "项"
    h_px = fig.get_size_inches()[1] * 100.0
    _footer(fig, h_px,
            f"超出带 {len(outside)} {word}（{len(outside) / n * 100.0:.1f}%）"
            " · 目标带=范围而非阈值 · 超出项用强调色", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-46 双轴柱线图
# --------------------------------------------------------------------------- #
def dual_axis(chart: Dict[str, Any], theme: str) -> Optional[str]:
    xl = [str(x) for x in chart.get("xlabels") or []]
    bars = chart.get("bars") or {}
    line = chart.get("line") or {}
    bvals: List[float] = []
    lvals: List[float] = []
    for v in bars.get("values") or []:
        f = _num(v)
        if f is None:
            return None
        bvals.append(f)
    for v in line.get("values") or []:
        f = _num(v)
        if f is None:
            return None
        lvals.append(f)
    if len(xl) < 2 or len(bvals) != len(xl) or len(lvals) != len(xl):
        return None
    if min(bvals) < 0:
        return None

    n = len(xl)
    bmax = max(max(bvals), 0.0) * 1.16 or 1.0
    lmin_, lmax_ = min(lvals), max(lvals)
    lspan = _rng(lmin_, lmax_)
    llo, lhi = lmin_ - lspan * 0.14, lmax_ + lspan * 0.14

    fig, ax, T = canvas(400, theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""),
                        pad_l=72, pad_r=104, pad_b=68, pad_t=64)
    _clean(ax, T)
    ax.set_xlim(-0.55, n - 0.45)
    ax.set_ylim(0, bmax)

    bt = [bmax * i / 4.0 for i in range(5)]
    ax.set_yticks(bt)
    ax.set_yticklabels([fmt_num(v) for v in bt], fontsize=8.3)
    ax.tick_params(axis="y", length=0, labelleft=True, labelsize=8.3,
                   colors=T["muted"])
    ax.grid(axis="y", color=T["line"], linewidth=0.7)
    ax.set_axisbelow(True)
    ax.axhline(0, color=T["line_strong"], linewidth=0.9, linestyle=(0, (4, 3)), zorder=3)

    width = 0.52
    for i, v in enumerate(bvals):
        ax.bar(i, v, width=width, bottom=0, color=T["context"], edgecolor="none",
               alpha=0.80, zorder=2)
        if n <= 10:
            ax.text(i, v + bmax * 0.025, fmt_num(v), ha="center", va="bottom",
                    fontsize=8.0, color=T["muted"], zorder=4)

    ax2 = ax.twinx()
    ax2.set_xlim(-0.55, n - 0.45)
    ax2.set_ylim(llo, lhi)
    lt = [llo + (lhi - llo) * i / 4.0 for i in range(5)]
    ax2.set_yticks(lt)
    ax2.set_yticklabels([fmt_num(v) for v in lt], fontsize=8.3)
    ax2.tick_params(axis="y", length=0, labelright=True, labelsize=8.3,
                    colors=T["accent"])
    for side in ("top", "right", "left", "bottom"):
        ax2.spines[side].set_visible(False)
    ax2.grid(False)

    ax2.plot(range(n), lvals, color=T["accent"], linewidth=1.9,
             marker="o", markersize=3.4, markeredgecolor=T["paper"],
             markeredgewidth=0.8, solid_capstyle="round", zorder=6)
    ax2.annotate(f"{fmt_num(lvals[-1])}{line.get('unit') or ''}",
                 xy=(n - 1, lvals[-1]), xytext=(8, 0),
                 textcoords="offset points", ha="left", va="center",
                 fontsize=8.6, fontweight="bold", color=T["accent"],
                 annotation_clip=False, zorder=7)

    pk = max(range(n), key=lambda i: lvals[i])
    if pk == n - 1:
        ax2.annotate(f"峰值 {_short(xl[pk], 6)}（{fmt_num(lvals[pk])}）",
                     xy=(pk, lvals[pk]), xytext=(-6, 12),
                     textcoords="offset points", ha="right", va="bottom",
                     fontsize=8.2, fontweight="bold", color=T["ink"],
                     zorder=7)
    else:
        ax2.annotate(f"峰值 {_short(xl[pk], 6)}（{fmt_num(lvals[pk])}）",
                     xy=(pk, lvals[pk]), xytext=(0, 12),
                     textcoords="offset points", ha="center", va="bottom",
                     fontsize=8.2, fontweight="bold", color=T["ink"],
                     zorder=7)

    ax.text(0.0, 1.015, f"■ {bars.get('name') or '柱'}（左轴·{bars.get('unit') or '—'}）",
            transform=ax.transAxes, ha="left", va="bottom", fontsize=8.6,
            color=T["ink"], zorder=7)
    ax2.text(1.0, 1.015, f"— {line.get('name') or '线'}（右轴·{line.get('unit') or '—'}）",
             transform=ax2.transAxes, ha="right", va="bottom", fontsize=8.6,
             fontweight="bold", color=T["accent"], zorder=7)

    idx = _x_slice(n, 9)
    ax.set_xticks(idx)
    ax.set_xticklabels([_short(xl[i], 7) for i in idx], fontsize=8.5,
                       color=T["muted"])
    ax.tick_params(axis="x", length=0, pad=8, labelbottom=True)

    h_px = fig.get_size_inches()[1] * 100.0
    _footer(fig, h_px, "两指标单位不同，右轴仅看趋势，柱线不可直接比大小", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-20 雷达图
# --------------------------------------------------------------------------- #
def radar(chart: Dict[str, Any], theme: str) -> Optional[str]:
    axes_lab = [str(a) for a in chart.get("axes") or []]
    if len(axes_lab) < 3 or len(axes_lab) > 8:
        return None
    series: List[Dict[str, Any]] = []
    for s in chart.get("series") or []:
        vals: List[float] = []
        for v in s.get("values") or []:
            f = _num(v)
            if f is None:
                return None
            vals.append(f)
        if len(vals) != len(axes_lab):
            return None
        series.append({"name": str(s.get("name") or "对象"),
                       "values": vals, "accent": bool(s.get("accent"))})
    if not series or len(series) > 2:
        return None

    allv = [v for s in series for v in s["values"]]
    if min(allv) < 0:
        return None
    smax = _num(chart.get("scale_max"))
    if smax is None or smax <= 0:
        smax = max(allv)
    if smax <= 0 or max(allv) > smax + 1e-9:
        return None

    n = len(axes_lab)
    fig, ax, T = canvas(520, theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""),
                        note=chart.get("note", ""),
                        pad_l=14, pad_r=14, pad_b=52, pad_t=62)
    _clean(ax, T)
    ax.set_aspect("equal")
    ax.set_xlim(-1.38, 1.38)
    ax.set_ylim(-1.38, 1.38)
    ax.set_xticks([])
    ax.set_yticks([])

    def pt(i: int, v: float):
        a = math.radians(-90.0 + 360.0 * i / n)
        rr = max(0.0, min(1.0, v / smax))
        return rr * math.cos(a), rr * math.sin(a)

    colors = [T["accent"] if (j == 0 or s["accent"]) else T["context"]
              for j, s in enumerate(series)]

    # 4 圈网格（25/50/75/100%）
    for ring in (0.25, 0.50, 0.75, 1.00):
        xs = [pt(i, smax * ring)[0] for i in range(n)]
        ys = [pt(i, smax * ring)[1] for i in range(n)]
        ax.plot(xs + xs[:1], ys + ys[:1], color=T["line"], linewidth=0.7,
                zorder=1)
    for i in range(n):
        x, y = pt(i, smax)
        ax.plot([0, x], [0, y], color=T["line"], linewidth=0.7, zorder=1)
        a = math.radians(-90.0 + 360.0 * i / n)
        nx, ny = 1.16 * math.cos(a), 1.16 * math.sin(a)
        ha = "left" if math.cos(a) > 0.12 else ("right" if math.cos(a) < -0.12 else "center")
        va = "bottom" if math.sin(a) > 0.12 else ("top" if math.sin(a) < -0.12 else "center")
        ax.text(nx, ny, _short(axes_lab[i], 10), ha=ha, va=va,
                fontsize=9.0, color=T["ink"], zorder=2)

    for j, s in enumerate(series):
        col = colors[j]
        xs, ys = [], []
        for i, v in enumerate(s["values"]):
            x, y = pt(i, v)
            xs.append(x)
            ys.append(y)
        ax.fill(xs, ys, color=col, alpha=0.14, zorder=2)
        ax.plot(xs + xs[:1], ys + ys[:1], color=col, linewidth=1.8,
                solid_capstyle="round", zorder=3)
        ax.plot(xs, ys, "o", markersize=3.4, color=col,
                markeredgecolor=T["paper"], markeredgewidth=0.8, zorder=4)
        for i, v in enumerate(s["values"]):
            a = math.radians(-90.0 + 360.0 * i / n)
            x, y = pt(i, v)
            ax.text(x + 0.035 * math.cos(a), y + 0.035 * math.sin(a),
                    fmt_num(v), ha="center", va="center", fontsize=8.0,
                    color=col, zorder=5)

    # 最强/最弱维：放在画布下沿，压不到径向轴标签
    first = series[0]["values"]
    best = max(range(n), key=lambda i: first[i])
    worst = min(range(n), key=lambda i: first[i])
    fig.text(0.5, 0.060,
             f"重点：最强 {_short(axes_lab[best], 8)}（{fmt_num(first[best])}） · "
             f"最弱 {_short(axes_lab[worst], 8)}（{fmt_num(first[worst])}）",
             ha="center", va="bottom", fontsize=8.2, color=T["accent"], zorder=6)

    # 顶部一行直接标注（不用图例框）；嵌入报告时贴到画布上沿，避免压住雷达
    h_px = fig.get_size_inches()[1] * 100.0
    _ylab = 12.0 if _base.EMBED else 47.0
    if len(series) == 1:
        fig.text(0.5, 1.0 - _ylab / h_px, f"● {series[0]['name']}", ha="center",
                 va="top", fontsize=9.2, color=colors[0])
    else:
        fig.text(0.46, 1.0 - _ylab / h_px, f"● {series[0]['name']}", ha="right",
                 va="top", fontsize=9.2, color=colors[0])
        fig.text(0.54, 1.0 - _ylab / h_px, f"● {series[1]['name']}", ha="left",
                 va="top", fontsize=9.2, color=colors[1])

    _footer(fig, h_px, f"各维统一尺度 0~{fmt_num(smax)}，面积不是总分", T)
    return svg_of(fig)

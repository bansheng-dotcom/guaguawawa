# -*- coding: utf-8 -*-
"""core.charts.v2.types_b3 —— 流程、时间与构成类（8 型）。

覆盖：cal_heatmap / gantt / candlestick / sankey / streamgraph / kpi_break / waffle / rose。

工艺约束（与 types_b1/b2 一致）：
- 六要素：结论式标题、口径副标题、直接标注、参考线、异常归因、来源+图注；
- 单一强调色 + 灰阶；缺失值用斜纹（≠0）；红绿只表达涨跌/好坏；
- 颜色一律取主题令牌；数据不足返回 None，由上层回退 v1。
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from matplotlib.patches import FancyBboxPatch, PathPatch, Polygon, Rectangle
from matplotlib.path import Path

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
    # 嵌入报告图卡时，底注由卡框统一给
    if _base.EMBED:
        return
    h = fig.get_size_inches()[1] * 100.0
    fig.text(0.5, 15.0 / h, text, ha="center", va="bottom",
             fontsize=8.6, color=color or T["muted"])


def _date(s: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


def _nice_ticks(lo: float, hi: float, n: int = 4) -> List[float]:
    return [lo + (hi - lo) * i / n for i in range(n + 1)]


def _bezier(p0: Tuple[float, float], p1: Tuple[float, float],
            p2: Tuple[float, float], p3: Tuple[float, float], n: int = 24) -> List[Tuple[float, float]]:
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        pts.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return pts


# --------------------------------------------------------------------------- #
# viz-32 日历热力图
# --------------------------------------------------------------------------- #
_WD = "一二三四五六日"


def cal_heatmap(chart: Dict[str, Any], theme: str) -> Optional[str]:
    days: Dict[str, Optional[float]] = {}
    for d in chart.get("days") or []:
        key = str(d.get("date") or "")[:10]
        if _date(key) is None:
            continue
        days[key] = _num(d.get("value"))
    if len(days) < 14:
        return None

    ds = sorted(_date(k) for k in days if _date(k) is not None)
    d0, d1 = ds[0], ds[-1]
    if (d1 - d0).days > 400:
        return None
    col0 = d0 - timedelta(days=d0.weekday())
    ncols = ((d1 - col0).days // 7) + 1
    vals = [v for v in days.values() if v is not None]
    if not vals:
        return None
    vmax = max(vals)
    if vmax <= 0:
        return None
    total_days = (d1 - d0).days + 1
    missing = sum(1 for i in range(total_days)
                  if (d0 + timedelta(days=i)).isoformat() not in days)
    peak_key = max((k for k in days if days[k] is not None), key=lambda k: days[k] or 0)

    fig, ax, T = canvas(7 * 30 + 150, theme, chart.get("title", ""),
                        chart.get("unit_meta", chart.get("unit", "")),
                        chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=132, pad_r=54, pad_b=96, pad_t=64)
    _clean(ax, T)
    ax.set_xlim(0, ncols)
    ax.set_ylim(-8.9, 1.5)
    gap = 0.06

    month_seen: set = set()
    last_lab = -99
    for i in range(ncols):
        wk = col0 + timedelta(weeks=i)
        if wk > d1:
            break
        key = (wk.year, wk.month)
        # 月份切换且距上一个标签至少 3 列才写，否则「12月 / 1月」会叠在一起
        if key not in month_seen and wk <= d1 and i - last_lab >= 3:
            month_seen.add(key)
            last_lab = i
            right_edge = i > ncols - 3
            ax.text(i + (1.0 if right_edge else 0.0), -0.35, f"{wk.month}月",
                    ha="right" if right_edge else "left", va="bottom", fontsize=8.0,
                    color=T["muted"], clip_on=False)
        elif key not in month_seen:
            month_seen.add(key)

    for wd in range(7):
        ax.text(-0.12, -(wd + 0.55), _WD[wd], ha="right", va="center", fontsize=8.0,
                color=T["muted"], clip_on=False)

    date_set = {k for k in days}
    for i in range(ncols):
        for wd in range(7):
            d = col0 + timedelta(weeks=i, days=wd)
            if d < d0 or d > d1:
                continue
            y = -(wd + 1)
            if d.isoformat() in date_set and days[d.isoformat()] is not None:
                v = days[d.isoformat()] or 0.0
                t = max(0.0, min(1.0, v / vmax))
                ax.add_patch(Rectangle((i + gap, y + gap), 1 - 2 * gap, 1 - 2 * gap,
                                       facecolor=T["accent"], edgecolor="none",
                                       alpha=0.08 + t * 0.84, zorder=3))
                if v == vmax:
                    ax.text(i + 0.5, y + 0.5, fmt_num(v), ha="center", va="center",
                            fontsize=6.6, color=T["paper"], fontweight="bold", zorder=6)
            else:
                ax.add_patch(Rectangle((i + gap, y + gap), 1 - 2 * gap, 1 - 2 * gap,
                                       facecolor=T["surface"], edgecolor=T["line"],
                                       hatch="///", linewidth=0.6, zorder=3))

    # 色阶图例（按网格列宽均分，避免越界）
    legend_step = max(1.4, (ncols - 0.8) / 4.0)
    for k, (alpha, lab) in enumerate(((0.92, f"高 {fmt_num(vmax)}"), (0.50, "中"), (0.10, "低 >0"))):
        lx = k * legend_step
        ax.add_patch(Rectangle((lx, -8.15), 0.28, 0.55, facecolor=T["accent"],
                               edgecolor="none", alpha=alpha, clip_on=False))
        ax.text(lx + 0.36, -7.88, lab, ha="left", va="center", fontsize=7.2,
                color=T["muted"], clip_on=False)
    mx = 3 * legend_step
    ax.add_patch(Rectangle((mx, -8.15), 0.28, 0.55, facecolor=T["surface"],
                           edgecolor=T["line"], hatch="///", linewidth=0.6, clip_on=False))
    ax.text(mx + 0.36, -7.88, "缺失（≠0）", ha="left", va="center",
            fontsize=7.2, color=T["muted"], clip_on=False)

    ax.text(0, 1.25, f"峰值 {peak_key}：{fmt_num(days[peak_key] or 0)}", ha="left",
            va="bottom", fontsize=8.4, color=T["accent"], clip_on=False)
    ax.set_xticks([])
    ax.set_yticks([])
    _footer(fig, f"周一至周日（自上而下）· 覆盖 {d0.isoformat()} 至 {d1.isoformat()}"
                 f" · 共 {total_days} 天", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-33 甘特图
# --------------------------------------------------------------------------- #
def gantt(chart: Dict[str, Any], theme: str) -> Optional[str]:
    tasks: List[Dict[str, Any]] = []
    for t in chart.get("tasks") or []:
        s, e = _date(t.get("start")), _date(t.get("end"))
        if s is None or e is None or e < s:
            continue
        tasks.append({"label": str(t.get("label") or ""), "start": s, "end": e,
                      "accent": bool(t.get("accent")), "milestone": bool(t.get("milestone"))})
    if len(tasks) < 2:
        return None

    d_lo = min(t["start"] for t in tasks)
    d_hi = max(t["end"] for t in tasks)
    span = max((d_hi - d_lo).days, 1)
    today = _date(chart.get("today"))
    n = len(tasks)

    digger = max((t for t in tasks if not t["milestone"]),
                 key=lambda t: (t["end"] - t["start"]).days, default=None)

    fig, ax, T = canvas(104 + 50 * n, theme, chart.get("title", ""),
                        chart.get("unit_meta", ""), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=150, pad_r=76, pad_b=70, pad_t=76)
    _clean(ax, T)
    ax.set_xlim(-span * 0.02, span * 1.02)
    ax.set_ylim(0.4, n + 1.0)

    # 月刻度
    m = d_lo.replace(day=1)
    while m <= d_hi:
        x = (m - d_lo).days
        ax.axvline(x, color=T["line"], linewidth=0.7, zorder=1)
        ax.text(x, n + 0.72, f"{m.year}-{m.month:02d}", ha="left", va="bottom",
                fontsize=7.8, color=T["muted"], clip_on=False)
        m = (m.replace(day=28) + timedelta(days=4)).replace(day=1)

    if today is not None and d_lo <= today <= d_hi:
        xt = (today - d_lo).days
        ax.axvline(xt, color=T["critical"], linewidth=1.4, linestyle=(0, (4, 3)), zorder=2)
        ax.text(xt, 0.52, f"今日 {today.isoformat()}", ha="center", va="bottom",
                fontsize=8.2, color=T["critical"], clip_on=False)

    for i, t in enumerate(tasks):
        y = n - i
        x0 = (t["start"] - d_lo).days
        w = max((t["end"] - t["start"]).days, 1)
        if t["milestone"]:
            ax.scatter([x0 + w / 2], [y], marker="D", s=62, color=T["watch"],
                       edgecolors=T["paper"], linewidths=1.0, zorder=5)
            ax.text(x0 + w / 2 + span * 0.012, y, f"里程碑 {t['start'].isoformat()}",
                    ha="left", va="center", fontsize=8.2, color=T["watch"], zorder=6)
        else:
            col = T["accent"] if t["accent"] else T["context"]
            ax.barh(y, w, left=x0, height=0.42, color=col, edgecolor="none",
                    alpha=0.90 if t["accent"] else 0.45, zorder=3)
            if w > span * 0.16:
                ax.text(x0 + w / 2, y, f"{t['start'].isoformat()[5:]}→{t['end'].isoformat()[5:]}",
                        ha="center", va="center", fontsize=7.6, color=T["paper"], zorder=5)
        ax.text(-span * 0.03, y, _short(t["label"], 12), ha="right", va="center",
                fontsize=8.8, color=T["ink"],
                fontweight="bold" if t["accent"] else "normal", clip_on=False)

    if digger is not None and digger["accent"] is False:
        mid_x = ((digger["start"] - d_lo).days
                 + (digger["end"] - digger["start"]).days / 2)
        ax.annotate(f"最长任务：{_short(digger['label'], 10)}"
                    f"（{(digger['end'] - digger['start']).days} 天）",
                    xy=(mid_x, n - tasks.index(digger)),
                    xytext=(span * 0.99, n + 0.55), ha="right", va="bottom",
                    fontsize=8.4, color=T["accent"], zorder=8,
                    arrowprops=dict(arrowstyle="-", color=T["reference"], linewidth=0.7,
                                    shrinkA=2, shrinkB=4, connectionstyle="arc3,rad=-0.1"))
    ax.set_xticks([])
    ax.set_yticks([])
    _footer(fig, "时间条长度 = 起止日期实际天数 · 菱形为里程碑 · 虚线为今日 · 依赖关系需专业项目管理工具", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-34 K 线图
# --------------------------------------------------------------------------- #
def candlestick(chart: Dict[str, Any], theme: str) -> Optional[str]:
    candles: List[Dict[str, Any]] = []
    for c in chart.get("candles") or []:
        o, h, l, cl = (_num(c.get("open")), _num(c.get("high")),
                       _num(c.get("low")), _num(c.get("close")))
        if None in (o, h, l, cl):
            return None
        if not (h >= max(o, cl) and l <= min(o, cl)):
            return None
        candles.append({"label": str(c.get("label") or ""), "open": o, "high": h,
                        "low": l, "close": cl, "accent": bool(c.get("accent"))})
    if len(candles) < 5:
        return None

    lo = min(c["low"] for c in candles)
    hi = max(c["high"] for c in candles)
    span = (hi - lo) or abs(hi) * 0.2 or 1.0
    ylo, yhi = lo - span * 0.05, hi + span * 0.08
    n = len(candles)
    closes = [c["close"] for c in candles]
    ma = sum(closes) / n
    up_count = sum(1 for c in candles if c["close"] >= c["open"])

    fig, ax, T = canvas(400, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=64, pad_r=76, pad_b=68, pad_t=62)
    _clean(ax, T)
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(ylo, yhi)

    for v in _nice_ticks(ylo, yhi, 4):
        ax.axhline(v, color=T["line"], linewidth=0.7, zorder=1)
        ax.text(-0.55, v, fmt_num(v, digits=1), ha="right", va="center", fontsize=8.2,
                color=T["muted"], clip_on=False)

    ax.axhline(ma, color=T["reference"], linewidth=1.0, linestyle=(0, (4, 3)), zorder=2)
    ax.text(n - 0.45, ma, f"收盘均值 {fmt_num(ma, digits=1)}", ha="right", va="bottom",
            fontsize=8.0, color=T["reference"], zorder=5)

    zone = 1.0
    bw = min(zone * 0.52, 26)
    for i, c in enumerate(candles):
        up = c["close"] >= c["open"]
        col = T["critical"] if up else T["healthy"]
        ax.plot([i, i], [c["low"], c["high"]], color=col, linewidth=1.0, zorder=4)
        body_lo, body_hi = min(c["open"], c["close"]), max(c["open"], c["close"])
        ax.bar(i, max(body_hi - body_lo, span * 0.004), bottom=body_lo, width=bw,
               color=col, edgecolor=col, linewidth=0.6, alpha=0.95 if up else 0.85, zorder=5)
        if c["accent"]:
            ax.text(i, c["high"] + span * 0.012, fmt_num(c["high"], digits=1), ha="center",
                    va="bottom", fontsize=8.0, color=col, fontweight="bold", zorder=6)

    step = max(1, n // 10)
    ax.set_xticks(list(range(0, n, step)))
    ax.set_xticklabels([_short(candles[i]["label"], 6) for i in range(0, n, step)],
                       fontsize=8.0, color=T["muted"])
    ax.tick_params(axis="x", length=0, pad=6)
    ax.set_yticks([])

    highest = max(candles, key=lambda c: c["high"])
    ax.text(0.995, 0.985,
            f"红涨绿跌 · 最高 {fmt_num(highest['high'], digits=1)}（{_short(highest['label'], 8)}）",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.4,
            color=T["muted"], zorder=6)
    _footer(fig, f"开高低收已通过合法性校验 · 阳线 {up_count}/{n} · 仅适用于 OHLC 结构数据", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-35 桑基图
# --------------------------------------------------------------------------- #
def sankey(chart: Dict[str, Any], theme: str) -> Optional[str]:
    nodes = {str(n.get("id")): str(n.get("label") or n.get("id"))
             for n in chart.get("nodes") or []}
    links: List[Dict[str, Any]] = []
    for lk in chart.get("links") or []:
        a, b, v = str(lk.get("from")), str(lk.get("to")), _num(lk.get("value"))
        if a not in nodes or b not in nodes or v is None or v <= 0 or a == b:
            return None
        links.append({"from": a, "to": b, "value": v})
    if len(nodes) < 3 or len(links) < 2:
        return None

    layer = {nid: 0 for nid in nodes}
    for _ in range(len(nodes) + 1):
        changed = False
        for lk in links:
            if layer[lk["to"]] <= layer[lk["from"]]:
                layer[lk["to"]] = layer[lk["from"]] + 1
                changed = True
        if not changed:
            break
    else:
        return None
    max_layer = max(layer.values())
    if max_layer < 1:
        return None

    cols: Dict[int, List[str]] = {}
    for nid, ly in sorted(layer.items(), key=lambda kv: (kv[1], kv[0])):
        cols.setdefault(ly, []).append(nid)
    total_out = {nid: 0.0 for nid in nodes}
    total_in = {nid: 0.0 for nid in nodes}
    for lk in links:
        total_out[lk["from"]] += lk["value"]
        total_in[lk["to"]] += lk["value"]
    node_total = {nid: max(total_in[nid], total_out[nid]) for nid in nodes}

    main_links = set()
    for ly in range(max_layer):
        cand = [lk for lk in links if layer[lk["from"]] == ly]
        if cand:
            main_links.add(id(max(cand, key=lambda q: (q["value"], q["from"], q["to"]))))

    fig, ax, T = canvas(450, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=150, pad_r=160, pad_b=62, pad_t=58)
    _clean(ax, T)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    left, right = 0.055, 0.945
    node_w = 0.018
    gap = 0.045
    avail = 0.84
    node_y: Dict[str, Tuple[float, float]] = {}
    for ly, nids in cols.items():
        x = left + (right - left - node_w) * (ly / max(max_layer, 1))
        total = sum(node_total[n] for n in nids) or 1.0
        usable = avail - gap * (len(nids) - 1)
        k = usable / total
        y = 0.08 + (avail - usable) / 2
        for nid in sorted(nids, key=lambda q: (-node_total[q], q)):
            h = node_total[nid] * k
            node_y[nid] = (y, h)
            y += h + gap
        for nid in nids:
            ax.add_patch(Rectangle((x, node_y[nid][0]), node_w, max(node_y[nid][1], 0.004),
                                   facecolor=T["context"], edgecolor="none", zorder=6))

    cur_out = {nid: node_y[nid][0] for nid in nodes}
    cur_in = {nid: node_y[nid][0] for nid in nodes}
    x_of = {nid: left + (right - left - node_w) * (layer[nid] / max(max_layer, 1))
            for nid in nodes}

    for lk in links:
        a, b = lk["from"], lk["to"]
        xa = x_of[a] + node_w
        xb = x_of[b]
        ya0 = cur_out[a]
        yb0 = cur_in[b]
        ha = node_y[a][1] * (lk["value"] / max(total_out[a], 1e-9))
        hb = node_y[b][1] * (lk["value"] / max(total_in[b], 1e-9))
        ha, hb = max(ha, 0.004), max(hb, 0.004)
        cur_out[a] += ha + 0.002
        cur_in[b] += hb + 0.002
        main = id(lk) in main_links
        xm = (xa + xb) / 2
        top = _bezier((xa, ya0), (xm, ya0), (xm, yb0), (xb, yb0))
        bot = _bezier((xb, yb0 + hb), (xm, yb0 + hb), (xm, ya0 + ha), (xa, ya0 + ha))
        pts = top + bot
        verts = pts + [pts[0]]
        codes = [Path.MOVETO] + [Path.LINETO] * (len(pts) - 1) + [Path.CLOSEPOLY]
        path = Path(verts, codes)
        ax.add_patch(PathPatch(path, facecolor=T["accent"], edgecolor="none",
                               alpha=0.46 if main else 0.18, zorder=3))
        if main:
            ax.text(xm, (ya0 + yb0 + hb) / 2, fmt_num(lk["value"]), ha="center",
                    va="center", fontsize=8.4, color=T["accent"], fontweight="bold", zorder=7)

    for nid in nodes:
        x = x_of[nid]
        y, h = node_y[nid]
        ly = layer[nid]
        if ly == 0:
            ax.text(x - 0.010, y + h / 2,
                    f"{_short(nodes[nid], 10)} {fmt_num(node_total[nid])}",
                    ha="right", va="center", fontsize=8.6, color=T["ink"],
                    fontweight="bold", clip_on=False)
        elif ly == max_layer:
            ax.text(x + node_w + 0.010, y + h / 2,
                    f"{_short(nodes[nid], 10)} {fmt_num(node_total[nid])}",
                    ha="left", va="center", fontsize=8.6, color=T["ink"], clip_on=False)
        else:
            ax.text(x + node_w / 2, y + h + 0.008, f"{_short(nodes[nid], 8)} {fmt_num(node_total[nid])}",
                    ha="center", va="bottom", fontsize=7.8, color=T["ink"], clip_on=False)

    main_path = "→".join(_short(nodes[nid], 6) for nid in sorted(
        {lk["from"] for lk in links if id(lk) in main_links} |
        {lk["to"] for lk in links if id(lk) in main_links},
        key=lambda q: (layer[q], q)))
    # 主路径写在节点下方空白区：放轴顶会压住中列节点标签
    ax.text(0.5, 0.012, f"主路径：{main_path}", ha="center",
            va="bottom", fontsize=8.4, color=T["accent"], zorder=8)
    ax.set_xticks([])
    ax.set_yticks([])
    _footer(fig, "流带宽度∝流量 · 加粗并标值者为逐层最大主路径 · 无环流向（检测通过）", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-36 河流图
# --------------------------------------------------------------------------- #
def streamgraph(chart: Dict[str, Any], theme: str) -> Optional[str]:
    xlabels = [str(x) for x in (chart.get("xlabels") or [])]
    series: List[Dict[str, Any]] = []
    for s in chart.get("series") or []:
        vals = [_num(v) for v in (s.get("values") or [])]
        if any(v is None or v < 0 for v in vals) or len(vals) != len(xlabels):
            return None
        series.append({"name": str(s.get("name") or ""), "values": vals,
                       "accent": bool(s.get("accent"))})
    if len(xlabels) < 3 or not 2 <= len(series) <= 6:
        return None

    n = len(xlabels)
    totals = [sum(s["values"][i] for s in series) for i in range(n)]
    vmax = max(totals) or 1.0
    last = sorted(range(len(series)), key=lambda k: -series[k]["values"][-1])
    top_last = last[0]

    fig, ax, T = canvas(400, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=58, pad_r=190, pad_b=64, pad_t=58)
    _clean(ax, T)
    ax.set_xlim(0, n - 1)
    ax.set_ylim(0, vmax * 1.06)

    # 对称居中：每条带的起点 =（全期最大值 − 当期合计）/2，
    # 否则从合计一半往上堆会让最上层溢出画布（标签被裁）。
    base = [(vmax - totals[i]) / 2 for i in range(n)]
    xs = list(range(n))
    tones = [T["context"], T["reference"], T["muted"]]
    for k, s in enumerate(series):
        top = [base[i] + s["values"][i] for i in range(n)]
        col = T["accent"] if s["accent"] or k == 0 else tones[min(k - 1, len(tones) - 1)]
        ax.fill_between(xs, base, top, color=col, alpha=0.55 if (s["accent"] or k == 0) else 0.26,
                        linewidth=0.8, edgecolor=col, zorder=3 + k)
        ax.text(n - 1 + 0.15, (top[-1] + base[-1]) / 2, f"{_short(s['name'], 8)} {fmt_num(s['values'][-1])}",
                ha="left", va="center", fontsize=8.4,
                color=T["ink"] if (s["accent"] or k == 0) else T["muted"],
                fontweight="bold" if (s["accent"] or k == 0) else "normal", clip_on=False)
        base = top

    ax.axhline(totals[-1] / 2, color=T["reference"], linewidth=0.8,
               linestyle=(0, (3, 3)), zorder=2)
    step = max(1, n // 10)
    ax.set_xticks(list(range(0, n, step)))
    ax.set_xticklabels([xlabels[i] for i in range(0, n, step)], fontsize=8.2, color=T["muted"])
    ax.tick_params(axis="x", length=0, pad=6)
    ax.set_yticks([])

    if not _base.EMBED:
        # 放在标题行右侧（副标题只占左侧），避免压住最上层流带的标签
        fig.text(1.0, 1.0 - 33.0 / (fig.get_size_inches()[1] * 100.0),
                 f"最新期最大：{_short(series[top_last]['name'], 10)}"
                 f"（{series[top_last]['values'][-1] / max(totals[-1], 1e-9):.0%}）",
                 ha="right", va="top", fontsize=8.4, color=T["accent"])
    _footer(fig, "非负中心堆叠 · 右端为各主题最新值标签列 · 面积厚度∝当期数值", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-47 KPI 趋势分解
# --------------------------------------------------------------------------- #
def kpi_break(chart: Dict[str, Any], theme: str) -> Optional[str]:
    kpi = chart.get("kpi") or {}
    value = _num(kpi.get("value"))
    trend = chart.get("trend") or {}
    tv = [_num(v) for v in (trend.get("values") or [])]
    tx = [str(x) for x in (trend.get("xlabels") or [])]
    items: List[Dict[str, Any]] = []
    for it in (chart.get("breakdown") or {}).get("items") or []:
        v = _num(it.get("value"))
        if v is None:
            continue
        items.append({"label": str(it.get("label") or ""), "value": v,
                      "accent": bool(it.get("accent"))})
    if value is None or len(tv) < 3 or any(v is None for v in tv) or len(tx) != len(tv) \
            or not items:
        return None

    fig, ax, T = canvas(470, theme, chart.get("title", ""), "",
                        chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=30, pad_r=30, pad_b=44, pad_t=52)
    _clean(ax, T)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])

    # 模块 1：KPI 卡
    ax.add_patch(FancyBboxPatch((0.035, 0.60), 0.30, 0.32,
                                boxstyle="round,pad=0.008",
                                facecolor=T["surface"], edgecolor=T["line_strong"],
                                linewidth=0.8, transform=ax.transAxes, zorder=2))
    ax.text(0.055, 0.875, _short(kpi.get("label", "核心指标"), 14),
            transform=ax.transAxes, ha="left", va="top", fontsize=9.0, color=T["muted"], zorder=4)
    ax.text(0.055, 0.765, fmt_num(value), transform=ax.transAxes, ha="left", va="center",
            fontsize=30, fontweight="bold", color=T["ink"], zorder=4)
    ax.text(0.055, 0.695, str(kpi.get("unit") or ""), transform=ax.transAxes,
            ha="left", va="center", fontsize=9.0, color=T["muted"], zorder=4)
    if kpi.get("delta_label"):
        ax.text(0.055, 0.635, str(kpi["delta_label"]), transform=ax.transAxes,
                ha="left", va="center", fontsize=8.4, color=T["muted"], zorder=4)

    # 模块 2：趋势
    tlo, thi = min(tv), max(tv)
    span = (thi - tlo) or abs(thi) * 0.2 or 1.0
    tlo, thi = tlo - span * 0.10, thi + span * 0.10
    px0, px1 = 0.38, 0.965
    py0, py1 = 0.645, 0.925
    ax.text(px0, 0.955, f"趋势（口径同 KPI）· {_short(kpi.get('unit') or '', 8)}",
            transform=ax.transAxes, ha="left", va="top", fontsize=8.2, color=T["muted"], zorder=4)
    ax.plot([px0, px1], [0.675] * 2, transform=ax.transAxes, color=T["line"], linewidth=0.7, zorder=2)
    xs = [px0 + (px1 - px0) * i / (len(tv) - 1) for i in range(len(tv))]
    ys = [py0 + (py1 - py0) * (v - tlo) / (thi - tlo) for v in tv]
    ax.plot(xs, ys, transform=ax.transAxes, color=T["accent"], linewidth=2.0, zorder=4)
    ax.scatter([xs[-1]], [ys[-1]], transform=ax.transAxes, s=32, color=T["accent"],
               edgecolors=T["paper"], linewidths=1.0, zorder=6)
    ax.text(xs[-1] - 0.01, ys[-1] + 0.028, fmt_num(tv[-1]), transform=ax.transAxes,
            ha="right", va="bottom", fontsize=8.6, color=T["accent"],
            fontweight="bold", zorder=6)
    step = max(1, len(tx) // 7)
    for i in range(0, len(tx), step):
        ax.text(xs[i], 0.612, _short(tx[i], 6), transform=ax.transAxes, ha="center",
                va="top", fontsize=7.6, color=T["muted"], zorder=4)

    # 模块 3：驱动拆解
    ax.text(0.035, 0.545, "驱动拆解（口径与 KPI 一致，同单位才可加总）",
            transform=ax.transAxes, ha="left", va="top", fontsize=8.4, color=T["muted"], zorder=4)
    ranked = sorted(items, key=lambda q: (-abs(q["value"]), q["label"]))
    bmax = max(abs(it["value"]) for it in ranked) or 1.0
    y = 0.485
    for it in ranked[:7]:
        w = 0.46 * abs(it["value"]) / bmax
        col = T["healthy"] if it["value"] >= 0 else T["critical"]
        if it["accent"]:
            col = T["accent"] if it["value"] >= 0 else T["critical"]
        ax.text(0.035, y, _short(it["label"], 14), transform=ax.transAxes,
                ha="left", va="center", fontsize=8.6, color=T["ink"], zorder=4)
        ax.add_patch(Rectangle((0.325, y - 0.016), max(w, 0.004), 0.032,
                               facecolor=col, edgecolor="none", alpha=0.75,
                               transform=ax.transAxes, zorder=3))
        ax.text(0.333 + w, y, f"{'+' if it['value'] >= 0 else '−'}{fmt_num(abs(it['value']))}",
                transform=ax.transAxes, ha="left", va="center", fontsize=8.2,
                color=T["muted"], zorder=4)
        y -= 0.062

    top_drv = ranked[0]
    ax.text(0.965, 0.545, f"最大驱动：{_short(top_drv['label'], 10)} "
                          f"{'+' if top_drv['value'] >= 0 else '−'}{fmt_num(abs(top_drv['value']))}",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.4,
            color=T["accent"], zorder=4)
    _footer(fig, "三模块同口径 · 趋势与拆解均对应同一 KPI · 拆解项之和应能回到 KPI 变化", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-15 华夫图
# --------------------------------------------------------------------------- #
def waffle(chart: Dict[str, Any], theme: str) -> Optional[str]:
    items: List[Dict[str, Any]] = []
    for it in chart.get("items") or []:
        v = _num(it.get("value"))
        if v is None or v < 0:
            continue
        items.append({"label": str(it.get("label") or ""), "value": v,
                      "accent": bool(it.get("accent"))})
    if not items:
        return None
    total = sum(it["value"] for it in items)
    if total <= 0:
        return None

    raw = [it["value"] / total * 100.0 for it in items]
    cells = [int(math.floor(r)) for r in raw]
    rest = 100 - sum(cells)
    order = sorted(range(len(items)), key=lambda k: (-(raw[k] - cells[k]), k))
    for k in order[:max(rest, 0)]:
        cells[k] += 1
    covered = sum(cells)
    biggest = max(range(len(items)), key=lambda k: cells[k])

    fig, ax, T = canvas(430, theme, chart.get("title", ""), chart.get("unit_meta", "%"),
                        chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=36, pad_r=30, pad_b=54, pad_t=58)
    _clean(ax, T)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    cell, gap = 0.060, 0.006
    x0, y_top = 0.035, 0.90
    tones = [T["context"], T["reference"], T["muted"], T["line_strong"]]
    pos = 0
    for k, it in enumerate(items):
        col = T["accent"] if (it["accent"] or k == 0) else tones[min(k - 1, len(tones) - 1)]
        alpha = 0.90 if (it["accent"] or k == 0) else 0.50
        for _ in range(cells[k]):
            r_, c_ = divmod(pos, 10)
            x = x0 + c_ * cell
            y = y_top - (r_ + 1) * cell
            ax.add_patch(Rectangle((x + gap, y + gap), cell - 2 * gap, cell - 2 * gap,
                                   facecolor=col, edgecolor="none", alpha=alpha, zorder=3))
            pos += 1
        # 图例一项一行（名称 + 占比 + 格数）：原来两行会与下一项挤在一起
        ly = 0.86 - k * 0.072
        ax.add_patch(Rectangle((0.68, ly - 0.016), 0.022, 0.022, facecolor=col,
                               edgecolor="none", alpha=alpha, zorder=3))
        ax.text(0.715, ly,
                f"{_short(it['label'], 8)} {raw[k]:.1f}% · {cells[k]} 格",
                transform=ax.transAxes, ha="left", va="center", fontsize=8.0,
                color=T["ink"], fontweight="bold" if it["accent"] or k == 0 else "normal",
                zorder=4)

    if covered < 100:
        for p in range(covered, 100):
            r_, c_ = divmod(p, 10)
            x = x0 + c_ * cell
            y = y_top - (r_ + 1) * cell
            ax.add_patch(Rectangle((x + gap, y + gap), cell - 2 * gap, cell - 2 * gap,
                                   facecolor=T["surface"], edgecolor=T["line"],
                                   hatch="///", linewidth=0.5, zorder=3))

    ax.text(0.035, 0.955, "每格 = 1% · 合计 100 格（最大余数法取整）", transform=ax.transAxes,
            ha="left", va="bottom", fontsize=8.2, color=T["muted"], zorder=4)
    ax.text(0.035, 0.16,
            f"最大项 {_short(items[biggest]['label'], 10)} 占 {raw[biggest]:.1f}%"
            + (f" · 未覆盖 {100 - covered}%" if covered < 100 else ""),
            transform=ax.transAxes, ha="left", va="center", fontsize=8.4,
            color=T["accent"], zorder=4)
    ax.set_xticks([])
    ax.set_yticks([])
    _footer(fig, "填充格数与标注占比一致 · 斜纹为未覆盖部分（≠0）· 10×10 便于心算", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-43 玫瑰图
# --------------------------------------------------------------------------- #
def rose(chart: Dict[str, Any], theme: str) -> Optional[str]:
    sectors: List[Dict[str, Any]] = []
    for s in chart.get("sectors") or []:
        v = _num(s.get("value"))
        if v is None or v < 0:
            continue
        sectors.append({"label": str(s.get("label") or ""), "value": v,
                        "accent": bool(s.get("accent"))})
    if not 5 <= len(sectors) <= 12:
        return None
    vmax = max(s["value"] for s in sectors)
    if vmax <= 0:
        return None
    n = len(sectors)
    top = max(range(n), key=lambda k: sectors[k]["value"])

    fig, ax, T = canvas(470, theme, chart.get("title", ""), chart.get("unit_meta", ""),
                        chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=30, pad_r=30, pad_b=48, pad_t=56)
    _clean(ax, T)
    ax.set_aspect("equal")
    ax.set_xlim(-1.52, 1.52)
    ax.set_ylim(-1.34, 1.34)

    for ring in (0.25, 0.5, 0.75, 1.0):
        rr = math.sqrt(ring)
        ax.add_patch(Polygon(_circle(0, 0, rr, 96), closed=True, fill=False,
                             edgecolor=T["line"], linewidth=0.7, zorder=1))
        ax.text(rr * 0.72, -rr * 0.72 + 0.02, fmt_num(vmax * ring), ha="left", va="center",
                fontsize=7.4, color=T["muted"], zorder=2)

    for i, s in enumerate(sectors):
        a0 = 90.0 - 360.0 * i / n
        a1 = a0 - 360.0 / n
        rad = math.sqrt(s["value"] / vmax)
        pts = [(0.0, 0.0)]
        steps = 12
        for k in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * k / steps)
            pts.append((rad * math.cos(a), rad * math.sin(a)))
        col = T["accent"] if s["accent"] or i == top else T["context"]
        ax.add_patch(Polygon(pts, closed=True, facecolor=col, edgecolor=T["paper"],
                             linewidth=1.2, alpha=0.88 if s["accent"] or i == top else 0.42,
                             zorder=3))
        am = math.radians((a0 + a1) / 2)
        lx0, ly0 = (rad + 0.03) * math.cos(am), (rad + 0.03) * math.sin(am)
        lx1, ly1 = (rad + 0.10) * math.cos(am), (rad + 0.10) * math.sin(am)
        ax.plot([lx0, lx1], [ly0, ly1], color=T["line_strong"], linewidth=0.7, zorder=4)
        ax.text(lx1 + 0.02 * math.cos(am), ly1 + 0.02 * math.sin(am),
                f"{_short(s['label'], 8)} {fmt_num(s['value'])}",
                ha="left" if math.cos(am) >= 0 else "right", va="center", fontsize=8.0,
                color=T["ink"] if s["accent"] or i == top else T["muted"],
                fontweight="bold" if s["accent"] or i == top else "normal",
                zorder=6, clip_on=False)

    ax.text(0, -1.26,
            f"最大扇区 {_short(sectors[top]['label'], 10)} 占 "
            f"{sectors[top]['value'] / sum(s['value'] for s in sectors):.1%}",
            ha="center", va="center", fontsize=8.4, color=T["accent"], zorder=6)
    ax.set_xticks([])
    ax.set_yticks([])
    _footer(fig, "扇区面积∝数值（半径 √ 映射）· 按给定周期顺序排列 · 环刻度为面积等分", T)
    return svg_of(fig)


def _circle(cx: float, cy: float, r: float, n: int) -> List[Tuple[float, float]]:
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
            for i in range(n)]

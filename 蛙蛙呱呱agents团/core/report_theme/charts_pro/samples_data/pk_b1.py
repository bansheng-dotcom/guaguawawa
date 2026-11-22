# -*- coding: utf-8 -*-
"""flow 图型库 · 第一批：比较与构成（11 型）"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from .prokit2 import (  # noqa: E402
    ACCENT, BLUE, INK, INK2, LINE, LINE2, MUTED, FAINT, WHITE,
    CATS, V24, V25, CITIES, TICKET, MONTHS, TOTAL, DS,
    ci, esc, f0, f1, ln, pa, rc, svg, sx, sy, t,
)

TINTS = ["#1F2A37", "#3C4A57", "#5A6874", "#78838E", "#9AA3AC", "#BCC2C8"]


def _grid_y(b, vals, x1, x2, Y, fmt=f1, lx=None):
    for v in vals:
        y = Y(v)
        b.append(ln(x1, y, x2, y, LINE, 1))
        b.append(t(lx if lx is not None else x1 - 8, y + 3, fmt(v), 7.2, FAINT, anchor="end"))


# --------------------------------------------------------------------------- #
# vbar · 纵向柱 + 目标线
# --------------------------------------------------------------------------- #
def fig_vbar() -> str:
    W, H = 640, 320
    L, R, T, B = 64, 596, 52, 258
    vals = list(DS.RETAIL)
    years = list(DS.YEARS)
    lo, hi = 0, 400
    Y = sy(lo, hi, B, T)
    slot = (R - L) / len(vals)
    bw = slot * 0.46
    b = svg(W, H, "年度规模柱状")
    _grid_y(b, (0, 100, 200, 300, 400), L, R, Y, f0)
    for i, (yr, v) in enumerate(zip(years, vals)):
        cx = L + slot * i + slot / 2
        b.append(rc(cx - bw / 2, Y(v), bw, B - Y(v), ACCENT if i == len(vals) - 1 else INK2, rx=2))
        b.append(t(cx, Y(v) - 7, f1(v), 9, INK, 700, anchor="middle", halo=True))
        b.append(t(cx, B + 18, yr, 8, MUTED, anchor="middle"))
    cagr = (vals[-1] / vals[0]) ** (1 / (len(vals) - 1)) - 1
    b.append(t(R, T - 14, f"2020–2025 CAGR {cagr * 100:.1f}%", 8.2, INK, 700, anchor="end"))
    b.append(t(20, 306, "灰色为历史年份，红色为最新一年；数值标在柱顶。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# lollipop · 棒棒糖
# --------------------------------------------------------------------------- #
def fig_lollipop() -> str:
    W, H = 640, 300
    L, R = 130, 590
    rows = sorted(zip(CATS, V25), key=lambda x: -x[1])
    X = sx(0, 110, L, R)
    b = svg(W, H, "品类棒棒糖图")
    for v in (0, 25, 50, 75, 100):
        b.append(ln(X(v), 40, X(v), 240, LINE, 1))
        b.append(t(X(v), 254, str(v), 7.2, FAINT, anchor="middle"))
    for i, (name, v) in enumerate(rows):
        y = 56 + i * 30
        b.append(t(20, y + 4, name, 8.4, INK2))
        b.append(ln(L, y, X(v), y, LINE2, 1.4))
        b.append(ci(X(v), y, 5, ACCENT if i == 0 else INK2))
        b.append(t(X(v) + 10, y + 4, f1(v), 8.2, INK, 600, halo=True))
    b.append(t(20, 288, "茎线代替柱子：省墨，且端点即精确值。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# pareto · 帕累托（柱 + 累计线）
# --------------------------------------------------------------------------- #
def fig_pareto() -> str:
    W, H = 640, 320
    L, R, T, B = 64, 596, 52, 252
    rows = sorted(DS.RETURN_REASONS, key=lambda x: -x[1])
    total = sum(v for _, v in rows)
    mx = rows[0][1] * 1.2
    Y = sy(0, mx, B, T)
    slot = (R - L) / len(rows)
    bw = slot * 0.5
    b = svg(W, H, "退货原因帕累托")
    _grid_y(b, (0, 20, 40), L, R, Y, f0)
    cum = 0
    pts = []
    for i, (name, v) in enumerate(rows):
        cx = L + slot * i + slot / 2
        b.append(rc(cx - bw / 2, Y(v), bw, B - Y(v), INK2, rx=1.5))
        b.append(t(cx, Y(v) - 6, f"{v:.0f}", 7.6, INK, 600, anchor="middle", halo=True))
        b.append(t(cx, B + 18, name, 7.4, INK2, anchor="middle"))
        cum += v
        pts.append((cx, B - (cum / 100) * (B - T)))
    b.append(pa("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts), "none", ACCENT, 1.8))
    for x, y in pts:
        b.append(ci(x, y, 3.2, ACCENT))
    b.append(ln(L, B - 0.8 * (B - T), R, B - 0.8 * (B - T), ACCENT, 1, "3 3"))
    b.append(t(R, B - 0.8 * (B - T) - 6, "累计 80%", 7.2, ACCENT, anchor="end"))
    b.append(t(20, 306, "柱=单项占比，线=累计占比；前两项已占 69%。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# bridge · 横向贡献桥
# --------------------------------------------------------------------------- #
def fig_bridge() -> str:
    """横向贡献条：从 0 轴出发的正负贡献，期初/期末写在图内。"""
    W, H = 640, 330
    L, R = 150, 600
    start, end = DS.RETAIL[-2], DS.RETAIL[-1]
    deltas = sorted([(c, round(a - b, 1)) for c, a, b in zip(CATS, V25, V24)], key=lambda x: -x[1])
    mx = max(abs(d) for _, d in deltas) * 1.35
    X = sx(-mx, mx, L + 60, R - 60)
    zero = X(0)
    b = svg(W, H, "贡献拆解")
    b.append(ln(zero, 40, zero, 262, LINE2, 1))
    for i, (name, d) in enumerate(deltas):
        y = 56 + i * 32
        x0, x1 = zero, X(d)
        b.append(rc(min(x0, x1), y - 9, max(abs(x1 - x0), 2), 18,
                    BLUE if d > 0 else ACCENT, rx=1.5))
        b.append(t(L - 10, y + 4, name, 8, INK2, anchor="end"))
        b.append(t(max(x0, x1) + 8, y + 4, f"{d:+.1f}", 8, INK, 600))
    b.append(t(20, 296, f"期初 {start} → 期末 {end}：六项贡献合计 {end - start:+.1f} 亿元。", 8, INK2))
    b.append(t(20, 314, "以 0 为轴：蓝=增、红=减；不是瀑布，故不画累计水位。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# grouped_bar · 分组柱
# --------------------------------------------------------------------------- #
def fig_grouped() -> str:
    W, H = 640, 330
    L, R, T, B = 64, 596, 52, 258
    Y = sy(0, 110, B, T)
    slot = (R - L) / len(CATS)
    bw = min(slot / 3.2, 26)
    b = svg(W, H, "两期分组柱")
    _grid_y(b, (0, 25, 50, 75, 100), L, R, Y, f0)
    for i, cat in enumerate(CATS):
        cx = L + slot * i + slot / 2
        for j, (v, color) in enumerate(((V24[i], LINE2), (V25[i], INK2))):
            x = cx - bw + j * bw
            b.append(rc(x, Y(v), bw - 2, B - Y(v), ACCENT if (i == 2 and j == 1) else color, rx=1))
        b.append(t(cx, B + 18, cat, 7.2, INK2, anchor="middle"))
        b.append(t(cx, Y(V25[i]) - 8, f1(V25[i]), 7.4, INK, 600, anchor="middle", halo=True))
    b.append(rc(L, T - 20, 10, 8, LINE2))
    b.append(t(L + 16, T - 13, "2024", 7.2, MUTED))
    b.append(rc(L + 54, T - 20, 10, 8, INK2))
    b.append(t(L + 70, T - 13, "2025", 7.2, MUTED))
    b.append(t(20, 316, "同组两根柱：左 2024、右 2025；红色只标增速最快的品类。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# stacked_bar · 堆叠柱（三年 × 六品类）
# --------------------------------------------------------------------------- #
def fig_stacked() -> str:
    W, H = 640, 330
    L, R, T, B = 64, 596, 52, 258
    sums = {c: [sum(DS.MONTHLY[c][i * 12:(i + 1) * 12]) for i in range(3)] for c in CATS}
    totals = [sum(sums[c][i] for c in CATS) for i in range(3)]
    Y = sy(0, 420, B, T)
    slot = (R - L) / 3
    bw = 110
    b = svg(W, H, "三年堆叠柱")
    _grid_y(b, (0, 100, 200, 300, 400), L, R, Y, f0)
    for i in range(3):
        cx = L + slot * i + slot / 2
        acc = 0
        for j, cat in enumerate(CATS):
            v = sums[cat][i]
            y0, y1 = Y(acc), Y(acc + v)
            b.append(rc(cx - bw / 2, y1, bw, y0 - y1, TINTS[j], rx=0))
            if v > 15:
                b.append(t(cx, (y0 + y1) / 2 + 3, f"{v:.0f}", 7, WHITE, 600, anchor="middle"))
            acc += v
        b.append(t(cx, Y(acc) - 8, f"{acc:.0f}", 8.2, INK, 700, anchor="middle", halo=True))
        b.append(t(cx, B + 18, ("2023", "2024", "2025")[i], 8, MUTED, anchor="middle"))
    b.append(t(20, 316, "柱内为品类，顶数为合计（月度合计口径 346→363→376）。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# area · 面积
# --------------------------------------------------------------------------- #
def fig_area() -> str:
    W, H = 640, 300
    L, R, T, B = 64, 590, 50, 240
    Y = sy(18, 46, B, T)
    X = sx(0, len(TOTAL) - 1, L + 6, R - 6)
    b = svg(W, H, "月度规模面积")
    _grid_y(b, (20, 30, 40), L, R, Y, f0)
    pts = [(X(i), Y(v)) for i, v in enumerate(TOTAL)]
    b.append(pa(f"M {pts[0][0]:.1f},{B} " + " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts)
                + f" L {pts[-1][0]:.1f},{B} Z", ACCENT, opacity=".08"))
    b.append(pa("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts), "none", INK2, 1.8))
    b.append(t(pts[-1][0], pts[-1][1] - 10, f"{TOTAL[-1]:.1f}", 8.4, INK, 700, anchor="end", halo=True))
    for i in range(0, len(TOTAL), 6):
        b.append(t(X(i), B + 16, MONTHS[i], 7, FAINT, anchor="middle"))
    b.append(t(20, 286, "面积强调量级；端点标最新值。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# streamgraph · 流图
# --------------------------------------------------------------------------- #
def fig_stream() -> str:
    W, H = 640, 330
    L, R, T, B = 64, 520, 50, 262
    series = {c: [DS.MONTHLY[c][i] for i in range(36)] for c in CATS}
    totals = [sum(series[c][i] for c in CATS) for i in range(36)]
    mx = max(totals)
    X = sx(0, 35, L + 4, R)
    Hh = (B - T) / mx
    base = [(T + B) / 2] * 36
    b = svg(W, H, "品类结构流图")
    lower = list(base)
    for j, cat in enumerate(CATS):
        upper = [lower[i] - series[cat][i] * Hh for i in range(36)]
        d = (f"M {X(0):.1f},{lower[0]:.1f} " +
             " ".join(f"L {X(i):.1f},{lower[i]:.1f}" for i in range(1, 36)) +
             " " + " ".join(f"L {X(i):.1f},{upper[i]:.1f}" for i in range(35, -1, -1)) + " Z")
        b.append(pa(d, TINTS[j], opacity=".9"))
        b.append(t(R + 8, (upper[-1] + lower[-1]) / 2 + 3, cat, 7.2, MUTED))
        lower = upper
    for i, lab in enumerate(("2023-01", "2024-01", "2025-01")):
        b.append(t(X(i * 12), B + 18, lab, 7, FAINT, anchor="middle"))
    b.append(t(20, 316, "以中线为轴的堆叠流图；只看结构变化，不读单点数值。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# kpi_break · KPI + 拆解
# --------------------------------------------------------------------------- #
def fig_kpi() -> str:
    W, H = 640, 330
    b = svg(W, H, "KPI 与拆解")
    kpis = [("376.3", "2025 规模", "亿元", "+6.9%"), ("62.7", "品类均值", "亿元", "—"),
            ("71%", "两项贡献占比", "—", "家纺+小家电")]
    for i, (v, lab, unit, note) in enumerate(kpis):
        x = 24 + i * 204
        b.append(t(x, 56, v, 24, INK, 700))
        b.append(t(x, 74, lab, 8, MUTED))
        b.append(t(x, 90, f"{unit} · {note}", 7.2, FAINT))
    b.append(ln(20, 108, 620, 108, LINE, 1))
    rows = sorted(zip(CATS, V25), key=lambda x: -x[1])
    X = sx(0, 100, 200, 600)
    for i, (name, v) in enumerate(rows):
        y = 138 + i * 30
        b.append(t(20, y + 4, name, 8, INK2))
        b.append(rc(200, y - 7, X(v) - 200, 14, ACCENT if i == 0 else INK2, rx=1))
        b.append(t(X(v) + 8, y + 4, f1(v), 8, INK, 600))
    b.append(t(20, 320, "上半区三个口径一致；下半区是同一总量的拆解。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)

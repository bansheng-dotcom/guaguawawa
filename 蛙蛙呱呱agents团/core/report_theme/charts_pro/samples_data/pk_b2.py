# -*- coding: utf-8 -*-
"""flow 图型库 · 第二批：构成与分布（12 型）"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from .prokit2 import (  # noqa: E402
    ACCENT, BLUE, INK, INK2, LINE, LINE2, MUTED, FAINT, WHITE,
    CATS, V24, V25, CITIES, TICKET, DS, median,
    ci, f0, f1, ln, pa, rc, svg, sx, sy, t,
)

TINTS = ["#1F2A37", "#3D4B58", "#5C6A76", "#7B8792", "#9BA4AD", "#BCC3C9"]


def arc(cx, cy, r0, r1, a0, a1, fill, opacity=None) -> str:
    p0 = (cx + r0 * math.cos(a0), cy + r0 * math.sin(a0))
    p1 = (cx + r1 * math.cos(a0), cy + r1 * math.sin(a0))
    p2 = (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1))
    p3 = (cx + r0 * math.cos(a1), cy + r0 * math.sin(a1))
    large = 1 if (a1 - a0) > math.pi else 0
    o = f' opacity="{opacity}"' if opacity else ""
    d = (f"M {p0[0]:.1f},{p0[1]:.1f} L {p1[0]:.1f},{p1[1]:.1f} "
         f"A {r1},{r1} 0 {large} 1 {p2[0]:.1f},{p2[1]:.1f} "
         f"L {p3[0]:.1f},{p3[1]:.1f} A {r0},{r0} 0 {large} 0 {p0[0]:.1f},{p0[1]:.1f} Z")
    return f'<path d="{d}" fill="{fill}"{o}/>'


def _share_rows():
    rows = sorted(zip(CATS, V25), key=lambda x: -x[1])
    big = [(c, v) for c, v in rows if v / sum(V25) >= 0.08]
    small = [(c, v) for c, v in rows if v / sum(V25) < 0.08]
    if small:
        big.append(("其他", sum(v for _, v in small)))
    return big


# --------------------------------------------------------------------------- #
# pie / donut
# --------------------------------------------------------------------------- #
def _pie(donut: bool) -> str:
    W, H = 640, 320
    cx, cy, r = 210, 160, 108
    rows = _share_rows()
    total = sum(v for _, v in rows)
    b = svg(W, H, "品类构成" + ("环形图" if donut else "饼图"))
    a = -math.pi / 2
    for i, (name, v) in enumerate(rows):
        da = v / total * math.tau
        b.append(arc(cx, cy, r * (0.58 if donut else 0), r, a, a + da, TINTS[i]))
        mid = a + da / 2
        lx, ly = cx + (r + 18) * math.cos(mid), cy + (r + 18) * math.sin(mid)
        side = "start" if math.cos(mid) > 0 else "end"
        b.append(ln(cx + (r + 2) * math.cos(mid), cy + (r + 2) * math.sin(mid), lx, ly, LINE2, 1))
        b.append(t(lx + (6 if side == "start" else -6), ly + 3,
                   f"{name} {v / total * 100:.0f}%", 7.6, INK2, anchor=side))
        a += da
    if donut:
        b.append(t(cx, cy - 2, "376.3", 20, INK, 700, anchor="middle"))
        b.append(t(cx, cy + 16, "亿元 · 2025", 7.4, MUTED, anchor="middle"))
    b.append(t(20, 306, ("环形图" if donut else "饼图") + "只用于 ≤6 类占比；标签直接拉出，不用图例。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


def fig_pie() -> str:
    return _pie(False)


def fig_donut() -> str:
    return _pie(True)


# --------------------------------------------------------------------------- #
# treemap · 树图（squarify 简化版）
# --------------------------------------------------------------------------- #
def _layout(items, x, y, w, h, out, vertical=True):
    if not items:
        return
    if len(items) == 1:
        out.append((items[0][0], items[0][1], x, y, w, h))
        return
    total = sum(v for _, v in items)
    acc, k = 0.0, 0
    while k < len(items) - 1 and acc + items[k][1] < total / 2:
        acc += items[k][1]
        k += 1
    k = max(1, k)
    first, rest = items[:k], items[k:]
    ratio = sum(v for _, v in first) / total
    if vertical:
        _layout(first, x, y, w * ratio, h, out, not vertical)
        _layout(rest, x + w * ratio, y, w * (1 - ratio), h, out, not vertical)
    else:
        _layout(first, x, y, w, h * ratio, out, not vertical)
        _layout(rest, x, y + h * ratio, w, h * (1 - ratio), out, not vertical)


def fig_treemap() -> str:
    W, H = 640, 360
    items = sorted([(c, float(sum(v for _, v in DS.TREEMAP[c]))) for c in DS.TREEMAP], key=lambda x: -x[1])
    total = sum(v for _, v in items)
    out = []
    _layout(items, 24, 40, 592, 270, out, True)
    b = svg(W, H, "品类树图")
    for i, (name, v, x, y, w, h) in enumerate(out):
        b.append(rc(x + 1, y + 1, w - 2, h - 2, TINTS[i % 6], rx=2))
        b.append(t(x + 8, y + 18, name, 8.6, WHITE, 600))
        b.append(t(x + 8, y + 34, f"{v:.0f}", 9.2, WHITE, 700))
        b.append(t(x + 8, y + 46, f"{v / total * 100:.0f}%", 7.2, "#E8E8E8"))
    b.append(t(20, 344, "面积 = 规模；只标前六类（子类在旭日图里）。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# sunburst · 旭日图（品类 → 子类）
# --------------------------------------------------------------------------- #
def fig_sunburst() -> str:
    W, H = 640, 360
    cx, cy = 300, 180
    cats = sorted([(c, DS.TREEMAP[c]) for c in DS.TREEMAP],
                  key=lambda x: -sum(v for _, v in x[1]))
    total = sum(sum(v for _, v in subs) for _, subs in cats)
    b = svg(W, H, "品类与子类旭日图")
    a = -math.pi / 2
    tops = []
    for i, (cat, subs) in enumerate(cats):
        da = sum(v for _, v in subs) / total * math.tau
        b.append(arc(cx, cy, 40, 92, a, a + da, TINTS[i % 6]))
        mid = a + da / 2
        if da > 0.34:
            b.append(t(cx + 66 * math.cos(mid), cy + 66 * math.sin(mid) + 3,
                       cat[:2], 7.4, WHITE, 600, anchor="middle"))
        aa = a
        for j, (sub, v) in enumerate(sorted(subs, key=lambda x: -x[1])):
            dda = v / total * math.tau
            b.append(arc(cx, cy, 92, 126, aa, aa + dda, TINTS[(i + j) % 6], opacity=".75"))
            tops.append((v, aa + dda / 2, sub))
            aa += dda
        a += da
    for v, ang, sub in sorted(tops)[-3:]:
        lx, ly = cx + 142 * math.cos(ang), cy + 142 * math.sin(ang)
        side = "start" if math.cos(ang) > 0 else "end"
        b.append(ln(cx + 128 * math.cos(ang), cy + 128 * math.sin(ang), lx, ly, LINE2, 1))
        b.append(t(lx + (5 if side == "start" else -5), ly + 3, f"{sub} {v:.0f}", 7, MUTED, anchor=side))
    b.append(t(cx, cy - 2, "376", 14, INK, 700, anchor="middle"))
    b.append(t(cx, cy + 12, "亿元", 7, MUTED, anchor="middle"))
    b.append(t(20, 344, "内环品类、外环子类；面积按金额，小扇区不标字。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# waffle · 华夫格
# --------------------------------------------------------------------------- #
def fig_waffle() -> str:
    W, H = 640, 300
    rows = _share_rows()
    total = sum(v for _, v in rows)
    cells = []
    for i, (name, v) in enumerate(rows):
        n = round(v / total * 100)
        cells += [(i, name, v)] * n
    cells = cells[:100] + [(len(rows) - 1, "", 0)] * (100 - len(cells))
    b = svg(W, H, "品类占比华夫格")
    for k, (i, name, v) in enumerate(cells):
        r, c = divmod(k, 10)
        b.append(rc(40 + c * 22, 44 + r * 22, 19, 19, TINTS[i], rx=2))
    y = 56
    for i, (name, v) in enumerate(rows):
        b.append(rc(300, y - 9, 11, 11, TINTS[i], rx=2))
        b.append(t(318, y, name, 8.2, INK2))
        b.append(t(560, y, f"{v / total * 100:.0f}%", 8.2, INK, 600, anchor="end"))
        y += 24
    b.append(t(20, 290, "每格 = 1%，共 100 格；比饼图更容易心算。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# rose · 玫瑰图
# --------------------------------------------------------------------------- #
def fig_rose() -> str:
    W, H = 640, 340
    cx, cy = 280, 175
    rows = sorted(zip(CATS, V25), key=lambda x: -x[1])
    mx = max(v for _, v in rows)
    b = svg(W, H, "品类玫瑰图")
    for i, (name, v) in enumerate(rows):
        a0 = -math.pi / 2 + i * math.tau / len(rows) + 0.02
        a1 = -math.pi / 2 + (i + 1) * math.tau / len(rows) - 0.02
        r = 28 + 96 * math.sqrt(v / mx)
        b.append(arc(cx, cy, 18, r, a0, a1, TINTS[i]))
        mid = (a0 + a1) / 2
        b.append(t(cx + (r + 14) * math.cos(mid), cy + (r + 14) * math.sin(mid) + 3,
                   f"{name} {v:.0f}", 7.4, INK2,
                   anchor="start" if math.cos(mid) > 0 else "end"))
    b.append(t(20, 326, "半径按 √ 面积缩放，避免半径放大视觉差异。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# histogram · 直方图
# --------------------------------------------------------------------------- #
def fig_hist() -> str:
    W, H = 640, 300
    L, R, T, B = 64, 580, 46, 240
    vals = [float(v) for v in DS.TICKETS["呼和浩特"]]
    lo, hi, step = 60, 420, 30
    bins = [0] * int((hi - lo) / step)
    for v in vals:
        k = min(int((v - lo) / step), len(bins) - 1)
        bins[max(0, k)] += 1
    mx = max(bins) * 1.1
    Y = sy(0, mx, B, T)
    X = sx(lo, hi, L, R)
    b = svg(W, H, "客单价分布直方图")
    for yy in (0, 20, 40):
        if yy <= mx:
            b.append(ln(L, Y(yy), R, Y(yy), LINE, 1))
            b.append(t(L - 8, Y(yy) + 3, str(yy), 7.2, FAINT, anchor="end"))
    for i, n in enumerate(bins):
        x = X(lo + i * step)
        b.append(rc(x + 1, Y(n), X(lo + (i + 1) * step) - x - 2, B - Y(n), INK2, rx=1))
    med = median(vals)
    b.append(ln(X(med), T, X(med), B, ACCENT, 1, "3 3"))
    b.append(t(X(med) + 5, T - 6, f"中位 {med:.0f}", 7.4, ACCENT))
    for v in (100, 200, 300, 400):
        b.append(t(X(v), B + 16, str(v), 7.2, FAINT, anchor="middle"))
    b.append(t(20, 286, f"n = {len(vals)} 笔；分箱 30 元，纵轴为笔数。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# violin / ridgeline · 分布形状
# --------------------------------------------------------------------------- #
def _density(vals, x0, x1, n=90, h=28.0):
    out = []
    for i in range(n):
        x = x0 + (x1 - x0) * i / (n - 1)
        s = sum(math.exp(-0.5 * ((x - v) / h) ** 2) for v in vals)
        out.append(s / (len(vals) * h * math.sqrt(2 * math.pi)))
    return out


def fig_violin() -> str:
    W, H = 640, 380
    L, R = 96, 560
    x0, x1 = 80, 400
    X = sx(x0, x1, L, R)
    b = svg(W, H, "六城客单价小提琴")
    for i, city in enumerate(CITIES[:6]):
        vals = [float(v) for v in DS.TICKETS[city]]
        d = _density(vals, x0, x1)
        mx = max(d) or 1
        cy = 60 + i * 54
        pts_up = [(X(x0 + (x1 - x0) * k / (len(d) - 1)), cy - (v / mx) * 22) for k, v in enumerate(d)]
        pts_dn = [(x, 2 * cy - y) for x, y in pts_up]
        b.append(pa("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts_up + pts_dn[::-1]) + " Z",
                    INK2, opacity=".35"))
        b.append(ln(X(min(vals)), cy, X(max(vals)), cy, LINE2, 1))
        b.append(ci(X(median(vals)), cy, 3, ACCENT))
        b.append(t(20, cy + 4, city, 8, INK2))
        b.append(t(R + 8, cy + 4, f"{median(vals):.0f}", 7.6, INK, 600))
    b.append(t(20, 368, "形状 = 分布；红点 = 中位；横线 = 全距。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


def fig_ridge() -> str:
    W, H = 640, 360
    L, R = 96, 600
    x0, x1 = 80, 400
    X = sx(x0, x1, L, R)
    b = svg(W, H, "六城客单价山脊图")
    for i, city in enumerate(CITIES[:6]):
        vals = [float(v) for v in DS.TICKETS[city]]
        d = _density(vals, x0, x1)
        mx = max(d) or 1
        base = 268 - i * 38
        pts = [(X(x0 + (x1 - x0) * k / (len(d) - 1)), base - (v / mx) * 34) for k, v in enumerate(d)]
        b.append(pa("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                    + f" L {pts[-1][0]:.1f},{base} L {pts[0][0]:.1f},{base} Z", TINTS[i], opacity=".85"))
        b.append(t(20, base - 4, city, 7.6, INK2))
        b.append(t(R + 8, base - 4, f"{median(vals):.0f}", 7, INK, 600))
    b.append(ln(L, 280, R, 280, LINE2, 1))
    b.append(t(20, 342, "同一横轴六条密度；层叠比箱线更能看出多峰。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# bubble · 气泡（第三维）
# --------------------------------------------------------------------------- #
def fig_bubble() -> str:
    W, H = 640, 360
    L, R, T, B = 70, 590, 50, 280
    px = [float(v) for v in DS.SKU_PRICE]
    sales = [float(v) for v in DS.SKU_SALES]
    lx = [math.log10(v) for v in px]
    ly = [math.log10(v) for v in sales]
    X = sx(min(lx) * .95, max(lx) * 1.02, L, R)
    Y = sy(min(ly) * .95, math.log10(5200), B, T)
    rev = [p * s for p, s in zip(px, sales)]
    rmax = max(rev)
    b = svg(W, H, "价格销量气泡")
    for v in (100, 1000, 5000):
        b.append(ln(L, Y(math.log10(v)), R, Y(math.log10(v)), LINE, 1))
        b.append(t(L - 8, Y(math.log10(v)) + 3, f"{v:,}", 7.2, FAINT, anchor="end"))
    for v in (20, 40, 60, 80, 100):
        b.append(ln(X(math.log10(v)), T, X(math.log10(v)), B, LINE, 1))
        b.append(t(X(math.log10(v)), B + 16, str(v), 7.2, FAINT, anchor="middle"))
    for i in range(len(px)):
        r = 3 + 13 * math.sqrt(rev[i] / rmax)
        b.append(ci(X(lx[i]), Y(ly[i]), r, INK2, WHITE, 1))
    top = sorted(range(len(px)), key=lambda i: -rev[i])[:3]
    for i in top:
        b.append(t(X(lx[i]) + 14, Y(ly[i]) - 8, f"{px[i]:.0f} 元", 7.2, ACCENT))
    b.append(t(20, 346, "面积 = 销售额（价格 × 销量）；双对数轴，顶部标三个最大单品。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# parallel · 平行坐标
# --------------------------------------------------------------------------- #
def fig_parallel() -> str:
    W, H = 640, 330
    xs = [150, 330, 510]
    T, B = 60, 260
    years = [0, 1, 2]
    sums = {c: [sum(DS.MONTHLY[c][i * 12:(i + 1) * 12]) for i in years] for c in CATS}
    mn = {y: min(sums[c][y] for c in CATS) for y in years}
    mx = {y: max(sums[c][y] for c in CATS) for y in years}
    Y = lambda y, v: B - (v - mn[y]) / (mx[y] - mn[y]) * (B - T)
    b = svg(W, H, "三年平行坐标")
    for i, y in enumerate(years):
        b.append(ln(xs[i], T, xs[i], B, LINE2, 1))
        b.append(t(xs[i], B + 20, ("2023", "2024", "2025")[i], 8, INK2, 600, anchor="middle"))
        b.append(t(xs[i], T - 8, f"{mx[y]:.0f}", 7, FAINT, anchor="middle"))
        b.append(t(xs[i], B + 34, f"{mn[y]:.0f}", 7, FAINT, anchor="middle"))
    for j, cat in enumerate(CATS):
        hot = cat in ("小家电", "家居饰品")
        color = BLUE if cat == "小家电" else (ACCENT if cat == "家居饰品" else LINE2)
        pts = [(xs[i], Y(i, sums[cat][i])) for i in range(3)]
        b.append(pa("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts),
                    "none", color, 2 if hot else 1))
        if hot:
            b.append(t(xs[-1] + 8, pts[-1][1] + 4, cat, 7.6, color, 600))
    b.append(t(20, 312, "每条轴独立归一（0–1）；灰线为其余品类，避免六色。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# network · 关系网络
# --------------------------------------------------------------------------- #
def fig_network() -> str:
    W, H = 640, 340
    cx, cy, r = 310, 170, 104
    nodes = DS.NETWORK["nodes"]
    edges = DS.NETWORK["edges"]
    pos = {}
    for i, n in enumerate(nodes):
        a = -math.pi / 2 + i * math.tau / len(nodes)
        pos[n] = (cx + r * math.cos(a), cy + r * math.sin(a))
    b = svg(W, H, "品类关联网络")
    for a, bb, w in edges:
        x1, y1 = pos[a]
        x2, y2 = pos[bb]
        b.append(ln(x1, y1, x2, y2, LINE2, 1 + 4 * w))
    top2 = sorted(edges, key=lambda e: -e[2])[:3]
    for a, bb, w in top2:
        x1, y1 = pos[a]
        x2, y2 = pos[bb]
        b.append(t((x1 + x2) / 2, (y1 + y2) / 2 - 5, f"{w:.2f}", 7, ACCENT, anchor="middle", halo=True))
    for n, (x, y) in pos.items():
        b.append(ci(x, y, 17, INK2, WHITE, 2))
        b.append(t(x, y + 4, n[:2], 8.4, WHITE, 600, anchor="middle"))
        b.append(t(x, y + 32, n, 7.2, MUTED, anchor="middle"))
    b.append(t(20, 328, "线宽 = 关联强度；节点等大，不表达第三维。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)

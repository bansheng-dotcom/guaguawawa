# -*- coding: utf-8 -*-
"""flow 图型库 · 第四批：再 28 张（正负、构成、轨迹、密度、矩阵、对比）。"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from .prokit2 import (  # noqa: E402
    ACCENT, BLUE, INK, INK2, LINE, LINE2, MUTED, FAINT, WHITE,
    CATS, CITIES, TICKET, TOTAL, MONTHS, DS, blend, median,
    ci, f0, f1, ln, pa, rc, svg, sx, sy, t,
)

TINTS = ["#1F2A37", "#3D4B58", "#5C6A76", "#7B8792", "#9BA4AD", "#BCC3C9"]
RNG = random.Random(7)


def _num(v, d=1):
    return f"{v:.{d}f}"


def _deltas():
    v24 = [v / (1 + g / 100) for v, g in zip(DS.CAT_2025, DS.CAT_GROWTH)]
    return [(c, v - b) for c, v, b in zip(CATS, DS.CAT_2025, v24)]


def _store_totals():
    return [float(sum(row)) for row in DS.STORE_MATRIX]


# --------------------------------------------------------------------------- #
# 1. 正负贡献条
# --------------------------------------------------------------------------- #
def fig_diverging() -> str:
    W, H = 640, 300
    L, R = 140, 580
    rows = sorted(_deltas(), key=lambda x: x[1])
    mx = max(abs(v) for _, v in rows) * 1.35
    X = sx(-mx, mx, L + 70, R - 70)
    zero = X(0)
    b = svg(W, H, "正负贡献条")
    b.append(ln(zero, 36, zero, 250, LINE2, 1))
    for i, (name, v) in enumerate(rows):
        y = 50 + i * 30
        b.append(t(L - 8, y + 4, name, 8, INK2, anchor="end"))
        b.append(rc(min(zero, X(v)), y - 8, max(abs(X(v) - zero), 2), 16,
                    BLUE if v > 0 else ACCENT, rx=1.5))
        b.append(t(max(zero, X(v)) + 7, y + 4, f"{v:+.1f}", 7.8, INK, 600))
    b.append(t(20, 286, "以 0 为轴：正负一眼分开，不用看颜色也能读方向。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 2. 堆叠面积
# --------------------------------------------------------------------------- #
def fig_stack_area() -> str:
    W, H = 640, 330
    L, R, T, B = 64, 520, 48, 266
    series = {c: [DS.MONTHLY[c][i] for i in range(36)] for c in CATS}
    totals = [sum(series[c][i] for c in CATS) for i in range(36)]
    mx = max(totals) * 1.05
    X = sx(0, 35, L + 4, R)
    Y = sy(0, mx, B, T)
    b = svg(W, H, "品类堆叠面积")
    cum = [0.0] * 36
    for j, cat in enumerate(CATS):
        top = [cum[i] + series[cat][i] for i in range(36)]
        d = (f"M {X(0):.1f},{Y(cum[0]):.1f} " +
             " ".join(f"L {X(i):.1f},{Y(top[i]):.1f}" for i in range(36)) +
             " " + " ".join(f"L {X(i):.1f},{Y(cum[i]):.1f}" for i in range(35, -1, -1)) + " Z")
        b.append(pa(d, TINTS[j], opacity=".85"))
        b.append(t(R + 6, Y((top[-1] + cum[-1]) / 2) + 3, cat, 7, MUTED))
        cum = top
    for i in range(0, 36, 6):
        b.append(t(X(i), B + 16, MONTHS[i], 6.8, FAINT, anchor="middle"))
    b.append(t(20, 316, "堆叠面积 = 总量 + 构成；只看结构，不读单点。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 3. 多系列线
# --------------------------------------------------------------------------- #
def fig_multi_line() -> str:
    W, H = 640, 320
    L, R, T, B = 64, 560, 48, 256
    Y = sy(0, 10, B, T)
    X = sx(0, 35, L + 4, R)
    b = svg(W, H, "三品类月度折线")
    for v in (0, 2.5, 5, 7.5, 10):
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, f"{v:g}", 7.2, FAINT, anchor="end"))
    for cat, color in (("家纺布艺", INK2), ("小家电", BLUE), ("家居饰品", ACCENT)):
        s = DS.MONTHLY[cat]
        b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(s)),
                    "none", color, 1.8))
        b.append(t(R + 6, Y(s[-1]) + 3, cat, 7.2, color, 600))
    b.append(t(20, 306, "三系列、同单位、≤3 条：不用图例，末端直标。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 4. 轨迹散点（connected scatter）
# --------------------------------------------------------------------------- #
def fig_connected() -> str:
    W, H = 640, 340
    L, R, T, B = 64, 560, 48, 268
    pts = []
    for i in range(12, 36):
        yoy = (TOTAL[i] / TOTAL[i - 12] - 1) * 100
        pts.append((yoy, TOTAL[i]))
    X = sx(-8, 12, L, R)
    Y = sy(18, 42, B, T)
    b = svg(W, H, "同比与规模的轨迹")
    for v in (20, 30, 40):
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, str(v), 7.2, FAINT, anchor="end"))
    b.append(ln(X(0), T, X(0), B, LINE2, 1))
    b.append(t(X(0) + 4, B + 14, "同比 0%", 7, FAINT))
    d = "M " + " L ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in pts)
    b.append(pa(d, "none", INK2, 1.4))
    for i, (x, y) in enumerate(pts):
        b.append(ci(X(x), Y(y), 2.6, INK2))
    b.append(ci(X(pts[-1][0]), Y(pts[-1][1]), 4.4, ACCENT))
    b.append(t(X(pts[-1][0]) + 8, Y(pts[-1][1]) + 4, "最新", 7.4, ACCENT, 600))
    b.append(t(20, 326, "轨迹散点：每个点是「同比 × 规模」，顺序就是时间。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 5. 四象限散点
# --------------------------------------------------------------------------- #
def fig_quadrant() -> str:
    W, H = 640, 360
    L, R, T, B = 70, 590, 48, 282
    sizes = [float(v) for v in DS.STORE_SIZE]
    sales = _store_totals()
    mx, my = sum(sizes) / len(sizes), sum(sales) / len(sales)
    X = sx(min(sizes) * .85, max(sizes) * 1.05, L, R)
    Y = sy(min(sales) * .9, max(sales) * 1.05, B, T)
    b = svg(W, H, "门店四象限")
    b.append(ln(X(mx), T, X(mx), B, LINE2, 1, "3 3"))
    b.append(ln(L, Y(my), R, Y(my), LINE2, 1, "3 3"))
    b.append(t(20, 40, "规模小 / 销售高", 6.8, FAINT))
    b.append(t(R, 40, "规模大 / 销售高", 6.8, FAINT, anchor="end"))
    b.append(t(20, B + 16, "规模小 / 销售低", 6.8, FAINT))
    b.append(t(R, B + 16, "规模大 / 销售低", 6.8, FAINT, anchor="end"))
    for v in (300, 500, 700):
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, str(v), 7, FAINT, anchor="end"))
    for v in (0.5, 1.0, 1.5):
        b.append(t(X(v), B + 18, f"{v:g}", 7, FAINT, anchor="middle"))
    top = sorted(range(len(sales)), key=lambda i: -sales[i])[:3]
    for i, (x, y) in enumerate(zip(sizes, sales)):
        hot = i in top
        b.append(ci(X(x), Y(y), 5 if hot else 3.4, ACCENT if hot else INK2))
        if hot:
            b.append(t(X(x) + 8, Y(y) + 4, DS.STORES[i], 7, INK2, halo=True))
    b.append(t(20, 344, "x = 门店规模系数，y = 销售额；虚线是均值分割。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 6. 表格 + 迷你线（spark table）
# --------------------------------------------------------------------------- #
def fig_spark() -> str:
    W, H = 640, 300
    L, R = 110, 470
    b = svg(W, H, "品类迷你线表格")
    b.append(t(20, 34, "品类", 7.6, FAINT))
    b.append(t(R + 40, 34, "36 个月走势", 7.6, FAINT))
    b.append(t(560, 34, "2025", 7.6, FAINT, anchor="end"))
    for i, cat in enumerate(sorted(CATS, key=lambda c: -DS.CAT_2025[CATS.index(c)])):
        y = 56 + i * 34
        s = DS.MONTHLY[cat]
        mn, mxv = min(s), max(s)
        X = sx(0, 35, L, R)
        Y = sy(mn * .95, mxv * 1.05, y + 12, y - 12)
        b.append(t(20, y + 4, cat, 8, INK2))
        b.append(pa("M " + " L ".join(f"{X(k):.1f},{Y(v):.1f}" for k, v in enumerate(s)),
                    "none", INK2, 1.2))
        b.append(ci(X(35), Y(s[-1]), 2.8, ACCENT))
        b.append(t(560, y + 4, f"{DS.CAT_2025[CATS.index(cat)]:.1f}", 8, INK, 600, anchor="end"))
    b.append(t(20, 286, "表格里塞进走势：一行一个对象，扫读时不必翻图。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 7. 六宫格小倍数
# --------------------------------------------------------------------------- #
def fig_small6() -> str:
    W, H = 640, 400
    b = svg(W, H, "六品类小倍数")
    for i, cat in enumerate(CATS):
        col, row = i % 2, i // 2
        x0 = 40 + col * 290
        y0 = 40 + row * 112
        s = DS.MONTHLY[cat]
        X = sx(0, 35, x0, x0 + 250)
        Y = sy(0, 10, y0 + 78, y0 + 8)
        b.append(pa("M " + " L ".join(f"{X(k):.1f},{Y(v):.1f}" for k, v in enumerate(s)),
                    "none", INK2, 1.2))
        b.append(t(x0, y0, cat, 7.6, INK2, 600))
        b.append(t(x0 + 250, y0, f"{s[-1]:.1f}", 7.6, INK, 600, anchor="end"))
        b.append(ln(x0, y0 + 78, x0 + 250, y0 + 78, LINE2, 1))
    b.append(t(20, 386, "6 格共享 0–10 纵轴；每一格只回答「这条线怎么走」。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 8. 年 × 月热力
# --------------------------------------------------------------------------- #
def fig_ym_heat() -> str:
    W, H = 640, 300
    L, T = 70, 46
    cw, ch = 40, 56
    vals = [[TOTAL[y * 12 + m] for m in range(12)] for y in range(3)]
    mx = max(max(r) for r in vals)
    b = svg(W, H, "年 × 月热力")
    for m in range(12):
        b.append(t(L + m * cw + cw / 2, T - 10, f"{m + 1}", 7, FAINT, anchor="middle"))
    for y in range(3):
        b.append(t(L - 10, T + y * ch + 34, f"{2023 + y}", 7.4, INK2, anchor="end"))
        for m in range(12):
            v = vals[y][m]
            b.append(rc(L + m * cw + 1, T + y * ch + 1, cw - 2, ch - 2, blend(v / mx)))
            b.append(t(L + m * cw + cw / 2, T + y * ch + 34, f"{v:.0f}", 6.8,
                       WHITE if v / mx > .55 else INK2, anchor="middle"))
    b.append(t(20, 286, "行 = 年、列 = 月；色与数字同一口径。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 9. 累计曲线
# --------------------------------------------------------------------------- #
def fig_cumulative() -> str:
    W, H = 640, 300
    L, R, T, B = 64, 580, 48, 240
    cum, run = [], 0.0
    for v in TOTAL:
        run += v
        cum.append(run)
    Y = sy(0, cum[-1] * 1.06, B, T)
    X = sx(0, 35, L + 4, R)
    b = svg(W, H, "累计规模")
    for v in (0, 400, 800, 1200):
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, str(v), 7.2, FAINT, anchor="end"))
    b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(cum)),
                "none", INK2, 1.8))
    b.append(t(X(35) - 4, Y(cum[-1]) - 8, f"{cum[-1]:,.0f}", 8.4, INK, 700, anchor="end", halo=True))
    b.append(t(20, 286, "累计曲线回答「到此刻一共多少」，不替代月度图。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 10. Marimekko（宽度=总量，内部=构成）
# --------------------------------------------------------------------------- #
def fig_marimekko() -> str:
    W, H = 640, 320
    L, R, T, B = 50, 590, 50, 264
    years = [0, 1, 2]
    sums = {c: [sum(DS.MONTHLY[c][i * 12:(i + 1) * 12]) for i in years] for c in CATS}
    totals = [sum(sums[c][y] for c in CATS) for y in years]
    mx = sum(totals)
    x = L
    b = svg(W, H, "三年 Marimekko")
    for y in range(3):
        w = (R - L) * totals[y] / mx
        acc = 0
        for j, cat in enumerate(CATS):
            v = sums[cat][y]
            h = (B - T) * v / totals[y]
            y0 = B - acc - h
            b.append(rc(x + 1, y0 + 1, w - 2, h - 2, TINTS[j], rx=1))
            if h > 26 and w > 46:
                b.append(t(x + w / 2, y0 + h / 2 + 3, f"{v:.0f}", 7.4, WHITE, 600, anchor="middle"))
            acc += h
        b.append(t(x + w / 2, B + 16, ("2023", "2024", "2025")[y], 8, INK2, 600, anchor="middle"))
        b.append(t(x + w / 2, T - 8, f"{totals[y]:.0f}", 7.4, FAINT, anchor="middle"))
        x += w
    b.append(t(20, 306, "宽度 = 当年总量，内部高度 = 品类占比；两维一起读。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 11. 箱线 + 散点
# --------------------------------------------------------------------------- #
def fig_box_jitter() -> str:
    W, H = 640, 320
    L, R = 90, 580
    X = sx(60, 420, L, R)
    b = svg(W, H, "箱线叠加散点")
    for v in (100, 200, 300, 400):
        b.append(ln(X(v), 40, X(v), 262, LINE, 1))
        b.append(t(X(v), 278, str(v), 7.2, FAINT, anchor="middle"))
    for i, city in enumerate(CITIES[:6]):
        vals = [float(v) for v in DS.TICKETS[city]]
        y = 60 + i * 34
        q1, q3, med = sorted(vals)[len(vals) // 4], sorted(vals)[3 * len(vals) // 4], median(vals)
        b.append(t(20, y + 4, city, 7.8, INK2))
        b.append(rc(X(q1), y - 5, X(q3) - X(q1), 10, INK2, opacity=".25", rx=1))
        b.append(ln(X(med), y - 7, X(med), y + 7, INK, 1.6))
        for v in vals[::12]:
            b.append(ci(X(float(v)), y + RNG.uniform(-3, 3), 1.6, INK2, opacity=".5"))
    b.append(t(20, 306, "箱给区间，点给密度：两件事一张图说完。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 12. 区间 + 中位
# --------------------------------------------------------------------------- #
def fig_range_median() -> str:
    W, H = 640, 300
    L, R = 110, 580
    X = sx(60, 420, L, R)
    b = svg(W, H, "区间与中位")
    for v in (100, 200, 300, 400):
        b.append(ln(X(v), 40, X(v), 250, LINE, 1))
        b.append(t(X(v), 266, str(v), 7.2, FAINT, anchor="middle"))
    for i, city in enumerate(CITIES[:6]):
        vals = [float(v) for v in DS.TICKETS[city]]
        y = 58 + i * 30
        b.append(t(20, y + 4, city, 7.8, INK2))
        b.append(ln(X(min(vals)), y, X(max(vals)), y, LINE2, 3, cap="round"))
        b.append(ci(X(median(vals)), y, 4.6, ACCENT))
        b.append(t(min(X(max(vals)) + 8, 566), y + 4, f"{median(vals):.0f}", 7.4, INK, 600))
    b.append(t(20, 288, "线 = 全距，点 = 中位；比箱线更轻，适合 6 组以内。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 13. 多指标子弹图
# --------------------------------------------------------------------------- #
def fig_bullet_multi() -> str:
    W, H = 640, 280
    L, R = 150, 570
    rows = [("规模（亿元）", 376.3, 420, 400), ("客单价（元）", 188, 200, 195),
            ("复购率（%）", 34, 40, 38)]
    b = svg(W, H, "三指标对目标")
    for i, (name, v, target, good) in enumerate(rows):
        y = 60 + i * 60
        mx = target * 1.15
        X = sx(0, mx, L, R)
        b.append(t(20, y + 4, name, 7.8, INK2))
        b.append(rc(L, y - 10, R - L, 20, LINE2, opacity=".25", rx=2))
        b.append(rc(L, y - 7, X(good) - L, 14, BLUE, opacity=".10", rx=2))
        b.append(rc(L, y - 5, X(v) - L, 10, ACCENT if v < target else INK2, rx=1))
        b.append(ln(X(target), y - 12, X(target), y + 12, INK, 1.6))
        b.append(t(X(target) + 4, y - 14, f"目标 {target:g}", 7, MUTED))
        b.append(t(X(v) + 6, y + 4, f"{v:g}", 7.4, INK, 600))
    b.append(t(20, 266, "三条各自的目标带；黑线是目标，浅蓝是达成区。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 14. 误差条（值 ± CI）
# --------------------------------------------------------------------------- #
def fig_bar_ci() -> str:
    W, H = 640, 300
    L, R = 110, 580
    X = sx(0, 110, L, R)
    ci_fake = [4.2, 3.1, 5.5, 2.4, 3.8, 1.9]
    b = svg(W, H, "品类与置信区间")
    for v in (0, 25, 50, 75, 100):
        b.append(ln(X(v), 40, X(v), 250, LINE, 1))
        b.append(t(X(v), 266, str(v), 7.2, FAINT, anchor="middle"))
    for i, cat in enumerate(CATS):
        y = 56 + i * 32
        v = DS.CAT_2025[i]
        b.append(t(20, y + 4, cat, 8, INK2))
        b.append(ln(X(v - ci_fake[i]), y, X(v + ci_fake[i]), y, INK2, 1.6))
        b.append(ln(X(v - ci_fake[i]), y - 4, X(v - ci_fake[i]), y + 4, INK2, 1.2))
        b.append(ln(X(v + ci_fake[i]), y - 4, X(v + ci_fake[i]), y + 4, INK2, 1.2))
        b.append(ci(X(v), y, 4.4, ACCENT))
        b.append(t(X(v + ci_fake[i]) + 8, y + 4, f"{v:.1f}", 7.4, INK, 600))
    b.append(t(20, 288, "点 = 估计值，横线 = ±CI；没有区间就不该下确定性结论。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 15. 百分比横条（3 年 × 6 品类）
# --------------------------------------------------------------------------- #
def fig_pct_hbar() -> str:
    W, H = 640, 300
    L, R = 80, 590
    sums = {c: [sum(DS.MONTHLY[c][i * 12:(i + 1) * 12]) for i in range(3)] for c in CATS}
    totals = [sum(sums[c][y] for c in CATS) for y in range(3)]
    b = svg(W, H, "三年 100% 横条")
    for y in range(3):
        yy = 64 + y * 60
        x = L
        for j, cat in enumerate(CATS):
            w = (R - L) * sums[cat][y] / totals[y]
            b.append(rc(x, yy, w, 34, TINTS[j], stroke=WHITE, sw=1))
            if w > 48:
                b.append(t(x + w / 2, yy + 22, f"{sums[cat][y] / totals[y] * 100:.0f}%", 7.6, WHITE, 600, anchor="middle"))
            x += w
        b.append(t(L - 20, yy + 22, ("2023", "2024", "2025")[y], 7.8, INK2, anchor="end"))
    b.append(t(20, 286, "每年一条，合计各自 100%；行间可直接比结构。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 16. 阶梯线
# --------------------------------------------------------------------------- #
def fig_step() -> str:
    W, H = 640, 300
    L, R, T, B = 64, 580, 48, 240
    Y = sy(18, 42, B, T)
    X = sx(0, 35, L + 4, R)
    b = svg(W, H, "价格/政策步进")
    for v in (20, 30, 40):
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, str(v), 7.2, FAINT, anchor="end"))
    for i in (11, 23):
        b.append(ln(X(i), T, X(i), B, ACCENT, 1, "3 3"))
        b.append(t(X(i) + 4, T + 10, ("调价 A", "调价 B")[i == 23], 7, ACCENT))
    pts = []
    for i, v in enumerate(TOTAL):
        pts.append((X(i), Y(v)))
    d = f"M {pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(1, len(pts)):
        d += f" L {pts[i][0]:.1f},{pts[i - 1][1]:.1f} L {pts[i][0]:.1f},{pts[i][1]:.1f}"
    b.append(pa(d, "none", INK2, 1.6))
    b.append(t(20, 286, "阶梯线：值只在事件点跳变，不画成连续趋势。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 17. 区间带（min–max envelope）
# --------------------------------------------------------------------------- #
def fig_area_range() -> str:
    W, H = 640, 300
    L, R, T, B = 64, 580, 48, 240
    X = sx(0, 35, L + 4, R)
    lo = [min(DS.MONTHLY[c][i] for c in CATS) for i in range(36)]
    hi = [max(DS.MONTHLY[c][i] for c in CATS) for i in range(36)]
    Y = sy(0, 10, B, T)
    b = svg(W, H, "品类极差带")
    d = ("M " + " L ".join(f"{X(i):.1f},{Y(hi[i]):.1f}" for i in range(36)) +
         " " + " ".join(f"L {X(i):.1f},{Y(lo[i]):.1f}" for i in range(35, -1, -1)) + " Z")
    b.append(pa(d, BLUE, opacity=".12"))
    b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(hi[i]):.1f}" for i in range(36)), "none", BLUE, 1.2))
    b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(lo[i]):.1f}" for i in range(36)), "none", INK2, 1.2))
    for v in (0, 5, 10):
        b.append(t(L - 8, Y(v) + 3, str(v), 7.2, FAINT, anchor="end"))
    b.append(t(20, 286, "带 = 六品类的最高/最低；看图先看带宽，再看中线。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 18. 蜡烛 + 成交量
# --------------------------------------------------------------------------- #
def fig_candle_vol() -> str:
    W, H = 640, 380
    L, R = 60, 590
    O = DS.OHLC
    lo, hi = float(O[:, 2].min()) - 1, float(O[:, 1].max()) + 1
    Y = sy(lo, hi, 180, 44)
    slot = (R - L) / len(O)
    bw = slot * 0.56
    b = svg(W, H, "蜡烛与成交量")
    for v in (96, 98, 100, 102):
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, str(v), 7, FAINT, anchor="end"))
    for i, (o, h, l, c) in enumerate(O):
        cx = L + slot * i + slot / 2
        color = BLUE if c >= o else ACCENT
        b.append(ln(cx, Y(h), cx, Y(l), color, 1))
        b.append(rc(cx - bw / 2, Y(max(o, c)), bw, max(abs(Y(o) - Y(c)), 1.5), color, rx=1))
    vol = [abs(c - o) + (h - l) * .5 for o, h, l, c in O]
    mv = max(vol)
    for i, v in enumerate(vol):
        cx = L + slot * i + slot / 2
        h = 70 * v / mv
        b.append(rc(cx - bw / 2, 340 - h, bw, h, LINE2, rx=1))
    b.append(t(20, 300, "价", 7, FAINT))
    b.append(t(20, 358, "量", 7, FAINT))
    b.append(t(20, 372, "量 = |收-开| + 振幅/2，示意口径。", 7, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 19. KPI + 迷你线
# --------------------------------------------------------------------------- #
def fig_kpi_spark() -> str:
    W, H = 640, 260
    b = svg(W, H, "三 KPI 与走势")
    last12 = TOTAL[-12:]
    items = [("376.3", "2025 规模", "+6.9%", last12),
             ("33.9", "最新月度", f"{(TOTAL[-1] / TOTAL[-2] - 1) * 100:+.1f}%", last12),
             ("1.2%", "近 12 月同比", "—", [TOTAL[i] / TOTAL[i - 12] * 100 for i in range(24, 36)])]
    for i, (v, lab, delta, series) in enumerate(items):
        x = 24 + i * 204
        b.append(t(x, 54, v, 24, INK, 700))
        b.append(t(x, 72, lab, 8, MUTED))
        b.append(t(x, 88, delta, 7.6, ACCENT if str(delta).startswith("-") else MUTED))
        lo, hi2 = min(series), max(series)
        X = sx(0, len(series) - 1, x, x + 170)
        Y = sy(lo, hi2 or lo + 1, 200, 150)
        b.append(pa("M " + " L ".join(f"{X(k):.1f},{Y(val):.1f}" for k, val in enumerate(series)),
                    "none", INK2, 1.2))
    b.append(t(20, 240, "数字 + 走势：KPI 不做孤零零的大字报。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 20. 蜂群图（beeswarm）
# --------------------------------------------------------------------------- #
def fig_beeswarm() -> str:
    W, H = 640, 280
    L, R = 60, 600
    vals = [float(v) for v in DS.TICKETS["呼和浩特"]]
    X = sx(60, 420, L, R)
    bins = {}
    b = svg(W, H, "客单价蜂群")
    for v in vals:
        k = int(v // 8)
        n = bins.get(k, 0)
        bins[k] = n + 1
        y = 150 - ((n % 7) * 7 - 21) * (1 if (n // 7) % 2 == 0 else -1)
        b.append(ci(X(v), y, 2.4, INK2, opacity=".55"))
    b.append(ln(L, 214, R, 214, LINE2, 1))
    for v in (100, 200, 300, 400):
        b.append(t(X(v), 230, str(v), 7.2, FAINT, anchor="middle"))
    b.append(t(20, 262, f"n = {len(vals)}；同值堆叠成蜂群，分布不丢点。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 21. 棒棒糖 + CI
# --------------------------------------------------------------------------- #
def fig_lollipop_ci() -> str:
    W, H = 640, 300
    L, R = 190, 560
    X = sx(-4, 7, L, R)
    b = svg(W, H, "效应与区间")
    b.append(ln(X(0), 40, X(0), 250, LINE2, 1))
    b.append(t(X(0), 32, "0", 7, MUTED, anchor="middle"))
    for i, (name, eff, lo, hi, n) in enumerate(DS.EFFECTS):
        y = 60 + i * 36
        sig = lo > 0 or hi < 0
        color = BLUE if (sig and eff > 0) else (ACCENT if sig else MUTED)
        b.append(t(20, y + 4, name, 7.8, INK2))
        b.append(ln(X(lo), y, X(hi), y, color, 1.4))
        b.append(ln(X(0), y, X(eff), y, color, 1.4))
        b.append(ci(X(eff), y, 4.6, color))
        b.append(t(X(hi) + 8, y + 4, f"{eff:+.1f}", 7.4, INK, 600))
    b.append(t(20, 286, "茎从 0 长到估计值，横线是 CI；跨 0 即不可宣称有效。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 22. 点阵矩阵（替代热力）
# --------------------------------------------------------------------------- #
def fig_dot_matrix() -> str:
    W, H = 640, 380
    L, T = 120, 56
    cw, ch = 80, 28
    M = DS.STORE_MATRIX
    mx = float(M.max())
    b = svg(W, H, "门店 × 品类点阵")
    for j, cat in enumerate(CATS):
        b.append(t(L + j * cw + cw / 2, T - 10, cat[:4], 7, MUTED, anchor="middle"))
    for i, store in enumerate(DS.STORES):
        y = T + i * ch + ch / 2
        b.append(t(L - 10, y + 3, store, 7, INK2, anchor="end"))
        for j in range(len(CATS)):
            v = float(M[i][j])
            b.append(ci(L + j * cw + cw / 2, y, 2 + 7 * math.sqrt(v / mx), INK2, opacity=".45"))
    b.append(t(20, 362, "圆面积 = 销售额；比热力更轻，能看清「大小」而不是「深浅」。", 7.4, MUTED))
    b.append(t(600, 56, "38", 7, FAINT, anchor="end"))
    b.append(t(600, 168, "18", 7, FAINT, anchor="end"))
    b.append(t(600, 280, "7", 7, FAINT, anchor="end"))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 23. 三城直方图（小倍数）
# --------------------------------------------------------------------------- #
def fig_hist_multi() -> str:
    W, H = 640, 380
    b = svg(W, H, "三城客单价直方图")
    for k, city in enumerate(("呼和浩特", "包头", "赤峰")):
        vals = [float(v) for v in DS.TICKETS[city]]
        lo, hi, step = 60, 420, 30
        bins = [0] * 12
        for v in vals:
            bins[min(int((v - lo) / step), 11)] += 1
        mx = max(bins)
        y0 = 50 + k * 106
        X = sx(lo, hi, 60, 560)
        for i, n in enumerate(bins):
            x = X(lo + i * step)
            h = 66 * n / mx
            b.append(rc(x + 1, y0 + 66 - h, X(lo + (i + 1) * step) - x - 2, h, INK2, rx=1))
        b.append(t(20, y0 + 10, city, 7.4, INK2, 600))
        b.append(ln(60, y0 + 66, 560, y0 + 66, LINE2, 1))
        for v in (100, 200, 300, 400):
            b.append(t(X(v), y0 + 80, str(v), 6.6, FAINT, anchor="middle"))
    b.append(t(20, 370, "三城共用横轴与分箱；只比形状，不比绝对高度。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 24. 散点 + 拟合带
# --------------------------------------------------------------------------- #
def fig_scatter_band() -> str:
    W, H = 640, 340
    L, R, T, B = 70, 580, 50, 270
    px = [float(v) for v in DS.SKU_PRICE]
    py = [float(v) for v in DS.SKU_SALES]
    lx, ly = [math.log10(v) for v in px], [math.log10(v) for v in py]
    X = sx(min(lx) * .95, max(lx) * 1.02, L, R)
    Y = sy(min(ly) * .95, max(ly) * 1.05, B, T)
    b = svg(W, H, "价格销量与拟合带")
    for v in (20, 40, 60, 80, 100):
        b.append(t(X(math.log10(v)), B + 16, str(v), 7, FAINT, anchor="middle"))
    for v in (100, 1000, 5000):
        b.append(ln(L, Y(math.log10(v)), R, Y(math.log10(v)), LINE, 1))
        b.append(t(L - 8, Y(math.log10(v)) + 3, f"{v:,}", 7, FAINT, anchor="end"))
    k, c0 = -0.72, math.log10(24000)
    band = []
    for sign in (1, -1):
        pts = []
        for i in range(40):
            x = min(lx) + (max(lx) - min(lx)) * i / 39
            pts.append((X(x), Y(k * x + c0 + sign * 0.12)))
        band.append(pts)
    d = ("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in band[0]) +
         " " + " ".join(f"L {x:.1f},{y:.1f}" for x, y in band[1][::-1]) + " Z")
    b.append(pa(d, BLUE, opacity=".10"))
    b.append(pa(f"M {X(min(lx)):.1f},{Y(k*min(lx)+c0):.1f} L {X(max(lx)):.1f},{Y(k*max(lx)+c0):.1f}",
                "none", BLUE, 1.4, "4 3"))
    for i in range(len(px)):
        b.append(ci(X(lx[i]), Y(ly[i]), 2.8, INK2))
    b.append(t(20, 326, "拟合线加 ±带：点落在带外才是异常，不是凭感觉。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 25. 里程碑时间轴
# --------------------------------------------------------------------------- #
def fig_timeline() -> str:
    W, H = 640, 260
    L, R = 60, 590
    X = sx(0, 90, L, R)
    b = svg(W, H, "项目里程碑")
    b.append(ln(L, 130, R, 130, LINE2, 1.4))
    for d in (0, 30, 60, 90):
        b.append(ln(X(d), 126, X(d), 134, LINE2, 1))
        b.append(t(X(d), 150, f"D{d}", 7, FAINT, anchor="middle"))
    for i, (d, name) in enumerate(DS.MILESTONES):
        y = 96 if i % 2 == 0 else 164
        b.append(ln(X(d), 130, X(d), y + (6 if i % 2 == 0 else -6), INK2, 1))
        b.append(ci(X(d), 130, 4, ACCENT))
        b.append(t(X(d), y, name, 7.6, INK2, 600, anchor="middle"))
    b.append(t(20, 236, "里程碑：只标节点，不画工期；工期图见甘特。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 26. 双漏斗对比
# --------------------------------------------------------------------------- #
def fig_funnel_cmp() -> str:
    W, H = 640, 340
    stages = DS.FUNNEL
    b = svg(W, H, "两期漏斗对比")
    for k, (label, scale) in enumerate((("2024", 0.86), ("2025", 1.0))):
        x0 = 80 + k * 300
        for i, (name, v) in enumerate(stages):
            vv = v * scale
            w = 30 + 180 * (vv / stages[0][1]) ** 0.45
            y = 54 + i * 52
            b.append(rc(x0 + (200 - w) / 2, y, w, 34, ACCENT if k == 1 else LINE2,
                        opacity=".9" if k == 1 else ".5", rx=1))
            b.append(t(x0 + 100, y + 21, f"{name} {vv:,.0f}" if vv >= 1000 else f"{name} {vv:.2f} 万",
                       7.2, WHITE if k == 1 else INK2, anchor="middle"))
        b.append(t(x0 + 100, 324, label, 8, INK2, 600, anchor="middle"))
    b.append(t(20, 330, "同尺并排：只比形状与转化率，宽度按 √ 缩放。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 27. 仪表 + 上期标记
# --------------------------------------------------------------------------- #
def fig_gauge_delta() -> str:
    W, H = 640, 300
    cx, cy, r = 320, 210, 118
    v, prev, target = 376.3, 352.1, 420
    pct = v / target
    b = svg(W, H, "仪表与上期")
    b.append(f'<path d="M {cx-r},{cy} A {r},{r} 0 0 1 {cx+r},{cy}" fill="none" stroke="{LINE2}" stroke-width="16"/>')
    a = math.pi + math.pi * min(pct, 1)
    x1, y1 = cx + r * math.cos(a), cy + r * math.sin(a)
    b.append(f'<path d="M {cx-r},{cy} A {r},{r} 0 0 1 {x1:.1f},{y1:.1f}" fill="none" stroke="{ACCENT}" stroke-width="16"/>')
    ap = math.pi + math.pi * (prev / target)
    b.append(ln(cx + (r - 18) * math.cos(ap), cy + (r - 18) * math.sin(ap),
                cx + (r + 18) * math.cos(ap), cy + (r + 18) * math.sin(ap), INK, 1.6))
    b.append(t(cx, cy - 44, f"{pct * 100:.0f}%", 34, INK, 700, anchor="middle"))
    b.append(t(cx, cy - 16, f"{v} / {target} 亿元；上期 {prev}", 8.2, MUTED, anchor="middle"))
    b.append(t(cx - r, cy + 16, "0%", 7, FAINT, anchor="middle"))
    b.append(t(cx + r, cy + 16, "100%", 7, FAINT, anchor="middle"))
    b.append(t(20, 286, "黑刻度 = 上期；两个时点同尺，避免「进步感」造假。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 28. 双华夫格
# --------------------------------------------------------------------------- #
def fig_waffle_cmp() -> str:
    W, H = 640, 300
    rows = sorted(zip(CATS, DS.CAT_2025), key=lambda x: -x[1])
    total = sum(v for _, v in rows)
    b = svg(W, H, "两年华夫格")
    for k, (label, shift) in enumerate((("2023", -0.03), ("2025", 0.0))):
        x0 = 40 + k * 300
        cells = []
        for i, (_, v) in enumerate(rows):
            n = round(v / total * 100 * (1 + shift * (i - 2)))
            cells += [i] * max(n, 0)
        cells = cells[:100] + [len(rows) - 1] * (100 - len(cells))
        for n, idx in enumerate(cells):
            r_, c_ = divmod(n, 10)
            b.append(rc(x0 + c_ * 18, 60 + r_ * 18, 15, 15, TINTS[idx % 6], rx=2))
        b.append(t(x0 + 90, 262, label, 8, INK2, 600, anchor="middle"))
    b.append(t(20, 288, "两格同尺：每格 1%，肉眼能比出结构变化。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)

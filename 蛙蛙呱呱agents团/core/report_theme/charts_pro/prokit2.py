# -*- coding: utf-8 -*-
"""prokit2 —— flow 版式内的高级图表原语 + 18 张样张。

设计约束（与 core/report_theme/kit.py 同一套 token）：
- 640 宽坐标系（A4 图卡 174mm ≈ 658px），打印缩放后字号仍 ≥7px；
- 一个强调色（红 #C0392B），蓝只用于"正向/第二系列"，灰只做上下文；
- 无外框、无纵向网格、无图例；值直标；差值用括号；结论在页面图题里。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ...charts import dataset as DS  # noqa: E402

INK, INK2, MUTED, FAINT = "#1F2A37", "#33424F", "#66737F", "#98A2AC"
LINE, LINE2 = "#E3E5E8", "#C9D0D6"
ACCENT, BLUE, WHITE = "#C0392B", "#2E6F9E", "#FFFFFF"

CATS = DS.CATS
V25 = list(DS.CAT_2025)
G = list(DS.CAT_GROWTH)
V24 = [round(v / (1 + g / 100), 1) for v, g in zip(V25, G)]
CITIES = DS.CITIES
TICKET = list(DS.CITY_TICKET)
MONTHS = DS.MONTHS
TOTAL = list(DS.MONTH_TOTAL)


# --------------------------------------------------------------------------- #
# 基元
# --------------------------------------------------------------------------- #
def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def f1(v) -> str:
    return f"{v:.1f}"


def f0(v) -> str:
    return f"{v:,.0f}"


def t(x, y, s, size=8.6, fill=INK, fw=400, anchor="start", halo=False, ls=None) -> str:
    a = (f'x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
         f'text-anchor="{anchor}" font-weight="{fw}"')
    if ls:
        a += f' letter-spacing="{ls}"'
    if halo:
        a += ' paint-order="stroke" stroke="#FFFFFF" stroke-width="3" stroke-linejoin="round"'
    return f"<text {a}>{esc(s)}</text>"


def ln(x1, y1, x2, y2, stroke=LINE, w=1, dash=None, cap="butt") -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{w}" stroke-linecap="{cap}"{d}/>')


def rc(x, y, w, h, fill, rx=0, stroke=None, sw=1, opacity=None) -> str:
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o = f' opacity="{opacity}"' if opacity is not None else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="{rx}" fill="{fill}"{s}{o}/>')


def ci(cx, cy, r, fill, stroke=None, sw=1, opacity=None) -> str:
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}"{s}{o}/>'


def pa(d, fill="none", stroke=None, w=1, dash=None, opacity=None) -> str:
    s = f' stroke="{stroke}" stroke-width="{w}"' if stroke else ""
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    o = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<path d="{d}" fill="{fill}"{s}{ds}{o}/>'


def sx(lo, hi, a, b):
    return lambda v: a + (v - lo) / (hi - lo) * (b - a)


def sy(lo, hi, b, top):
    return lambda v: b - (v - lo) / (hi - lo) * (b - top)


def svg(w, h, label) -> list[str]:
    return [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{esc(label)}" preserveAspectRatio="xMidYMid meet">']


def grid(b, vals, x1, x2, Y, fmt=f1, label_x=None) -> None:
    for v in vals:
        y = Y(v)
        b.append(ln(x1, y, x2, y, LINE, 1))
        b.append(t((label_x if label_x is not None else x1 - 8), y + 3, fmt(v), 7.4, FAINT,
                   anchor="end"))


def axis_x(b, xs, labels, y, size=7.4, color=FAINT) -> None:
    for x, lab in zip(xs, labels):
        b.append(ln(x, y, x, y + 4, LINE2, 1))
        b.append(t(x, y + 16, lab, size, color, anchor="middle"))


def bracket(b, x1, x2, y, label, color=ACCENT, size=7.8, drop=5, dy=-6) -> None:
    b.append(ln(x1, y, x2, y, color, 1))
    b.append(ln(x1, y - drop, x1, y, color, 1))
    b.append(ln(x2, y - drop, x2, y, color, 1))
    b.append(t((x1 + x2) / 2, y + dy, label, size, color, 700, anchor="middle"))


def blend(v: float) -> str:
    """0（白）→ 1（强调红）。热力图专用。"""
    a, c = (255, 255, 255), (192, 57, 43)
    p = max(0.0, min(1.0, v))
    return "#%02X%02X%02X" % tuple(int(a[i] + (c[i] - a[i]) * p) for i in range(3))


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quantile(xs, q):
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


# --------------------------------------------------------------------------- #
# A01/A02/A03 · 排序条 + 均值线 + 端点直标
# --------------------------------------------------------------------------- #
def fig_hbar() -> str:
    W, H = 640, 330
    L, R = 132, 596
    cats = sorted(zip(CATS, V25), key=lambda x: -x[1])
    mx = max(V25) * 1.12
    X = sx(0, mx, L, R)
    mean = sum(V25) / len(V25)
    b = svg(W, H, "六品类规模排序条形")
    for v in (0, 25, 50, 75, 100):
        b.append(ln(X(v), 40, X(v), 276, LINE, 1))
        b.append(t(X(v), 290, str(v), 7.2, FAINT, anchor="middle"))
    b.append(ln(X(mean), 40, X(mean), 276, LINE2, 1, "3 3"))
    b.append(t(X(mean), 32, f"均值 {mean:.1f}", 7.4, MUTED, anchor="middle"))
    for i, (name, v) in enumerate(cats):
        y = 56 + i * 37
        b.append(t(20, y + 4, name, 9, INK2))
        hot = i == 0
        b.append(rc(L, y - 8, X(v) - L, 16, ACCENT if hot else INK2, rx=1.5))
        b.append(t(X(v) + 8, y + 4, f1(v), 9.4, INK, 700, halo=True))
        if hot:
            b.append(t(X(v) + 40, y + 4, f"高于均值 {v / mean * 100 - 100:+.0f}%", 7.6, ACCENT))
    b.append(t(20, 318, "六个品类合计 376.3 亿元；灰线为六项均值。", 7.6, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# A04/A05/A06 · 点图 + 中位线 + 中间 50% 带
# --------------------------------------------------------------------------- #
def fig_dot() -> str:
    W, H = 640, 384
    L, R = 118, 586
    rows = sorted(zip(CITIES, TICKET), key=lambda x: -x[1])
    vals = [v for _, v in rows]
    X = sx(100, 250, L, R)
    q1, q3, med = quantile(vals, .25), quantile(vals, .75), median(vals)
    b = svg(W, H, "十二城客单价点图")
    b.append(rc(X(q1), 40, X(q3) - X(q1), 296, ACCENT, opacity=".05"))
    b.append(t((X(q1) + X(q3)) / 2, 32, f"中间 50%：{q1:.0f}–{q3:.0f}", 7.2, MUTED, anchor="middle"))
    for v in (120, 160, 200, 240):
        b.append(ln(X(v), 40, X(v), 336, LINE, 1))
        b.append(t(X(v), 350, str(v), 7.2, FAINT, anchor="middle"))
    b.append(ln(X(med), 40, X(med), 336, ACCENT, 1, "3 3", "butt"))
    b.append(t(X(med) + 5, 52, f"中位 {med:.0f}", 7.4, ACCENT))
    for i, (name, v) in enumerate(rows):
        y = 58 + i * 24
        b.append(t(20, y + 4, name, 7.8, INK2))
        b.append(ln(L, y, X(v) - 6, y, LINE, 1))
        hot = v == max(vals)
        b.append(ci(X(v), y, 4, ACCENT if hot else INK2))
        b.append(t(X(v) + 9, y + 4, f"{v:.0f}", 8, INK, 600, halo=True))
    b.append(t(20, 374, "12 个城市客单价（元/单）；红点为最高，虚线为中位数。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# A07 · 哑铃：2024 → 2025
# --------------------------------------------------------------------------- #
def fig_dumbbell() -> str:
    W, H = 640, 320
    L, R = 118, 500
    pairs = sorted(zip(CATS, V24, V25), key=lambda x: x[2])
    X = sx(0, 110, L, R)
    b = svg(W, H, "六品类两期哑铃")
    for v in (0, 25, 50, 75, 100):
        b.append(ln(X(v), 40, X(v), 258, LINE, 1))
        b.append(t(X(v), 272, str(v), 7.2, FAINT, anchor="middle"))
    for i, (name, a, bb) in enumerate(pairs):
        y = 58 + i * 32
        b.append(t(20, y + 4, name, 8.4, INK2))
        b.append(ln(X(a), y, X(bb), y, LINE2, 2.4, cap="round"))
        b.append(ci(X(a), y, 3.6, WHITE, INK2, 1.4))
        b.append(ci(X(bb), y, 4.4, ACCENT if bb < a else INK2))
        b.append(t(X(a) - 8, y + 4, f1(a), 7.6, MUTED, anchor="end"))
        b.append(t(X(bb) + 8, y + 4, f1(bb), 8, INK, 600))
        delta = (bb / a - 1) * 100
        b.append(t(R + 74, y + 4, f"{delta:+.1f}%", 7.8,
                   ACCENT if delta < 0 else MUTED, 600, anchor="end"))
    b.append(t(R + 74, 272, "同比", 7.2, FAINT, anchor="end"))
    b.append(t(20, 306, "空心 = 2024，实心 = 2025；红点为下降品类。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# A08 · 三年斜率
# --------------------------------------------------------------------------- #
def _year_sum(cat: str) -> list[float]:
    m = DS.MONTHLY[cat]
    return [round(sum(m[i * 12:(i + 1) * 12]), 1) for i in range(3)]


def fig_slope() -> str:
    W, H = 640, 340
    T, B = 54, 264
    ys = [sum(_year_sum(c)[i] for c in CATS) for i in range(3)]
    lo, hi = 0, 100
    Y = sy(lo, hi, B, T)
    xs = [150, 330, 510]
    b = svg(W, H, "六品类三年斜率")
    for v in (20, 40, 60, 80, 100):
        b.append(ln(96, Y(v), 596, Y(v), LINE, 1))
        b.append(t(88, Y(v) + 3, str(v), 7.4, FAINT, anchor="end"))
    for cat in CATS:
        s = _year_sum(cat)
        hot = cat in ("小家电", "家居饰品")
        color = BLUE if cat == "小家电" else (ACCENT if cat == "家居饰品" else LINE2)
        b.append(pa("M " + " L ".join(f"{xs[i]},{Y(v):.1f}" for i, v in enumerate(s)),
                    "none", color, 2 if hot else 1))
        if hot:
            b.append(t(xs[-1] + 10, Y(s[-1]) + 4, f"{cat} {s[-1]:.0f}", 7.8,
                       color, 600))
    for i, lab in enumerate(("2023", "2024", "2025")):
        b.append(t(xs[i], B + 22, lab, 8, INK2, 600, anchor="middle"))
    b.append(t(20, 328, "灰线为其余四品类；蓝=增速最快，红=唯一下降。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# B03/B04/B05 · 水位线瀑布
# --------------------------------------------------------------------------- #
def fig_waterfall() -> str:
    W, H = 640, 360
    L, R, T, B = 56, 604, 60, 286
    start, end = DS.RETAIL[-2], DS.RETAIL[-1]
    deltas = [(c, round(a - b, 1)) for c, a, b in zip(CATS, V25, V24)]
    steps = [("2024", start, "total")] + [(c, d, "delta") for c, d in deltas] + [("2025", end, "total")]
    lo, hi = 320, 400
    Y = sy(lo, hi, B, T)
    slot = (R - L) / len(steps)
    bw = slot * 0.52
    b = svg(W, H, "规模桥：2024 到 2025 的品类贡献")
    for v in (320, 340, 360, 380):
        b.append(ln(L - 8, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 14, Y(v) + 3, str(v), 7.4, FAINT, anchor="end"))
    cum = start
    for i, (label, v, kind) in enumerate(steps):
        cx = L + slot * i + slot / 2
        if kind == "total":
            y0, y1, fill = Y(lo), Y(v), INK
            val = f1(v)
        else:
            y0, y1 = Y(cum), Y(cum + v)
            fill = BLUE if v > 0 else ACCENT
            val = f"{v:+.1f}"
            cum += v
        b.append(rc(cx - bw / 2, min(y0, y1), bw, max(abs(y1 - y0), 2), fill, rx=1))
        b.append(t(cx, min(y0, y1) - 6, val, 7.8, INK, 600, anchor="middle", halo=True))
        b.append(t(cx, B + 18, label, 7.4, INK2, anchor="middle"))
        if i < len(steps) - 1:
            b.append(ln(cx + bw / 2, min(y0, y1), L + slot * (i + 1) + slot / 2 - bw / 2,
                        min(y0, y1), LINE2, 1, "2 2"))
    b.append(t(20, 348, f"期初 {start}，期末 {end}，六项贡献合计 {end - start:+.1f} 亿元；蓝=增、红=减。",
               7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# B01/B02/B13 · 100% 堆叠 + 小项合并 + 标签内嵌
# --------------------------------------------------------------------------- #
def fig_share() -> str:
    W, H = 640, 220
    x0, x1, y, h = 24, 616, 92, 54
    total = sum(V25)
    rows = sorted(zip(CATS, V25), key=lambda x: -x[1])
    big = [(c, v) for c, v in rows if v / total >= 0.08]
    small = [(c, v) for c, v in rows if v / total < 0.08]
    segs = big + ([("其他", sum(v for _, v in small))] if small else [])
    b = svg(W, H, "2025 年品类构成 100% 堆叠")
    x = x0
    for i, (name, v) in enumerate(segs):
        w = v / total * (x1 - x0)
        color = ACCENT if i == 0 else (MUTED if name == "其他" else INK2)
        b.append(rc(x, y, w, h, color, stroke=WHITE, sw=1.2))
        if w > 46:
            b.append(t(x + w / 2, y + 24, f"{v / total * 100:.0f}%", 11, WHITE, 700, anchor="middle"))
            b.append(t(x + w / 2, y + 40, name, 7.4, WHITE, anchor="middle"))
        x += w
    b.append(t(x0, 78, "2025 年构成（合计 376.3 亿元）", 7.6, MUTED))
    if small:
        names = "、".join(c for c, _ in small)
        b.append(t(x0, 200, f"「其他」= {names}（各 <8%）；占比按金额实算，四舍五入到整数。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# C01/C02/C03/C04 · 折线 + MA + 同比 + 峰谷
# --------------------------------------------------------------------------- #
def fig_line() -> str:
    W, H = 640, 330
    L, R, T, B = 62, 596, 52, 268
    Y = sy(18, 48, B, T)
    X = sx(0, len(TOTAL) - 1, L + 6, R - 6)
    b = svg(W, H, "月度规模与三月移动平均")
    for v in (20, 30, 40):
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, str(v), 7.4, FAINT, anchor="end"))
    pts = [(X(i), Y(v)) for i, v in enumerate(TOTAL)]
    b.append(pa("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts), "none", INK2, 1.6))
    ma = [sum(TOTAL[max(0, i - 2):i + 1]) / len(TOTAL[max(0, i - 2):i + 1]) for i in range(len(TOTAL))]
    b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(ma)),
                "none", ACCENT, 1.4, "4 3"))
    peak = max(range(len(TOTAL)), key=lambda i: TOTAL[i])
    low = min(range(len(TOTAL)), key=lambda i: TOTAL[i])
    for i, lab, dy in ((peak, f"峰 {TOTAL[peak]:.1f}", -10), (low, f"谷 {TOTAL[low]:.1f}", 16)):
        b.append(ci(X(i), Y(TOTAL[i]), 3.6, ACCENT))
        b.append(t(X(i), Y(TOTAL[i]) + dy, lab, 7.4, ACCENT, 600, anchor="middle", halo=True))
    last = TOTAL[-1]
    yoy = (last / TOTAL[-13] - 1) * 100
    b.append(t(R, T - 12, f"近 12 个月同比 {yoy:+.1f}%", 8.2, INK, 700, anchor="end"))
    for i in range(0, len(TOTAL), 6):
        b.append(t(X(i), B + 18, MONTHS[i], 7, FAINT, anchor="middle"))
    b.append(t(20, 318, "实线 = 月度合计，虚线 = 3 月移动平均；峰谷与同比直接标注。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# C05 · 实测 + 预测（虚线 + 区间带）
# --------------------------------------------------------------------------- #
def fig_forecast() -> str:
    W, H = 640, 320
    L, R, T, B = 62, 596, 52, 262
    hist = TOTAL[-18:]
    fut = [round(hist[-1] * (1 + 0.003 * i), 2) for i in range(1, 7)]
    lo = [v * 0.95 for v in fut]
    hi = [v * 1.05 for v in fut]
    Y = sy(18, 46, B, T)
    X = sx(0, len(hist) + len(fut) - 1, L + 8, R - 8)
    b = svg(W, H, "实测与预测")
    for v in (20, 30, 40):
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, str(v), 7.4, FAINT, anchor="end"))
    xs = [X(i) for i in range(len(hist))]
    b.append(pa("M " + " L ".join(f"{x:.1f},{Y(v):.1f}" for x, v in zip(xs, hist)), "none", INK2, 1.8))
    fx = [X(len(hist) - 1 + i) for i in range(1, len(fut) + 1)]
    b.append(pa("M " + " L ".join(f"{x:.1f},{Y(v):.1f}" for x, v in zip(fx, fut)),
                "none", MUTED, 1.6, "4 3"))
    band = (f"M {fx[0]:.1f},{Y(hi[0]):.1f} " +
            " ".join(f"L {x:.1f},{Y(v):.1f}" for x, v in zip(fx, hi)) +
            " " + " ".join(f"L {x:.1f},{Y(v):.1f}" for x, v in zip(reversed(fx), reversed(lo))) + " Z")
    b.append(pa(band, ACCENT, opacity=".07"))
    b.append(ln(X(len(hist) - 0.5), T, X(len(hist) - 0.5), B, LINE2, 1, "2 3"))
    b.append(t(X(len(hist) - 0.5), T - 8, "预测起点", 7.2, MUTED, anchor="middle"))
    b.append(t(fx[-1] + 6, Y(fut[-1]) + 4, f"{fut[-1]:.1f}", 8.2, MUTED, 600))
    b.append(t(20, 310, "实线 = 实测 18 个月；虚线 = 未来 6 个月（季节朴素）；阴影 = ±5% 区间。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# A18 · 小倍数（三品类，共享尺度）
# --------------------------------------------------------------------------- #
def fig_small() -> str:
    W, H = 640, 400
    cats = ["家纺布艺", "小家电", "家居饰品"]
    L, R = 70, 596
    panel_h, gap = 92, 26
    all_vals = [v for c in cats for v in DS.MONTHLY[c]]
    lo, hi = 0, max(all_vals) * 1.1
    b = svg(W, H, "三品类月度小倍数")
    for p, cat in enumerate(cats):
        top = 40 + p * (panel_h + gap)
        bot = top + panel_h
        Y = sy(lo, hi, bot, top)
        X = sx(0, 35, L, R)
        b.append(ln(L, bot, R, bot, LINE2, 1))
        b.append(t(20, top + 12, cat, 8.4, INK2, 600))
        b.append(t(20, top + 26, f"{DS.MONTHLY[cat][-1]:.1f}", 10.5, INK, 700))
        b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(DS.MONTHLY[cat])),
                    "none", INK2, 1.4))
    b.append(t(20, 388, "三条曲线共享同一纵轴；右侧数字为 2025-12 值。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# A17 · 指数化（2023-01 = 100）
# --------------------------------------------------------------------------- #
def fig_index() -> str:
    W, H = 640, 320
    L, R, T, B = 62, 540, 52, 256
    Y = sy(80, 160, B, T)
    X = sx(0, 35, L + 4, R)
    b = svg(W, H, "六品类指数化走势")
    for v in (80, 100, 120, 140):
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, str(v), 7.4, FAINT, anchor="end"))
    for cat in CATS:
        s = DS.MONTHLY[cat]
        base = s[0]
        idx = [v / base * 100 for v in s]
        hot = cat in ("小家电", "家居饰品")
        color = BLUE if cat == "小家电" else (ACCENT if cat == "家居饰品" else LINE2)
        b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(idx)),
                    "none", color, 1.8 if hot else 1))
        if hot:
            b.append(t(R + 8, Y(idx[-1]) + 4, f"{cat} {idx[-1]:.0f}", 7.6, color, 600))
    b.append(t(R + 8, Y(100) + 4, "100", 7.2, FAINT))
    b.append(ln(L, Y(100), R, Y(100), LINE2, 1, "3 3"))
    b.append(t(20, 308, "以 2023-01 为 100；灰线为其余四品类。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# D01 · 点条（原始值分布）
# --------------------------------------------------------------------------- #
def fig_strip() -> str:
    W, H = 640, 236
    L, R = 60, 600
    vals = list(DS.TICKETS["呼和浩特"])
    lo, hi = 60, 420
    X = sx(lo, hi, L, R)
    med = median(vals)
    q1, q3 = quantile(vals, .25), quantile(vals, .75)
    b = svg(W, H, "客单价原始分布点条")
    b.append(rc(X(q1), 62, X(q3) - X(q1), 96, ACCENT, opacity=".05"))
    for v in (100, 200, 300, 400):
        b.append(ln(X(v), 58, X(v), 166, LINE, 1))
        b.append(t(X(v), 182, str(v), 7.2, FAINT, anchor="middle"))
    b.append(ln(X(med), 54, X(med), 170, ACCENT, 1, "3 3"))
    b.append(t(X(med) + 5, 52, f"中位 {med:.0f}", 7.4, ACCENT))
    for i, v in enumerate(vals):
        y = 70 + (i * 37 % 80)
        b.append(ci(X(v), y, 2.1, INK2))
    b.append(t(20, 214, f"n = {len(vals)} 笔订单；灰带为中间 50%，点未聚合。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# D02 · 箱线（四分位 + 端点）
# --------------------------------------------------------------------------- #
def fig_box() -> str:
    W, H = 640, 300
    L, R = 110, 580
    X = sx(60, 420, L, R)
    b = svg(W, H, "六城客单价箱线")
    for v in (100, 200, 300, 400):
        b.append(ln(X(v), 40, X(v), 240, LINE, 1))
        b.append(t(X(v), 256, str(v), 7.2, FAINT, anchor="middle"))
    for i, city in enumerate(CITIES[:6]):
        vals = list(DS.TICKETS[city])
        y = 58 + i * 30
        q1, q3, med = quantile(vals, .25), quantile(vals, .75), median(vals)
        p10, p90 = quantile(vals, .1), quantile(vals, .9)
        b.append(t(20, y + 4, city, 8.2, INK2))
        b.append(ln(X(p10), y, X(p90), y, LINE2, 1))
        b.append(ln(X(p10), y - 4, X(p10), y + 4, LINE2, 1))
        b.append(ln(X(p90), y - 4, X(p90), y + 4, LINE2, 1))
        b.append(rc(X(q1), y - 6, X(q3) - X(q1), 12, INK2, opacity=".85", rx=1))
        b.append(ln(X(med), y - 8, X(med), y + 8, WHITE, 2))
        b.append(t(600, y + 4, f"{med:.0f}", 7.8, INK, 600, anchor="end"))
    b.append(t(600, 40, "中位", 7, FAINT, anchor="end"))
    b.append(t(20, 288, "箱 = 中间 50%，须 = P10–P90，白线 = 中位；n 每城 260 笔。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# E01/E02/E03 · 双对数散点 + 拟合 + 离群
# --------------------------------------------------------------------------- #
def fig_scatter() -> str:
    W, H = 640, 360
    L, R, T, B = 70, 590, 52, 280
    px = [float(v) for v in DS.SKU_PRICE]
    py = [float(v) for v in DS.SKU_SALES]
    lx, ly = [math.log10(v) for v in px], [math.log10(v) for v in py]
    X = sx(min(lx) * .95, max(lx) * 1.02, L, R)
    Y = sy(min(ly) * .95, math.log10(5200), B, T)
    b = svg(W, H, "价格与销量双对数散点")
    for v in (20, 40, 60, 80, 100):
        b.append(ln(X(math.log10(v)), T, X(math.log10(v)), B, LINE, 1))
        b.append(t(X(math.log10(v)), B + 16, str(v), 7.2, FAINT, anchor="middle"))
    for v in (100, 1000, 5000):
        b.append(ln(L, Y(math.log10(v)), R, Y(math.log10(v)), LINE, 1))
        b.append(t(L - 8, Y(math.log10(v)) + 3, f"{v:,}", 7.2, FAINT, anchor="end"))
    b.append(pa(f"M {X(min(lx)):.1f},{Y(-0.72*min(lx)+math.log10(24000)):.1f} "
                f"L {X(max(lx)):.1f},{Y(-0.72*max(lx)+math.log10(24000)):.1f}",
                "none", LINE2, 1.4, "4 3"))
    out = max(range(len(px)), key=lambda i: py[i] / (24000 * px[i] ** -0.72))
    for i, (x, y) in enumerate(zip(px, py)):
        hot = i == out
        b.append(ci(X(lx[i]), Y(ly[i]), 4.4 if hot else 3, ACCENT if hot else INK2,
                    WHITE if hot else None, 1.2))
    b.append(ln(X(lx[out]) + 6, Y(ly[out]) - 6, X(lx[out]) + 52, Y(ly[out]) - 26, ACCENT, 1))
    b.append(t(X(lx[out]) + 56, Y(ly[out]) - 24, "39 元爆款：偏离弹性线 2.6 倍", 7.6, ACCENT))
    b.append(t(20, 348, "双对数坐标；虚线为价格弹性参考（斜率 −0.72）。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# E04 · 热力矩阵（门店 × 品类）
# --------------------------------------------------------------------------- #
def fig_heatmap() -> str:
    W, H = 640, 370
    L, T = 132, 66
    cw, ch = 78, 26
    M = DS.STORE_MATRIX
    mx = float(M.max())
    b = svg(W, H, "门店 × 品类销售热力矩阵")
    for j, cat in enumerate(CATS):
        b.append(t(L + cw * j + cw / 2, T - 10, cat[:4], 7.4, MUTED, anchor="middle"))
    for i, store in enumerate(DS.STORES):
        y = T + i * ch
        b.append(t(L - 10, y + 17, store, 7.6, INK2, anchor="end"))
        for j in range(len(CATS)):
            v = float(M[i][j])
            b.append(rc(L + cw * j + 1, y + 1, cw - 2, ch - 2, blend(v / mx)))
            b.append(t(L + cw * j + cw / 2, y + 18, f"{v:.0f}", 7.4,
                       WHITE if v / mx > 0.55 else INK2, anchor="middle"))
    b.append(t(20, 356, "颜色越深销售额越高；用于定位「哪些店靠哪些品类」。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# A09 · 排名变化（bump）
# --------------------------------------------------------------------------- #
def fig_bump() -> str:
    W, H = 640, 320
    T, B = 60, 250
    years = ["2023", "2024", "2025"]
    sums = {c: _year_sum(c) for c in CATS}
    ranks = []
    for i in range(3):
        order = sorted(CATS, key=lambda c: -sums[c][i])
        ranks.append({c: r + 1 for r, c in enumerate(order)})
    xs = [160, 340, 520]
    Y = lambda r: T + (r - 1) * (B - T) / 5
    b = svg(W, H, "六品类排名变化")
    for i, y in enumerate(years):
        b.append(t(xs[i], B + 22, y, 8, INK2, 600, anchor="middle"))
    for cat in CATS:
        hot = cat in ("小家电", "家居饰品")
        color = BLUE if cat == "小家电" else (ACCENT if cat == "家居饰品" else LINE2)
        b.append(pa("M " + " L ".join(f"{xs[i]},{Y(ranks[i][cat]):.1f}" for i in range(3)),
                    "none", color, 2 if hot else 1))
        for i in range(3):
            b.append(ci(xs[i], Y(ranks[i][cat]), 3.2, color))
        b.append(t(xs[-1] + 12, Y(ranks[2][cat]) + 4, cat, 7.6, color if hot else MUTED))
    b.append(t(20, 306, "纵轴为名次（1 最高）；只看位次，不看绝对值。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# B08 · 漏斗 + 转化率
# --------------------------------------------------------------------------- #
def fig_funnel() -> str:
    W, H = 640, 300
    stages = DS.FUNNEL
    b = svg(W, H, "转化漏斗")
    maxv = stages[0][1]
    top, height = 44, 34
    b.append(t(612, 36, "阶段转化", 7, FAINT, anchor="end"))
    for i, (name, v) in enumerate(stages):
        w = 60 + 480 * (v / maxv) ** 0.45
        x = (640 - w) / 2
        y = top + i * (height + 18)
        b.append(rc(x, y, w, height, ACCENT if i == 0 else INK2, opacity=".9" if i == 0 else ".82", rx=1))
        b.append(t(320, y + 22, f"{name} {f0(v)}", 8.4, WHITE, 600, anchor="middle"))
        if i:
            rate = v / stages[i - 1][1] * 100
            b.append(t(600, y - 4, f"{rate:.1f}%", 7.8, ACCENT if rate < 30 else MUTED, 600, anchor="end"))
    b.append(t(20, 288, "宽度按 √ 量级缩放（否则末段不可见）；右侧为阶段转化率。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# C14 · 甘特 + 里程碑
# --------------------------------------------------------------------------- #
def fig_gantt() -> str:
    W, H = 640, 320
    L, R = 130, 600
    X = sx(0, 90, L, R)
    b = svg(W, H, "上线计划甘特")
    for d in (0, 15, 30, 45, 60, 75, 90):
        b.append(ln(X(d), 44, X(d), 268, LINE, 1))
        b.append(t(X(d), 284, f"D{d}", 7.2, FAINT, anchor="middle"))
    for i, (name, a, bb) in enumerate(DS.GANTT):
        y = 58 + i * 32
        b.append(t(20, y + 4, name, 7.8, INK2))
        b.append(rc(X(a), y - 7, X(bb) - X(a), 14, INK2, rx=1.5))
        b.append(t(X(bb) + 6, y + 4, f"{bb - a} 天", 7, MUTED))
    for d, name in DS.MILESTONES:
        b.append(ln(X(d), 44, X(d), 268, ACCENT, 1, "2 3"))
        b.append(t(X(d) + 4, 40, name, 7.2, ACCENT))
    b.append(t(20, 306, "红虚线为里程碑；条长为计划工期。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# D05 · 森林图（效应 + CI）
# --------------------------------------------------------------------------- #
def fig_forest() -> str:
    W, H = 640, 300
    L, R = 190, 560
    X = sx(-4, 7, L, R)
    b = svg(W, H, "五项措施的效果与置信区间")
    b.append(ln(X(0), 44, X(0), 244, INK2, 1))
    b.append(t(X(0), 36, "0（无效）", 7.2, MUTED, anchor="middle"))
    for i, (name, eff, lo, hi, n) in enumerate(DS.EFFECTS):
        y = 62 + i * 36
        sig = lo > 0 or hi < 0
        color = BLUE if (sig and eff > 0) else (ACCENT if sig else MUTED)
        b.append(t(20, y + 4, name, 7.8, INK2))
        b.append(t(20, y + 16, f"n={n}", 6.8, FAINT))
        b.append(ln(X(lo), y, X(hi), y, color, 1.6))
        b.append(ln(X(lo), y - 4, X(lo), y + 4, color, 1.2))
        b.append(ln(X(hi), y - 4, X(hi), y + 4, color, 1.2))
        b.append(ci(X(eff), y, 4.2, color))
        b.append(t(X(hi) + 10, y + 4, f"{eff:+.1f}", 7.6, INK, 600))
    b.append(t(20, 288, "线 = 95% 置信区间；跨过 0 的效应不可宣称有效。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)

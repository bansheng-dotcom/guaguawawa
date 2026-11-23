# -*- coding: utf-8 -*-
"""flow 图型库 · 第三批：统计、时间、空间（12 型）"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from .prokit2 import (  # noqa: E402
    ACCENT, BLUE, INK, INK2, LINE, LINE2, MUTED, FAINT, WHITE,
    CATS, CITIES, TICKET, TOTAL, DS, blend, median,
    ci, f0, f1, ln, pa, rc, svg, sx, sy, t,
)
from .pk_b2 import arc  # noqa: E402

TINTS = ["#1F2A37", "#3D4B58", "#5C6A76", "#7B8792", "#9BA4AD", "#BCC3C9"]


# --------------------------------------------------------------------------- #
# error_bar · 误差线
# --------------------------------------------------------------------------- #
def fig_error_bar() -> str:
    W, H = 640, 280
    L, R = 150, 580
    qs = [TOTAL[i * 3:(i + 1) * 3] for i in range(12)]
    rows = [(f"{2023 + i // 4} Q{i % 4 + 1}", sum(q) / len(q), q) for i, q in enumerate(qs)]
    vals = [m for _, m, _ in rows]
    lo, hi = 20, 45
    X = sx(lo, hi, L, R)
    b = svg(W, H, "季度均值误差线")
    for v in (20, 30, 40):
        b.append(ln(X(v), 44, X(v), 246, LINE, 1))
        b.append(t(X(v), 260, str(v), 7.2, FAINT, anchor="middle"))
    for i, (name, m, q) in enumerate(rows[-6:]):
        sd = (sum((x - m) ** 2 for x in q) / max(len(q) - 1, 1)) ** 0.5
        se = sd / math.sqrt(len(q))
        y = 56 + i * 32
        b.append(t(20, y + 4, name, 7.6, INK2))
        b.append(ln(X(m - se), y, X(m + se), y, INK2, 1.6))
        b.append(ln(X(m - se), y - 5, X(m - se), y + 5, INK2, 1.2))
        b.append(ln(X(m + se), y - 5, X(m + se), y + 5, INK2, 1.2))
        b.append(ci(X(m), y, 4.2, ACCENT))
        b.append(t(X(m + se) + 8, y + 4, f"{m:.1f}±{se:.1f}", 7.4, INK, 600))
    b.append(t(20, 274, "点 = 季度均值，线 = ±1 SE；近六个季度。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# control · 控制图
# --------------------------------------------------------------------------- #
def fig_control() -> str:
    W, H = 640, 300
    L, R, T, B = 60, 596, 50, 240
    vals = [float(v) for v in DS.CONTROL]
    m = sum(vals) / len(vals)
    sd = (sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5
    ucl, lcl = m + 3 * sd, m - 3 * sd
    lo, hi = lcl - 2, ucl + 2
    Y = sy(lo, hi, B, T)
    X = sx(0, len(vals) - 1, L + 6, R - 6)
    b = svg(W, H, "控制图")
    b.append(rc(L, Y(ucl), R - L, Y(lcl) - Y(ucl), BLUE, opacity=".05"))
    for v, lab, color in ((ucl, f"UCL {ucl:.1f}", BLUE), (m, f"均值 {m:.1f}", INK2),
                          (lcl, f"LCL {lcl:.1f}", BLUE)):
        b.append(ln(L, Y(v), R, Y(v), color, 1, "4 3" if v != m else None))
        b.append(t(R, Y(v) - 5, lab, 7, color, anchor="end"))
    pts = [(X(i), Y(v)) for i, v in enumerate(vals)]
    b.append(pa("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts), "none", INK2, 1.4))
    for i, (x, y) in enumerate(pts):
        out = vals[i] > ucl or vals[i] < lcl
        b.append(ci(x, y, 3.4 if out else 2.6, ACCENT if out else INK2))
    b.append(t(20, 286, "灰色带 = ±3σ 控制限；红点为越限点。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# bullet · 子弹图（目标带）
# --------------------------------------------------------------------------- #
def fig_bullet() -> str:
    W, H = 640, 360
    L, R = 150, 580
    totals = [float(sum(row)) for row in DS.STORE_MATRIX]
    target = sum(totals) / len(totals) * 1.15
    mx = max(totals) * 1.06
    X = sx(0, mx, L, R)
    b = svg(W, H, "门店销售子弹图")
    for i, (store, v) in enumerate(sorted(zip(DS.STORES, totals), key=lambda x: x[1])):
        y = 54 + i * 30
        b.append(t(20, y + 4, store, 7.4, INK2))
        b.append(rc(L, y - 8, X(mx) - L, 16, LINE2, opacity=".35", rx=1))
        b.append(rc(L, y - 6, X(v) - L, 12, ACCENT if v < target else INK2, rx=1))
        b.append(ln(X(target), y - 10, X(target), y + 10, INK, 1.6))
        b.append(t(X(v) + 8, y + 4, f"{v:.0f}", 7.4, INK, 600))
    b.append(t(X(target) + 4, 40, f"目标 {target:.0f}", 7.2, INK))
    b.append(t(20, 348, "灰底 = 同组区间；粗条 = 实际；黑线 = 目标。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# gauge · 仪表盘
# --------------------------------------------------------------------------- #
def fig_gauge() -> str:
    W, H = 640, 300
    cx, cy, r = 320, 210, 120
    v, target = 376.3, 420
    pct = v / target
    b = svg(W, H, "目标完成率仪表")
    b.append(arc(cx, cy, r - 20, r, math.pi, 2 * math.pi, LINE2))
    b.append(arc(cx, cy, r - 20, r, math.pi, math.pi + math.pi * min(pct, 1), ACCENT))
    ang = math.pi + math.pi * min(pct, 1)
    b.append(ln(cx, cy, cx + (r - 26) * math.cos(ang), cy + (r - 26) * math.sin(ang), INK, 2.4))
    b.append(ci(cx, cy, 5, INK))
    b.append(t(cx, cy - 46, f"{pct * 100:.0f}%", 34, INK, 700, anchor="middle"))
    b.append(t(cx, cy - 18, f"{v} / 目标 {target}（亿元）", 8.4, MUTED, anchor="middle"))
    b.append(t(cx - r, cy + 18, "0", 7.4, FAINT, anchor="middle"))
    b.append(t(cx + r, cy + 18, "100%", 7.4, FAINT, anchor="middle"))
    b.append(t(20, 284, "单指标用仪表；多指标不要并排放四个表盘。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# target_band · 目标带
# --------------------------------------------------------------------------- #
def fig_target() -> str:
    W, H = 640, 300
    L, R, T, B = 60, 590, 50, 240
    Y = sy(20, 46, B, T)
    X = sx(0, len(TOTAL) - 1, L + 6, R - 6)
    b = svg(W, H, "月度规模与目标带")
    for v in (20, 30, 40):
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, str(v), 7.2, FAINT, anchor="end"))
    b.append(rc(L, Y(36), R - L, Y(30) - Y(36), BLUE, opacity=".06"))
    b.append(t(R, Y(36) - 6, "目标带 30–36", 7.2, BLUE, anchor="end"))
    pts = [(X(i), Y(v)) for i, v in enumerate(TOTAL)]
    b.append(pa("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts), "none", INK2, 1.6))
    for i, (x, y) in enumerate(pts):
        if TOTAL[i] > 36 or TOTAL[i] < 30:
            b.append(ci(x, y, 3.2, ACCENT))
    b.append(t(20, 286, "红点为越出目标带的月份；带回比阈值线更容易看出越界。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# radar · 雷达图
# --------------------------------------------------------------------------- #
def fig_radar() -> str:
    W, H = 640, 380
    cx, cy, r = 310, 180, 110
    M = DS.STORE_MATRIX
    names = list(CATS)
    mx = [max(float(M[i][j]) for i in range(len(DS.STORES))) for j in range(len(names))]
    sel = [0, 4]
    b = svg(W, H, "两家门店品类结构雷达")
    for ring in (0.33, 0.66, 1.0):
        pts = []
        for k in range(len(names)):
            a = -math.pi / 2 + k * math.tau / len(names)
            pts.append(f"{cx + r * ring * math.cos(a):.1f},{cy + r * ring * math.sin(a):.1f}")
        b.append(f'<polygon points="{" ".join(pts)}" fill="none" stroke="{LINE}" stroke-width="1"/>')
    for k, nm in enumerate(names):
        a = -math.pi / 2 + k * math.tau / len(names)
        b.append(ln(cx, cy, cx + r * math.cos(a), cy + r * math.sin(a), LINE, 1))
        b.append(t(cx + (r + 16) * math.cos(a), cy + (r + 16) * math.sin(a) + 3,
                   nm, 7.2, MUTED, anchor="middle"))
    b.append(t(cx + 6, cy - r * 0.66, "50", 6.8, FAINT))
    b.append(t(cx + 6, cy - r * 0.33, "25", 6.8, FAINT))
    b.append(t(cx + 6, cy - r - 3, "100", 6.8, FAINT))
    for idx, store in enumerate(sel):
        pts = []
        for k in range(len(names)):
            v = float(M[store][k]) / mx[k]
            a = -math.pi / 2 + k * math.tau / len(names)
            pts.append(f"{cx + r * v * math.cos(a):.1f},{cy + r * v * math.sin(a):.1f}")
        color = ACCENT if idx == 0 else BLUE
        b.append(f'<polygon points="{" ".join(pts)}" fill="{color}" fill-opacity=".10" '
                 f'stroke="{color}" stroke-width="1.8"/>')
        b.append(t(300 + idx * 120, 336, DS.STORES[store], 7.6, color))
    b.append(t(20, 360, "两家门店 × 六个品类；按各品类最大值归一。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# cal_heatmap · 日历热力
# --------------------------------------------------------------------------- #
def fig_cal() -> str:
    W, H = 640, 300
    L, T = 56, 44
    cw, ch = 17, 16
    vals = [float(v) for v in DS.DAILY]
    mx = max(vals)
    b = svg(W, H, "日销日历热力")
    for m in range(12):
        b.append(t(L - 8, T + m * ch + 12, f"{m + 1}月", 7, FAINT, anchor="end"))
    for i, v in enumerate(vals):
        m = i // 30
        d = i % 30
        if m > 11:
            break
        b.append(rc(L + d * cw, T + m * ch, cw - 2, ch - 2, blend(v / mx)))
    b.append(t(20, 286, "格 = 一天；越深销量越高；12 行 × 30 天。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# candlestick · 蜡烛
# --------------------------------------------------------------------------- #
def fig_candle() -> str:
    W, H = 640, 320
    L, R, T, B = 60, 596, 48, 250
    O = DS.OHLC
    lo, hi = float(O[:, 2].min()) - 1, float(O[:, 1].max()) + 1
    Y = sy(lo, hi, B, T)
    slot = (R - L) / len(O)
    bw = slot * 0.56
    b = svg(W, H, "日线蜡烛")
    for v in (96, 98, 100, 102):
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, str(v), 7.2, FAINT, anchor="end"))
    for i, (o, h, l, c) in enumerate(O):
        cx = L + slot * i + slot / 2
        up = c >= o
        color = BLUE if up else ACCENT
        b.append(ln(cx, Y(h), cx, Y(l), color, 1))
        b.append(rc(cx - bw / 2, Y(max(o, c)), bw, max(abs(Y(o) - Y(c)), 1.5), color, rx=1))
    b.append(t(20, 306, "红 = 收跌、蓝 = 收涨；影线为当日高低。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# sankey · 桑基
# --------------------------------------------------------------------------- #
def fig_sankey() -> str:
    W, H = 640, 360
    nodes = DS.SANKEY["nodes"]
    links = DS.SANKEY["links"]
    xs = [70, 190, 310, 430, 550]
    cy = 170
    main = [1860, 214, 61.4, 28.9, 24.6]
    hmax = 150
    b = svg(W, H, "转化桑基")
    # 节点：高度 ∝ √ 量级
    for i, x in enumerate(xs):
        h = 14 + hmax * math.sqrt(main[i] / main[0])
        b.append(rc(x - 6, cy - h / 2, 12, h, ACCENT if i == 0 else INK2, rx=2))
        b.append(t(x, cy - h / 2 - 8, nodes[i], 7.4, INK2, anchor="middle"))
    # 主链路：带宽度 ∝ √ 流量
    for i in range(4):
        x1, x2 = xs[i] + 6, xs[i + 1] - 6
        w = 3 + 16 * math.sqrt(main[i + 1] / main[0])
        d = f"M {x1},{cy} C {(x1 + x2) / 2},{cy} {(x1 + x2) / 2},{cy} {x2},{cy}"
        b.append(pa(d, "none", INK2, w, opacity=".30"))
    # 流失：每条从对应节点弯到右侧列
    loss_y = [70, 120, 170, 220]
    k = 0
    for a, bb, v in links:
        if bb < 5:
            continue
        y = loss_y[k % len(loss_y)]
        k += 1
        x1 = xs[a] + 6
        d = f"M {x1},{cy} C {x1 + 60},{cy} {560},{y} 596,{y}"
        b.append(pa(d, "none", ACCENT, 1.6 + 2 * math.sqrt(v / main[0]), opacity=".45"))
        b.append(ci(598, y, 3.4, ACCENT))
        b.append(t(606, y + 3, nodes[bb], 7, MUTED))
    b.append(t(20, 344, "节点高 ∝ √流量；红线为各阶段流失，右侧标流失人数。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 真实市界地图：choropleth / symbol_map / geo_flow
# --------------------------------------------------------------------------- #
def _geo():
    from . import geo
    return geo.project()


def _key(d, city):
    for k in d:
        if k.startswith(city) or city.startswith(k):
            return k
    return None


OFFSET = {
    "呼和浩特": (0, -12), "包头": (-16, -4), "乌海": (-12, 12), "鄂尔多斯": (2, 18),
    "乌兰察布": (16, -8), "巴彦淖尔": (-6, -8), "锡林郭勒盟": (0, -10),
    "赤峰": (10, 4), "通辽": (8, -6), "兴安盟": (6, -8), "呼伦贝尔": (0, -10),
    "阿拉善盟": (0, 6),
}


def _dark(fill: str) -> bool:
    r, g, b2 = int(fill[1:3], 16), int(fill[3:5], 16), int(fill[5:7], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b2) > 150


def fig_choropleth() -> str:
    W, H = 640, 380
    paths, cents = _geo()
    vals = dict(zip(CITIES, TICKET))
    mx, mn = max(vals.values()), min(vals.values())
    b = svg(W, H, "十二城客单价地图")
    for name, d in paths.items():
        city = next((c for c in CITIES if name.startswith(c) or c.startswith(name)), None)
        v = vals.get(city, mn)
        b.append(f'<path d="{d}" fill="{blend((v - mn) / (mx - mn))}" stroke="{WHITE}" stroke-width="1"/>')
    top5 = set(sorted(vals, key=lambda c: -vals[c])[:5])
    for name, (x, y) in cents.items():
        city = next((c for c in CITIES if name.startswith(c) or c.startswith(name)), None)
        if not city or city not in top5:
            continue
        v = vals.get(city, 0)
        fill = blend((v - mn) / (mx - mn))
        ink = INK if _dark(fill) else WHITE
        dx, dy = OFFSET.get(name, (0, 0))
        b.append(t(x + dx, y + dy - 2, city, 6.6, ink, 600, anchor="middle"))
        b.append(t(x + dx, y + dy + 9, str(v), 7.4, ink, 700, anchor="middle"))
    # 图例
    lx, ly = 26, 330
    for i in range(10):
        b.append(rc(lx + i * 11, ly, 11, 8, blend(i / 9)))
    b.append(t(lx, ly - 6, f"{mn}", 6.8, FAINT))
    b.append(t(lx + 110, ly - 6, f"{mx} 元/单", 6.8, FAINT, anchor="end"))
    b.append(t(20, 360, "真实市界（DataV 150000_full）；颜色 = 客单价；只标前五，避免中心城区标签打架。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


def fig_symbol() -> str:
    W, H = 640, 380
    paths, cents = _geo()
    pops = dict(zip(CITIES, DS.CITY_POP))
    mx = max(pops.values())
    b = svg(W, H, "十二城人口符号地图")
    for d in paths.values():
        b.append(f'<path d="{d}" fill="#F3F1EA" stroke="{LINE2}" stroke-width=".6"/>')
    top5 = set(sorted(pops, key=lambda c: -pops[c])[:5])
    for name, (x, y) in cents.items():
        city = next((c for c in CITIES if name.startswith(c) or c.startswith(name)), None)
        if not city:
            continue
        rad = 4 + 15 * math.sqrt(pops.get(city, 0) / mx)
        b.append(ci(x, y, rad, INK2, WHITE, 1))
        if city not in top5:
            continue
        dx, dy = OFFSET.get(name, (0, 0))
        b.append(t(x + dx, y + dy + rad + 9, f"{city} {pops.get(city, 0)}", 6.6, MUTED,
                   anchor="middle", halo=True))
    b.append(t(20, 360, "圆面积 = 常住人口（万人）；底图为真实市界。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)


def fig_geoflow() -> str:
    W, H = 640, 380
    paths, cents = _geo()
    pops = dict(zip(CITIES, DS.CITY_POP))
    hub = _key(cents, "呼和浩特")
    hx, hy = cents[hub]
    b = svg(W, H, "呼市到各城流量图")
    for d in paths.values():
        b.append(f'<path d="{d}" fill="#F3F1EA" stroke="{LINE2}" stroke-width=".6"/>')
    for name, (x, y) in cents.items():
        if name == hub:
            continue
        city = next((c for c in CITIES if name.startswith(c) or c.startswith(name)), None)
        w = 1.2 + 4.5 * math.sqrt(pops.get(city, 0) / 400)
        mx, my = (hx + x) / 2, (hy + y) / 2 - 26
        b.append(f'<path d="M {hx:.1f},{hy:.1f} Q {mx:.1f},{my:.1f} {x:.1f},{y:.1f}" '
                 f'fill="none" stroke="{INK2}" stroke-width="{w:.2f}" stroke-opacity=".38"/>')
        b.append(ci(x, y, 3.2, INK2))
        if pops.get(city, 0) >= 219:
            dx, dy = OFFSET.get(name, (0, -8))
            b.append(t(x + dx, y + dy - 6, city, 6.6, MUTED, anchor="middle", halo=True))
    b.append(ci(hx, hy, 5.5, ACCENT))
    b.append(t(hx, hy - 10, "呼和浩特", 7.4, ACCENT, 600, anchor="middle", halo=True))
    # 最强三条流标注数值
    links = sorted(((pops.get(next((c for c in CITIES if name.startswith(c) or c.startswith(name)), ""), 0),
                     name) for name in cents if name != hub), reverse=True)[:3]
    for v, name in links:
        x, y = cents[name]
        b.append(t(x + 6, y + 12, str(v), 7, INK2, 600, halo=True))
    b.append(t(20, 360, "曲线为示意流量（按人口），非真实货运；底图为真实市界。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)

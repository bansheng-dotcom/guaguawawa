# -*- coding: utf-8 -*-
"""charts_pro.spec_points —— 点位族 + 构成族参数化渲染器（18 型）。

点位：strip beeswarm violin ridge histogram hist_multi box_jitter bump quadrant
      parallel bubble lollipop_ci dot_matrix
构成：pie waffle rose sunburst
"""
from __future__ import annotations

import math

from .prokit2 import (
    ACCENT, BLUE, INK, INK2, LINE, LINE2, MUTED, FAINT, WHITE,
    ci, ln, pa, rc, sx, sy, t, median, quantile,
)

TINTS = ["#1F2A37", "#3D4B58", "#5C6A76", "#7B8792", "#9BA4AD", "#BCC3C9"]


def _svg(w, h, label):
    return [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{label}" preserveAspectRatio="xMidYMid meet">']


def _density(vals, lo, hi, n=80, h=26.0):
    out = []
    for i in range(n):
        x = lo + (hi - lo) * i / (n - 1)
        s = sum(math.exp(-0.5 * ((x - v) / h) ** 2) for v in vals)
        out.append(s / (len(vals) * h * math.sqrt(2 * math.pi)))
    return out


def _strip(s: dict) -> str:
    vals = [float(v) for v in s["values"]]
    W, H = 640, 240
    L, R = 70, 600
    lo, hi = s.get("domain") or (min(vals) * .9, max(vals) * 1.1)
    X = sx(lo, hi, L, R)
    b = _svg(W, H, "点条")
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        b.append(ln(X(v), 50, X(v), 178, LINE, 1))
        b.append(t(X(v), 196, f"{v:.0f}", 7, FAINT, anchor="middle"))
    med = median(vals)
    b.append(ln(X(med), 44, X(med), 184, ACCENT, 1, "3 3"))
    b.append(t(X(med) + 4, 40, f"中位 {med:.1f}", 7, ACCENT))
    for i, v in enumerate(vals):
        y = 168 - (i * 37 % 120) * .55
        b.append(ci(X(v), y, 2.1, INK2, opacity=".55"))
    b.append(t(20, 224, f"n = {len(vals)}；点未聚合。", 7, MUTED))
    b.append("</svg>")
    return "".join(b)


def _beeswarm(s: dict) -> str:
    vals = [float(v) for v in s["values"]]
    W, H = 640, 240
    L, R = 70, 600
    lo, hi = s.get("domain") or (min(vals) * .9, max(vals) * 1.1)
    X = sx(lo, hi, L, R)
    bins = {}
    b = _svg(W, H, "蜂群")
    for v in vals:
        k = int(v // 6)
        n = bins.get(k, 0)
        bins[k] = n + 1
        y = 120 - ((n % 6) * 8 - 20) * (1 if (n // 6) % 2 == 0 else -1)
        b.append(ci(X(v), y, 2.2, INK2, opacity=".55"))
    b.append(ln(L, 180, R, 180, LINE2, 1))
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        b.append(t(X(v), 196, f"{v:.0f}", 7, FAINT, anchor="middle"))
    b.append(t(20, 224, f"n = {len(vals)}；同值堆叠。", 7, MUTED))
    b.append("</svg>")
    return "".join(b)


def _violin(s: dict) -> str:
    groups = s["groups"]
    W, H = 640, 40 + len(groups) * 52 + 20
    L, R = 110, 560
    allv = [v for g in groups for v in g["values"]]
    lo, hi = min(allv) * .9, max(allv) * 1.1
    X = sx(lo, hi, L, R)
    b = _svg(W, H, "小提琴")
    for i, g in enumerate(groups):
        vals = [float(v) for v in g["values"]]
        d = _density(vals, lo, hi)
        mx = max(d) or 1
        cy = 56 + i * 52
        up = [(X(lo + (hi - lo) * k / (len(d) - 1)), cy - v / mx * 20) for k, v in enumerate(d)]
        dn = [(x, 2 * cy - y) for x, y in up]
        b.append(pa("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in up + dn[::-1]) + " Z",
                    INK2, opacity=".30"))
        b.append(ci(X(median(vals)), cy, 3, ACCENT))
        b.append(t(20, cy + 4, g["label"], 7.8, INK2))
        b.append(t(R + 8, cy + 4, f"{median(vals):.0f}", 7.4, INK, 600))
    b.append("</svg>")
    return "".join(b)


def _ridge(s: dict) -> str:
    groups = s["groups"]
    W, H = 640, 40 + len(groups) * 36 + 20
    L, R = 110, 590
    allv = [v for g in groups for v in g["values"]]
    lo, hi = min(allv) * .9, max(allv) * 1.1
    X = sx(lo, hi, L, R)
    b = _svg(W, H, "山脊")
    for i, g in enumerate(groups):
        d = _density([float(v) for v in g["values"]], lo, hi)
        mx = max(d) or 1
        base = H - 20 - i * 36
        pts = [(X(lo + (hi - lo) * k / (len(d) - 1)), base - v / mx * 30) for k, v in enumerate(d)]
        b.append(pa("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                    + f" L {pts[-1][0]:.1f},{base} L {pts[0][0]:.1f},{base} Z", TINTS[i % 6], opacity=".85"))
        b.append(t(20, base - 4, g["label"], 7.2, INK2))
    b.append("</svg>")
    return "".join(b)


def _hist(s: dict) -> str:
    vals = [float(v) for v in s["values"]]
    W, H = 640, 290
    L, R, T, B = 64, 580, 46, 238
    lo, hi = s.get("domain") or (min(vals), max(vals))
    nb = s.get("bins", 12)
    step = (hi - lo) / nb
    bins = [0] * nb
    for v in vals:
        bins[min(int((v - lo) / step), nb - 1)] += 1
    mx = max(bins) * 1.1
    Y = sy(0, mx, B, T)
    X = sx(lo, hi, L, R)
    b = _svg(W, H, "直方图")
    for i, n in enumerate(bins):
        x = X(lo + i * step)
        b.append(rc(x + 1, Y(n), X(lo + (i + 1) * step) - x - 2, B - Y(n), INK2, rx=1))
    med = median(vals)
    b.append(ln(X(med), T, X(med), B, ACCENT, 1, "3 3"))
    b.append(t(X(med) + 4, T - 6, f"中位 {med:.0f}", 7, ACCENT))
    for k in range(4):
        v = lo + (hi - lo) * k / 3
        b.append(t(X(v), B + 16, f"{v:.0f}", 7, FAINT, anchor="middle"))
    b.append("</svg>")
    return "".join(b)


def _hist_multi(s: dict) -> str:
    groups = s["groups"]
    W, H = 640, 40 + len(groups) * 96 + 20
    b = _svg(W, H, "分组直方图")
    for gi, g in enumerate(groups):
        vals = [float(v) for v in g["values"]]
        lo, hi = min(vals), max(vals)
        step = (hi - lo) / 10
        bins = [0] * 10
        for v in vals:
            bins[min(int((v - lo) / step), 9)] += 1
        mx = max(bins)
        y0 = 46 + gi * 96
        X = sx(lo, hi, 110, 560)
        for i, n in enumerate(bins):
            x = X(lo + i * step)
            b.append(rc(x + 1, y0 + 62 - 58 * n / mx, X(lo + (i + 1) * step) - x - 2,
                        58 * n / mx, INK2, rx=1))
        b.append(t(20, y0 + 34, g["label"], 7.4, INK2, 600))
        b.append(ln(110, y0 + 62, 560, y0 + 62, LINE2, 1))
    b.append("</svg>")
    return "".join(b)


def _box_jitter(s: dict) -> str:
    groups = s["groups"]
    W, H = 640, 40 + len(groups) * 36 + 20
    L, R = 110, 560
    allv = [v for g in groups for v in g["values"]]
    lo, hi = min(allv) * .9, max(allv) * 1.1
    X = sx(lo, hi, L, R)
    b = _svg(W, H, "箱线加散点")
    for i, g in enumerate(groups):
        vals = sorted(float(v) for v in g["values"])
        q1, med, q3 = quantile(vals, .25), median(vals), quantile(vals, .75)
        y = 54 + i * 36
        b.append(t(20, y + 4, g["label"], 7.6, INK2))
        b.append(rc(X(q1), y - 6, X(q3) - X(q1), 12, INK2, opacity=".25", rx=1))
        b.append(ln(X(med), y - 8, X(med), y + 8, INK, 1.6))
        for k, v in enumerate(vals[::max(1, len(vals) // 24)]):
            b.append(ci(X(v), y + ((k % 5) - 2) * 1.6, 1.5, INK2, opacity=".45"))
    b.append("</svg>")
    return "".join(b)


def _bump(s: dict) -> str:
    stages, series = s["stages"], s["series"]
    W, H = 640, 340
    T, B = 56, 280
    xs = [90 + (520) * i / max(len(stages) - 1, 1) for i in range(len(stages))]
    n = len(series)
    Y = lambda r: T + (r - 1) * (B - T) / max(n - 1, 1)
    b = _svg(W, H, "排名变化")
    for i, st in enumerate(stages):
        b.append(t(xs[i], B + 20, st, 8, INK2, 600, anchor="middle"))
    for j, se in enumerate(series):
        color = BLUE if j == 0 else (ACCENT if j == 1 else LINE2)
        b.append(pa("M " + " L ".join(f"{xs[i]},{Y(r):.1f}" for i, r in enumerate(se["ranks"])),
                    "none", color, 2 if j < 2 else 1))
        for i, r in enumerate(se["ranks"]):
            b.append(ci(xs[i], Y(r), 3.2, color))
        b.append(t(xs[-1] + 10, Y(se["ranks"][-1]) + 4, se["name"], 7.2, color if j < 2 else MUTED))
    b.append("</svg>")
    return "".join(b)


def _quadrant(s: dict) -> str:
    pts = s["points"]
    W, H = 640, 360
    L, R, T, B = 70, 580, 50, 280
    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    X = sx(min(xs) * .85, max(xs) * 1.1, L, R)
    Y = sy(min(ys) * .85, max(ys) * 1.1, B, T)
    b = _svg(W, H, "四象限")
    b.append(ln(X(mx), T, X(mx), B, LINE2, 1, "3 3"))
    b.append(ln(L, Y(my), R, Y(my), LINE2, 1, "3 3"))
    for p in pts:
        b.append(ci(X(p["x"]), Y(p["y"]), 4, ACCENT if p.get("hot") else INK2))
        if p.get("label"):
            b.append(t(X(p["x"]) + 7, Y(p["y"]) - 5, p["label"], 7, INK2, halo=True))
    b.append("</svg>")
    return "".join(b)


def _parallel(s: dict) -> str:
    axes, series = s["axes"], s["series"]
    W, H = 640, 320
    T, B = 56, 258
    xs = [100 + 440 * i / max(len(axes) - 1, 1) for i in range(len(axes))]
    mins = [min(se["values"][i] for se in series) for i in range(len(axes))]
    maxs = [max(se["values"][i] for se in series) for i in range(len(axes))]
    b = _svg(W, H, "平行坐标")
    for i, ax in enumerate(axes):
        b.append(ln(xs[i], T, xs[i], B, LINE2, 1))
        b.append(t(xs[i], B + 18, ax, 7.4, INK2, anchor="middle"))
    for j, se in enumerate(series):
        color = BLUE if j == 0 else (ACCENT if j == 1 else LINE2)
        pts = [(xs[i], B - (se["values"][i] - mins[i]) / (maxs[i] - mins[i] or 1) * (B - T))
               for i in range(len(axes))]
        b.append(pa("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts), "none", color, 1.8 if j < 2 else 1))
        b.append(t(pts[-1][0] + 8, pts[-1][1] + 4, se["name"], 7.2, color if j < 2 else MUTED))
    b.append("</svg>")
    return "".join(b)


def _bubble(s: dict) -> str:
    pts = s["points"]
    W, H = 640, 350
    L, R, T, B = 74, 570, 50, 274
    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    rs = [p.get("r", 1) for p in pts]
    X = sx(min(xs) * .95, max(xs) * 1.05, L, R)
    Y = sy(min(ys) * .9, max(ys) * 1.1, B, T)
    rmax = max(rs) or 1
    b = _svg(W, H, "气泡")
    for k in range(4):
        v = min(ys) + (max(ys) - min(ys)) * k / 3
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, f"{v:.0f}", 7, FAINT, anchor="end"))
    for p in pts:
        b.append(ci(X(p["x"]), Y(p["y"]), 3 + 14 * math.sqrt(p.get("r", 1) / rmax),
                    INK2, WHITE, 1, opacity=".75"))
        if p.get("label"):
            b.append(t(X(p["x"]) + 10, Y(p["y"]) + 4, p["label"], 7, INK2, halo=True))
    b.append("</svg>")
    return "".join(b)


def _lollipop_ci(s: dict) -> str:
    rows = s["rows"]
    W, H = 640, 40 + len(rows) * 36 + 20
    L, R = 170, 560
    vals = [v for r in rows for v in (r["lo"], r["hi"])]
    X = sx(min(0, min(vals)) * .9, max(vals) * 1.1, L, R)
    b = _svg(W, H, "棒棒糖加区间")
    b.append(ln(X(0), 36, X(0), 36 + len(rows) * 36, LINE2, 1))
    for i, r in enumerate(rows):
        y = 52 + i * 36
        sig = r["lo"] > 0 or r["hi"] < 0
        color = BLUE if (sig and r["est"] > 0) else (ACCENT if sig else MUTED)
        b.append(t(20, y + 4, r["label"], 7.6, INK2))
        b.append(ln(X(r["lo"]), y, X(r["hi"]), y, color, 1.4))
        b.append(ln(X(0), y, X(r["est"]), y, color, 1.4))
        b.append(ci(X(r["est"]), y, 4.2, color))
    b.append("</svg>")
    return "".join(b)


def _dot_matrix(s: dict) -> str:
    rows, cols, M = s["rows"], s["cols"], s["matrix"]
    cw = min(80, int(520 / max(len(cols), 1)))
    ch = 26
    L, T = 130, 56
    mx = max(max(r) for r in M) or 1
    b = _svg(640, T + len(rows) * ch + 30, "点阵矩阵")
    for j, c in enumerate(cols):
        b.append(t(L + cw * j + cw / 2, T - 10, c, 7, MUTED, anchor="middle"))
    for i, r in enumerate(rows):
        y = T + i * ch + ch / 2
        b.append(t(L - 10, y + 3, r, 7, INK2, anchor="end"))
        for j in range(len(cols)):
            b.append(ci(L + cw * j + cw / 2, y, 2 + 7 * math.sqrt(M[i][j] / mx), INK2, opacity=".45"))
    b.append("</svg>")
    return "".join(b)


# ---------------------------- 构成族 ---------------------------- #
def _arcs(b, cx, cy, r0, r1, items, start=-math.pi / 2):
    total = sum(i["value"] for i in items)
    a = start
    for i, it in enumerate(items):
        da = it["value"] / total * math.tau
        p0 = (cx + r1 * math.cos(a), cy + r1 * math.sin(a))
        p1 = (cx + r1 * math.cos(a + da), cy + r1 * math.sin(a + da))
        q0 = (cx + r0 * math.cos(a + da), cy + r0 * math.sin(a + da))
        q1 = (cx + r0 * math.cos(a), cy + r0 * math.sin(a))
        large = 1 if da > math.pi else 0
        d = (f"M {p0[0]:.1f},{p0[1]:.1f} A {r1},{r1} 0 {large} 1 {p1[0]:.1f},{p1[1]:.1f} "
             f"L {q0[0]:.1f},{q0[1]:.1f} A {r0},{r0} 0 {large} 0 {q1[0]:.1f},{q1[1]:.1f} Z")
        b.append(f'<path d="{d}" fill="{TINTS[i % 6]}"/>')
        a += da
    return total


def _pie(s: dict) -> str:
    items = sorted(s["items"], key=lambda x: -x["value"])
    W, H = 640, 320
    cx, cy, r = 250, 160, 100
    b = _svg(W, H, "饼图")
    total = _arcs(b, cx, cy, 0, r, items)
    a = -math.pi / 2
    for it in items:
        da = it["value"] / total * math.tau
        mid = a + da / 2
        lx, ly = cx + (r + 20) * math.cos(mid), cy + (r + 20) * math.sin(mid)
        side = "start" if math.cos(mid) > 0 else "end"
        b.append(ln(cx + (r + 2) * math.cos(mid), cy + (r + 2) * math.sin(mid), lx, ly, LINE2, 1))
        b.append(t(lx + (5 if side == "start" else -5), ly + 3,
                   f"{it['label']} {it['value']/total*100:.0f}%", 7, INK2, anchor=side))
        a += da
    b.append("</svg>")
    return "".join(b)


def _waffle(s: dict) -> str:
    items = sorted(s["items"], key=lambda x: -x["value"])
    total = sum(i["value"] for i in items)
    cells = []
    for i, it in enumerate(items):
        cells += [i] * max(0, round(it["value"] / total * 100))
    cells = cells[:100] + [len(items) - 1] * (100 - len(cells))
    W, H = 640, 300
    b = _svg(W, H, "华夫格")
    for k, idx in enumerate(cells):
        r_, c_ = divmod(k, 10)
        b.append(rc(50 + c_ * 20, 40 + r_ * 20, 17, 17, TINTS[idx % 6], rx=2))
    y = 56
    for i, it in enumerate(items):
        b.append(rc(290, y - 9, 10, 10, TINTS[i % 6], rx=2))
        b.append(t(306, y, it["label"], 7.6, INK2))
        b.append(t(560, y, f"{it['value']/total*100:.0f}%", 7.6, INK, 600, anchor="end"))
        y += 22
    b.append("</svg>")
    return "".join(b)


def _rose(s: dict) -> str:
    items = sorted(s["items"], key=lambda x: -x["value"])
    W, H = 640, 340
    cx, cy = 280, 175
    mx = max(i["value"] for i in items) or 1
    b = _svg(W, H, "玫瑰图")
    a0 = -math.pi / 2
    n = len(items)
    for i, it in enumerate(items):
        a1 = a0 + math.tau / n - 0.03
        r = 24 + 100 * math.sqrt(it["value"] / mx)
        p0 = (cx + r * math.cos(a0), cy + r * math.sin(a0))
        p1 = (cx + r * math.cos(a1), cy + r * math.sin(a1))
        q0 = (cx + 14 * math.cos(a1), cy + 14 * math.sin(a1))
        q1 = (cx + 14 * math.cos(a0), cy + 14 * math.sin(a0))
        large = 0
        d = (f"M {p0[0]:.1f},{p0[1]:.1f} A {r},{r} 0 {large} 1 {p1[0]:.1f},{p1[1]:.1f} "
             f"L {q0[0]:.1f},{q0[1]:.1f} A 14,14 0 {large} 0 {q1[0]:.1f},{q1[1]:.1f} Z")
        b.append(f'<path d="{d}" fill="{TINTS[i % 6]}"/>')
        mid = (a0 + a1) / 2
        b.append(t(cx + (r + 12) * math.cos(mid), cy + (r + 12) * math.sin(mid) + 3,
                   it["label"], 7, INK2, anchor="start" if math.cos(mid) > 0 else "end"))
        a0 += math.tau / n
    b.append("</svg>")
    return "".join(b)


def _sunburst(s: dict) -> str:
    items = s["items"]
    W, H = 640, 360
    cx, cy = 300, 175
    b = _svg(W, H, "旭日图")
    inner = [{"label": it["label"], "value": sum(c["value"] for c in it["children"])} for it in items]
    total = _arcs(b, cx, cy, 40, 92, inner)
    a = -math.pi / 2
    for it in items:
        da = sum(c["value"] for c in it["children"]) / total * math.tau
        aa = a
        for j, ch in enumerate(it["children"]):
            dda = ch["value"] / total * math.tau
            sub = [{"label": ch["label"], "value": ch["value"]}]
            tmp = []
            _arcs(tmp, cx, cy, 92, 122, sub, aa)
            b.extend(tmp)
            aa += dda
        a += da
    b.append("</svg>")
    return "".join(b)


RENDERERS = {
    "strip": _strip, "beeswarm": _beeswarm, "violin": _violin, "ridge": _ridge,
    "histogram": _hist, "hist_multi": _hist_multi, "box_jitter": _box_jitter,
    "bump": _bump, "quadrant": _quadrant, "parallel": _parallel, "bubble": _bubble,
    "lollipop_ci": _lollipop_ci, "dot_matrix": _dot_matrix,
    "pie": _pie, "waffle": _waffle, "rose": _rose, "sunburst": _sunburst,
}

# -*- coding: utf-8 -*-
"""charts_pro.spec_families —— 条形族 + 折线族参数化渲染器。

条形族：vbar lollipop diverging grouped stacked pct_stacked marimekko bullet bridge
折线族：area stack_area multi_line step cumulative area_range connected
"""
from __future__ import annotations

import math

from .prokit_helpers import (
    ACCENT, BLUE, INK, INK2, LINE, LINE2, MUTED, FAINT, WHITE,
    ci, ln, pa, rc, sx, sy, t,
)

TINTS = ["#1F2A37", "#3D4B58", "#5C6A76", "#7B8792", "#9BA4AD", "#BCC3C9"]


def _svg(w, h, label):
    return [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{label}" preserveAspectRatio="xMidYMid meet">']


def _axis_y(b, lo, hi, Y, x0, x1, fmt="{:.0f}", n=4):
    for k in range(n + 1):
        v = lo + (hi - lo) * k / (n or 1)
        b.append(ln(x0, Y(v), x1, Y(v), LINE, 1))
        b.append(t(x0 - 8, Y(v) + 3, fmt.format(v), 7, FAINT, anchor="end"))


# --------------------------------------------------------------------------- #
# 条形族
# --------------------------------------------------------------------------- #
def _nice_step(v: float) -> float:
    """把刻度间隔归到 1/2/2.5/5 × 10^k，别出现 0、3、7、10、13 这种。"""
    if v <= 0:
        return 1.0
    k = math.floor(math.log10(v))
    base = 10 ** k
    for m in (1, 2, 2.5, 5, 10):
        if v <= m * base:
            return m * base
    return 10 * base


def _accent_hit(it: dict, acc) -> bool:
    """accent 支持标签或下标——排序后下标会错位，优先按标签匹配。"""
    if isinstance(acc, str):
        return str(it.get("label")) == acc
    return False


def _vbar(s: dict) -> str:
    items = s["items"]
    hi0 = s.get("max") or max(i["value"] for i in items) * 1.12
    step = _nice_step((s.get("max") or max(i["value"] for i in items)) / 4)
    hi = math.ceil(hi0 / step) * step
    # 高度随条目数量走：两条不要占 330 高
    H = max(200, min(340, 118 + 42 * len(items)))
    T, B = 46, H - 56
    W = 640
    L, R = 64, 590
    Y = sy(0, hi, B, T)
    slot = (R - L) / len(items)
    bw = slot * 0.46
    b = _svg(W, H, "纵向柱")
    v = 0.0
    while v <= hi + 1e-9:
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, f"{v:g}", 7, FAINT, anchor="end"))
        v += step
    acc = s.get("accent", -1)
    hot_i = -1
    for i, it in enumerate(items):
        cx = L + slot * i + slot / 2
        hot = (i == acc) or _accent_hit(it, acc)
        if hot:
            hot_i = i
        b.append(rc(cx - bw / 2, Y(it["value"]), bw, B - Y(it["value"]),
                    ACCENT if hot else INK2, rx=2))
        b.append(t(cx, Y(it["value"]) - 7, f"{it['value']:g}", 8, INK, 700,
                   anchor="middle", halo=True))
        b.append(t(cx, B + 16, it["label"], 7.4, MUTED, anchor="middle"))
    # 注释上墙：把「是彩妆的 3.44 倍」这类话画在图上，而不是只躺在数据里
    note = str(s.get("accent_note") or "").strip()
    if note and 0 <= hot_i < len(items):
        cx = L + slot * hot_i + slot / 2
        b.append(t(cx, Y(items[hot_i]["value"]) - 21, note, 7.2, ACCENT,
                   anchor="middle"))
    if s.get("target"):
        b.append(ln(L, Y(s["target"]), R, Y(s["target"]), ACCENT, 1, "3 3"))
        b.append(t(R, Y(s["target"]) - 5, f"目标 {s['target']:g}", 7, ACCENT, anchor="end"))
    b.append("</svg>")
    return "".join(b)


def _lollipop(s: dict) -> str:
    items = sorted(s["items"], key=lambda x: -x["value"])
    W, H = 640, 60 + len(items) * 30 + 30
    L, R = 140, 580
    hi = s.get("max") or max(i["value"] for i in items) * 1.1
    X = sx(0, hi, L, R)
    b = _svg(W, H, "棒棒糖")
    for i, it in enumerate(items):
        y = 54 + i * 30
        b.append(t(20, y + 4, it["label"], 8, INK2))
        b.append(ln(L, y, X(it["value"]), y, LINE2, 1.4))
        b.append(ci(X(it["value"]), y, 4.6, ACCENT if i == s.get("accent", -1) else INK2))
        b.append(t(X(it["value"]) + 8, y + 4, f"{it['value']:g}", 7.8, INK, 600, halo=True))
    b.append("</svg>")
    return "".join(b)


def _diverging(s: dict) -> str:
    items = sorted(s["items"], key=lambda x: x["value"])
    W, H = 640, 56 + len(items) * 32 + 24
    L, R = 150, 560
    mx = max(abs(i["value"]) for i in items) * 1.3 or 1
    X = sx(-mx, mx, L + 30, R - 30)
    zero = X(0)
    b = _svg(W, H, "正负条")
    b.append(ln(zero, 36, zero, 36 + len(items) * 32, LINE2, 1))
    for i, it in enumerate(items):
        y = 50 + i * 32
        b.append(t(L - 10, y + 4, it["label"], 7.8, INK2, anchor="end"))
        b.append(rc(min(zero, X(it["value"])), y - 8, max(abs(X(it["value"]) - zero), 2), 16,
                    BLUE if it["value"] > 0 else ACCENT, rx=1.5))
        b.append(t(max(zero, X(it["value"])) + 7, y + 4, f"{it['value']:+.1f}", 7.6, INK, 600))
    b.append("</svg>")
    return "".join(b)


def _grouped(s: dict) -> str:
    groups, series = s["groups"], s["series"]
    W, H = 640, 330
    L, R, T, B = 64, 596, 56, 258
    hi = s.get("max") or max(max(g["values"]) for g in groups) * 1.15
    Y = sy(0, hi, B, T)
    slot = (R - L) / len(groups)
    n = len(series)
    bw = min(slot / (n + 1.2), 30)
    b = _svg(W, H, "分组柱")
    _axis_y(b, 0, hi, Y, L, R, "{:.0f}")
    for i, g in enumerate(groups):
        cx = L + slot * i + slot / 2
        for j, v in enumerate(g["values"]):
            x = cx - n * bw / 2 + j * bw
            b.append(rc(x + 1, Y(v), bw - 2, B - Y(v), INK2 if j else LINE2, rx=1))
            b.append(t(x + bw / 2, Y(v) - 6, f"{v:g}", 7, INK, 600, anchor="middle", halo=True))
        b.append(t(cx, B + 16, g["label"], 7.2, INK2, anchor="middle"))
    for j, name in enumerate(series):
        b.append(rc(L + j * 70, T - 22, 9, 8, INK2 if j else LINE2))
        b.append(t(L + j * 70 + 14, T - 15, name, 7, MUTED))
    b.append("</svg>")
    return "".join(b)


def _stacked(s: dict, pct: bool = False) -> str:
    cats, series = s["categories"], s["series"]
    W, H = 640, 340
    L, R, T, B = 64, 596, 56, 262
    totals = [sum(se["values"][i] for se in series) for i in range(len(cats))]
    hi = 100 if pct else (s.get("max") or max(totals) * 1.1)
    Y = sy(0, hi, B, T)
    slot = (R - L) / len(cats)
    bw = slot * 0.55
    b = _svg(W, H, "堆叠柱")
    _axis_y(b, 0, hi, Y, L, R, "{:.0f}%" if pct else "{:.0f}")
    for i in range(len(cats)):
        cx = L + slot * i + slot / 2
        acc = 0.0
        for j, se in enumerate(series):
            v = se["values"][i]
            vv = v / totals[i] * 100 if pct else v
            y0, y1 = Y(acc), Y(acc + vv)
            b.append(rc(cx - bw / 2, y1, bw, y0 - y1, TINTS[j % 6], stroke=WHITE, sw=1))
            if vv > (8 if pct else hi * 0.06):
                b.append(t(cx, (y0 + y1) / 2 + 3,
                           f"{vv:.0f}%" if pct else f"{vv:.1f}", 7, WHITE, 600, anchor="middle"))
            acc += vv
        b.append(t(cx, Y(acc) - 7, f"{acc:.0f}%" if pct else f"{acc:.0f}", 7.6, INK, 700,
                   anchor="middle", halo=True))
        b.append(t(cx, B + 16, cats[i], 7.2, MUTED, anchor="middle"))
    b.append("</svg>")
    return "".join(b)


def _pct(s: dict) -> str:
    return _stacked(s, pct=True)


def _marimekko(s: dict) -> str:
    cols = s["columns"]
    W, H = 640, 340
    L, R, T, B = 50, 590, 56, 268
    total = sum(c["total"] for c in cols)
    x = L
    b = _svg(W, H, "Marimekko")
    for c in cols:
        w = (R - L) * c["total"] / total
        acc = 0.0
        for j, p in enumerate(c["parts"]):
            h = (B - T) * p["value"] / c["total"]
            y0 = B - acc - h
            b.append(rc(x + 1, y0 + 1, w - 2, h - 2, TINTS[j % 6], rx=1))
            acc += h
        b.append(t(x + w / 2, B + 16, c["label"], 7.6, INK2, 600, anchor="middle"))
        b.append(t(x + w / 2, T - 8, f"{c['total']:.0f}", 7.2, FAINT, anchor="middle"))
        x += w
    b.append("</svg>")
    return "".join(b)


def _bullet(s: dict) -> str:
    rows = s["rows"]
    W, H = 640, 50 + len(rows) * 46 + 20
    L, R = 150, 580
    b = _svg(W, H, "子弹图")
    for i, r in enumerate(rows):
        y = 56 + i * 46
        X = sx(0, r.get("max", r["target"] * 1.2), L, R)
        b.append(t(20, y + 4, r["label"], 7.8, INK2))
        b.append(rc(L, y - 9, R - L, 18, LINE2, opacity=".25", rx=2))
        b.append(rc(L, y - 6, X(r["value"]) - L, 12, ACCENT if r["value"] < r["target"] else INK2, rx=1))
        b.append(ln(X(r["target"]), y - 11, X(r["target"]), y + 11, INK, 1.6))
        b.append(t(X(r["value"]) + 6, y + 4, f"{r['value']:g}", 7.2, INK, 600))
    b.append("</svg>")
    return "".join(b)


def _bridge(s: dict) -> str:
    start, deltas, end = s["start"], s["deltas"], s.get("end")
    end = end if end is not None else start + sum(d["value"] for d in deltas)
    steps = [{"label": s.get("start_label", "期初"), "value": start, "kind": "t"}] + \
            [{"label": d["label"], "value": d["value"], "kind": "d"} for d in deltas] + \
            [{"label": s.get("end_label", "期末"), "value": end, "kind": "t"}]
    W, H = 640, 340
    L, R, T, B = 60, 596, 70, 268
    lo = s.get("floor", min(start, end) * .96)
    hi = max(start, end) * 1.04
    Y = sy(lo, hi, B, T)
    slot = (R - L) / len(steps)
    bw = slot * .52
    b = _svg(W, H, "桥图")
    _axis_y(b, lo, hi, Y, L, R, "{:.1f}")
    cum = start
    for i, st in enumerate(steps):
        cx = L + slot * i + slot / 2
        if st["kind"] == "t":
            y0, y1, fill = Y(lo), Y(st["value"]), INK
            val = f"{st['value']:.2f}"
        else:
            y0, y1 = Y(cum), Y(cum + st["value"])
            fill = BLUE if st["value"] > 0 else ACCENT
            val = f"{st['value']:+.2f}"
            cum += st["value"]
        b.append(rc(cx - bw / 2, min(y0, y1), bw, max(abs(y1 - y0), 2), fill, rx=1))
        b.append(t(cx, min(y0, y1) - 6, val, 7.4, INK, 600, anchor="middle", halo=True))
        b.append(t(cx, B + 16, st["label"], 7, INK2, anchor="middle"))
        if i < len(steps) - 1:
            b.append(ln(cx + bw / 2, min(y0, y1), L + slot * (i + 1) + slot * .24,
                        min(y0, y1), LINE2, 1, "2 2"))
    b.append("</svg>")
    return "".join(b)


# --------------------------------------------------------------------------- #
# 折线族
# --------------------------------------------------------------------------- #
def _area(s: dict) -> str:
    pts = s["points"]
    W, H = 640, 320
    L, R, T, B = 64, 590, 50, 252
    lo, hi = s.get("domain") or (min(p["value"] for p in pts) * .9, max(p["value"] for p in pts) * 1.08)
    Y = sy(lo, hi, B, T)
    X = sx(0, len(pts) - 1, L + 6, R - 6)
    b = _svg(W, H, "面积")
    _axis_y(b, lo, hi, Y, L, R, "{:.1f}")
    d = "M " + " L ".join(f"{X(i):.1f},{Y(p['value']):.1f}" for i, p in enumerate(pts))
    b.append(pa(d + f" L {X(len(pts)-1):.1f},{B} L {L:.1f},{B} Z", ACCENT, opacity=".08"))
    b.append(pa(d, "none", INK2, 1.8))
    b.append(t(X(len(pts) - 1), Y(pts[-1]["value"]) - 8, f"{pts[-1]['value']:.2f}", 8, INK, 700,
               anchor="end", halo=True))
    for i, p in enumerate(pts):
        if i % max(1, len(pts) // 6) == 0:
            b.append(t(X(i), B + 16, p["label"], 7, FAINT, anchor="middle"))
    b.append("</svg>")
    return "".join(b)


def _stack_area(s: dict) -> str:
    series, xs = s["series"], s.get("xlabels")
    W, H = 640, 330
    L, R, T, B = 64, 590, 50, 262
    n = len(series[0]["points"])
    totals = [sum(se["points"][i] for se in series) for i in range(n)]
    hi = s.get("max") or max(totals) * 1.05
    Y = sy(0, hi, B, T)
    X = sx(0, n - 1, L + 4, R - 4)
    b = _svg(W, H, "堆叠面积")
    cum = [0.0] * n
    for j, se in enumerate(series):
        top = [cum[i] + se["points"][i] for i in range(n)]
        d = ("M " + " L ".join(f"{X(i):.1f},{Y(cum[i]):.1f}" for i in range(n)) +
             " " + " ".join(f"L {X(i):.1f},{Y(top[i]):.1f}" for i in range(n - 1, -1, -1)) + " Z")
        b.append(pa(d, TINTS[j % 6], opacity=".9"))
        b.append(t(X(n - 1) + 6, Y((top[-1] + cum[-1]) / 2) + 3, se["name"], 7, MUTED))
        cum = top
    if xs:
        for i in range(0, n, max(1, n // 6)):
            b.append(t(X(i), B + 16, xs[i], 7, FAINT, anchor="middle"))
    b.append("</svg>")
    return "".join(b)


def _multi_line(s: dict) -> str:
    series = s["series"]
    W, H = 640, 320
    L, R, T, B = 64, 560, 50, 252
    vals = [v for se in series for v in se["points"]]
    lo, hi = s.get("domain") or (min(vals) * .9, max(vals) * 1.08)
    Y = sy(lo, hi, B, T)
    n = len(series[0]["points"])
    X = sx(0, n - 1, L + 4, R)
    b = _svg(W, H, "多系列线")
    _axis_y(b, lo, hi, Y, L, R, "{:.1f}")
    for j, se in enumerate(series):
        color = se.get("color") or (INK2 if j == 0 else (BLUE if j == 1 else ACCENT))
        b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(se["points"])),
                    "none", color, 1.8))
        b.append(t(R + 6, Y(se["points"][-1]) + 3, se["name"], 7, color, 600))
    b.append("</svg>")
    return "".join(b)


def _step(s: dict) -> str:
    pts = s["points"]
    W, H = 640, 310
    L, R, T, B = 64, 590, 50, 244
    lo, hi = s.get("domain") or (min(p["value"] for p in pts) * .9, max(p["value"] for p in pts) * 1.08)
    Y = sy(lo, hi, B, T)
    X = sx(0, len(pts) - 1, L + 6, R - 6)
    b = _svg(W, H, "阶梯线")
    _axis_y(b, lo, hi, Y, L, R, "{:.1f}")
    d = f"M {X(0):.1f},{Y(pts[0]['value']):.1f}"
    for i in range(1, len(pts)):
        d += f" L {X(i):.1f},{Y(pts[i-1]['value']):.1f} L {X(i):.1f},{Y(pts[i]['value']):.1f}"
    b.append(pa(d, "none", INK2, 1.6))
    for ev in s.get("events", []):
        b.append(ln(X(ev["x"]), T, X(ev["x"]), B, ACCENT, 1, "3 3"))
        b.append(t(X(ev["x"]) + 4, T + 10, ev["label"], 7, ACCENT))
    b.append("</svg>")
    return "".join(b)


def _cumulative(s: dict) -> str:
    pts = s["points"]
    run, cum = 0.0, []
    for p in pts:
        run += p["value"]
        cum.append(run)
    W, H = 640, 300
    L, R, T, B = 64, 580, 50, 238
    Y = sy(0, cum[-1] * 1.06, B, T)
    X = sx(0, len(cum) - 1, L + 4, R)
    b = _svg(W, H, "累计")
    _axis_y(b, 0, cum[-1] * 1.06, Y, L, R, "{:.0f}")
    b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(cum)),
                "none", INK2, 1.8))
    b.append(t(X(len(cum) - 1) - 4, Y(cum[-1]) - 8, f"{cum[-1]:,.0f}", 8, INK, 700,
               anchor="end", halo=True))
    b.append("</svg>")
    return "".join(b)


def _area_range(s: dict) -> str:
    lo, hi = s["low"], s["high"]
    W, H = 640, 300
    L, R, T, B = 64, 580, 50, 238
    Y = sy(min(lo) * .95, max(hi) * 1.05, B, T)
    X = sx(0, len(lo) - 1, L + 4, R)
    b = _svg(W, H, "极差带")
    _axis_y(b, min(lo) * .95, max(hi) * 1.05, Y, L, R, "{:.0f}")
    d = ("M " + " L ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(hi)) +
         " " + " ".join(f"L {X(i):.1f},{Y(v):.1f}" for i, v in enumerate(lo[::-1], 0)) + " Z")
    # 反向索引修正
    d = ("M " + " L ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(hi)) + " " +
         " ".join(f"L {X(len(lo)-1-i):.1f},{Y(v):.1f}" for i, v in enumerate(lo)) + " Z")
    b.append(pa(d, BLUE, opacity=".12"))
    b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(hi)), "none", BLUE, 1.2))
    b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(lo)), "none", INK2, 1.2))
    b.append("</svg>")
    return "".join(b)


def _connected(s: dict) -> str:
    pts = s["points"]
    W, H = 640, 340
    L, R, T, B = 74, 570, 50, 268
    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    X = sx(min(xs) * .95, max(xs) * 1.05, L, R)
    Y = sy(min(ys) * .9, max(ys) * 1.08, B, T)
    b = _svg(W, H, "轨迹散点")
    _axis_y(b, min(ys) * .9, max(ys) * 1.08, Y, L, R, "{:.1f}")
    b.append(pa("M " + " L ".join(f"{X(p['x']):.1f},{Y(p['y']):.1f}" for p in pts), "none", INK2, 1.2))
    for i, p in enumerate(pts):
        b.append(ci(X(p["x"]), Y(p["y"]), 2.6, ACCENT if i == len(pts) - 1 else INK2))
    b.append("</svg>")
    return "".join(b)


RENDERERS = {
    "vbar": _vbar, "lollipop": _lollipop, "diverging": _diverging,
    "grouped": _grouped, "stacked": _stacked, "pct_stacked": _pct,
    "marimekko": _marimekko, "bullet": _bullet, "bridge": _bridge,
    "area": _area, "stack_area": _stack_area, "multi_line": _multi_line,
    "step": _step, "cumulative": _cumulative, "area_range": _area_range,
    "connected": _connected,
}

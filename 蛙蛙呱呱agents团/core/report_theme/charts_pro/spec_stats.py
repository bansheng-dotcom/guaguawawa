# -*- coding: utf-8 -*-
"""charts_pro.spec_stats —— 统计族 + 时间族参数化渲染器（参数化第 4 批）。"""
from __future__ import annotations

import math

from .prokit2 import (
    ACCENT, BLUE, INK, INK2, LINE, LINE2, MUTED, FAINT, WHITE,
    ci, ln, pa, rc, sx, sy, t,
)

TINTS = ["#1F2A37", "#3D4B58", "#5C6A76", "#7B8792", "#9BA4AD", "#BCC3C9"]


def _svg(w, h, label):
    return [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{label}" preserveAspectRatio="xMidYMid meet">']


# ---------------------------- 统计族 ---------------------------- #
def _error_bar(s: dict) -> str:
    rows = s["rows"]
    W, H = 640, 40 + len(rows) * 34 + 20
    L, R = 150, 560
    vals = [v for r in rows for v in (r["lo"], r["hi"])]
    X = sx(min(vals) * .9, max(vals) * 1.1, L, R)
    b = _svg(W, H, "误差条")
    for i, r in enumerate(rows):
        y = 52 + i * 34
        b.append(t(20, y + 4, r["label"], 7.8, INK2))
        b.append(ln(X(r["lo"]), y, X(r["hi"]), y, INK2, 1.4))
        b.append(ln(X(r["lo"]), y - 4, X(r["lo"]), y + 4, INK2, 1))
        b.append(ln(X(r["hi"]), y - 4, X(r["hi"]), y + 4, INK2, 1))
        b.append(ci(X(r["est"]), y, 4, ACCENT))
        b.append(t(X(r["hi"]) + 8, y + 4, f"{r['est']:.1f}", 7.4, INK, 600))
    b.append("</svg>")
    return "".join(b)


def _forest(s: dict) -> str:
    rows = s["rows"]
    W, H = 640, 40 + len(rows) * 36 + 24
    L, R = 190, 540
    vals = [v for r in rows for v in (r["lo"], r["hi"])]
    X = sx(min(vals + [0]) * 1.05, max(vals + [0]) * 1.05, L, R)
    b = _svg(W, H, "森林图")
    b.append(ln(X(0), 36, X(0), 36 + len(rows) * 36, LINE2, 1))
    b.append(t(X(0), 30, "0", 7, MUTED, anchor="middle"))
    for i, r in enumerate(rows):
        y = 52 + i * 36
        sig = r["lo"] > 0 or r["hi"] < 0
        color = BLUE if (sig and r["est"] > 0) else (ACCENT if sig else MUTED)
        b.append(t(20, y + 4, r["label"], 7.6, INK2))
        b.append(ln(X(r["lo"]), y, X(r["hi"]), y, color, 1.5))
        b.append(ln(X(r["lo"]), y - 4, X(r["lo"]), y + 4, color, 1))
        b.append(ln(X(r["hi"]), y - 4, X(r["hi"]), y + 4, color, 1))
        b.append(ci(X(r["est"]), y, 4, color))
        b.append(t(X(r["hi"]) + 8, y + 4, f"{r['est']:+.1f}", 7.2, INK, 600))
    b.append("</svg>")
    return "".join(b)


def _control(s: dict) -> str:
    vals = [float(v) for v in s["values"]]
    W, H = 640, 300
    L, R, T, B = 64, 590, 50, 238
    m = sum(vals) / len(vals)
    sd = (sum((v - m) ** 2 for v in vals) / max(len(vals) - 1, 1)) ** 0.5 or 1
    ucl, lcl = m + 3 * sd, m - 3 * sd
    Y = sy(lcl - sd, ucl + sd, B, T)
    X = sx(0, len(vals) - 1, L + 6, R - 6)
    b = _svg(W, H, "控制图")
    b.append(rc(L, Y(ucl), R - L, Y(lcl) - Y(ucl), BLUE, opacity=".05"))
    for v, lab in ((ucl, "UCL"), (m, "均值"), (lcl, "LCL")):
        b.append(ln(L, Y(v), R, Y(v), BLUE if v != m else INK2, 1, "4 3" if v != m else None))
        b.append(t(R, Y(v) - 5, f"{lab} {v:.1f}", 7, BLUE if v != m else INK2, anchor="end"))
    pts = [(X(i), Y(v)) for i, v in enumerate(vals)]
    b.append(pa("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts), "none", INK2, 1.4))
    for v, (x, y) in zip(vals, pts):
        b.append(ci(x, y, 3.4 if v > ucl or v < lcl else 2.6,
                    ACCENT if v > ucl or v < lcl else INK2))
    b.append("</svg>")
    return "".join(b)


def _gauge(s: dict) -> str:
    v, target = s["value"], s["target"]
    prev = s.get("prev")
    W, H = 640, 300
    cx, cy, r = 320, 210, 118
    pct = max(0.0, min(v / target, 1.2))
    b = _svg(W, H, "仪表")
    b.append(f'<path d="M {cx-r},{cy} A {r},{r} 0 0 1 {cx+r},{cy}" fill="none" '
             f'stroke="{LINE2}" stroke-width="16"/>')
    a = math.pi + math.pi * min(pct, 1)
    b.append(f'<path d="M {cx-r},{cy} A {r},{r} 0 0 1 {cx+r*math.cos(a):.1f},{cy+r*math.sin(a):.1f}" '
             f'fill="none" stroke="{ACCENT}" stroke-width="16"/>')
    if prev is not None:
        ap = math.pi + math.pi * min(prev / target, 1)
        b.append(ln(cx + (r - 18) * math.cos(ap), cy + (r - 18) * math.sin(ap),
                    cx + (r + 18) * math.cos(ap), cy + (r + 18) * math.sin(ap), INK, 1.6))
        b.append(t(cx, cy + 34, f"上期 {prev:g}", 7.4, MUTED, anchor="middle"))
    b.append(t(cx, cy - 44, f"{v / target * 100:.0f}%", 34, INK, 700, anchor="middle"))
    b.append(t(cx, cy - 16, f"{v:g} / 目标 {target:g}", 8.2, MUTED, anchor="middle"))
    b.append(t(cx - r, cy + 18, "0", 7, FAINT, anchor="middle"))
    b.append(t(cx + r, cy + 18, "100%", 7, FAINT, anchor="middle"))
    b.append("</svg>")
    return "".join(b)


def _target_band(s: dict) -> str:
    pts = s["points"]
    lo, hi = s["band"]
    W, H = 640, 300
    L, R, T, B = 64, 590, 50, 238
    lo_d = s.get("domain") or (min(p["value"] for p in pts) * .9, max(p["value"] for p in pts) * 1.1)
    Y = sy(lo_d[0], lo_d[1], B, T)
    X = sx(0, max(len(pts) - 1, 1), L + 6, R - 6)
    b = _svg(W, H, "目标带")
    b.append(rc(L, Y(hi), R - L, Y(lo) - Y(hi), BLUE, opacity=".06"))
    b.append(t(R, Y(hi) - 6, f"目标带 {lo:g}–{hi:g}", 7, BLUE, anchor="end"))
    b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(p['value']):.1f}" for i, p in enumerate(pts)),
                "none", INK2, 1.6))
    for i, p in enumerate(pts):
        if p["value"] > hi or p["value"] < lo:
            b.append(ci(X(i), Y(p["value"]), 3.2, ACCENT))
    b.append("</svg>")
    return "".join(b)


def _radar(s: dict) -> str:
    axes, series = s["axes"], s["series"]
    W, H = 640, 360
    cx, cy, r = 300, 176, 110
    b = _svg(W, H, "雷达")
    for ring in (.33, .66, 1.0):
        pts = []
        for k in range(len(axes)):
            a = -math.pi / 2 + k * math.tau / len(axes)
            pts.append(f"{cx + r * ring * math.cos(a):.1f},{cy + r * ring * math.sin(a):.1f}")
        b.append(f'<polygon points="{" ".join(pts)}" fill="none" stroke="{LINE}" stroke-width="1"/>')
    for k, ax in enumerate(axes):
        a = -math.pi / 2 + k * math.tau / len(axes)
        b.append(ln(cx, cy, cx + r * math.cos(a), cy + r * math.sin(a), LINE, 1))
        b.append(t(cx + (r + 16) * math.cos(a), cy + (r + 16) * math.sin(a) + 3, ax, 7, MUTED,
                   anchor="middle"))
    for j, se in enumerate(series):
        color = ACCENT if j == 0 else BLUE
        pts = []
        for k, v in enumerate(se["values"]):
            a = -math.pi / 2 + k * math.tau / len(axes)
            rr = r * max(0.0, min(v, 1.0))
            pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
        b.append(f'<polygon points="{" ".join(pts)}" fill="{color}" fill-opacity=".10" '
                 f'stroke="{color}" stroke-width="1.8"/>')
        b.append(t(300 + j * 120, 330, se["name"], 7.4, color))
    b.append("</svg>")
    return "".join(b)


def _pareto(s: dict) -> str:
    items = sorted(s["items"], key=lambda x: -x["value"])
    total = sum(i["value"] for i in items)
    W, H = 640, 320
    L, R, T, B = 64, 590, 50, 252
    mx = items[0]["value"] * 1.25
    Y = sy(0, mx, B, T)
    slot = (R - L) / len(items)
    bw = slot * .5
    b = _svg(W, H, "帕累托")
    pts, cum = [], 0.0
    for i, it in enumerate(items):
        cx = L + slot * i + slot / 2
        b.append(rc(cx - bw / 2, Y(it["value"]), bw, B - Y(it["value"]), INK2, rx=1))
        b.append(t(cx, Y(it["value"]) - 6, f"{it['value']:g}", 7, INK, 600, anchor="middle", halo=True))
        b.append(t(cx, B + 16, it["label"], 7, INK2, anchor="middle"))
        cum += it["value"] / total
        pts.append((cx, B - cum * (B - T)))
    b.append(pa("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts), "none", ACCENT, 1.8))
    for x, y in pts:
        b.append(ci(x, y, 3, ACCENT))
    b.append(ln(L, B - .8 * (B - T), R, B - .8 * (B - T), ACCENT, 1, "3 3"))
    b.append(t(R, B - .8 * (B - T) - 5, "累计 80%", 7, ACCENT, anchor="end"))
    b.append("</svg>")
    return "".join(b)


def _kpi(s: dict) -> str:
    items = s["items"]
    W, H = 640, 200
    b = _svg(W, H, "KPI")
    for i, it in enumerate(items):
        x = 24 + i * (592 / len(items))
        b.append(t(x, 70, f"{it['value']}", 26, INK, 700))
        b.append(t(x, 90, it["label"], 8, MUTED))
        if it.get("delta"):
            b.append(t(x, 106, it["delta"], 7.6,
                       ACCENT if str(it["delta"]).startswith("-") else MUTED))
    b.append("</svg>")
    return "".join(b)


def _spark_table(s: dict) -> str:
    rows = s["rows"]
    W, H = 640, 40 + len(rows) * 34 + 20
    b = _svg(W, H, "表内迷你线")
    for i, r in enumerate(rows):
        y = 50 + i * 34
        vals = r["values"]
        mn, mx = min(vals), max(vals)
        X = sx(0, len(vals) - 1, 140, 470)
        Y = sy(mn * .95, mx * 1.05, y + 12, y - 12)
        b.append(t(20, y + 4, r["label"], 7.8, INK2))
        b.append(pa("M " + " L ".join(f"{X(k):.1f},{Y(v):.1f}" for k, v in enumerate(vals)),
                    "none", INK2, 1.2))
        b.append(t(560, y + 4, f"{vals[-1]:.1f}", 7.8, INK, 600, anchor="end"))
    b.append("</svg>")
    return "".join(b)


def _dual(s: dict) -> str:
    top, bottom = s["top"], s["bottom"]
    W, H = 640, 380
    L, R = 64, 590
    b = _svg(W, H, "上下两栏")
    for k, (pts, box, unit) in enumerate(((top, (42, 190), s.get("top_label", "规模")),
                                          (bottom, (236, 340), s.get("bottom_label", "同比")))):
        T, B = box
        vals = [p["value"] for p in pts]
        lo, hi = min(vals) * .95, max(vals) * 1.05
        Y = sy(lo, hi, B, T)
        X = sx(0, max(len(pts) - 1, 1), L + 6, R - 6)
        b.append(t(L, T - 10, unit, 7.4, MUTED))
        b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(p['value']):.1f}" for i, p in enumerate(pts)),
                    "none", INK2 if k == 0 else MUTED, 1.6))
        if k == 0:
            for i, p in enumerate(pts):
                if i % max(1, len(pts) // 6) == 0:
                    b.append(t(X(i), B + 16, p["label"], 6.8, FAINT, anchor="middle"))
    b.append("</svg>")
    return "".join(b)


def _share_bar(s: dict) -> str:
    items = sorted(s["items"], key=lambda x: -x["value"])
    total = sum(i["value"] for i in items)
    W, H = 640, 200
    b = _svg(W, H, "占比条")
    x = 30
    for i, it in enumerate(items):
        w = 580 * it["value"] / total
        b.append(rc(x, 80, w, 44, TINTS[i % 6], stroke=WHITE, sw=1.2))
        if w > 46:
            b.append(t(x + w / 2, 100, f"{it['value']/total*100:.0f}%", 10, WHITE, 700, anchor="middle"))
            b.append(t(x + w / 2, 116, it["label"], 7, WHITE, anchor="middle"))
        x += w
    b.append("</svg>")
    return "".join(b)


RENDERERS = {
    "error_bar": _error_bar, "forest": _forest, "control": _control,
    "gauge": _gauge, "target_band": _target_band, "radar": _radar,
    "pareto": _pareto, "kpi": _kpi, "spark_table": _spark_table,
    "dual_panels": _dual, "share_bar": _share_bar,
}

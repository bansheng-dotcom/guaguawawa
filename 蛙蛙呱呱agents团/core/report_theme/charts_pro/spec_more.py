# -*- coding: utf-8 -*-
"""charts_pro.spec_more —— 第二批参数化图型（slope / dumbbell / small_mult / box / scatter）。"""
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


def _slope(s: dict) -> str:
    series = s["series"]
    stages = s.get("stages") or [f"T{i+1}" for i in range(len(series[0]["points"]))]
    W, H = 640, 340
    L, R, T, B = 90, 540, 50, 266
    vals = [v for se in series for v in se["points"]]
    lo, hi = s.get("domain") or (min(vals) * .9, max(vals) * 1.05)
    Y = sy(lo, hi, B, T)
    n = len(stages)
    xs = [L + (R - L) * i / max(n - 1, 1) for i in range(n)]
    b = _svg(W, H, "斜率")
    for k in range(4):
        v = lo + (hi - lo) * k / 3
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, f"{v:.0f}" if v >= 10 else f"{v:.1f}", 7, FAINT, anchor="end"))
    for i, st in enumerate(stages):
        b.append(t(xs[i], B + 18, st, 8, INK2, 600, anchor="middle"))
    for idx, se in enumerate(series):
        hi_light = idx == s.get("highlight", 0)
        color = se.get("color") or (ACCENT if idx == 0 and s.get("highlight") == 0 else
                                    BLUE if idx == 1 else LINE2)
        b.append(pa("M " + " L ".join(f"{xs[k]:.1f},{Y(v):.1f}" for k, v in enumerate(se["points"])),
                    "none", color, 2.2 if hi_light else 1.2))
        for k, v in enumerate(se["points"]):
            b.append(ci(xs[k], Y(v), 3.6 if hi_light else 2.6, color))
        b.append(t(xs[-1] + 10, Y(se["points"][-1]) + 4, f"{se['name']} {se['points'][-1]:.1f}",
                   7.4, color if hi_light else MUTED, 600 if hi_light else 400))
    b.append("</svg>")
    return "".join(b)


def _dumbbell(s: dict) -> str:
    rows = s["rows"]
    W, H = 640, 50 + len(rows) * 34 + 20
    L, R = 150, 520
    vals = [v for r in rows for v in (r["a"], r["b"])]
    lo, hi = s.get("domain") or (min(vals) * .85, max(vals) * 1.08)
    X = sx(lo, hi, L, R)
    b = _svg(W, H, "哑铃")
    for i, r in enumerate(rows):
        y = 50 + i * 34
        b.append(t(20, y + 4, r["label"], 8, INK2))
        b.append(ln(X(r["a"]), y, X(r["b"]), y, LINE2, 2.4, cap="round"))
        b.append(ci(X(r["a"]), y, 3.6, WHITE, INK2, 1.4))
        b.append(ci(X(r["b"]), y, 4.2, ACCENT if r["b"] < r["a"] else INK2))
        b.append(t(X(r["a"]) - 7, y + 4, f"{r['a']:.1f}", 7.2, MUTED, anchor="end"))
        b.append(t(X(r["b"]) + 7, y + 4, f"{r['b']:.1f}", 7.6, INK, 600))
        if r.get("delta"):
            b.append(t(R + 70, y + 4, r["delta"], 7.2, MUTED, anchor="end"))
    b.append("</svg>")
    return "".join(b)


def _small_mult(s: dict) -> str:
    panels = s["panels"]
    W, H = 640, 40 + len(panels) * 88 + 20
    b = _svg(W, H, "小倍数")
    allv = [v for p in panels for v in p["points"]]
    lo, hi = s.get("domain") or (0, max(allv) * 1.1)
    for i, p in enumerate(panels):
        top = 40 + i * 88
        bot = top + 70
        Y = sy(lo, hi, bot, top)
        X = sx(0, len(p["points"]) - 1, 70, 560)
        b.append(ln(70, bot, 560, bot, LINE2, 1))
        b.append(t(20, top + 12, p["label"], 7.6, INK2, 600))
        b.append(t(560, top + 12, f"{p['points'][-1]:.1f}", 7.6, INK, 600, anchor="end"))
        b.append(pa("M " + " L ".join(f"{X(k):.1f},{Y(v):.1f}" for k, v in enumerate(p["points"])),
                    "none", INK2, 1.3))
    b.append("</svg>")
    return "".join(b)


def _box(s: dict) -> str:
    groups = s["groups"]
    W, H = 640, 50 + len(groups) * 38 + 20
    L, R = 110, 560
    vals = [v for g in groups for v in g["values"]]
    lo, hi = s.get("domain") or (min(vals) * .8, max(vals) * 1.1)
    X = sx(lo, hi, L, R)
    b = _svg(W, H, "箱线")
    for i, g in enumerate(groups):
        vs = sorted(g["values"])
        q1, med, q3 = vs[len(vs) // 4], vs[len(vs) // 2], vs[3 * len(vs) // 4]
        p10, p90 = vs[max(0, int(len(vs) * .1))], vs[min(len(vs) - 1, int(len(vs) * .9))]
        y = 56 + i * 38
        b.append(t(20, y + 4, g["label"], 8, INK2))
        b.append(ln(X(p10), y, X(p90), y, LINE2, 1))
        b.append(ln(X(p10), y - 4, X(p10), y + 4, LINE2, 1))
        b.append(ln(X(p90), y - 4, X(p90), y + 4, LINE2, 1))
        b.append(rc(X(q1), y - 6, X(q3) - X(q1), 12, INK2, opacity=".8", rx=1))
        b.append(ln(X(med), y - 8, X(med), y + 8, WHITE, 2))
        b.append(t(X(q3) + 8, y + 4, f"{med:.0f}", 7.4, INK, 600))
    b.append("</svg>")
    return "".join(b)


def _scatter(s: dict) -> str:
    pts = s["points"]
    W, H = 640, 350
    L, R, T, B = 74, 570, 50, 274
    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    X = sx(min(xs) * .95, max(xs) * 1.05, L, R)
    Y = sy(min(ys) * .9, max(ys) * 1.08, B, T)
    b = _svg(W, H, "散点")
    for k in range(4):
        v = min(ys) + (max(ys) - min(ys)) * k / 3
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, f"{v:.0f}" if v >= 10 else f"{v:.1f}", 7, FAINT, anchor="end"))
    for p in pts:
        hot = p.get("hot")
        b.append(ci(X(p["x"]), Y(p["y"]), 4.4 if hot else 3, ACCENT if hot else INK2, WHITE, 1))
        if p.get("label"):
            b.append(t(X(p["x"]) + 7, Y(p["y"]) - 6, p["label"], 7, INK2, halo=True))
    b.append("</svg>")
    return "".join(b)


RENDERERS = {"slope": _slope, "dumbbell": _dumbbell, "small_mult": _small_mult,
             "box": _box, "scatter": _scatter}

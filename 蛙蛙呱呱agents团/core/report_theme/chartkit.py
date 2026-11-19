# -*- coding: utf-8 -*-
"""core.report_theme.chartkit —— 自包含 SVG 基元 + 通用图型。

由 sample_fruit/charts.py 的基元与 seasoning_v3/charts.py 的通用图型固化而来，
不依赖 workspace。项目自带的 charts.py 只需 `from core.report_theme import chartkit`
再写自己的数据。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

INK = "var(--ink)"
INK2 = "var(--ink2)"
MUTED = "var(--muted)"
FAINT = "var(--faint)"
LINE = "var(--line)"
ACCENT = "#C0392B"
BLUE = "#2C5F8A"
GRAY = "#8E99A5"

# --------------------------------------------------------------------------- #
# 基元
# --------------------------------------------------------------------------- #
def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))
def svg(w: int, h: int, label: str, body: list[str] | None = None) -> str:
    head = (f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{esc(label)}" preserveAspectRatio="xMidYMid meet">')
    if body is None:
        return head
    return head + "".join(body) + "</svg>"
def t(x, y, s, size=11, fill=INK, anchor="start", weight=400,
      opacity=None, ls=None, halo=False) -> str:
    a = (f'x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
         f'text-anchor="{anchor}"')
    if weight:
        a += f' font-weight="{weight}"'
    if opacity is not None:
        a += f' opacity="{opacity}"'
    if ls:
        a += f' letter-spacing="{ls}"'
    if halo:
        a += ' paint-order="stroke" stroke="#FFFFFF" stroke-width="3.2" stroke-linejoin="round"'
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
def circ(cx, cy, r, fill, stroke=None, sw=1, opacity=None) -> str:
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"{s}{o}/>'
def path(d, fill="none", stroke=None, w=1, dash=None, opacity=None) -> str:
    s = f' stroke="{stroke}" stroke-width="{w}"' if stroke else ""
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    o = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<path d="{d}" fill="{fill}"{s}{ds}{o}/>'
def hit(tip: str, inner: str = "") -> str:
    """Hoverable group; transparent hit area is supplied by the shape itself."""
    return f'<g class="hit" data-tip="{esc(tip)}">{inner}</g>'
def f2(v: float) -> str:
    return f"{v:,.2f}"

# --------------------------------------------------------------------------- #
# 通用图型
# --------------------------------------------------------------------------- #
def hbar(items, unit="", maxv=None, accent=0, note="") -> str:
    """items: [(label, value, note)]"""
    W = 640
    H = 80 + len(items) * 50
    L, R = 180, 540
    mx = maxv or max(max(v for _, v, _ in items), 0) * 1.18
    b = [svg(W, H, "横向条形图")]
    for i, (label, value, sub) in enumerate(items):
        y = 54 + i * 50
        b.append(t(20, y + 4, label, 10, INK2))
        if sub:
            b.append(t(20, y + 18, sub, 8.4, FAINT))
        b.append(hit(f"{label}：{value:g} {unit}",
                     rc(L, y - 10, max((value / mx) * (R - L), 2), 20,
                        ACCENT if i == accent else INK2, rx=2)))
        b.append(t(L + (value / mx) * (R - L) + 8, y + 4,
                   f"{value:,.1f}".rstrip("0").rstrip("."), 11, INK, weight=700))
    if unit:
        b.append(t(L, 26, unit, 8.5, FAINT))
    if note:
        b.append(t(20, H - 12, note, 8.2, MUTED))
    b.append(ln(L, H - 28, L, 36, "var(--line2)", 1))
    return "".join(b) + "</svg>"
def range_bar(rows, unit="", minv=0, maxv=None) -> str:
    """rows: [(label, low, high, note)]"""
    W = 640
    H = 84 + len(rows) * 54
    L, R = 190, 540
    lo = minv if minv is not None else min(min(r[1] for r in rows), 0)
    hi = maxv or max(max(r[2] for r in rows), 1) * 1.12

    def X(v):
        return L + (v - lo) / (hi - lo) * (R - L)

    b = [svg(W, H, "区间图")]
    for i, (label, low, high, note) in enumerate(rows):
        y = 58 + i * 54
        b.append(t(20, y + 4, label, 9.8, INK2))
        if note:
            b.append(t(20, y + 18, note, 8.2, FAINT))
        b.append(ln(X(low), y, X(high), y, "var(--line2)", 4, cap="round"))
        b.append(circ(X(low), y, 4.5, GRAY))
        b.append(circ(X(high), y, 4.5, ACCENT))
        b.append(t(X(low) - 8, y + 4, f"{low:,.1f}", 9.2, MUTED, anchor="end"))
        b.append(t(X(high) + 8, y + 4, f"{high:,.1f}", 9.4, INK, weight=700))
    if unit:
        b.append(t(L, 26, unit, 8.5, FAINT))
    b.append(t(600, H - 14, "灰点 = 下限  ·  红点 = 上限", 8, FAINT, anchor="end"))
    return "".join(b) + "</svg>"
def share_bar(segments, unit="%") -> str:
    """segments: [(label, pct, color)]"""
    W, H = 640, 190
    L, R = 30, 610
    total = sum(v for _, v, _ in segments)
    b = [svg(W, H, "占比条")]
    x = L
    for label, pct, col in segments:
        w = (pct / total) * (R - L)
        b.append(hit(f"{label}：{pct:g}{unit}", rc(x, 58, w, 34, col, rx=2)))
        b.append(t(x + w / 2, 79, f"{pct:g}{unit}", 12, "#FFFFFF", anchor="middle", weight=700))
        b.append(t(x + w / 2, 112, label, 9, INK2, anchor="middle"))
        x += w
    b.append(t(L, 30, "构成", 8.5, FAINT))
    return "".join(b) + "</svg>"
def grouped_bar(groups, series, unit="", colors=None) -> str:
    """groups: [(label, [v1, v2])], series: [name1, name2]"""
    W, H = 640, 330
    L, R, T, B = 76, 590, 42, 260
    n = len(groups)
    nser = len(series)
    mx = max(max(vs) for _, vs in groups) * 1.16
    colors = colors or [ACCENT, BLUE, GRAY]

    def Y(v):
        return B - v / mx * (B - T)

    b = [svg(W, H, "分组条形图")]
    for gv in (0, mx / 2, mx):
        b.append(ln(L, Y(gv), R, Y(gv), LINE, 1))
        b.append(t(L - 8, Y(gv) + 4, f"{gv:,.0f}", 8.2, FAINT, anchor="end"))
    zone = (R - L) / n
    bw = min(zone / (nser + 1), 42)
    for i, (label, vals) in enumerate(groups):
        cx = L + zone * i + zone / 2
        for j, v in enumerate(vals):
            x = cx - (nser * bw) / 2 + j * bw
            b.append(hit(f"{label} · {series[j]}：{v:g}{unit}", rc(x, Y(v), bw - 3, B - Y(v), colors[j])))
            b.append(t(x + (bw - 3) / 2, Y(v) - 7, f"{v:g}", 9.4, INK, anchor="middle", weight=600))
        b.append(t(cx, B + 18, label, 9, INK2, anchor="middle"))
    # legend
    lx = 420
    for j, name in enumerate(series):
        b.append(circ(lx, 24, 4, colors[j]))
        b.append(t(lx + 8, 27, name, 8.4, MUTED))
        lx += 86
    if unit:
        b.append(t(L, 24, unit, 8.4, FAINT))
    return "".join(b) + "</svg>"
def cost_range(rows, unit="元/公斤") -> str:
    """rows: [(label, cost, price)]"""
    W, H = 640, 90 + len(rows) * 50
    L, R = 190, 530
    mx = max(max(p for _, _, p in rows), 1) * 1.15

    def X(v):
        return L + v / mx * (R - L)

    b = [svg(W, H, "成本到价格区间")]
    for i, (label, cost, price) in enumerate(rows):
        y = 56 + i * 50
        b.append(t(20, y + 4, label, 9.6, INK2))
        b.append(ln(X(cost), y, X(price), y, "var(--line2)", 3, cap="round"))
        b.append(circ(X(cost), y, 4.5, GRAY))
        b.append(circ(X(price), y, 5, ACCENT))
        b.append(t(X(cost) - 7, y + 4, f"{cost:g}", 9, MUTED, anchor="end"))
        b.append(t(X(price) + 7, y + 4, f"{price:g}", 9.4, INK, weight=700))
    if unit:
        b.append(t(L, 26, unit, 8.4, FAINT))
    return "".join(b) + "</svg>"

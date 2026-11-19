# -*- coding: utf-8 -*-
"""core.charts.consulting —— consulting 主题的 13 型确定性 SVG 图表。

这些不是 v2（matplotlib）的替代，而是「A4 页式 + 咨询白底」这一出口的
图表语法：更少的墨、直接标注、一图一结论。注册在 CONSULTING_RENDERERS，
由 core.report_theme.pages 调用；v2 的 48 型能力不退化。

约定：输入 chart dict 尽量复用既有契约字段（bars / groups / rows / points /
series / steps），不要求调用方改数据；缺字段返回空图而不是抛异常。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

INK = "var(--ink)"
INK2 = "var(--ink2)"
MUTED = "var(--muted)"
FAINT = "var(--faint)"
LINE = "var(--line)"
LINE2 = "var(--line2)"
ACCENT = "var(--accent)"
BLUE = "var(--blue)"
GRAY = "var(--gray)"
PAPER = "var(--paper)"


def _esc(s: Any) -> str:
    return ("" if s is None else str(s)).replace("&", "&amp;").replace("<", "&lt;") \
        .replace(">", "&gt;").replace('"', "&quot;")


def _open(w: int, h: int, label: str) -> str:
    return (f'<svg class="chart" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{_esc(label)}" preserveAspectRatio="xMidYMid meet">')


def _svg(w: int, h: int, label: str, body: List[str]) -> str:
    return _open(w, h, label) + "".join(body) + "</svg>"


def _t(x, y, s, size=10, fill=INK, anchor="start", weight=400, opacity=None, halo=False) -> str:
    a = f'x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"'
    if weight:
        a += f' font-weight="{weight}"'
    if opacity is not None:
        a += f' opacity="{opacity}"'
    if halo:
        a += ' paint-order="stroke" stroke="#FFFFFF" stroke-width="3" stroke-linejoin="round"'
    return f"<text {a}>{_esc(s)}</text>"


def _ln(x1, y1, x2, y2, stroke=LINE, w=1, dash=None, cap="butt") -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{w}" stroke-linecap="{cap}"{d}/>')


def _rc(x, y, w, h, fill, rx=0, stroke=None, sw=1, opacity=None) -> str:
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o = f' opacity="{opacity}"' if opacity is not None else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="{rx}" fill="{fill}"{s}{o}/>')


def _circ(cx, cy, r, fill, stroke=None, sw=1, opacity=None) -> str:
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"{s}{o}/>'


def _hit(tip: str, inner: str) -> str:
    return f'<g class="hit" data-tip="{_esc(tip)}">{inner}</g>'


def _num(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _items(ch: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = ch.get("bars") or ch.get("items") or []
    out = []
    for x in raw:
        if isinstance(x, dict):
            out.append({"label": str(x.get("label", "")), "value": _num(x.get("value")),
                        "note": str(x.get("note", ""))})
        elif isinstance(x, (list, tuple)) and len(x) >= 2:
            out.append({"label": str(x[0]), "value": _num(x[1]), "note": ""})
    return out


# --------------------------------------------------------------------------- #
def hbar(chart: Dict[str, Any], theme: str = "consulting") -> str:
    items = _items(chart)
    if not items:
        return ""
    W, H = 640, 70 + len(items) * 48
    L, R = 180, 545
    mx = max([it["value"] for it in items] or [1]) * 1.18 or 1
    b = [_open(W, H, chart.get("title", "条形图"))]
    b.append(_t(L, 24, chart.get("unit_meta", ""), 8.5, FAINT))
    for i, it in enumerate(items):
        y = 52 + i * 48
        b.append(_t(20, y + 4, it["label"], 10, INK2))
        if it["note"]:
            b.append(_t(20, y + 18, it["note"], 8.2, FAINT))
        w = max((it["value"] / mx) * (R - L), 2)
        b.append(_hit(f'{it["label"]}：{it["value"]:g}',
                      _rc(L, y - 9, w, 18, ACCENT if i == 0 else INK2, rx=2)))
        b.append(_t(L + w + 8, y + 4, f'{it["value"]:,.1f}'.rstrip("0").rstrip("."), 10.6, INK, weight=700))
    b.append("</svg>")
    return "".join(b)


def grouped_bar(chart: Dict[str, Any], theme: str = "consulting") -> str:
    groups = chart.get("groups") or []
    series = chart.get("series") or ["A", "B"]
    if not groups:
        return ""
    W, H = 640, 320
    L, R, T, B = 75, 585, 45, 255
    vals = [v for g in groups for v in (g[1] if isinstance(g, (list, tuple)) else g.get("values", []))]
    mx = max(vals or [1]) * 1.16 or 1
    colors = [ACCENT, BLUE, GRAY]

    def Y(v):
        return B - v / mx * (B - T)

    b = [_open(W, H, chart.get("title", "分组柱"))]
    for gv in (0, mx / 2, mx):
        b.append(_ln(L, Y(gv), R, Y(gv), LINE, 1))
        b.append(_t(L - 8, Y(gv) + 4, f"{gv:,.0f}", 8.2, FAINT, anchor="end"))
    zone = (R - L) / len(groups)
    bw = min(zone / (len(series) + 1), 42)
    for i, g in enumerate(groups):
        label, vs = (g[0], g[1]) if isinstance(g, (list, tuple)) else (g.get("label", ""), g.get("values", []))
        cx = L + zone * i + zone / 2
        for j, v in enumerate(vs):
            x = cx - (len(series) * bw) / 2 + j * bw
            b.append(_hit(f"{label} · {series[j]}：{v:g}",
                          _rc(x, Y(_num(v)), bw - 3, B - Y(_num(v)), colors[j % len(colors)])))
            b.append(_t(x + (bw - 3) / 2, Y(_num(v)) - 7, f"{_num(v):g}", 9.2, INK,
                        anchor="middle", weight=600))
        b.append(_t(cx, B + 18, label, 8.8, INK2, anchor="middle"))
    lx = 400
    for j, name in enumerate(series):
        b.append(_circ(lx, 24, 4, colors[j % len(colors)]))
        b.append(_t(lx + 8, 27, name, 8.2, MUTED))
        lx += 82
    b.append("</svg>")
    return "".join(b)


def _rows(chart: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = chart.get("rows") or chart.get("pairs") or []
    out = []
    for x in raw:
        if isinstance(x, dict):
            out.append(x)
        elif isinstance(x, (list, tuple)) and len(x) >= 3:
            out.append({"label": x[0], "a": _num(x[1]), "b": _num(x[2])})
    return out


def two_point(chart: Dict[str, Any], theme: str = "consulting") -> str:
    rows = _rows(chart)
    if not rows:
        return ""
    mode = "slope" if str(chart.get("type")) == "slope" else "dumbbell"
    W, H = 640, 80 + len(rows) * 50
    L, R = 150, 515
    vals = [v for r in rows for v in (_num(r.get("a")), _num(r.get("b")))]
    lo, hi = min(vals or [0]), max(vals or [1])
    if hi == lo:
        hi = lo + 1
    b = [_open(W, H, chart.get("title", "两点对比"))]
    for i, r in enumerate(rows):
        y = 58 + i * 48
        a, z = _num(r.get("a")), _num(r.get("b"))
        b.append(_t(20, y + 4, str(r.get("label", "")), 9.8, INK2))
        if mode == "slope":
            x1, x2 = 230, 430
            y1 = 250 - (a - lo) / (hi - lo) * 190
            y2 = 250 - (z - lo) / (hi - lo) * 190
            b.append(_hit(f'{r.get("label")}：{a:g} → {z:g}',
                          f'<line x1="{x1}" y1="{y1:.1f}" x2="{x2}" y2="{y2:.1f}" stroke="{ACCENT}" stroke-width="2.4"/>'
                          + _circ(x1, y1, 4.5, ACCENT) + _circ(x2, y2, 4.5, BLUE)))
            b.append(_t(x1 - 8, y1 + 4, f"{a:g}", 9.2, INK, anchor="end"))
            b.append(_t(x2 + 8, y2 + 4, f"{z:g}", 9.2, INK))
        else:
            x1 = L + (a - lo) / (hi - lo) * (R - L)
            x2 = L + (z - lo) / (hi - lo) * (R - L)
            b.append(_ln(x1, y, x2, y, LINE2, 3, cap="round"))
            b.append(_hit(f'{r.get("label")}：{a:g}', _circ(x1, y, 5, GRAY)))
            b.append(_hit(f'{r.get("label")}：{z:g}', _circ(x2, y, 5, ACCENT)))
            b.append(_t(x1 - 8, y + 4, f"{a:g}", 9.2, MUTED, anchor="end"))
            b.append(_t(x2 + 8, y + 4, f"{z:g}", 9.4, INK, weight=700))
    b.append("</svg>")
    return "".join(b)


def range_bar(chart: Dict[str, Any], theme: str = "consulting") -> str:
    rows = chart.get("rows") or []
    if not rows:
        return ""
    W, H = 640, 80 + len(rows) * 52
    L, R = 180, 530
    lows = [_num(r.get("low")) for r in rows]
    highs = [_num(r.get("high")) for r in rows]
    lo, hi = min(lows + [0]), max(highs or [1])
    if hi == lo:
        hi = lo + 1

    def X(v):
        return L + (v - lo) / (hi - lo) * (R - L)

    b = [_open(W, H, chart.get("title", "区间图"))]
    for i, r in enumerate(rows):
        y = 56 + i * 52
        low, high = _num(r.get("low")), _num(r.get("high"))
        b.append(_t(20, y + 4, str(r.get("label", "")), 9.6, INK2))
        if r.get("note"):
            b.append(_t(20, y + 18, str(r.get("note")), 8, FAINT))
        b.append(_ln(X(low), y, X(high), y, LINE2, 4, cap="round"))
        b.append(_circ(X(low), y, 4.5, GRAY))
        b.append(_circ(X(high), y, 4.5, ACCENT))
        b.append(_t(X(low) - 8, y + 4, f"{low:g}", 9, MUTED, anchor="end"))
        b.append(_t(X(high) + 8, y + 4, f"{high:g}", 9.2, INK, weight=700))
    b.append("</svg>")
    return "".join(b)


def share(chart: Dict[str, Any], theme: str = "consulting") -> str:
    segs = chart.get("segments") or chart.get("parts") or []
    if not segs:
        return ""
    W, H = 640, 180
    L, R = 30, 610
    total = sum(_num(s.get("value", s.get("pct", 0))) for s in segs) or 1
    b = [_open(W, H, chart.get("title", "构成"))]
    x = L
    colors = [ACCENT, GRAY, BLUE, "#B08D57"]
    for i, s in enumerate(segs):
        v = _num(s.get("value", s.get("pct", 0)))
        w = v / total * (R - L)
        b.append(_hit(f'{s.get("label")}：{v:g}',
                      _rc(x, 55, w, 34, colors[i % len(colors)], rx=2)))
        b.append(_t(x + w / 2, 76, f"{v:g}%", 11.5, "#FFFFFF", anchor="middle", weight=700))
        b.append(_t(x + w / 2, 108, str(s.get("label", "")), 8.8, INK2, anchor="middle"))
        x += w
    b.append("</svg>")
    return "".join(b)


def waterfall(chart: Dict[str, Any], theme: str = "consulting") -> str:
    steps = chart.get("steps") or []
    if not steps:
        return ""
    W = 640
    H = 80 + len(steps) * 44
    L, R = 175, 520
    vals = []
    run = 0.0
    parsed = []
    for s in steps:
        kind = str(s.get("kind") or ("total" if s.get("total") else "delta"))
        if kind in ("start", "base"):
            v = _num(s.get("value"))
            run = v
        elif kind in ("end", "total"):
            v = _num(s.get("value"))
            run = v
        else:
            v = _num(s.get("delta", s.get("value")))
            run += v
        parsed.append((str(s.get("label", "")), v, kind, run))
        vals.append(run)
    mx = max(vals + [1]) * 1.15

    def X(v):
        return L + v / mx * (R - L)

    b = [_open(W, H, chart.get("title", "瀑布图"))]
    for i, (label, v, kind, run) in enumerate(parsed):
        y = 52 + i * 44
        if kind == "delta":
            xa, xb = X(run - v), X(run)
            x0, x1 = min(xa, xb), max(xa, xb)
            col = ACCENT if v >= 0 else GRAY
        else:
            x0, x1 = X(0), X(run)
            col = INK2
        b.append(_t(20, y + 4, label, 9.4, INK2))
        b.append(_hit(f"{label}：{v:+g}" if kind == "delta" else f"{label}：{v:g}",
                      _rc(x0, y - 9, max(x1 - x0, 2), 18, col, rx=2)))
        txt = f"{v:+g}" if kind == "delta" else f"{v:g}"
        b.append(_t(x1 + 8, y + 4, txt, 9.8, INK, weight=700))
    b.append("</svg>")
    return "".join(b)


def bubble(chart: Dict[str, Any], theme: str = "consulting") -> str:
    pts = chart.get("points") or []
    if not pts:
        return ""
    W, H = 640, 340
    L, R, T, B = 70, 600, 40, 290
    xs = [_num(p.get("x")) for p in pts]
    ys = [_num(p.get("y")) for p in pts]
    x0, x1 = min(xs), max(xs) or 1
    y0, y1 = min(ys + [0]), max(ys)
    if x1 == x0:
        x1 = x0 + 1
    if y1 == y0:
        y1 = y0 + 1

    def X(v):
        return L + (v - x0) / (x1 - x0) * (R - L)

    def Y(v):
        return B - (v - y0) / (y1 - y0) * (B - T)

    b = [_open(W, H, chart.get("title", "气泡图"))]
    for i, p in enumerate(pts):
        x, y = X(_num(p.get("x"))), Y(_num(p.get("y")))
        r = 6 + math.sqrt(max(_num(p.get("size"), 1), 1)) * 1.4
        b.append(_hit(f'{p.get("label")}：{_num(p.get("y")):g}',
                      _circ(x, y, r, ACCENT, opacity=.18) + _circ(x, y, 3.4, ACCENT)))
        b.append(_t(x + 10, y - 8, str(p.get("label", "")), 8.8, INK2, weight=600))
    b.append(_t(L, H - 12, chart.get("unit_meta", ""), 8, FAINT))
    b.append("</svg>")
    return "".join(b)


def coverage(chart: Dict[str, Any], theme: str = "consulting") -> str:
    rows = chart.get("rows") or []
    cols = chart.get("columns") or []
    if not rows or not cols:
        return ""
    W, H = 640, 80 + len(rows) * 28
    L = 155
    step = min(78, (620 - L) / max(len(cols), 1))
    b = [_open(W, H, chart.get("title", "覆盖矩阵"))]
    for j, c in enumerate(cols):
        b.append(_t(L + j * step, 30, str(c), 8.2, MUTED, anchor="middle"))
    b.append(_ln(140, 42, 620, 42, LINE2, 1))
    for i, r in enumerate(rows):
        y = 64 + i * 28
        b.append(_t(20, y + 4, str(r.get("label", "")), 9.2, INK2,
                    weight=600 if i < 6 else 400))
        for j, v in enumerate(r.get("values") or []):
            x = L + j * step
            if v:
                b.append(_circ(x, y, 5.2, ACCENT))
            else:
                b.append(_circ(x, y, 4.8, "#FFFFFF", stroke=LINE2, sw=1))
    b.append("</svg>")
    return "".join(b)


def yoy(chart: Dict[str, Any], theme: str = "consulting") -> str:
    items = chart.get("items") or chart.get("bars") or []
    if not items:
        return ""
    W, H = 640, 70 + len(items) * 36
    C = 330
    ppu = 11.0
    vals = [_num(x.get("value", x.get("pct", 0))) for x in items]
    b = [_open(W, H, chart.get("title", "同比"))]
    for i, it in enumerate(items):
        y = 50 + i * 36
        v = _num(it.get("value", it.get("pct", 0)))
        b.append(_t(180, y + 4, str(it.get("label", "")), 9.4, INK2, anchor="end"))
        x0, x1 = (C, C + v * ppu) if v >= 0 else (C + v * ppu, C)
        b.append(_hit(f'{it.get("label")}：{v:+.1f}%',
                      _rc(x0, y - 8, max(x1 - x0, 2), 16, ACCENT if v >= 0 else GRAY, rx=2)))
        if v >= 0:
            b.append(_t(x1 + 6, y + 4, f"{v:+.1f}%", 9.4, ACCENT, weight=700))
        else:
            b.append(_t(C - 6, y + 4, f"{v:+.1f}%", 8.8, "#FFFFFF", anchor="end", weight=700))
    b.append(_ln(C, 36, C, H - 16, LINE2, 1))
    b.append("</svg>")
    return "".join(b)


def fan(chart: Dict[str, Any], theme: str = "consulting") -> str:
    series = chart.get("series") or []
    xlabels = chart.get("xlabels") or []
    if not series:
        return ""
    W, H = 640, 310
    L, R, T, B = 80, 545, 45, 255
    allv = [v for s in series for v in (s.get("values") or [])]
    if not allv:
        return ""
    lo, hi = min(allv), max(allv)
    if hi == lo:
        hi = lo + 1
    n = max(len(xlabels), max(len(s.get("values") or []) for s in series))

    def X(i):
        return L + (i / max(n - 1, 1)) * (R - L)

    def Y(v):
        return B - (v - lo) / (hi - lo) * (B - T)

    b = [_open(W, H, chart.get("title", "趋势"))]
    colors = [INK, GRAY, LINE2, ACCENT]
    for k, s in enumerate(series):
        pts = " ".join(f"{X(i):.1f},{Y(_num(v)):.1f}" for i, v in enumerate(s.get("values") or []))
        b.append(f'<polyline points="{pts}" fill="none" stroke="{colors[k % len(colors)]}" '
                 f'stroke-width="{2.2 if k == 0 else 1.4}" stroke-dasharray="{"" if k == 0 else "5 4"}"/>')
    for i, lab in enumerate(xlabels):
        b.append(_t(X(i), B + 20, str(lab), 8, FAINT, anchor="middle"))
    b.append("</svg>")
    return "".join(b)


def path_matrix(chart: Dict[str, Any], theme: str = "consulting") -> str:
    pts = chart.get("points") or []
    if not pts:
        return ""
    W, H = 640, 340
    L, R, T, B = 85, 595, 45, 285
    xs = [_num(p.get("x")) for p in pts]
    ys = [_num(p.get("y")) for p in pts]
    x0, x1 = min(xs + [0]), max(xs)
    y0, y1 = min(ys + [0]), max(ys)
    if x1 == x0:
        x1 = x0 + 1
    if y1 == y0:
        y1 = y0 + 1

    def X(v):
        return L + (v - x0) / (x1 - x0) * (R - L)

    def Y(v):
        return B - (v - y0) / (y1 - y0) * (B - T)

    b = [_open(W, H, chart.get("title", "矩阵"))]
    for i, p in enumerate(pts):
        b.append(_hit(f'{p.get("label")}：x {_num(p.get("x")):g} / y {_num(p.get("y")):g}',
                      _circ(X(_num(p.get("x"))), Y(_num(p.get("y"))), 7, ACCENT, opacity=.16)
                      + _circ(X(_num(p.get("x"))), Y(_num(p.get("y"))), 3.6, ACCENT)))
        b.append(_t(X(_num(p.get("x"))) + 10, Y(_num(p.get("y"))) - 8,
                    str(p.get("label", "")), 8.6, INK2, weight=600))
    b.append("</svg>")
    return "".join(b)


def gantt(chart: Dict[str, Any], theme: str = "consulting") -> str:
    tasks = chart.get("tasks") or []
    if not tasks:
        return ""
    weeks = int(chart.get("weeks") or max(int(_num(t.get("end"), 1)) for t in tasks) or 6)
    W, H = 640, 80 + len(tasks) * 38
    L, R = 210, 600
    b = [_open(W, H, chart.get("title", "甘特图"))]
    for w in range(weeks):
        x = L + w / weeks * (R - L)
        b.append(_ln(x, 40, x, H - 30, LINE, 1))
        b.append(_t(x + (R - L) / weeks / 2, 30, f"W{w+1}", 7.4, FAINT, anchor="middle"))
    for i, t in enumerate(tasks):
        y = 56 + i * 38
        start = max(int(_num(t.get("start"), 1)), 1)
        end = max(int(_num(t.get("end"), start)), start)
        x = L + (start - 1) / weeks * (R - L)
        w = (end - start + 1) / weeks * (R - L)
        b.append(_t(20, y + 4, str(t.get("label", "")), 8.8, INK2))
        b.append(_hit(f'{t.get("label")}：W{start}–W{end}',
                      _rc(x, y - 6, w, 12, ACCENT, rx=2, opacity=.9)))
    b.append("</svg>")
    return "".join(b)


def pareto(chart: Dict[str, Any], theme: str = "consulting") -> str:
    items = _items(chart)
    if not items:
        return ""
    items = sorted(items, key=lambda x: abs(x["value"]), reverse=True)
    total = sum(abs(x["value"]) for x in items) or 1
    W, H = 640, 80 + len(items) * 42
    L, R = 180, 520
    mx = max(abs(x["value"]) for x in items) or 1
    b = [_open(W, H, chart.get("title", "帕累托图"))]
    run = 0.0
    for i, it in enumerate(items):
        y = 54 + i * 42
        w = abs(it["value"]) / mx * (R - L)
        run += abs(it["value"])
        b.append(_t(20, y + 4, it["label"], 9.4, INK2))
        b.append(_hit(f'{it["label"]}：{it["value"]:g}',
                      _rc(L, y - 8, max(w, 2), 16, ACCENT if i < 3 else INK2, rx=2)))
        b.append(_t(L + w + 8, y + 4, f'{it["value"]:g}', 9.6, INK, weight=700))
        b.append(_t(R + 36, y + 4, f"{run / total * 100:.0f}%", 8.4, MUTED))
    b.append("</svg>")
    return "".join(b)


def line(chart: Dict[str, Any], theme: str = "consulting") -> str:
    series = chart.get("series") or []
    xlabels = chart.get("xlabels") or []
    if not series:
        return ""
    W, H = 640, 300
    L, R, T, B = 75, 590, 42, 250
    vals = [v for s in series for v in (s.get("values") or [])]
    if not vals:
        return ""
    lo, hi = min(vals), max(vals)
    if hi == lo:
        hi = lo + 1
    n = len(xlabels) or max(len(s.get("values") or []) for s in series)

    def X(i):
        return L + i / max(n - 1, 1) * (R - L)

    def Y(v):
        return B - (v - lo) / (hi - lo) * (B - T)

    b = [_open(W, H, chart.get("title", "折线"))]
    for k, s in enumerate(series):
        pts = " ".join(f"{X(i):.1f},{Y(_num(v)):.1f}" for i, v in enumerate(s.get("values") or []))
        b.append(f'<polyline points="{pts}" fill="none" stroke="{ACCENT if k == 0 else BLUE}" '
                 f'stroke-width="2.4"/>')
    for i, lab in enumerate(xlabels):
        b.append(_t(X(i), B + 18, str(lab), 8, FAINT, anchor="middle"))
    b.append("</svg>")
    return "".join(b)


RENDERERS = {
    "hbar": hbar, "vbar": hbar, "bar": hbar,
    "grouped_bar": grouped_bar,
    "dumbbell": two_point, "slope": two_point,
    "range": range_bar, "error_bar": range_bar,
    "share": share, "stacked_bar": share, "pct_stacked": share,
    "waterfall": waterfall, "bridge": waterfall, "pareto": pareto,
    "bubble": bubble, "scatter": bubble,
    "coverage": coverage, "coverage_matrix": coverage, "heatmap": coverage,
    "yoy": yoy, "diverging": yoy,
    "fan": fan, "forecast": fan,
    "path_matrix": path_matrix,
    "gantt": gantt,
    "line": line, "area": line,
}


def supports(t: str) -> bool:
    return t in RENDERERS


def render(chart: Dict[str, Any], theme: str = "consulting") -> str:
    t = str(chart.get("type") or "")
    fn = RENDERERS.get(t)
    if not fn:
        if chart.get("bars") or chart.get("items"):
            fn = hbar
        elif chart.get("series"):
            fn = line
        else:
            return ""
    try:
        return fn(chart, theme)
    except Exception:
        return ""

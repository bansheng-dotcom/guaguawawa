# -*- coding: utf-8 -*-
"""charts_pro.spec —— 参数化图表层：{type, data, annotations} → SVG。

项目侧不再写 SVG / 坐标：facts 里给一段 spec，render(spec) 出图。
    render({"type": "hbar", "items": [{"label": "…", "value": 96.4}], "ref": 62.7})
"""
from __future__ import annotations

import math

from .prokit_helpers import (
    ACCENT, BLUE, INK, INK2, LINE, LINE2, MUTED, FAINT, WHITE,
    blend, ci, ln, pa, rc, sx, sy, t,
)

TINTS = ["#1F2A37", "#3D4B58", "#5C6A76", "#7B8792", "#9BA4AD", "#BCC3C9"]


def _svg(w, h, label):
    return [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{label}" preserveAspectRatio="xMidYMid meet">']


def _nice_step(v: float) -> float:
    """刻度间隔归到 1/2/2.5/5 × 10^k，避免 354 / 709 / 1063 这种刻度。"""
    if v <= 0:
        return 1.0
    k = math.floor(math.log10(v))
    base = 10 ** k
    for m in (1, 2, 2.5, 5, 10):
        if v <= m * base:
            return m * base
    return 10 * base


def _hbar(s: dict) -> str:
    items = sorted(s["items"], key=lambda x: -x["value"])
    dec = s.get("decimals", 1)
    W, H = 640, 60 + len(items) * 34
    L, R = 150, 596
    hi0 = s.get("max") or max(i["value"] for i in items) * 1.08
    step = _nice_step(hi0 / 4)
    mx = math.ceil(hi0 / step) * step
    X = sx(0, mx, L, R)
    b = _svg(W, H, s.get("label", "排序条形"))
    v = 0.0
    while v <= mx + 1e-9:
        b.append(ln(X(v), 36, X(v), 26 + len(items) * 34, LINE, 1))
        b.append(t(X(v), 26 + len(items) * 34 + 16,
                   f"{v:.0f}" if v >= 10 else f"{v:g}", 7, FAINT, anchor="middle"))
        v += step
    if s.get("ref") is not None:
        b.append(ln(X(s["ref"]), 36, X(s["ref"]), 26 + len(items) * 34, LINE2, 1, "3 3"))
        b.append(t(X(s["ref"]), 30, s.get("ref_label", "参照"), 7, MUTED, anchor="middle"))
    accent = s.get("accent", 0)
    for i, it in enumerate(items):
        y = 50 + i * 34
        b.append(t(20, y + 4, it["label"], 8.6, INK2))
        if it.get("sub"):
            b.append(t(20, y + 16, it["sub"], 7, FAINT))
        hot = (i == accent) or (isinstance(accent, str) and it["label"] == accent)
        b.append(rc(L, y - 8, max(X(it["value"]) - L, 2), 16,
                    ACCENT if hot else INK2, rx=1.5))
        b.append(t(X(it["value"]) + 8, y + 4, f"{it['value']:.{dec}f}", 8.6, INK, 700, halo=True))
    note = str(s.get("accent_note") or "").strip()
    if note:
        b.append(t(R, 26, note, 7.2, ACCENT, anchor="end"))
    b.append("</svg>")
    return "".join(b)


def _dot(s: dict) -> str:
    items = sorted(s["points"], key=lambda x: -x["value"])
    dec = s.get("decimals", 1)
    W, H = 640, 46 + len(items) * 26 + 40
    L, R = 130, 590
    vals = [i["value"] for i in items]
    lo, hi = s.get("domain") or (min(vals) * .9, max(vals) * 1.05)
    X = sx(lo, hi, L, R)
    b = _svg(W, H, s.get("label", "点图"))
    band = s.get("band")
    if band:
        b.append(rc(X(band[0]), 36, X(band[1]) - X(band[0]), 18 + len(items) * 26, ACCENT, opacity=".06"))
    if s.get("median", True):
        med = sorted(vals)[len(vals) // 2]
        b.append(ln(X(med), 36, X(med), 18 + len(items) * 26, ACCENT, 1, "3 3"))
        b.append(t(X(med) + 4, 30, f"中位 {med:.{dec}f}", 7, ACCENT))
    for i, it in enumerate(items):
        y = 52 + i * 26
        b.append(t(20, y + 4, it["label"], 8, INK2))
        b.append(ln(L, y, X(it["value"]) - 6, y, LINE, 1))
        hot = i == 0 and s.get("accent_top", True)
        b.append(ci(X(it["value"]), y, 4.2, ACCENT if hot else INK2))
        b.append(t(X(it["value"]) + 9, y + 4, f"{it['value']:.{dec}f}", 8, INK, 600, halo=True))
    b.append("</svg>")
    return "".join(b)


def _line(s: dict) -> str:
    pts = s["points"]
    W, H = 640, 330
    L, R, T, B = 64, 590, 48, 256
    ys = [p["value"] for p in pts]
    lo, hi = s.get("domain") or (min(ys) * .92, max(ys) * 1.06)
    Y = sy(lo, hi, B, T)
    X = sx(0, len(pts) - 1, L + 6, R - 6)
    b = _svg(W, H, s.get("label", "折线"))
    for k in range(4):
        v = lo + (hi - lo) * k / 3
        b.append(ln(L, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 8, Y(v) + 3, f"{v:.2f}" if v < 10 else f"{v:.1f}", 7, FAINT, anchor="end"))
    fc = s.get("forecast_from")
    end = fc if fc is not None else len(pts)
    b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(p['value']):.1f}" for i, p in enumerate(pts[:end])),
                "none", INK2, 1.8))
    if fc is not None:
        b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(p['value']):.1f}"
                                      for i, p in enumerate(pts[fc - 1:], start=fc - 1)),
                    "none", MUTED, 1.6, "4 3"))
        b.append(ln(X(fc - 0.5), T, X(fc - 0.5), B, LINE2, 1, "2 3"))
        b.append(t(X(fc - 0.5), T - 6, "预测起点", 7, MUTED, anchor="middle"))
    for i, p in enumerate(pts):
        if i % max(1, len(pts) // 6) == 0 or i == len(pts) - 1:
            b.append(t(X(i), B + 16, p["label"], 7, FAINT, anchor="middle"))
    show_vals = len(pts) <= 10
    for i, p in enumerate(pts):
        b.append(ci(X(i), Y(p["value"]), 3.2, INK2 if i < end else MUTED, WHITE, 1))
        if show_vals:
            b.append(t(X(i), Y(p["value"]) - 9, f"{p['value']:.2f}", 7.4, INK, 600,
                       anchor="middle", halo=True))
    last = pts[-1]
    b.append(ci(X(len(pts) - 1), Y(last["value"]), 4.4, ACCENT, WHITE, 1.2))
    b.append("</svg>")
    return "".join(b)


def _waterfall(s: dict) -> str:
    start = s["start"]
    deltas = s["deltas"]
    end = s.get("end") or start + sum(d["value"] for d in deltas)
    steps = [{"label": s.get("start_label", "期初"), "value": start, "kind": "total"}] + \
            [{"label": d["label"], "value": d["value"], "kind": "d"} for d in deltas] + \
            [{"label": s.get("end_label", "期末"), "value": end, "kind": "total"}]
    W, H = 640, 330
    L, R, T, B = 60, 596, 70, 268
    lo = s.get("floor", min(start, end) * 0.96)
    hi = max(start, end, start + sum(d["value"] for d in deltas)) * 1.04
    Y = sy(lo, hi, B, T)
    slot = (R - L) / len(steps)
    bw = slot * 0.52
    b = _svg(W, H, "瀑布")
    for k in range(4):
        v = lo + (hi - lo) * k / 3
        b.append(ln(L - 6, Y(v), R, Y(v), LINE, 1))
        b.append(t(L - 12, Y(v) + 3, f"{v:.2f}", 7, FAINT, anchor="end"))
    cum = start
    for i, st in enumerate(steps):
        cx = L + slot * i + slot / 2
        if st["kind"] == "total":
            y0, y1, fill = Y(lo), Y(st["value"]), INK
            val = f"{st['value']:.2f}"
        else:
            y0, y1 = Y(cum), Y(cum + st["value"])
            fill = BLUE if st["value"] > 0 else ACCENT
            val = f"{st['value']:+.2f}"
            cum += st["value"]
        b.append(rc(cx - bw / 2, min(y0, y1), bw, max(abs(y1 - y0), 2), fill, rx=1))
        b.append(t(cx, min(y0, y1) - 6, val, 7.6, INK, 600, anchor="middle", halo=True))
        b.append(t(cx, B + 18, st["label"], 7.2, INK2, anchor="middle"))
        if i < len(steps) - 1:
            b.append(ln(cx + bw / 2, min(y0, y1), L + slot * (i + 1) + slot * 0.24,
                        min(y0, y1), LINE2, 1, "2 2"))
    b.append("</svg>")
    return "".join(b)


def _range(s: dict) -> str:
    rows = s["rows"]
    W, H = 640, 46 + len(rows) * 40 + 30
    L, R = 150, 580
    lo, hi = s.get("domain") or (0, max(r["high"] for r in rows) * 1.1)
    X = sx(lo, hi, L, R)
    b = _svg(W, H, "区间")
    for i, r in enumerate(rows):
        y = 50 + i * 40
        b.append(t(20, y + 4, r["label"], 8, INK2))
        if r.get("sub"):
            b.append(t(20, y + 16, r["sub"], 7, FAINT))
        b.append(ln(X(r["low"]), y, X(r["high"]), y, INK2, 3, cap="round"))
        if r.get("mid") is not None:
            b.append(ci(X(r["mid"]), y, 3.4, ACCENT, WHITE, 1.2))
        b.append(t(X(r["low"]) - 8, y + 4, f"{r['low']:g}", 7.2, MUTED, anchor="end"))
        b.append(t(X(r["high"]) + 8, y + 4, f"{r['high']:g}", 7.6, INK, 600))
    b.append("</svg>")
    return "".join(b)


def _heatmap(s: dict) -> str:
    rows, cols, M = s["rows"], s["cols"], s["matrix"]
    cw = min(70, int(520 / max(len(cols), 1)))
    ch = 26
    L, T = 130, 56
    mx = max(max(r) for r in M) or 1
    b = _svg(640, T + len(rows) * ch + 40, "热力矩阵")
    for j, c in enumerate(cols):
        b.append(t(L + cw * j + cw / 2, T - 10, c, 7, MUTED, anchor="middle"))
    for i, r in enumerate(rows):
        y = T + i * ch
        b.append(t(L - 10, y + 17, r, 7.2, INK2, anchor="end"))
        for j in range(len(cols)):
            v = M[i][j]
            b.append(rc(L + cw * j + 1, y + 1, cw - 2, ch - 2, blend(v / mx)))
            b.append(t(L + cw * j + cw / 2, y + 18, f"{v:.0f}", 7,
                       WHITE if v / mx > .55 else INK2, anchor="middle"))
    b.append("</svg>")
    return "".join(b)


def _donut(s: dict) -> str:
    items = sorted(s["items"], key=lambda x: -x["value"])
    total = sum(i["value"] for i in items)
    W, H = 640, 320
    cx, cy, r = 250, 160, 104
    b = _svg(W, H, "环形图")
    a0 = -math.pi / 2
    for i, it in enumerate(items):
        da = it["value"] / total * math.tau
        a1 = a0 + da
        p0 = (cx + r * math.cos(a0), cy + r * math.sin(a0))
        p1 = (cx + r * math.cos(a1), cy + r * math.sin(a1))
        q0 = (cx + 60 * math.cos(a1), cy + 60 * math.sin(a1))
        q1 = (cx + 60 * math.cos(a0), cy + 60 * math.sin(a0))
        large = 1 if da > math.pi else 0
        d = (f"M {p0[0]:.1f},{p0[1]:.1f} A {r},{r} 0 {large} 1 {p1[0]:.1f},{p1[1]:.1f} "
             f"L {q0[0]:.1f},{q0[1]:.1f} A 60,60 0 {large} 0 {q1[0]:.1f},{q1[1]:.1f} Z")
        b.append(f'<path d="{d}" fill="{TINTS[i % 6]}"/>')
        mid = a0 + da / 2
        lx, ly = cx + (r + 18) * math.cos(mid), cy + (r + 18) * math.sin(mid)
        side = "start" if math.cos(mid) > 0 else "end"
        b.append(ln(cx + (r + 2) * math.cos(mid), cy + (r + 2) * math.sin(mid), lx, ly, LINE2, 1))
        b.append(t(lx + (5 if side == "start" else -5), ly + 3,
                   f"{it['label']} {it['value'] / total * 100:.0f}%", 7.2, INK2, anchor=side))
        a0 = a1
    b.append(t(cx, cy - 2, f"{total:.0f}", 20, INK, 700, anchor="middle"))
    b.append(t(cx, cy + 16, s.get("center_label", "合计"), 7.2, MUTED, anchor="middle"))
    b.append("</svg>")
    return "".join(b)


def _funnel(s: dict) -> str:
    stages = s["stages"]
    W, H = 640, 60 + len(stages) * 56 + 20
    mx = stages[0]["value"]
    b = _svg(W, H, "漏斗")
    for i, st in enumerate(stages):
        w = 60 + 460 * (st["value"] / mx) ** 0.45
        x = (640 - w) / 2
        y = 44 + i * 56
        b.append(rc(x, y, w, 38, ACCENT if i == 0 else INK2, rx=1, opacity=".9" if i == 0 else ".85"))
        b.append(t(320, y + 24, f"{st['label']} {st['value']:,.0f}", 8, WHITE, 600, anchor="middle"))
        if i:
            b.append(t(612, y + 4, f"{st['value'] / stages[i-1]['value'] * 100:.0f}%", 7.4, MUTED, anchor="end"))
    b.append("</svg>")
    return "".join(b)


def _treemap(s: dict) -> str:
    items = sorted(s["items"], key=lambda x: -x["value"])
    total = sum(i["value"] for i in items)

    def layout(items, x, y, w, h, out, vert=True):
        if len(items) == 1:
            out.append((items[0], x, y, w, h))
            return
        acc, k = 0.0, 0
        half = sum(i["value"] for i in items) / 2
        while k < len(items) - 1 and acc + items[k]["value"] < half:
            acc += items[k]["value"]
            k += 1
        k = max(1, k)
        first, rest = items[:k], items[k:]
        r = sum(i["value"] for i in first) / sum(i["value"] for i in items)
        if vert:
            layout(first, x, y, w * r, h, out, not vert)
            layout(rest, x + w * r, y, w * (1 - r), h, out, not vert)
        else:
            layout(first, x, y, w, h * r, out, not vert)
            layout(rest, x, y + h * r, w, h * (1 - r), out, not vert)

    out = []
    layout(items, 24, 36, 592, 268, out, True)
    b = _svg(640, 344, "树图")
    for i, (it, x, y, w, h) in enumerate(out):
        b.append(rc(x + 1, y + 1, w - 2, h - 2, TINTS[i % 6], rx=2))
        b.append(t(x + 8, y + 18, it["label"], 8, WHITE, 600))
        b.append(t(x + 8, y + 34, f"{it['value']:.1f}", 8.6, WHITE, 700))
        b.append(t(x + 8, y + 46, f"{it['value'] / total * 100:.0f}%", 7, "#E8E8E8"))
    b.append("</svg>")
    return "".join(b)


RENDERERS = {
    "hbar": _hbar, "dot": _dot, "line": _line, "waterfall": _waterfall,
    "range": _range, "heatmap": _heatmap, "donut": _donut,
    "funnel": _funnel, "treemap": _treemap,
}

try:  # 第二批：slope / dumbbell / small_mult / box / scatter
    from .spec_more import RENDERERS as _MORE
    RENDERERS.update(_MORE)
except Exception:  # pragma: no cover
    pass

try:  # 条形族 + 折线族
    from .spec_families import RENDERERS as _FAM
    RENDERERS.update(_FAM)
except Exception:  # pragma: no cover
    pass

try:  # 点位族 + 构成族
    from .spec_points import RENDERERS as _PTS
    RENDERERS.update(_PTS)
except Exception:  # pragma: no cover
    pass

try:  # 统计族
    from .spec_stats import RENDERERS as _STA
    RENDERERS.update(_STA)
except Exception:  # pragma: no cover
    pass

try:  # 时间族
    from .spec_time import RENDERERS as _TIME
    RENDERERS.update(_TIME)
except Exception:  # pragma: no cover
    pass

try:  # 空间 / 流程 / 派生
    from .spec_space import RENDERERS as _SPC
    RENDERERS.update(_SPC)
except Exception:  # pragma: no cover
    pass

ALIASES = {
    "forecast": "line", "small6": "small_mult", "small_mult6": "small_mult",
    "range_median": "range", "bar_ci": "error_bar", "pct_hbar": "pct_stacked",
    "scatter_band": "scatter", "kpi_spark": "kpi", "gauge_delta": "gauge",
    "waffle_cmp": "waffle", "funnel_cmp": "funnel", "candle_vol": "candle",
    "dual": "dual_panels", "share": "share_bar", "spark": "spark_table",
    "grouped_bar": "grouped", "stacked_bar": "stacked", "candlestick": "candle",
    "kpi_break": "kpi", "ridgeline": "ridge", "streamgraph": "stream",
    "symbol_map": "symbol", "dual_axis": "dual_panels",
}

REQUIRED = {
    "hbar": ("items",), "dot": ("points",), "line": ("points",),
    "waterfall": ("start", "deltas"), "range": ("rows",),
    "heatmap": ("rows", "cols", "matrix"), "donut": ("items",),
    "funnel": ("stages",), "treemap": ("items",),
    "slope": ("series", "stages"), "dumbbell": ("rows",),
    "small_mult": ("panels",), "box": ("groups",), "scatter": ("points",),
    "vbar": ("items",), "lollipop": ("items",), "diverging": ("items",),
    "grouped": ("groups", "series"), "stacked": ("categories", "series"),
    "pct_stacked": ("categories", "series"), "marimekko": ("columns",),
    "bullet": ("rows",), "bridge": ("start", "deltas"),
    "area": ("points",), "stack_area": ("series",), "multi_line": ("series",),
    "step": ("points",), "cumulative": ("points",),
    "area_range": ("low", "high"), "connected": ("points",),
    "strip": ("values",), "beeswarm": ("values",), "violin": ("groups",),
    "ridge": ("groups",), "histogram": ("values",), "hist_multi": ("groups",),
    "box_jitter": ("groups",), "bump": ("stages", "series"),
    "quadrant": ("points",), "parallel": ("axes", "series"),
    "bubble": ("points",), "lollipop_ci": ("rows",),
    "dot_matrix": ("rows", "cols", "matrix"),
    "pie": ("items",), "waffle": ("items",), "rose": ("items",), "sunburst": ("items",),
    "error_bar": ("rows",), "forest": ("rows",), "control": ("values",),
    "gauge": ("value", "target"), "target_band": ("points", "band"),
    "radar": ("axes", "series"), "pareto": ("items",), "kpi": ("items",),
    "spark_table": ("rows",), "dual_panels": ("top", "bottom"), "share_bar": ("items",),
    "gantt": ("tasks",), "timeline": ("milestones",), "cal_heatmap": ("values",),
    "candle": ("ohlc",), "ym_heat": ("rows", "matrix"),
    "choropleth": ("values",), "symbol": ("values",), "geo_flow": ("values",),
    "network": ("nodes", "edges"), "sankey": ("nodes", "links"),
    "index": ("series",), "stream": ("series",),
}


def validate(spec: dict) -> None:
    typ = spec.get("type")
    if typ not in RENDERERS:
        raise KeyError(f"未知图型: {typ}；可用 {len(RENDERERS)} 型")
    missing = [k for k in REQUIRED.get(typ, ()) if k not in spec]
    if missing:
        raise ValueError(f"{typ} 缺少字段: {','.join(missing)}")


def render(spec: dict) -> str:
    if spec.get("type") in ALIASES:
        spec = {**spec, "type": ALIASES[spec["type"]]}
    validate(spec)
    return RENDERERS[spec["type"]](spec)


def kinds() -> list[str]:
    return sorted(RENDERERS)

# -*- coding: utf-8 -*-
"""剩余参数化：空间（choropleth/symbol/geo_flow）、流程（network/sankey）、派生（index/stream）。"""
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


def _geo():
    # 2026-11-23：geo 样例数据改为懒加载——只有真的画空间图才导入，不再拖累 import。
    from .samples_data import geo as geo_mod  # noqa: PLC0415
    return geo_mod.project()


def _key(cents, name):
    for k in cents:
        if k.startswith(name) or name.startswith(k):
            return k
    return None


def _choropleth(s: dict) -> str:
    paths, cents = _geo()
    vals = s["values"]
    mx = max(vals.values()) or 1
    mn = min(vals.values())
    W, H = 640, 380
    b = _svg(W, H, "choropleth")
    for name, d in paths.items():
        city = _key(cents, name)
        v = vals.get(city, mn)
        b.append(f'<path d="{d}" fill="{blend((v - mn) / (mx - mn + 1e-9))}" '
                 f'stroke="{WHITE}" stroke-width="1"/>')
    top = sorted(vals, key=lambda c: -vals[c])[:5]
    for city, (x, y) in cents.items():
        base = _key(cents, city)
        if base not in top:
            continue
        v = vals.get(base, 0)
        b.append(t(x, y + 3, f"{v:g}", 7.2, WHITE, 700, anchor="middle", halo=True))
    b.append("</svg>")
    return "".join(b)


def _symbol(s: dict) -> str:
    paths, cents = _geo()
    vals = s["values"]
    mx = max(vals.values()) or 1
    W, H = 640, 380
    b = _svg(W, H, "符号地图")
    for d in paths.values():
        b.append(f'<path d="{d}" fill="#F3F1EA" stroke="{LINE2}" stroke-width=".6"/>')
    for name, (x, y) in cents.items():
        base = _key(cents, name)
        v = vals.get(base, 0)
        b.append(ci(x, y, 4 + 15 * math.sqrt(v / mx), INK2, WHITE, 1))
    b.append("</svg>")
    return "".join(b)


def _geoflow(s: dict) -> str:
    paths, cents = _geo()
    # 2026-11-23 清理：不再写死默认呼和浩特，取调用方给的 hub，缺省用第一个城市
    hub = _key(cents, s.get("hub") or next(iter(cents), ""))
    hx, hy = cents[hub]
    vals = s["values"]
    mx = max(vals.values()) or 1
    W, H = 640, 380
    b = _svg(W, H, "流向图")
    for d in paths.values():
        b.append(f'<path d="{d}" fill="#F3F1EA" stroke="{LINE2}" stroke-width=".6"/>')
    for name, (x, y) in cents.items():
        if name == hub:
            continue
        base = _key(cents, name)
        w = 1 + 4.5 * math.sqrt(vals.get(base, 0) / mx)
        b.append(f'<line x1="{hx:.1f}" y1="{hy:.1f}" x2="{x:.1f}" y2="{y:.1f}" '
                 f'stroke="{INK2}" stroke-width="{w:.2f}" stroke-opacity=".38"/>')
        b.append(ci(x, y, 3, INK2))
    b.append(ci(hx, hy, 5, ACCENT))
    b.append("</svg>")
    return "".join(b)


def _network(s: dict) -> str:
    nodes, edges = s["nodes"], s["edges"]
    W, H = 640, 340
    cx, cy, r = 310, 170, 104
    pos = {}
    for i, n in enumerate(nodes):
        a = -math.pi / 2 + i * math.tau / len(nodes)
        pos[n] = (cx + r * math.cos(a), cy + r * math.sin(a))
    b = _svg(W, H, "网络")
    for a, bb, w in edges:
        x1, y1 = pos[a]
        x2, y2 = pos[bb]
        b.append(ln(x1, y1, x2, y2, LINE2, 1 + 4 * w))
    for n, (x, y) in pos.items():
        b.append(ci(x, y, 14, INK2, WHITE, 1.5))
        b.append(t(x, y + 26, n, 7, MUTED, anchor="middle"))
    b.append("</svg>")
    return "".join(b)


def _sankey(s: dict) -> str:
    nodes, links = s["nodes"], s["links"]
    W, H = 640, 360
    xs = [70 + i * 120 for i in range(5)]
    cy = 170
    main = s.get("main") or [1] * 5
    mx = main[0] or 1
    b = _svg(W, H, "桑基")
    for i, x in enumerate(xs[:len(main)]):
        h = 14 + 150 * math.sqrt(main[i] / mx)
        b.append(rc(x - 6, cy - h / 2, 12, h, ACCENT if i == 0 else INK2, rx=2))
        b.append(t(x, cy - h / 2 - 8, nodes[i], 7.2, INK2, anchor="middle"))
    for a, bb, v in links:
        if a >= len(xs) or bb >= len(xs):
            continue
        x1, x2 = xs[a] + 6, xs[bb] - 6
        w = 2 + 14 * math.sqrt(v / (links[0][2] or 1))
        b.append(pa(f"M {x1},{cy} C {(x1+x2)/2},{cy} {(x1+x2)/2},{cy} {x2},{cy}",
                    "none", INK2, w, opacity=".30"))
    b.append("</svg>")
    return "".join(b)


def _index(s: dict) -> str:
    series = s["series"]
    W, H = 640, 320
    L, R, T, B = 64, 560, 48, 252
    idx = []
    for se in series:
        base = se["points"][0] or 1
        idx.append([v / base * 100 for v in se["points"]])
    vals = [v for row in idx for v in row]
    Y = sy(min(vals) * .9, max(vals) * 1.05, B, T)
    n = len(idx[0])
    X = sx(0, n - 1, L + 4, R)
    b = _svg(W, H, "指数化")
    b.append(ln(L, Y(100), R, Y(100), LINE2, 1, "3 3"))
    for j, se in enumerate(series):
        color = INK2 if j == 0 else (BLUE if j == 1 else ACCENT)
        b.append(pa("M " + " L ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(idx[j])),
                    "none", color, 1.8))
        b.append(t(R + 6, Y(idx[j][-1]) + 3, f"{se['name']} {idx[j][-1]:.0f}", 7, color))
    b.append("</svg>")
    return "".join(b)


def _stream(s: dict) -> str:
    series, n = s["series"], len(s["series"][0]["points"])
    W, H = 640, 330
    L, R, T, B = 64, 520, 50, 262
    totals = [sum(se["points"][i] for se in series) for i in range(n)]
    mx = max(totals) or 1
    X = sx(0, n - 1, L + 4, R)
    Hh = (B - T) / mx
    lower = [(T + B) / 2] * n
    b = _svg(W, H, "流图")
    for j, se in enumerate(series):
        upper = [lower[i] - se["points"][i] * Hh for i in range(n)]
        d = ("M " + " L ".join(f"{X(i):.1f},{lower[i]:.1f}" for i in range(n)) + " " +
             " ".join(f"L {X(i):.1f},{upper[i]:.1f}" for i in range(n - 1, -1, -1)) + " Z")
        b.append(pa(d, TINTS[j % 6], opacity=".9"))
        b.append(t(R + 8, (upper[-1] + lower[-1]) / 2 + 3, se["name"], 7, MUTED))
        lower = upper
    b.append("</svg>")
    return "".join(b)


RENDERERS = {
    "choropleth": _choropleth, "symbol": _symbol, "geo_flow": _geoflow,
    "network": _network, "sankey": _sankey, "index": _index, "stream": _stream,
}

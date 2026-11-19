# -*- coding: utf-8 -*-
"""core.charts.editorial —— 三张样图的编辑风 SVG。

不是最终全量图表库，是先验证三种最难的情况：
1. 少数据点（2–4 类）——点图，不硬画柱；
2. 成本结构——成本桥，不画普通柱；
3. 地理流向——编号节点 + 流向，不画色块地图。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

INK = "#1E1B18"
SLATE = "#6F685D"
FOG = "#C9C0B2"
PAPER = "#F6F1E7"
ACCENT = "#732F2A"
BLUE = "#1F4E5A"
OCHRE = "#A47B42"


def _esc(s: Any) -> str:
    return ("" if s is None else str(s)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _t(x, y, s, size=12, fill=INK, anchor="start", weight=400, family="sans") -> str:
    fam = "Georgia, 'Noto Serif SC', serif" if family == "serif" else "'Noto Sans SC', 'Microsoft YaHei', sans-serif"
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}" font-family="{fam}">{_esc(s)}</text>')


def _ln(x1, y1, x2, y2, stroke=FOG, w=1, dash=None) -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{w}"{d}/>'


def _rect(x, y, w, h, fill, rx=0, opacity=None) -> str:
    o = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{o}/>'


def _dot(cx, cy, r, fill, stroke=None, sw=2) -> str:
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{s}/>'


def _head(title: str, kicker: str, w=1200) -> List[str]:
    return [
        _rect(0, 0, w, 430, PAPER),
        _t(38, 40, kicker, 10, ACCENT, weight=700),
        _t(38, 82, title, 24, INK, weight=700, family="serif"),
        _ln(38, 104, w - 38, 104, INK, 1.2),
    ]


def dot_change(title: str, kicker: str, items: List[Dict[str, Any]], source: str) -> str:
    """items: label/value/note; value=None 表示无数据。"""
    W, H = 1200, 430
    L, R = 300, 1080
    lo, hi = -0.8, 0.8
    x = lambda v: L + (v - lo) / (hi - lo) * (R - L)
    b = _head(title, kicker, W)
    # grid
    for gv in (-0.8, -0.4, 0, 0.4, 0.8):
        b.append(_ln(x(gv), 150, x(gv), 340, FOG if gv else INK, 1 if gv else 1.4, "3 3" if gv else None))
        b.append(_t(x(gv), 365, "0" if gv == 0 else f"{gv:+.1f}pp", 10, SLATE, "middle"))
    b.append(_t(x(0), 392, "份额同比变化（pp）", 10, SLATE, "middle"))
    rows = [190, 250, 310]
    for i, it in enumerate(items[:3]):
        y = rows[i]
        v = it.get("value")
        col = ACCENT if i == 0 else BLUE if (v is not None and v < 0) else SLATE
        b.append(_t(38, y + 4, it["label"], 15, INK, weight=700, family="serif"))
        b.append(_t(38, y + 24, it.get("note", ""), 10, SLATE))
        if v is None:
            b.append(_dot(x(0), y, 7, PAPER, FOG, 2))
            b.append(_t(x(0) + 14, y + 4, "无同比数据", 11, FOG))
        else:
            b.append(_ln(x(0), y, x(v), y, col, 2))
            b.append(_dot(x(v), y, 6, col))
            b.append(_t(x(v) + (10 if v >= 0 else -10), y + 4, f"{v:+.2f}pp", 13, col,
                        "start" if v >= 0 else "end", 700))
    b.append(_t(38, 415, source, 9, FOG))
    return f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">' + "".join(b) + "</svg>"


def cost_bridge(title: str, kicker: str, items: List[Dict[str, Any]], source: str) -> str:
    """items: label/value, 最后 total。横向成本分项：标签左、数值右、一个高亮。"""
    W, H = 1200, 440
    total = next((i["value"] for i in items if i.get("total")), sum(i["value"] for i in items))
    b = _head(title, kicker, W)
    rows = [i for i in items if not i.get("total")]
    L, R = 250, 1080
    scale = (R - L) / total
    for i, it in enumerate(rows):
        y = 150 + i * 38
        v = it["value"]
        col = ACCENT if it.get("highlight") else (SLATE if i % 2 == 0 else FOG)
        b.append(_t(38, y + 14, it["label"], 11, INK if it.get("highlight") else SLATE,
                    weight=700 if it.get("highlight") else 400))
        b.append(_rect(L, y, max(v * scale, 2), 18, col))
        b.append(_t(L + v * scale + 8, y + 14, f"{v:g}", 11, INK, weight=700))
    b.append(_t(38, 400, f"合计 {total:g} 元 / 500ml；渠道+毛利占 53%，运输只占 5%。", 10, SLATE))
    b.append(_t(38, 425, source, 8, FOG))
    return f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">' + "".join(b) + "</svg>"


def flow_map(title: str, kicker: str, china_path: str, inner_path: str,
             origins: List[Tuple[str, str, float, float]], hub: Tuple[str, float, float],
             cities: List[Tuple[str, float, float]], source: str) -> str:
    """中国底图 + 7 产地 → 呼市 → 包头/赤峰；编号节点，不做色块。"""
    W, H = 1200, 710
    geo = json.loads(open(china_path, encoding="utf-8").read())
    inner = json.loads(open(inner_path, encoding="utf-8").read())
    def polys(f):
        g = f["geometry"]
        return [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    rings = [r for f in geo["features"] for poly in polys(f) for r in poly]
    pts = [p for r in rings for p in r if p[1] >= 17.5]
    lo = min(p[0] for p in pts); hi = max(p[0] for p in pts)
    la = min(p[1] for p in pts); ha = max(p[1] for p in pts)
    sc = min((W - 80) / (hi - lo), 470 / (ha - la))
    ox = (W - (hi - lo) * sc) / 2; oy = 105
    def P(lon, lat):
        return ox + (lon - lo) * sc, oy + (ha - lat) * sc
    b = _head(title, kicker, W)
    for r in rings:
        if min(y for _, y in r) < 17.5:
            continue
        d = "M " + " L ".join(f"{P(x, y)[0]:.1f},{P(x, y)[1]:.1f}" for x, y in r) + " Z"
        b.append(f'<path d="{d}" fill="#F2EDE3" stroke="#D8CEBE" stroke-width=".6"/>')
    for f in inner["features"]:
        for poly in polys(f):
            for r in poly:
                d = "M " + " L ".join(f"{P(x, y)[0]:.1f},{P(x, y)[1]:.1f}" for x, y in r) + " Z"
                b.append(f'<path d="{d}" fill="#E6DAC6" stroke="#B9A88F" stroke-width="1"/>')
    hx, hy = P(hub[1], hub[2])
    for num, name, lon, lat in origins:
        x, y = P(lon, lat)
        b.append(_ln(x, y, hx, hy, SLATE, .7, "2 3"))
        b.append(_dot(x, y, 8, PAPER, SLATE, 1.2))
        b.append(_t(x, y + 3, num, 7, INK, "middle", 700))
    b.append(_dot(hx, hy, 9, ACCENT))
    b.append(_t(hx, hy + 22, hub[0], 11, INK, "middle", 700, "serif"))
    for i, (name, lon, lat) in enumerate(cities):
        x, y = P(lon, lat)
        col = ACCENT if i == 0 else OCHRE
        b.append(_ln(hx, hy, x, y, col, 1.8 if i == 0 else 1.2))
        b.append(_dot(x, y, 5, col))
        if i == 0:
            b.append(_ln(x - 3, y - 3, x - 30, y - 24, FOG, .7))
            b.append(_t(x - 32, y - 26, name, 10, INK, "end", 700))
        else:
            b.append(_ln(x + 3, y - 3, x + 30, y - 24, FOG, .7))
            b.append(_t(x + 32, y - 26, name, 10, INK, weight=700))
    # legend
    for i, (num, name, lon, lat) in enumerate(origins):
        cx = 38 + (i // 4) * 420
        cy = 590 + (i % 4) * 24
        b.append(_t(cx, cy, f"{num}", 8, ACCENT, weight=700))
        b.append(_t(cx + 18, cy, name, 9, SLATE))
    b.append(_t(38, 690, source, 8, FOG))
    return f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">' + "".join(b) + "</svg>"


def flow_nodes(title: str, kicker: str, origins: List[str], hub: str,
               cities: List[str], source: str) -> str:
    W, H = 1200, 540
    b = _head(title, kicker, W)
    ox, hx, cx = 230, 650, 1000
    ys = [160 + i * 40 for i in range(len(origins))]
    hy = 280
    cy = [210, 330]
    for i, (o, y) in enumerate(zip(origins, ys)):
        b.append(_ln(ox, y, hx, hy, FOG, 1.2, "2 2"))
        b.append(_dot(ox, y, 4, SLATE))
        b.append(_t(ox - 10, y + 4, o, 11, SLATE, "end"))
    b.append(_dot(hx, hy, 12, ACCENT))
    b.append(_t(hx, hy + 28, hub, 13, INK, "middle", 700, "serif"))
    for i, (c, y) in enumerate(zip(cities, cy)):
        b.append(_ln(hx, hy, cx, y, ACCENT if i == 0 else SLATE, 2.2 if i == 0 else 1.4))
        b.append(_dot(cx, y, 6, ACCENT if i == 0 else SLATE))
        b.append(_t(cx + 14, y + 4, c, 13, INK, weight=700))
    b.append(_t(38, 450, "产地", 11, SLATE, weight=700))
    b.append(_t(38, 470, "7 个主产区跨 6 省", 10, FOG))
    b.append(_t(hx, 450, "分拨", 11, SLATE, "middle", 700))
    b.append(_t(hx, 470, "呼市 1 个节点", 10, FOG, "middle"))
    b.append(_t(W - 38, 450, "消费", 11, SLATE, "end", 700))
    b.append(_t(W - 38, 470, "包头 / 赤峰", 10, FOG, "end"))
    b.append(_t(38, 520, source, 9, FOG))
    return f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">' + "".join(b) + "</svg>"

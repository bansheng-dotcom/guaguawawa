# -*- coding: utf-8 -*-
"""core.charts.v2.types_b4 —— 地理、关系与层级类（5 型）。

覆盖：choropleth / symbol_map / geo_flow / network / sunburst。

工艺约束（与 types_b1/b2/b3 一致）：
- 六要素：结论式标题、口径副标题、直接标注、参考线、异常归因、来源+图注；
- 地图为离线示意投影（非精确边界），必须在图注中写明；
- 单一强调色 + 灰阶；颜色一律取主题令牌；数据不足返回 None，回退 v1。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from matplotlib.patches import Polygon, Rectangle

from . import base as _base
from .base import canvas, fmt_num, svg_of


# --------------------------------------------------------------------------- #
# 通用小工具
# --------------------------------------------------------------------------- #
def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _short(s: Any, n: int = 12) -> str:
    t = str(s if s is not None else "")
    return t if len(t) <= n else t[: max(n - 1, 1)] + "…"


def _clean(ax, T: Dict[str, Any]) -> None:
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.grid(False)


def _footer(fig, text: str, T: Dict[str, Any],
            color: Optional[str] = None) -> None:
    # 嵌入报告图卡时，底注由卡框统一给
    if _base.EMBED:
        return
    h = fig.get_size_inches()[1] * 100.0
    fig.text(0.5, 15.0 / h, text, ha="center", va="bottom",
             fontsize=8.6, color=color or T["muted"])


def _circle(cx: float, cy: float, r: float, n: int = 48) -> List[Tuple[float, float]]:
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
            for i in range(n)]


def _arc(cx: float, cy: float, r: float, a0: float, a1: float,
         steps: int = 20) -> List[Tuple[float, float]]:
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / steps)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / steps)))
            for i in range(steps + 1)]


# --------------------------------------------------------------------------- #
# viz-39 填色地图（离线省域格网）
# --------------------------------------------------------------------------- #
_PROVINCE_GRID: Dict[str, Tuple[int, int]] = {
    "新疆": (0, 0), "内蒙古": (4, 0), "黑龙江": (7, 0),
    "甘肃": (1, 1), "宁夏": (3, 1), "陕西": (4, 1), "山西": (5, 1), "北京": (6, 1), "吉林": (7, 1),
    "青海": (1, 2), "四川": (2, 2), "重庆": (3, 2), "河南": (4, 2), "山东": (5, 2), "河北": (6, 2), "辽宁": (7, 2),
    "西藏": (0, 3), "云南": (2, 3), "贵州": (3, 3), "湖北": (4, 3), "江苏": (5, 3), "天津": (6, 3), "上海": (7, 3),
    "广西": (3, 4), "湖南": (4, 4), "安徽": (5, 4), "浙江": (6, 4),
    "江西": (4, 5), "福建": (5, 5), "台湾": (6, 5),
    "广东": (4, 6), "香港": (5, 6), "澳门": (6, 6), "海南": (3, 6),
}


def _prov(name: str) -> str:
    t = str(name or "").strip()
    for suf in ("壮族自治区", "回族自治区", "维吾尔自治区", "自治区",
                "特别行政区", "省", "市"):
        if t.endswith(suf) and len(t) > len(suf):
            return t[: -len(suf)]
    return t


def choropleth(chart: Dict[str, Any], theme: str) -> Optional[str]:
    regions: Dict[str, Optional[float]] = {}
    for r in chart.get("regions") or []:
        key = _prov(r.get("name"))
        if not key:
            continue
        regions[key] = _num(r.get("value"))
    matched = {k: v for k, v in regions.items() if k in _PROVINCE_GRID}
    unmatched = [k for k in regions if k not in _PROVINCE_GRID]
    if len(matched) < 3:
        return None
    vals = [v for v in matched.values() if v is not None and v != 0]
    if not vals:
        return None
    vmax = max(vals)
    if vmax <= 0:
        return None

    fig, ax, T = canvas(680, theme, chart.get("title", ""),
                        chart.get("unit_meta", chart.get("unit", "")), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=54, pad_r=54, pad_b=104, pad_t=66)
    _clean(ax, T)
    ax.set_xlim(0, 8)
    ax.set_ylim(-1.55, 7.35)
    gap = 0.075

    for name, (c, r) in _PROVINCE_GRID.items():
        x, y = c, 6 - r
        if name not in matched:
            ax.add_patch(Rectangle((x + gap, y + gap), 1 - 2 * gap, 1 - 2 * gap,
                                   facecolor="none", edgecolor=T["line"],
                                   linestyle=(0, (2, 2)), linewidth=0.6, zorder=2))
            ax.text(x + 0.5, y + 0.5, _short(name, 4), ha="center", va="center",
                    fontsize=7.4, color=T["line_strong"], zorder=3)
            continue
        v = matched[name]
        if v is None:
            ax.add_patch(Rectangle((x + gap, y + gap), 1 - 2 * gap, 1 - 2 * gap,
                                   facecolor=T["surface"], edgecolor=T["line"],
                                   hatch="///", linewidth=0.6, zorder=3))
            ax.text(x + 0.5, y + 0.62, _short(name, 4), ha="center", va="center",
                    fontsize=7.4, color=T["muted"], zorder=4)
            ax.text(x + 0.5, y + 0.34, "缺失", ha="center", va="center",
                    fontsize=6.6, color=T["muted"], zorder=4)
        elif v == 0:
            ax.add_patch(Rectangle((x + gap, y + gap), 1 - 2 * gap, 1 - 2 * gap,
                                   facecolor=T["surface"], edgecolor=T["line_strong"],
                                   linewidth=0.7, zorder=3))
            ax.text(x + 0.5, y + 0.62, _short(name, 4), ha="center", va="center",
                    fontsize=7.4, color=T["ink"], zorder=4)
            ax.text(x + 0.5, y + 0.34, "0", ha="center", va="center",
                    fontsize=6.6, color=T["muted"], zorder=4)
        else:
            t = max(0.0, min(1.0, v / vmax))
            ax.add_patch(Rectangle((x + gap, y + gap), 1 - 2 * gap, 1 - 2 * gap,
                                   facecolor=T["accent"], edgecolor="none",
                                   alpha=0.10 + t * 0.82, zorder=3))
            tc = T["paper"] if t > 0.55 else T["ink"]
            ax.text(x + 0.5, y + 0.62, _short(name, 4), ha="center", va="center",
                    fontsize=7.6, color=tc, fontweight="bold", zorder=4)
            ax.text(x + 0.5, y + 0.34, fmt_num(v), ha="center", va="center",
                    fontsize=6.8, color=tc, zorder=4)

    for k, (alpha, lab) in enumerate(((0.92, f"高 {fmt_num(vmax)}"), (0.52, "中"),
                                      (0.12, "低 >0"))):
        ax.add_patch(Rectangle((k * 1.5, -1.10), 0.28, 0.28, facecolor=T["accent"],
                               edgecolor="none", alpha=alpha, zorder=3))
        ax.text(k * 1.5 + 0.36, -0.96, lab, ha="left", va="center", fontsize=7.6,
                color=T["muted"], zorder=4)
    ax.add_patch(Rectangle((4.6, -1.10), 0.28, 0.28, facecolor=T["surface"],
                           edgecolor=T["line_strong"], linewidth=0.7, zorder=3))
    ax.text(4.96, -0.96, "0", ha="left", va="center", fontsize=7.6, color=T["muted"], zorder=4)
    ax.add_patch(Rectangle((5.5, -1.10), 0.28, 0.28, facecolor=T["surface"],
                           edgecolor=T["line"], hatch="///", linewidth=0.6, zorder=3))
    ax.text(5.86, -0.96, "缺失（≠0）", ha="left", va="center", fontsize=7.6,
            color=T["muted"], zorder=4)

    rate = len(matched) / len(regions) * 100 if regions else 100
    ax.text(0, 7.22, f"匹配率 {rate:.0f}%（{len(matched)}/{len(regions)}）",
            ha="left", va="bottom", fontsize=8.2, color=T["muted"], clip_on=False)
    peak = max((k for k in matched if matched[k] is not None),
               key=lambda k: matched[k] or 0, default=None)
    if peak:
        ax.text(8, 7.22, f"最高：{peak} {fmt_num(matched[peak] or 0)}", ha="right",
                va="bottom", fontsize=8.4, color=T["accent"], clip_on=False)
    if unmatched:
        ax.text(0, -1.38, f"未匹配（无格网坐标）：{'、'.join(unmatched[:12])}",
                ha="left", va="top", fontsize=7.6, color=T["watch"], clip_on=False)
    ax.set_xticks([])
    ax.set_yticks([])
    _footer(fig, "离线示意格网（非精确地理边界）· 等距分级 · 虚线框为未提供数据的地区", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-40 符号地图
# --------------------------------------------------------------------------- #
def symbol_map(chart: Dict[str, Any], theme: str) -> Optional[str]:
    pts: List[Dict[str, Any]] = []
    for p in chart.get("points") or []:
        lon, lat, v = _num(p.get("lon")), _num(p.get("lat")), _num(p.get("value"))
        if None in (lon, lat, v) or v < 0:
            continue
        pts.append({"name": str(p.get("name") or ""), "lon": lon, "lat": lat,
                    "value": v, "accent": bool(p.get("accent"))})
    if len(pts) < 3:
        return None
    lon0, lon1 = min(p["lon"] for p in pts), max(p["lon"] for p in pts)
    lat0, lat1 = min(p["lat"] for p in pts), max(p["lat"] for p in pts)
    mid = math.radians((lat0 + lat1) / 2)
    kx = math.cos(mid) or 1.0
    xr = (lon1 - lon0) * kx
    yr = lat1 - lat0
    if xr < 1e-9 and yr < 1e-9:
        return None
    scale = max(xr, yr, 1e-6)
    xs = [((p["lon"] - lon0) * kx) / scale for p in pts]
    ys = [(p["lat"] - lat0) / scale for p in pts]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    padx = max((xmax - xmin) * 0.10, 0.06)
    pady = max((ymax - ymin) * 0.10, 0.06)
    xlo, xhi = xmin - padx, xmax + padx
    ylo, yhi = ymin - pady, ymax + pady
    vmax = max(p["value"] for p in pts)
    if vmax <= 0:
        return None
    biggest = max(pts, key=lambda p: p["value"])

    fig, ax, T = canvas(460, theme, chart.get("title", ""),
                        chart.get("unit_meta", chart.get("unit", "")), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=56, pad_r=140, pad_b=66, pad_t=60)
    _clean(ax, T)
    ax.set_aspect("equal")
    ax.set_xlim(xlo, xhi)
    ax.set_ylim(ylo, yhi)
    ax.add_patch(Rectangle((xlo + 0.006, ylo + 0.006), (xhi - xlo) - 0.012,
                           (yhi - ylo) - 0.012, facecolor=T["surface"],
                           edgecolor=T["line_strong"], linewidth=0.7, zorder=1))

    # 经纬参考网
    for k in range(5):
        fx = xlo + (xhi - xlo) * k / 4
        fy = ylo + (yhi - ylo) * k / 4
        ax.plot([fx, fx], [ylo, yhi], color=T["line"], linewidth=0.5, zorder=2)
        ax.plot([xlo, xhi], [fy, fy], color=T["line"], linewidth=0.5, zorder=2)
        lon_t = lon0 + (lon1 - lon0) * k / 4
        lat_t = lat0 + (lat1 - lat0) * k / 4
        ax.text(fx, ylo - 0.012, f"{lon_t:.1f}°E", ha="center", va="top", fontsize=6.8,
                color=T["muted"], clip_on=False)
        ax.text(xlo - 0.012, fy, f"{lat_t:.1f}°N", ha="right", va="center", fontsize=6.8,
                color=T["muted"], clip_on=False)

    rmax = min((xhi - xlo), (yhi - ylo)) * 0.16
    for p in sorted(pts, key=lambda q: -q["value"]):
        r = max(math.sqrt(p["value"] / vmax) * rmax, 0.008)
        col = T["accent"] if p["accent"] or p is biggest else T["context"]
        ax.add_patch(Polygon(_circle(xs[pts.index(p)], ys[pts.index(p)], r, 40),
                             closed=True, facecolor=col, edgecolor=T["accent"] if p["accent"] else "none",
                             linewidth=1.0, alpha=0.68 if p["accent"] or p is biggest else 0.38,
                             zorder=4))
        if p["accent"] or p is biggest:
            ax.text(xs[pts.index(p)], ys[pts.index(p)] + r + 0.012,
                    f"{_short(p['name'], 8)} {fmt_num(p['value'])}", ha="center",
                    va="bottom", fontsize=8.0, color=T["ink"], fontweight="bold", zorder=6)

    for k, frac in enumerate((1.0, 0.5, 0.25)):
        r = max(math.sqrt(frac) * rmax, 0.008)
        cx = xhi + (xhi - xlo) * 0.22
        cy = yhi - k * rmax * 1.25 - rmax * 0.9
        ax.add_patch(Polygon(_circle(cx, cy, r, 30), closed=True,
                             facecolor=T["context"], edgecolor=T["line_strong"],
                             linewidth=0.5, alpha=0.22, zorder=3))
        ax.text(cx + rmax * 1.25, cy, fmt_num(vmax * frac), ha="left", va="center",
                fontsize=7.8, color=T["muted"], zorder=4)
    ax.text(xhi + (xhi - xlo) * 0.22, yhi + 0.005, "符号大小\n面积映射", ha="left",
            va="top", fontsize=7.4, color=T["muted"], linespacing=1.5, zorder=4)

    ax.text(0.005, 0.995, f"最大：{_short(biggest['name'], 10)} {fmt_num(biggest['value'])}",
            transform=ax.transAxes, ha="left", va="top", fontsize=8.4,
            color=T["accent"], zorder=6)
    ax.set_xticks([])
    ax.set_yticks([])
    _footer(fig, "等距圆柱近似投影（非精确地图）· 气泡面积∝数值 · 网格为经纬参考线", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-41 地理流向图
# --------------------------------------------------------------------------- #
def geo_flow(chart: Dict[str, Any], theme: str) -> Optional[str]:
    points: Dict[str, Dict[str, Any]] = {}
    for p in chart.get("points") or []:
        pid = str(p.get("id") or "")
        lon, lat = _num(p.get("lon")), _num(p.get("lat"))
        if not pid or lon is None or lat is None:
            continue
        points[pid] = {"name": str(p.get("name") or pid), "lon": lon, "lat": lat}
    flows: List[Dict[str, Any]] = []
    for f in chart.get("flows") or []:
        a, b, v = str(f.get("from")), str(f.get("to")), _num(f.get("value"))
        if a not in points or b not in points or v is None or v <= 0:
            return None
        flows.append({"from": a, "to": b, "value": v})
    if len(points) < 3 or len(flows) < 1:
        return None

    lon0, lon1 = min(p["lon"] for p in points.values()), max(p["lon"] for p in points.values())
    lat0, lat1 = min(p["lat"] for p in points.values()), max(p["lat"] for p in points.values())
    if lon1 - lon0 < 1e-9 and lat1 - lat0 < 1e-9:
        return None
    mid = math.radians((lat0 + lat1) / 2)
    kx = math.cos(mid) or 1.0
    scale = max((lon1 - lon0) * kx, lat1 - lat0, 1e-6)

    def X(lon: float) -> float:
        return ((lon - lon0) * kx) / scale

    def Y(lat: float) -> float:
        return (lat - lat0) / scale

    xs = [X(p["lon"]) for p in points.values()]
    ys = [Y(p["lat"]) for p in points.values()]
    xlo, xhi = min(xs) - 0.08, max(xs) + 0.08
    ylo, yhi = min(ys) - 0.08, max(ys) + 0.08
    vmax = max(f["value"] for f in flows)
    main = max(flows, key=lambda q: (q["value"], q["from"], q["to"]))
    busiest = max(points, key=lambda k: sum(f["value"] for f in flows
                                             if f["from"] == k or f["to"] == k))

    fig, ax, T = canvas(470, theme, chart.get("title", ""),
                        chart.get("unit_meta", chart.get("unit", "")), chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=56, pad_r=80, pad_b=64, pad_t=60)
    _clean(ax, T)
    ax.set_aspect("equal")
    ax.set_xlim(xlo, xhi)
    ax.set_ylim(ylo, yhi)
    ax.add_patch(Rectangle((xlo + 0.004, ylo + 0.004), (xhi - xlo) - 0.008,
                           (yhi - ylo) - 0.008, facecolor=T["surface"],
                           edgecolor=T["line_strong"], linewidth=0.7, zorder=1))
    for k in range(5):
        fx = xlo + (xhi - xlo) * k / 4
        ax.plot([fx, fx], [ylo, yhi], color=T["line"], linewidth=0.5, zorder=2)
    for k in range(4):
        fy = ylo + (yhi - ylo) * k / 3
        ax.plot([xlo, xhi], [fy, fy], color=T["line"], linewidth=0.5, zorder=2)

    for f in flows:
        a, b = points[f["from"]], points[f["to"]]
        x0, y0, x1, y1 = X(a["lon"]), Y(a["lat"]), X(b["lon"]), Y(b["lat"])
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2 - max(abs(x1 - x0), abs(y1 - y0)) * 0.22
        pts = []
        for i in range(25):
            t = i / 24
            u = 1 - t
            pts.append((u * u * x0 + 2 * u * t * mx + t * t * x1,
                        u * u * y0 + 2 * u * t * my + t * t * y1))
        lw = 0.8 + 4.2 * f["value"] / vmax
        is_main = f is main
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=T["accent"],
                linewidth=lw, alpha=0.65 if is_main else 0.28, zorder=4,
                solid_capstyle="round")
        ax.scatter([x1], [y1], s=18 + 26 * f["value"] / vmax, color=T["accent"],
                   alpha=0.85 if is_main else 0.45, edgecolors="none", zorder=5)
        if is_main:
            ax.text(mx, my, f"主通道 {_short(a['name'], 6)}→{_short(b['name'], 6)} "
                            f"{fmt_num(f['value'])}", ha="center", va="bottom",
                    fontsize=8.2, color=T["accent"], fontweight="bold", zorder=7)

    for pid, p in points.items():
        x, y = X(p["lon"]), Y(p["lat"])
        ax.scatter([x], [y], s=30, color=T["ink"], edgecolors=T["paper"],
                   linewidths=1.1, zorder=6)
        ax.text(x, y - 0.030, _short(p["name"], 8), ha="center", va="top",
                fontsize=7.6, color=T["ink"], zorder=6)

    ax.text(0.005, 0.995, f"最繁忙节点：{_short(points[busiest]['name'], 10)}",
            transform=ax.transAxes, ha="left", va="top", fontsize=8.4,
            color=T["accent"], zorder=6)
    ax.set_xticks([])
    ax.set_yticks([])
    _footer(fig, "等距圆柱近似投影 · 线宽∝流量 · 弧线方向由起点指向终点 · 主通道标值", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-42 网络图
# --------------------------------------------------------------------------- #
def network(chart: Dict[str, Any], theme: str) -> Optional[str]:
    nodes: List[Dict[str, Any]] = []
    for n in chart.get("nodes") or []:
        nid = str(n.get("id") or "")
        if not nid:
            continue
        size = _num(n.get("size"))
        nodes.append({"id": nid, "label": str(n.get("label") or nid),
                      "size": size if size and size > 0 else None,
                      "accent": bool(n.get("accent"))})
    ids = {n["id"] for n in nodes}
    edges: List[Dict[str, Any]] = []
    for e in chart.get("edges") or []:
        a, b = str(e.get("a")), str(e.get("b"))
        if a not in ids or b not in ids or a == b:
            return None
        w = _num(e.get("weight"))
        edges.append({"a": a, "b": b, "weight": w if w and w > 0 else 1.0})
    if len(nodes) < 3 or not edges:
        return None

    deg = {n["id"]: 0 for n in nodes}
    for e in edges:
        deg[e["a"]] += 1
        deg[e["b"]] += 1
    sizes = {n["id"]: (n["size"] or deg[n["id"]]) for n in nodes}
    smax = max(sizes.values()) or 1
    wmax = max(e["weight"] for e in edges) or 1
    hub = max(nodes, key=lambda n: sizes[n["id"]])

    fig, ax, T = canvas(480, theme, chart.get("title", ""), "",
                        chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=60, pad_r=60, pad_b=62, pad_t=56)
    _clean(ax, T)
    ax.set_aspect("equal")
    ax.set_xlim(-1.42, 1.42)
    ax.set_ylim(-1.12, 1.12)

    ax.add_patch(Polygon(_circle(0, 0, 0.86, 96), closed=True, fill=False,
                         edgecolor=T["line"], linewidth=0.7, zorder=1))
    n = len(nodes)
    pos: Dict[str, Tuple[float, float]] = {}
    for i, nd in enumerate(nodes):
        a = math.radians(-90 + 360 * i / n)
        pos[nd["id"]] = (0.76 * math.cos(a), 0.76 * math.sin(a))

    for e in edges:
        x0, y0 = pos[e["a"]]
        x1, y1 = pos[e["b"]]
        ax.plot([x0, x1], [y0, y1], color=T["context"],
                linewidth=0.6 + 3.0 * e["weight"] / wmax, alpha=0.30, zorder=2)

    for nd in nodes:
        x, y = pos[nd["id"]]
        r = 0.028 + 0.075 * math.sqrt(sizes[nd["id"]] / smax)
        col = T["accent"] if nd["accent"] or nd is hub else T["context"]
        ax.add_patch(Polygon(_circle(x, y, r, 36), closed=True, facecolor=col,
                             edgecolor=T["paper"], linewidth=1.2,
                             alpha=0.90 if nd["accent"] or nd is hub else 0.62, zorder=4))
        ang = math.atan2(y, x)
        lx, ly = 0.76 + 0.11, 0.0
        lx, ly = 1.00 * math.cos(ang), 1.00 * math.sin(ang)
        ha = "left" if math.cos(ang) > 0.15 else ("right" if math.cos(ang) < -0.15 else "center")
        va = "bottom" if math.sin(ang) > 0.15 else ("top" if math.sin(ang) < -0.15 else "center")
        ax.text(lx, ly, _short(nd["label"], 8), ha=ha, va=va, fontsize=8.0,
                color=T["ink"] if nd["accent"] or nd is hub else T["muted"],
                fontweight="bold" if nd["accent"] or nd is hub else "normal", zorder=6)

    ax.text(0.005, 0.985, f"度数最高：{_short(hub['label'], 10)}（{fmt_num(sizes[hub['id']])} 条）",
            transform=ax.transAxes, ha="left", va="top", fontsize=8.4,
            color=T["accent"], zorder=6)
    ax.text(0.995, 0.02, "● 大小=度数（面积映射）\n— 边宽=联系强度", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=7.6, color=T["muted"], linespacing=1.6, zorder=6)
    ax.set_xticks([])
    ax.set_yticks([])
    _footer(fig, "环形等比布局（无地理含义）· 节点与边各自只表达一个指标 · 无方向箭头", T)
    return svg_of(fig)


# --------------------------------------------------------------------------- #
# viz-38 旭日图
# --------------------------------------------------------------------------- #
def sunburst(chart: Dict[str, Any], theme: str) -> Optional[str]:
    root = chart.get("root") or {}
    children: List[Dict[str, Any]] = []
    for c in root.get("children") or []:
        v = _num(c.get("value"))
        if v is None or v <= 0:
            continue
        kids: List[Dict[str, Any]] = []
        for k in c.get("children") or []:
            kv = _num(k.get("value"))
            if kv is None or kv <= 0:
                continue
            kids.append({"label": str(k.get("label") or ""), "value": kv})
        children.append({"label": str(c.get("label") or ""), "value": v,
                         "children": kids, "accent": bool(c.get("accent"))})
    if len(children) < 2 or len(children) > 8:
        return None
    total = sum(c["value"] for c in children)
    top = max(range(len(children)), key=lambda k: children[k]["value"])

    fig, ax, T = canvas(520, theme, chart.get("title", ""), "",
                        chart.get("source", ""),
                        subtitle=chart.get("subtitle", ""), note=chart.get("note", ""),
                        pad_l=34, pad_r=34, pad_b=76, pad_t=62)
    _clean(ax, T)
    ax.set_aspect("equal")
    ax.set_xlim(-1.22, 1.22)
    ax.set_ylim(-1.14, 1.14)

    r0, r1, r2 = 0.40, 0.70, 0.94
    deferred: List[str] = []
    a0 = 90.0
    for i, c in enumerate(children):
        frac = c["value"] / total
        a1 = a0 - frac * 360.0
        col = T["accent"] if (c["accent"] or i == top) else T["cat"][i % len(T["cat"])]
        pts = _arc(0, 0, r1, a0, a1) + _arc(0, 0, r0, a1, a0)
        ax.add_patch(Polygon(pts, closed=True, facecolor=col, edgecolor=T["paper"],
                             linewidth=1.4, alpha=0.92 if c["accent"] or i == top else 0.62,
                             zorder=3))
        if c["children"]:
            ca0 = a0
            for kid in c["children"]:
                kf = kid["value"] / c["value"]
                ca1 = ca0 - frac * 360.0 * kf
                kpts = _arc(0, 0, r2, ca0, ca1) + _arc(0, 0, r1, ca1, ca0)
                ax.add_patch(Polygon(kpts, closed=True, facecolor=col,
                                     edgecolor=T["paper"], linewidth=0.8,
                                     alpha=0.28, zorder=2))
                ca0 = ca1
        mid = math.radians((a0 + a1) / 2)
        if abs(a1 - a0) >= 14:
            lx, ly = 0.55 * math.cos(mid), 0.55 * math.sin(mid)
            ax.text(lx, ly, f"{_short(c['label'], 7)}\n{fmt_num(c['value'])}"
                            f"（{frac:.0%}）", ha="center", va="center", fontsize=7.6,
                    color=T["paper"] if c["accent"] or i == top else T["ink"],
                    fontweight="bold" if c["accent"] or i == top else "normal",
                    linespacing=1.5, zorder=5)
        else:
            deferred.append(f"{_short(c['label'], 6)} {frac:.0%}")
        a0 = a1

    ax.text(0, 0.08, _short(root.get("label", "合计"), 10), ha="center", va="center",
            fontsize=9.0, color=T["ink"], fontweight="bold", zorder=5)
    ax.text(0, -0.16, fmt_num(total), ha="center", va="center", fontsize=7.6,
            color=T["muted"], zorder=5)

    if deferred:
        ax.text(-1.18, -1.00, f"小扇区外置（<14°）：{'、'.join(deferred)}", ha="left",
                va="center", fontsize=7.4, color=T["muted"], clip_on=False)
    ax.text(0.005, 0.995,
            f"最大类：{_short(children[top]['label'], 8)} 占 "
            f"{children[top]['value'] / total:.1%}",
            transform=ax.transAxes, ha="left", va="top", fontsize=8.4,
            color=T["accent"], zorder=6)
    ax.set_xticks([])
    ax.set_yticks([])
    _footer(fig, "内环=一级，外环=二级（颜色随父级）· 标签水平正对用户 · 小扇区标签外置", T)
    return svg_of(fig)

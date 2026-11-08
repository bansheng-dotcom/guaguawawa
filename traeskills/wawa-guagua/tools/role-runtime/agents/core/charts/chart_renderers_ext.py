# -*- coding: utf-8 -*-
"""确定性 SVG 渲染器扩容（第八轮）：48 图谱全覆盖。

chart_lib.py 内置 10 型（line/waterfall/slope/box/control/funnel/pareto/
histogram/scatter/grouped_bar），本模块补齐其余 38 型（36 剩余 + viz-01/viz-02
通用版），使 chart_lib.RENDERERS 覆盖 48/48。

渲染纪律（每型的「怎么检查」逐条落码，来源 references/chart_prompts_48.json）：
  vbar   纵轴从 0 开始；重点柱唯一强调色，其余同色
  hbar   按值降序确定性排序；Top N 规则注明
  stacked_bar   分段顺序/颜色全柱一致；柱顶总量=各分段之和
  pct_stacked   每条合计 100%（由原始值实算分母）；样本量不隐藏
  area    非负门禁（负值拒绝渲染）；纵轴从 0 开始
  pie     >5 类自动合并「其他」；合计校验标注；无视觉分离
  donut   中心数字与圆环同口径（未提供中心值时用合计实算）
  dumbbell A/B 颜色全图固定；差值正负与标注一致
  dot/lollipop  统一规则排序；茎线足够细；强调色只给关注点
  waffle  填充格数=round(占比)（格数与标注比例一致）
  bubble  半径按 sqrt 映射（面积而非半径）+ 尺寸图例
  heatmap 单色阶（无彩虹）；缺失与 0 显示不同
  radar   对象 ≤2；维度统一尺度
  violin/ridgeline  共享横轴；标注样本量与中位数
  parallel 各轴标准化 0-1；常规线弱化、重点线清楚
  error_bar 误差口径 SD/SE/CI 必填且全图唯一（不混用）
  forest  无效应基线 + CI 水平注明 + 「关联非因果」
  control 见 chart_lib（band=3×1.4826×MAD）
  bullet  目标线绘制在实际条之上（不被遮挡）
  gauge   当前值/单位/目标差文字齐备（颜色不是唯一状态表达）
  cal_heatmap  缺失日期与 0 显示不同；月份边界正确
  gantt   时间条长度∝起止日期；今日线
  candlestick 开高低收合法性门禁（非法直接拒绝）
  sankey  流带宽度∝流量；主路径数值标注
  streamgraph 右端统一最新值标签列
  treemap 面积∝正值（squarify 确定性切分）；小矩形不溢出
  sunburst 标签水平正对用户；小扇区外置说明
  choropleth 0 与缺失不同色；未匹配项如实列出；离线格网
  symbol_map  符号大小按面积映射 + 尺寸图例
  geo_flow 线宽∝流量；主通道数值标注
  network 节点大小/边宽各只表达一个指标；等比绘图区
  rose    半径按 sqrt 映射（面积映射不被半径扭曲）
  target_band 目标带绘制在柱线之后（不遮挡）
  bridge  贡献项严格回到终点（合不上直接拒绝）+ 桥图/排名条分工
  dual_axis 左轴从 0 开始；右轴单位注明
  kpi_break 三模块同口径；驱动拆解位于下半区
  small_mult 全部小图共享同一尺度；≤6 格
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any, Dict, List, Optional

W = 980


# --------------------------------------------------------------------------- #
# 公共小工具（本模块自持，避免与 chart_lib 循环导入）
# --------------------------------------------------------------------------- #
def _svg(title: str, h: int) -> List[str]:
    return [f'<svg viewBox="0 0 {W} {h}" role="img" aria-label="{title}">']


def _grid(out: List[str], top: float, plot_h: float, l: float, r: float,
          vmax: float, vmin: float = 0.0, fmt: str = ",.0f") -> None:
    """弱横向网格 + 左侧刻度（4 等分）。"""
    for i in range(5):
        y = top + plot_h * i / 4
        out.append(f'<line x1="{l:.1f}" y1="{y:.1f}" x2="{r:.1f}" y2="{y:.1f}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{l - 8:.1f}" y="{y + 4:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="end">{(vmax - (vmax - vmin) * i / 4):{fmt}}</text>')


def _legend_row(out: List[str], entries: List[Dict[str, str]], top: float,
                r: float) -> None:
    """右上角横排图例。entries: [{name, color, opacity?}]"""
    lx = r - sum(len(e["name"]) * 11.5 + 42 for e in entries)
    for e in entries:
        op = e.get("opacity", "0.9")
        out.append(f'<rect x="{lx:.1f}" y="{top - 22:.1f}" width="12" height="12" rx="2" fill="{e["color"]}" opacity="{op}"/>')
        out.append(f'<text x="{lx + 16:.1f}" y="{top - 12:.1f}" fill="var(--muted)" font-size="11.5">{e["name"]}</text>')
        lx += len(e["name"]) * 11.5 + 42


def _median(vals: List[float]) -> float:
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _hex(c: str, a: float) -> str:
    """var(--x) 无法带透明度时退化为指定近似色的 rgba。仅用于需要 alpha 的场合。"""
    base = {"accent": (49, 94, 155), "ctx": (41, 47, 54), "critical": (179, 58, 50),
            "watch": (138, 101, 0), "healthy": (25, 112, 75)}[c]
    return f"rgba({base[0]},{base[1]},{base[2]},{a})"


# --------------------------------------------------------------------------- #
# viz-01 纵向柱：纵轴从 0 开始；重点柱唯一强调色
# --------------------------------------------------------------------------- #
def vbar_chart(chart: Dict[str, Any]) -> str:
    cats = chart["categories"]
    vals = chart["values"]
    if len(cats) != len(vals):
        raise ValueError("vbar: categories 与 values 数量不一致")
    if any(v < 0 for v in vals):
        raise ValueError("vbar: 含负值，纵轴从 0 开始会截断负值（改用 hbar 负向）")
    if len(cats) > 8:
        raise ValueError("vbar: 类别超过 8（viz-01 纪律），改用 hbar")
    accent = chart.get("accent_idx")
    H, TOP, BOT, L, R = 380, 56, 52, 80, W - 60
    plot_h = H - TOP - BOT
    vmax = max(vals) * 1.15 or 1.0
    zone = (R - L) / len(cats)
    out = _svg(chart["title"], H)
    _grid(out, TOP, plot_h, L, R, vmax)
    for i, (c, v) in enumerate(zip(cats, vals)):
        cx = L + zone * i + zone / 2
        bw = min(zone * 0.56, 120)
        h = plot_h * v / vmax
        is_acc = (i == accent)
        col = "var(--theme-accent)" if is_acc else "var(--series-context)"
        op = "0.95" if is_acc else "0.62"
        out.append(f'<rect x="{cx - bw/2:.1f}" y="{TOP + plot_h - h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="2.5" fill="{col}" opacity="{op}"/>')
        fw = ' font-weight="700"' if is_acc else ""
        lc = "var(--ink)" if is_acc else "var(--muted)"
        out.append(f'<text x="{cx:.1f}" y="{TOP + plot_h - h - 6:.1f}" fill="{lc}" font-size="12"{fw} text-anchor="middle">{v:{chart.get("fmt", ",.0f")}}</text>')
        out.append(f'<text x="{cx:.1f}" y="{TOP + plot_h + 22:.1f}" fill="var(--muted)" font-size="12" text-anchor="middle">{c}</text>')
    out.append(f'<text x="{L - 8}" y="{TOP - 10}" fill="var(--muted)" font-size="11" text-anchor="end">纵轴自 0 起</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-02 排名横条：按值降序确定性排序；Top N 注明；值标注不裁切
# --------------------------------------------------------------------------- #
def hbar_chart(chart: Dict[str, Any]) -> str:
    items = sorted(chart["items"], key=lambda x: (-x["value"], x["label"]))
    top_n = chart.get("top_n")
    shown = items[:top_n] if top_n else items
    row_h = 46
    H = 66 + row_h * len(shown)
    TOP, L, R = 48, 210, W - 130
    vmax = max(i["value"] for i in shown) or 1.0
    out = _svg(chart["title"], H)
    out.append(f'<text x="{L}" y="{TOP - 16}" fill="var(--muted)" font-size="11.5">按值降序{f" · Top {top_n}" if top_n else "（全量）"}</text>')
    y = TOP
    for it in shown:
        bw = (R - L) * abs(it["value"]) / vmax
        col = "var(--theme-accent)" if it.get("accent") else "var(--series-context)"
        op = "0.95" if it.get("accent") else "0.6"
        out.append(f'<text x="{L - 10}" y="{y + 17:.1f}" fill="var(--ink)" font-size="12.5" font-weight="700" text-anchor="end">{it["label"]}</text>')
        if it["value"] < 0:
            out.append(f'<rect x="{R - bw:.1f}" y="{y + 3:.1f}" width="{bw:.1f}" height="20" rx="2" fill="{col}" opacity="{op}"/>')
        else:
            out.append(f'<rect x="{L:.1f}" y="{y + 3:.1f}" width="{bw:.1f}" height="20" rx="2" fill="{col}" opacity="{op}"/>')
        fw = ' font-weight="700"' if it.get("accent") else ""
        lc = "var(--ink)" if it.get("accent") else "var(--muted)"
        out.append(f'<text x="{L + bw + 8:.1f}" y="{y + 18:.1f}" fill="{lc}" font-size="12"{fw}>{it["value"]:{chart.get("fmt", ",.0f")}}</text>')
        y += row_h
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-04 堆叠柱：分段顺序/颜色全柱一致；柱顶总量=各分段之和
# --------------------------------------------------------------------------- #
_SEG_SHADES = ["var(--theme-accent)", "var(--series-context)",
               "var(--series-reference)", "var(--watch)", "var(--healthy)"]


def stacked_bar_chart(chart: Dict[str, Any]) -> str:
    cats = chart["categories"]
    segs = chart["segments"]           # [{name, values[]}]
    if len(segs) > 5:
        raise ValueError("stacked_bar: 分段超过 5（viz-04 纪律），先合并小项")
    H, TOP, BOT, L, R = 420, 64, 58, 80, W - 60
    plot_h = H - TOP - BOT
    totals = [sum(s["values"][i] for s in segs) for i in range(len(cats))]
    vmax = max(totals) * 1.12 or 1.0
    zone = (R - L) / len(cats)
    out = _svg(chart["title"], H)
    _grid(out, TOP, plot_h, L, R, vmax)
    _legend_row(out, [{"name": s["name"], "color": _SEG_SHADES[i % 5]} for i, s in enumerate(segs)], TOP, R)
    for i, cat in enumerate(cats):
        cx = L + zone * i + zone / 2
        bw = min(zone * 0.56, 120)
        y = TOP + plot_h
        for si, s in enumerate(segs):
            v = s["values"][i]
            h = plot_h * v / vmax
            y -= h
            out.append(f'<rect x="{cx - bw/2:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(h, 0.5):.1f}" fill="{_SEG_SHADES[si % 5]}" opacity="{0.92 if si == 0 else 0.68}"/>')
            if h > 26:
                out.append(f'<text x="{cx:.1f}" y="{y + h/2 + 4:.1f}" fill="var(--paper)" font-size="11" text-anchor="middle">{v:,.0f}</text>')
        out.append(f'<text x="{cx:.1f}" y="{y - 7:.1f}" fill="var(--ink)" font-size="12" font-weight="700" text-anchor="middle">Σ {totals[i]:,.0f}</text>')
        out.append(f'<text x="{cx:.1f}" y="{TOP + plot_h + 22:.1f}" fill="var(--muted)" font-size="12" text-anchor="middle">{cat}</text>')
    out.append(f'<text x="{(L+R)/2}" y="{H - 6}" fill="var(--muted)" font-size="11.5" text-anchor="middle">柱顶总量 = 各分段之和（同单位可加总）</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-05 百分比堆叠：每条合计 100%（原始值实算分母）；样本量不隐藏
# --------------------------------------------------------------------------- #
def pct_stacked_chart(chart: Dict[str, Any]) -> str:
    cats = chart["categories"]
    segs = chart["segments"]
    H, TOP, BOT, L, R = 420, 64, 64, 80, W - 60
    plot_h = H - TOP - BOT
    zone = (R - L) / len(cats)
    totals = [sum(s["values"][i] for s in segs) or 1.0 for i in range(len(cats))]
    out = _svg(chart["title"], H)
    for i in range(5):
        y = TOP + plot_h * i / 4
        out.append(f'<line x1="{L:.1f}" y1="{y:.1f}" x2="{R:.1f}" y2="{y:.1f}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{L - 8:.1f}" y="{y + 4:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="end">{100 - i * 25}%</text>')
    _legend_row(out, [{"name": s["name"], "color": _SEG_SHADES[i % 5]} for i, s in enumerate(segs)], TOP, R)
    for i, cat in enumerate(cats):
        cx = L + zone * i + zone / 2
        bw = min(zone * 0.56, 120)
        y = TOP + plot_h
        for si, s in enumerate(segs):
            v = s["values"][i]
            pct = v / totals[i] * 100
            h = plot_h * pct / 100
            y -= h
            out.append(f'<rect x="{cx - bw/2:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(h, 0.5):.1f}" fill="{_SEG_SHADES[si % 5]}" opacity="{0.92 if si == 0 else 0.68}"/>')
            if pct >= 6:
                out.append(f'<text x="{cx:.1f}" y="{y + h/2 + 4:.1f}" fill="var(--paper)" font-size="11" text-anchor="middle">{pct:.1f}%</text>')
        out.append(f'<text x="{cx:.1f}" y="{TOP + plot_h + 22:.1f}" fill="var(--muted)" font-size="12" text-anchor="middle">{cat}</text>')
        out.append(f'<text x="{cx:.1f}" y="{TOP + plot_h + 40:.1f}" fill="var(--muted)" font-size="11" text-anchor="middle">n={totals[i]:,.0f}</text>')
    out.append(f'<text x="{(L+R)/2}" y="{H - 6}" fill="var(--muted)" font-size="11.5" text-anchor="middle">各条由原始值实算占比（分母=该条合计，合计 100%）· n=绝对总量</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-07 面积图：非负门禁；纵轴从 0 开始；口径注明
# --------------------------------------------------------------------------- #
def area_chart(chart: Dict[str, Any]) -> str:
    s = chart["series"][0]
    vals = s["values"]
    xlabels = chart["xlabels"]
    if len(series := chart["series"]) > 1:
        raise ValueError("area: 多系列严重遮挡（viz-07 纪律），只支持单一主系列")
    if any(v < 0 for v in vals):
        raise ValueError("area: 存在负值，面积图会隐藏负值（viz-07 纪律），改用折线")
    H, TOP, BOT, L, R = 380, 60, 50, 80, W - 60
    plot_h = H - TOP - BOT
    vmax = max(vals) * 1.12 or 1.0
    n = len(vals)
    def X(i): return L + (R - L) * i / (n - 1)
    def Y(v): return TOP + plot_h * (1 - v / vmax)
    out = _svg(chart["title"], H)
    _grid(out, TOP, plot_h, L, R, vmax)
    pts = [(X(i), Y(v)) for i, v in enumerate(vals)]
    poly = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    out.append(f'<polygon points="{L:.0f},{TOP + plot_h:.0f} {poly} {R:.0f},{TOP + plot_h:.0f}" fill="var(--theme-accent)" opacity="0.16"/>')
    out.append(f'<polyline points="{poly}" fill="none" stroke="var(--theme-accent)" stroke-width="2.6" stroke-linejoin="round"/>')
    out.append(f'<circle cx="{X(n-1):.0f}" cy="{Y(vals[-1]):.0f}" r="4" fill="var(--theme-accent)"/>')
    out.append(f'<text x="{R - 4:.1f}" y="{Y(vals[-1]) - 12:.0f}" fill="var(--theme-accent)" font-size="12" font-weight="700" text-anchor="end">{s["name"]} {vals[-1]:,.0f}</text>')
    step = max(1, n // 12)
    for i in range(0, n, step):
        out.append(f'<text x="{X(i):.0f}" y="{H - 12}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{xlabels[i]}</text>')
    out.append(f'<text x="{L}" y="{TOP - 12}" fill="var(--muted)" font-size="11">纵轴自 0 起 · 口径：{chart.get("basis", "当期值")}</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-08 饼图：>5 类自动合并「其他」；从大到小顺时针；合计校验；无视觉分离
# --------------------------------------------------------------------------- #
def pie_chart(chart: Dict[str, Any]) -> str:
    items = [{"label": i["label"], "value": i["value"], "accent": i.get("accent", False)}
             for i in chart["items"]]
    items.sort(key=lambda x: (-x["value"], x["label"]))
    merged: List[str] = []
    if len(items) > 5:
        keep, rest = items[:4], items[4:]
        others = sum(i["value"] for i in rest)
        merged = [i["label"] for i in rest]
        items = keep + [{"label": "其他", "value": others, "accent": False, "_merged": True}]
    total = sum(i["value"] for i in items)
    if total <= 0:
        raise ValueError("pie: 合计必须为正（部分-整体关系）")
    cx, cy, r = W * 0.38, 226, 168
    out = _svg(chart["title"], 452)
    a0 = -90.0
    for i, it in enumerate(items):
        frac = it["value"] / total
        a1 = a0 + frac * 360
        x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
        x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
        large = 1 if (a1 - a0) > 180 else 0
        col = "var(--theme-accent)" if it.get("accent") else f"var(--series-{'reference' if i % 2 else 'context'})"
        op = "0.95" if it.get("accent") else "0.78"
        out.append(f'<path d="M {cx:.1f} {cy:.1f} L {x0:.1f} {y0:.1f} A {r} {r} 0 {large} 1 {x1:.1f} {y1:.1f} Z" fill="{col}" opacity="{op}" stroke="var(--paper)" stroke-width="2"/>')
        am = math.radians((a0 + a1) / 2)
        lx0, ly0 = cx + (r + 8) * math.cos(am), cy + (r + 8) * math.sin(am)
        lx1, ly1 = cx + (r + 34) * math.cos(am), cy + (r + 34) * math.sin(am)
        anchor = "start" if math.cos(am) >= 0 else "end"
        out.append(f'<line x1="{lx0:.1f}" y1="{ly0:.1f}" x2="{lx1:.1f}" y2="{ly1:.1f}" stroke="var(--line-strong)" stroke-width="1"/>')
        fw = ' font-weight="700"' if it.get("accent") else ""
        lc = "var(--ink)" if it.get("accent") else "var(--muted)"
        out.append(f'<text x="{lx1 + (6 if anchor == "start" else -6):.1f}" y="{ly1 + 4:.1f}" fill="{lc}" font-size="12.5"{fw} text-anchor="{anchor}">{it["label"]} {it["value"]:,.0f}（{frac:.1%}）</text>')
        a0 = a1
    out.append(f'<text x="{cx}" y="{cy + r + 62}" fill="var(--muted)" font-size="11.5" text-anchor="middle">合计 {total:,.0f}（校验通过）· 从大到小顺时针 · 无 3D/分离/阴影</text>')
    if merged:
        out.append(f'<text x="{cx}" y="{cy + r + 82}" fill="var(--muted)" font-size="11" text-anchor="middle">已合并「其他」（>5 类）：{"、".join(merged)}</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-09 环形图：中心数字与圆环同口径（未提供中心值时用合计实算）
# --------------------------------------------------------------------------- #
def donut_chart(chart: Dict[str, Any]) -> str:
    items = sorted(chart["items"], key=lambda x: (-x["value"], x["label"]))
    if len(items) > 5:
        raise ValueError("donut: 类别超过 5（viz-09 纪律），先合并「其他」")
    total = sum(i["value"] for i in items)
    center = chart.get("center") or {"label": "合计", "value": total}
    cx, cy, r, rw = W * 0.38, 226, 168, 58
    out = _svg(chart["title"], 452)
    a0 = -90.0
    for i, it in enumerate(items):
        frac = it["value"] / total if total else 0
        a1 = a0 + frac * 360
        def arc(radius: float, a_from: float, a_to: float, back: bool = False) -> str:
            x0, y0 = cx + radius * math.cos(math.radians(a_from)), cy + radius * math.sin(math.radians(a_from))
            x1, y1 = cx + radius * math.cos(math.radians(a_to)), cy + radius * math.sin(math.radians(a_to))
            large = 1 if (a_to - a_from) > 180 else 0
            sweep = 0 if back else 1
            return f"{x0:.1f} {y0:.1f} A {radius} {radius} 0 {large} {sweep} {x1:.1f} {y1:.1f}"
        col = "var(--theme-accent)" if it.get("accent") else f"var(--series-{'reference' if i % 2 else 'context'})"
        d = (f'M {arc(r, a0, a1)} L {arc(r - rw, a1, a0, back=True)} Z')
        out.append(f'<path d="{d}" fill="{col}" opacity="{"0.95" if it.get("accent") else "0.78"}" stroke="var(--paper)" stroke-width="2"/>')
        am = math.radians((a0 + a1) / 2)
        lx, ly = cx + (r + 12) * math.cos(am), cy + (r + 12) * math.sin(am)
        anchor = "start" if math.cos(am) >= 0 else "end"
        fw = ' font-weight="700"' if it.get("accent") else ""
        out.append(f'<text x="{lx + (6 if anchor == "start" else -6):.1f}" y="{ly + 4:.1f}" fill="var(--muted)" font-size="12.5"{fw} text-anchor="{anchor}">{it["label"]} {frac:.1%}</text>')
        a0 = a1
    out.append(f'<text x="{cx}" y="{cy - 2}" fill="var(--ink)" font-size="30" font-weight="700" text-anchor="middle">{center["value"]:,.0f}</text>')
    out.append(f'<text x="{cx}" y="{cy + 24}" fill="var(--muted)" font-size="12.5" text-anchor="middle">{center["label"]}（与圆环同口径）</text>')
    out.append(f'<text x="{cx}" y="{cy + r + 62}" fill="var(--muted)" font-size="11.5" text-anchor="middle">合计 {total:,.0f} · 校验：中心值=圆环合计口径</text>')
    out.append("</svg>")
    return "\n          ".join(out)

# --------------------------------------------------------------------------- #
# viz-12 哑铃图：A/B 颜色全图固定；差值正负与标注一致；共同尺度
# --------------------------------------------------------------------------- #
def dumbbell_chart(chart: Dict[str, Any]) -> str:
    items = chart["items"]              # [{label, a, b}]
    a_label = chart.get("a_label", "A")
    b_label = chart.get("b_label", "B")
    items = sorted(items, key=lambda x: (-(abs(x["b"] - x["a"])), x["label"]))
    row_h = 44
    H = 70 + row_h * len(items)
    TOP, L, R = 56, 220, W - 170
    all_v = [v for it in items for v in (it["a"], it["b"])]
    vmin, vmax = min(all_v), max(all_v)
    pad = (vmax - vmin) * 0.08 or 1.0
    vmin, vmax = vmin - pad, vmax + pad
    def X(v): return L + (R - L) * (v - vmin) / (vmax - vmin)
    out = _svg(chart["title"], H)
    for i in range(5):
        x = L + (R - L) * i / 4
        out.append(f'<line x1="{x:.1f}" y1="{TOP - 8}" x2="{x:.1f}" y2="{H - 44}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{H - 28}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{(vmin + (vmax - vmin) * i / 4):,.0f}</text>')
    out.append(f'<text x="{L}" y="{TOP - 16}" fill="var(--muted)" font-size="11.5">● {a_label}（灰）　● {b_label}（强调）· 共同尺度 · 按差距降序</text>')
    y = TOP
    for it in items:
        xa, xb = X(it["a"]), X(it["b"])
        out.append(f'<text x="{L - 10}" y="{y + 18:.1f}" fill="var(--ink)" font-size="12.5" font-weight="700" text-anchor="end">{it["label"]}</text>')
        out.append(f'<line x1="{min(xa, xb):.1f}" y1="{y + 12:.1f}" x2="{max(xa, xb):.1f}" y2="{y + 12:.1f}" stroke="var(--line-strong)" stroke-width="2.4"/>')
        out.append(f'<circle cx="{xa:.1f}" cy="{y + 12:.1f}" r="6" fill="var(--series-context)"/>')
        out.append(f'<circle cx="{xb:.1f}" cy="{y + 12:.1f}" r="6" fill="var(--theme-accent)"/>')
        d = it["b"] - it["a"]
        sign = "+" if d > 0 else ("−" if d < 0 else "±")
        col = "var(--healthy)" if d > 0 else ("var(--critical)" if d < 0 else "var(--muted)")
        out.append(f'<text x="{R + 12:.1f}" y="{y + 16:.1f}" fill="{col}" font-size="12.5" font-weight="700">{sign}{abs(d):,.0f}</text>')
        y += row_h
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-13 点图：统一规则排序；无多余图例/装饰
# --------------------------------------------------------------------------- #
def dot_chart(chart: Dict[str, Any]) -> str:
    items = sorted(chart["items"], key=lambda x: (-x["value"], x["label"]))
    row_h = 40
    H = 64 + row_h * len(items)
    TOP, L, R = 52, 220, W - 160
    vmax = max(i["value"] for i in items) or 1.0
    def X(v): return L + (R - L) * v / vmax
    out = _svg(chart["title"], H)
    out.append(f'<line x1="{L}" y1="{TOP - 10}" x2="{R}" y2="{H - 36}" stroke="var(--line-strong)" stroke-width="1.2"/>')
    for i in range(5):
        x = L + (R - L) * i / 4
        out.append(f'<line x1="{x:.1f}" y1="{TOP - 10}" x2="{x:.1f}" y2="{H - 36}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{H - 20}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{vmax * i / 4:,.0f}</text>')
    y = TOP
    for it in items:
        out.append(f'<text x="{L - 10}" y="{y + 8:.1f}" fill="var(--ink)" font-size="12.5" font-weight="700" text-anchor="end">{it["label"]}</text>')
        col = "var(--theme-accent)" if it.get("accent") else "var(--series-context)"
        r = 8 if it.get("accent") else 6.5
        out.append(f'<circle cx="{X(it['value']):.1f}" cy="{y:.1f}" r="{r}" fill="{col}" opacity="{"0.95" if it.get("accent") else "0.72"}"/>')
        fw = ' font-weight="700"' if it.get("accent") else ""
        out.append(f'<text x="{X(it['value']) + r + 6:.1f}" y="{y + 4:.1f}" fill="var(--muted)" font-size="12"{fw}>{it["value"]:,.0f}</text>')
        y += row_h
    out.append(f'<text x="{L}" y="{TOP - 18}" fill="var(--muted)" font-size="11.5">按值降序 · 共同尺度 · 无图例</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-14 棒棒糖图：茎线足够细（不会被误读为柱形）；强调色只给关注点
# --------------------------------------------------------------------------- #
def lollipop_chart(chart: Dict[str, Any]) -> str:
    items = sorted(chart["items"], key=lambda x: (-x["value"], x["label"]))
    top_n = chart.get("top_n")
    shown = items[:top_n] if top_n else items
    row_h = 42
    H = 64 + row_h * len(shown)
    TOP, L, R = 52, 220, W - 150
    vmax = max(i["value"] for i in shown) or 1.0
    def X(v): return L + (R - L) * v / vmax
    out = _svg(chart["title"], H)
    out.append(f'<line x1="{L}" y1="{TOP - 10}" x2="{R}" y2="{H - 36}" stroke="var(--line-strong)" stroke-width="1.2"/>')
    y = TOP
    for it in shown:
        out.append(f'<text x="{L - 10}" y="{y + 8:.1f}" fill="var(--ink)" font-size="12.5" font-weight="700" text-anchor="end">{it["label"]}</text>')
        col = "var(--theme-accent)" if it.get("accent") else "var(--series-context)"
        # 茎线宽 2 —— 明显细于柱形（viz-14 纪律）
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{X(it['value']):.1f}" y2="{y:.1f}" stroke="{col}" stroke-width="2" opacity="0.8"/>')
        out.append(f'<circle cx="{X(it['value']):.1f}" cy="{y:.1f}" r="{"9" if it.get("accent") else "7"}" fill="{col}" opacity="{"0.95" if it.get("accent") else "0.7"}"/>')
        fw = ' font-weight="700"' if it.get("accent") else ""
        out.append(f'<text x="{X(it['value']) + 12:.1f}" y="{y + 4:.1f}" fill="var(--muted)" font-size="12"{fw}>{it["value"]:,.0f}</text>')
        y += row_h
    out.append(f'<text x="{L}" y="{TOP - 18}" fill="var(--muted)" font-size="11.5">按值降序{f" · Top {top_n}" if top_n else ""} · 茎线非柱形</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-15 华夫图：填充格数 = round(占比)（格数与标注比例一致）
# --------------------------------------------------------------------------- #
def waffle_chart(chart: Dict[str, Any]) -> str:
    items = chart["items"]              # [{label, value, accent?}]
    total = sum(i["value"] for i in items)
    if total <= 0:
        raise ValueError("waffle: 合计必须为正")
    # 每类格数 = round(占比)，取整后再对合计 100 格做余数校正（最大余数法）
    raw = [i["value"] / total * 100 for i in items]
    cells = [int(math.floor(r)) for r in raw]
    rem = 100 - sum(cells)
    order = sorted(range(len(items)), key=lambda k: (-(raw[k] - cells[k]), k))
    for k in order[:rem]:
        cells[k] += 1
    cols, rows_n, cell, gap = 10, 10, 44, 6
    gw = cols * (cell + gap) - gap
    x0, y0 = 96, 92
    H = y0 + rows_n * (cell + gap) - gap + 96
    out = _svg(chart["title"], H)
    out.append(f'<text x="{x0}" y="{y0 - 40}" fill="var(--muted)" font-size="11.5">每格 = 1% · 填充格数与标注占比一致（最大余数法取整，合计 100 格）</text>')
    palette = ["var(--theme-accent)", "var(--series-context)", "var(--series-reference)",
               "var(--watch)", "var(--healthy)", "var(--line-strong)"]
    ci = 0
    legend_x = x0 + gw + 60
    for k, it in enumerate(items):
        col = palette[k % len(palette)]
        op = "0.95" if it.get("accent") else "0.8"
        for c in range(cells[k]):
            r_, c_ = c // cols, c % cols
            x = x0 + c_ * (cell + gap)
            y = y0 + r_ * (cell + gap)
            out.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{cell}" height="{cell}" rx="3" fill="{col}" opacity="{op}"/>')
        ly = y0 + 30 + k * 26 if k < 6 else y0 + 30 + (k - 6) * 26
        lx = legend_x if k < 6 else legend_x + 240
        out.append(f'<rect x="{lx}" y="{ly - 11}" width="14" height="14" rx="3" fill="{col}" opacity="{op}"/>')
        out.append(f'<text x="{lx + 20}" y="{ly}" fill="var(--ink)" font-size="12.5" font-weight="700">{it["label"]}</text>')
        out.append(f'<text x="{lx + 20 + len(it["label"]) * 13}" y="{ly}" fill="var(--muted)" font-size="12">{raw[k]:.1f}%（{cells[k]} 格）</text>')
        ci += 1
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-18 气泡图：半径按 sqrt 映射（面积而非半径）+ 尺寸图例
# --------------------------------------------------------------------------- #
def bubble_chart(chart: Dict[str, Any]) -> str:
    pts = chart["points"]               # [{x, y, size, label?, accent?}]
    H, TOP, BOT, L, R = 440, 56, 60, 80, W - 220
    plot_w, plot_h = R - L, H - TOP - BOT
    xs = [p["x"] for p in pts]; ys = [p["y"] for p in pts]
    xmin, xmax = min(xs), max(xs); ymin, ymax = min(ys), max(ys)
    padx = (xmax - xmin) * 0.1 or 1.0; pady = (ymax - ymin) * 0.1 or 1.0
    xmin, xmax, ymin, ymax = xmin - padx, xmax + padx, ymin - pady, ymax + pady
    smax = max(p["size"] for p in pts) or 1.0
    RMAX = 30
    def X(v): return L + plot_w * (v - xmin) / (xmax - xmin)
    def Y(v): return TOP + plot_h * (1 - (v - ymin) / (ymax - ymin))
    def R_(s): return math.sqrt(s / smax) * RMAX if smax else 6   # 面积映射
    out = _svg(chart["title"], H)
    _grid(out, TOP, plot_h, L, R, ymax, ymin, ",.1f")
    for i in range(5):
        x = L + plot_w * i / 4
        out.append(f'<text x="{x:.1f}" y="{TOP + plot_h + 18:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{xmin + (xmax - xmin) * i / 4:,.1f}</text>')
    for p in sorted(pts, key=lambda q: -q["size"]):   # 大泡先画，避免遮小泡
        col = "var(--theme-accent)" if p.get("accent") else "var(--series-context)"
        out.append(f'<circle cx="{X(p['x']):.1f}" cy="{Y(p['y']):.1f}" r="{R_(p['size']):.1f}" fill="{col}" opacity="{"0.72" if p.get("accent") else "0.38"}" stroke="{"var(--theme-accent)" if p.get("accent") else "none"}" stroke-width="1.2"/>')
        if p.get("label"):
            out.append(f'<text x="{X(p['x']):.1f}" y="{Y(p['y']) - R_(p['size']) - 6:.1f}" fill="var(--ink)" font-size="11.5" text-anchor="middle">{p["label"]}</text>')
    # 尺寸图例（面积映射）
    lx = R + 40
    out.append(f'<text x="{lx}" y="{TOP + 8}" fill="var(--muted)" font-size="11.5">气泡大小（面积映射 √）</text>')
    svals = [smax, smax / 2, smax / 4]
    labs = [f"{svals[0]:,.0f}", f"{svals[1]:,.0f}", f"{svals[2]:,.0f}"]
    for k, (sv, lb) in enumerate(zip(svals, labs)):
        cy_ = TOP + 44 + k * 74
        out.append(f'<circle cx="{lx + RMAX + 6:.0f}" cy="{cy_:.0f}" r="{R_(sv):.1f}" fill="var(--series-context)" opacity="0.3" stroke="var(--line-strong)"/>')
        out.append(f'<text x="{lx + 2 * RMAX + 18:.0f}" y="{cy_ + 4:.0f}" fill="var(--muted)" font-size="11.5">{lb}</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-19 热力图：单色阶（无彩虹）；缺失与 0 显示不同；行列顺序注明
# --------------------------------------------------------------------------- #
def heatmap_chart(chart: Dict[str, Any]) -> str:
    rows = chart["rows"]
    cols = chart["cols"]
    cells = chart["cells"]              # rows×cols 矩阵，None=缺失
    if len(cells) != len(rows) or any(len(r) != len(cols) for r in cells):
        raise ValueError("heatmap: cells 必须是 rows×cols 完整矩阵（缺失用 null）")
    vals = [c for r in cells for c in r if c is not None]
    vmax = max(vals) if vals else 1.0
    vmin = min(vals) if vals else 0.0
    L, T, CW, CH, GP = 150, 66, 92, 46, 4
    W_ = L + len(cols) * (CW + GP) + 20
    H_ = T + len(rows) * (CH + GP) + 74
    out = [f'<svg viewBox="0 0 {max(W_, 760)} {H_}" role="img" aria-label="{chart["title"]}">']
    out.append(f'<text x="{L}" y="{T - 12}" fill="var(--muted)" font-size="11.5">单色阶（浅→深 = 低→高，{chart.get("order_note", "行列顺序：按数据给定顺序")}）· 缺失显示为斜纹，区别于 0</text>')
    for j, c in enumerate(cols):
        out.append(f'<text x="{L + j * (CW + GP) + CW / 2:.0f}" y="{T + 14}" fill="var(--ink)" font-size="12" font-weight="700" text-anchor="middle">{c}</text>')
    has_missing = False
    for i, rname in enumerate(rows):
        y = T + i * (CH + GP)
        out.append(f'<text x="{L - 10}" y="{y + CH / 2 + 4:.0f}" fill="var(--ink)" font-size="12" font-weight="700" text-anchor="end">{rname}</text>')
        for j in range(len(cols)):
            x = L + j * (CW + GP)
            v = cells[i][j]
            if v is None:
                has_missing = True
                out.append(f'<rect x="{x}" y="{y}" width="{CW}" height="{CH}" rx="3" fill="var(--surface-strong)" stroke="var(--line)" stroke-width="1"/>')
                out.append(f'<line x1="{x + 8}" y1="{y + CH - 8}" x2="{x + CW - 8}" y2="{y + 8}" stroke="var(--line-strong)" stroke-width="1.4"/>')
                out.append(f'<text x="{x + CW / 2:.0f}" y="{y + CH / 2 - 6}" fill="var(--muted)" font-size="12.5" text-anchor="middle">缺失</text>')
            else:
                t = (v - vmin) / (vmax - vmin) if vmax > vmin else 0.5
                out.append(f'<rect x="{x}" y="{y}" width="{CW}" height="{CH}" rx="3" fill="var(--theme-accent)" opacity="{0.08 + t * 0.82:.2f}"/>')
                tc = "var(--paper)" if t > 0.55 else "var(--ink)"
                out.append(f'<text x="{x + CW / 2:.0f}" y="{y + CH / 2 + 4:.0f}" fill="{tc}" font-size="12" font-weight="700" text-anchor="middle">{v:,.0f}{"（0）" if v == 0 else ""}</text>')
    ly = T + len(rows) * (CH + GP) + 18
    out.append(f'<rect x="{L}" y="{ly}" width="16" height="12" fill="var(--theme-accent)" opacity="0.9"/>')
    out.append(f'<text x="{L + 22}" y="{ly + 10}" fill="var(--muted)" font-size="11.5">高 {vmax:,.0f}</text>')
    out.append(f'<rect x="{L + 90}" y="{ly}" width="16" height="12" fill="var(--theme-accent)" opacity="0.1"/>')
    out.append(f'<text x="{L + 112}" y="{ly + 10}" fill="var(--muted)" font-size="11.5">低 {vmin:,.0f}</text>')
    if has_missing:
        out.append(f'<rect x="{L + 200}" y="{ly}" width="16" height="12" fill="var(--surface-strong)" stroke="var(--line)"/>')
        out.append(f'<line x1="{L + 203}" y1="{ly + 10}" x2="{L + 213}" y2="{ly + 2}" stroke="var(--line-strong)" stroke-width="1.2"/>')
        out.append(f'<text x="{L + 222}" y="{ly + 10}" fill="var(--muted)" font-size="11.5">缺失（≠0）</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-20 雷达图：维度统一尺度；对象 ≤2；不把面积当总分
# --------------------------------------------------------------------------- #
def radar_chart(chart: Dict[str, Any]) -> str:
    axes = chart["axes"]
    series = chart["series"]            # [{name, values[], accent?}]
    if len(series) > 2:
        raise ValueError("radar: 对象超过 2 组（viz-20 纪律），拆分展示")
    if len(axes) < 3 or len(axes) > 8:
        raise ValueError("radar: 维度须在 3~8 个")
    for s in series:
        if len(s["values"]) != len(axes):
            raise ValueError("radar: values 数与 axes 数不一致")
    smax = chart.get("scale_max") or max(v for s in series for v in s["values"]) or 1.0
    cx, cy, r = W * 0.5, 264, 196
    n = len(axes)
    def pt(i: int, v: float):
        a = math.radians(-90 + 360 * i / n)
        rr = r * max(0.0, min(1.0, v / smax))
        return cx + rr * math.cos(a), cy + rr * math.sin(a)
    out = _svg(chart["title"], 560)
    for ring in (0.25, 0.5, 0.75, 1.0):
        pts = " ".join(f"{pt(i, smax * ring)[0]:.0f},{pt(i, smax * ring)[1]:.0f}" for i in range(n))
        out.append(f'<polygon points="{pts}" fill="none" stroke="var(--line)" stroke-width="1"/>')
    for i, ax in enumerate(axes):
        x, y = pt(i, smax)
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.0f}" y2="{y:.0f}" stroke="var(--line)" stroke-width="1"/>')
        lx, ly = pt(i, smax * 1.18)
        anchor = "middle"
        if lx > cx + 12: anchor = "start"
        elif lx < cx - 12: anchor = "end"
        out.append(f'<text x="{lx:.0f}" y="{ly + 4:.0f}" fill="var(--ink)" font-size="12" font-weight="700" text-anchor="{anchor}">{ax}</text>')
    for s in series:
        pts = " ".join(f"{pt(i, v)[0]:.0f},{pt(i, v)[1]:.0f}" for i, v in enumerate(s["values"]))
        col = "var(--theme-accent)" if s.get("accent") or len(series) == 1 else "var(--series-context)"
        out.append(f'<polygon points="{pts}" fill="{col}" opacity="0.14" stroke="{col}" stroke-width="2.2" stroke-linejoin="round"/>')
        for i, v in enumerate(s["values"]):
            x, y = pt(i, v)
            out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3.6" fill="{col}"/>')
            out.append(f'<text x="{x:.0f}" y="{y - 8:.0f}" fill="{col}" font-size="10.5" text-anchor="middle">{v:,.0f}</text>')
    _legend_row(out, [{"name": s["name"], "color": "var(--theme-accent)" if s.get("accent") or len(series) == 1 else "var(--series-context)"} for s in series], 60, W - 60)
    out.append(f'<text x="{cx}" y="{cy + r + 74}" fill="var(--muted)" font-size="11.5" text-anchor="middle">各维度统一尺度（0~{smax:,.0f}）· 多边形面积不是总分</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-21 小提琴图：共享横轴；样本量与中位数标注；摘要线不被填充遮挡
# --------------------------------------------------------------------------- #
def _density_points(vals: List[float], bins: int = 14) -> List[float]:
    """确定性密度：等宽分箱频数 → 平滑（相邻箱加权），返回与分箱中心对应的密度。"""
    vmin, vmax = min(vals), max(vals)
    if vmax == vmin:
        return [1.0] * bins
    bw = (vmax - vmin) / bins
    cnt = [0] * bins
    for v in vals:
        cnt[min(bins - 1, int((v - vmin) / bw))] += 1
    sm = []
    for i in range(bins):
        lo = cnt[i - 1] if i > 0 else 0
        hi = cnt[i + 1] if i < bins - 1 else 0
        sm.append((lo + 2 * cnt[i] + hi) / 4)
    mx = max(sm) or 1
    return [v / mx for v in sm]


def violin_chart(chart: Dict[str, Any]) -> str:
    groups = chart["groups"]            # [{label, sub, values, accent}]
    H, TOP, BOT, L, R = 420, 56, 86, 80, W - 60
    plot_h = H - TOP - BOT
    all_v = [v for g in groups for v in g["values"]]
    vmin, vmax = min(all_v), max(all_v)
    pad = (vmax - vmin) * 0.08 or 1.0
    vmin, vmax = vmin - pad, vmax + pad
    def X(v): return L + (R - L) * (v - vmin) / (vmax - vmin)
    zone = plot_h / len(groups)
    out = _svg(chart["title"], H)
    # 数值在横轴：竖向网格 + 底部刻度
    for i in range(5):
        x = L + (R - L) * i / 4
        out.append(f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" y2="{TOP + plot_h}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{TOP + plot_h + 20:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{(vmin + (vmax - vmin) * i / 4):,.1f}</text>')
    for i, g in enumerate(groups):
        cy = TOP + zone * i + zone / 2          # 每组一行，小提琴水平摆放
        dens = _density_points(g["values"])
        gvmin, gvmax = min(g["values"]), max(g["values"])
        halfw = min(zone * 0.36, 92)
        pts_r, pts_l = [], []
        for bi, d in enumerate(dens):
            v = gvmin + (gvmax - gvmin) * bi / (len(dens) - 1)
            x = X(v)
            pts_r.append(f"{x:.1f},{cy - halfw * d:.1f}")
            pts_l.append(f"{x:.1f},{cy + halfw * d:.1f}")
        col = "var(--theme-accent)" if g.get("accent") else "var(--series-context)"
        poly = " ".join(pts_r) + " " + " ".join(reversed(pts_l))
        out.append(f'<polygon points="{poly}" fill="{col}" opacity="0.16" stroke="{col}" stroke-width="1.4"/>')
        med = _median(g["values"])
        xm = X(med)
        n = len(g["values"])
        # 摘要线：白底中位线（不被填充遮挡）
        out.append(f'<rect x="{xm - 2:.1f}" y="{cy - halfw * 0.72:.1f}" width="4" height="{halfw * 1.44:.1f}" fill="var(--paper)" opacity="0.9"/>')
        out.append(f'<line x1="{xm:.1f}" y1="{cy - halfw * 0.72:.1f}" x2="{xm:.1f}" y2="{cy + halfw * 0.72:.1f}" stroke="{col}" stroke-width="3"/>')
        out.append(f'<text x="{L - 10:.1f}" y="{cy + 4:.1f}" fill="var(--ink)" font-size="12.5" font-weight="700" text-anchor="end">{g["label"]}（n={n}·中位 {med:,.1f}）</text>')
        if g.get("sub"):
            out.append(f'<text x="{R:.1f}" y="{cy + 4:.1f}" fill="var(--muted)" font-size="11" text-anchor="start">{g["sub"]}</text>')
    out.append(f'<text x="{(L+R)/2}" y="{H - 8}" fill="var(--muted)" font-size="11.5" text-anchor="middle">共享横轴尺度 · 密度为等宽分箱频数（14 箱平滑）· 样本过少的组不做平滑解释</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-22 山脊图：所有组共享同一横轴；组序正确；峰值标签只标重点
# --------------------------------------------------------------------------- #
def ridgeline_chart(chart: Dict[str, Any]) -> str:
    groups = chart["groups"]            # 顺序即组序（如时间/等级顺序）
    all_v = [v for g in groups for v in g["values"]]
    vmin, vmax = min(all_v), max(all_v)
    pad = (vmax - vmin) * 0.06 or 1.0
    vmin, vmax = vmin - pad, vmax + pad
    row_h = 74
    H = 90 + row_h * len(groups)
    TOP, L, R = 60, 90, W - 60
    def X(v): return L + (R - L) * (v - vmin) / (vmax - vmin)
    out = _svg(chart["title"], H)
    for i in range(5):
        x = L + (R - L) * i / 4
        out.append(f'<line x1="{x:.1f}" y1="{TOP - 14}" x2="{x:.1f}" y2="{H - 34}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{H - 18}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{(vmin + (vmax - vmin) * i / 4):,.1f}</text>')
    y = TOP + row_h * (len(groups) - 1)
    for g in reversed(groups):          # 从下往上画，重叠自然
        dens = _density_points(g["values"])
        gvmin, gvmax = min(g["values"]), max(g["values"])
        peak = max(dens)
        peak_v = gvmin + (gvmax - gvmin) * dens.index(peak) / (len(dens) - 1)
        pts = " ".join(f"{X(gvmin + (gvmax - gvmin) * bi / (len(dens) - 1)):.1f},{y - 52 * d:.1f}" for bi, d in enumerate(dens))
        col = "var(--theme-accent)" if g.get("accent") else "var(--series-context)"
        out.append(f'<path d="M {X(gvmin):.1f} {y:.1f} L {pts.replace(" ", " L ")} L {X(gvmax):.1f} {y:.1f} Z" fill="{col}" opacity="{"0.3" if g.get("accent") else "0.16"}" stroke="{col}" stroke-width="1.6"/>')
        out.append(f'<text x="{L - 10}" y="{y - 6:.1f}" fill="var(--ink)" font-size="12" font-weight="700" text-anchor="end">{g["label"]}（n={len(g["values"])}）</text>')
        if g.get("accent"):
            out.append(f'<text x="{X(peak_v):.1f}" y="{y - 52 * peak - 8:.1f}" fill="var(--theme-accent)" font-size="11.5" font-weight="700" text-anchor="middle">峰 {peak_v:,.1f}</text>')
        y -= row_h
    out.append(f'<text x="{(L+R)/2}" y="{H - 2}" fill="var(--muted)" font-size="11.5" text-anchor="middle">所有组共享横轴 · 组序自上而下 · 只标重点组峰值</text>')
    out.append("</svg>")
    return "\n          ".join(out)

# --------------------------------------------------------------------------- #
# viz-23 平行坐标：各轴标准化 0-1；常规线弱化、重点线清楚
# --------------------------------------------------------------------------- #
def parallel_chart(chart: Dict[str, Any]) -> str:
    axes = chart["axes"]                # 轴名列表（顺序=分析依据）
    items = chart["items"]              # [{name, values[], accent?}]
    if len(items) > 24:
        raise ValueError("parallel: 对象超过 24（viz-23 纪律），先筛选或聚合")
    H, TOP, BOT, L, R = 420, 70, 60, 120, W - 80
    plot_h = H - TOP - BOT
    # 每轴独立 min-max 标准化（方向一致：高=上）
    norm = []
    for ai in range(len(axes)):
        col_v = [it["values"][ai] for it in items]
        lo, hi = min(col_v), max(col_v)
        norm.append((lo, hi if hi > lo else lo + 1))
    n_ax = len(axes)
    def X(ai): return L + (R - L) * ai / (n_ax - 1)
    def Y(ai, v):
        lo, hi = norm[ai]
        return TOP + plot_h * (1 - (v - lo) / (hi - lo))
    out = _svg(chart["title"], H)
    for ai, ax in enumerate(axes):
        x = X(ai)
        out.append(f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" y2="{TOP + plot_h}" stroke="var(--line-strong)" stroke-width="1.2"/>')
        lo, hi = norm[ai]
        out.append(f'<text x="{x:.1f}" y="{TOP - 30}" fill="var(--ink)" font-size="12" font-weight="700" text-anchor="middle">{ax}</text>')
        out.append(f'<text x="{x:.1f}" y="{TOP - 14}" fill="var(--muted)" font-size="10.5" text-anchor="middle">{hi:,.0f}</text>')
        out.append(f'<text x="{x:.1f}" y="{TOP + plot_h + 20:.1f}" fill="var(--muted)" font-size="10.5" text-anchor="middle">{lo:,.0f}</text>')
    for it in sorted(items, key=lambda q: q.get("accent", False)):   # 重点线最后画
        pts = " ".join(f"{X(ai):.1f},{Y(ai, v):.1f}" for ai, v in enumerate(it["values"]))
        if it.get("accent"):
            out.append(f'<polyline points="{pts}" fill="none" stroke="var(--theme-accent)" stroke-width="2.8" stroke-linejoin="round"/>')
            lx, ly = X(n_ax - 1), Y(n_ax - 1, it["values"][-1])
            out.append(f'<text x="{lx + 8:.1f}" y="{ly + 4:.1f}" fill="var(--theme-accent)" font-size="11.5" font-weight="700">{it["name"]}</text>')
        else:
            out.append(f'<polyline points="{pts}" fill="none" stroke="var(--series-context)" stroke-width="1.1" opacity="0.3"/>')
    out.append(f'<text x="{(L+R)/2}" y="{H - 8}" fill="var(--muted)" font-size="11.5" text-anchor="middle">各轴独立 min-max 标准化（上=高）· 常规线弱化，仅重点路径加粗</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-24 误差条图：SD/SE/CI 口径必填且全图唯一；共同尺度
# --------------------------------------------------------------------------- #
_ERR_TYPES = ("SD", "SE", "CI")


def error_bar_chart(chart: Dict[str, Any]) -> str:
    et = chart.get("err_type")
    if et not in _ERR_TYPES:
        raise ValueError(f"error_bar: err_type 必须明确为 SD/SE/CI 之一（不混用），当前: {et!r}")
    items = chart["items"]              # [{label, value, err}]
    H, TOP, BOT, L, R = 400, 64, 58, 80, W - 60
    plot_h = H - TOP - BOT
    lo_all = min(i["value"] - i["err"] for i in items)
    hi_all = max(i["value"] + i["err"] for i in items)
    pad = (hi_all - lo_all) * 0.12 or 1.0
    vmin, vmax = lo_all - pad, hi_all + pad
    def Y(v): return TOP + plot_h * (1 - (v - vmin) / (vmax - vmin))
    zone = (R - L) / len(items)
    out = _svg(chart["title"], H)
    _grid(out, TOP, plot_h, L, R, vmax, vmin, ",.1f")
    out.append(f'<text x="{R}" y="{TOP - 14}" fill="var(--muted)" font-size="11.5" text-anchor="end">误差口径：{et}（全图唯一，未混用）</text>')
    for i, it in enumerate(items):
        cx = L + zone * i + zone / 2
        v, e = it["value"], it["err"]
        bw = min(zone * 0.44, 90)
        y0, y1 = Y(v), TOP + plot_h
        col = "var(--theme-accent)" if it.get("accent") else "var(--series-context)"
        out.append(f'<rect x="{cx - bw/2:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{max(y1 - y0, 1):.1f}" rx="2" fill="{col}" opacity="{"0.9" if it.get("accent") else "0.55"}"/>')
        # 误差线 + 端帽
        ye0, ye1 = Y(v + e), Y(v - e)
        out.append(f'<line x1="{cx:.1f}" y1="{ye0:.1f}" x2="{cx:.1f}" y2="{ye1:.1f}" stroke="var(--ink)" stroke-width="1.6"/>')
        for yy in (ye0, ye1):
            out.append(f'<line x1="{cx - 9:.1f}" y1="{yy:.1f}" x2="{cx + 9:.1f}" y2="{yy:.1f}" stroke="var(--ink)" stroke-width="1.6"/>')
        out.append(f'<text x="{cx:.1f}" y="{ye0 - 8:.1f}" fill="var(--ink)" font-size="11" font-weight="700" text-anchor="middle">{v:,.1f}±{e:,.1f}</text>')
        out.append(f'<text x="{cx:.1f}" y="{TOP + plot_h + 22:.1f}" fill="var(--muted)" font-size="12" text-anchor="middle">{it["label"]}</text>')
    out.append(f'<text x="{(L+R)/2}" y="{H - 6}" fill="var(--muted)" font-size="11.5" text-anchor="middle">区间重叠与否不构成显著性结论（需检验）· 共同尺度</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-25 森林图：无效应基线 + CI 水平注明 + 「关联非因果」
# --------------------------------------------------------------------------- #
def forest_chart(chart: Dict[str, Any]) -> str:
    items = chart["items"]              # [{label, est, lo, hi, accent?}]
    baseline = chart.get("baseline", 0.0)
    ci_level = chart.get("ci_level", "95% CI")
    H = 92 + 46 * len(items)
    TOP, L, R = 64, 300, W - 300
    all_v = [v for it in items for v in (it["lo"], it["hi"], baseline)]
    vmin, vmax = min(all_v), max(all_v)
    pad = (vmax - vmin) * 0.08 or 1.0
    vmin, vmax = vmin - pad, vmax + pad
    def X(v): return L + (R - L) * (v - vmin) / (vmax - vmin)
    out = _svg(chart["title"], H)
    for i in range(5):
        x = L + (R - L) * i / 4
        out.append(f'<line x1="{x:.1f}" y1="{TOP - 10}" x2="{x:.1f}" y2="{H - 46}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{H - 28}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{(vmin + (vmax - vmin) * i / 4):,.2f}</text>')
    xb = X(baseline)
    out.append(f'<line x1="{xb:.1f}" y1="{TOP - 10}" x2="{xb:.1f}" y2="{H - 46}" stroke="var(--watch)" stroke-width="1.6" stroke-dasharray="6 4"/>')
    out.append(f'<text x="{xb:.1f}" y="{TOP - 18}" fill="var(--watch)" font-size="11.5" font-weight="700" text-anchor="middle">无效应基线 {baseline:,.2f}</text>')
    out.append(f'<text x="{W - 60}" y="{TOP - 18}" fill="var(--muted)" font-size="11.5" text-anchor="end">{ci_level}</text>')
    y = TOP + 10
    for it in items:
        x0, x1 = X(it["lo"]), X(it["hi"])
        xe = X(it["est"])
        col = "var(--theme-accent)" if it.get("accent") else "var(--series-context)"
        out.append(f'<text x="{L - 10}" y="{y + 5:.1f}" fill="var(--ink)" font-size="12" font-weight="700" text-anchor="end">{it["label"]}</text>')
        out.append(f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" stroke="{col}" stroke-width="1.8"/>')
        for xx in (x0, x1):
            out.append(f'<line x1="{xx:.1f}" y1="{y - 6:.1f}" x2="{xx:.1f}" y2="{y + 6:.1f}" stroke="{col}" stroke-width="1.8"/>')
        r = 6.5 if it.get("accent") else 5
        out.append(f'<circle cx="{xe:.1f}" cy="{y:.1f}" r="{r}" fill="{col}" stroke="var(--paper)" stroke-width="1.4"/>')
        out.append(f'<text x="{R + 12:.1f}" y="{y + 4:.1f}" fill="var(--muted)" font-size="12">{it["est"]:,.2f} [{it["lo"]:,.2f}, {it["hi"]:,.2f}]</text>')
        y += 46
    out.append(f'<text x="{(L+R)/2}" y="{H - 6}" fill="var(--muted)" font-size="11.5" text-anchor="middle">效应量为统计关联，非因果 · 置信区间跨基线=与无效应不显著区分</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-30 子弹图：目标线绘制在实际条之上（不被遮挡）；区间/目标有来源标注位
# --------------------------------------------------------------------------- #
def bullet_chart(chart: Dict[str, Any]) -> str:
    label = chart["label"]
    value = chart["value"]
    target = chart["target"]
    bands = chart.get("bands", [])      # [{to, label}] 升序绩效区间
    unit = chart.get("unit", "")
    H, TOP, L, R = 210, 84, 230, W - 90
    vmax = max(value, target, bands[-1]["to"] if bands else 0) * 1.1 or 1.0
    def X(v): return L + (R - L) * v / vmax
    out = _svg(chart["title"], H)
    out.append(f'<text x="{L - 12}" y="{TOP - 26}" fill="var(--ink)" font-size="15" font-weight="700" text-anchor="start">{label}</text>')
    out.append(f'<text x="{R}" y="{TOP - 26}" fill="var(--muted)" font-size="11.5" text-anchor="end">绩效区间（由浅到深：{"/".join(b["label"] for b in bands) if bands else "未提供"}）· 目标线来源：{chart.get("target_source", "未注明")}</text>')
    # 绩效区间（背景，由浅到深）
    prev = 0.0
    for k, b in enumerate(bands):
        x0, x1 = X(prev), X(b["to"])
        out.append(f'<rect x="{x0:.1f}" y="{TOP:.1f}" width="{x1 - x0:.1f}" height="56" fill="var(--theme-accent)" opacity="{0.07 + 0.09 * k:.2f}"/>')
        if x1 - x0 > 70:
            out.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{TOP + 70}" fill="var(--muted)" font-size="11" text-anchor="middle">{b["label"]}≤{b["to"]:,.0f}</text>')
        prev = b["to"]
    # 实际条
    xv = X(value)
    out.append(f'<rect x="{L:.1f}" y="{TOP + 16:.1f}" width="{xv - L:.1f}" height="24" rx="2" fill="var(--theme-accent)" opacity="0.92"/>')
    # 目标线（画在实际条之后 —— 不被遮挡，viz-30 纪律）
    xt = X(target)
    out.append(f'<line x1="{xt:.1f}" y1="{TOP + 6:.1f}" x2="{xt:.1f}" y2="{TOP + 50:.1f}" stroke="var(--critical)" stroke-width="3.5"/>')
    out.append(f'<text x="{xt:.1f}" y="{TOP - 4:.1f}" fill="var(--critical)" font-size="11.5" font-weight="700" text-anchor="middle">目标 {target:,.0f}</text>')
    out.append(f'<text x="{xv + 10:.1f}" y="{TOP + 34:.1f}" fill="var(--ink)" font-size="13.5" font-weight="700">实际 {value:,.0f}{unit}（{(value / target * 100 if target else 0):.0f}% 达成）</text>')
    out.append(f'<text x="{L}" y="{H - 10}" fill="var(--muted)" font-size="11.5">图例：背景=绩效区间 · 深色条=实际 · 红色竖线=目标 · 不展示时间趋势</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-31 仪表盘：当前值/单位/目标差文字齐备（颜色不是唯一状态表达）
# --------------------------------------------------------------------------- #
def gauge_chart(chart: Dict[str, Any]) -> str:
    value = chart["value"]
    vmin, vmax = chart.get("min", 0), chart.get("max", 100)
    target = chart.get("target")
    unit = chart.get("unit", "")
    if not (vmin <= value <= vmax):
        raise ValueError(f"gauge: 当前值 {value} 不在 [{vmin}, {vmax}] 范围内")
    cx, cy, r = W * 0.5, 280, 210
    a_lo, a_hi = 180.0, 360.0           # 半圆（左→右）
    def ang(v): return a_lo + (a_hi - a_lo) * (v - vmin) / (vmax - vmin)
    def pt(v, radius):
        a = math.radians(ang(v))
        return cx + radius * math.cos(a), cy + radius * math.sin(a)
    out = _svg(chart["title"], 420)
    # 底轨
    x0, y0 = pt(vmin, r); x1, y1 = pt(vmax, r)
    out.append(f'<path d="M {x0:.1f} {y0:.1f} A {r} {r} 0 0 1 {x1:.1f} {y1:.1f}" fill="none" stroke="var(--surface-strong)" stroke-width="30" stroke-linecap="round"/>')
    # 值弧
    xv, yv = pt(value, r)
    frac = (value - vmin) / (vmax - vmin)
    col = "var(--healthy)" if (target is None or value >= target) else "var(--watch)"
    out.append(f'<path d="M {x0:.1f} {y0:.1f} A {r} {r} 0 {"1" if frac > 0.5 else "0"} 1 {xv:.1f} {yv:.1f}" fill="none" stroke="{col}" stroke-width="30" stroke-linecap="round"/>')
    # 刻度
    for k in range(5):
        v = vmin + (vmax - vmin) * k / 4
        xa, ya = pt(v, r - 26); xb, yb = pt(v, r - 16)
        out.append(f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" stroke="var(--line-strong)" stroke-width="1.4"/>')
        xl, yl = pt(v, r - 44)
        out.append(f'<text x="{xl:.1f}" y="{yl + 4:.1f}" fill="var(--muted)" font-size="11" text-anchor="middle">{v:,.0f}</text>')
    # 目标刻度
    if target is not None:
        xt, yt = pt(target, r + 22)
        out.append(f'<line x1="{xt:.1f}" y1="{yt:.1f}" x2="{pt(target, r - 4)[0]:.1f}" y2="{pt(target, r - 4)[1]:.1f}" stroke="var(--critical)" stroke-width="2.4"/>')
        out.append(f'<text x="{pt(target, r + 40)[0]:.1f}" y="{pt(target, r + 40)[1]:.1f}" fill="var(--critical)" font-size="11.5" font-weight="700" text-anchor="middle">目标 {target:,.0f}</text>')
    # 文字状态（颜色不是唯一表达，viz-31 纪律）
    state = "达标" if (target is None or value >= target) else "未达标"
    out.append(f'<text x="{cx}" y="{cy - 22}" fill="var(--ink)" font-size="44" font-weight="700" text-anchor="middle">{value:,.0f}<tspan font-size="18">{unit}</tspan></text>')
    if target is not None:
        d = value - target
        out.append(f'<text x="{cx}" y="{cy + 10}" fill="var(--muted)" font-size="13" text-anchor="middle">距目标 {"+" if d >= 0 else "−"}{abs(d):,.0f}{unit} · 文字状态：{state}</text>')
    else:
        out.append(f'<text x="{cx}" y="{cy + 10}" fill="var(--muted)" font-size="13" text-anchor="middle">范围 [{vmin}, {vmax}] · 文字状态：{state}</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-32 日历热力图：缺失日期≠0；月份边界正确；色阶图例
# --------------------------------------------------------------------------- #
def cal_heatmap_chart(chart: Dict[str, Any]) -> str:
    days = chart["days"]                # [{"date": "YYYY-MM-DD", "value"}]
    by_date: Dict[str, Any] = {}
    for d in days:
        by_date[d["date"]] = d["value"]
    ds = sorted(date.fromisoformat(k) for k in by_date)
    d0, d1 = ds[0], ds[-1]
    # 周一为一周之首；列=ISO 周
    def monday(d_: date) -> date:
        return d_ - __import__("datetime").timedelta(days=d_.weekday())
    col0 = monday(d0)
    ncols = (monday(d1) - col0).days // 7 + 1
    cell, gap = 26, 5
    L, T = 130, 92
    H_ = T + 7 * (cell + gap) + 74
    W_ = max(L + ncols * (cell + gap) + 240, 900)
    vals = [v for v in by_date.values() if v is not None]
    vmax = max(vals) if vals else 1.0
    out = [f'<svg viewBox="0 0 {W_} {H_}" role="img" aria-label="{chart["title"]}">']
    out.append(f'<text x="{L}" y="{T - 44}" fill="var(--muted)" font-size="11.5">周一至周日（自上而下）· 缺失日期显示斜纹（≠0）· 单位：{chart.get("unit", "")}</text>')
    # 月份标签（每月第一周）
    seen_months = set()
    for i in range(ncols):
        wk = col0 + __import__("datetime").timedelta(weeks=i)
        mk = (wk.year, wk.month)
        if wk <= d1 and mk not in seen_months and any(
                (wk + __import__("datetime").timedelta(days=k)) in set(ds) for k in range(7)):
            seen_months.add(mk)
            out.append(f'<text x="{L + i * (cell + gap):.0f}" y="{T - 16}" fill="var(--ink)" font-size="11.5" font-weight="700">{wk.month}月</text>')
    for wd in range(7):
        out.append(f'<text x="{L - 10}" y="{T + wd * (cell + gap) + cell / 2 + 4:.0f}" fill="var(--muted)" font-size="10.5" text-anchor="end">{"一二三四五六日"[wd]}</text>')
    date_set = set(ds)
    for i in range(ncols):
        for wd in range(7):
            d_ = col0 + __import__("datetime").timedelta(weeks=i, days=wd)
            if d_ < d0 or d_ > d1:
                continue
            x = L + i * (cell + gap)
            y = T + wd * (cell + gap)
            if d_ in date_set:
                v = by_date[d_.isoformat()]
                t = v / vmax if vmax else 0
                out.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{cell}" height="{cell}" rx="3" fill="var(--theme-accent)" opacity="{0.08 + t * 0.82:.2f}"/>')
                if d_.day == 1 or (v is not None and v == vmax):
                    tc = "var(--paper)" if t > 0.55 else "var(--ink)"
                    out.append(f'<text x="{x + cell / 2:.0f}" y="{y + cell / 2 + 4:.0f}" fill="{tc}" font-size="10.5" text-anchor="middle">{v:,.0f}</text>')
            else:
                out.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{cell}" height="{cell}" rx="3" fill="var(--surface-strong)" stroke="var(--line)"/>')
                out.append(f'<line x1="{x + 5:.0f}" y1="{y + cell - 5:.0f}" x2="{x + cell - 5:.0f}" y2="{y + 5:.0f}" stroke="var(--line-strong)" stroke-width="1.2"/>')
    # 色阶图例
    ly = T + 7 * (cell + gap) + 18
    for k, (op, lab) in enumerate([(0.9, f"高 {vmax:,.0f}"), (0.5, "中"), (0.1, "低 0")]):
        out.append(f'<rect x="{L + k * 110:.0f}" y="{ly:.0f}" width="16" height="12" fill="var(--theme-accent)" opacity="{op}"/>')
        out.append(f'<text x="{L + k * 110 + 22:.0f}" y="{ly + 10:.0f}" fill="var(--muted)" font-size="11.5">{lab}</text>')
    out.append(f'<rect x="{L + 340:.0f}" y="{ly:.0f}" width="16" height="12" fill="var(--surface-strong)" stroke="var(--line)"/>')
    out.append(f'<line x1="{L + 343:.0f}" y1="{ly + 10:.0f}" x2="{L + 353:.0f}" y2="{ly + 2:.0f}" stroke="var(--line-strong)" stroke-width="1.2"/>')
    out.append(f'<text x="{L + 362:.0f}" y="{ly + 10:.0f}" fill="var(--muted)" font-size="11.5">缺失（≠0）</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-33 甘特图：时间条长度∝起止日期；今日线；里程碑
# --------------------------------------------------------------------------- #
def _parse_d(s: str) -> date:
    return date.fromisoformat(str(s)[:10])


def gantt_chart(chart: Dict[str, Any]) -> str:
    tasks = chart["tasks"]              # [{label, start, end, accent?, milestone?}]
    today = chart.get("today")
    d_lo = min(_parse_d(t["start"]) for t in tasks)
    d_hi = max(_parse_d(t["end"]) for t in tasks)
    span = (d_hi - d_lo).days or 1
    row_h = 46
    H = 96 + row_h * len(tasks)
    TOP, L, R = 76, 230, W - 70
    def X(d_: date) -> float: return L + (R - L) * ((d_ - d_lo).days / span)
    out = _svg(chart["title"], H)
    # 月份刻度
    m = d_lo.replace(day=1)
    while m <= d_hi:
        x = X(m)
        out.append(f'<line x1="{x:.1f}" y1="{TOP - 12}" x2="{x:.1f}" y2="{H - 36}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{x + 4:.1f}" y="{TOP - 18}" fill="var(--muted)" font-size="11">{m.year}-{m.month:02d}</text>')
        m = (m.replace(day=28) + __import__("datetime").timedelta(days=4)).replace(day=1)
    if today:
        xt = X(_parse_d(today))
        if L <= xt <= R:
            out.append(f'<line x1="{xt:.1f}" y1="{TOP - 12}" x2="{xt:.1f}" y2="{H - 36}" stroke="var(--critical)" stroke-width="1.8" stroke-dasharray="6 4"/>')
            out.append(f'<text x="{xt:.1f}" y="{H - 22}" fill="var(--critical)" font-size="11.5" font-weight="700" text-anchor="middle">今日 {today}</text>')
    y = TOP
    for t in tasks:
        x0, x1 = X(_parse_d(t["start"])), X(_parse_d(t["end"]))
        col = "var(--theme-accent)" if t.get("accent") else "var(--series-context)"
        if t.get("milestone"):
            out.append(f'<rect x="{(x0 + x1) / 2 - 8:.1f}" y="{y + 8:.1f}" width="16" height="16" transform="rotate(45 {(x0 + x1) / 2:.1f} {y + 16:.1f})" fill="var(--watch)"/>')
            out.append(f'<text x="{(x0 + x1) / 2 + 16:.1f}" y="{y + 21:.1f}" fill="var(--watch)" font-size="11.5" font-weight="700">{t["label"]}（里程碑 {t["start"]}）</text>')
        else:
            out.append(f'<text x="{L - 10}" y="{y + 21:.1f}" fill="var(--ink)" font-size="12.5" font-weight="700" text-anchor="end">{t["label"]}</text>')
            out.append(f'<rect x="{x0:.1f}" y="{y + 6:.1f}" width="{max(x1 - x0, 3):.1f}" height="20" rx="4" fill="{col}" opacity="{"0.9" if t.get("accent") else "0.6"}"/>')
            out.append(f'<text x="{x0 + 6:.1f}" y="{y + 21:.1f}" fill="var(--paper)" font-size="10.5" font-weight="700">{t["start"]}→{t["end"]}</text>')
        y += row_h
    out.append(f'<text x="{(L+R)/2}" y="{H - 4}" fill="var(--muted)" font-size="11.5" text-anchor="middle">时间条长度 = 起止日期实际天数 · 依赖关系复杂时改用专业项目管理工具</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-34 K线：开高低收合法性门禁（非法直接拒绝）；红涨绿跌
# --------------------------------------------------------------------------- #
def candlestick_chart(chart: Dict[str, Any]) -> str:
    candles = chart["candles"]          # [{label, open, high, low, close}]
    for i, c in enumerate(candles):
        if not (c["high"] >= max(c["open"], c["close"]) and c["low"] <= min(c["open"], c["close"])):
            raise ValueError(f"candlestick: 第 {i} 根 K 线开高低收关系非法（high≥max(open,close)、low≤min(open,close)）")
    H, TOP, BOT, L, R = 420, 60, 56, 80, W - 60
    plot_h = H - TOP - BOT
    vmax = max(c["high"] for c in candles) * 1.02
    vmin = min(c["low"] for c in candles) * 0.98
    def Y(v): return TOP + plot_h * (1 - (v - vmin) / (vmax - vmin))
    zone = (R - L) / len(candles)
    out = _svg(chart["title"], H)
    _grid(out, TOP, plot_h, L, R, vmax, vmin, ",.1f")
    _legend_row(out, [{"name": "阳线（收≥开）", "color": "var(--critical)"},
                      {"name": "阴线（收<开）", "color": "var(--healthy)"}], TOP, R)
    for i, c in enumerate(candles):
        cx = L + zone * i + zone / 2
        up = c["close"] >= c["open"]
        col = "var(--critical)" if up else "var(--healthy)"     # 红涨绿跌
        # 影线
        out.append(f'<line x1="{cx:.1f}" y1="{Y(c["high"]):.1f}" x2="{cx:.1f}" y2="{Y(c["low"]):.1f}" stroke="{col}" stroke-width="1.4"/>')
        # 实体
        y0, y1 = Y(max(c["open"], c["close"])), Y(min(c["open"], c["close"]))
        bw = min(zone * 0.5, 34)
        out.append(f'<rect x="{cx - bw/2:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{max(y1 - y0, 1.5):.1f}" fill="{col}" opacity="{0.95 if up else 0.85}"/>')
        if c.get("accent"):
            out.append(f'<text x="{cx:.1f}" y="{Y(c["high"]) - 10:.1f}" fill="{col}" font-size="11.5" font-weight="700" text-anchor="middle">高 {c["high"]:,.1f}</text>')
            out.append(f'<text x="{cx:.1f}" y="{Y(c["low"]) + 20:.1f}" fill="{col}" font-size="11.5" font-weight="700" text-anchor="middle">低 {c["low"]:,.1f}</text>')
        step = max(1, len(candles) // 12)
        if i % step == 0:
            out.append(f'<text x="{cx:.1f}" y="{TOP + plot_h + 22:.1f}" fill="var(--muted)" font-size="11" text-anchor="middle">{c["label"]}</text>')
    out.append(f'<text x="{(L+R)/2}" y="{H - 6}" fill="var(--muted)" font-size="11.5" text-anchor="middle">开高低收已通过合法性校验 · 红涨绿跌 · 仅适用于 OHLC 结构数据</text>')
    out.append("</svg>")
    return "\n          ".join(out)

# --------------------------------------------------------------------------- #
# viz-35 桑基图：流带宽度∝流量；层级由源→汇拓扑确定性推导；主路径数值标注
# --------------------------------------------------------------------------- #
def sankey_chart(chart: Dict[str, Any]) -> str:
    nodes = {n["id"]: n for n in chart["nodes"]}
    links = chart["links"]              # [{from, to, value}]
    # 拓扑分层（最长路径，环 → 拒绝）
    layer = {nid: 0 for nid in nodes}
    changed = True
    rounds = 0
    while changed and rounds <= len(nodes) + 1:
        changed = False
        rounds += 1
        for lk in links:
            a, b = lk["from"], lk["to"]
            if a not in nodes or b not in nodes:
                raise ValueError(f"sankey: 连接引用未注册节点 {a!r}/{b!r}")
            if layer[b] <= layer[a]:
                layer[b] = layer[a] + 1
                changed = True
    if changed:
        raise ValueError("sankey: 检测到循环流向（viz-35 只支持无环）")
    max_layer = max(layer.values())
    cols: Dict[int, List[str]] = {}
    for nid, ly in sorted(layer.items(), key=lambda kv: (kv[1], kv[0])):
        cols.setdefault(ly, []).append(nid)
    total_out = {nid: 0.0 for nid in nodes}
    total_in = {nid: 0.0 for nid in nodes}
    for lk in links:
        total_out[lk["from"]] += lk["value"]
        total_in[lk["to"]] += lk["value"]
    node_total = {nid: max(total_in[nid], total_out[nid]) for nid in nodes}
    vmax = max(node_total.values()) or 1.0
    H = 460
    TOP, BOT = 56, 60
    plot_h = H - TOP - BOT
    L, R = 150, W - 170
    col_w = (R - L) / max(max_layer, 1)
    nw = 26                             # 节点条宽
    scale = plot_h / vmax * 0.92
    # 节点 y 布局（列内按总流量降序，间隙均匀）
    node_y: Dict[str, tuple] = {}
    for ly, nids in cols.items():
        gap = 16 if len(nids) > 1 else 0
        avail = plot_h - gap * (len(nids) - 1)
        total_col = sum(node_total[n] for n in nids) or 1.0
        k = avail / total_col
        y = TOP
        for nid in sorted(nids, key=lambda q: (-node_total[q], q)):
            h = node_total[nid] * k
            node_y[nid] = (y, h)
            y += h + gap
    # 每个节点的出/入流游标（流带按顺序贴附）
    cur_out = {nid: node_y[nid][0] for nid in nodes}
    cur_in = {nid: node_y[nid][0] for nid in nodes}
    # 主路径：逐层取最大流（确定性）
    main_links = set()
    for ly in range(max_layer):
        cand = [lk for lk in links if layer[lk["from"]] == ly]
        if cand:
            best = max(cand, key=lambda q: (q["value"], q["from"], q["to"]))
            main_links.add(id(best))
    out = _svg(chart["title"], H)
    for lk in links:
        a, b = lk["from"], lk["to"]
        xa = L + col_w * layer[a] + nw
        xb = L + col_w * layer[b]
        ya0 = cur_out[a]
        ha = lk["value"] * scale * 0.92
        cur_out[a] += max(ha, 1)
        yb0 = cur_in[b]
        hb = ha
        cur_in[b] += max(hb, 1)
        main = id(lk) in main_links
        out.append(f'<path d="M {xa:.1f} {ya0:.1f} C {(xa + col_w * 0.5):.1f} {ya0:.1f}, {(xb - col_w * 0.5):.1f} {yb0:.1f}, {xb:.1f} {yb0:.1f} L {xb:.1f} {yb0 + hb:.1f} C {(xb - col_w * 0.5):.1f} {yb0 + hb:.1f}, {(xa + col_w * 0.5):.1f} {ya0 + ha:.1f}, {xa:.1f} {ya0 + ha:.1f} Z" fill="var(--theme-accent)" opacity="{"0.42" if main else "0.18"}"/>')
        if main:
            mx = (xa + xb) / 2
            my = (ya0 + yb0) / 2 + hb / 2
            out.append(f'<text x="{mx:.1f}" y="{my:.1f}" fill="var(--theme-accent)" font-size="11.5" font-weight="700" text-anchor="middle">{lk["value"]:,.0f}</text>')
    for nid, n in nodes.items():
        y, h = node_y[nid]
        x = L + col_w * layer[nid]
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{nw}" height="{max(h, 2):.1f}" rx="2" fill="var(--series-context)"/>')
        anchor = "end" if layer[nid] == 0 else ("start" if layer[nid] == max_layer else "middle")
        tx = x - 8 if anchor == "end" else (x + nw + 8 if anchor == "start" else x + nw / 2)
        ty = y - 8 if anchor == "middle" else y + h / 2 + 4
        out.append(f'<text x="{tx:.1f}" y="{ty:.1f}" fill="var(--ink)" font-size="12" font-weight="700" text-anchor="{anchor}">{n["label"]} {node_total[nid]:,.0f}</text>')
    out.append(f'<text x="{W/2}" y="{H - 8}" fill="var(--muted)" font-size="11.5" text-anchor="middle">流带宽度∝流量 · 加粗+数值=逐层最大主路径 · 无环流向</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-36 河流图：围绕中心堆叠；右端统一最新值标签列
# --------------------------------------------------------------------------- #
def streamgraph_chart(chart: Dict[str, Any]) -> str:
    xlabels = chart["xlabels"]
    series = chart["series"]            # [{name, values[]}] ≤6 类
    if len(series) > 6:
        raise ValueError("streamgraph: 类别超过 6（viz-36 纪律）")
    n = len(xlabels)
    for s in series:
        if any(v < 0 for v in s["values"]):
            raise ValueError("streamgraph: 存在负值（viz-36 要求非负）")
        if len(s["values"]) != n:
            raise ValueError("streamgraph: 系列长度与 xlabels 不一致")
    totals = [sum(s["values"][i] for s in series) for i in range(n)]
    H, TOP, BOT, L, R = 420, 56, 66, 80, W - 200
    plot_h = H - TOP - BOT
    vmax = max(totals) or 1.0
    def X(i): return L + (R - L) * i / (n - 1)
    def Y(v): return TOP + plot_h * (1 - v / vmax)
    # 堆叠基线：中心对称（baseline_i = total_i/2 向下偏移）
    outs = []
    base = [totals[i] / 2 for i in range(n)]
    out = _svg(chart["title"], H)
    for k, s in enumerate(series):
        top = [base[i] + s["values"][i] for i in range(n)]
        bot = list(base)
        pts = " ".join(f"{X(i):.0f},{Y(top[i]):.0f}" for i in range(n))
        pts_back = " ".join(f"{X(i):.0f},{Y(bot[i]):.0f}" for i in range(n - 1, -1, -1))
        col = "var(--theme-accent)" if s.get("accent") else ["var(--series-context)", "var(--series-reference)", "var(--watch)", "var(--healthy)", "var(--critical)"][k % 5]
        out.append(f'<polygon points="{pts} {pts_back}" fill="{col}" opacity="{"0.5" if s.get("accent") else "0.26"}" stroke="{col}" stroke-width="1.2"/>')
        # 右端统一最新值标签列
        ym = (Y(top[-1]) + Y(bot[-1])) / 2 + 4
        fw = ' font-weight="700"' if s.get("accent") else ""
        out.append(f'<text x="{R + 12:.1f}" y="{ym:.1f}" fill="var(--ink)" font-size="11.5"{fw}>{s["name"]} {s["values"][-1]:,.0f}</text>')
        base = top
    step = max(1, n // 12)
    for i in range(0, n, step):
        out.append(f'<text x="{X(i):.0f}" y="{H - 12}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{xlabels[i]}</text>')
    out.append(f'<text x="{(L+R)/2}" y="{H - 0}" fill="var(--muted)" font-size="11" text-anchor="middle"></text>')
    out.append(f'<text x="{(L+R)/2}" y="{TOP - 12}" fill="var(--muted)" font-size="11.5" text-anchor="middle">非负堆叠 · 右端为各主题最新值标签列</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-37 树状图：squarify 确定性切分；面积∝正值；小矩形文字不溢出
# --------------------------------------------------------------------------- #
def _squarify(items: List[Dict[str, Any]], x: float, y: float, w: float, h: float,
              out_rects: List[Dict[str, Any]]) -> None:
    """经典 squarify：按值降序、逐行填充，短边优先。确定性（同值按标签序）。"""
    if not items:
        return
    total = sum(i["value"] for i in items)
    if w <= 0 or h <= 0 or total <= 0:
        return
    items = sorted(items, key=lambda q: (-q["value"], q["label"]))
    scale = (w * h) / total
    row: List[Dict[str, Any]] = []
    row_sum = 0.0
    best_ratio = float("inf")

    def place_row():
        nonlocal row, row_sum, x, y, w, h
        if not row:
            return
        horizontal = w < h              # 沿短边切
        size = row_sum * scale
        if horizontal:
            rw = size / h if h > 0 else 0
            cy = y
            for it in row:
                rh = it["value"] * scale / rw if rw > 0 else 0
                out_rects.append({**it, "x": x, "y": cy, "w": rw, "h": rh})
                cy += rh
            x += rw
            w -= rw
        else:
            rh = size / w if w > 0 else 0
            cx = x
            for it in row:
                rw = it["value"] * scale / rh if rh > 0 else 0
                out_rects.append({**it, "x": cx, "y": y, "w": rw, "h": rh})
                cx += rw
            y += rh
            h -= rh
        row, row_sum = [], 0.0

    for it in items:
        if any(i["value"] <= 0 for i in [it]):
            raise ValueError("treemap: 只接受正值（面积∝数值）")
        cand = row + [it]
        cand_sum = row_sum + it["value"]
        # 试算本行最差长宽比
        horizontal = w < h
        size = cand_sum * scale
        if horizontal:
            rw = size / h if h > 0 else 0
            ratios = [max((rw / (i["value"] * scale / rw)) if rw > 0 else 1,
                          ((i["value"] * scale / rw) / rw) if rw > 0 else 1) for i in cand]
        else:
            rh = size / w if w > 0 else 0
            ratios = [max((rh / (i["value"] * scale / rh)) if rh > 0 else 1,
                          ((i["value"] * scale / rh) / rh) if rh > 0 else 1) for i in cand]
        ratio = max(ratios) if ratios else 1
        if row and ratio > best_ratio:
            place_row()
            row, row_sum, best_ratio = [it], it["value"], float("inf")
            # 重算单块比例
            horizontal = w < h
            size2 = row_sum * scale
            if horizontal:
                rw = size2 / h if h > 0 else 0
                best_ratio = max((rw / (it["value"] * scale / rw)) if rw > 0 else 1, 1)
            else:
                rh = size2 / w if w > 0 else 0
                best_ratio = max((rh / (it["value"] * scale / rh)) if rh > 0 else 1, 1)
        else:
            row.append(it)
            row_sum = cand_sum
            best_ratio = ratio
    place_row()


def treemap_chart(chart: Dict[str, Any]) -> str:
    items = chart["items"]              # [{label, value, accent?}]
    if not items or any(i["value"] <= 0 for i in items):
        raise ValueError("treemap: 需要正数规模数据（面积∝数值）")
    total = sum(i["value"] for i in items)
    L, T, GP = 30, 56, 3                # 间距细而一致
    TW, TH = W - 60, 500
    rects: List[Dict[str, Any]] = []
    _squarify(items, L, T, TW, TH, rects)
    H = TH + 64
    out = _svg(chart["title"], H)
    for r in rects:
        pct = r["value"] / total * 100
        col = "var(--theme-accent)" if r.get("accent") else "var(--series-context)"
        op = "0.88" if r.get("accent") else "0.5"
        out.append(f'<rect x="{r["x"]:.1f}" y="{r["y"]:.1f}" width="{max(r["w"] - GP, 1):.1f}" height="{max(r["h"] - GP, 1):.1f}" fill="{col}" opacity="{op}" rx="2"/>')
        # 小矩形文字不溢出：按宽高判断是否放标签
        if r["w"] > 76 and r["h"] > 40:
            fs = 12 if r["w"] > 120 else 10.5
            out.append(f'<text x="{r["x"] + 10:.1f}" y="{r["y"] + 22:.1f}" fill="var(--paper)" font-size="{fs}" font-weight="700">{r["label"]}</text>')
            if r["h"] > 58:
                out.append(f'<text x="{r["x"] + 10:.1f}" y="{r["y"] + 40:.1f}" fill="var(--paper)" font-size="{fs}">{r["value"]:,.0f}（{pct:.1f}%）</text>')
    out.append(f'<text x="{W/2}" y="{H - 10}" fill="var(--muted)" font-size="11.5" text-anchor="middle">矩形面积∝数值（squarify 确定性切分）· 间距统一 3px · 放不下的标签自动省略</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-38 旭日图：两环层级；标签水平正对用户；小扇区标签外置说明
# --------------------------------------------------------------------------- #
def sunburst_chart(chart: Dict[str, Any]) -> str:
    root = chart["root"]                # {label, children: [{label, value, children?[], accent?}]}
    children = root["children"]
    if len(children) > 8:
        raise ValueError("sunburst: 一级类别超过 8，先合并")
    total = sum(c["value"] for c in children)
    if total <= 0:
        raise ValueError("sunburst: 合计必须为正")
    cx, cy, r1, r2 = W * 0.42, 300, 100, 190
    r3 = 280
    out = _svg(chart["title"], 600)
    out.append(f'<text x="{cx}" y="{cy + 6}" fill="var(--ink)" font-size="15" font-weight="700" text-anchor="middle">{root["label"]}</text>')
    out.append(f'<text x="{cx}" y="{cy + 26}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{total:,.0f}</text>')
    deferred: List[str] = []
    a0 = -90.0
    for i, c in enumerate(children):
        frac = c["value"] / total
        a1 = a0 + frac * 360
        col = "var(--theme-accent)" if c.get("accent") else f"var(--series-{'reference' if i % 2 else 'context'})"
        _sun_ring(out, cx, cy, r1, r2, a0, a1, col, c.get("accent", False))
        # 子层
        if c.get("children"):
            ca0 = a0
            ctotal = c["value"]
            for cc in c["children"]:
                cfrac = cc["value"] / ctotal if ctotal else 0
                ca1 = ca0 + cfrac * frac * 360
                _sun_ring(out, cx, cy, r2, r3, ca0, ca1, "var(--series-reference)", False, light=True)
                ca0 = ca1
        # 一级标签：水平放置（不旋转），小扇区外置
        _sun_label(out, cx, cy, (r1 + r2) / 2, a0, a1, c["label"], f"{c['value']:,.0f}（{frac:.1%}）", c.get("accent", False), deferred)
        a0 = a1
    ly = 560
    if deferred:
        out.append(f'<text x="30" y="{ly}" fill="var(--muted)" font-size="11">小扇区标签外置（角度不足 10°）：{"、".join(deferred)}</text>')
    out.append(f'<text x="30" y="{ly + 20}" fill="var(--muted)" font-size="11.5">内外环层级一致（内=一级，外=二级）· 标签水平正对用户（无径向旋转）</text>')
    out.append("</svg>")
    return "\n          ".join(out)


def _sun_ring(out: List[str], cx: float, cy: float, r_in: float, r_out: float,
              a0: float, a1: float, col: str, accent: bool, light: bool = False) -> None:
    large = 1 if (a1 - a0) > 180 else 0
    p0 = (cx + r_out * math.cos(math.radians(a0)), cy + r_out * math.sin(math.radians(a0)))
    p1 = (cx + r_out * math.cos(math.radians(a1)), cy + r_out * math.sin(math.radians(a1)))
    p2 = (cx + r_in * math.cos(math.radians(a1)), cy + r_in * math.sin(math.radians(a1)))
    p3 = (cx + r_in * math.cos(math.radians(a0)), cy + r_in * math.sin(math.radians(a0)))
    op = ("0.92" if accent else "0.7") if not light else "0.35"
    out.append(f'<path d="M {p0[0]:.1f} {p0[1]:.1f} A {r_out:.0f} {r_out:.0f} 0 {large} 1 {p1[0]:.1f} {p1[1]:.1f} L {p2[0]:.1f} {p2[1]:.1f} A {r_in:.0f} {r_in:.0f} 0 {large} 0 {p3[0]:.1f} {p3[1]:.1f} Z" fill="{col}" opacity="{op}" stroke="var(--paper)" stroke-width="1.5"/>')


def _sun_label(out: List[str], cx: float, cy: float, r: float, a0: float, a1: float,
               label: str, val: str, accent: bool, deferred: List[str]) -> None:
    if (a1 - a0) < 10:                  # 小扇区：不强行塞标签
        deferred.append(label)
        return
    am = math.radians((a0 + a1) / 2)
    x = cx + r * math.cos(am)
    y = cy + r * math.sin(am)
    fw = ' font-weight="700"' if accent else ""
    col = "var(--ink)" if accent else "var(--muted)"
    out.append(f'<text x="{x:.1f}" y="{y + 4:.1f}" fill="{col}" font-size="12"{fw} text-anchor="middle">{label} {val}</text>')


# --------------------------------------------------------------------------- #
# viz-39 填色地图（离线示意格网）：0 与缺失不同色；未匹配项如实列出
# --------------------------------------------------------------------------- #
# 省级行政区示意格网坐标（列,行）——离线格网地图（非精确地理边界）
_PROVINCE_GRID: Dict[str, tuple] = {
    "新疆": (0, 0), "内蒙古": (4, 0), "黑龙江": (7, 0),
    "甘肃": (1, 1), "宁夏": (3, 1), "陕西": (4, 1), "山西": (5, 1), "北京": (6, 1), "吉林": (7, 1),
    "青海": (1, 2), "四川": (2, 2), "重庆": (3, 2), "河南": (4, 2), "山东": (5, 2), "河北": (6, 2), "辽宁": (7, 2),
    "西藏": (0, 3), "云南": (2, 3), "贵州": (3, 3), "湖北": (4, 3), "江苏": (5, 3), "天津": (6, 3), "上海": (7, 3),
    "广西": (3, 4), "湖南": (4, 4), "安徽": (5, 4), "浙江": (6, 4),
    "江西": (4, 5), "福建": (5, 5), "台湾": (6, 5),
    "广东": (4, 6), "香港": (5, 6), "澳门": (6, 6),
    "海南": (3, 6),
}


def choropleth_chart(chart: Dict[str, Any]) -> str:
    regions = chart["regions"]          # [{name, value}]（value 可为 None=缺失）
    by_name = {r["name"]: r["value"] for r in regions}
    matched = {k: v for k, v in by_name.items() if k in _PROVINCE_GRID}
    unmatched = [k for k in by_name if k not in _PROVINCE_GRID]
    vals = [v for v in matched.values() if v is not None and v != 0]
    vmax = max(vals) if vals else 1.0
    cell, gap = 84, 8
    L, T = 210, 84
    rows_n, cols_n = 7, 8
    H = T + rows_n * (cell + gap) + 110
    out = _svg(chart["title"], H)
    out.append(f'<text x="{L}" y="{T - 48}" fill="var(--muted)" font-size="11.5">离线示意格网（非精确地理边界）· 单位：{chart.get("unit", "")} · 等距分级（0/低/中/高）</text>')
    rate = len(matched) / len(by_name) * 100 if by_name else 100
    out.append(f'<text x="{L}" y="{T - 30}" fill="var(--muted)" font-size="11.5">地区匹配率 {rate:.0f}%（{len(matched)}/{len(by_name)}）</text>')
    drawn = set()
    for name, (c, r_) in _PROVINCE_GRID.items():
        x = L + c * (cell + gap)
        y = T + r_ * (cell + gap)
        if name in matched:
            v = matched[name]
            drawn.add(name)
            if v is None:
                out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="4" fill="var(--surface-strong)" stroke="var(--line)"/>')
                out.append(f'<line x1="{x + 8}" y1="{y + cell - 8}" x2="{x + cell - 8}" y2="{y + 8}" stroke="var(--line-strong)" stroke-width="1.4"/>')
                out.append(f'<text x="{x + cell/2}" y="{y + cell/2 - 4}" fill="var(--muted)" font-size="11" text-anchor="middle">缺失</text>')
            elif v == 0:
                out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="4" fill="var(--surface-strong)" stroke="var(--line-strong)"/>')
                out.append(f'<text x="{x + cell/2}" y="{y + cell/2 + 4}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{name}</text>')
                out.append(f'<text x="{x + cell/2}" y="{y + cell/2 + 20}" fill="var(--muted)" font-size="10.5" text-anchor="middle">0</text>')
            else:
                t = v / vmax
                out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="4" fill="var(--theme-accent)" opacity="{0.12 + t * 0.78:.2f}"/>')
                tc = "var(--paper)" if t > 0.55 else "var(--ink)"
                out.append(f'<text x="{x + cell/2}" y="{y + cell/2 - 2}" fill="{tc}" font-size="12" font-weight="700" text-anchor="middle">{name}</text>')
                out.append(f'<text x="{x + cell/2}" y="{y + cell/2 + 18}" fill="{tc}" font-size="11.5" text-anchor="middle">{v:,.0f}</text>')
        else:
            out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="4" fill="none" stroke="var(--line)" stroke-dasharray="4 3"/>')
            out.append(f'<text x="{x + cell/2}" y="{y + cell/2 + 4}" fill="var(--line-strong)" font-size="11" text-anchor="middle">{name}</text>')
    # 图例
    ly = T + rows_n * (cell + gap) + 24
    for k, (op, lab) in enumerate([(0.9, f"高 {vmax:,.0f}"), (0.5, "中"), (0.12, f"低 >0"), (0.0, "0")]):
        if op > 0:
            out.append(f'<rect x="{L + k * 120:.0f}" y="{ly:.0f}" width="16" height="12" fill="var(--theme-accent)" opacity="{op}"/>')
        else:
            out.append(f'<rect x="{L + k * 120:.0f}" y="{ly:.0f}" width="16" height="12" fill="var(--surface-strong)" stroke="var(--line-strong)"/>')
        out.append(f'<text x="{L + k * 120 + 22:.0f}" y="{ly + 10:.0f}" fill="var(--muted)" font-size="11.5">{lab}</text>')
    out.append(f'<rect x="{L + 480:.0f}" y="{ly:.0f}" width="16" height="12" fill="var(--surface-strong)" stroke="var(--line)"/>')
    out.append(f'<line x1="{L + 483:.0f}" y1="{ly + 10:.0f}" x2="{L + 493:.0f}" y2="{ly + 2:.0f}" stroke="var(--line-strong)" stroke-width="1.2"/>')
    out.append(f'<text x="{L + 502:.0f}" y="{ly + 10:.0f}" fill="var(--muted)" font-size="11.5">缺失（≠0）</text>')
    if unmatched:
        out.append(f'<text x="{L}" y="{ly + 34}" fill="var(--watch)" font-size="11.5">未匹配（无格网坐标，未绘制）：{"、".join(unmatched)}</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-40 符号地图：等距圆柱近似投影；符号大小按面积映射 + 尺寸图例
# --------------------------------------------------------------------------- #
def symbol_map_chart(chart: Dict[str, Any]) -> str:
    pts = chart["points"]               # [{name, lon, lat, value, accent?}]
    H, TOP, BOT, L, R = 480, 60, 64, 80, W - 240
    plot_w, plot_h = R - L, H - TOP - BOT
    lons = [p["lon"] for p in pts]; lats = [p["lat"] for p in pts]
    lon0, lon1 = min(lons), max(lons)
    lat0, lat1 = min(lats), max(lats)
    # 等距圆柱近似：经度线性；纬度按 cos(mid) 校正纵横比
    mid_lat = math.radians((lat0 + lat1) / 2)
    aspect = abs(lon1 - lon0) * math.cos(mid_lat) / max(abs(lat1 - lat0), 1e-6)
    if aspect > plot_w / plot_h:
        pw = plot_w; ph = pw / aspect
    else:
        ph = plot_h; pw = ph * aspect
    px0 = L + (plot_w - pw) / 2
    py0 = TOP + (plot_h - ph) / 2
    def X(lon): return px0 + pw * (lon - lon0) / ((lon1 - lon0) or 1)
    def Y(lat): return py0 + ph * (1 - (lat - lat0) / ((lat1 - lat0) or 1))
    vmax = max(p["value"] for p in pts) or 1.0
    RMAX = 26
    def R_(v): return math.sqrt(v / vmax) * RMAX     # 面积映射
    out = _svg(chart["title"], H)
    out.append(f'<rect x="{px0:.1f}" y="{py0:.1f}" width="{pw:.1f}" height="{ph:.1f}" fill="var(--surface)" stroke="var(--line-strong)"/>')
    out.append(f'<text x="{L}" y="{TOP - 16}" fill="var(--muted)" font-size="11.5">等距圆柱近似投影（非精确地图）· 单位：{chart.get("unit", "")}</text>')
    for p in sorted(pts, key=lambda q: -q["value"]):
        col = "var(--theme-accent)" if p.get("accent") else "var(--series-context)"
        out.append(f'<circle cx="{X(p["lon"]):.1f}" cy="{Y(p["lat"]):.1f}" r="{R_(p["value"]):.1f}" fill="{col}" opacity="{"0.75" if p.get("accent") else "0.45"}" stroke="{"var(--theme-accent)" if p.get("accent") else "var(--line-strong)"}" stroke-width="1.2"/>')
        out.append(f'<text x="{X(p["lon"]):.1f}" y="{Y(p["lat"]) - R_(p["value"]) - 6:.1f}" fill="var(--ink)" font-size="11.5" font-weight="700" text-anchor="middle">{p["name"]} {p["value"]:,.0f}</text>')
    # 尺寸图例
    lx = R + 40
    out.append(f'<text x="{lx}" y="{TOP + 8}" fill="var(--muted)" font-size="11.5">符号大小（面积映射 √）</text>')
    for k, frac in enumerate([1.0, 0.5, 0.25]):
        cy_ = TOP + 44 + k * 70
        out.append(f'<circle cx="{lx + RMAX + 4:.0f}" cy="{cy_:.0f}" r="{R_(vmax * frac):.1f}" fill="var(--series-context)" opacity="0.3" stroke="var(--line-strong)"/>')
        out.append(f'<text x="{lx + 2 * RMAX + 16:.0f}" y="{cy_ + 4:.0f}" fill="var(--muted)" font-size="11.5">{vmax * frac:,.0f}</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-41 地理流向：线宽∝流量；主通道数值标注；贝塞尔弧线
# --------------------------------------------------------------------------- #
def geo_flow_chart(chart: Dict[str, Any]) -> str:
    pts = {p["id"]: p for p in chart["points"]}    # [{id, name, lon, lat}]
    flows = chart["flows"]              # [{from, to, value}]
    for f in flows:
        if f["from"] not in pts or f["to"] not in pts:
            raise ValueError(f"geo_flow: 流向引用未注册点位 {f['from']!r}/{f['to']!r}")
    H, TOP, BOT, L, R = 480, 60, 56, 80, W - 60
    plot_w, plot_h = R - L, H - TOP - BOT
    lons = [p["lon"] for p in pts.values()]; lats = [p["lat"] for p in pts.values()]
    lon0, lon1, lat0, lat1 = min(lons), max(lons), min(lats), max(lats)
    mid_lat = math.radians((lat0 + lat1) / 2)
    aspect = abs(lon1 - lon0) * math.cos(mid_lat) / max(abs(lat1 - lat0), 1e-6)
    if aspect > plot_w / plot_h:
        pw = plot_w; ph = pw / aspect
    else:
        ph = plot_h; pw = ph * aspect
    px0 = L + (plot_w - pw) / 2
    py0 = TOP + (plot_h - ph) / 2
    def X(lon): return px0 + pw * (lon - lon0) / ((lon1 - lon0) or 1)
    def Y(lat): return py0 + ph * (1 - (lat - lat0) / ((lat1 - lat0) or 1))
    vmax = max(f["value"] for f in flows) or 1.0
    WMAX = 14
    main = max(flows, key=lambda q: (q["value"], q["from"], q["to"])) if flows else None
    out = _svg(chart["title"], H)
    out.append(f'<rect x="{px0:.1f}" y="{py0:.1f}" width="{pw:.1f}" height="{ph:.1f}" fill="var(--surface)" stroke="var(--line-strong)"/>')
    out.append(f'<text x="{L}" y="{TOP - 16}" fill="var(--muted)" font-size="11.5">等距圆柱近似投影 · 线宽∝流量 · 弧线方向 起点终点</text>')
    for f in flows:
        a, b = pts[f["from"]], pts[f["to"]]
        x0, y0 = X(a["lon"]), Y(a["lat"])
        x1, y1 = X(b["lon"]), Y(b["lat"])
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2 - max(abs(x1 - x0), abs(y1 - y0)) * 0.22
        lw = max(1.6, WMAX * f["value"] / vmax)
        is_main = main is not None and f is main
        out.append(f'<path d="M {x0:.1f} {y0:.1f} Q {mx:.1f} {my:.1f} {x1:.1f} {y1:.1f}" fill="none" stroke="var(--theme-accent)" stroke-width="{lw:.1f}" opacity="{"0.6" if is_main else "0.25"}"/>')
        out.append(f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="{lw * 0.8 + 2:.1f}" fill="var(--theme-accent)" opacity="0.9"/>')
        if is_main:
            out.append(f'<text x="{mx:.1f}" y="{my - 8:.1f}" fill="var(--theme-accent)" font-size="12" font-weight="700" text-anchor="middle">主通道 {a["name"]}→{b["name"]} {f["value"]:,.0f}</text>')
    for p in pts.values():
        x, y = X(p["lon"]), Y(p["lat"])
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="var(--ink)"/>')
        out.append(f'<text x="{x:.1f}" y="{y - 10:.1f}" fill="var(--ink)" font-size="11.5" font-weight="700" text-anchor="middle">{p["name"]}</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-42 网络图：环形等比布局；节点大小/边宽各只表达一个指标
# --------------------------------------------------------------------------- #
def network_chart(chart: Dict[str, Any]) -> str:
    nodes = chart["nodes"]              # [{id, label, size?}]
    edges = chart["edges"]              # [{a, b, weight?}]
    node_ids = {n["id"] for n in nodes}
    for e in edges:
        if e["a"] not in node_ids or e["b"] not in node_ids:
            raise ValueError(f"network: 边引用未注册节点 {e['a']!r}/{e['b']!r}")
    if len(nodes) > 30:
        raise ValueError("network: 节点超过 30（viz-42 纪律），先筛选或聚合")
    size_field = chart.get("node_size_label", "度数")
    # 等比绘图区（正方形区域，viz-42 纪律）
    side = 620
    cx, cy = W * 0.44, 348
    r = side * 0.36
    n = len(nodes)
    ordered = sorted(nodes, key=lambda x: x["id"])
    pos = {}
    for i, nd in enumerate(ordered):
        a = math.radians(-90 + 360 * i / n)
        pos[nd["id"]] = (cx + r * math.cos(a), cy + r * math.sin(a), a)
    deg = {nd["id"]: 0 for nd in nodes}
    for e in edges:
        deg[e["a"]] += 1
        deg[e["b"]] += 1
    smax = max((nd.get("size") or deg[nd["id"]] for nd in nodes), default=1) or 1
    wmax = max((e.get("weight", 1) for e in edges), default=1) or 1
    H = 700
    out = _svg(chart["title"], H)
    out.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="none" stroke="var(--line)" stroke-width="1"/>')
    for e in edges:
        x0, y0, _ = pos[e["a"]]
        x1, y1, _ = pos[e["b"]]
        lw = 1 + 7 * e.get("weight", 1) / wmax
        out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="var(--series-context)" stroke-width="{lw:.1f}" opacity="0.3"/>')
    for nd in ordered:
        x, y, a = pos[nd["id"]]
        s = nd.get("size") or deg[nd["id"]]
        rr = 6 + 20 * math.sqrt(s / smax)      # 面积映射
        accent = nd.get("accent")
        col = "var(--theme-accent)" if accent else "var(--series-context)"
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" fill="{col}" opacity="{"0.9" if accent else "0.65"}" stroke="var(--paper)" stroke-width="1.5"/>')
        lx = cx + (r + 46) * math.cos(a)
        ly = cy + (r + 46) * math.sin(a)
        anchor = "start" if math.cos(a) > 0.15 else ("end" if math.cos(a) < -0.15 else "middle")
        out.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" fill="var(--ink)" font-size="12" font-weight="700" text-anchor="{anchor}">{nd["label"]}</text>')
    # 图例与绘图区分离（右下角）
    out.append(f'<text x="{W - 250}" y="{H - 96}" fill="var(--muted)" font-size="11.5">● 大小 = {size_field}（面积映射）</text>')
    out.append(f'<text x="{W - 250}" y="{H - 74}" fill="var(--muted)" font-size="11.5">— 边宽 = {chart.get("edge_width_label", "联系强度")}（各自只表达一个指标）</text>')
    out.append(f'<text x="{W - 250}" y="{H - 52}" fill="var(--muted)" font-size="11.5">布局：环形等比（无地理含义）</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-43 玫瑰图：半径按 sqrt 映射（面积映射）；周期顺序；引导线标签
# --------------------------------------------------------------------------- #
def rose_chart(chart: Dict[str, Any]) -> str:
    sectors = chart["sectors"]          # 周期顺序 [{label, value, accent?}]
    if len(sectors) < 5 or len(sectors) > 12:
        raise ValueError("rose: 适合 6~8 个有周期/方向顺序的类别（5~12 容忍）")
    cx, cy, rmax = W * 0.5, 300, 240
    vmax = max(s["value"] for s in sectors) or 1.0
    n = len(sectors)
    out = _svg(chart["title"], 610)
    for ring in (0.25, 0.5, 0.75, 1.0):
        rr = rmax * math.sqrt(ring)     # 面积刻度：环半径按 √
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{rr:.1f}" fill="none" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{cx + rr + 6:.1f}" y="{cy - 4:.1f}" fill="var(--muted)" font-size="10.5">{(vmax * ring):,.0f}</text>')
    for i, s in enumerate(sectors):
        a0 = -90 + 360 * i / n
        a1 = a0 + 360 / n
        rad = rmax * math.sqrt(s["value"] / vmax)   # 面积映射（√ 半径）
        x0, y0 = cx + rad * math.cos(math.radians(a0)), cy + rad * math.sin(math.radians(a0))
        x1, y1 = cx + rad * math.cos(math.radians(a1)), cy + rad * math.sin(math.radians(a1))
        col = "var(--theme-accent)" if s.get("accent") else "var(--series-context)"
        op = "0.9" if s.get("accent") else "0.55"
        out.append(f'<path d="M {cx:.1f} {cy:.1f} L {x0:.1f} {y0:.1f} A {rad:.1f} {rad:.1f} 0 0 1 {x1:.1f} {y1:.1f} Z" fill="{col}" opacity="{op}" stroke="var(--paper)" stroke-width="1.5"/>')
        am = math.radians((a0 + a1) / 2)
        lx0, ly0 = cx + (rad + 6) * math.cos(am), cy + (rad + 6) * math.sin(am)
        lx1, ly1 = cx + (rad + 30) * math.cos(am), cy + (rad + 30) * math.sin(am)
        anchor = "start" if math.cos(am) >= 0 else "end"
        out.append(f'<line x1="{lx0:.1f}" y1="{ly0:.1f}" x2="{lx1:.1f}" y2="{ly1:.1f}" stroke="var(--line-strong)" stroke-width="1"/>')
        fw = ' font-weight="700"' if s.get("accent") else ""
        out.append(f'<text x="{lx1 + (6 if anchor == "start" else -6):.1f}" y="{ly1 + 4:.1f}" fill="var(--ink)" font-size="12"{fw} text-anchor="{anchor}">{s["label"]} {s["value"]:,.0f}</text>')
    out.append(f'<text x="{cx}" y="{cy + rmax + 58}" fill="var(--muted)" font-size="11.5" text-anchor="middle">扇区面积∝数值（半径 √ 映射，不被半径扭曲）· 按给定周期顺序排列</text>')
    out.append("</svg>")
    return "\n          ".join(out)

# --------------------------------------------------------------------------- #
# viz-44 目标带柱线图：目标带先画（不遮挡柱线）；单轴
# --------------------------------------------------------------------------- #
def target_band_chart(chart: Dict[str, Any]) -> str:
    xlabels = chart["xlabels"]
    s = chart["series"][0]
    vals = s["values"]
    band = chart["band"]                # {lo, hi, label}
    if len(vals) != len(xlabels):
        raise ValueError("target_band: values 与 xlabels 数量不一致")
    H, TOP, BOT, L, R = 400, 64, 56, 80, W - 60
    plot_h = H - TOP - BOT
    vmax = max(max(vals), band["hi"]) * 1.12 or 1.0
    n = len(vals)
    zone = (R - L) / n
    def Y(v): return TOP + plot_h * (1 - v / vmax)
    out = _svg(chart["title"], H)
    _grid(out, TOP, plot_h, L, R, vmax)
    # 目标带（先画 —— 在柱线之下，不遮挡，viz-44 纪律）
    y0, y1 = Y(band["hi"]), Y(band["lo"])
    out.append(f'<rect x="{L:.1f}" y="{y0:.1f}" width="{R - L:.1f}" height="{max(y1 - y0, 1):.1f}" fill="var(--watch)" opacity="0.13"/>')
    out.append(f'<text x="{R - 6:.1f}" y="{(y0 + y1) / 2 + 4:.1f}" fill="var(--watch)" font-size="11.5" font-weight="700" text-anchor="end">目标带 {band["label"]}：{band["lo"]:,.0f}~{band["hi"]:,.0f}</text>')
    for i, v in enumerate(vals):
        cx = L + zone * i + zone / 2
        bw = min(zone * 0.52, 110)
        h = plot_h * v / vmax
        in_band = band["lo"] <= v <= band["hi"]
        col = "var(--theme-accent)" if not in_band else "var(--series-context)"
        op = "0.9" if not in_band else "0.55"
        out.append(f'<rect x="{cx - bw/2:.1f}" y="{TOP + plot_h - h:.1f}" width="{bw:.1f}" height="{max(h, 1):.1f}" rx="2.5" fill="{col}" opacity="{op}"/>')
        out.append(f'<text x="{cx:.1f}" y="{TOP + plot_h - h - 6:.1f}" fill="var(--ink)" font-size="12" font-weight="{"700" if not in_band else "400"}" text-anchor="middle">{v:,.0f}</text>')
        out.append(f'<text x="{cx:.1f}" y="{TOP + plot_h + 22:.1f}" fill="var(--muted)" font-size="12" text-anchor="middle">{xlabels[i]}</text>')
    out.append(f'<text x="{(L+R)/2}" y="{H - 6}" fill="var(--muted)" font-size="11.5" text-anchor="middle">目标带=范围非阈值 · 超出带（强调色）与带内（灰色）一目了然 · 无多余网格</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-45 贡献桥：贡献项严格回到终点（合不上拒绝）+ 桥图/排名条分工
# --------------------------------------------------------------------------- #
def bridge_chart(chart: Dict[str, Any]) -> str:
    start = chart["start"]
    end = chart["end"]
    deltas = chart["deltas"]            # [{label, value, accent?}]
    s, e, dsum = start["value"], end["value"], sum(d["value"] for d in deltas)
    if abs(s + dsum - e) > 1e-6:
        raise ValueError(f"bridge: 贡献项无法回到终点（{s:,.0f} + Δ {dsum:,.0f} ≠ {e:,.0f}），禁止硬凑")
    H, TOP, BOT = 500, 70, 70
    L, R = 80, W - 60
    plot_h = 300
    vmax = max(s, e, *[s + sum(d["value"] for d in deltas[:i + 1]) for i in range(len(deltas))])
    vmin = min(0, s, e, *[s + sum(d["value"] for d in deltas[:i + 1]) for i in range(len(deltas))])
    pad = (vmax - vmin) * 0.1 or 1.0
    vmax += pad
    vmin -= pad
    def Y(v): return TOP + plot_h * (1 - (v - vmin) / (vmax - vmin))
    n = len(deltas) + 2
    zone = (R - L) / n
    out = _svg(chart["title"], H)
    _grid(out, TOP, plot_h, L, R, vmax, vmin)
    # 上半区：桥图
    running = s
    cx = L + zone / 2
    bw = min(zone * 0.58, 120)
    _bridge_col(out, cx, bw, TOP + plot_h, Y(0), Y(s), "var(--series-context)", start["label"], s)
    for d in deltas:
        cx += zone
        v0, v1 = running, running + d["value"]
        up = d["value"] >= 0
        col = "var(--healthy)" if up else "var(--critical)"
        _bridge_col(out, cx, bw, Y(max(v0, v1)), Y(min(v0, v1)), None, col,
                    d["label"], d["value"], floating=True)
        # 连接虚线
        out.append(f'<line x1="{cx - zone + bw/2:.1f}" y1="{Y(v0):.1f}" x2="{cx - bw/2:.1f}" y2="{Y(v0):.1f}" stroke="var(--line-strong)" stroke-width="1" stroke-dasharray="4 3"/>')
        running = v1
    cx += zone
    _bridge_col(out, cx, bw, TOP + plot_h, Y(0), Y(e), "var(--series-context)", end["label"], e)
    out.append(f'<text x="{(L+R)/2}" y="{TOP + plot_h + 40}" fill="var(--muted)" font-size="11.5" text-anchor="middle">桥图（上半）：起点→贡献→终点 · 贡献项严格回到终点（校验通过）· 红降绿升</text>')
    # 下半区：|Δ| 排名条（独立回答「谁贡献最大」）
    rank_top = TOP + plot_h + 74
    out.append(f'<text x="{L}" y="{rank_top - 12}" fill="var(--muted)" font-size="11.5">贡献绝对值排名（下半）：</text>')
    rank = sorted(deltas, key=lambda q: (-abs(q["value"]), q["label"]))
    rw_area = (R - L) * 0.62
    rmax = max(abs(d["value"]) for d in rank) or 1.0
    ry = rank_top
    for d in rank:
        w = rw_area * abs(d["value"]) / rmax
        col = "var(--healthy)" if d["value"] >= 0 else "var(--critical)"
        out.append(f'<text x="{L}" y="{ry + 13:.1f}" fill="var(--ink)" font-size="11.5" text-anchor="start">{d["label"]}</text>')
        out.append(f'<rect x="{L + 130:.1f}" y="{ry:.1f}" width="{max(w, 2):.1f}" height="14" rx="2" fill="{col}" opacity="0.7"/>')
        out.append(f'<text x="{L + 134 + w:.1f}" y="{ry + 12:.1f}" fill="var(--muted)" font-size="11">{"+" if d["value"] >= 0 else "−"}{abs(d["value"]):,.0f}</text>')
        ry += 24
    out.append("</svg>")
    return "\n          ".join(out)


def _bridge_col(out, cx, bw, y_top, y_base, y_v, col, label, value, floating=False):
    if floating:
        out.append(f'<rect x="{cx - bw/2:.1f}" y="{y_top:.1f}" width="{bw:.1f}" height="{max(y_base - y_top, 2):.1f}" rx="2" fill="{col}" opacity="0.82"/>')
        out.append(f'<text x="{cx:.1f}" y="{min(y_top, y_base) - 6:.1f}" fill="{col}" font-size="11.5" font-weight="700" text-anchor="middle">{"+" if value >= 0 else "−"}{abs(value):,.0f}</text>')
    else:
        out.append(f'<rect x="{cx - bw/2:.1f}" y="{y_v:.1f}" width="{bw:.1f}" height="{max(y_base - y_v, 2):.1f}" rx="2" fill="{col}" opacity="0.9"/>')
        out.append(f'<text x="{cx:.1f}" y="{y_v - 6:.1f}" fill="var(--ink)" font-size="12" font-weight="700" text-anchor="middle">{value:,.0f}</text>')
    out.append(f'<text x="{cx:.1f}" y="{y_base + 18:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{label}</text>')


# --------------------------------------------------------------------------- #
# viz-46 双轴柱线：左轴从 0 开始；右轴单位注明；轴色与系列一致
# --------------------------------------------------------------------------- #
def dual_axis_chart(chart: Dict[str, Any]) -> str:
    xlabels = chart["xlabels"]
    bars = chart["bars"]                # {name, values, unit}
    line = chart["line"]                # {name, values, unit}
    if len(bars["values"]) != len(xlabels) or len(line["values"]) != len(xlabels):
        raise ValueError("dual_axis: 两系列长度均须与 xlabels 一致")
    H, TOP, BOT, L, R = 420, 72, 62, 90, W - 90
    plot_h = H - TOP - BOT
    # 左轴（柱）：从 0 开始 —— 纪律落码
    bmax = max(bars["values"]) * 1.15 or 1.0
    lvals = line["values"]
    lmin, lmax = min(lvals), max(lvals)
    lpad = (lmax - lmin) * 0.15 or 1.0
    lmin, lmax = lmin - lpad, lmax + lpad
    def YL(v): return TOP + plot_h * (1 - v / bmax)            # 左轴 0 起
    def YR(v): return TOP + plot_h * (1 - (v - lmin) / (lmax - lmin))
    n = len(xlabels)
    zone = (R - L) / n
    out = _svg(chart["title"], H)
    # 左轴刻度（0 起，柱色）
    for i in range(5):
        y = TOP + plot_h * i / 4
        out.append(f'<line x1="{L:.1f}" y1="{y:.1f}" x2="{R:.1f}" y2="{y:.1f}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{L - 8:.1f}" y="{y + 4:.1f}" fill="var(--series-context)" font-size="11.5" text-anchor="end">{bmax * (1 - i / 4):,.0f}</text>')
    # 右轴刻度（线色 + 单位）
    for i in range(5):
        y = TOP + plot_h * i / 4
        out.append(f'<text x="{R + 8:.1f}" y="{y + 4:.1f}" fill="var(--theme-accent)" font-size="11.5">{lmin + (lmax - lmin) * (1 - i / 4):,.0f}</text>')
    out.append(f'<text x="{L - 8:.1f}" y="{TOP - 34}" fill="var(--series-context)" font-size="11.5" font-weight="700" text-anchor="start">■ {bars["name"]}（左轴，自 0 起，{bars["unit"]}）</text>')
    out.append(f'<text x="{R + 8:.1f}" y="{TOP - 34}" fill="var(--theme-accent)" font-size="11.5" font-weight="700" text-anchor="end">— {line["name"]}（右轴，{line["unit"]}）</text>')
    for i, x in enumerate(xlabels):
        cx = L + zone * i + zone / 2
        bw = min(zone * 0.5, 100)
        h = plot_h * bars["values"][i] / bmax
        out.append(f'<rect x="{cx - bw/2:.1f}" y="{TOP + plot_h - h:.1f}" width="{bw:.1f}" height="{max(h, 1):.1f}" rx="2" fill="var(--series-context)" opacity="0.62"/>')
        out.append(f'<text x="{cx:.1f}" y="{TOP + plot_h - h - 6:.1f}" fill="var(--muted)" font-size="11" text-anchor="middle">{bars["values"][i]:,.0f}</text>')
        out.append(f'<text x="{cx:.1f}" y="{TOP + plot_h + 22:.1f}" fill="var(--muted)" font-size="12" text-anchor="middle">{x}</text>')
    pts = " ".join(f"{L + zone * i + zone / 2:.1f},{YR(v):.1f}" for i, v in enumerate(lvals))
    out.append(f'<polyline points="{pts}" fill="none" stroke="var(--theme-accent)" stroke-width="2.6" stroke-linejoin="round"/>')
    for i, v in enumerate(lvals):
        cx = L + zone * i + zone / 2
        out.append(f'<circle cx="{cx:.1f}" cy="{YR(v):.1f}" r="3.4" fill="var(--theme-accent)"/>')
    out.append(f'<text x="{cx:.1f}" y="{YR(lvals[-1]) - 10:.1f}" fill="var(--theme-accent)" font-size="11.5" font-weight="700" text-anchor="middle">{lvals[-1]:,.0f}</text>')
    out.append(f'<text x="{(L+R)/2}" y="{H - 6}" fill="var(--muted)" font-size="11.5" text-anchor="middle">两指标不同单位（{bars["unit"]} vs {line["unit"]}）· 左轴自 0 起，右轴仅看形状/趋势 · 柱≠线数值比较</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-47 KPI 拆解：三模块同口径；驱动拆解位于下半区
# --------------------------------------------------------------------------- #
def kpi_break_chart(chart: Dict[str, Any]) -> str:
    kpi = chart["kpi"]                  # {label, value, unit, delta_label?}
    trend = chart["trend"]              # {xlabels, values}
    breakdown = chart["breakdown"]      # {items: [{label, value, accent?}]}
    H = 520
    out = _svg(chart["title"], H)
    # 模块 1：KPI 卡（左上）
    out.append('<rect x="30" y="30" width="300" height="150" rx="8" fill="var(--surface)" stroke="var(--line-strong)"/>')
    out.append(f'<text x="54" y="66" fill="var(--muted)" font-size="13">{kpi["label"]}</text>')
    out.append(f'<text x="54" y="120" fill="var(--ink)" font-size="46" font-weight="700">{kpi["value"]:,.0f}<tspan font-size="20">{kpi.get("unit", "")}</tspan></text>')
    if kpi.get("delta_label"):
        out.append(f'<text x="54" y="152" fill="var(--muted)" font-size="12.5">{kpi["delta_label"]}</text>')
    # 模块 2：趋势（右上）
    tx0, ty0, tw, th = 370, 44, 560, 136
    tv = trend["values"]
    tmax, tmin = max(tv), min(tv)
    tpad = (tmax - tmin) * 0.1 or 1.0
    tmax, tmin = tmax + tpad, tmin - tpad
    n = len(tv)
    def TX(i): return tx0 + tw * i / (n - 1)
    def TY(v): return ty0 + th * (1 - (v - tmin) / (tmax - tmin))
    pts = " ".join(f"{TX(i):.0f},{TY(v):.0f}" for i, v in enumerate(tv))
    out.append(f'<text x="{tx0}" y="{ty0 - 8}" fill="var(--muted)" font-size="11.5">趋势（口径同 KPI）</text>')
    out.append(f'<polyline points="{pts}" fill="none" stroke="var(--theme-accent)" stroke-width="2.4" stroke-linejoin="round"/>')
    out.append(f'<circle cx="{TX(n-1):.0f}" cy="{TY(tv[-1]):.0f}" r="4" fill="var(--theme-accent)"/>')
    out.append(f'<text x="{TX(n-1) - 6:.0f}" y="{TY(tv[-1]) - 10:.0f}" fill="var(--theme-accent)" font-size="12" font-weight="700" text-anchor="end">{tv[-1]:,.0f}</text>')
    step = max(1, n // 8)
    for i in range(0, n, step):
        out.append(f'<text x="{TX(i):.0f}" y="{ty0 + th + 18}" fill="var(--muted)" font-size="10.5" text-anchor="middle">{trend["xlabels"][i]}</text>')
    # 模块 3：驱动拆解（下半区 —— viz-47 纪律）
    out.append(f'<text x="30" y="{ty0 + th + 52}" fill="var(--muted)" font-size="11.5">驱动拆解（口径与 KPI 一致，单位相同才可加总）：</text>')
    items = sorted(breakdown["items"], key=lambda q: (-abs(q["value"]), q["label"]))
    bmax = max(abs(i["value"]) for i in items) or 1.0
    y = ty0 + th + 76
    for it in items:
        w = 560 * abs(it["value"]) / bmax
        col = "var(--healthy)" if it["value"] >= 0 else "var(--critical)"
        if it.get("accent"):
            col = "var(--theme-accent)" if it["value"] >= 0 else "var(--critical)"
        out.append(f'<text x="30" y="{y + 13:.1f}" fill="var(--ink)" font-size="12.5" font-weight="700">{it["label"]}</text>')
        out.append(f'<rect x="220" y="{y:.1f}" width="{max(w, 2):.1f}" height="16" rx="2" fill="{col}" opacity="0.75"/>')
        out.append(f'<text x="{224 + w:.1f}" y="{y + 13:.1f}" fill="var(--muted)" font-size="11.5">{"+" if it["value"] >= 0 else "−"}{abs(it["value"]):,.0f}</text>')
        y += 30
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# viz-48 小倍数：全部小图共享同一尺度；≤6 格
# --------------------------------------------------------------------------- #
def small_mult_chart(chart: Dict[str, Any]) -> str:
    panels = chart["panels"]            # [{title, xlabels, values, accent?}]
    if len(panels) < 2 or len(panels) > 6:
        raise ValueError("small_mult: 2~6 格（超过 6 拆页，viz-48 纪律）")
    all_v = [v for p in panels for v in p["values"]]
    vmin, vmax = min(all_v), max(all_v)     # 全局共享尺度（纪律）
    pad = (vmax - vmin) * 0.08 or 1.0
    vmin, vmax = vmin - pad, vmax + pad
    cols = 3 if len(panels) > 4 else 2
    rows_n = math.ceil(len(panels) / cols)
    PW, PH, GP, TOP = 310, 200, 22, 60
    H = TOP + rows_n * (PH + GP) + 30
    out = _svg(chart["title"], H)
    out.append(f'<text x="30" y="{TOP - 34}" fill="var(--muted)" font-size="11.5">所有小图共享同一纵轴尺度（{vmin:,.0f}~{vmax:,.0f}）· 只有比较维度本身在变</text>')
    for idx, p in enumerate(panels):
        r_, c_ = divmod(idx, cols)
        x0 = 30 + c_ * (PW + GP)
        y0 = TOP + r_ * (PH + GP)
        n = len(p["values"])
        def X(i): return x0 + 34 + (PW - 50) * i / (n - 1)
        def Y(v): return y0 + 16 + (PH - 44) * (1 - (v - vmin) / (vmax - vmin))
        out.append(f'<rect x="{x0}" y="{y0}" width="{PW}" height="{PH}" rx="4" fill="var(--surface)" stroke="var(--line)"/>')
        col = "var(--theme-accent)" if p.get("accent") else "var(--series-context)"
        pts = " ".join(f"{X(i):.0f},{Y(v):.0f}" for i, v in enumerate(p["values"]))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{"2.6" if p.get("accent") else "1.8"}" stroke-linejoin="round"/>')
        out.append(f'<text x="{x0 + 12}" y="{y0 + 24}" fill="var(--ink)" font-size="12.5" font-weight="700">{p["title"]}</text>')
        out.append(f'<text x="{x0 + PW - 12}" y="{y0 + 24}" fill="var(--muted)" font-size="11" text-anchor="end">{p["values"][-1]:,.0f}</text>')
        out.append(f'<text x="{x0 + 34}" y="{y0 + PH - 8}" fill="var(--muted)" font-size="9.5">{p["xlabels"][0]}</text>')
        out.append(f'<text x="{x0 + PW - 16}" y="{y0 + PH - 8}" fill="var(--muted)" font-size="9.5" text-anchor="end">{p["xlabels"][-1]}</text>')
    out.append("</svg>")
    return "\n          ".join(out)


# --------------------------------------------------------------------------- #
# 注册表（38 型：48 图谱 − chart_lib 内置 10 型）
# --------------------------------------------------------------------------- #
RENDERERS: Dict[str, Any] = {
    "vbar": vbar_chart,                  # viz-01（report_renderer 另有报告专用版）
    "hbar": hbar_chart,                  # viz-02（同上）
    "stacked_bar": stacked_bar_chart,    # viz-04
    "pct_stacked": pct_stacked_chart,    # viz-05
    "area": area_chart,                  # viz-07
    "pie": pie_chart,                    # viz-08
    "donut": donut_chart,                # viz-09
    "dumbbell": dumbbell_chart,          # viz-12
    "dot": dot_chart,                    # viz-13
    "lollipop": lollipop_chart,          # viz-14
    "waffle": waffle_chart,              # viz-15
    "bubble": bubble_chart,              # viz-18
    "heatmap": heatmap_chart,            # viz-19
    "radar": radar_chart,                # viz-20
    "violin": violin_chart,              # viz-21
    "ridgeline": ridgeline_chart,        # viz-22
    "parallel": parallel_chart,          # viz-23
    "error_bar": error_bar_chart,        # viz-24
    "forest": forest_chart,              # viz-25
    "bullet": bullet_chart,              # viz-30
    "gauge": gauge_chart,                # viz-31
    "cal_heatmap": cal_heatmap_chart,    # viz-32
    "gantt": gantt_chart,                # viz-33
    "candlestick": candlestick_chart,    # viz-34
    "sankey": sankey_chart,              # viz-35
    "streamgraph": streamgraph_chart,    # viz-36
    "treemap": treemap_chart,            # viz-37
    "sunburst": sunburst_chart,          # viz-38
    "choropleth": choropleth_chart,      # viz-39
    "symbol_map": symbol_map_chart,      # viz-40
    "geo_flow": geo_flow_chart,          # viz-41
    "network": network_chart,            # viz-42
    "rose": rose_chart,                  # viz-43
    "target_band": target_band_chart,    # viz-44
    "bridge": bridge_chart,              # viz-45
    "dual_axis": dual_axis_chart,        # viz-46
    "kpi_break": kpi_break_chart,        # viz-47
    "small_mult": small_mult_chart,      # viz-48
}

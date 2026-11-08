# -*- coding: utf-8 -*-
"""图表规格库：把 48 个可视化提示词（ai-data-visualization-prompts）接成
「提示词分类法 → 图表选型建议 → 确定性 SVG」管线。

- CHART_INDEX：48 图谱注册（id/名称/分组/适用场景），对齐 prompts/index.json
- recommend()：按数据形态 + 分析意图推荐候选图表（确定性规则）
- 渲染器：按各提示词的确定性规则生成内嵌 SVG
    line_chart   (viz-06 折线)   真实时序/缺失不补零/只标峰谷拐点终点/事件窗口/参考线不抢眼
    waterfall    (viz-27 瀑布)    贡献桥接：期初→各项贡献→期末，红降绿升
    slope_chart  (viz-11 斜率)    两期对比：每类一条线，终点直接标注，重点系列唯一强调色
    box_compare  (viz-16 箱线)    分布对比：min/Q1/中位/Q3/max，由原始值确定性计算

用法：
    python chart_lib.py list                     # 48 图谱清单
    python chart_lib.py recommend --shape time_series --intent trend
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------- #
# 48 图谱注册（对齐 ai-data-visualization-prompts/prompts/index.json）
# --------------------------------------------------------------------------- #
CHART_INDEX: List[Dict[str, str]] = [
    {"id": "viz-01", "key": "vbar",          "title": "纵向柱状图",       "group": "基础比较、趋势与构成", "use_when": "少量类别的数值比较"},
    {"id": "viz-02", "key": "hbar",          "title": "排名横条图",       "group": "基础比较、趋势与构成", "use_when": "类别排名，标签长"},
    {"id": "viz-03", "key": "grouped_bar",  "title": "分组柱状图",       "group": "基础比较、趋势与构成", "use_when": "两组以上类别的跨期对比"},
    {"id": "viz-04", "key": "stacked_bar",  "title": "堆叠柱状图",       "group": "基础比较、趋势与构成", "use_when": "总量+构成同时展示"},
    {"id": "viz-05", "key": "pct_stacked",  "title": "百分比堆叠条形图", "group": "基础比较、趋势与构成", "use_when": "只关心占比结构"},
    {"id": "viz-06", "key": "line",         "title": "折线图",           "group": "基础比较、趋势与构成", "use_when": "连续时间趋势与拐点，≤3系列同单位"},
    {"id": "viz-07", "key": "area",         "title": "面积图",           "group": "基础比较、趋势与构成", "use_when": "强调量级变化"},
    {"id": "viz-08", "key": "pie",          "title": "饼图",             "group": "基础比较、趋势与构成", "use_when": "≤5 类占比"},
    {"id": "viz-09", "key": "donut",        "title": "环形图",           "group": "基础比较、趋势与构成", "use_when": "占比+中心指标"},
    {"id": "viz-10", "key": "histogram",    "title": "直方图",           "group": "基础比较、趋势与构成", "use_when": "单指标分布"},
    {"id": "viz-11", "key": "slope",        "title": "斜率图",           "group": "基础比较、趋势与构成", "use_when": "两期变化对比"},
    {"id": "viz-12", "key": "dumbbell",     "title": "哑铃图",           "group": "基础比较、趋势与构成", "use_when": "两组差异范围"},
    {"id": "viz-13", "key": "dot",          "title": "点图",             "group": "基础比较、趋势与构成", "use_when": "轻量精确比较多类"},
    {"id": "viz-14", "key": "lollipop",     "title": "棒棒糖图",         "group": "基础比较、趋势与构成", "use_when": "排名展示"},
    {"id": "viz-15", "key": "waffle",       "title": "华夫图",           "group": "基础比较、趋势与构成", "use_when": "占比的离散方块表达"},
    {"id": "viz-16", "key": "box",          "title": "箱线图",           "group": "分布与关系",           "use_when": "分布对比与离群检查"},
    {"id": "viz-17", "key": "scatter",      "title": "散点图",           "group": "分布与关系",           "use_when": "两连续变量关系"},
    {"id": "viz-18", "key": "bubble",       "title": "气泡图",           "group": "分布与关系",           "use_when": "三变量关系"},
    {"id": "viz-19", "key": "heatmap",      "title": "热力图",           "group": "分布与关系",           "use_when": "双维度密度/强度"},
    {"id": "viz-20", "key": "radar",        "title": "雷达图",           "group": "分布与关系",           "use_when": "多维能力画像"},
    {"id": "viz-21", "key": "violin",       "title": "小提琴图",         "group": "分布与关系",           "use_when": "分布形状对比"},
    {"id": "viz-22", "key": "ridgeline",    "title": "山脊图",           "group": "分布与关系",           "use_when": "多组分布纵向堆叠"},
    {"id": "viz-23", "key": "parallel",     "title": "平行坐标图",       "group": "分布与关系",           "use_when": "多维记录对比"},
    {"id": "viz-24", "key": "error_bar",    "title": "误差条图",         "group": "分布与关系",           "use_when": "不确定性表达"},
    {"id": "viz-25", "key": "forest",       "title": "森林图",           "group": "分布与关系",           "use_when": "多项研究/切片效应汇总"},
    {"id": "viz-26", "key": "control",      "title": "控制图",           "group": "分布与关系",           "use_when": "过程监控与异常判定"},
    {"id": "viz-27", "key": "waterfall",    "title": "瀑布图",           "group": "构成、流程与变化解释", "use_when": "期初→各贡献→期末的桥接解释"},
    {"id": "viz-28", "key": "pareto",       "title": "帕累托图",         "group": "构成、流程与变化解释", "use_when": "少数项解释多数缺口"},
    {"id": "viz-29", "key": "funnel",       "title": "漏斗图",           "group": "构成、流程与变化解释", "use_when": "转化流程"},
    {"id": "viz-30", "key": "bullet",       "title": "子弹图",           "group": "构成、流程与变化解释", "use_when": "指标 vs 目标 vs 区间"},
    {"id": "viz-31", "key": "gauge",        "title": "仪表盘图",         "group": "构成、流程与变化解释", "use_when": "单一指标进度"},
    {"id": "viz-32", "key": "cal_heatmap",  "title": "日历热力图",       "group": "构成、流程与变化解释", "use_when": "日粒度强度"},
    {"id": "viz-33", "key": "gantt",        "title": "甘特图",           "group": "构成、流程与变化解释", "use_when": "时间计划与占用"},
    {"id": "viz-34", "key": "candlestick",  "title": "K线图",            "group": "构成、流程与变化解释", "use_when": " OHLC 波动"},
    {"id": "viz-35", "key": "sankey",       "title": "桑基图",           "group": "构成、流程与变化解释", "use_when": "流向拆解"},
    {"id": "viz-36", "key": "streamgraph",  "title": "河流图",           "group": "构成、流程与变化解释", "use_when": "构成随时间演变"},
    {"id": "viz-37", "key": "treemap",      "title": "树状图",           "group": "构成、流程与变化解释", "use_when": "层级占比"},
    {"id": "viz-38", "key": "sunburst",     "title": "旭日图",           "group": "构成、流程与变化解释", "use_when": "多层级占比"},
    {"id": "viz-39", "key": "choropleth",  "title": "填色地图",         "group": "构成、流程与变化解释", "use_when": "地理分布"},
    {"id": "viz-40", "key": "symbol_map",  "title": "符号地图",         "group": "构成、流程与变化解释", "use_when": "地理数值"},
    {"id": "viz-41", "key": "geo_flow",    "title": "地理流向图",       "group": "构成、流程与变化解释", "use_when": "OD 流向"},
    {"id": "viz-42", "key": "network",     "title": "网络图",           "group": "构成、流程与变化解释", "use_when": "关系结构"},
    {"id": "viz-43", "key": "rose",        "title": "玫瑰图",           "group": "构成、流程与变化解释", "use_when": "周期性方向数据"},
    {"id": "viz-44", "key": "target_band", "title": "柱线目标带图",     "group": "高级专项",            "use_when": "目标区间监控"},
    {"id": "viz-45", "key": "bridge",      "title": "贡献桥接图",       "group": "高级专项",            "use_when": "变化量归因桥接"},
    {"id": "viz-46", "key": "dual_axis",   "title": "双轴柱线图",       "group": "高级专项",            "use_when": "两个不同单位指标"},
    {"id": "viz-47", "key": "kpi_break",   "title": "KPI趋势分解图",    "group": "高级专项",            "use_when": "核心指标趋势+构成分解"},
    {"id": "viz-48", "key": "small_mult",  "title": "小多组图",         "group": "高级专项",            "use_when": "同构分面对比"},
]
BY_KEY = {c["key"]: c for c in CHART_INDEX}

# --------------------------------------------------------------------------- #
# 选型建议（确定性规则：数据形态 + 意图 → 候选图表，按适配度排序）
# --------------------------------------------------------------------------- #
_RULES: List[Dict[str, Any]] = [
    {"shape": "time_series", "intent": "trend",    "charts": ["line", "area", "control"]},
    {"shape": "time_series", "intent": "anomaly",  "charts": ["line", "control", "cal_heatmap"]},
    {"shape": "time_series", "intent": "compose",  "charts": ["streamgraph", "stacked_bar", "area"]},
    {"shape": "two_period",  "intent": "compare",  "charts": ["slope", "dumbbell", "grouped_bar"]},
    {"shape": "two_period",  "intent": "explain",  "charts": ["waterfall", "bridge", "hbar"]},
    {"shape": "categories",  "intent": "rank",     "charts": ["hbar", "lollipop", "dot"]},
    {"shape": "categories",  "intent": "compose",  "charts": ["donut", "pie", "treemap", "pct_stacked"]},
    {"shape": "categories",  "intent": "explain",  "charts": ["pareto", "waterfall", "hbar"]},
    {"shape": "distribution","intent": "compare",  "charts": ["box", "violin", "ridgeline"]},
    {"shape": "distribution","intent": "explore",  "charts": ["histogram", "scatter"]},
    {"shape": "xy",          "intent": "relate",   "charts": ["scatter", "bubble", "parallel"]},
    {"shape": "funnel",      "intent": "convert",  "charts": ["funnel", "sankey"]},
]


# --------------------------------------------------------------------------- #
# 48 完整提示词注册表（references/chart_prompts_48.json，由
# build_chart_prompts.py 从 48 个 .md 确定性编译；按 viz-NN id 对接）
# --------------------------------------------------------------------------- #
_PROMPT_REG: Optional[Dict[str, Dict[str, Any]]] = None


def _prompt_by_id() -> Dict[str, Dict[str, Any]]:
    global _PROMPT_REG
    if _PROMPT_REG is None:
        import os
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "references", "chart_prompts_48.json")
        try:
            with open(path, encoding="utf-8") as f:
                _PROMPT_REG = {it["id"]: it for it in json.load(f).get("items", [])}
        except OSError:
            _PROMPT_REG = {}
    return _PROMPT_REG


def recommend(shape: str, intent: str) -> List[Dict[str, Any]]:
    """选型建议 + 附该图完整提示词元数据（use_when/prepare/checklist）。

    管线：数据形态+意图 → 候选图（确定性规则）→ 每个候选附上
    48 提示词注册表的真实「什么时候用/需要准备/怎么检查」，
    供 chart-spec 生成与渲染时直接引用。
    """
    for r in _RULES:
        if r["shape"] == shape and r["intent"] == intent:
            out: List[Dict[str, Any]] = []
            for i, k in enumerate(r["charts"]):
                base = dict(BY_KEY[k])
                p = _prompt_by_id().get(base.get("id", ""), {})
                if p:
                    base["use_when_full"] = p.get("use_when", "")
                    base["prepare"] = p.get("prepare", [])
                    base["checklist"] = p.get("checklist", [])
                out.append({"rank": i + 1, **base})
            return out
    return []


# --------------------------------------------------------------------------- #
# SVG 渲染器（坐标全部由数值确定性计算）
# --------------------------------------------------------------------------- #
def _q(vals: List[float]) -> Dict[str, float]:
    s = sorted(vals)

    def pct(p: float) -> float:
        idx = p * (len(s) - 1)
        lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
        frac = idx - lo
        return s[lo] * (1 - frac) + s[hi] * frac

    return {"min": s[0], "q1": pct(0.25), "median": pct(0.5),
            "q3": pct(0.75), "max": s[-1]}


def line_chart(chart: Dict[str, Any]) -> str:
    """viz-06：折线图。规则：真实时序、只标峰/谷/拐点/终点、事件窗口、参考线不抢眼。"""
    series = chart["series"]            # [{name, values[], accent:bool}]
    xlabels = chart["xlabels"]
    W, H = 980, 360
    TOP, BOT, L, R = 58, 46, 74, 930
    all_v = [v for s in series for v in s["values"]]
    vmax, vmin = max(all_v), min(all_v)
    pad = (vmax - vmin) * 0.18 or 1.0
    vmax, vmin = vmax + pad, vmin - pad
    plot_h = H - TOP - BOT
    n = len(xlabels)
    def X(i: int) -> float: return L + (R - L) * i / (n - 1)
    def Y(v: float) -> float: return TOP + plot_h * (1 - (v - vmin) / (vmax - vmin))
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{chart["title"]}">']
    # 弱网格线 + 刻度
    for i in range(5):
        y = TOP + plot_h * i / 4
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{R}" y2="{y:.1f}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{L - 8}" y="{y + 4:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="end">{vmax - (vmax - vmin) * i / 4:,.0f}</text>')
    # 事件窗口（可选）
    aw = chart.get("anomaly_window")
    if aw:
        x0, x1 = X(aw["from"]), X(aw["to"])
        out.append(f'<rect x="{x0:.1f}" y="{TOP - 24}" width="{x1 - x0:.1f}" height="{plot_h + 24}" fill="var(--critical-soft)"/>')
        out.append(f'<text x="{x0 + 10:.1f}" y="{TOP - 10}" fill="var(--critical)" font-size="12" font-weight="700">{aw["label"]}</text>')
    # 参考线（不抢眼）
    if chart.get("ref_line"):
        ref = chart["ref_line"]
        ry = Y(ref["value"])
        out.append(f'<line x1="{L}" y1="{ry:.1f}" x2="{R}" y2="{ry:.1f}" stroke="var(--series-reference)" stroke-width="1.2" stroke-dasharray="5 5"/>')
        out.append(f'<text x="{R - 4}" y="{ry - 6:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="end">{ref["label"]}</text>')
    # 系列
    for s in series:
        vals = s["values"]
        pts = " ".join(f"{X(i):.0f},{Y(v):.0f}" for i, v in enumerate(vals))
        color = "var(--theme-accent)" if s.get("accent") else "var(--series-context)"
        width = 2.8 if s.get("accent") else 2.2
        out.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>')
        # 普通点小圆
        if s.get("accent"):
            for i, v in enumerate(vals):
                out.append(f'<circle cx="{X(i):.0f}" cy="{Y(v):.0f}" r="3.5" fill="{color}" stroke="var(--paper)" stroke-width="1.6"/>')
        # 峰/谷/拐点标注（只标关键点）
        for mark in s.get("marks", []):
            i, label, color = mark["i"], mark["label"], mark.get("color", "var(--ink)")
            dy = mark.get("dy", -12)
            out.append(f'<text x="{X(i):.0f}" y="{Y(vals[i]) + dy:.0f}" fill="{color}" font-size="12" font-weight="700" text-anchor="middle">{label}</text>')
        # 终点直接标注系列名+最新值
        out.append(f'<text x="{R - 4}" y="{Y(vals[-1]) - 10:.0f}" fill="{color}" font-size="11.5" font-weight="700" text-anchor="end">{s["name"]} {vals[-1]:,.0f}</text>')
    # x 轴标签
    step = max(1, n // 12)
    for i in range(0, n, step):
        out.append(f'<text x="{X(i):.0f}" y="{H - 12}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{xlabels[i]}</text>')
    out.append("</svg>")
    return "\n          ".join(out)


def waterfall_chart(chart: Dict[str, Any]) -> str:
    """viz-27：瀑布图。期初→各贡献（红降绿升）→期末，浮动条由累计值确定性计算。"""
    steps = chart["steps"]              # [{label, value(total期初期末), delta(贡献), kind: start|end|delta}]
    W, H = 980, 380
    TOP, BOT, L, R = 60, 64, 74, 930
    totals = [s["value"] for s in steps if s.get("kind") != "delta"]
    all_v = totals + [s["value"] + s.get("delta", 0) for s in steps]
    vmax, vmin = max(all_v), min(all_v)
    pad = (vmax - vmin) * 0.15 or 1.0
    vmax, vmin = vmax + pad, vmin - pad
    plot_h = H - TOP - BOT
    n = len(steps)
    zone = (R - L) / n
    bw = zone * 0.52
    def Y(v: float) -> float: return TOP + plot_h * (1 - (v - vmin) / (vmax - vmin))
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{chart["title"]}">']
    for i in range(5):
        y = TOP + plot_h * i / 4
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{R}" y2="{y:.1f}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{L - 8}" y="{y + 4:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="end">{vmax - (vmax - vmin) * i / 4:,.0f}</text>')
    # 连接虚线 + 浮动条
    prev_y: Optional[float] = None
    prev_x: Optional[float] = None
    for i, s in enumerate(steps):
        cx = L + zone * i + zone / 2
        if s.get("kind") in ("start", "end"):
            v = s["value"]
            y0, y1 = Y(v), TOP + plot_h
            out.append(f'<rect x="{cx - bw / 2:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{y1 - y0:.1f}" fill="var(--series-context)"/>')
            out.append(f'<text x="{cx:.1f}" y="{y0 - 10:.0f}" fill="var(--ink)" font-size="12.5" font-weight="700" text-anchor="middle">{v:,.0f}</text>')
            top_y = y0
        else:
            d = s["delta"]
            base = s["value"]
            y_base, y_new = Y(base), Y(base + d)
            y_top, y_bot = min(y_base, y_new), max(y_base, y_new)
            color = "var(--healthy)" if d > 0 else "var(--critical)"
            out.append(f'<rect x="{cx - bw / 2:.1f}" y="{y_top:.1f}" width="{bw:.1f}" height="{max(y_bot - y_top, 1.5):.1f}" fill="{color}"/>')
            sign = "+" if d > 0 else "−"
            out.append(f'<text x="{cx:.1f}" y="{y_top - 10:.0f}" fill="{color}" font-size="12.5" font-weight="700" text-anchor="middle">{sign}{abs(d):,.0f}</text>')
            top_y = y_top
        if prev_y is not None:
            out.append(f'<line x1="{prev_x:.1f}" y1="{prev_y:.1f}" x2="{cx - bw / 2:.1f}" y2="{prev_y:.1f}" stroke="var(--line-strong)" stroke-width="1.2" stroke-dasharray="4 3"/>')
        prev_y = top_y if s.get("kind") in ("start", "end") else Y(s["value"] + s.get("delta", 0))
        prev_x = cx + bw / 2
        out.append(f'<text x="{cx:.1f}" y="{H - 22}" fill="var(--ink)" font-size="12" font-weight="700" text-anchor="middle">{s["label"]}</text>')
        if s.get("sub"):
            out.append(f'<text x="{cx:.1f}" y="{H - 6}" fill="var(--muted)" font-size="11" text-anchor="middle">{s["sub"]}</text>')
    out.append("</svg>")
    return "\n          ".join(out)


def slope_chart(chart: Dict[str, Any]) -> str:
    """viz-11：斜率图。两期对比，每类一条线，终点直接标注，重点系列唯一强调色。"""
    items = chart["items"]              # [{label, before, after, accent, marks}]
    left_label = chart.get("left_label", "期初")
    right_label = chart.get("right_label", "期末")
    W, H = 980, 400
    TOP, BOT, LX, RX = 56, 50, 300, 680
    all_v = [v for it in items for v in (it["before"], it["after"])]
    vmax, vmin = max(all_v), min(all_v)
    pad = (vmax - vmin) * 0.15 or 1.0
    vmax, vmin = vmax + pad, vmin - pad
    plot_h = H - TOP - BOT
    def Y(v: float) -> float: return TOP + plot_h * (1 - (v - vmin) / (vmax - vmin))
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{chart["title"]}">']
    out.append(f'<text x="{LX - 8}" y="{TOP - 20}" fill="var(--muted)" font-size="12" font-weight="700" text-anchor="end">{left_label}</text>')
    out.append(f'<text x="{RX + 8}" y="{TOP - 20}" fill="var(--muted)" font-size="12" font-weight="700">{right_label}</text>')
    out.append(f'<line x1="{LX}" y1="{TOP}" x2="{LX}" y2="{TOP + plot_h}" stroke="var(--line-strong)" stroke-width="1.2"/>')
    out.append(f'<line x1="{RX}" y1="{TOP}" x2="{RX}" y2="{TOP + plot_h}" stroke="var(--line-strong)" stroke-width="1.2"/>')
    for it in items:
        yb, ya = Y(it["before"]), Y(it["after"])
        color = "var(--theme-accent)" if it.get("accent") else "var(--series-context)"
        w = 3.2 if it.get("accent") else 1.8
        out.append(f'<line x1="{LX}" y1="{yb:.1f}" x2="{RX}" y2="{ya:.1f}" stroke="{color}" stroke-width="{w}" stroke-linecap="round"/>')
        d = it["after"] - it["before"]
        dl = f'{"+" if d > 0 else "−"}{abs(d):,.0f}'
        lc = "var(--critical)" if d < 0 else ("var(--healthy)" if d > 0 else "var(--muted)")
        if it.get("accent"):
            out.append(f'<text x="{LX - 12}" y="{yb + 4:.1f}" fill="{lc}" font-size="12.5" font-weight="700" text-anchor="end">{it["label"]} {it["before"]:,.0f}</text>')
            out.append(f'<text x="{RX + 12}" y="{ya + 4:.1f}" fill="{lc}" font-size="12.5" font-weight="700">{it["after"]:,.0f}（{dl}）</text>')
        else:
            out.append(f'<text x="{LX - 12}" y="{yb + 4:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="end">{it["label"]} {it["before"]:,.0f}</text>')
            out.append(f'<text x="{RX + 12}" y="{ya + 4:.1f}" fill="var(--muted)" font-size="11.5">{it["after"]:,.0f}（{dl}）</text>')
        out.append(f'<circle cx="{LX}" cy="{yb:.1f}" r="4" fill="{color}"/>')
        out.append(f'<circle cx="{RX}" cy="{ya:.1f}" r="4" fill="{color}"/>')
    out.append("</svg>")
    return "\n          ".join(out)


def box_compare_chart(chart: Dict[str, Any]) -> str:
    """viz-16：箱线对比。min/Q1/中位/Q3/max 由原始值确定性计算。"""
    groups = chart["groups"]            # [{label, sub, values[], accent}]
    W, H = 980, 380
    TOP, BOT = 56, 56
    plot_h = H - TOP - BOT
    all_v = [v for g in groups for v in g["values"]]
    vmax, vmin = max(all_v), min(all_v)
    pad = (vmax - vmin) * 0.2 or 1.0
    vmax, vmin = vmax + pad, vmin - pad
    def Y(v: float) -> float: return TOP + plot_h * (1 - (v - vmin) / (vmax - vmin))
    zone = (W - 160) / len(groups)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{chart["title"]}">']
    for i in range(5):
        y = TOP + plot_h * i / 4
        out.append(f'<line x1="80" y1="{y:.1f}" x2="{W - 40}" y2="{y:.1f}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="72" y="{y + 4:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="end">{vmax - (vmax - vmin) * i / 4:,.1f}</text>')
    stats_all = []
    for i, g in enumerate(groups):
        st = _q(g["values"])
        stats_all.append(st)
        cx = 80 + zone * i + zone / 2
        bw = min(zone * 0.36, 110)
        color = "var(--healthy)" if g.get("accent") else "var(--series-context)"
        soft = "var(--healthy-soft)" if g.get("accent") else "var(--surface-strong)"
        # whiskers
        out.append(f'<line x1="{cx}" y1="{Y(st["max"]):.1f}" x2="{cx}" y2="{Y(st["q3"]):.1f}" stroke="{color}" stroke-width="1.6"/>')
        out.append(f'<line x1="{cx}" y1="{Y(st["q1"]):.1f}" x2="{cx}" y2="{Y(st["min"]):.1f}" stroke="{color}" stroke-width="1.6"/>')
        for v in (st["max"], st["min"]):
            out.append(f'<line x1="{cx - 12}" y1="{Y(v):.1f}" x2="{cx + 12}" y2="{Y(v):.1f}" stroke="{color}" stroke-width="1.6"/>')
        # box
        yq1, yq3 = Y(st["q1"]), Y(st["q3"])
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{min(yq1, yq3):.1f}" width="{bw:.1f}" height="{max(abs(yq3 - yq1), 1.5):.1f}" fill="{soft}" stroke="{color}" stroke-width="1.4"/>')
        # median
        ym = Y(st["median"])
        out.append(f'<line x1="{cx - bw / 2:.1f}" y1="{ym:.1f}" x2="{cx + bw / 2:.1f}" y2="{ym:.1f}" stroke="{color}" stroke-width="2.6"/>')
        # mean marker
        mean = sum(g["values"]) / len(g["values"])
        out.append(f'<rect x="{cx - 5:.1f}" y="{Y(mean) - 5:.1f}" width="10" height="10" transform="rotate(45 {cx:.1f} {Y(mean):.1f})" fill="{color}"/>')
        # labels
        out.append(f'<text x="{cx:.1f}" y="{H - 34}" fill="var(--ink)" font-size="12.5" font-weight="700" text-anchor="middle">{g["label"]}</text>')
        out.append(f'<text x="{cx:.1f}" y="{H - 17}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{g.get("sub", "")}</text>')
        out.append(f'<text x="{cx + bw / 2 + 10:.1f}" y="{ym + 4:.1f}" fill="var(--muted)" font-size="11" text-anchor="start">中位 {st["median"]:,.1f}</text>')
        out.append(f'<text x="{cx + bw / 2 + 10:.1f}" y="{Y(mean) + 4:.1f}" fill="var(--muted)" font-size="11">均值 {mean:,.2f}</text>')
    out.append("</svg>")
    return "\n          ".join(out)


def control_chart(chart: Dict[str, Any]) -> str:
    """viz-26：控制图。中心线=均值带、UCL/LCL=±band（band=3×1.4826×MAD，由技能产出），
    越限点标红菱形。坐标全部确定性计算。"""
    s = chart["series"][0]            # 单系列
    vals = s["values"]
    xlabels = chart["xlabels"]
    center, band = chart["center"], chart["band"]
    ucl, lcl = center + band, center - band
    W, H = 980, 360
    TOP, BOT, L, R = 58, 46, 74, 930
    lo = min(min(vals), lcl) * 0.985
    hi = max(max(vals), ucl) * 1.015
    plot_h = H - TOP - BOT
    n = len(vals)
    def X(i: int) -> float: return L + (R - L) * i / (n - 1)
    def Y(v: float) -> float: return TOP + plot_h * (1 - (v - lo) / (hi - lo))
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{chart["title"]}">']
    # 控制带底色
    out.append(f'<rect x="{L}" y="{Y(ucl):.1f}" width="{R - L}" height="{max(Y(lcl) - Y(ucl), 1):.1f}" fill="var(--surface-strong)"/>')
    # 网格刻度
    for i in range(5):
        y = TOP + plot_h * i / 4
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{R}" y2="{y:.1f}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{L - 8}" y="{y + 4:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="end">{hi - (hi - lo) * i / 4:,.0f}</text>')
    # UCL / 中心线 / LCL
    for v, lab, color, dash in ((ucl, f"UCL {ucl:,.0f}", "var(--watch)", "6 4"),
                                (center, f"均值 {center:,.0f}", "var(--muted)", None),
                                (lcl, f"LCL {lcl:,.0f}", "var(--watch)", "6 4")):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{R}" y2="{Y(v):.1f}" stroke="{color}" stroke-width="1.4"{d}/>')
        out.append(f'<text x="{R - 4}" y="{Y(v) - 6:.1f}" fill="{color}" font-size="11.5" text-anchor="end">{lab}</text>')
    # 主线
    pts = " ".join(f"{X(i):.0f},{Y(v):.0f}" for i, v in enumerate(vals))
    out.append(f'<polyline points="{pts}" fill="none" stroke="var(--theme-accent)" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/>')
    # 点 + 越限标记
    for i, v in enumerate(vals):
        ooc = v > ucl or v < lcl
        color = "var(--critical)" if ooc else "var(--theme-accent)"
        r = 5.5 if ooc else 3.5
        out.append(f'<rect x="{X(i) - r:.1f}" y="{Y(v) - r:.1f}" width="{2 * r}" height="{2 * r}" fill="{color}" transform="rotate(45 {X(i):.1f} {Y(v):.1f})"/>' if ooc
                   else f'<circle cx="{X(i):.0f}" cy="{Y(v):.0f}" r="{r}" fill="{color}" stroke="var(--paper)" stroke-width="1.6"/>')
        if ooc:
            out.append(f'<text x="{X(i):.0f}" y="{Y(v) + 24:.0f}" fill="var(--critical)" font-size="12" font-weight="700" text-anchor="middle">{v:,.0f}（越限）</text>')
    out.append(f'<text x="{R - 4}" y="{Y(vals[-1]) - 12:.0f}" fill="var(--theme-accent)" font-size="11.5" font-weight="700" text-anchor="end">{s["name"]}</text>')
    step = max(1, n // 12)
    for i in range(0, n, step):
        out.append(f'<text x="{X(i):.0f}" y="{H - 12}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{xlabels[i]}</text>')
    out.append("</svg>")
    return "\n          ".join(out)


def funnel_chart(chart: Dict[str, Any]) -> str:
    """viz-29：漏斗图。逐级宽度∝量级，逐级流失率直接标注，最大流失点用 critical 高亮。"""
    stages = chart["stages"]           # [{label, value}]，按漏斗顺序
    W, H = 980, max(300, 90 + 66 * len(stages))
    vmax = max(s["value"] for s in stages)
    drop_rates = []
    for i in range(1, len(stages)):
        d = (stages[i - 1]["value"] - stages[i]["value"]) / stages[i - 1]["value"]
        drop_rates.append(d)
    worst = drop_rates.index(max(drop_rates)) if drop_rates else -1
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{chart["title"]}">']
    cx = W * 0.42
    y = 46
    out.append(f'<text x="{cx}" y="28" fill="var(--muted)" font-size="12" text-anchor="middle">{chart.get("unit_meta", "")}</text>')
    for i, s in enumerate(stages):
        bw = max(40, (W * 0.52) * s["value"] / vmax)
        x = cx - bw / 2
        col = "var(--theme-accent)" if i == 0 else "var(--series-context)"
        if i > 0:
            prev = stages[i - 1]
            prev_w = max(40, (W * 0.52) * prev["value"] / vmax)
            trapez = f'{cx - prev_w/2},{y} {cx + prev_w/2},{y} {cx + bw/2},{y+46} {cx - bw/2},{y+46}'
            fill = "var(--critical)" if i - 1 == worst else "var(--line)"
            op = "0.28" if i - 1 == worst else "0.12"
            out.append(f'<polygon points="{trapez}" fill="{fill}" opacity="{op}"/>')
            rate = drop_rates[i - 1]
            rc = "var(--critical)" if i - 1 == worst else "var(--watch)"
            fw = ' font-weight="700"' if i - 1 == worst else ""
            out.append(f'<text x="{cx + W*0.52/2 + 16}" y="{y - 2:.0f}" fill="{rc}" font-size="12.5"{fw}>流失 {rate:.1%}</text>')
            y += 20
        out.append(f'<rect x="{x:.1f}" y="{y}" width="{bw:.1f}" height="46" rx="3" fill="{col}" opacity="{0.92 if i == 0 else 0.72}"/>')
        out.append(f'<text x="{cx}" y="{y + 29}" fill="var(--ink)" font-size="13" font-weight="700" text-anchor="middle">{s["label"]} {s["value"]:,.0f}</text>')
        y += 66
    if worst >= 0:
        out.append(f'<text x="{cx}" y="{y + 8:.0f}" fill="var(--critical)" font-size="12.5" font-weight="700" text-anchor="middle">主要流失点：{stages[worst]["label"]} → {stages[worst+1]["label"]}（{drop_rates[worst]:.1%}）</text>')
    out.append("</svg>")
    return "\n          ".join(out)


def pareto_chart(chart: Dict[str, Any]) -> str:
    """viz-28：帕累托。柱按值降序（确定性排序），累计占比折线 + 80% 参考线，前 N 项结论标注。"""
    items = sorted(chart["items"], key=lambda x: (-x["value"], x["label"]))
    total = sum(x["value"] for x in items)
    thr = float(chart.get("threshold", 80))
    W, H = 980, 420
    TOP, BOT, L, R = 56, 56, 80, W - 60
    plot_w, plot_h = R - L, H - TOP - BOT
    vmax = items[0]["value"]
    bw = plot_w / len(items)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{chart["title"]}">']
    for i in range(5):
        y = TOP + plot_h * i / 4
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{R}" y2="{y:.1f}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{L - 8}" y="{y + 4:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="end">{vmax * (1 - i / 4):,.0f}</text>')
    for i in range(6):
        x = L + plot_w * i / 5
        out.append(f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" y2="{TOP + plot_h}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{TOP - 8}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{i * 20}%</text>')
    y80 = TOP + plot_h * (1 - thr / 100)
    out.append(f'<line x1="{L}" y1="{y80:.1f}" x2="{R}" y2="{y80:.1f}" stroke="var(--watch)" stroke-width="1.4" stroke-dasharray="6 4"/>')
    out.append(f'<text x="{R}" y="{y80 - 6:.1f}" fill="var(--watch)" font-size="11.5" text-anchor="end">累计 {thr:.0f}%</text>')
    cum, cum_pts, acc, cum_vals = 0.0, [], 0.0, []
    for i, it in enumerate(items):
        x = L + bw * i + bw / 2
        h = plot_h * it["value"] / vmax
        out.append(f'<rect x="{x - bw*0.32:.1f}" y="{TOP + plot_h - h:.1f}" width="{bw*0.64:.1f}" height="{h:.1f}" rx="2" fill="var(--series-context)" opacity="0.85"/>')
        out.append(f'<text x="{x:.1f}" y="{TOP + plot_h + 18:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="middle" transform="rotate(-18 {x:.1f} {TOP + plot_h + 18})">{it["label"]}</text>')
        acc += it["value"]
        cum = acc / total * 100
        cum_vals.append(cum)
        cum_pts.append((x, TOP + plot_h * (1 - cum / 100)))
    # 前 N 项 = 累计占比首次达到 thr 的最小 N（帕累托口径）
    n80 = next((i + 1 for i, cv in enumerate(cum_vals) if cv >= thr), len(items))
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in cum_pts)
    out.append(f'<polyline points="{pts}" fill="none" stroke="var(--theme-accent)" stroke-width="2.4"/>')
    for x, y in cum_pts:
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="var(--theme-accent)"/>')
    fx, fy = cum_pts[-1]
    out.append(f'<text x="{fx + 8:.1f}" y="{fy + 4:.1f}" fill="var(--theme-accent)" font-size="12" font-weight="700">累计 {cum:.1f}%</text>')
    out.append(f'<text x="{(L+R)/2}" y="{H - 6}" fill="var(--ink)" font-size="12.5" font-weight="700" text-anchor="middle">前 {n80} 项累计贡献 {cum_vals[n80-1]:.1f}%（达到 {thr:.0f}% 参考线）</text>')
    out.append("</svg>")
    return "\n          ".join(out)


def histogram_chart(chart: Dict[str, Any]) -> str:
    """viz-10：直方图。等宽分箱由数据确定性计算，均值/中位参考线，分布形态不超出数据。"""
    vals = sorted(float(v) for v in chart["values"])
    n_bins = int(chart.get("bins", 8))
    vmin, vmax = vals[0], vals[-1]
    span = (vmax - vmin) or 1.0
    bw = span / n_bins
    bins = [0] * n_bins
    for v in vals:
        b = min(n_bins - 1, int((v - vmin) / bw))
        bins[b] += 1
    mean = sum(vals) / len(vals)
    med = vals[len(vals) // 2] if len(vals) % 2 else (vals[len(vals)//2 - 1] + vals[len(vals)//2]) / 2
    W, H = 980, 400
    TOP, BOT, L, R = 56, 56, 80, W - 60
    plot_w, plot_h = R - L, H - TOP - BOT
    cmax = max(bins)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{chart["title"]}">']
    for i in range(5):
        y = TOP + plot_h * i / 4
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{R}" y2="{y:.1f}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{L - 8}" y="{y + 4:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="end">{cmax * (1 - i/4):.0f}</text>')
    bwpx = plot_w / n_bins
    for i, cnt in enumerate(bins):
        h = plot_h * cnt / cmax
        x = L + bwpx * i
        out.append(f'<rect x="{x + 1.5:.1f}" y="{TOP + plot_h - h:.1f}" width="{bwpx - 3:.1f}" height="{h:.1f}" rx="2" fill="var(--series-context)" opacity="0.82"/>')
        if cnt:
            out.append(f'<text x="{x + bwpx/2:.1f}" y="{TOP + plot_h - h - 6:.1f}" fill="var(--muted)" font-size="11" text-anchor="middle">{cnt}</text>')
        out.append(f'<text x="{x + bwpx/2:.1f}" y="{TOP + plot_h + 18:.1f}" fill="var(--muted)" font-size="10.5" text-anchor="middle">{vmin + bw*i:,.0f}</text>')
    for v, lbl, col in ((mean, f"均值 {mean:,.1f}", "var(--theme-accent)"),
                        (med, f"中位 {med:,.1f}", "var(--muted)")):
        x = L + plot_w * (v - vmin) / span
        out.append(f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" y2="{TOP + plot_h}" stroke="{col}" stroke-width="1.6" stroke-dasharray="5 4"/>')
        out.append(f'<text x="{x + 6:.1f}" y="{TOP + 14}" fill="{col}" font-size="11.5">{lbl}</text>')
    out.append("</svg>")
    return "\n          ".join(out)


def scatter_chart(chart: Dict[str, Any]) -> str:
    """viz-17：散点关系。坐标由数值计算，OLS 趋势线确定性拟合，r 与样本量直接标注。"""
    pts = chart["points"]              # [{x, y, label?}]
    W, H = 980, 420
    TOP, BOT, L, R = 56, 56, 80, W - 70
    plot_w, plot_h = R - L, H - TOP - BOT
    xs = [p["x"] for p in pts]; ys = [p["y"] for p in pts]
    xmin, xmax = min(xs), max(xs); ymin, ymax = min(ys), max(ys)
    padx = (xmax - xmin) * 0.08 or 1.0; pady = (ymax - ymin) * 0.08 or 1.0
    xmin, xmax, ymin, ymax = xmin - padx, xmax + padx, ymin - pady, ymax + pady
    n = len(pts)
    mx, my = sum(xs)/n, sum(ys)/n
    sxx = sum((x-mx)**2 for x in xs); sxy = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
    slope = sxy / sxx if sxx else 0.0
    r = sxy / ((sxx * sum((y-my)**2 for y in ys)) ** 0.5) if sxx else 0.0
    def X(v): return L + plot_w * (v - xmin) / (xmax - xmin)
    def Y(v): return TOP + plot_h * (1 - (v - ymin) / (ymax - ymin))
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{chart["title"]}">']
    for i in range(5):
        y = TOP + plot_h * i / 4
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{R}" y2="{y:.1f}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{L - 8}" y="{y + 4:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="end">{ymax - (ymax - ymin)*i/4:,.1f}</text>')
    for i in range(5):
        x = L + plot_w * i / 4
        out.append(f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" y2="{TOP + plot_h}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{TOP + plot_h + 18:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{xmin + (xmax - xmin)*i/4:,.1f}</text>')
    for p in pts:
        out.append(f'<circle cx="{X(p["x"]):.1f}" cy="{Y(p["y"]):.1f}" r="4.2" fill="var(--theme-accent)" opacity="0.62"/>')
    if chart.get("trend", True) and sxx:
        out.append(f'<line x1="{X(xmin):.1f}" y1="{Y(mx + slope*(xmin - mx)):.1f}" x2="{X(xmax):.1f}" y2="{Y(mx + slope*(xmax - mx)):.1f}" stroke="var(--critical)" stroke-width="1.8" stroke-dasharray="7 4"/>')
        out.append(f'<text x="{R}" y="{TOP - 10}" fill="var(--muted)" font-size="12" text-anchor="end">n={n} · r={r:.3f}（趋势线为 OLS，非因果）</text>')
    out.append(f'<text x="{(L+R)/2}" y="{H - 6}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{chart.get("xlabel", "x")}</text>')
    out.append("</svg>")
    return "\n          ".join(out)


def grouped_bar_chart(chart: Dict[str, Any]) -> str:
    """viz-03：分组柱。同单位 ≤3 系列并排，值直接标注，重点系列唯一强调色。"""
    cats = chart["categories"]
    series = chart["series"]           # [{name, values, accent?}]（len ≤ 3，值同单位）
    W, H = 980, 420
    TOP, BOT, L, R = 56, 62, 80, W - 60
    plot_w, plot_h = R - L, H - TOP - BOT
    vmax = max(v for s in series for v in s["values"])
    vmax = vmax * 1.12 or 1.0
    cw = plot_w / len(cats)
    gw = min(cw * 0.72, 120)
    bw = gw / len(series)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{chart["title"]}">']
    for i in range(5):
        y = TOP + plot_h * i / 4
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{R}" y2="{y:.1f}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{L - 8}" y="{y + 4:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="end">{vmax * (1 - i/4):,.0f}</text>')
    for ci, cat in enumerate(cats):
        cx = L + cw * ci + cw / 2
        gx = cx - gw / 2
        out.append(f'<text x="{cx:.1f}" y="{TOP + plot_h + 20:.1f}" fill="var(--muted)" font-size="12" text-anchor="middle">{cat}</text>')
        for si, s in enumerate(series):
            v = s["values"][ci]
            h = plot_h * v / vmax
            x = gx + bw * si
            col = "var(--theme-accent)" if s.get("accent") else "var(--series-context)"
            op = "0.95" if s.get("accent") else "0.6"
            out.append(f'<rect x="{x + 2:.1f}" y="{TOP + plot_h - h:.1f}" width="{bw - 4:.1f}" height="{h:.1f}" rx="2.5" fill="{col}" opacity="{op}"/>')
            fw = ' font-weight="700"' if s.get("accent") else ""
            out.append(f'<text x="{x + bw/2:.1f}" y="{TOP + plot_h - h - 6:.1f}" fill="var(--ink)" font-size="10.5"{fw} text-anchor="middle">{v:,.0f}</text>')
    # 图例：右上角横排，仅当多系列（单系列冗余，viz-03 纪律）
    if len(series) > 1:
        lx = R - sum(len(s["name"]) * 11 + 44 for s in series)
        for s in series:
            col = "var(--theme-accent)" if s.get("accent") else "var(--series-context)"
            out.append(f'<rect x="{lx:.1f}" y="{TOP - 22}" width="12" height="12" rx="2" fill="{col}" opacity="0.9"/>')
            out.append(f'<text x="{lx + 16:.1f}" y="{TOP - 12}" fill="var(--muted)" font-size="11.5">{s["name"]}</text>')
            lx += len(s["name"]) * 11 + 44
    out.append("</svg>")
    return "\n          ".join(out)


RENDERERS = {"line": line_chart, "waterfall": waterfall_chart,
             "slope": slope_chart, "box": box_compare_chart,
             "control": control_chart, "funnel": funnel_chart,
             "pareto": pareto_chart, "histogram": histogram_chart,
             "scatter": scatter_chart, "grouped_bar": grouped_bar_chart}

# 第八轮扩容：38 型扩展渲染器（references/chart_prompts_48.json 的渲染纪律逐条落码），
# 并入后 RENDERERS 覆盖 48/48（vbar/hbar 为通用版，report_renderer 保留报告专用版）。
import chart_renderers_ext as _chart_renderers_ext  # noqa: E402

RENDERERS.update(_chart_renderers_ext.RENDERERS)
assert len(RENDERERS) == 48 and {c["key"] for c in CHART_INDEX} == set(RENDERERS), \
    "RENDERERS 必须 48/48 全覆盖且键名与 CHART_INDEX 一致"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="48 图谱：选型建议 + 确定性 SVG 渲染")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    rec = sub.add_parser("recommend")
    rec.add_argument("--shape", required=True)
    rec.add_argument("--intent", required=True)
    args = ap.parse_args()
    if args.cmd == "list":
        print(json.dumps({"count": len(CHART_INDEX), "items": CHART_INDEX}, ensure_ascii=False, indent=1))
        return 0
    if args.cmd == "recommend":
        print(json.dumps({"shape": args.shape, "intent": args.intent,
                          "recommended": recommend(args.shape, args.intent)}, ensure_ascii=False, indent=1))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

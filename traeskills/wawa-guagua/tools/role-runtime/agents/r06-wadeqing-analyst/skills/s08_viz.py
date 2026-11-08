# -*- coding: utf-8 -*-
"""S08 可视化与报告 —— 能力域 8。

整合自 plotly（数据→chart）、ai-data-visualization-prompts（48 条图表提示词
→ 可审视图表契约）、data-analysis-report-agent（可审计报告 + QA）。

主张：**图表明结论不描述、标题即结论、决策建议默认禁止**。本技能提供
图表规格(Chart Spec)确定性校验 + 报告组装(带 QA 清单) + 图表选型提示词。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from . import _common as c

# --------------------------------------------------------------------------- #
# 48 条完整图表提示词注册表（由 build_chart_prompts.py 从
# ai-data-visualization-prompts 的 48 个 .md 确定性编译；
# 每条含 learn/use_when/prepare[]/prompt_template/outcome/checklist[]）。
_PROMPT_REGISTRY: Dict[str, Any] | None = None


def _prompts() -> Dict[str, Any]:
    """惰性加载 48 提示词注册表；缺文件时如实返回空（不假装有）。"""
    global _PROMPT_REGISTRY
    if _PROMPT_REGISTRY is None:
        path = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))),
            "references", "chart_prompts_48.json")
        try:
            with open(path, encoding="utf-8") as f:
                _PROMPT_REGISTRY = json.load(f)
        except OSError:
            _PROMPT_REGISTRY = {"count": 0, "items": []}
    return _PROMPT_REGISTRY


def _prompt_of(canon_key: str) -> Dict[str, Any]:
    """按规范图表名取整条提示词包（无则返回空 dict，不编造）。"""
    for it in _prompts().get("items", []):
        if it.get("key") == canon_key:
            return it
    return {}

NAME = "viz"
DESC = "可视化与报告：图表规格校验 / 报告组装 / 图表选型"

# 48 类图表（对齐 ai-data-visualization-prompts 的完整清单）
CHART_TYPES = [
    "vertical-bar", "horizontal-bar", "grouped-bar", "stacked-bar",
    "100pct-stacked", "line", "area", "pie", "donut", "histogram",
    "slope", "dumbbell", "dot", "lollipop", "waffle", "boxplot",
    "scatter", "bubble", "heatmap", "radar", "violin", "ridgeline",
    "parallel-coordinates", "error-bar", "forest", "control", "waterfall",
    "pareto", "funnel", "bullet", "gauge", "calendar-heatmap", "gantt",
    "candlestick", "sankey", "streamgraph", "treemap", "sunburst",
    "choropleth", "symbol-map", "geographic-flow", "network", "rose",
    "bar-line-target-band", "contribution-bridge", "dual-axis-bar-line",
    "kpi-trend-breakdown", "small-multiples",
]

# 旧别名 → 规范名（兼容早期 spec 与测试的 "bar"/"box" 等写法）
CHART_ALIASES = {
    "bar": "vertical-bar", "horizontal_bar": "horizontal-bar",
    "stacked_bar": "stacked-bar", "box": "boxplot",
    "retention_matrix": "heatmap",
}

# 各图表要求的必填字段（除 chart_type/title/data 外）
CHART_REQUIRED = {
    "vertical-bar": ["x_field", "y_field"],
    "horizontal-bar": ["x_field", "y_field"],
    "grouped-bar": ["x_field", "y_field", "series_field"],
    "stacked-bar": ["x_field", "y_field", "series_field"],
    "100pct-stacked": ["x_field", "y_field", "series_field"],
    "line": ["x_field", "y_field"],
    "area": ["x_field", "y_field"],
    "pie": ["label_field", "value_field"],
    "donut": ["label_field", "value_field"],
    "histogram": ["value_field"],
    "slope": ["x_field", "y_field"],
    "dumbbell": ["item_field", "start_field", "end_field"],
    "dot": ["x_field", "y_field"],
    "lollipop": ["x_field", "y_field"],
    "waffle": ["value", "total"],
    "boxplot": ["value_field"],
    "scatter": ["x_field", "y_field"],
    "bubble": ["x_field", "y_field", "size_field"],
    "heatmap": ["x_field", "y_field", "value_field"],
    "radar": ["category_field", "value_field"],
    "violin": ["value_field"],
    "ridgeline": ["x_field", "y_field", "series_field"],
    "parallel-coordinates": ["dimensions"],
    "error-bar": ["category_field", "value_field", "error_field"],
    "forest": ["label_field", "estimate_field", "ci_low_field", "ci_high_field"],
    "control": ["value_field", "center_field", "lower_field", "upper_field"],
    "waterfall": ["category_field", "value_field"],
    "pareto": ["category_field", "value_field"],
    "funnel": ["stage_field", "value_field"],
    "bullet": ["label_field", "value_field", "target_field"],
    "gauge": ["value", "min", "max"],
    "calendar-heatmap": ["date_field", "value_field"],
    "gantt": ["task_field", "start_field", "end_field"],
    "candlestick": ["date_field", "open_field", "high_field", "low_field", "close_field"],
    "sankey": ["source_field", "target_field", "value_field"],
    "streamgraph": ["x_field", "y_field", "series_field"],
    "treemap": ["label_field", "value_field"],
    "sunburst": ["label_field", "value_field", "parent_field"],
    "choropleth": ["region_field", "value_field"],
    "symbol-map": ["lat_field", "lon_field", "value_field"],
    "geographic-flow": ["origin_field", "dest_field", "value_field"],
    "network": ["source_field", "target_field"],
    "rose": ["category_field", "value_field"],
    "bar-line-target-band": ["category_field", "bar_field", "line_field"],
    "contribution-bridge": ["category_field", "value_field"],
    "dual-axis-bar-line": ["category_field", "bar_field", "line_field"],
    "kpi-trend-breakdown": ["period_field", "value_field"],
    "small-multiples": ["x_field", "y_field", "facet_field"],
}

# 图表选型提示词（浓缩自 48 条人工图表提示词）
CHART_GUIDE = {
    "vertical-bar": "类别比较（≤7 竖柱）；按值排序，强调关键柱",
    "horizontal-bar": "长标签/多类（8–15）比较；按值排序",
    "grouped-bar": "多系列分类对比（≤4 系列）；直接标值避免图例反复看",
    "stacked-bar": "部分与整体（总值也有意义）；底部色为基线类别",
    "100pct-stacked": "构成占比随时间/类变化；突出比例而非绝对量",
    "line": "时间连续趋势；Y 轴末端直接标注系列，最多 4 条，绝对值从 0 起",
    "area": "量级变化 + 累积感；系列≤4 且底层透明",
    "pie": "构成占比（≤6 类且合计 100%）；超过 6 类改用 bar",
    "donut": "中心放总额/关键数字的饼图变体；仍限少类",
    "histogram": "分布形态；bin 数≈sqrt(n) 或 Freedman-Diaconis",
    "slope": "两点间变化斜率（如同比）；标变化率与方向",
    "dumbbell": "两时点/两组差异；线长=变化量，按差排序",
    "dot": "精确比较多类别；无柱长误导，可横向排布",
    "lollipop": "柱顶收点为点的高级条形；强调值与排序",
    "waffle": "百分比直觉化（每格=单位）；适合≤100 格",
    "boxplot": "分布 + 离群；适用于多组对比",
    "scatter": "两变量关系；加趋势线，只标显著离群点",
    "bubble": "散点+第三维大小；限制气泡数防重叠",
    "heatmap": "矩阵强度（留存/相关）；单一色阶蓝橙，不用红绿",
    "radar": "多维轮廓对比（≤8 轴）；量纲须可比",
    "violin": "分布形态+密度；优于箱线的精细比较",
    "ridgeline": "多组分布叠放；适合时间/类别密度演化",
    "parallel-coordinates": "高维个体轨迹；先标准化再绘图",
    "error-bar": "均值±误差/置信区间；必须标注误差含义",
    "forest": "效应量+置信区间（meta/模型系数）；虚线标 0",
    "control": "过程控制图；中心线+±3σ 控制限",
    "waterfall": "累积增减贡献；起点/终点显式标注",
    "pareto": "累计贡献 80/20；左轴值+右轴累计%",
    "funnel": "有序流失过程；标每步绝对数 + 转化率，高亮最大流失步",
    "bullet": "KPI 对照目标；标区间（差/达标/超额）",
    "gauge": "单一 KPI 仪表；明确刻度上下限与阈值色",
    "calendar-heatmap": "日期×强度（GitHub 贡献矩阵式）；适合日粒度",
    "gantt": "任务时间轴；标依赖与里程碑",
    "candlestick": "金融 OHLC；涨跌用统一配色并声明",
    "sankey": "流量/转化流向；宽度=量，层级清晰",
    "streamgraph": "多系列占比随时间的波动；强调形态而非精确值",
    "treemap": "层级占比（面积=值）；适合大类目嵌套",
    "sunburst": "多层环形层级占比；由内向外逐层",
    "choropleth": "地理区域着色；用分位数分档不用线性色",
    "symbol-map": "地图散点/气泡；半径按值缩放",
    "geographic-flow": "起点→终点流动；流量分级上色",
    "network": "关系网络；节点度+边权表达，避免毛发团",
    "rose": "极坐标条形（风向玫瑰/周期）；量纲一致",
    "bar-line-target-band": "柱=实际 + 线=对比 + 带=目标区间",
    "contribution-bridge": "瀑布桥接：从基期→逐项→报告期",
    "dual-axis-bar-line": "双轴柱线；标明左右轴口径，谨慎用双轴",
    "kpi-trend-breakdown": "KPI 随时间 + 构成拆解；首图给总量趋势",
    "small-multiples": "多面板同尺度对比；保持轴一致便于横比",
}

# 别名也提供 guide 入口（guide --chart bar 可用）
for _alias, _canon in CHART_ALIASES.items():
    CHART_GUIDE.setdefault(_alias, CHART_GUIDE.get(_canon, ""))


def _canon(ct: str) -> str:
    return CHART_ALIASES.get(ct, ct)


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)

    s = act.add_parser("spec", help="校验图表规格 JSON（确定性 schema 门禁）")
    s.add_argument("--input", required=True)

    r = act.add_parser("report", help="组装可审计 markdown 报告（含 QA 清单）")
    r.add_argument("--metrics", required=True, help="指标结果 JSON 路径")
    r.add_argument("--title", default="分析报告")
    r.add_argument("--output", default="report.md")

    g = act.add_parser("guide", help="图表选型提示词（或全部列出）")
    g.add_argument("--chart", default=None, choices=list(CHART_GUIDE))

    pr = act.add_parser("prompt", help="输出某图的完整提示词包（提示词模板+检查清单，来自 48 提示词注册表）")
    pr.add_argument("--chart", default=None,
                    help="规范图表名；缺省则列出全部 48 条的 id/key/标题")


def run(args) -> Dict[str, Any]:
    if args.action == "spec":
        return _validate_spec(c.load_json(args.input))
    if args.action == "report":
        metrics = c.load_json(args.metrics)
        out = _report(metrics, args.title, args.output)
        return out
    if args.action == "guide":
        return _guide(args.chart)
    if args.action == "prompt":
        return _prompt(args.chart)
    return {"error": f"未知动作: {args.action}"}


def _prompt(chart):
    reg = _prompts()
    if reg.get("count", 0) < 48:
        return {"error": "48 提示词注册表缺失或不完整：先运行 "
                         "python build_chart_prompts.py 重新编译（不假装有提示词）"}
    if not chart:
        return {"count": reg["count"],
                "items": [{"id": i["id"], "key": i["key"], "number": i["number"],
                           "title": i["title"], "level": i["level"]}
                          for i in reg["items"]]}
    canon = _canon(chart)
    it = _prompt_of(canon)
    if not it:
        return {"error": f"未注册的图表: {chart}"}
    return {"prompt": it, "canonical": canon}


def _prompt_meta(canon: str) -> Dict[str, Any]:
    it = _prompt_of(canon)
    if not it:
        return {"prompt_id": None, "note": "该图无提示词条目（注册表缺）"}
    return {"prompt_id": it["id"], "level": it["level"], "group": it["group"],
            "use_when": it["use_when"], "prepare": it["prepare"],
            "checklist": it["checklist"]}


# --------------------------------------------------------------------------- #
def _validate_spec(spec: Any) -> Dict[str, Any]:
    errors: List[str] = []
    if not isinstance(spec, dict):
        return {"ok": False, "errors": ["chart spec 必须是 JSON 对象"]}
    ct = spec.get("chart_type", "")
    canon = _canon(ct)
    if canon not in CHART_TYPES:
        errors.append(f"chart_type 非法: {ct!r}（应为 48 类之一，见 valid_chart_types）")
    else:
        for req in CHART_REQUIRED[canon]:
            if not spec.get(req):
                errors.append(f"{ct} 缺必填字段 {req}")
    if not spec.get("title"):
        errors.append("缺 title（标题即结论，禁止空）")
    if "data" not in spec:
        errors.append("缺 data（数据数组）")
    # 报告纪律：决策建议默认禁止
    if spec.get("decision_recommendation"):
        errors.append("decision_recommendation 默认禁止（仅授权才写）")
    return {"ok": not errors, "chart_type": ct, "canonical": _canon(ct),
            "errors": errors, "chart_type_count": len(CHART_TYPES),
            "valid_chart_types": CHART_TYPES,
            "prompt_meta": _prompt_meta(_canon(ct))}


def _guide(chart):
    if chart:
        return {"chart": chart, "guide": CHART_GUIDE.get(chart, ""),
                "canonical": _canon(chart)}
    return {"chart_guide": CHART_GUIDE, "aliases": CHART_ALIASES,
            "chart_type_count": len(CHART_TYPES),
            "valid_chart_types": CHART_TYPES}


def _report(metrics: Dict[str, Any], title: str, output: str) -> Dict[str, Any]:
    lines = [f"# {title}", "",
             f"_生成时间：{_ts()} · 数据结论不超数据边界_", ""]
    # 金字塔：先结论后证据（无 conclusion 就从标量信号合成一句）
    lines += ["## 结论", "", _synthesize_conclusion(metrics), ""]
    for sec, content in metrics.items():
        if sec == "conclusion":
            continue
        lines += [f"## {sec}", "", "```json",
                  __import__("json").dumps(content, ensure_ascii=False, indent=2),
                  "```", ""]
    # QA 清单（可审计纪律）
    lines += ["## QA 清单", "", "- [ ] 图表与文字互证、不互抄", 
              "- [ ] 点名季节性/促销等驱动因素已做 driver 分解",
              "- [ ] 结论未超过数据边界", "- [ ] 决策建议（若写出）已获授权",
              "- [ ] 每个数字给了上下文与适度舍入", ""]
    c.write_text(output, "\n".join(lines))
    return {"report_path": output, "sections": list(metrics.keys()),
            "qa_checklist": ["文图互证", "driver分解", "结论边界",
                             "决策授权", "数字上下文"]}


def _synthesize_conclusion(metrics: Dict[str, Any]) -> str:
    if isinstance(metrics, dict) and "conclusion" in metrics:
        return str(metrics["conclusion"])
    if not isinstance(metrics, dict):
        return "无结构化结论"
    parts = []
    for k in ("total", "status", "grade", "verdict", "decision", "ok"):
        if k in metrics:
            parts.append(f"{k}={metrics[k]}")
    return "；".join(parts) if parts else "见下方明细指标"


def _ts() -> str:
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
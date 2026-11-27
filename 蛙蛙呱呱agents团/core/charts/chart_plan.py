# -*- coding: utf-8 -*-
"""core/chart_plan —— 自动选图 + 图表规格。

用户要的「每份报告都高级」，拆成三条可执行规格：

    1. 数据准备：每节要画图，至少得有几个点、几个维度（不够就改表格，不硬画）
    2. 自动选型：按数据形状 + 要讲的结论选图型，而不是一律 hbar
    3. 图会讲话：标题即结论、必须给基线（和谁比）、关键点必须标注、脚注给口径

形状由 chart 负载本身推断（bars/items/steps/series/…），不靠调用方声明。

用法：
    from core.charts.chart_plan import choose, audit
    plan = choose(chart)          # -> {"type": ..., "why": ...} 或 {"type": "table", "missing": [...]}
    issues = audit(sec)           # -> ["图缺基线", ...]
"""
from __future__ import annotations

from typing import Any, Dict, List

# 形状 → 可用图型（第一个是首选）。都是 charts_pro 已实现的型。
SHAPES: Dict[str, Dict[str, Any]] = {
    # 纯类别排名/比较
    "categorical": {"types": ["hbar", "vbar", "dot"], "min_points": 3,
                    "why": "少类别比较，条图最不容易读错顺序"},
    # 两期变化（期初→期末，含中间贡献）
    "bridge": {"types": ["waterfall", "bridge"], "min_points": 3,
               "why": "期初到期末有中间增减，瀑布图直接显示谁贡献了多少"},
    # 构成（部分占整体）
    "composition": {"types": ["stacked_bar", "pct_stacked", "donut"],
                    "min_points": 2, "why": "构成用堆叠，比饼图更耐读"},
    # 时间序列
    "timeline": {"types": ["line", "area"], "min_points": 4,
                 "why": "时间序列只看趋势，线图信息密度最高"},
    # 分布/集中度（帕累托）
    "distribution": {"types": ["pareto", "hbar"], "min_points": 3,
                     "why": "看头部集中度用帕累托，80% 参考线就是结论"},
    # 两两关系
    "relationship": {"types": ["scatter", "bubble"], "min_points": 5,
                     "why": "相关关系只能用散点，柱图会误导读成排名"},
}

# 少于这个点数，一律改表格（用户确认的规则）
MIN_POINTS_FOR_CHART = 3


def infer_shape(chart: Dict[str, Any]) -> str:
    """从负载字段推断数据形状。"""
    if chart.get("steps"):
        return "bridge"
    if chart.get("points") or chart.get("x") is not None:
        return "relationship"
    if chart.get("series"):
        return "timeline"
    if chart.get("segments") or chart.get("parts"):
        return "composition"
    items = chart.get("items") or chart.get("bars") or []
    # items 里带累计/份额语义 → 分布
    if chart.get("cumulative") or chart.get("threshold"):
        return "distribution"
    return "categorical"


def count_points(chart: Dict[str, Any]) -> int:
    for k in ("bars", "items", "steps", "segments", "parts", "points"):
        v = chart.get(k)
        if isinstance(v, list) and v:
            return len(v)
    series = chart.get("series")
    if isinstance(series, list) and series:
        first = series[0] if isinstance(series[0], dict) else {}
        pts = first.get("points") or first.get("values") or []
        return len(pts) if isinstance(pts, list) else 0
    return 0


def choose(chart: Dict[str, Any]) -> Dict[str, Any]:
    """给一张图定图型；数据不够就明确建议改表格并说缺什么。"""
    shape = infer_shape(chart)
    n = count_points(chart)
    spec = SHAPES.get(shape, SHAPES["categorical"])
    current = str(chart.get("type") or "")

    if n < MIN_POINTS_FOR_CHART:
        return {"type": "table", "shape": shape, "points": n,
                "missing": [f"至少 {MIN_POINTS_FOR_CHART} 个数据点（现在 {n} 个）"],
                "why": "点数不足，图会读成一条线；改用表格 + 大数字更清楚"}

    if n < spec["min_points"]:
        return {"type": "table", "shape": shape, "points": n,
                "missing": [f"「{spec['types'][0]}」至少要 {spec['min_points']} 个点（现在 {n} 个）"],
                "why": spec["why"]}

    allowed = spec["types"]
    picked = current if current in allowed else allowed[0]
    return {"type": picked, "shape": shape, "points": n,
            "upgrade": current != picked,
            "why": spec["why"]}


def audit(chart: Dict[str, Any]) -> List[str]:
    """图的叙事规格：结论标题、基线、标注、口径脚注。"""
    issues: List[str] = []
    if not chart.get("title"):
        issues.append("图缺结论标题")
    if not chart.get("source"):
        issues.append("图缺来源")
    if not chart.get("baseline") and not chart.get("references"):
        issues.append("图缺基线（和谁比）；没有基线的图只能看大小，看不出好坏")
    if not (chart.get("annotate") or chart.get("callout")):
        issues.append("图缺关键点标注（转折/异常/首末值）")
    # 单位一致性：一张图只能有一个单位；混单位是错图，不是风格问题
    items = (chart.get("bars") or chart.get("items") or chart.get("points") or [])
    units = {str(x.get("unit")) for x in items
             if isinstance(x, dict) and x.get("unit")}
    if len(units) > 1:
        issues.append(f"图混单位：{sorted(units)[:4]}；请按单位拆图或只留主单位")
    if not chart.get("unit_meta") and not units:
        issues.append("图缺 unit_meta（读者不知道数字是什么单位）")
    return issues

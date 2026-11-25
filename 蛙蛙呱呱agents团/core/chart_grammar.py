# -*- coding: utf-8 -*-
"""core.chart_grammar —— 图表语法：意图 × 数据形状 → 图型（2026-11-21）。

学的是两家公开体系，不是拍脑袋：

1. Financial Times《Visual Vocabulary》按**意图**分 9 类
   （deviation / correlation / ranking / distribution / change over time /
   part-to-whole / magnitude / spatial / flow），每类写清"什么时候用、怎么用错"。
   https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary
2. From Data to Viz 按**数据格式**分（numeric / categoric / num+cat /
   maps / time series / network），用决策树落到图型并列 caveat。
   https://www.data-to-viz.com/

本模块把两条轴交叉：**先判意图，再判形状，最后在能画的图里选**。
关键词只用来判意图，不用来选图；形状不合的图直接排除
（例如"构成图"必须加总≈100%）。

GRAMMAR 共 100 条，含我们**暂时画不了**的图型（`_UNSUPPORTED`），
它们不是死代码：是"角色该补什么数据"的缺口清单。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:  # 以渲染器实际能力为准，不写死
    from core.report_theme.charts_pro.spec import RENDERERS
except Exception:  # noqa: BLE001
    RENDERERS = {}

INTENT_KEYS: Dict[str, Tuple[str, ...]] = {
    "deviation": ("偏差", "高于", "低于", "剪刀差", "差距", "超额", "缺口",
                  "正负", "增减", "涨跌", "同比", "环比", "vs", "对比于"),
    "correlation": ("相关", "关系", "伴随", "带动", "联动", "正相关", "负相关"),
    "ranking": ("排名", "前五", "前 5", "头部", "集中度", "CR", "梯队", "领跑",
                "第几", "排序", "谁最"),
    "distribution": ("分布", "区间", "中位", "分位", "长尾", "离散", "波动", "极值"),
    "change": ("趋势", "增长", "上升", "下降", "爬坡", "周期", "周", "月", "年",
               "期", "轨迹"),
    "composition": ("构成", "占比", "份额", "结构", "各部分", "拆分"),
    "magnitude": ("规模", "总量", "多少", "亿元", "件", "家", "网点", "体量"),
    "spatial": ("地图", "区域", "城市", "省", "地市", "区县", "分布图"),
    "flow": ("流向", "调拨", "流转", "转化", "漏斗", "链路"),
}

SHAPES = ("series", "category", "signed", "composition", "range",
          "distribution", "matrix", "flow", "single")

# intent, chart, shape, 什么时候用, 常见误用
GRAMMAR: List[Tuple[str, str, str, str, str]] = [
    # ---- deviation（偏差）：相对一个基准的 +/- ----------------------------
    ("deviation", "diverging", "signed", "相对 0 或目标的正负偏离", "不标基准线"),
    ("deviation", "diverging_stacked", "composition", "问卷式赞同/中立/反对", "中性段挤掉两侧"),
    ("deviation", "spine", "signed", "一个值拆成两个对立分量", "两段比例失真"),
    ("deviation", "surplus_line", "series", "盈余/赤字随时间的填充面积", "基线漂移"),
    ("deviation", "baseline_dot", "category", "每个点相对基准的偏移", "基准不一致"),
    ("deviation", "change_column", "signed", "相对上期的增减柱", "正负配色反直觉"),
    # ---- correlation（相关） --------------------------------------------
    ("correlation", "scatter", "category", "两个连续变量找关系", "把相关讲成因果"),
    ("correlation", "bubble", "category", "第三维用面积编码", "面积按半径画（应平方）"),
    ("correlation", "connected_scatter", "series", "两变量的关系随时间移动", "路径交叉看不懂"),
    ("correlation", "line_column", "series", "量（柱）与率（线）同图", "双轴刻度误导"),
    ("correlation", "heatmap", "matrix", "两类目交叉的强弱", "色阶不归一"),
    ("correlation", "correlogram", "matrix", "多变量两两相关", "只给系数不给样本量"),
    ("correlation", "density_2d", "distribution", "点太多时的二维密度", "把密度当概率"),
    ("correlation", "hexbin", "distribution", "超大数据量的分箱", "分箱尺寸掩盖结构"),
    # ---- ranking（排序） -------------------------------------------------
    ("ranking", "dot", "category", "名次比数值重要，3–8 项", "点太密"),
    ("ranking", "lollipop", "category", "要名次也要数值", "杆太长"),
    ("ranking", "pareto", "category", "头部集中度，含其他", "把其他排第一"),
    ("ranking", "hbar", "category", "类目名长、条目多", "轴不从 0 起"),
    ("ranking", "ordered_column", "category", "名次且标签短", "列太多变栅栏"),
    ("ranking", "slope", "series", "名次随时间变化", "只两点也画斜率"),
    ("ranking", "bump", "series", "多主体名次交替", "名次线交叉成毛线"),
    ("ranking", "proportional_symbol", "category", "差距极大、只比量级", "面积难精读"),
    ("ranking", "dot_strip", "distribution", "多类目下摊开个体值", "重复值重叠"),
    # ---- distribution（分布） -------------------------------------------
    ("distribution", "histogram", "distribution", "看形状与偏态", "分箱拍脑袋"),
    ("distribution", "box", "distribution", "多组分布比较", "样本太少也画"),
    ("distribution", "violin", "distribution", "复杂分布、多峰", "小样本形状假"),
    ("distribution", "strip", "distribution", "个体值直接摊开", "点重叠"),
    ("distribution", "beeswarm", "distribution", "避免重叠的散点分布", "点数过多"),
    ("distribution", "ridge", "distribution", "多组分布叠成山脊", "层数太多糊成一片"),
    ("distribution", "density", "distribution", "连续变量的密度曲线", "带宽选择影响结论"),
    ("distribution", "cumulative_curve", "distribution", "看集中度（洛伦兹）", "不标对角线"),
    ("distribution", "barcode", "distribution", "逐条列出所有值", "密集处看不清"),
    ("distribution", "population_pyramid", "matrix", "年龄×性别的背靠背分布", "分组粒度不一致"),
    # ---- change over time（时序） ---------------------------------------
    ("change", "line", "series", "连续时间看趋势", "时间轴不等距"),
    ("change", "area", "series", "总量变化、单系列", "多系列堆叠看不出个体"),
    ("change", "step", "series", "阶梯式变化", "平滑掩盖跳变"),
    ("change", "column", "series", "少数时点的量", "时点太多"),
    ("change", "line_column", "series", "量与率同时看", "双轴"),
    ("change", "slope", "series", "两三个时点的变化", "点多就不适用"),
    ("change", "fan", "series", "预测区间随时间变宽", "把区间当中值"),
    ("change", "calendar_heatmap", "matrix", "日/周/月的周期规律", "精确值读不出"),
    ("change", "priestley", "flow", "起止时间与时长", "时间轴拥挤"),
    ("change", "circle_timeline", "flow", "离散事件的大小与时间", "圆面积难比较"),
    ("change", "seismogram", "series", "波动极大的序列", "基线被噪声吃掉"),
    ("change", "streamgraph", "series", "多系列总量与结构", "读数困难"),
    ("change", "stock", "series", "开高低收", "没有量纲说明"),
    ("change", "connected_scatter", "series", "两变量随时间移动", "路径交叉"),
    # ---- part-to-whole（构成） ------------------------------------------
    ("composition", "share_bar", "composition", "占比且强调结构", "分段 <5%"),
    ("composition", "treemap", "composition", "层级构成、面积即份额", "小块点不出"),
    ("composition", "waffle", "composition", "数格子的占比直觉", "格子不能整除"),
    ("composition", "donut", "composition", "2–3 个大块", "超过 5 块"),
    ("composition", "pie", "composition", "最常见但不精确", "多块难比较"),
    ("composition", "stacked_bar", "composition", "构成随时间/类目变化", "中间段不可比"),
    ("composition", "pct_stacked", "composition", "只比结构不比总量", "总量差异被抹掉"),
    ("composition", "marimekko", "composition", "宽度=总量、高度=结构", "格子太多"),
    ("composition", "sunburst", "composition", "两层以上层级构成", "内圈小到看不见"),
    ("composition", "gridplot", "composition", "百分比用格子铺", "格子数不整除"),
    ("composition", "arc", "composition", "议会式席位构成", "只适合整数席位"),
    ("composition", "voronoi", "composition", "点转面积", "面积难精读"),
    ("composition", "waterfall", "flow", "有增有减的构成", "起终点不闭合"),
    ("composition", "fluid", "composition", "构成随时间的流动", "标签拥挤"),
    # ---- magnitude（量级） ----------------------------------------------
    ("magnitude", "hbar", "category", "比大小、标签长", "轴不从 0"),
    ("magnitude", "vbar", "category", "比大小、项少", "项多就挤"),
    ("magnitude", "kpi", "single", "3–5 个关键数字", "无关数字拼一起"),
    ("magnitude", "range", "range", "给的是区间不是单值", "只画中点"),
    ("magnitude", "dumbbell", "category", "两组值在同一行对比", "差值方向不标"),
    ("magnitude", "bullet", "category", "实际值 vs 目标 vs 区间", "目标线不标数值"),
    ("magnitude", "gauge", "single", "单指标完成度", "表盘过度装饰"),
    ("magnitude", "paired_bar", "category", "两个系列并排", "系列超过 2 个"),
    ("magnitude", "radar", "category", "多维度画像", "轴顺序随意"),
    ("magnitude", "parallel", "matrix", "多维比较", "维度过多"),
    ("magnitude", "isotype", "category", "整数计数、直觉化", "用小数切图"),
    # ---- spatial（空间） -------------------------------------------------
    ("spatial", "choropleth", "matrix", "按行政区着色", "用总量而非比率"),
    ("spatial", "symbol_map", "matrix", "按点位大小编码", "小差异看不出"),
    ("spatial", "flow_map", "flow", "明确的空间移动", "线条交叉"),
    ("spatial", "contour", "matrix", "等值线", "插值过度"),
    ("spatial", "cartogram", "matrix", "面积按值缩放", "地理失真"),
    ("spatial", "dot_density", "distribution", "事件点位密度", "不标注模式"),
    ("spatial", "hexbin_map", "distribution", "网格化密度", "网格尺寸影响结论"),
    # ---- flow（流向） ----------------------------------------------------
    ("flow", "sankey", "flow", "多对多流转", "流量不加总核对"),
    ("flow", "funnel", "flow", "阶段转化", "阶段口径不一致"),
    ("flow", "chord", "matrix", "两两流向", "读不出净流向"),
    ("flow", "network", "matrix", "关系强度", "节点太多成毛球"),
    ("flow", "waterfall", "flow", "过程账（有增有减）", "起终点不闭合"),
    ("flow", "gantt", "flow", "任务与时长", "时间粒度不一致"),
    # ---- 补充批（对齐 100 条；含 data-to-viz 的决策树分支） --------------
    ("distribution", "raincloud", "distribution", "分布 + 个体点 + 箱线三合一", "元素过多"),
    ("distribution", "qq", "distribution", "检验分布是否正态", "样本太少"),
    ("distribution", "lorenz", "distribution", "不平等程度", "不标基尼系数"),
    ("correlation", "pca", "matrix", "多维降维后的聚类", "主成分不可解释"),
    ("correlation", "dendrogram", "matrix", "层次聚类结构", "距离度量不写清"),
    ("change", "spiral", "series", "长周期节律（年/季）", "读不出绝对时间"),
    ("change", "small_mult", "matrix", "多主体同一时间轴对比", "小图太多看不清"),
    ("change", "multi_line", "series", "多系列同时看", "系列超过 4 条"),
    ("change", "area_range", "range", "区间随时间的带状", "上下限来源不明"),
    ("change", "spark_table", "matrix", "表格里嵌迷你趋势", "迷你图没有刻度"),
    ("composition", "venn", "composition", "两个集合的交叠", "面积不按比例"),
    ("composition", "dot_matrix", "matrix", "类目×类目的点阵", "点大小无说明"),
    ("magnitude", "dual_axis", "series", "量 + 率双轴", "两轴不标单位"),
    ("magnitude", "timeline", "flow", "里程碑与时长", "时间轴不等距"),
    ("spatial", "locator", "matrix", "先定位再看数据", "地图喧宾夺主"),
]

# 能画（渲染器里有）与画不了的（缺口清单）
SUPPORTED = {c for _i, c, _s, _w, _c in GRAMMAR if c in RENDERERS}
UNSUPPORTED = sorted({c for _i, c, _s, _w, _c in GRAMMAR if c not in RENDERERS})


def infer_intent(text: str) -> str:
    import re
    t = str(text or "")
    best, hit = "magnitude", 0
    for intent, keys in INTENT_KEYS.items():
        n = sum(1 for k in keys if re.search(k, t))
        if n > hit:
            best, hit = intent, n
    return best


def infer_shape(payload: Dict[str, Any], nums: List[Dict[str, Any]]) -> str:
    n = len(nums)
    if n >= 2:
        periods = {str(x.get("period")) for x in nums if x.get("period")}
        if len(periods) >= 2:
            return "series"
        pct = [x for x in nums if str(x.get("unit")) == "%"]
        if pct and len(pct) == n and any(x["_v"] < 0 for x in pct) and any(x["_v"] > 0 for x in pct):
            return "signed"
        if len(pct) >= 3 and 88 <= sum(x["_v"] for x in pct) <= 112:
            return "composition"
        if any("下限" in str(x.get("name")) for x in nums):
            return "range"
    items = payload.get("bars") or payload.get("items") or payload.get("points") or []
    if items:
        vals = [float(i.get("value", 0)) for i in items]
        if any(v < 0 for v in vals):
            return "signed"
        if 3 <= len(vals) <= 8 and 88 <= sum(vals) <= 112:
            return "composition"
        if len(vals) >= 7 and (max(vals) - min(vals)) > 0.8 * max(vals):
            return "distribution"
        return "category"
    return "single"


def candidates(intent: str, shape: str, n: int, history: List[str]) -> List[str]:
    out = []
    for it, chart, sh, _why, _caveat in GRAMMAR:
        if it != intent or sh != shape:
            continue
        if chart not in RENDERERS:
            continue
        if chart == "pareto" and n < 4:
            continue
        if chart in ("share_bar", "treemap", "waffle", "donut", "pie") and not (2 <= n <= 8):
            continue
        if chart in ("histogram", "box", "violin", "strip", "beeswarm", "ridge") and n < 7:
            continue
        out.append(chart)
    used: Dict[str, int] = {}
    for h in history:
        used[h] = used.get(h, 0) + 1
    return sorted(dict.fromkeys(out), key=lambda c: used.get(c, 0))


def pick(intent: str, shape: str, n: int, history: List[str]) -> Optional[str]:
    cands = candidates(intent, shape, n, history)
    if not cands:
        return None
    for c in cands:
        if history[-2:] != [c, c]:
            return c
    return cands[0]


def explain(intent: str, shape: str, n: int, history: List[str]) -> Dict[str, Any]:
    return {"intent": intent, "shape": shape, "n": n,
            "candidates": candidates(intent, shape, n, history),
            "chosen": pick(intent, shape, n, history)}


def build(chart: Dict[str, Any], section: Dict[str, Any],
          pack: Dict[str, Any], history: List[str]) -> Optional[Dict[str, Any]]:
    from core import chart_shapes

    nums = chart_shapes._nums(pack, list(chart.get("refs") or section.get("refs") or []))
    items = (chart.get("bars") or chart.get("vbars")
             or chart.get("items") or chart.get("points") or [])
    shape = infer_shape(chart, nums)
    text = " ".join(str(x or "") for x in (
        section.get("title"), section.get("question"), chart.get("title")))
    intent = infer_intent(text)
    n = max(len(nums), len(items))
    typ = pick(intent, shape, n, history)
    if not typ:
        return None

    if shape == "series":
        s = chart_shapes._series(nums)
        if not s:
            return None
        if typ in ("line", "area", "step"):
            return {"type": typ, "points": s["points"], "unit_meta": s["unit_meta"]}
        if typ in ("vbar", "hbar", "column"):
            return {"type": "vbar" if typ == "column" else typ,
                    "items": s["points"], "unit_meta": s["unit_meta"]}
        return None

    if shape == "range":
        return chart_shapes._range(nums)

    if shape == "signed":
        sig = chart_shapes._signed(nums)
        return sig or {"type": "diverging", "items": items}

    if shape == "composition":
        comp = chart_shapes._compose(nums) or {"items": items,
                                               "unit_meta": chart.get("unit_meta")}
        base_items = comp.get("items") or []
        if typ in ("treemap", "donut", "waffle", "share_bar", "pie"):
            return {"type": typ, "items": base_items,
                    "unit_meta": comp.get("unit_meta") or "%"}
        return None

    if shape == "category" and items:
        norm = [{"label": str(i.get("label")), "value": float(i.get("value", 0))}
                for i in items]
        if typ in ("dot", "lollipop", "pareto"):
            key = "points" if typ == "dot" else "items"
            return {"type": typ, key: norm}
        if typ in ("hbar", "vbar", "ordered_column"):
            return {"type": "hbar" if typ in ("hbar", "ordered_column") else "vbar",
                    "items": norm}
        return None

    return None

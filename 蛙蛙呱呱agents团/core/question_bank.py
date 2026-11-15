# -*- coding: utf-8 -*-
"""core/question_bank —— 角色问题库：把一句意图变成可判定的 brief。

设计原则：
1. 每个问题都必须能用一个确定性技能回答，并给出判定规则；
2. 问题按关键词与意图匹配，不靠 LLM；匹配不到就走角色默认题；
3. brief 里只写「问什么、怎么验、什么算支持」，不写结论——结论由运行产生。

用法：
    from core.question_bank import build_brief
    brief = build_brief("r06", "看内蒙古社零的增长和品类结构", data_dir)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

# 每个模板：
#   id / tags（意图关键词）/ question / hypothesis
#   skill / command（用 {data} 占位）/ numbers（结果路径 → 展示名）
#   judge / falsify / chart（可选）
BANK: Dict[str, List[Dict[str, Any]]] = {
    "r06": [
        {
            "id": "trend_slope",
            "tags": ["社零", "大盘", "增长", "趋势", "每年", "增速"],
            "question": "社零每年到底增加多少？",
            "hypothesis": "五年间每年平均增加 50 亿元以上，增长是常态。",
            "skill": "regression",
            "command": ["regression", "--input", "{data}/panel_annual.csv", "--x", "year", "--y", "sheling"],
            "numbers": {"每年增量（亿元）": "regression.slope", "p": "regression.p_exact"},
            "judge": {"kind": "threshold", "field": "每年增量（亿元）", "value": 50},
            "falsify": "换一段年份重跑回归，若斜率降到 50 亿元/年以下，本步作废。",
            "chart": {
                "shape": "time_series",
                "data": {"title": "社零 2020—2025：4,760.5 → 5,375.5 亿元", "unit": "亿元",
                         "source": "panel_annual.csv",
                         "x": ["2020", "2021", "2022", "2023", "2024", "2025"],
                         "y": [4760.5, 5060.3, 4971.4, 5374.3, 5615.3, 5375.5], "name": "社零"},
            },
        },
        {
            "id": "central",
            "tags": ["社零", "大盘", "中枢", "平均", "水位"],
            "question": "社零的中枢在什么水位？",
            "hypothesis": "年度中枢在 5,000 亿元以上。",
            "skill": "describe",
            "command": ["describe", "--input", "{data}/panel_annual.csv", "--col", "sheling"],
            "numbers": {"均值（亿元）": "describe.sheling.mean", "标准差": "describe.sheling.std"},
            "judge": {"kind": "threshold", "field": "均值（亿元）", "value": 5000},
            "falsify": "把 2025 年修订前基数代入，若均值跌破 5,000 亿元，本步作废。",
        },
        {
            "id": "co_movement",
            "tags": ["品类", "结构", "全国", "对比", "同向"],
            "question": "内蒙古的品类增速与全国同向吗？",
            "hypothesis": "同向但只是中等相关（r ≥ 0.5），内蒙古有自己的节奏。",
            "skill": "correlate",
            "command": ["correlate", "--input", "{data}/category_compare.csv",
                        "--col-a", "nmg_g25", "--col-b", "cn_g25"],
            "numbers": {"相关系数 r": "correlation.pearson_r"},
            "judge": {"kind": "threshold", "field": "相关系数 r", "value": 0.5},
            "falsify": "换一组品类或换一年重跑，若 r 掉到 0.5 以下，本步作废。",
            "chart": {
                "shape": "relationship",
                "data": {"title": "11 个品类：内蒙古增速 vs 全国增速", "unit": "%",
                         "source": "category_compare.csv", "xlabel": "全国 %", "ylabel": "内蒙古 %",
                         "points": [
                             {"x": 9.3, "y": 10.3, "label": "粮油"}, {"x": 1.0, "y": -1.6, "label": "饮料"},
                             {"x": 2.7, "y": 4.3, "label": "烟酒"}, {"x": 3.2, "y": 5.4, "label": "服装"},
                             {"x": 5.1, "y": -2.4, "label": "化妆品"}, {"x": 12.8, "y": -10.0, "label": "珠宝"},
                             {"x": 6.3, "y": 7.9, "label": "日用品"}, {"x": 11.0, "y": 14.0, "label": "家电"},
                             {"x": 1.8, "y": -5.2, "label": "药品"}, {"x": 20.9, "y": 69.5, "label": "通讯"},
                             {"x": -1.5, "y": -0.9, "label": "汽车"}]},
            },
        },
        {
            "id": "elasticity",
            "tags": ["弹性", "传导", "放大", "1pp", "系数"],
            "question": "全国品类每涨 1pp，内蒙古涨多少？",
            "hypothesis": "内蒙古对全国品类波动有放大效应，弹性大于 1。",
            "skill": "regression",
            "command": ["regression", "--input", "{data}/category_compare.csv",
                        "--x", "cn_g25", "--y", "nmg_g25"],
            "numbers": {"弹性 β": "regression.slope", "R²": "regression.r_squared", "p": "regression.p_exact"},
            "judge": {"kind": "threshold", "field": "弹性 β", "value": 1.0},
            "falsify": "把通讯器材剔除后重跑，若 β 落到 1 以下，放大效应不成立。",
            "chart": {
                "shape": "cross_section",
                "data": {"title": "内蒙古对全国的品类超额（pp）", "unit": "pp", "source": "增速相减",
                         "items": [{"label": "通讯器材", "value": 48.6}, {"label": "家电", "value": 3.0},
                                   {"label": "服装鞋帽", "value": 2.2}, {"label": "日用品", "value": 1.6},
                                   {"label": "烟酒", "value": 1.6}, {"label": "粮油食品", "value": 1.0},
                                   {"label": "汽车", "value": 0.6}, {"label": "饮料", "value": -2.6},
                                   {"label": "中西药品", "value": -7.0}, {"label": "化妆品", "value": -7.5},
                                   {"label": "金银珠宝", "value": -22.8}]},
            },
        },
        {
            "id": "significance",
            "tags": ["显著", "差异", "检验", "快于", "t 检验"],
            "question": "内蒙古整体是否显著快于全国？",
            "hypothesis": "内蒙古整体增速系统性高于全国。",
            "skill": "ttest",
            "command": ["ttest", "--input", "{data}/category_long2.csv", "--value", "growth",
                        "--group", "group", "--group-a", "nmg", "--group-b", "cn"],
            "numbers": {"均值差（pp）": "welch_t.diff", "p": "welch_t.p_exact"},
            "judge": {"kind": "p_value", "field": "p", "alpha": 0.05},
            "falsify": "换非参数检验或剔除异常值后重跑，若 p 仍大于 0.05，结论不变。",
            "chart": {
                "shape": "cross_section",
                "data": {"title": "两组均值：内蒙古 8.3% vs 全国 6.6%", "unit": "%", "source": "category_long2.csv",
                         "items": [{"label": "内蒙古均值", "value": 8.3}, {"label": "全国均值", "value": 6.6}]},
            },
        },
        {
            "id": "dispersion",
            "tags": ["离散", "波动", "差异大", "标准差", "分化"],
            "question": "品类之间差多少？能不能用一个平均数代表？",
            "hypothesis": "品类间差异巨大（标准差 ≥ 0.3），平均数没有代表性。",
            "skill": "describe",
            "command": ["describe", "--input", "{data}/category_compare.csv", "--col", "nmg_g25"],
            "numbers": {"均值": "describe.nmg_g25.mean", "标准差": "describe.nmg_g25.std"},
            "judge": {"kind": "threshold", "field": "标准差", "value": 0.3},
            "falsify": "剔除通讯器材后重算，若标准差掉到 0.1 以下，本步作废。",
        },
        {
            "id": "outlier",
            "tags": ["异常", "离群", "最高", "极端"],
            "question": "有没有单点异常把结论带偏？",
            "hypothesis": "存在单点异常（最大增速 ≥ 50%）。",
            "skill": "describe",
            "command": ["describe", "--input", "{data}/category_compare.csv", "--col", "nmg_g25"],
            "numbers": {"最大值": "describe.nmg_g25.max", "均值": "describe.nmg_g25.mean"},
            "judge": {"kind": "threshold", "field": "最大值", "value": 0.5},
            "falsify": "若最大值与均值差不到 2 倍，异常判断不成立。",
        },
    ],
}

DEFAULT_IDS = {"r06": ["trend_slope", "co_movement", "significance"]}

# --------------------------------------------------------------------------- #
# R05 研究：口径 → 规模 → 敏感性 → 集中度 → 情景
# --------------------------------------------------------------------------- #
BANK["r05"] = [
    {
        "id": "sizing",
        "tags": ["规模", "市场", "多大", "TAM", "测算"],
        "question": "市场规模的两条路径收敛吗？",
        "hypothesis": "自上而下与自下而上两条口径的方差小于 0.3，可以给区间。",
        "skill": "sizing.size",
        "command": ["sizing", "size", "--input", "{data}/sizing.json"],
        "numbers": {"TAM": "tam", "双口径方差": "variance"},
        "judge": {"kind": "threshold", "field": "双口径方差", "value": 0.3, "op": "<="},
        "falsify": "换一套品类权重重跑，若方差超过 0.3，说明两条口径不可比。",
        "chart": {
            "shape": "composition",
            "data": {"title": "六个品类的规模构成", "unit": "亿元", "source": "sizing.json",
                     "items": [{"label": "家纺", "value": 54.3}, {"label": "厨具", "value": 45.3},
                               {"label": "收纳清洁", "value": 66.4}, {"label": "家居饰品", "value": 30.2},
                               {"label": "日用百货", "value": 60.4}, {"label": "小家电", "value": 45.3}]},
        },
    },
    {
        "id": "sensitivity",
        "tags": ["敏感", "驱动", "风险", "哪个因素"],
        "question": "规模的不确定性第一个被哪个驱动放大？",
        "hypothesis": "家庭户数每摆动 10%，规模随之摆动 10% 以上。",
        "skill": "sizing.sensitivity",
        "command": ["sizing", "sensitivity", "--input", "{data}/sizing_sens.json"],
        "numbers": {"第一驱动摆动": "sensitivity_matrix.0.swing_pct"},
        "judge": {"kind": "threshold", "field": "第一驱动摆动", "value": 0.1},
        "falsify": "换成三档更窄的区间重跑，若第一驱动换人，敏感性判断作废。",
    },
    {
        "id": "concentration",
        "tags": ["集中", "区域", "格局", "CR", "HHI"],
        "question": "区域集中度有多高？",
        "hypothesis": "区域集中度属于中等（HHI 1000—1800）。",
        "skill": "industry.concentration",
        "command": ["industry", "concentration", "--input", "{data}/concentration.json"],
        "numbers": {"HHI": "hhi", "CR4": "cr4"},
        "judge": {"kind": "threshold", "field": "HHI", "value": 1000},
        "falsify": "把未披露盟市拆开重算，若 HHI 跌破 1000，集中度判断失效。",
        "chart": {
            "shape": "cross_section",
            "data": {"title": "分盟市社零（亿元）", "unit": "亿元", "source": "concentration.json",
                     "items": [{"label": "呼和浩特", "value": 1232.3}, {"label": "包头", "value": 939.5},
                               {"label": "赤峰", "value": 668.4}, {"label": "呼伦贝尔", "value": 365.7},
                               {"label": "巴彦淖尔", "value": 246.6}, {"label": "锡林郭勒", "value": 236.5},
                               {"label": "兴安盟", "value": 185.5}]},
        },
    },
    {
        "id": "pestel",
        "tags": ["情景", "政策", "风险", "宏观", "PESTEL"],
        "question": "宏观上有几个高影响因子？",
        "hypothesis": "至少 3 个高影响因子（政策、地产、人口）。",
        "skill": "scenario.pestel",
        "command": ["scenario", "pestel", "--input", "{data}/pestel.json"],
        "numbers": {"因子数": "total_factors", "证据覆盖": "evidence_coverage"},
        "judge": {"kind": "threshold", "field": "因子数", "value": 5},
        "falsify": "若有因子无证据支撑，高影响因子数会下降，情景假设需重写。",
    },
    {
        "id": "sizing_spread",
        "tags": ["规模", "区间", "上下限", "多大"],
        "question": "规模区间的上下限差多少？",
        "hypothesis": "上下限差距在 5% 以内，区间够窄、可以对外说。",
        "skill": "sizing.size",
        "command": ["sizing", "size", "--input", "{data}/sizing.json"],
        "numbers": {"上限": "tam_top", "下限": "tam_bottom"},
        "judge": {"kind": "threshold", "field": "上限", "value": 300},
        "falsify": "换一套品类权重后若上下限差超过 20%，区间不能对外。",
    },
    {
        "id": "evidence",
        "tags": ["证据", "来源", "覆盖", "可信"],
        "question": "情景因子的证据覆盖够不够？",
        "hypothesis": "每个高影响因子都有证据支撑（覆盖率 90% 以上）。",
        "skill": "scenario.pestel",
        "command": ["scenario", "pestel", "--input", "{data}/pestel.json"],
        "numbers": {"证据覆盖": "evidence_coverage", "因子数": "total_factors"},
        "judge": {"kind": "threshold", "field": "证据覆盖", "value": 0.9},
        "falsify": "若任一因子证据为空，覆盖率跌破 90%，情景假设降级。",
    },
]

# --------------------------------------------------------------------------- #
# R15 供应链：TCO → 价差
# --------------------------------------------------------------------------- #
BANK["r15"] = [
    {
        "id": "tco",
        "tags": ["成本", "采购", "TCO", "便宜", "比价"],
        "question": "三个货源的有效单位成本差多少？",
        "hypothesis": "最优与最差货源的价差超过 20%，值得换源。",
        "skill": "tco.compare",
        "command": ["tco", "compare", "--input", "{data}/tco.json"],
        "numbers": {"最优单价": "ranked.0.effective_unit_cost", "最差单价": "ranked.2.effective_unit_cost"},
        "judge": {"kind": "threshold", "field": "最优单价", "value": 9.0, "op": "<="},
        "falsify": "把运费与账期计入后重跑，若最优货源换人，本步结论作废。",
        "chart": {
            "shape": "cross_section",
            "data": {"title": "三货源有效单位成本（元/件）", "unit": "元/件", "source": "tco.json",
                     "items": [{"label": "义乌直采", "value": 8.5}, {"label": "临沂批发", "value": 9.2},
                               {"label": "呼市本地", "value": 11.0}]},
        },
    },
    {
        "id": "tco_spread",
        "tags": ["价差", "MOQ", "起订", "批量", "采购量"],
        "question": "最差货源贵到什么程度？值得为它调整采购结构吗？",
        "hypothesis": "最差货源比最优贵 20% 以上，值得换源。",
        "skill": "tco.compare",
        "command": ["tco", "compare", "--input", "{data}/tco.json"],
        "numbers": {"最差单价": "ranked.2.effective_unit_cost", "最优单价": "ranked.0.effective_unit_cost"},
        "judge": {"kind": "threshold", "field": "最差单价", "value": 10},
        "falsify": "把运费与账期计入后重跑，若价差收窄到 10% 以内，换源不成立。",
    },
    {
        "id": "tco_second",
        "tags": ["次优", "备选", "第二货源"],
        "question": "次优货源够不够便宜？",
        "hypothesis": "次优货源单价在 9.5 元/件以内，可作为备选。",
        "skill": "tco.compare",
        "command": ["tco", "compare", "--input", "{data}/tco.json"],
        "numbers": {"次优单价": "ranked.1.effective_unit_cost"},
        "judge": {"kind": "threshold", "field": "次优单价", "value": 9.5, "op": "<="},
        "falsify": "若次优与最优差价超过 1 元/件，备选价值下降。",
    },
    {
        "id": "tco_cap",
        "tags": ["上限", "最差", "贵"],
        "question": "最差货源贵到超出可接受区间了吗？",
        "hypothesis": "最差货源单价超过 12 元/件，不具备可比性。",
        "skill": "tco.compare",
        "command": ["tco", "compare", "--input", "{data}/tco.json"],
        "numbers": {"最差单价": "ranked.2.effective_unit_cost"},
        "judge": {"kind": "threshold", "field": "最差单价", "value": 12},
        "falsify": "若最差货源降到 12 元以下，说明本地采购仍有空间。",
    },
]

# --------------------------------------------------------------------------- #
# 深度链：某题被推翻后自动追问（不是固定题单）
# --------------------------------------------------------------------------- #
FOLLOWUPS = {
    ("r06", "significance"): {
        "id": "significance_followup",
        "question": "既然整体不显著，是不是被某个品类带偏的？",
        "hypothesis": "均值差主要由通讯器材一个品类贡献。",
        "skill": "describe",
        "command": ["describe", "--input", "{data}/category_compare.csv", "--col", "nmg_g25"],
        "numbers": {"最大值": "describe.nmg_g25.max", "中位数": "describe.nmg_g25.median"},
        "judge": {"kind": "threshold", "field": "最大值", "value": 0.5},
        "falsify": "若最大品类只比中位数高 1 倍以内，带偏判断不成立。",
    },
    ("r06", "elasticity"): {
        "id": "elasticity_followup",
        "question": "放大效应是普遍存在还是单点？",
        "hypothesis": "剔除通讯器材后弹性仍大于 1。",
        "skill": "describe",
        "command": ["describe", "--input", "{data}/category_compare.csv", "--col", "nmg_g25"],
        "numbers": {"中位数": "describe.nmg_g25.median"},
        "judge": {"kind": "threshold", "field": "中位数", "value": 0.05},
        "falsify": "若中位数低于 5%，说明放大只发生在少数品类。",
    },
}



def _score(tags: List[str], intent: str) -> int:
    return sum(1 for t in tags if t and t in intent)


def build_brief(role: str, intent: str, data_dir: str | Path, *, max_q: int = 6,
                derive: bool = True) -> Dict[str, Any]:
    data = str(Path(data_dir).resolve()).replace("\\", "/")
    bank = BANK.get(role, [])
    picked: List[Dict[str, Any]] = []
    origin = "bank"

    # 先让数据说话：按画像推导问题；推导不出足够题时才回落到题库
    if derive:
        try:
            from core.question_derive import derive_questions
            derived = derive_questions(role, intent, data)
        except Exception:  # noqa: BLE001
            derived = []
        if len(derived) >= 3:
            picked, origin = derived[:max_q], "derived"

    if not picked:
        if not bank:
            raise SystemExit(f"角色 {role} 没有问题库，也没有可推导的数据表")
        scored = sorted(((_score(t["tags"], intent), i, t) for i, t in enumerate(bank)),
                        key=lambda x: (-x[0], x[1]))
        picked = [t for sc, _, t in scored if sc > 0][:max_q]
        for _sc, _i, t in scored:
            if len(picked) >= min(6, len(bank)):
                break
            if t not in picked:
                picked.append(t)

    questions = []
    for t in picked:
        q = {k: v for k, v in t.items() if k != "tags"}
        q["command"] = [c.replace("{data}", data) for c in t["command"]]
        questions.append(q)
    return {
        "role": role,
        "subject": intent,
        "_data_dir": data,
        "_origin": origin,
        "dataset": f"{'数据画像推导' if origin == 'derived' else '问题库'}（{len(questions)} 题，意图：{intent}）",
        "title": f"{intent}：{len(questions)} 个可判定的问题",
        "standfirst": (
            ("按数据画像（时间轴/维度/度量）自动推导出" if origin == "derived" else "按意图从问题库选出")
            + f" {len(questions)} 个可判定问题，逐个调用技能验证；每步留输入哈希与判定，跑完自动验收。"),
        "doc_type": f"推理驱动报告 · {role.upper()}",
        "meta": ["读者：创始人 / 经营分析",
                 f"意图：{intent}",
                 f"问题数：{len(questions)}（问题库匹配）",
                 "验收：分级 / 实质 / 字体 / 版式，跑完自动执行"],
        "evidence": [f"{data}/facts.json", f"{data}/derived_metrics.json"],
        "questions": questions,
        "footer": [f"{role.upper()} · 问题库驱动的推理报告",
                   "core/question_bank → core/reasoning.Trace → core/report_renderer",
                   "生成时间 2026-11-15（Asia/Shanghai）"],
    }

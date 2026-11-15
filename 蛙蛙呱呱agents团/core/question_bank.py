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


def _score(tags: List[str], intent: str) -> int:
    return sum(1 for t in tags if t and t in intent)


def build_brief(role: str, intent: str, data_dir: str | Path, *, max_q: int = 6) -> Dict[str, Any]:
    data = str(Path(data_dir).resolve()).replace("\\", "/")
    bank = BANK.get(role)
    if not bank:
        raise SystemExit(f"角色 {role} 还没有问题库，先在 core/question_bank.py 里加")
    scored = sorted((( _score(t["tags"], intent), i, t) for i, t in enumerate(bank)),
                    key=lambda x: (-x[0], x[1]))
    picked = [t for sc, _, t in scored if sc > 0][:max_q]
    # 命中不足 5 题时，按问题库顺序补齐：宁可多问一题，也不交一份问不全的报告
    for _sc, _i, t in scored:
        if len(picked) >= min(6, len(bank)):
            break
        if t not in picked:
            picked.append(t)
    questions = []
    for t in picked:
        q = {k: v for k, v in t.items() if k not in ("id", "tags")}
        q["command"] = [c.replace("{data}", data) for c in t["command"]]
        questions.append(q)
    return {
        "role": role,
        "subject": intent,
        "dataset": f"问题库自动生成（{len(questions)} 题，命中意图：{intent}）",
        "title": f"{intent}：{len(questions)} 个可判定的问题",
        "standfirst": f"按意图「{intent}」从 R06 问题库选了 {len(questions)} 个可判定问题，逐个调用技能验证；"
                      "每步留下输入哈希与判定，跑完自动验收。",
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

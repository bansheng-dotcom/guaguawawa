# -*- coding: utf-8 -*-
"""把 12 题种子扩到 20 题（幂等：按 id 去重）。"""
from __future__ import annotations

import json
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "evals" / "consulting" / "tasks.json"

NEW = [
    {"id": "Q13", "domain": "供应链中断",
     "question": "单一供应商突然断供，2 周内怎么保供？",
     "must_answer": ["影响面与库存天数", "替代货源", "切换成本与质量风险", "客户分级", "应急与长期方案"],
     "common_errors": ["只找替代不评估质量", "不给客户分级", "忽略切换成本", "无复盘"],
     "gold_points": ["按 SKU/客户分级保供", "替代货源做小批验证", "写明断供根因与长期双源"]},
    {"id": "Q14", "domain": "区域扩张",
     "question": "呼市跑通了，要不要进包头/鄂尔多斯？",
     "must_answer": ["两地需求与竞争", "复制成本", "物流与履约", "组织能力", "进入方式与节奏"],
     "common_errors": ["把呼市数据直接外推", "忽略距离/履约成本", "一次进两个城市", "无退出条件"],
     "gold_points": ["单城试点 + 对照", "算清单城经济模型", "明确复制前提", "写退出条件"]},
    {"id": "Q15", "domain": "品牌升级",
     "question": "区域品牌要不要升级为全国品牌？",
     "must_answer": ["品牌资产现状", "目标人群", "投入与回收", "渠道匹配", "风险"],
     "common_errors": ["只换视觉不改产品", "预算拍脑袋", "忽略渠道", "无阶段目标"],
     "gold_points": ["先做区域心智验证", "分阶段投入", "定义品牌指标", "写止损"]},
    {"id": "Q16", "domain": "组织设计",
     "question": "采购应该集中还是分散到各业务线？",
     "must_answer": ["采购品类与规模", "集中/分散的利弊", "决策速度", "合规与腐败风险", "过渡方案"],
     "common_errors": ["一刀切", "忽略品类差异", "不算沟通成本", "无过渡"],
     "gold_points": ["按品类分层（战略/杠杆/瓶颈/常规）", "先集中标品", "保留业务线执行权", "设过渡期"]},
    {"id": "Q17", "domain": "数据资产",
     "question": "内部数据要不要产品化对外卖？",
     "must_answer": ["数据独特性", "合规与隐私", "客户与场景", "定价与交付", "投入与风险"],
     "common_errors": ["有数据就卖", "忽略合规", "无交付能力", "低估维护"],
     "gold_points": ["先做 3 个客户验证", "合规定级", "按 API/报告交付", "写数据质量 SLA"]},
    {"id": "Q18", "domain": "客户分层",
     "question": "20% 客户贡献 80% 收入，怎么经营？",
     "must_answer": ["分层标准", "各层价值与成本", "服务策略", "流失风险", "度量"],
     "common_errors": ["只按收入分层", "大客户过度服务", "忽略中小客户", "无健康分"],
     "gold_points": ["收入×增长×战略价值三维分层", "差异化服务", "健康分监控", "资源上限"]},
    {"id": "Q19", "domain": "价格战",
     "question": "对手低价冲击，跟不跟？",
     "must_answer": ["对手成本与动机", "自身成本位置", "客户转换成本", "非价格手段", "情景损益"],
     "common_errors": ["情绪化跟价", "假设对手长期亏", "忽略品牌", "不做情景"],
     "gold_points": ["判断是清库存还是抢份额", "算跟价损失", "设计非价格回应", "设观察窗口"]},
    {"id": "Q20", "domain": "年度预算",
     "question": "明年预算：要增长还是要利润？",
     "must_answer": ["增长与利润的取舍", "投入产出", "现金约束", "情景", "考核指标"],
     "common_errors": ["两个都要", "预算按去年加百分比", "忽略现金", "无情景"],
     "gold_points": ["给出增长/利润两套预算", "标出翻转点", "现金约束", "分季考核"]},
]


def main() -> None:
    data = json.loads(P.read_text(encoding="utf-8"))
    have = {t["id"] for t in data["tasks"]}
    added = 0
    for t in NEW:
        if t["id"] not in have:
            data["tasks"].append(t)
            added += 1
    data["note"] = "20 题金题；含必答要点、常见错误、金标准要点。正式评分需人工标注 10 题校准 LLM judge。"
    P.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"added {added}，total {len(data['tasks'])}")


if __name__ == "__main__":
    main()

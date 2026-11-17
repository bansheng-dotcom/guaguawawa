# -*- coding: utf-8 -*-
"""core/question_library —— 20 角色的问题库（升级 P2）。

这不是“22 个报告纲领”的替代分类学，而是**输入分类学**：
每个角色回答 3—5 个它能回答的问题；报告是这些问题被回答后的视图。

字段：
    id           q.<role>.<suffix>
    role         主责角色
    text         问题（写进 M1 问题树）
    capability   所需能力 key（与 capability_graph / coverage 对齐）
    group        最近的 MECE 组（demand / supply / competition / finance / risk）
    dimension    对应 report_framework.DIMENSIONS 的 key；None = v9 还没有这个维度
    primary      是否该角色的核心问题
    providers    能回答该问题的角色（可跨角色）
    needs        所需能力（默认 [capability]）
    evidence     典型证据
"""
from __future__ import annotations

from typing import Any, Dict, List

# 问题模板：(suffix, text, capability, primary, providers)
ROLE_QUESTIONS: Dict[str, List[tuple]] = {
    "r01": [
        ("decision", "这件事该不该做、可逆性如何、谁签字？", "decision.frame", True, ["r01", "r03", "r04"]),
        ("portfolio", "业务组合的优先级与资源分配是什么？", "strategy.portfolio", True, ["r01", "r03"]),
        ("org", "组织与关键岗位是否匹配目标？", "org.design", False, ["r01", "r16"]),
        ("risk", "最大的不可逆风险是什么？", "risk.irreversible", False, ["r01", "r03", "r04"]),
    ],
    "r02": [
        ("capacity", "现有产能能否支撑目标，瓶颈在哪？", "delivery.capacity", True, ["r02", "r01"]),
        ("controls", "关键流程的控制点与验收口是什么？", "process.controls", True, ["r02", "r04"]),
        ("handoff", "跨角色交接的依赖与失败点在哪？", "process.handoff", False, ["r02", "r04"]),
        ("cadence", "排期与节奏是否可行？", "delivery.cadence", False, ["r02", "r01"]),
    ],
    "r03": [
        ("recon", "三表是否勾稽，差异在哪？", "finance.recon", True, ["r03", "r06"]),
        ("cash", "现金 runway 与资金缺口？", "finance.cash", True, ["r03", "r06"]),
        ("tax", "税务与合规红线？", "compliance.tax", False, ["r03", "r04"]),
        ("contract", "合同条款的财务风险？", "compliance.contract", False, ["r03", "r04"]),
    ],
    "r04": [
        ("evidence", "证据链是否完整、可回溯？", "review.evidence", True, ["r04"]),
        ("gate", "门禁是否真的执行？", "review.gate", True, ["r04"]),
        ("independence", "评审是否独立于生产者？", "review.independence", False, ["r04"]),
        ("verdict", "PASS/FAIL/BLOCKED 的裁决依据？", "review.verdict", False, ["r04"]),
    ],
    "r05": [
        ("sources", "来源等级与覆盖够不够？", "research.sources", True, ["r05"]),
        ("size", "市场规模/空间有多大？", "market.size", True, ["r05", "r06"]),
        ("landscape", "竞争格局与玩家位置？", "competition.landscape", False, ["r05", "r06"]),
        ("scenario", "关键情景与假设是什么？", "research.scenario", False, ["r05", "r03"]),
    ],
    "r06": [
        ("trend", "趋势/结构/节奏怎么变？", "market.trend", True, ["r06", "r05"]),
        ("structure", "品类/区域/渠道结构怎么分化？", "market.structure", True, ["r06", "r05"]),
        ("momentum", "环比与同比矛盾时信谁？", "market.momentum", False, ["r06"]),
        ("trajectory", "这是趋势还是噪声？", "market.trajectory", False, ["r06"]),
        ("contribution", "净差小是不是没变化？", "market.contribution", False, ["r06"]),
    ],
    "r07": [
        ("problem", "用户问题与需求优先级？", "product.problem", True, ["r07", "r05"]),
        ("prd", "P0 功能与验收标准？", "product.prd", True, ["r07"]),
        ("opportunity", "机会大小与切入点是哪？", "product.opportunity", False, ["r07", "r05"]),
        ("risk", "做错/不做的代价？", "product.risk", False, ["r07", "r04"]),
    ],
    "r08": [
        ("slice", "最小切片是什么，杀死标准？", "mvp.slice", True, ["r08"]),
        ("prototype", "原型能否验证核心假设？", "mvp.prototype", False, ["r08"]),
        ("launch", "上线路径与埋点？", "mvp.launch", False, ["r08", "r09"]),
        ("learning", "验证后学到什么？", "mvp.learning", False, ["r08"]),
    ],
    "r09": [
        ("spec", "技术规格与模块边界？", "tech.spec", True, ["r09"]),
        ("test", "测试覆盖与关键路径？", "tech.test", True, ["r09"]),
        ("rollback", "发布/回滚方案？", "tech.rollback", False, ["r09", "r20"]),
        ("debt", "技术债与维护成本？", "tech.debt", False, ["r09", "r03"]),
    ],
    "r10": [
        ("brand", "品牌/视觉一致性？", "brand.consistency", True, ["r10", "r11"]),
        ("tokens", "设计令牌与组件？", "brand.tokens", False, ["r10"]),
        ("usability", "信息层级与可用性？", "design.usability", False, ["r10", "r07"]),
        ("production", "物料交付规格？", "brand.production", False, ["r10", "r11"]),
    ],
    "r11": [
        ("audience", "受众与选题？", "content.audience", True, ["r11", "r05"]),
        ("structure", "长文/笔记结构？", "content.structure", True, ["r11"]),
        ("voice", "品牌语调一致性？", "content.voice", False, ["r11", "r10"]),
        ("performance", "内容效果怎么衡量？", "content.performance", False, ["r11", "r12"]),
    ],
    "r12": [
        ("funnel", "增长卡在获客/转化/留存？", "growth.funnel", True, ["r12", "r06"]),
        ("channel", "渠道 ROI 与预算分配？", "channel.roi", True, ["r12", "r06"]),
        ("experiment", "A/B 实验设计与显著性？", "growth.experiment", False, ["r12", "r06"]),
        ("retention", "留存/复购/生命周期？", "growth.retention", False, ["r12", "r06"]),
    ],
    "r13": [
        ("health", "客户健康分与续约风险？", "customer.health", True, ["r13", "r06"]),
        ("voc", "VOC/工单的主要问题？", "customer.voc", True, ["r13"]),
        ("pipeline", "商机与交付进度？", "customer.pipeline", False, ["r13", "r14"]),
        ("escalation", "哪些客户要升级处理？", "customer.escalation", False, ["r13", "r04"]),
    ],
    "r14": [
        ("order", "订单三态是否一致？", "commerce.order", True, ["r14", "r15"]),
        ("payment", "支付/退款/对账差异？", "commerce.payment", True, ["r14", "r03"]),
        ("fulfillment", "履约成功率与瓶颈？", "commerce.fulfillment", False, ["r14", "r15"]),
        ("sku", "商品结构与定价？", "commerce.sku", False, ["r14", "r15"]),
    ],
    "r15": [
        ("tco", "总拥有成本（TCO）哪家低？", "supply.tco", True, ["r15", "r03"]),
        ("quote", "报价/MOQ/关税是否可比？", "supply.quote", True, ["r15", "r03"]),
        ("inventory", "库存周转与缺货风险？", "supply.inventory", False, ["r15", "r14"]),
        ("chain", "链路断点与传导？", "supply.chain", False, ["r15", "r06"]),
    ],
    "r16": [
        ("recruit", "招聘漏斗与达标率？", "people.recruit", True, ["r16"]),
        ("capacity", "编制与人效？", "people.capacity", True, ["r16", "r02"]),
        ("comp", "薪酬带宽与公平性？", "people.comp", False, ["r16", "r03"]),
        ("risk", "关键岗位流失风险？", "people.risk", False, ["r16", "r01"]),
    ],
    "r17": [
        ("contract", "系统集成与接口契约？", "integration.contract", True, ["r17", "r09"]),
        ("webhook", "回调/重试/死信是否可靠？", "integration.webhook", True, ["r17"]),
        ("workflow", "自动化流程覆盖率？", "integration.workflow", False, ["r17", "r02"]),
        ("audit", "审计日志与权限？", "integration.audit", False, ["r17", "r04"]),
    ],
    "r18": [
        ("pipeline", "管道/DAG 是否可靠？", "data.pipeline", True, ["r18"]),
        ("quality", "数据质量六维？", "data.quality6", True, ["r18", "r06"]),
        ("lineage", "血缘与口径来源？", "data.lineage", False, ["r18"]),
        ("catalog", "数据资产目录？", "data.catalog", False, ["r18"]),
    ],
    "r19": [
        ("eval", "模型评测集与评分器？", "model.eval", True, ["r19", "r06"]),
        ("regression", "新旧模型回归对比？", "model.regression", True, ["r19"]),
        ("release", "发布门禁与监控？", "model.release", False, ["r19", "r20"]),
        ("card", "模型卡与边界？", "model.card", False, ["r19", "r04"]),
    ],
    "r20": [
        ("slo", "SLO/可用性达标吗？", "reliability.slo", True, ["r20"]),
        ("incident", "故障/MTTR/升级路径？", "reliability.incident", True, ["r20", "r02"]),
        ("backup", "备份/恢复演练 RTO/RPO？", "reliability.backup", False, ["r20"]),
        ("postmortem", "复盘根因与改进？", "reliability.postmortem", False, ["r20", "r02"]),
    ],
}

# 最近的 MECE 组（v9 只有 5 组；org/tech/reliability 等先并入 risk/execution）
GROUP_BY_PREFIX: Dict[str, str] = {
    "decision": "risk", "strategy": "finance", "org": "risk", "risk": "risk",
    "delivery": "risk", "process": "risk",
    "finance": "finance", "compliance": "risk", "review": "risk",
    "research": "demand", "market": "demand", "competition": "competition",
    "data": "risk", "product": "competition", "mvp": "risk",
    "tech": "risk", "brand": "competition", "design": "competition",
    "content": "competition", "growth": "demand", "channel": "competition",
    "customer": "demand", "commerce": "supply", "supply": "supply",
    "people": "finance", "integration": "risk",
    "model": "risk", "reliability": "risk",
}

# v9 维度映射：只映射清楚的；None = v9 还没有这个维度（P4 扩）
DIMENSION_BY_CAPABILITY: Dict[str, str] = {
    "market.size": "market_size",
    "market.trend": "growth",
    "market.momentum": "growth",
    "market.trajectory": "growth",
    "market.structure": "demand_structure",
    "market.contribution": "price",
    "competition.landscape": "competition",
    "product.problem": "product",
    "product.prd": "product",
    "product.opportunity": "product",
    "channel.roi": "channel",
    "content.performance": "channel",
    "growth.funnel": "growth",
    "growth.retention": "customer",
    "customer.health": "customer",
    "customer.voc": "customer",
    "finance.recon": "unit_economics",
    "finance.cash": "capital_return",
    "supply.tco": "cost",
    "supply.quote": "cost",
    "supply.inventory": "store_ops",
    "supply.chain": "chain",
    "commerce.fulfillment": "store_ops",
    "commerce.sku": "product",
    "reliability.slo": "risk",
    "reliability.incident": "risk",
    "risk.irreversible": "risk",
    "decision.frame": "risk",
    "review.evidence": "risk",
    "review.gate": "risk",
    "data.pipeline": "risk",
    "data.quality6": "risk",
    "model.eval": "risk",
    "model.regression": "risk",
}

EVIDENCE_BY_PREFIX: Dict[str, str] = {
    "decision": "决策卡 / 可逆性分级 / 签字",
    "strategy": "组合 / 预算 / 资源表",
    "org": "组织图 / 岗位 / 编制",
    "risk": "风险清单 / 证伪条件",
    "delivery": "排期 / 容量 / 验收口",
    "process": "SOP / 控制点 / 交接包",
    "finance": "三表 / 凭证 / 现金台账",
    "compliance": "合同 / 税务 / 红线清单",
    "review": "证据链 / 门禁 / 裁决",
    "research": "来源分级 / 研究台账",
    "market": "价格 / 销量 / 份额数据",
    "competition": "CR/HHI / 玩家表",
    "data": "数据集 / 血缘 / 质量报告",
    "product": "VOC / 需求池 / PRD",
    "mvp": "原型 / 埋点 / 杀死标准",
    "tech": "规格 / 测试 / diff",
    "brand": "令牌 / 对比度 / 截图",
    "design": "信息架构 / 可用性测试",
    "content": "选题 / 稿件 / 发布数据",
    "growth": "漏斗 / 实验 / 留存",
    "channel": "渠道 / ROI / 预算",
    "customer": "CRM / 工单 / NPS",
    "commerce": "订单 / 支付 / 对账",
    "supply": "报价 / MOQ / 库存 / TCO",
    "people": "评分卡 / 编制 / 薪酬",
    "integration": "接口 / 重试 / 死信",
    "model": "评测集 / 评分器 / 回归",
    "reliability": "SLO / 告警 / 演练",
}


def build() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for role, rows in ROLE_QUESTIONS.items():
        for suffix, text, cap, primary, providers in rows:
            prefix = cap.split(".")[0]
            out.append({
                "id": f"q.{role}.{suffix}",
                "role": role,
                "text": text,
                "capability": cap,
                "group": GROUP_BY_PREFIX.get(prefix, "risk"),
                "dimension": DIMENSION_BY_CAPABILITY.get(cap),
                "primary": bool(primary),
                "providers": list(providers),
                "needs": [cap],
                "evidence": EVIDENCE_BY_PREFIX.get(prefix, ""),
            })
    return out


QUESTIONS: List[Dict[str, Any]] = build()


def by_role(role: str) -> List[Dict[str, Any]]:
    return [q for q in QUESTIONS if q["role"] == role]


def by_capability(cap: str) -> List[Dict[str, Any]]:
    return [q for q in QUESTIONS if q["capability"] == cap]


def summary() -> Dict[str, Any]:
    roles = sorted(ROLE_QUESTIONS)
    caps = {q["capability"] for q in QUESTIONS}
    return {
        "schema": "dsh.question_library/v1",
        "roles": len(roles),
        "questions": len(QUESTIONS),
        "capabilities": len(caps),
        "primary": sum(1 for q in QUESTIONS if q["primary"]),
        "without_v9_dimension": sorted({q["capability"] for q in QUESTIONS if not q["dimension"]}),
        "by_role": {r: len(by_role(r)) for r in roles},
        "by_group": {g: sum(1 for q in QUESTIONS if q["group"] == g)
                     for g in sorted({q["group"] for q in QUESTIONS})},
    }

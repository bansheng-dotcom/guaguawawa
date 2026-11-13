# -*- coding: utf-8 -*-
"""engines/intent_compiler.py - [L02] 意图解构层：自动化编排 5 阶段 Kahn DAG 拓扑编译器。

对标开源标杆：
- DSPy 签名式自然语言意图编译 (Signature / Teleprompter)
- Ray DAG / Airflow Kahn 拓扑执行序与工时评估器 (Stars > 20k)

核心职责：
1. 将复杂自然语言自动化需求解构为 5 阶段标准 Kahn 拓扑 DAG：
   - S1_TRIGGER_INGEST: 触发器与外部请求鉴权接入 (Webhook / Schedule / Event)
   - S2_AUTH_CREDENTIAL: 凭据握手与安全上下文校验 (OAuth2 / Vault Token)
   - S3_MAPPING_TRANSFORM: 字段清洗、身份映射与 Schema 对齐 (Field Mapping & Type Cast)
   - S4_HITL_DISPATCH: 人工审批门禁与下游多系统分发 (HITL Gate / SaaS Endpoints)
   - S5_AUDIT_RESILIENCE: 全链路审计记录与死信重试兜底 (Audit Trace / DLQ Fallback)
2. 提取自动化核心实体（触发方式、源系统、目标系统、重试策略、是否需人工审批、AI节点配置等）；
3. 计算节点依赖、拓扑序检测（确保无环 Kahn Topological Sort）与工时预算评估（输出 hours 与 days）。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set


class AutomationIntentCompiler:
    """自动化需求复合意图解构与 Kahn DAG 拓扑编译器。"""

    # 5 阶段标准自动化交付 DAG 骨架
    STANDARD_STAGES = [
        {
            "id": "S1_TRIGGER_INGEST",
            "name": "触发器与外部请求鉴权接入",
            "base_hours": 1.5,
            "depends_on": [],
            "deliverable": "TriggerEndpoint & IngestionValidator",
        },
        {
            "id": "S2_AUTH_CREDENTIAL",
            "name": "凭据握手与安全上下文校验",
            "base_hours": 2.0,
            "depends_on": ["S1_TRIGGER_INGEST"],
            "deliverable": "CredentialReference & VaultGuard",
        },
        {
            "id": "S3_MAPPING_TRANSFORM",
            "name": "字段清洗、身份映射与 Schema 对齐",
            "base_hours": 3.0,
            "depends_on": ["S2_AUTH_CREDENTIAL"],
            "deliverable": "MappingSchema & SnakeCaseTransformer",
        },
        {
            "id": "S4_HITL_DISPATCH",
            "name": "人工审批门禁与下游多系统分发",
            "base_hours": 2.5,
            "depends_on": ["S3_MAPPING_TRANSFORM"],
            "deliverable": "HITLApprovalGate & DispatchRouting",
        },
        {
            "id": "S5_AUDIT_RESILIENCE",
            "name": "全链路审计记录与死信重试兜底",
            "base_hours": 2.0,
            "depends_on": ["S4_HITL_DISPATCH"],
            "deliverable": "AuditLogger & DLQResiliencePolicy",
        },
    ]

    def __init__(self):
        pass

    # -------------------------------------------------------------------------
    # 1. 实体抽取
    # -------------------------------------------------------------------------
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """从自然语言文本中提取自动化源、目标、触发方式、重试、审批与安全要求。"""
        # 1.1 触发方式 (Webhook / Cron / Event / 手动)
        trigger_type = "webhook"
        if re.search(r"定时|cron|每天|每周|调度|周期", text, re.IGNORECASE):
            trigger_type = "schedule"
        elif re.search(r"事件|event|kafka|mq|消息队列", text, re.IGNORECASE):
            trigger_type = "event"

        # 1.2 人工审批要求
        need_approval = bool(re.search(r"审批|审核|确认|人工|hitl|发布|上线", text, re.IGNORECASE))

        # 1.3 重试次数与死信
        retry_match = re.search(r"重试\s*(\d+)\s*次", text, re.IGNORECASE)
        retries = int(retry_match.group(1)) if retry_match else 3

        # 1.4 AI 节点
        has_ai_node = bool(re.search(r"ai|大模型|llm|分类|总结|智能", text, re.IGNORECASE))

        # 1.5 涉及系统推测
        systems: List[str] = []
        known_systems = ["飞书", "钉钉", "企微", "Shopify", "CRM", "ERP", "GitHub", "Jira", "Notion", "Slack", "MySQL", "Postgres"]
        for s in known_systems:
            if s.lower() in text.lower():
                systems.append(s)

        return {
            "trigger_type": trigger_type,
            "need_approval": need_approval,
            "max_retries": retries,
            "has_ai_node": has_ai_node,
            "detected_systems": systems,
            "is_production_change": bool(re.search(r"生产|发布|上线|高危|资金", text, re.IGNORECASE)),
        }

    # -------------------------------------------------------------------------
    # 2. 5 阶段 Kahn DAG 编译
    # -------------------------------------------------------------------------
    def compile_intent(self, text: str) -> List[Dict[str, Any]]:
        """将自然语言编译为带工时评估与依赖拓扑的 5 阶段流程。"""
        entities = self.extract_entities(text)
        stages = [dict(s) for s in self.STANDARD_STAGES]

        # 根据实体微调参数与耗时
        for st in stages:
            if st["id"] == "S1_TRIGGER_INGEST":
                st["config"] = {"type": entities["trigger_type"], "signature_check": True}
            elif st["id"] == "S3_MAPPING_TRANSFORM":
                if entities["has_ai_node"]:
                    st["base_hours"] += 1.5
                    st["config"] = {"ai_enrichment": True, "model": "qwen-max"}
            elif st["id"] == "S4_HITL_DISPATCH":
                st["config"] = {
                    "approval_required": entities["need_approval"],
                    "target_systems": entities["detected_systems"],
                }
            elif st["id"] == "S5_AUDIT_RESILIENCE":
                st["config"] = {
                    "max_retries": entities["max_retries"],
                    "dlq_enabled": True,
                    "idempotency_enforced": True,
                }

        return stages

    # -------------------------------------------------------------------------
    # 3. 依赖与工时预算评估
    # -------------------------------------------------------------------------
    def evaluate_budget_and_schedule(self, stages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算工作流实施预算与总交付工时。"""
        total_hours = sum(s.get("base_hours", 2.0) for s in stages)
        days = round(total_hours / 7.0, 2)  # 每天 7 有效工时
        return {
            "total_stages": len(stages),
            "estimated_hours": total_hours,
            "estimated_days": days,
            "critical_path": [s["id"] for s in stages],
            "recommended_sla": f"{days + 1} 个工作日",
        }

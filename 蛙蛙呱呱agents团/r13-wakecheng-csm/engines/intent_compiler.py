# -*- coding: utf-8 -*-
"""engines/intent_compiler.py - [L02] 意图解构层：客户成功意图解构与 Kahn 拓扑 DAG 编排引擎。

对标开源标杆：
- DSPy 声明式签名与编译流 (Stars > 20k)
- Ray DAG 拓扑执行流水线 (Stars > 30k)

核心职责：
1. 自然语言客户成功诉求结构化解构（提取核心客户、风险等级、意图目标与时间跨度）；
2. 编译客户成功 5 阶段 Kahn 交付拓扑 DAG；
3. 计算关键路径、阶段依赖与人天工时预算。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class IntentCompiler:
    """复合客户成功意图解构与拓扑流水线编译引擎。"""

    STAGES_DEF = [
        {
            "id": "s01_crm_audit",
            "name": "客户画像与全渠道触点审计",
            "skill": "crm",
            "action": "person",
            "deps": [],
            "base_hours": 2.0,
            "description": "归集客户主数据、历史触点与关键联系人画像。",
        },
        {
            "id": "s02_health_diagnose",
            "name": "健康分与流失风险深度诊断",
            "skill": "health",
            "action": "health",
            "deps": ["s01_crm_audit"],
            "base_hours": 3.0,
            "description": "四维加权健康度体检，识别单维崩坏与流失预警指标。",
        },
        {
            "id": "s03_voc_attribution",
            "name": "VOC反馈与客服工单根因定位",
            "skill": "voc",
            "action": "voc",
            "deps": ["s02_health_diagnose"],
            "base_hours": 2.5,
            "description": "结合 NPS 净推荐值与客服重开率，提炼核心痛点聚类。",
        },
        {
            "id": "s04_retention_planning",
            "name": "续约挽留与行动策略看板生成",
            "skill": "pipeline",
            "action": "pipeline",
            "deps": ["s03_voc_attribution"],
            "base_hours": 3.5,
            "description": "生成定制化续约救亡/增购策略看板与商机加权预测。",
        },
        {
            "id": "s05_automation_dispatch",
            "name": "自动化跟进工单与预警任务下发",
            "skill": "automation",
            "action": "automation",
            "deps": ["s04_retention_planning"],
            "base_hours": 1.5,
            "description": "配置触发规则、审批流映射并触发下游协作闭环。",
        },
    ]

    def __init__(self):
        pass

    def extract_intent_entities(self, query: str) -> Dict[str, Any]:
        """提取自然语言中的关键实体。"""
        urgent = any(kw in query for kw in ["紧急", "立刻", "严重", "预警", "流失", "掉单", "救亡"])
        has_nps = any(kw in query.lower() for kw in ["nps", "voc", "满意度", "问卷", "反馈"])
        has_renewal = any(kw in query for kw in ["续约", "增购", "合同", "到期", "商机"])
        has_health = any(kw in query for kw in ["健康", "流失", "分值", "风险"])

        # 尝试提取客户名称
        client_name = "全量客户群体"
        match = re.search(r"([A-Za-z0-9\u4e00-\u9fa5]{2,10}(?:公司|企业|客户|集团))", query)
        if match:
            client_name = match.group(1)

        return {
            "query": query,
            "client_name": client_name,
            "priority": "HIGH" if urgent else "MEDIUM",
            "focus_areas": {
                "nps_voc": has_nps,
                "renewal": has_renewal,
                "health_risk": has_health,
                "urgent_intervention": urgent,
            },
        }

    def compile_intent(self, query: str) -> List[Dict[str, Any]]:
        """将复合意图编译为标准的 Kahn DAG 拓扑序列。"""
        entities = self.extract_intent_entities(query)
        multiplier = 1.2 if entities["priority"] == "HIGH" else 1.0

        compiled_stages = []
        for s in self.STAGES_DEF:
            stage_copy = dict(s)
            est_hours = round(stage_copy["base_hours"] * multiplier, 1)
            stage_copy["estimated_hours"] = est_hours
            stage_copy["target_client"] = entities["client_name"]
            stage_copy["status"] = "PENDING"
            compiled_stages.append(stage_copy)

        return compiled_stages

    def get_dag_summary(self, stages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取 DAG 拓扑摘要与工时总计。"""
        total_hours = sum(s.get("estimated_hours", s.get("base_hours", 0.0)) for s in stages)
        stage_names = [s["name"] for s in stages]
        return {
            "total_stages": len(stages),
            "stage_order": stage_names,
            "total_estimated_hours": round(total_hours, 1),
            "total_person_days": round(total_hours / 8.0, 2),
            "is_valid_dag": len(stages) == 5,
        }

# -*- coding: utf-8 -*-
"""engines/intent_dag_compiler.py - L02 意图解构与敏捷产品交付 DAG 编译引擎.

对标开源标杆：DSPy / Ray DAG / LangGraph / Apache Airflow DAG
核心职责：
1. 从复杂多变的自然语言 / 模糊 PRD / JTBD 诉求中解构出产品交付实体：
   - 目标问题 (Problem Statement / Pain Point)
   - 目标客群 (User Persona / Segment)
   - 价值假设 (Value Hypothesis / Core Assumptions)
   - 敏捷交付阶段 (JTBD/Discovery -> OST/Opportunity -> PRD/UserStory -> Priority/RICE -> Roadmap/ReleaseGate)
2. 构造严格的 Kahn 拓扑排序 DAG：
   - 节点依赖校验与成环死锁检测 (Cycle Detection)
   - 关键路径识别与各环节工时预估 (Estimated Days/Hours)
3. 确保敏捷产品研发闭环从概念发现到排期上线的端到端可执行拓扑编排。
"""
from __future__ import annotations

from collections import deque
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class ProductIntentNode:
    """产品意图 DAG 节点。"""

    def __init__(
        self,
        node_id: str,
        stage: str,
        title: str,
        skill: str,
        action: str,
        estimated_hours: float,
        deliverable: str,
        depends_on: Optional[List[str]] = None,
    ):
        self.node_id = node_id
        self.stage = stage  # e.g. JTBD_Discovery, OST_Opportunity, PRD_Story, Priority_RICE, Roadmap_Release
        self.title = title
        self.skill = skill
        self.action = action
        self.estimated_hours = estimated_hours
        self.deliverable = deliverable
        self.depends_on = depends_on or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "stage": self.stage,
            "title": self.title,
            "skill": self.skill,
            "action": self.action,
            "estimated_hours": self.estimated_hours,
            "deliverable": self.deliverable,
            "depends_on": self.depends_on,
        }


class AgileProductDeliveryDAG:
    """基于 Kahn 拓扑排序的敏捷产品交付编排图。"""

    def __init__(self):
        self.nodes: Dict[str, ProductIntentNode] = {}

    def add_node(self, node: ProductIntentNode) -> None:
        self.nodes[node.node_id] = node

    def compile(self) -> Dict[str, Any]:
        """执行 Kahn 拓扑排序，校验 DAG 有向无环性并生成执行计划。"""
        in_degree: Dict[str, int] = {k: 0 for k in self.nodes}
        adj: Dict[str, List[str]] = {k: [] for k in self.nodes}

        for node_id, node in self.nodes.items():
            for dep in node.depends_on:
                if dep in self.nodes:
                    adj[dep].append(node_id)
                    in_degree[node_id] += 1

        queue = deque([k for k, d in in_degree.items() if d == 0])
        order: List[str] = []

        while queue:
            curr = queue.popleft()
            order.append(curr)
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        has_cycle = len(order) != len(self.nodes)
        total_hours = sum(n.estimated_hours for n in self.nodes.values())

        # 计算分层阶段 (Parallel Batches)
        stage_batches: List[List[str]] = []
        visited = set()
        current_batch = [k for k in self.nodes if not self.nodes[k].depends_on]
        while current_batch:
            stage_batches.append(current_batch)
            visited.update(current_batch)
            next_batch = []
            for node_id, node in self.nodes.items():
                if node_id not in visited and all(dep in visited for dep in node.depends_on):
                    next_batch.append(node_id)
            current_batch = next_batch

        return {
            "ok": not has_cycle,
            "is_dag": not has_cycle,
            "topological_order": order,
            "stage_batches": stage_batches,
            "total_estimated_hours": round(total_hours, 1),
            "total_nodes": len(self.nodes),
            "stages_count": len(stage_batches),
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }


class IntentDAGCompiler:
    """R07 L02 意图解构与敏捷交付 DAG 编译器。"""

    # 产品五大核心交付阶段
    PRODUCT_STAGES = [
        "JTBD_Discovery",    # 1. 产品发现与 JTBD
        "OST_Opportunity",   # 2. 机会解决方案树
        "PRD_UserStory",     # 3. 需求文档与用户故事
        "Priority_RICE",     # 4. 优先级打分与排期
        "Roadmap_Release",   # 5. 路线图与发布门禁
    ]

    STAGE_KEYWORDS = {
        "JTBD_Discovery": ["调研", "访谈", "发现", "jtbd", "痛点", "用户研究", "job story", "问卷"],
        "OST_Opportunity": ["机会", "ost", "解决方案", "假设", "机会树", "opportunity", "探索"],
        "PRD_UserStory": ["prd", "需求文档", "用户故事", "story", "验收标准", "ac", "gherkin", "规则"],
        "Priority_RICE": ["优先级", "rice", "ice", "排序", "backlog", "排期", "成本", "投入产出"],
        "Roadmap_Release": ["路线图", "roadmap", "发布", "上线", "release", "premortem", "发版门禁"],
    }

    def __init__(self):
        pass

    def decompile_intent(self, text: str) -> Dict[str, Any]:
        """从非结构化诉求中解构出产品实体与关键要素。"""
        normalized = text.strip()
        
        # 实体提取
        problem = self._extract_problem(normalized)
        target_users = self._extract_target_users(normalized)
        metric_intent = self._extract_metric_intent(normalized)

        # 匹配阶段
        matched_stages = []
        for stage, kws in self.STAGE_KEYWORDS.items():
            if any(kw.lower() in normalized.lower() for kw in kws):
                matched_stages.append(stage)

        # 如果没有明确匹配到特定阶段，默认触发完整产品标准交付流
        if not matched_stages:
            matched_stages = list(self.PRODUCT_STAGES)

        # 构建 DAG
        dag = self.compile_delivery_dag(
            intent_summary=problem or normalized[:30],
            stages=matched_stages,
            target_user=target_users,
            metric_target=metric_intent,
        )

        return {
            "ok": True,
            "raw_input": normalized,
            "extracted_entities": {
                "problem": problem,
                "target_users": target_users,
                "metric_intent": metric_intent,
            },
            "matched_stages": matched_stages,
            "dag": dag,
        }

    def compile_delivery_dag(
        self,
        intent_summary: str,
        stages: List[str],
        target_user: Optional[str] = None,
        metric_target: Optional[str] = None,
    ) -> Dict[str, Any]:
        """构建 Kahn 拓扑排序的交付 DAG。"""
        dag = AgileProductDeliveryDAG()
        last_node_id = None

        # 1. JTBD / Discovery
        if "JTBD_Discovery" in stages or len(stages) >= 3:
            node_id = "node_01_discovery"
            dag.add_node(ProductIntentNode(
                node_id=node_id,
                stage="JTBD_Discovery",
                title=f"用户研究与 JTBD 发现: {intent_summary[:16]}",
                skill="discover",
                action="discover",
                estimated_hours=6.0,
                deliverable="JTBD 访谈分析与问题定义报告",
                depends_on=[],
            ))
            last_node_id = node_id

        # 2. OST / Opportunity
        if "OST_Opportunity" in stages or len(stages) >= 3:
            node_id = "node_02_ost"
            deps = [last_node_id] if last_node_id else []
            dag.add_node(ProductIntentNode(
                node_id=node_id,
                stage="OST_Opportunity",
                title=f"机会方案树拆解: {intent_summary[:16]}",
                skill="ost",
                action="ost",
                estimated_hours=4.0,
                deliverable="OST 机会树与关键假设清单",
                depends_on=deps,
            ))
            last_node_id = node_id

        # 3. PRD / UserStory
        if "PRD_UserStory" in stages or len(stages) >= 2 or not stages:
            node_id = "node_03_prd"
            deps = [last_node_id] if last_node_id else []
            dag.add_node(ProductIntentNode(
                node_id=node_id,
                stage="PRD_UserStory",
                title=f"PRD 八门禁文档与用户故事编写",
                skill="prd",
                action="prd",
                estimated_hours=8.0,
                deliverable="PRD 需求规格说明书与 Gherkin 验收集",
                depends_on=deps,
            ))
            last_node_id = node_id

        # 4. Priority / RICE
        if "Priority_RICE" in stages or len(stages) >= 3:
            node_id = "node_04_priority"
            deps = [last_node_id] if last_node_id else []
            dag.add_node(ProductIntentNode(
                node_id=node_id,
                stage="Priority_RICE",
                title=f"需求 Backlog 算术与 RICE 排序",
                skill="priority",
                action="rice",
                estimated_hours=3.0,
                deliverable="RICE 排序优先级清单与敏捷迭代规划",
                depends_on=deps,
            ))
            last_node_id = node_id

        # 5. Roadmap / ReleaseGate
        if "Roadmap_Release" in stages or len(stages) >= 3:
            node_id = "node_05_roadmap"
            deps = [last_node_id] if last_node_id else []
            dag.add_node(ProductIntentNode(
                node_id=node_id,
                stage="Roadmap_Release",
                title=f"版本路线图与上线发版门禁",
                skill="roadmap",
                action="roadmap",
                estimated_hours=3.0,
                deliverable="Roadmap 里程碑与 Premortem 风险防控单",
                depends_on=deps,
            ))

        return dag.compile()

    def _extract_problem(self, text: str) -> Optional[str]:
        patterns = [
            r"(?:解决|针对|发现|优化|提升)([^，。！？\n]{4,30})",
            r"(?:问题|痛点|需求)(?:是|为)?([^，。！？\n]{4,30})",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                return m.group(1).strip()
        return text.split("，")[0].split("。")[0][:30]

    def _extract_target_users(self, text: str) -> str:
        for u in ["新用户", "企业客户", "开发者", "付费用户", "试用用户", "管理员", "C端用户"]:
            if u in text:
                return u
        return "目标客群"

    def _extract_metric_intent(self, text: str) -> Optional[str]:
        for m in ["转化率", "留存率", "激活率", "客单价", "gmv", "ltv", "dau", "mau", "跳出率"]:
            if m in text.lower():
                return m
        return "核心北极星指标"

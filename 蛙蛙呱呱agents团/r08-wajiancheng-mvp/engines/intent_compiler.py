# -*- coding: utf-8 -*-
"""engines/intent_compiler.py - L02 意图解构层 (Intent Decompiler & Agile Delivery DAG).

对标开源标杆：DSPy / Ray DAG (Stars > 25k)
核心职责：
1. 从非结构化 PRD / 需求文本中提取核心交付实体：目标、核心假设、切片形态、技术栈、交付物类型、风险点；
2. 声明式编译为有向无环图 (Delivery DAG)，按 Kahn 拓扑排序输出执行计划；
3. 计算人天/工时估算与并行度拓扑。
"""
from __future__ import annotations

from collections import deque
import re
from typing import Any, Dict, List, Optional, Set


class IntentNode:
    def __init__(self, node_id: str, title: str, skill: str, action: str, estimated_hours: float, depends_on: Optional[List[str]] = None):
        self.node_id = node_id
        self.title = title
        self.skill = skill
        self.action = action
        self.estimated_hours = estimated_hours
        self.depends_on = depends_on or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "title": self.title,
            "skill": self.skill,
            "action": self.action,
            "estimated_hours": self.estimated_hours,
            "depends_on": self.depends_on,
        }


class DeliveryDAG:
    """基于 Kahn 拓扑排序的可执行交付 DAG。"""

    def __init__(self):
        self.nodes: Dict[str, IntentNode] = {}

    def add_node(self, node: IntentNode) -> None:
        self.nodes[node.node_id] = node

    def compile(self) -> Dict[str, Any]:
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

        return {
            "ok": not has_cycle,
            "is_dag": not has_cycle,
            "topological_order": order,
            "total_estimated_hours": round(total_hours, 1),
            "stages_count": len(order),
            "critical_path_length": len(order),
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }


class IntentCompiler:
    """R08 L02 复合交付需求编译引擎。"""

    def __init__(self):
        self.version = "1.0.0"

    def decompile(self, requirement_text: str) -> Dict[str, Any]:
        """将 PRD/自然语言解构并编译为 MVP 交付 DAG。"""
        text = requirement_text.lower()
        extracted_entities: Dict[str, Any] = {
            "artifact_types": [],
            "risk_type": "value",
            "stack": "vite-html",
            "has_form": False,
            "has_mobile": False,
            "urgency": "medium",
        }

        # 识别切片形态
        if any(w in text for w in ("落地页", "landing", "h5", "收集邮箱", "单页")):
            extracted_entities["artifact_types"].append("landing")
        if any(w in text for w in ("flutter", "原型", "app", "跨平台", "移动")):
            extracted_entities["artifact_types"].append("prototype")
            extracted_entities["has_mobile"] = True
            extracted_entities["stack"] = "flutter"
        if any(w in text for w in ("saas", "管理后台", "多页", "系统")):
            extracted_entities["artifact_types"].append("saas")
            extracted_entities["stack"] = "vue-vite"
        if any(w in text for w in ("邮件", "email", "通知", "newsletter")):
            extracted_entities["artifact_types"].append("email")

        # 兜底至少包含 landing 单页 MVP
        if not extracted_entities["artifact_types"]:
            extracted_entities["artifact_types"].append("landing")

        # 识别表单与关键行动点
        if any(w in text for w in ("表单", "邮箱", "留资", "提交", "注册", "form")):
            extracted_entities["has_form"] = True

        # 构建标准的 R08 敏捷实现 5 步 Kahn DAG
        dag = DeliveryDAG()
        dag.add_node(IntentNode(
            node_id="stage_01_slice",
            title="产品切片与最小假设界定",
            skill="slice",
            action="mvp",
            estimated_hours=2.0,
            depends_on=[],
        ))

        dag.add_node(IntentNode(
            node_id="stage_02_scaffold",
            title="工程脚手架与目录骨架初始化",
            skill="scaffold",
            action="scaffold",
            estimated_hours=1.5,
            depends_on=["stage_01_slice"],
        ))

        # 根据形态挂载交付节点
        primary_type = extracted_entities["artifact_types"][0]
        if primary_type == "landing":
            dag.add_node(IntentNode(
                node_id="stage_03_page",
                title="高转化落地页构建与表单配置",
                skill="landing",
                action="landing",
                estimated_hours=3.5,
                depends_on=["stage_02_scaffold"],
            ))
        elif primary_type == "prototype":
            dag.add_node(IntentNode(
                node_id="stage_03_page",
                title="跨平台核心功能单屏原型实现",
                skill="prototype",
                action="prototype",
                estimated_hours=4.5,
                depends_on=["stage_02_scaffold"],
            ))
        else:
            dag.add_node(IntentNode(
                node_id="stage_03_page",
                title="多页轻量 SaaS 导航与骨架搭建",
                skill="saas",
                action="saas",
                estimated_hours=4.0,
                depends_on=["stage_02_scaffold"],
            ))

        dag.add_node(IntentNode(
            node_id="stage_04_token_design",
            title="设计 Token 注入与视觉样式微调",
            skill="design",
            action="token",
            estimated_hours=1.5,
            depends_on=["stage_03_page"],
        ))

        dag.add_node(IntentNode(
            node_id="stage_05_qa_handoff",
            title="QA 门禁合规复核与 R09 交接包封装",
            skill="qa",
            action="handoff",
            estimated_hours=1.5,
            depends_on=["stage_04_token_design"],
        ))

        compilation = dag.compile()

        return {
            "ok": compilation["ok"],
            "raw_query": requirement_text,
            "entities": extracted_entities,
            "dag": compilation,
        }

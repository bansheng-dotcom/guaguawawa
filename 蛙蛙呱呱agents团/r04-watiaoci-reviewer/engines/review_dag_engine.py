# -*- coding: utf-8 -*-
"""L02 意图解构层：声明式 Review DAG 与 Kahn 拓扑排序调度引擎。
对标开源项目：DSPy (Stars > 18k), Ray DAG (Stars > 34k)。
解决病灶：审查流程串行硬编码，无法动态根据复合自然语言意图编译审查节点网络及依赖拓扑。
"""
from __future__ import annotations

from collections import deque
import re
from typing import Any, Callable, Dict, List, Set, Tuple


class ReviewDAGNode:
    """DAG 中的单一审查执行节点。"""

    def __init__(self, node_id: str, skill: str, action: str, params: Dict[str, Any], deps: List[str] | None = None) -> None:
        self.node_id = node_id
        self.skill = skill
        self.action = action
        self.params = params or {}
        self.deps = deps or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "skill": self.skill,
            "action": self.action,
            "params": self.params,
            "deps": self.deps,
        }


class ReviewDAGEngine:
    """声明式审查 DAG 构建与 Kahn 算法拓扑排程引擎。"""

    INTENT_TAXONOMY = [
        ("artifact_inventory", ("清点", "盘点", "物料", "inventory", "成品清单"), "artifact", "inventory"),
        ("artifact_verify", ("证据链", "三级证据", "孤岛", "stub", "verify"), "artifact", "verify"),
        ("gate_audit", ("门禁强度", "戏法门禁", "gate audit", "强度审计"), "gate", "audit"),
        ("gate_run", ("硬门禁", "跑门禁", "命令门禁", "gate run"), "gate", "run"),
        ("criteria_review", ("判据审查", "验收标准", "外置判据", "criteria review"), "criteria", "review"),
        ("criteria_delta", ("增量差异", "复评对照", "fixed new", "criteria delta"), "criteria", "delta"),
        ("quality_critique", ("质量批评", "绝对化词", "禁词", "critique"), "quality", "critique"),
        ("quality_converge", ("收敛趋势", "不再下降", "converge"), "quality", "converge"),
        ("facts_check", ("事实核查", "数字幻觉", "来源质量", "facts check"), "facts", "check"),
        ("facts_trace", ("数字回溯", "单数字", "trace"), "facts", "trace"),
        ("strengths_mark", ("优点保留", "keep list", "优点标记"), "strengths", "mark"),
        ("strengths_recheck", ("优点降级", "复评修改", "recheck"), "strengths", "recheck"),
        ("human_package", ("人工评审包", "发起评审", "package"), "human", "package"),
        ("human_ingest", ("逐字回填", "回填核验", "ingest"), "human", "ingest"),
        ("human_ack", ("确认批次", "staged复制", "ack"), "human", "ack"),
    ]

    @classmethod
    def compile_intent_to_dag(cls, natural_language_request: str) -> Dict[str, Any]:
        """将用户自然语言意图编译为 Review DAG，并自动解析依赖关系。"""
        req_lower = natural_language_request.lower()
        matched_tasks: List[Tuple[str, str, str]] = []

        for task_id, keywords, skill, action in cls.INTENT_TAXONOMY:
            for kw in keywords:
                if kw in req_lower:
                    matched_tasks.append((task_id, skill, action))
                    break

        if not matched_tasks:
            # 默认全量质检最小闭环：清点 -> 判据 -> 门禁
            matched_tasks = [
                ("artifact_inventory", "artifact", "inventory"),
                ("criteria_review", "criteria", "review"),
                ("gate_audit", "gate", "audit"),
            ]

        # 依据业务逻辑构建依赖约束边
        # 1. 证据链校验/盘点必须在门禁/判据前
        # 2. 事实核查与质量批评在判据审查之后
        # 3. 人工评审包必须在所有分析之后
        nodes: Dict[str, ReviewDAGNode] = {}
        for task_id, skill, action in matched_tasks:
            deps = []
            if task_id in ("artifact_verify", "gate_audit", "gate_run", "criteria_review"):
                if "artifact_inventory" in [m[0] for m in matched_tasks] and task_id != "artifact_inventory":
                    deps.append("artifact_inventory")
            if task_id in ("quality_critique", "facts_check"):
                if "criteria_review" in [m[0] for m in matched_tasks]:
                    deps.append("criteria_review")
            if task_id in ("human_package", "human_ack"):
                for prior_id, _, _ in matched_tasks:
                    if prior_id != task_id:
                        deps.append(prior_id)
            nodes[task_id] = ReviewDAGNode(task_id, skill, action, {}, list(set(deps)))

        # Kahn 拓扑排序
        in_degree: Dict[str, int] = {k: 0 for k in nodes}
        adj: Dict[str, List[str]] = {k: [] for k in nodes}

        for n_id, node in nodes.items():
            for dep in node.deps:
                if dep in nodes:
                    adj[dep].append(n_id)
                    in_degree[n_id] += 1

        queue = deque([n for n, deg in in_degree.items() if deg == 0])
        execution_order: List[str] = []

        while queue:
            curr = queue.popleft()
            execution_order.append(curr)
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        has_cycle = len(execution_order) < len(nodes)
        return {
            "ok": not has_cycle,
            "raw_intent": natural_language_request,
            "nodes": {k: v.to_dict() for k, v in nodes.items()},
            "execution_order": execution_order if not has_cycle else list(nodes.keys()),
            "has_cycle": has_cycle,
            "parallel_stages": cls._extract_parallel_stages(nodes, execution_order),
        }

    @classmethod
    def _extract_parallel_stages(cls, nodes: Dict[str, ReviewDAGNode], order: List[str]) -> List[List[str]]:
        """按层级划分可以并行执行的 stage 组。"""
        stages: List[List[str]] = []
        resolved: Set[str] = set()

        remaining = set(order)
        while remaining:
            current_stage = [
                n_id for n_id in remaining
                if set(nodes[n_id].deps).issubset(resolved)
            ]
            if not current_stage:
                # 环形兜底
                current_stage = list(remaining)
            stages.append(current_stage)
            resolved.update(current_stage)
            remaining.difference_update(current_stage)

        return stages

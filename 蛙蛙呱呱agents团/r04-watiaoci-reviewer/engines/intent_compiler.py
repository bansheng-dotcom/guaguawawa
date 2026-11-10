# -*- coding: utf-8 -*-
"""L02 意图解构层：声明式审查意图与多动作审查 DAG 图谱编译器。
对标开源标杆：stanfordnlp/dspy (Stars: 19k+), ray-project/ray (Dag Engine, Stars: 34k+)

功能：
1. 接收用户的自然语言复合作业请求（例如：“先盘点交付物，再运行门禁与强度审计，最后做事实核查和禁词批判”）；
2. 语义解构与实体槽位提取：提取 target_path、strict_mode、skip_gates、max_hedges、tolerance 等超参；
3. 将复合意图编译为确定性的审查任务拓扑有向无环图 (Review DAG)；
4. 支持节点依赖关系校验（例如：verify 依赖 inventory，package 依赖 critique 与 check）；
5. 拓扑排序计算最优审查执行序列。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple


class ReviewTaskNode:
    """审查 DAG 节点"""

    def __init__(self, node_id: str, skill: str, action: str, params: Optional[Dict[str, Any]] = None, depends_on: Optional[List[str]] = None) -> None:
        self.node_id = node_id
        self.skill = skill
        self.action = action
        self.params = params or {}
        self.depends_on = depends_on or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "skill": self.skill,
            "action": self.action,
            "params": self.params,
            "depends_on": self.depends_on,
        }


class IntentDAGCompiler:
    """声明式意图编译与 DAG 调度图构建器"""

    # 意图模式库
    PATTERNS: List[Dict[str, Any]] = [
        {"skill": "artifact", "action": "inventory", "keywords": ["盘点", "物料", "清单", "交付物", "文件是否齐全", "inventory"]},
        {"skill": "artifact", "action": "verify", "keywords": ["三级证据链", "证据链", "占位符", "桩代码", "verify", "stub", "实质性"]},
        {"skill": "gate", "action": "run", "keywords": ["跑门禁", "运行门禁", "执行门禁", "测试用例", "run gate", "gate run"]},
        {"skill": "gate", "action": "audit", "keywords": ["门禁强度", "强度审计", "门禁审计", "伪门禁", "门禁作弊", "gate audit", "strength"]},
        {"skill": "criteria", "action": "review", "keywords": ["判据", "验收判据", "外置判据", "验收标准", "criteria review", "acceptance"]},
        {"skill": "criteria", "action": "delta", "keywords": ["两轮对比", "判据对照", "修复对比", "delta", "差异比对"]},
        {"skill": "quality", "action": "critique", "keywords": ["禁词", "禁词扫描", "完成声明", "主观词", "浮夸词", "hedge", "critique", "吹嘘"]},
        {"skill": "quality", "action": "converge", "keywords": ["收敛", "迭代收敛", "是否收敛", "converge"]},
        {"skill": "facts", "action": "check", "keywords": ["事实核查", "数字核查", "数据真实性", "facts check", "幻觉"]},
        {"skill": "facts", "action": "trace", "keywords": ["单数字回溯", "数字来源", "trace", "精度回溯"]},
        {"skill": "strengths", "action": "mark", "keywords": ["保留优点", "优点标记", "keep list", "亮点"]},
        {"skill": "strengths", "action": "recheck", "keywords": ["复评修改", "优点复核", "recheck", "降级审计"]},
        {"skill": "human", "action": "package", "keywords": ["人工评审", "人工打包", "打包评审", "交付人类", "package", "评审包"]},
        {"skill": "human", "action": "ingest", "keywords": ["人工回灌", "意见回填", "ingest", "批次回灌"]},
        {"skill": "human", "action": "ack", "keywords": ["归档确认", "资产归档", "ack", "staged确认"]},
    ]

    # 规范层依赖约束 (Dependency Rules)
    DEFAULT_DEPENDENCIES: Dict[Tuple[str, str], List[Tuple[str, str]]] = {
        ("artifact", "verify"): [("artifact", "inventory")],
        ("gate", "audit"): [("gate", "run")],
        ("quality", "converge"): [("quality", "critique")],
        ("human", "package"): [("artifact", "verify"), ("quality", "critique")],
        ("human", "ack"): [("human", "package")],
    }

    def deconstruct(self, text: str) -> Dict[str, Any]:
        """将自然语言解析为意图匹配项与抽取参数"""
        matched_actions: List[Tuple[str, str]] = []
        lowered = text.lower()

        # 扫描关键词匹配
        for item in self.PATTERNS:
            for kw in item["keywords"]:
                if kw.lower() in lowered:
                    action_tuple = (item["skill"], item["action"])
                    if action_tuple not in matched_actions:
                        matched_actions.append(action_tuple)
                    break

        # 默认回退
        if not matched_actions:
            matched_actions.append(("criteria", "review"))

        # 提取参数槽位
        params: Dict[str, Any] = {
            "strict_mode": ("严格" in text or "严苛" in text or "strict" in lowered),
            "deep_trace": ("深溯" in text or "深度" in text or "deep" in lowered),
            "allow_warn": not ("零容忍" in text or "不容忍" in text),
        }

        # 提取目标路径（如果存在形如 xxx/xxx 或 xxx.py 等）
        path_matches = re.findall(r"([a-zA-Z0-9_\-\./\\]+\.(?:py|json|md|txt|ts|js|yml|yaml))", text)
        if path_matches:
            params["target_path"] = path_matches[0]

        return {
            "original_query": text,
            "matched_actions": matched_actions,
            "extracted_params": params,
        }

    def compile(self, text: str) -> Dict[str, Any]:
        """编译为完整的 Review DAG 图"""
        deconstruction = self.deconstruct(text)
        actions = deconstruction["matched_actions"]
        params = deconstruction["extracted_params"]

        # 构建节点字典
        nodes: Dict[str, ReviewTaskNode] = {}
        action_to_id: Dict[Tuple[str, str], str] = {}

        for idx, (skill, action) in enumerate(actions, start=1):
            node_id = f"task_{idx:02d}_{skill}_{action}"
            node = ReviewTaskNode(node_id, skill, action, params=dict(params))
            nodes[node_id] = node
            action_to_id[(skill, action)] = node_id

        # 自动补全或注入依赖边
        for (skill, action), node_id in action_to_id.items():
            req_deps = self.DEFAULT_DEPENDENCIES.get((skill, action), [])
            for dep_skill, dep_action in req_deps:
                if (dep_skill, dep_action) in action_to_id:
                    dep_node_id = action_to_id[(dep_skill, dep_action)]
                    if dep_node_id not in nodes[node_id].depends_on:
                        nodes[node_id].depends_on.append(dep_node_id)

        # 拓扑排序计算执行序
        exec_sequence = self._topological_sort(nodes)

        return {
            "query": text,
            "params": params,
            "dag_nodes": [n.to_dict() for n in nodes.values()],
            "execution_sequence": exec_sequence,
            "node_count": len(nodes),
            "is_valid_dag": len(exec_sequence) == len(nodes),
        }

    def _topological_sort(self, nodes: Dict[str, ReviewTaskNode]) -> List[str]:
        """Kahn 算法拓扑排序"""
        in_degree: Dict[str, int] = {nid: 0 for nid in nodes}
        adj: Dict[str, List[str]] = {nid: [] for nid in nodes}

        for nid, node in nodes.items():
            for dep in node.depends_on:
                if dep in adj:
                    adj[dep].append(nid)
                    in_degree[nid] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result: List[str] = []

        while queue:
            curr = queue.pop(0)
            result.append(curr)
            for neighbor in adj.get(curr, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

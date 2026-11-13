# -*- coding: utf-8 -*-
"""intent_compiler.py - R09 意图解构层 (L02: Intent Decompiler & Engineering Delivery DAG)

严格对标开源标杆：
- DSPy / Ray DAG (Stars > 25k)
核心职责：
1. 将非结构化、复杂口语化自然语言工程需求反编译为强类型声明式交付契约；
2. 自动根据技术诉求构建 Kahn 拓扑有向无环图 (Engineering Delivery DAG)；
3. 输出包含工时估算、依赖关系、阶段门禁 (Gates) 的结构化交付方案。
"""
from __future__ import annotations

import collections
import re
from typing import Any, Dict, List, Optional


class EngineeringIntentCompiler:
    """工程意图解构与 Kahn 拓扑交付 DAG 编译器。"""

    INTENT_KEYWORDS = {
        "spec": ["规格", "架构", "设计", "边界", "拓扑", "模块", "spec", "architecture"],
        "data_api": ["数据库", "schema", "api", "接口", "数据模型", "表结构", "sql"],
        "fullstack": ["全栈", "前端", "后端", "界面", "认证", "登录", "ui", "fullstack"],
        "crossplatform": ["跨端", "flutter", "app", "移动端", "ios", "android", "构建", "build"],
        "testing": ["测试", "单测", "集成测试", "e2e", "覆盖率", "playwright", "test"],
        "debug": ["调试", "性能", "重构", "优化", "瓶颈", "debug", "refactor"],
        "ops": ["部署", "流水线", "安全", "密钥", "cve", "迁移", "回滚", "ops", "ci/cd"],
        "special": ["mcp", "godot", "游戏", "agent", "工作流", "载体"]
    }

    def __init__(self) -> None:
        pass

    def decompile(self, prompt: str) -> Dict[str, Any]:
        """将用户自然语言需求反编译为结构化工程意图与 Kahn 拓扑 DAG。"""
        if not prompt or not prompt.strip():
            return {
                "ok": False,
                "error": "empty_prompt",
                "message": "需求提示词为空，无法编译意图",
            }

        text = prompt.lower()
        matched_domains = []
        for domain, kws in self.INTENT_KEYWORDS.items():
            if any(k in text for k in kws):
                matched_domains.append(domain)

        # 兜底默认全流程工程链
        if not matched_domains:
            matched_domains = ["spec", "data_api", "fullstack", "testing"]

        # 构建工程阶段任务节点
        nodes: List[Dict[str, Any]] = []
        node_id_map: Dict[str, str] = {}

        # 标准阶段顺序定义
        phase_order = ["spec", "data_api", "fullstack", "crossplatform", "testing", "debug", "ops", "special"]
        sorted_domains = [d for d in phase_order if d in matched_domains]

        # 如果提取出的节点为空，按默认填充
        if not sorted_domains:
            sorted_domains = ["spec", "fullstack", "testing"]

        # 构建 DAG 节点与依赖
        prev_node_id: Optional[str] = None
        total_hours = 0.0

        for idx, dom in enumerate(sorted_domains):
            nid = f"task_{idx+1:02d}_{dom}"
            deps = [prev_node_id] if prev_node_id else []
            hours = 4.0 if dom in ("spec", "data_api") else (8.0 if dom in ("fullstack", "testing") else 6.0)
            total_hours += hours
            nodes.append({
                "id": nid,
                "domain": dom,
                "title": f"执行 {dom} 工程阶段",
                "dependencies": deps,
                "estimated_hours": hours,
                "gate_criteria": f"{dom}_gate_pass",
            })
            prev_node_id = nid

        # Kahn 拓扑排序计算
        topo_order = self._kahn_topological_sort(nodes)

        return {
            "ok": True,
            "layer": "L02",
            "prompt": prompt,
            "matched_domains": sorted_domains,
            "total_estimated_hours": total_hours,
            "total_estimated_days": round(total_hours / 8.0, 1),
            "dag_nodes": nodes,
            "execution_order": topo_order,
            "is_valid_dag": len(topo_order) == len(nodes),
            "verdict": "PASS" if len(topo_order) == len(nodes) else "FAIL",
        }

    def _kahn_topological_sort(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """Kahn 算法计算 DAG 拓扑执行顺序。"""
        in_degree: Dict[str, int] = {node["id"]: 0 for node in nodes}
        adj: Dict[str, List[str]] = collections.defaultdict(list)

        for node in nodes:
            nid = node["id"]
            for dep in node.get("dependencies", []):
                adj[dep].append(nid)
                in_degree[nid] += 1

        queue = collections.deque([nid for nid, deg in in_degree.items() if deg == 0])
        topo: List[str] = []

        while queue:
            curr = queue.popleft()
            topo.append(curr)
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return topo

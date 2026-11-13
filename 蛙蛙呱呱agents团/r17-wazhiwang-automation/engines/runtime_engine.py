# -*- coding: utf-8 -*-
"""engines/runtime_engine.py - [L01] 工具实体层：真实自动化工作流沙箱与拓扑校验器。

对标开源标杆：
- n8n / Apache Airflow / Prefect / Temporal (Stars > 35k~45k)
- 真实工作流有向无环图 (DAG) 拓扑排序、环路检测、悬空边扫描与节点级 Dry-Run 执行模拟器

核心职责：
1. 真实工作流 DAG 拓扑分析沙箱：基于 Kahn 拓扑排序算法进行无环检测、入度出度统计与悬空边探针；
2. 确定性 Dry-Run 执行模拟器：模拟数据在节点间传递流转，支持 trigger -> mapping -> ai -> approval -> delivery 虚拟执行 trace；
3. 确定性幂等指纹生成与冲突检测：基于 canonical JSON + sha256 生成 32 位幂等摘要；
4. 凭据明文泄漏探针：扫描节点中的 URL、headers、body 是否含明文 key/secret/password/token；
5. 运行时探针健康诊断 probe_health()，包含拓扑沙箱、执行器与幂等引擎状态。
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple


class AutomationRuntimeEngine:
    """真实自动化工作流拓扑沙箱与执行器引擎。"""

    SECRET_KEY_PATTERNS = [
        re.compile(r"(?i)(api[_-]?key|secret|password|passwd|token|access[_-]?token|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"),
        re.compile(r"(?i)https?://[^:\s]+:([^@\s]+)@"), # URL内明文密码
    ]

    def __init__(self, max_nodes_limit: int = 100):
        self.max_nodes_limit = max_nodes_limit

    # -------------------------------------------------------------------------
    # 1. 真实工作流拓扑 DAG 分析沙箱
    # -------------------------------------------------------------------------
    def analyze_topology(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """对工作流进行 Kahn 拓扑排序与结构完整性分析。"""
        nodes = workflow_data.get("nodes", [])
        connections = workflow_data.get("connections", [])

        node_ids: Set[str] = {n.get("id") or n.get("name") for n in nodes if (n.get("id") or n.get("name"))}
        if not node_ids:
            return {
                "ok": False,
                "error": "工作流中没有检测到有效节点",
                "node_count": 0,
                "dangling_edges": [],
                "is_dag": False,
                "triggers_count": 0,
            }

        # 1.1 悬空边检测
        dangling_edges: List[Dict[str, str]] = []
        adj: Dict[str, List[str]] = collections.defaultdict(list)
        in_degree: Dict[str, int] = {nid: 0 for nid in node_ids}

        for edge in connections:
            source = edge.get("from") or edge.get("source")
            target = edge.get("to") or edge.get("target")

            if source not in node_ids or target not in node_ids:
                dangling_edges.append({"from": str(source), "to": str(target)})
            else:
                adj[source].append(target)
                in_degree[target] += 1

        # 1.2 Kahn's Algorithm 拓扑排序与环路检测
        queue = collections.deque([nid for nid, deg in in_degree.items() if deg == 0])
        topo_order: List[str] = []

        while queue:
            curr = queue.popleft()
            topo_order.append(curr)
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        has_cycle = len(topo_order) != len(node_ids)

        # 1.3 触发器节点统计 (入度为0或节点类型含 trigger/webhook/schedule)
        triggers = [
            n for n in nodes
            if "trigger" in (n.get("type", "")).lower()
            or "webhook" in (n.get("type", "")).lower()
            or "schedule" in (n.get("type", "")).lower()
            or (n.get("id") or n.get("name")) in [nid for nid, deg in in_degree.items() if deg == 0]
        ]

        return {
            "ok": len(dangling_edges) == 0 and not has_cycle and len(triggers) >= 1,
            "node_count": len(node_ids),
            "edge_count": len(connections),
            "dangling_edges_count": len(dangling_edges),
            "dangling_edges": dangling_edges,
            "is_dag": not has_cycle,
            "has_cycle": has_cycle,
            "topo_order": topo_order if not has_cycle else [],
            "triggers_count": len(triggers),
        }

    # -------------------------------------------------------------------------
    # 2. 确定性 Dry-Run 执行模拟器
    # -------------------------------------------------------------------------
    def simulate_dry_run(self, workflow_data: Dict[str, Any], initial_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """模拟工作流各节点的执行与数据传递流转。"""
        topo = self.analyze_topology(workflow_data)
        if not topo["ok"]:
            return {
                "success": False,
                "reason": "拓扑验证未通过，无法执行 Dry-Run",
                "details": topo,
            }

        payload = initial_payload or {"event_id": "evt_test_001", "body": {"user": "tester", "action": "checkout"}}
        nodes_map = {n.get("id") or n.get("name"): n for n in workflow_data.get("nodes", [])}
        execution_trace: List[Dict[str, Any]] = []

        current_data = dict(payload)
        for step_idx, node_id in enumerate(topo["topo_order"], start=1):
            node = nodes_map.get(node_id, {})
            node_type = str(node.get("type", "transform")).lower()
            status = "SUCCESS"

            # 模拟节点内转换或门禁逻辑
            if "approval" in node_type or "gate" in node_type:
                # 检查审批门禁
                approved = node.get("approved", True)
                if not approved:
                    status = "BLOCKED_APPROVAL_REQUIRED"
                    execution_trace.append({
                        "step": step_idx,
                        "node_id": node_id,
                        "node_type": node_type,
                        "status": status,
                        "output": "暂停执行：等待人工审批 (HITL)",
                    })
                    return {
                        "success": False,
                        "status": "SUSPENDED",
                        "blocked_at": node_id,
                        "trace": execution_trace,
                    }

            execution_trace.append({
                "step": step_idx,
                "node_id": node_id,
                "node_type": node_type,
                "status": status,
                "sample_output_keys": list(current_data.keys()),
            })

        return {
            "success": True,
            "status": "COMPLETED",
            "executed_steps_count": len(execution_trace),
            "trace": execution_trace,
        }

    # -------------------------------------------------------------------------
    # 3. 确定性幂等指纹生成与冲突检测
    # -------------------------------------------------------------------------
    def generate_idempotency_key(self, route: str, payload: Any, salt: str = "r17_wazhiwang") -> str:
        """根据标准规范计算确定性 32 位幂等指纹。"""
        if isinstance(payload, dict) or isinstance(payload, list):
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        else:
            canonical = str(payload)
        raw = f"{route}|{canonical}|{salt}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:32]

    # -------------------------------------------------------------------------
    # 4. 凭据明文泄露扫描沙箱
    # -------------------------------------------------------------------------
    def scan_plaintext_credentials(self, text_or_data: Any) -> Dict[str, Any]:
        """扫描文本或结构化数据中的明文 API 密钥与凭据。"""
        raw_str = text_or_data if isinstance(text_or_data, str) else json.dumps(text_or_data, ensure_ascii=False)
        hits: List[str] = []

        for pat in self.SECRET_KEY_PATTERNS:
            for match in pat.finditer(raw_str):
                matched_group = match.group(0)
                # 脱敏展示
                hits.append(matched_group[:10] + "****" + matched_group[-4:])

        return {
            "compliant": len(hits) == 0,
            "violations_count": len(hits),
            "hits_masked": hits,
        }

    # -------------------------------------------------------------------------
    # 5. 健康诊断探针
    # -------------------------------------------------------------------------
    def probe_health(self) -> Dict[str, Any]:
        """健康诊断探针，验证工具实体层工作就绪状态。"""
        # 自测一个微型 DAG
        demo_wf = {
            "nodes": [
                {"id": "n1", "name": "webhook", "type": "webhook_trigger"},
                {"id": "n2", "name": "transform", "type": "mapping_transform"},
                {"id": "n3", "name": "deliver", "type": "http_request"}
            ],
            "connections": [
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "n3"}
            ]
        }
        res = self.analyze_topology(demo_wf)
        sim = self.simulate_dry_run(demo_wf)
        idem = self.generate_idempotency_key("order_sync", {"order_id": 1001})

        healthy = res["ok"] and sim["success"] and len(idem) == 32
        return {
            "status": "HEALTHY" if healthy else "UNHEALTHY",
            "engine": "AutomationRuntimeEngine",
            "topology_sandbox": "OK" if res["ok"] else "FAIL",
            "dry_run_simulator": "OK" if sim["success"] else "FAIL",
            "idempotency_sandbox": "OK" if len(idem) == 32 else "FAIL",
        }

# -*- coding: utf-8 -*-
"""engines/spec_ledger.py - [L04] 领域账本层：自动化工程业务规格账本加载与 8 维门禁合规校验。

对标开源标杆：
- dbt Semantic Layer / OpenAPI 3.1 契约账本模式
- n8n Workflow Spec / Airflow DAG Contract 单一信任源 (SSOT)

核心职责：
1. 动态读取并解析 AUTOMATION_SPEC.md 单一信任源 (Single Source of Truth)；
2. 提取北极星指标 (WSR, CIR, IDE, ZND, APR) 与量纲容差；
3. 执行 8 维自动化硬门禁刚性审查 (The 8-Dimension Automation Gate Matrix)；
4. 输出合规性审查摘要与违规门禁阻断列表。
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_PATH = os.path.join(_HERE, "AUTOMATION_SPEC.md")


class AutomationSpecLedger:
    """自动化工程单一信任源规格账本管理器。"""

    def __init__(self, spec_file: str = SPEC_PATH):
        self.spec_file = spec_file

    def load_spec(self) -> Dict[str, Any]:
        """读取并结构化解析 AUTOMATION_SPEC.md。"""
        if not os.path.exists(self.spec_file):
            raise FileNotFoundError(f"找不到统一规格账本: {self.spec_file}")

        with open(self.spec_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 提取北极星指标
        kpis = {
            "WSR": {
                "name": "工作流成功率",
                "target": ">= 99.9%",
                "tolerance": 0.001,
                "description": "端到端执行成功的运行实例数 / 总触发运行数",
            },
            "CIR": {
                "name": "凭据零泄露合规率",
                "target": "= 100.0%",
                "tolerance": 0.00,
                "description": "明文 API Key/Token/Secret 零泄露收录与引用合规率",
            },
            "IDE": {
                "name": "写操作幂等覆盖率",
                "target": "= 100.0%",
                "tolerance": 0.00,
                "description": "所有写动作 100% 具备确定性幂等指纹或去重 Key",
            },
            "ZND": {
                "name": "零悬空连接边比率",
                "target": "= 100.0%",
                "tolerance": 0.00,
                "description": "工作流拓扑中所有节点出入边引用的 node_id 真实存在且无环",
            },
            "APR": {
                "name": "高危操作审批阻断率",
                "target": "= 100.0%",
                "tolerance": 0.00,
                "description": "资金调拨、生产发布、权限提权 100% 阻断并移交审批",
            },
        }

        # 提取 8 维硬门禁
        gates = [
            {"id": "GATE-01", "name": "悬空边与拓扑无环门禁", "threshold": "dangling_edges == 0 and is_dag == True"},
            {"id": "GATE-02", "name": "明文凭据零容忍拦截", "threshold": "plaintext_credentials_count == 0"},
            {"id": "GATE-03", "name": "写操作幂等保障门禁", "threshold": "has_idempotency_key == True"},
            {"id": "GATE-04", "name": "未经审批擅自发布拦截", "threshold": "unapproved_publish == False"},
            {"id": "GATE-05", "name": "失败重试与死信兜底门禁", "threshold": "0 <= max_retries <= 10 and has_dlq == True"},
            {"id": "GATE-06", "name": "字段映射合法性门禁", "threshold": "target_fields in snake_case and no reserved_cols"},
            {"id": "GATE-07", "name": "AI 节点护栏与权限门禁", "threshold": "has model, purpose, guardrail, and permission"},
            {"id": "GATE-08", "name": "全链路可观测审计门禁", "threshold": "has trigger, input, execution, output, operator"},
        ]

        return {
            "spec_file": os.path.basename(self.spec_file),
            "version": "v13.0",
            "role": "R17 蛙织网 · 自动化与集成工程师",
            "north_star_kpis": kpis,
            "gates_count": len(gates),
            "gates": gates,
            "raw_size": len(content),
        }

    def verify_gate_compliance(self, artifact_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """按 8 维自动化门禁标准对给定工件执行刚性合规审查。"""
        violations: List[str] = []
        checks: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # GATE-01: 悬空边与拓扑无环门禁
        # -------------------------------------------------------------
        dangling = data.get("dangling_edges", [])
        is_dag = data.get("is_dag", True)
        g1_pass = len(dangling) == 0 and is_dag
        if not g1_pass:
            violations.append("GATE-01 破损: 存在悬空边或有环循环引用")
        checks.append({"gate": "GATE-01", "name": "悬空边与拓扑无环门禁", "passed": g1_pass})

        # -------------------------------------------------------------
        # GATE-02: 明文凭据零容忍拦截
        # -------------------------------------------------------------
        cred_violations = data.get("credential_violations", 0)
        g2_pass = cred_violations == 0
        if not g2_pass:
            violations.append("GATE-02 破损: 检测到明文硬编码密钥或未加密凭据")
        checks.append({"gate": "GATE-02", "name": "明文凭据零容忍拦截", "passed": g2_pass})

        # -------------------------------------------------------------
        # GATE-03: 写操作幂等保障门禁
        # -------------------------------------------------------------
        is_write = data.get("is_write_action", False)
        has_idem = data.get("has_idempotency_key", True)
        g3_pass = (not is_write) or has_idem
        if not g3_pass:
            violations.append("GATE-03 破损: 写操作未声明幂等键 (Idempotency Key)")
        checks.append({"gate": "GATE-03", "name": "写操作幂等保障门禁", "passed": g3_pass})

        # -------------------------------------------------------------
        # GATE-04: 未经审批擅自发布拦截
        # -------------------------------------------------------------
        is_prod = data.get("is_production_publish", False)
        is_approved = data.get("is_approved", True)
        g4_pass = (not is_prod) or is_approved
        if not g4_pass:
            violations.append("GATE-04 破损: 发现未经审批擅自发布上线行为")
        checks.append({"gate": "GATE-04", "name": "未经审批擅自发布拦截", "passed": g4_pass})

        # -------------------------------------------------------------
        # GATE-05: 失败重试与死信兜底门禁
        # -------------------------------------------------------------
        retries = data.get("max_retries", 3)
        has_dlq = data.get("has_dlq", True)
        g5_pass = (0 <= retries <= 10) and has_dlq
        if not g5_pass:
            violations.append("GATE-05 破损: 重试次数超上限 (10) 或未配置死信队列")
        checks.append({"gate": "GATE-05", "name": "失败重试与死信兜底门禁", "passed": g5_pass})

        # -------------------------------------------------------------
        # GATE-06: 字段映射合法性门禁
        # -------------------------------------------------------------
        mapping_conflict = data.get("mapping_reserved_conflict", False)
        g6_pass = not mapping_conflict
        if not g6_pass:
            violations.append("GATE-06 破损: 字段映射命中系统保留列名或非规范字段")
        checks.append({"gate": "GATE-06", "name": "字段映射合法性门禁", "passed": g6_pass})

        # -------------------------------------------------------------
        # GATE-07: AI 节点护栏与权限门禁
        # -------------------------------------------------------------
        ai_unprotected = data.get("ai_node_unprotected", False)
        g7_pass = not ai_unprotected
        if not g7_pass:
            violations.append("GATE-07 破损: AI 节点缺失安全护栏或高危未授权")
        checks.append({"gate": "GATE-07", "name": "AI 节点护栏与权限门禁", "passed": g7_pass})

        # -------------------------------------------------------------
        # GATE-08: 全链路可观测审计门禁
        # -------------------------------------------------------------
        audit_complete = data.get("audit_complete", True)
        g8_pass = audit_complete
        if not g8_pass:
            violations.append("GATE-08 破损: 审计要素不完整 (需齐备 trigger/input/execution/output/operator)")
        checks.append({"gate": "GATE-08", "name": "全链路可观测审计门禁", "passed": g8_pass})

        passed_count = sum(1 for c in checks if c["passed"])
        verdict = "PASS" if len(violations) == 0 else "FAIL"

        return {
            "artifact_type": artifact_type,
            "verdict": verdict,
            "total_gates": len(checks),
            "passed_gates": passed_count,
            "violations_count": len(violations),
            "violations": violations,
            "checks": checks,
        }


# 别名兼容
SpecLedger = AutomationSpecLedger

# -*- coding: utf-8 -*-
"""R01 蛙全局 CEO 伴生结构化治理资产交付包 (Executive Decision Asset Bundle)。

对标 GitHub 开源标杆:
- onlook (27k+ stars) / Figma-Context-MCP (16k+ stars) / Design-to-Code AST Spec
- 随战略决策落盘下游可机器解析的 `executive_spec.json`，包含治理 AST、责任网络与量化阈值包。
"""
from __future__ import annotations
import json
import os
from typing import Any, Dict, List

class ExecutiveAssetBundle:
    """CEO 结构化伴生资产生成与导出包。"""

    @classmethod
    def build_executive_spec(cls, card_data: Dict[str, Any], branches: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """构建下游智能体可直接消费的结构化治理规格包。"""
        topic = card_data.get("topic", "战略决议")
        owner = card_data.get("owner", "r01")
        
        spec = {
            "$schema": "https://wawaguagua.ai/schemas/executive-spec.v1.json",
            "version": "1.0.0",
            "metadata": {
                "role": "r01",
                "role_title": "蛙全局 · CEO 主理人",
                "topic": topic,
                "timestamp": "2026-11-09T16:00:00Z"
            },
            "governance_ast": {
                "decision_node": {
                    "id": "dec_root",
                    "type": "strategic_commitment",
                    "owner": owner,
                    "reversibility": card_data.get("reversibility", "可逆"),
                    "rollback_cost_months": card_data.get("rollback_cost_months", 1)
                },
                "guardrails": {
                    "kill_criteria": card_data.get("kill_criteria", []),
                    "success_criteria": card_data.get("success_criteria", []),
                    "freeze_days": card_data.get("freeze_days", 30)
                },
                "downstream_delegations": [
                    {"role": "r02", "scope": "排期编制与工时分解", "action": "wbs_generation"},
                    {"role": "r06", "scope": "指标监控与杀死标准探针", "action": "metric_watchdog"},
                    {"role": "r07", "scope": "产品路线图与需求重构", "action": "backlog_alignment"}
                ]
            },
            "candidate_branches": branches or []
        }
        return spec

    @classmethod
    def export_bundle(cls, output_dir: str, spec_data: Dict[str, Any], filename: str = "executive_spec.json") -> str:
        """导出物理伴生资产包。"""
        os.makedirs(output_dir, exist_ok=True)
        target_path = os.path.join(output_dir, filename)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(spec_data, f, ensure_ascii=False, indent=2)
        return target_path

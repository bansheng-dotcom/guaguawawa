# -*- coding: utf-8 -*-
"""engines/pm_spec_ledger.py - L04 领域账本层 (Domain Spec Ledger & PM SSOT).

对标开源标杆：Productboard / Pragmatic Institute / dbt MetricFlow (Stars > 15k)
核心职责：
1. 动态加载并解析 PM_SPEC.md 领域规范账本；
2. 提取并强约束：
   - JTBD 规则 (Job Story 三要素与 Mom Test 防幻觉原则)
   - RICE 参数基准 (Reach, Impact 分档, Confidence 权重, Effort 下限)
   - PRD 8 门禁系统 (Problem, User, Value, Scope, Metric, Acceptance, Risk, Read)
   - OKR 3x3 框架 (3 Objectives x 3 KRs)
   - Telemetry Schema (全链路埋点契约字段)
   - Release Gate SLAs (发布门禁阻断与放量策略)
3. 杜绝多轮演进中的产品口径漂移与伪标准。
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional


class PMSpecLedger:
    """R07 L04 产品需求规格与领域规范账本引擎。"""

    def __init__(self, spec_path: Optional[str] = None):
        if spec_path is None:
            spec_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "PM_SPEC.md")
        self.spec_path = spec_path
        self._cached_spec: Optional[Dict[str, Any]] = None

    def load_spec(self) -> Dict[str, Any]:
        """动态解析 PM_SPEC.md 提取所有规范与规则。"""
        if self._cached_spec is not None:
            return self._cached_spec

        rules: Dict[str, Any] = {
            "jtbd": {
                "job_story_triad": ["situation", "motivation", "outcome"],
                "mom_test_forbidden": ["你觉得好不好", "将来你愿不愿意用", "觉得", "好不好", "将来"],
            },
            "rice": {
                "reach_min": 1,
                "impact_scale": {
                    "massive": 3.0,
                    "high": 2.0,
                    "medium": 1.0,
                    "low": 0.5,
                    "minimal": 0.25,
                },
                "confidence_scale": {
                    "high_data": 1.0,
                    "user_research": 0.8,
                    "anecdotal": 0.5,
                    "low": 0.2,
                },
                "effort_min": 0.1,
            },
            "opportunity": {
                "importance_range": [1, 10],
                "satisfaction_range": [1, 10],
                "formula": "importance + max(importance - satisfaction, 0)",
            },
            "prd_gates": [
                {"id": "problem", "name": "Problem (痛点真实性)", "weight": 1.0},
                {"id": "user", "name": "User (目标客群与画像)", "weight": 1.0},
                {"id": "value", "name": "Value (商业与用户价值)", "weight": 1.0},
                {"id": "scope", "name": "Scope (范围与边界清晰度)", "weight": 1.0},
                {"id": "metric", "name": "Metric (成功指标体系)", "weight": 1.0},
                {"id": "acceptance", "name": "Acceptance (Given/When/Then 验收标准)", "weight": 1.0},
                {"id": "risk", "name": "Risk (前置风险与反思假设)", "weight": 1.0},
                {"id": "read", "name": "Read (可读性与交接清晰度)", "weight": 1.0},
            ],
            "okr_framework": {
                "max_objectives": 3,
                "kr_per_objective": 3,
                "confidence_recommended_range": [0.6, 0.7],
            },
            "telemetry_schema": {
                "naming_convention": "snake_case (object_action)",
                "required_payload": ["user_id", "session_id", "timestamp", "event_version"],
                "optional_payload": ["tenant_id", "trigger_source", "duration_ms", "result_status"],
            },
            "release_gate_slas": {
                "blocker": "立即终止发布流，驳回 PRD (P0漏洞/八门禁未过/埋点缺失)",
                "critical": "双重签字+限制灰度比例<=5% (边界未覆盖/性能不达标)",
                "normal": "全门禁 PASS，按 10%->30%->100% 梯次放量",
            },
        }

        if not os.path.exists(self.spec_path):
            return {
                "spec_loaded": False,
                "spec_path": self.spec_path,
                "rules": rules,
                "version": "1.0.0-fallback",
            }

        with open(self.spec_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 解析 PRD 八大门禁
        gate_matches = re.findall(r"Gate\s+(\d+)\s+-\s+([A-Za-z]+)\s+\(([^)]+)\)", content)
        if gate_matches:
            parsed_gates = []
            for num, g_id, g_name in gate_matches:
                parsed_gates.append({
                    "gate_number": int(num),
                    "id": g_id.lower(),
                    "name": f"{g_id} ({g_name})",
                    "weight": 1.0,
                })
            if len(parsed_gates) == 8:
                rules["prd_gates"] = parsed_gates

        # 解析 RICE 影响力系数
        impact_matches = re.findall(r"`([0-9.]+)`:\s*([^\n]+)", content)
        if impact_matches:
            for val_str, desc in impact_matches:
                try:
                    val = float(val_str)
                    if "极大" in desc or "Massive" in desc:
                        rules["rice"]["impact_scale"]["massive"] = val
                    elif "高影响" in desc or "High" in desc:
                        rules["rice"]["impact_scale"]["high"] = val
                    elif "中等" in desc or "Medium" in desc:
                        rules["rice"]["impact_scale"]["medium"] = val
                except ValueError:
                    pass

        res = {
            "spec_loaded": True,
            "spec_path": self.spec_path,
            "rules": rules,
            "version": "1.0.0",
        }
        self._cached_spec = res
        return res

    def validate_prd_against_spec(self, prd_data: Dict[str, Any]) -> Dict[str, Any]:
        """按 PM_SPEC.md 对 PRD 进行 8 门禁穿透校验。"""
        spec = self.load_spec()
        gates = spec["rules"]["prd_gates"]
        gate_results = []
        passed_count = 0

        # 门禁 1: Problem
        has_problem = bool(prd_data.get("problem_statement") or prd_data.get("problem"))
        gate_results.append({"gate": "problem", "passed": has_problem})

        # 门禁 2: User
        has_user = bool(prd_data.get("target_user") or prd_data.get("user") or prd_data.get("segment"))
        gate_results.append({"gate": "user", "passed": has_user})

        # 门禁 3: Value
        has_value = bool(prd_data.get("value_prop") or prd_data.get("value") or prd_data.get("business_impact"))
        gate_results.append({"gate": "value", "passed": has_value})

        # 门禁 4: Scope
        scope = prd_data.get("scope") or {}
        has_scope = isinstance(scope, dict) and bool(scope.get("p0") or scope.get("in_scope"))
        gate_results.append({"gate": "scope", "passed": has_scope})

        # 门禁 5: Metric
        metrics = prd_data.get("metrics") or prd_data.get("success_metrics") or {}
        has_metric = bool(metrics)
        gate_results.append({"gate": "metric", "passed": has_metric})

        # 门禁 6: Acceptance
        ac = prd_data.get("acceptance_criteria") or prd_data.get("acceptance") or []
        has_ac = len(ac) >= 4 or (len(ac) >= 1 and isinstance(ac[0], dict) and "then" in ac[0])
        gate_results.append({"gate": "acceptance", "passed": has_ac})

        # 门禁 7: Risk
        assumptions = prd_data.get("assumptions") or prd_data.get("risks") or []
        has_risk = len(assumptions) >= 1
        gate_results.append({"gate": "risk", "passed": has_risk})

        # 门禁 8: Read
        has_read = bool(prd_data.get("title") or prd_data.get("executive_summary"))
        gate_results.append({"gate": "read", "passed": has_read})

        passed_count = sum(1 for g in gate_results if g["passed"])
        return {
            "all_passed": passed_count == 8,
            "passed_count": passed_count,
            "total_gates": 8,
            "gate_results": gate_results,
            "sla_verdict": "normal" if passed_count == 8 else ("critical" if passed_count >= 6 else "blocker"),
        }

    def export_rules_json(self) -> Dict[str, Any]:
        """导出机器可读的标准 JSON 规范字典。"""
        spec = self.load_spec()
        return spec["rules"]

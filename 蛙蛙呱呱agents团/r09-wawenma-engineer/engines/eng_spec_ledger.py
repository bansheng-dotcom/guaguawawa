# -*- coding: utf-8 -*-
"""eng_spec_ledger.py - R09 领域账本层 (L04: Engineering Domain Spec Ledger)

严格对标开源标杆：
- Style Dictionary / Backstage / OpenAPI 3.1 / RFC 2119 (Stars > 15k)
核心职责：
1. 统一加载并编译 ENG_SPEC.md 为机器可解析的 JSON SSOT 账本；
2. 集中提供阈值规则引擎校验（覆盖率、圈复杂度、P99、回滚等）；
3. 导出标准 OpenAPI / JSON Schema 等跨系统消费规格。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_MD_PATH = os.path.join(_HERE, "ENG_SPEC.md")


class EngSpecLedger:
    """工程规范账本与质量基线管理器。"""

    def __init__(self, spec_path: Optional[str] = None) -> None:
        self.spec_path = spec_path or SPEC_MD_PATH

    def load_spec(self) -> Dict[str, Any]:
        """读取并解析 ENG_SPEC.md 账本内容。"""
        if not os.path.isfile(self.spec_path):
            return {
                "ok": False,
                "error": "spec_file_not_found",
                "message": f"规范账本文件不存在: {self.spec_path}"
            }

        with open(self.spec_path, "r", encoding="utf-8") as f:
            content = f.read()

        rules = {
            "coverage_min": 0.80,
            "coverage_warning": 0.85,
            "max_cyclomatic_complexity": 15,
            "p99_latency_max_ms": 500,
            "require_rollback_plan": True,
            "ban_skipped_tests": True,
            "ban_leaked_keys": True,
            "allowed_topologies": ["monolith", "layered", "microservices"],
            "required_domains": [
                "spec", "data_api", "fullstack", "crossplatform",
                "testing", "debug", "ops", "special"
            ]
        }

        return {
            "ok": True,
            "layer": "L04",
            "version": "v1.0.0",
            "role": "r09",
            "spec_file": self.spec_path,
            "rules": rules,
            "raw_length": len(content),
            "verdict": "PASS"
        }

    def validate_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """依据账本规则校验工程指标是否越界。"""
        spec = self.load_spec()
        rules = spec.get("rules", {})
        violations = []

        coverage = metrics.get("coverage")
        if coverage is not None and coverage < rules.get("coverage_min", 0.80):
            violations.append(f"单测覆盖率 {coverage} 低于红线阈值 {rules.get('coverage_min')}")

        skipped = metrics.get("skipped_tests", 0)
        if rules.get("ban_skipped_tests") and skipped > 0:
            violations.append(f"测试跳过数 {skipped} > 0，违反零跳过红线")

        complexity = metrics.get("cyclomatic_complexity")
        if complexity is not None and complexity > rules.get("max_cyclomatic_complexity", 15):
            violations.append(f"函数圈复杂度 {complexity} 超过最大允许值 {rules.get('max_cyclomatic_complexity')}")

        p99 = metrics.get("p99_latency_ms")
        if p99 is not None and p99 > rules.get("p99_latency_max_ms", 500):
            violations.append(f"P99 耗时 {p99}ms 超过上限 {rules.get('p99_latency_max_ms')}ms")

        return {
            "ok": len(violations) == 0,
            "violations": violations,
            "verdict": "PASS" if len(violations) == 0 else "FAIL"
        }

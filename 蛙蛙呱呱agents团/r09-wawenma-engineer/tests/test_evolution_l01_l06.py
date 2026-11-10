# -*- coding: utf-8 -*-
"""test_evolution_l01_l06.py - R09 蛙稳码十维元模型配套集成演进测试套件 (L01~L06)

覆盖：
- T_L01: 工具实体层 (AST 语法树审查、圈复杂度测算、沙箱探针)
- T_L02: 意图解构层 (自然语言需求反编译、Kahn 拓扑 DAG 算法)
- T_L03: 自愈反思层 (自愈字段修复、三类红线拦截)
- T_L04: 领域账本层 (ENG_SPEC.md 账本解析、阈值指标检验)
- T_L05: 质感去劣化 (代码/文档套话过滤、SlopGuard 行动力得分)
- T_L06: 横向决策层 (三维方案裂变、权衡矩阵计算)
"""
from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENT_ROOT = os.path.dirname(_HERE)
for p in (_AGENT_ROOT, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from engines.runtime_engine import EngineeringRuntimeEngine
from engines.intent_compiler import EngineeringIntentCompiler
from engines.reflexive_healer import EngineeringReflexiveHealer
from engines.eng_spec_ledger import EngSpecLedger
from engines.eng_slop_guard import EngSlopGuard
from engines.scenario_matrix import ScenarioMatrix


class TestEvolutionL01L06(unittest.TestCase):
    """十维演进集成测试门禁 (L01 ~ L06)。"""

    def test_l01_runtime_engine_probe(self):
        eng = EngineeringRuntimeEngine()
        health = eng.probe_health()
        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["layer"], "L01")
        self.assertTrue(len(health["capabilities"]) >= 3)

    def test_l01_runtime_engine_ast(self):
        eng = EngineeringRuntimeEngine()
        code = "def add(a, b):\n    if a > 0:\n        return a + b\n    return b\n"
        res = eng.inspect_python_code(code)
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["functions"]), 1)
        self.assertEqual(res["functions"][0]["name"], "add")
        self.assertGreaterEqual(res["cyclomatic_complexity"], 2)
        self.assertFalse(res["has_unsafe_eval"])

    def test_l02_intent_compiler(self):
        comp = EngineeringIntentCompiler()
        prompt = "开发一个订单管理系统，需要MySQL表结构设计、REST API契约以及高覆盖率测试"
        res = comp.decompile(prompt)
        self.assertTrue(res["ok"])
        self.assertIn("data_api", res["matched_domains"])
        self.assertIn("testing", res["matched_domains"])
        self.assertTrue(res["is_valid_dag"])
        self.assertEqual(res["verdict"], "PASS")

    def test_l03_reflexive_healer_normal(self):
        healer = EngineeringReflexiveHealer()
        packet = {"title": "用户中心", "steps": [{"name": "step1", "description": "创建普通表"}]}
        res = healer.heal_engineering_packet(packet)
        self.assertTrue(res["ok"])
        self.assertTrue(res["healed"])
        self.assertEqual(res["verdict"], "PASS")
        self.assertIn("checks", res["data"])
        self.assertIn("rollback_steps", res["data"])

    def test_l03_reflexive_healer_redline(self):
        healer = EngineeringReflexiveHealer()
        dirty_packet = {"title": "跳过测试跑批", "test_skipped": True}
        res = healer.heal_engineering_packet(dirty_packet)
        self.assertFalse(res["ok"])
        self.assertEqual(res["verdict"], "BLOCKED")
        self.assertTrue(len(res["violations"]) >= 1)

    def test_l04_spec_ledger(self):
        ledger = EngSpecLedger()
        spec = ledger.load_spec()
        self.assertTrue(spec["ok"])
        self.assertEqual(spec["layer"], "L04")
        self.assertIn("coverage_min", spec["rules"])
        
        # 指标测试
        valid = ledger.validate_metrics({"coverage": 0.88, "cyclomatic_complexity": 8})
        self.assertTrue(valid["ok"])
        invalid = ledger.validate_metrics({"coverage": 0.70, "skipped_tests": 2})
        self.assertFalse(invalid["ok"])

    def test_l05_slop_guard(self):
        guard = EngSlopGuard()
        res = guard.audit_text("此处编写业务逻辑，TODO: 稍后补充")
        self.assertFalse(res["is_clean"])
        self.assertLess(res["score"], 100)
        self.assertIn("/* 已补充防御性参数校验与异常处理 */", res["cleaned_text"])

    def test_l06_scenario_matrix(self):
        matrix = ScenarioMatrix()
        res = matrix.generate_matrix("智能调度核心")
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["scenarios"]), 3)
        self.assertIn("recommendation", res)


if __name__ == "__main__":
    unittest.main()

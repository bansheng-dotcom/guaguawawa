# -*- coding: utf-8 -*-
"""L01-L10 十维演进元模型核心引擎集成测试套件。
针对 engines/ 下的 ast_inspector, intent_compiler, critic_reflexion, spec_registry,
slop_guard, scenario_matrix, sarif_exporter, diff_patch_reviewer, session_memory,
telemetry_watchdog 进行全面闭环断言测试。
"""
from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
for p in (PARENT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)


from engines.ast_inspector import ASTCodeInspector
from engines.intent_compiler import IntentDAGCompiler
from engines.critic_reflexion import CriticReflexionEngine
from engines.spec_registry import ReviewSpecRegistry
from engines.slop_guard import SlopGuard
from engines.scenario_matrix import ScenarioMatrixPlanner
from engines.sarif_exporter import SarifExporter
from engines.diff_patch_reviewer import DiffPatchReviewer
from engines.session_memory import ReviewSessionMemory
from engines.telemetry_watchdog import ExecutionWatchdog, TelemetryLogger


class TestEnginesEvolutionL01ToL10(unittest.TestCase):

    def test_l01_ast_inspector(self):
        inspector = ASTCodeInspector()
        sample_code = """
def good_func(x):
    if x > 0:
        return x * 2
    return 0

def bad_stub():
    pass

def bad_swallow():
    try:
        good_func(1)
    except:
        pass
"""
        res = inspector.analyze_source(sample_code, "test.py")
        self.assertTrue(res["ok"])
        self.assertEqual(res["stats"]["function_count"], 3)
        issues = {i["type"] for i in res["issues"]}
        self.assertIn("STUB_IMPLEMENTATION", issues)
        self.assertIn("SILENT_EXCEPTION_SWALLOW", issues)

    def test_l02_intent_compiler(self):
        compiler = IntentDAGCompiler()
        query = "请先做交付物盘点，再跑门禁与强度审计，最后做禁词扫描与人工打包"
        res = compiler.compile(query)
        self.assertTrue(res["is_valid_dag"])
        self.assertGreaterEqual(res["node_count"], 4)
        seq = res["execution_sequence"]
        self.assertIn("task_01_artifact_inventory", seq)

    def test_l03_critic_reflexion(self):
        refl = CriticReflexionEngine()
        # 1. 别名自愈
        h1 = refl.diagnose_and_heal_review_input("inventory", {"artifacts": [{"path": "a.txt"}]})
        self.assertTrue(h1["was_healed"])
        self.assertIn("items", h1["healed_payload"])
        # 2. 身份红线反思
        h2 = refl.diagnose_and_heal_review_input("package", {"reviewer": "bob", "producer": "bob"})
        self.assertTrue(h2["has_critical_blocker"])

    def test_l04_spec_registry(self):
        reg = ReviewSpecRegistry()
        raw_spec = reg.get_raw_spec()
        self.assertIn("REVIEW_SPEC", raw_spec)
        check_res = reg.validate_against_spec("complexity", 12)
        self.assertTrue(check_res["passed"])

    def test_l05_slop_guard(self):
        sg = SlopGuard()
        bad_text = "代码整体结构良好，建议后续进一步加强。"
        audit_bad = sg.audit_text(bad_text)
        self.assertFalse(audit_bad["is_actionable"])
        self.assertGreater(len(audit_bad["slop_hits"]), 0)

        good_text = "在 r04/agent.py:42 处的 parse_args 函数缺少 try-except 保护。"
        audit_good = sg.audit_text(good_text)
        self.assertTrue(audit_good["is_actionable"])

    def test_l06_scenario_matrix(self):
        planner = ScenarioMatrixPlanner()
        res = planner.evaluate_scenarios({"blockers": 0, "warnings": 1, "code_score": 85})
        self.assertEqual(len(res["scenarios"]), 3)
        self.assertIn("### [Board]", res["markdown_board"])

    def test_l07_sarif_exporter(self):
        exporter = SarifExporter()
        findings = [{"type": "MOCK_ISSUE", "severity": "blocker", "message": "error msg", "target": "a.py", "line": 10}]
        doc = exporter.export_sarif(findings)
        self.assertEqual(doc["version"], "2.1.0")
        self.assertEqual(doc["runs"][0]["results"][0]["level"], "error")

    def test_l08_diff_patch_reviewer(self):
        dpr = DiffPatchReviewer()
        diff = """--- a/f.py
+++ b/f.py
@@ -5,2 +5,3 @@
 line5
+line6_new
"""
        findings = [
            {"target": "f.py", "line": 5, "type": "OLD"},
            {"target": "f.py", "line": 6, "type": "NEW"},
        ]
        res = dpr.filter_incremental_findings(findings, diff)
        self.assertEqual(res["incremental_count"], 1)
        self.assertEqual(res["legacy_count"], 1)
        self.assertEqual(res["incremental_findings"][0]["line"], 6)

    def test_l09_session_memory(self):
        mem = ReviewSessionMemory()
        sid = mem.record_round("review", "src/foo.py", "PASS", [])
        q = mem.resolve_pronoun_query("针对刚才的文件做复审")
        self.assertEqual(q["resolved_target"], "src/foo.py")

    def test_l10_telemetry_watchdog(self):
        wd = ExecutionWatchdog()
        res = wd.execute_with_guard("unit_test_op", lambda: 100)
        self.assertTrue(res["ok"])
        self.assertEqual(res["result"], 100)
        self.assertIn("trace_", res["trace_id"])


if __name__ == "__main__":
    unittest.main()

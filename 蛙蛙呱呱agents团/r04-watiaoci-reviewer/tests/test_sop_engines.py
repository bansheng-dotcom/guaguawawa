# -*- coding: utf-8 -*-
"""SOP 演进统一自测与全量回归套件。"""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
for p in (_PARENT, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from engines.code_metric_engine import CodeMetricEngine
from engines.review_dag_engine import ReviewDAGEngine
from engines.reflexion_engine import ReflexionSelfHealingEngine
from engines.review_spec_engine import ReviewSpecEngine
from engines.slop_guard_engine import SlopGuardEngine
from engines.scenario_dashboard_engine import ScenarioDashboardEngine
from engines.sarif_export_engine import SarifExportEngine
from engines.diff_slice_engine import DiffSliceEngine
from engines.session_memory_engine import SessionMemoryEngine
from engines.industrial_resilience_engine import IndustrialResilienceEngine


class TestSOPEvolutionEngines(unittest.TestCase):
    def test_r01_code_metric(self):
        res = CodeMetricEngine.analyze_source("def foo(x):\n    if x > 0:\n        return True\n    return False\n")
        self.assertTrue(res["ok"])
        self.assertEqual(res["functions_count"], 1)
        self.assertGreaterEqual(res["complexity_by_func"]["foo"], 2)

    def test_r02_review_dag(self):
        dag = ReviewDAGEngine.compile_intent_to_dag("做成品清单清点，然后做判据审查，最后生成人工评审包")
        self.assertTrue(dag["ok"])
        self.assertFalse(dag["has_cycle"])
        order = dag["execution_order"]
        self.assertIn("artifact_inventory", order)
        self.assertIn("criteria_review", order)
        self.assertIn("human_package", order)

    def test_r03_reflexion(self):
        ok, healed, refs, viols = ReflexionSelfHealingEngine.audit_and_heal_payload(
            {"item_id": "ITM-01", "verdict": "FAIL"}, ["id", "status"]
        )
        self.assertTrue(ok)
        self.assertEqual(healed["id"], "ITM-01")
        self.assertEqual(healed["status"], "FAIL")
        self.assertEqual(len(viols), 0)

        # 测红线拦截
        bad_ok, _, _, bad_viols = ReflexionSelfHealingEngine.audit_and_heal_payload(
            {"item_id": "ITM-02", "content": "这是R04自评放行报告"}, ["id"]
        )
        self.assertFalse(bad_ok)
        self.assertGreaterEqual(len(bad_viols), 1)

    def test_r04_spec_engine(self):
        spec = ReviewSpecEngine.load_spec()
        self.assertTrue(spec["ok"])
        self.assertIn("P-THEATRE", spec["penalties"])
        eval_res = ReviewSpecEngine.evaluate_verdict(100, ["P-SLOP"])
        self.assertEqual(eval_res["verdict"], "PASS")
        self.assertEqual(eval_res["final_score"], 90)

    def test_r05_slop_guard(self):
        res = SlopGuardEngine.audit_critique("整体良好，建议进一步加强")
        self.assertTrue(res["is_slop"])
        self.assertFalse(res["actionable"])

        good = SlopGuardEngine.audit_critique("第15行请替换裸except为具体捕获", line_number=15, file_anchor="test.py")
        self.assertFalse(good["is_slop"])
        self.assertTrue(good["actionable"])

    def test_r06_scenario_dashboard(self):
        findings = [
            {"id": "F1", "severity": "MEDIUM", "penalty": 10},
            {"id": "F2", "severity": "HIGH", "penalty": 20},
        ]
        res = ScenarioDashboardEngine.generate_three_tier_dashboard(findings)
        self.assertIn("aggressive", res["scenarios"])
        self.assertIn("balanced", res["scenarios"])
        self.assertIn("strict", res["scenarios"])
        self.assertEqual(res["scenarios"]["aggressive"]["verdict"], "PASS")

    def test_r07_sarif_export(self):
        findings = [
            {"pattern": "P-THEATRE", "severity": "CRITICAL", "message": "Gate bypass", "file_path": "a.py", "line": 10}
        ]
        out_path = os.path.join(_HERE, "examples", "test_out.sarif.json")
        sarif = SarifExportEngine.export_sarif(findings, output_file=out_path)
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertEqual(len(sarif["runs"][0]["results"]), 1)
        if os.path.exists(out_path):
            os.remove(out_path)

    def test_r08_diff_slice(self):
        diff = "--- a/test.py\n+++ b/test.py\n@@ -1,3 +1,4 @@\n a = 1\n+b = 2\n"
        findings = [
            {"file_path": "test.py", "line": 2, "message": "line 2 issue"},
            {"file_path": "test.py", "line": 50, "message": "line 50 issue"}
        ]
        res = DiffSliceEngine.filter_incremental_findings(findings, diff)
        self.assertEqual(res["incremental_count"], 1)
        self.assertEqual(res["suppressed_count"], 1)

    def test_r09_session_memory(self):
        state_path = os.path.join(_HERE, "workspace", "test_sop_mem.json")
        mem = SessionMemoryEngine("unit_test", state_file=state_path)
        mem.current_state["last_inspected_target"] = "agent.py"
        v1 = mem.checkpoint("Initial")
        mem.current_state["last_inspected_target"] = "other.py"
        self.assertEqual(mem.current_state["last_inspected_target"], "other.py")
        mem.rollback(v1)
        self.assertEqual(mem.current_state["last_inspected_target"], "agent.py")
        if os.path.exists(state_path):
            os.remove(state_path)

    def test_r10_resilience(self):
        res = IndustrialResilienceEngine.run_with_watchdog(lambda: 42, timeout_seconds=2.0)
        self.assertTrue(res["ok"])
        self.assertEqual(res["result"], 42)


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""SOP v13.0 L01~L10 演进回归测试（真实引擎，非占位）。

运行：
    python tests/test_evolution_l01_l10.py -v
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engines import (R20AssetBundle, R20DiffPatchEngine, R20IntentCompiler,  # noqa: E402
                     R20ReflexiveHealer, R20RuntimeEngine, R20ScenarioMatrix,
                     R20SessionMemory, R20SpecLedger, R20TelemetryWatchdog,
                     PatchError, R20TelemetryWatchdog as _WD, SreSlopGuard)
from engines.telemetry_watchdog import (CLOSED, HALF_OPEN, OPEN,  # noqa: E402
                                       TelemetryTracer, WatchdogBreaker)


class TestL01Runtime(unittest.TestCase):
    def setUp(self):
        self.eng = R20RuntimeEngine()

    def test_sli_golden_and_budget_conservation(self):
        out = self.eng.compute_sli([True] * 9995 + [False] * 5, slo=0.999)
        self.assertEqual(out["availability"], 0.9995)
        self.assertEqual(out["allowed_failures"], 10)
        self.assertEqual(out["budget_remaining"], 5)
        self.assertEqual(out["burn_rate"], 0.5)
        self.assertEqual(out["conservation"]["delta"], 0.0)
        self.assertTrue(out["meets_slo"])

    def test_sli_rejects_empty(self):
        with self.assertRaises(Exception):
            self.eng.compute_sli([], slo=0.999)

    def test_incident_mttr_and_mtbf(self):
        out = self.eng.compute_incident_metrics([
            {"started_at": "2026-11-01T10:00:00", "resolved_at": "2026-11-01T10:20:00",
             "severity": "critical"},
            {"started_at": "2026-11-01T14:00:00", "resolved_at": "2026-11-01T14:40:00",
             "severity": "warning"}])
        self.assertEqual(out["mttr_minutes"], 30.0)
        self.assertEqual(out["mtbf_hours"], 3.667)
        self.assertEqual(out["severity_distribution"]["critical"], 1)

    def test_rpo_rto_boundary(self):
        self.assertTrue(self.eng.check_rpo_rto({"rpo_hours": 0.5, "rto_hours": 2.0})["ok"])
        bad = self.eng.check_rpo_rto({"rpo_hours": 2.0, "rto_hours": 6.0})
        self.assertFalse(bad["ok"])
        self.assertEqual(len([c for c in bad["checks"] if not c["ok"]]), 2)

    def test_latency_percentiles(self):
        out = self.eng.compute_latency_percentiles([10, 20, 30, 40, 100])
        self.assertEqual(out["p50"], 30.0)
        self.assertEqual(out["p95"], 88.0)
        self.assertEqual(out["count"], 5)

    def test_probe_healthy(self):
        out = self.eng.probe_health()
        self.assertTrue(out["ok"], out["checks"])
        self.assertEqual(out["status"], "HEALTHY")


class TestL02Intent(unittest.TestCase):
    def setUp(self):
        self.eng = R20IntentCompiler()
        self.text = ("支付服务 P1 故障，30 分钟内恢复，RTO<=2h，RPO<=0.5h，"
                     "影响 3 万用户，先回滚再复盘")

    def test_entities(self):
        e = self.eng.extract_entities(self.text)
        self.assertEqual(e["service"], "支付服务")
        self.assertEqual(e["severity"], "critical")
        self.assertEqual(e["window_hours"], 0.5)
        self.assertEqual(e["rto_hours"], 2.0)
        self.assertEqual(e["rpo_hours"], 0.5)
        self.assertEqual(e["affected_users"], 30000)
        self.assertTrue(e["requires_rollback"])

    def test_dag_shape(self):
        out = self.eng.compile_request(self.text)
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["stages"]), 5)
        self.assertEqual(out["dag"], {"vertices": 5, "edges": 4, "is_dag": True})
        self.assertEqual(out["parallel_waves"], 4)
        self.assertEqual(out["topo_order"][0], "audit")
        self.assertEqual(out["topo_order"][-1], "review")
        self.assertEqual(out["bottleneck"], "recover")

    def test_critical_path_and_deadline(self):
        out = self.eng.compile_request(self.text, deadline_hours=7)
        self.assertEqual(out["critical_path"]["hours"], 8.25)
        self.assertEqual(out["critical_path"]["path"],
                         ["probe", "diagnose", "recover", "review"])
        self.assertFalse(out["deadline_feasible"])
        out2 = self.eng.compile_request(self.text, deadline_hours=12)
        self.assertTrue(out2["deadline_feasible"])

    def test_cycle_detection(self):
        bad = [{"id": "a", "deps": ["b"], "effort_hours": 1},
               {"id": "b", "deps": ["a"], "effort_hours": 1}]
        out = self.eng.topo_sort(bad)
        self.assertFalse(out["ok"])
        self.assertTrue(out["cycle_detected"])

    def test_markdown(self):
        md = self.eng.render_markdown(self.eng.compile_request(self.text))
        self.assertIn("恢复 DAG 编译单", md)
        self.assertIn("diagnose", md)


class TestL03Healer(unittest.TestCase):
    def setUp(self):
        self.eng = R20ReflexiveHealer()

    def test_normalize_aliases(self):
        out = self.eng.heal_artifact({"severity": "P0", "status": "进行中",
                                      "component_status": "正常"})
        h = out["healed"]
        self.assertEqual(h["severity"], "critical")
        self.assertEqual(h["status"], "investigating")
        self.assertEqual(h["component_status"], "operational")
        self.assertEqual(h["owner"], "蛙值守")

    def test_redline_unauthorized_restore(self):
        out = self.eng.audit_redlines("直接恢复生产")
        self.assertTrue(out["blocked"])
        self.assertEqual(out["violations"][0]["code"], "RL-01")
        self.assertIn("[REDLINE BLOCKED]", out["banner"])

    def test_redline_with_handoff_passes(self):
        out = self.eng.audit_redlines("直接恢复生产", {"handoff": "R01 审批",
                                                      "restored_count": 3,
                                                      "checksum": "sha256:abc"})
        self.assertFalse(out["blocked"], out["violations"])

    def test_credential_and_scope(self):
        self.assertEqual(self.eng.audit_redlines("", {"note": "password=123"})
                         ["violations"][0]["code"], "RL-02")
        self.assertEqual(self.eng.audit_redlines("", {"summary": "给出统计显著性结论"})
                         ["violations"][0]["code"], "RL-04")

    def test_fake_drill(self):
        out = self.eng.audit_redlines("", {"summary": "演练通过，可恢复"})
        self.assertIn("RL-05", [v["code"] for v in out["violations"]])

    def test_reflexive_loop_and_idempotent(self):
        out = self.eng.reflexive_loop({"severity": "P1", "status": "已恢复"})
        self.assertTrue(out["ok"])
        self.assertTrue(out["converged"])
        self.assertEqual(out["rounds"], 1)
        self.assertTrue(self.eng.verify_idempotent({"severity": "P2"})["is_fixpoint"])


class TestL04SpecLedger(unittest.TestCase):
    def setUp(self):
        self.ledger = R20SpecLedger()

    def test_load_spec_and_fingerprint(self):
        spec = self.ledger.load_spec()
        self.assertTrue(spec["ok"], spec["missing_north_star"])
        self.assertEqual(spec["gates_count"], 8)
        self.assertEqual(len(spec["sha256"]), 64)
        self.assertEqual(spec["north_star"]["availability_slo"], 0.999)

    def test_demo_artifact_all_gates_pass(self):
        out = self.ledger.verify_gate_compliance("release", self.ledger.demo_artifact())
        self.assertTrue(out["ok"], out["failed_gates"])
        self.assertEqual(out["passed"], 8)

    def test_bad_artifact_fails(self):
        bad = {"availability": 0.95, "slo": 0.999,
               "summary": "token=abc", "checks": []}
        out = self.ledger.verify_gate_compliance("release", bad)
        self.assertFalse(out["ok"])
        self.assertIn("G8", out["failed_gates"])
        self.assertIn("G2", out["failed_gates"])

    def test_export(self):
        tmp = tempfile.mkdtemp(prefix="r20_spec_")
        out = self.ledger.export_gates(tmp)
        self.assertTrue(os.path.isfile(out["gates_path"]))
        self.assertTrue(os.path.isfile(out["matrix_path"]))
        self.assertIn("发布硬门禁矩阵", open(out["matrix_path"], encoding="utf-8").read())


class TestL05Slop(unittest.TestCase):
    def setUp(self):
        self.guard = SreSlopGuard()

    def test_audit_hits(self):
        out = self.guard.audit("整体稳定，运行正常，持续关注")
        self.assertTrue(out["has_slop"])
        self.assertEqual(out["hit_count"], 3)
        self.assertFalse(out["has_quantified_evidence"])
        self.assertFalse(out["has_dri"])

    def test_clean_removes_and_injects(self):
        out = self.guard.clean("整体稳定，运行正常，持续关注，视情况而定"
                               "，相关细节待定，基本可用")
        self.assertEqual(out["after"]["hit_count"], 0)
        self.assertEqual(out["after"]["verdict"], "PASS")
        self.assertTrue(out["after"]["has_dri"])
        self.assertGreater(out["actionability_gain"], 0)
        self.assertIn("99.9%", out["cleaned_text"])

    def test_quantified_report_passes(self):
        out = self.guard.audit("可用率 99.95%，错误预算剩余 5 次；"
                               "责任人 蛙值守，截止 24 小时提交 RCA")
        self.assertEqual(out["verdict"], "PASS")
        self.assertEqual(out["actionability"], 100)


class TestL06Scenario(unittest.TestCase):
    def setUp(self):
        self.eng = R20ScenarioMatrix()

    def test_three_scenarios_and_weights(self):
        out = self.eng.compile_matrix("支付服务", "critical")
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["scenarios"]), 3)
        self.assertAlmostEqual(sum(out["weights"].values()), 1.0, places=4)
        self.assertEqual(out["ranking"][0], "SCN_B_STEADY")
        self.assertTrue(out["rank_stable"], out["sensitivity_winners"])
        self.assertEqual([r["rank"] for r in out["scenarios"]], [1, 2, 3])

    def test_severity_changes_weights(self):
        c = self.eng.compile_matrix("支付服务", "critical")["weights"]
        m = self.eng.compile_matrix("支付服务", "minor")["weights"]
        self.assertGreater(c["speed"], m["speed"])
        self.assertLess(c["evidence"], m["evidence"])

    def test_markdown(self):
        md = self.eng.render_markdown(self.eng.compile_matrix("支付服务", "major"))
        self.assertIn("三维处置方案权衡", md)
        self.assertIn("推荐", md)


class TestL07Bundle(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="r20_bundle_")
        self.out = R20AssetBundle(self.dir).build("TST")

    def test_files_and_hashes(self):
        self.assertTrue(self.out["ok"])
        self.assertEqual(len(self.out["files"]), 3)
        for name in self.out["files"]:
            path = os.path.join(self.dir, name)
            self.assertTrue(os.path.isfile(path))
        for role, sha in self.out["fingerprints"].items():
            self.assertEqual(len(sha), 64, role)

    def test_sarif_contract(self):
        single = json.load(open(self.out["paths"]["sarif"], encoding="utf-8"))
        self.assertEqual(single["version"], "2.1.0")
        self.assertIn("sarif-2.1.0", single["$schema"])
        self.assertEqual(single["runs"][0]["tool"]["driver"]["name"], "R20-蛙值守")
        self.assertGreaterEqual(len(single["runs"][0]["results"]), 3)

    def test_vega_contract(self):
        vega = json.load(open(self.out["paths"]["vega"], encoding="utf-8"))
        self.assertIn("vega-lite/v5", vega["$schema"])
        self.assertEqual(len(vega["data"]["values"]), 7)


class TestL08Patch(unittest.TestCase):
    def setUp(self):
        self.eng = R20DiffPatchEngine()

    def test_diff_and_apply_roundtrip(self):
        old = {"a": {"b": [1, 2, 3]}, "keep": True}
        new = {"a": {"b": [1, 2, 4, 5]}, "added": "x"}
        ops = self.eng.diff(old, new)
        self.assertTrue(any(op["op"] == "replace" for op in ops))
        self.assertTrue(any(op["op"] == "add" for op in ops))
        self.assertTrue(any(op["op"] == "remove" for op in ops))
        self.assertEqual(self.eng.apply_patch(old, ops), new)

    def test_pointer_escape(self):
        ops = self.eng.diff({"a/b": 1}, {"a/b": 2})
        self.assertEqual(ops[0]["path"], "/a~1b")
        self.assertEqual(self.eng.apply_patch({"a/b": 1}, ops), {"a/b": 2})

    def test_test_op_failure(self):
        with self.assertRaises(PatchError):
            self.eng.apply_patch({"a": 1}, [{"op": "test", "path": "/a", "value": 2}])

    def test_invariants(self):
        bad = {"rules": [{"id": "r1", "severity": "fatal"}],
               "escalation": [{"level": 2}, {"level": 1}]}
        out = self.eng.verify_invariants(bad, "alert")
        self.assertFalse(out["ok"])
        self.assertEqual(len([c for c in out["checks"] if not c["ok"]]), 2)
        dup = {"monitors": [{"id": "m1", "interval_seconds": 5},
                            {"id": "m1", "interval_seconds": 60}]}
        self.assertFalse(self.eng.verify_invariants(dup, "monitor")["ok"])

    def test_demo_end_to_end(self):
        out = self.eng.demo()
        self.assertTrue(out["ok"], out)


class TestL09Memory(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="r20_mem_")
        self.mem = R20SessionMemory(self.dir)

    def test_slot_sync(self):
        self.mem.update_slot("service", "订单服务")
        self.assertEqual(self.mem.state["entities"]["service"], "订单服务")

    def test_snapshot_rollback(self):
        self.mem.update_slot("alert_threshold", 0.95)
        snap = self.mem.snapshot("v1")
        self.mem.update_slot("alert_threshold", 0.8)
        out = self.mem.rollback(snap["version"])
        self.assertTrue(out["ok"])
        self.assertEqual(self.mem.state["slots"]["alert_threshold"], 0.95)
        self.assertFalse(self.mem.rollback(999)["ok"])

    def test_disambiguation(self):
        self.mem.update_slot("service", "支付服务")
        self.mem.update_slot("alert_threshold", 0.95)
        out = self.mem.disambiguate_query(
            "按刚才第二套方案调整，把上次那个服务的阈值调高0.05")
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["resolved"]), 3)
        self.assertEqual(out["slots"]["scenario"], "SCN_B_STEADY")
        self.assertEqual(out["slots"]["alert_threshold"], 1.0)

    def test_persistence(self):
        self.mem.update_slot("service", "搜索服务")
        self.mem.save()
        again = R20SessionMemory(self.dir)
        self.assertEqual(again.state["slots"]["service"], "搜索服务")

    def test_demo(self):
        self.assertTrue(self.mem.demo()["ok"])


class TestL10Watchdog(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="r20_tel_")
        self.eng = R20TelemetryWatchdog(self.dir)

    def test_breaker_three_states(self):
        now = [1000.0]
        br = WatchdogBreaker(failure_threshold=2, recovery_timeout=10,
                             clock=lambda: now[0])
        br.record_failure(); br.record_failure()
        self.assertEqual(br.state, OPEN)
        self.assertFalse(br.allow())
        now[0] += 11
        self.assertTrue(br.allow())
        self.assertEqual(br.state, HALF_OPEN)
        br.record_success()
        self.assertEqual(br.state, CLOSED)

    def test_backoff_bounds_and_determinism(self):
        a = [self.eng.compute_backoff(i, 0.5, 30.0, random.Random(7)) for i in range(6)]
        b = [self.eng.compute_backoff(i, 0.5, 30.0, random.Random(7)) for i in range(6)]
        self.assertEqual(a, b)
        self.assertLessEqual(a[0], 0.5)
        self.assertLessEqual(a[5], 30.0)
        self.assertGreater(len(set(a)), 1)

    def test_execute_success_and_telemetry_integrity(self):
        out = self.eng.execute_with_resilience("t.ok", lambda: 42)
        self.assertTrue(out["ok"])
        self.assertEqual(out["result"], 42)
        with open(self.eng.telemetry_path, encoding="utf-8") as f:
            line = f.read().splitlines()[-1]
        rec = json.loads(line)
        for key in ("trace_id", "span_id", "sha256", "duration_ms", "status"):
            self.assertIn(key, rec)
        raw = json.dumps({k: v for k, v in rec.items() if k != "sha256"},
                         ensure_ascii=False, sort_keys=True)
        self.assertEqual(hashlib.sha256(raw.encode("utf-8")).hexdigest(), rec["sha256"])

    def test_execute_exhaustion_opens_breaker(self):
        br = WatchdogBreaker(failure_threshold=2)
        tracer = TelemetryTracer(os.path.join(self.dir, "t2.jsonl"))

        def boom():
            raise RuntimeError("db timeout")

        out = self.eng.execute_with_resilience("t.boom", boom, retries=2,
                                               breaker=br, tracer=tracer)
        self.assertFalse(out["ok"])
        self.assertEqual(out["attempts"], 2)
        self.assertEqual(br.state, OPEN)
        self.assertEqual(len(out["backoffs"]), 1)

    def test_probe_health(self):
        out = self.eng.probe_health()
        self.assertTrue(out["ok"], out["checks"])
        self.assertEqual(out["status"], "HEALTHY")


if __name__ == "__main__":
    unittest.main(verbosity=2)

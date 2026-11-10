# -*- coding: utf-8 -*-
"""tests/test_evolution_cycle2.py — R19 蛙智模 Cycle 2 深度增强验收套件。

Cycle 1 已完成十层全绿；Cycle 2 对每层做「真实能力加深」，本套件逐层验证新增
能力与旧行为兼容性（严格超集），不依赖网络、不依赖随机。

运行：
    python -m unittest tests.test_evolution_cycle2 -v
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = os.path.dirname(HERE)
REPO = os.path.dirname(AGENTS)
for _p in (HERE, AGENTS, REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

from engines import (  # noqa: E402
    R19RuntimeEngine, MetricSandboxError, R19IntentCompiler,
    R19ReflexiveHealer, R19SpecLedger, MLSlopGuard, R19ScenarioMatrix,
    R19AssetBundle, R19DiffPatchEngine, R19SessionMemory,
    R19TelemetryWatchdog, SlidingWindowBreaker,
)
import auto_evolve_runner as runner  # noqa: E402

TMP_ROOT = os.path.join(HERE, "workspace", "tmp")
os.makedirs(TMP_ROOT, exist_ok=True)


def _tmpdir(prefix: str) -> str:
    return tempfile.mkdtemp(prefix=prefix, dir=TMP_ROOT)


class TestL01DeepMetrics(unittest.TestCase):
    def test_multiclass_macro_weighted_known_values(self):
        eng = R19RuntimeEngine()
        recs = [
            {"expected": "pos", "predicted": "pos"},
            {"expected": "pos", "predicted": "neg"},
            {"expected": "neg", "predicted": "neg"},
            {"expected": "neg", "predicted": "neg"},
        ]
        out = eng.compute_multiclass_metrics(recs)
        self.assertTrue(out["ok"])
        self.assertEqual(out["n"], 4)
        self.assertEqual(out["accuracy"], 0.75)
        self.assertEqual(out["per_class"]["pos"]["f1"], 0.6667)
        self.assertEqual(out["per_class"]["neg"]["f1"], 0.8)
        self.assertEqual(out["per_class"]["neg"]["precision"], 0.6667)
        self.assertEqual(out["macro_f1"], 0.7334)
        self.assertEqual(out["weighted_f1"], 0.7334)
        self.assertEqual(out["micro_f1"], 0.75)
        self.assertEqual(out["conservation"]["delta"], 0.0)
        self.assertEqual(out["labels"], ["neg", "pos"])

    def test_agreement_kappa_mcc(self):
        eng = R19RuntimeEngine()
        binary = eng.compute_classification_metrics([
            {"expected": "pass", "predicted": "pass"},
            {"expected": "pass", "predicted": "fail"},
            {"expected": "fail", "predicted": "fail"},
            {"expected": "fail", "predicted": "fail"},
        ])
        out = eng.compute_agreement_metrics(binary)
        self.assertEqual(out["cohen_kappa"], 0.5)
        self.assertEqual(out["mcc"], 0.5774)
        self.assertEqual(out["balanced_accuracy"], 0.75)
        self.assertIn(out["kappa_band"], ("moderate", "substantial"))

    def test_multiclass_rejects_empty(self):
        with self.assertRaises(MetricSandboxError):
            R19RuntimeEngine().compute_multiclass_metrics([{"expected": None}])


class TestL02Cpm(unittest.TestCase):
    def _stages(self):
        return [
            {"id": "A", "deps": [], "estimated_hours": 2},
            {"id": "B", "deps": ["A"], "estimated_hours": 3},
            {"id": "C", "deps": ["A"], "estimated_hours": 1},
        ]

    def test_cpm_float_and_near_critical(self):
        cpm = R19IntentCompiler().compute_cpm(self._stages())
        self.assertTrue(cpm["ok"])
        self.assertEqual(cpm["project_duration_hours"], 5.0)
        self.assertEqual(cpm["critical_path"], ["A", "B"])
        rows = {r["id"]: r for r in cpm["schedule"]}
        self.assertEqual(rows["C"]["total_float"], 2.0)
        self.assertEqual(rows["B"]["free_float"], 0.0)

    def test_deadline_crash_plan(self):
        comp = R19IntentCompiler()
        out = comp.assess_deadline(self._stages(), 4)
        self.assertFalse(out["feasible"])
        self.assertEqual(out["verdict"], "FEASIBLE_WITH_CRASH")
        self.assertEqual(round(sum(p["compress_hours"] for p in out["crash_plan"]), 4), 1.0)

    def test_deadline_feasible(self):
        out = R19IntentCompiler().assess_deadline(self._stages(), 8)
        self.assertTrue(out["feasible"])
        self.assertEqual(out["verdict"], "FEASIBLE")
        self.assertEqual(out["slack_hours"], 3.0)


class TestL03HealGovernance(unittest.TestCase):
    def test_redline_corpus_full_recall(self):
        out = R19ReflexiveHealer().evaluate_redline_corpus()
        self.assertTrue(out["ok"])
        self.assertEqual(out["recall"], 1.0)
        self.assertEqual(out["false_positive_rate"], 0.0)
        self.assertEqual(out["code_coverage"], 5)

    def test_repair_plan_blocker_first(self):
        healer = R19ReflexiveHealer()
        audit = {"violations": [{"code": "RL-05", "redline": "禁止篡改历史",
                                 "handoff": "红线登记表", "hits": ["篡改"]}]}
        plan = healer.build_repair_plan(audit, {"notes": ["归一 stage: 'prod' → 'production'"]})
        self.assertTrue(plan["has_blocker"])
        self.assertFalse(plan["ok"])
        self.assertEqual(plan["steps"][0]["severity"], "blocker")

    def test_heal_idempotent(self):
        dirty = {"verdict": "pass", "stage": "prod",
                 "records": [{"ground_truth": "pass", "prediction": "pass"}]}
        out = R19ReflexiveHealer().verify_idempotent(dirty)
        self.assertTrue(out["ok"])
        self.assertEqual(out["first_hash"], out["second_hash"])


class TestL04LedgerGovernance(unittest.TestCase):
    def test_diff_detects_breaking_threshold(self):
        ledger = R19SpecLedger()
        spec = ledger.load_spec()
        changed = json.loads(json.dumps(spec))
        gid = sorted(changed["gates"])[0]
        changed["gates"][gid]["threshold"] = "99.99%"
        changed["spec_hash"] = "changed"
        out = ledger.diff_snapshots(spec, changed)
        self.assertEqual(out["impact"], "BREAKING")
        self.assertEqual(out["change_count"], 1)
        self.assertTrue(out["gates_changed"][0]["breaking"])

    def test_lint_blocks_duplicate_and_empty(self):
        ledger = R19SpecLedger()
        spec = json.loads(json.dumps(ledger.load_spec()))
        gid = sorted(spec["gates"])[0]
        spec["gates"][gid]["threshold"] = ""
        spec["gate_ids"] = list(spec["gate_ids"]) + [gid]
        out = ledger.lint_spec(spec, raw_text=f"{gid} ... {gid}")
        codes = {f["code"] for f in out["findings"]}
        self.assertFalse(out["ok"])
        self.assertIn("EMPTY_THRESHOLD", codes)
        self.assertIn("DUPLICATE_GATE", codes)
        self.assertIn("DUPLICATE_GATE_MD", codes)


class TestL05SlopDeep(unittest.TestCase):
    def test_regex_catches_variants(self):
        guard = MLSlopGuard()
        out = guard.audit_extended(
            "模型可能存在一定的风险，效果显著提升，significantly improved，整体基本符合预期。")
        labels = {m["label"] for m in out["regex_matches"]}
        self.assertGreaterEqual(out["regex_count"], 4)
        self.assertIn("模糊概率断言", labels)
        self.assertIn("EN vague claim", labels)
        self.assertEqual(out["status_extended"], "SLOP_DETECTED")
        self.assertFalse(out["evidence_density"]["ok"])

    def test_clean_dense_passes(self):
        out = MLSlopGuard().audit_extended(
            "准确率 0.91，P95 180ms，样本 500 条，回归 ID REG-19。")
        self.assertEqual(out["status_extended"], "PASS")
        self.assertTrue(out["evidence_density"]["ok"])
        self.assertEqual(out["regex_count"], 0)


class TestL06DecisionRobustness(unittest.TestCase):
    def test_topsis_pareto_minimax(self):
        matrix = R19ScenarioMatrix().compile_matrix("客服助手", 500)
        topsis = matrix["topsis"]
        self.assertEqual(topsis["winner"], "SCN_B_STEADY")
        self.assertEqual(topsis["ranking"][0], "SCN_B_STEADY")
        self.assertGreater(topsis["rows"][0]["closeness"], topsis["rows"][1]["closeness"])
        self.assertLessEqual(max(r["closeness"] for r in topsis["rows"]), 1.0)

        pareto = matrix["pareto"]
        self.assertGreaterEqual(pareto["frontier_size"], 1)
        self.assertEqual(sorted(pareto["frontier"] + pareto["dominated"]),
                         sorted(["SCN_A_QUICK", "SCN_B_STEADY", "SCN_C_STRICT"]))

        regret = matrix["minimax_regret"]
        self.assertEqual(regret["winner"], "SCN_B_STEADY")
        self.assertGreaterEqual(regret["worst_case_regret"], 0.0)


class TestL07Interop(unittest.TestCase):
    def test_bundle_junit_merkle_schema(self):
        out_dir = _tmpdir("c2_bundle_")
        self.addCleanup(shutil.rmtree, out_dir, True)
        built = R19AssetBundle(out_dir=out_dir).build("C2TEST")
        self.assertTrue(os.path.exists(built["paths"]["junit_file"]))
        with open(built["paths"]["junit_file"], encoding="utf-8") as f:
            head = f.readline()
        self.assertIn("<?xml", head)
        self.assertEqual(len(built["merkle_root"]), 64)
        self.assertTrue(built["schema_check"]["ok"])
        self.assertTrue(built["bundle"]["merkle"]["root"])
        rules = built["sarif"]["runs"][0]["tool"]["driver"]["rules"]
        self.assertTrue(all("help" in r and r.get("helpUri") for r in rules))
        states = [x.get("baselineState") for x in built["sarif"]["runs"][0]["results"]]
        self.assertTrue(all(s in ("new", "unchanged") for s in states))


class TestL08PatchSafety(unittest.TestCase):
    def test_inverse_conflict_compact(self):
        eng = R19DiffPatchEngine()
        old = {"n": 4, "confusion": {"tp": 1, "fp": 1, "tn": 1, "fn": 1},
               "accuracy": 0.5, "precision": 0.5, "recall": 0.5, "f1": 0.5}
        new = {"n": 4, "confusion": {"tp": 2, "fp": 0, "tn": 1, "fn": 1},
               "accuracy": 0.75}
        out = eng.diff_evaluation(old, new)
        self.assertTrue(out["rollback_ok"])
        self.assertEqual(out["inverse_count"], out["patch_count"])

        drift = eng.detect_conflicts(old, [
            {"op": "replace", "path": "/missing", "value": 1},
            {"op": "test", "path": "/n", "value": 999}])
        self.assertEqual(drift["conflict_count"], 2)
        self.assertFalse(drift["ok"])

        compact = eng.compact_patch([
            {"op": "replace", "path": "/accuracy", "value": 0.6},
            {"op": "replace", "path": "/accuracy", "value": 0.75},
            {"op": "test", "path": "/n", "value": 4},
            {"op": "remove", "path": "/precision"}])
        self.assertEqual(compact["after"], 2)
        self.assertEqual(compact["reduction_ratio"], 0.5)


class TestL09MemoryGovernance(unittest.TestCase):
    def test_diff_multi_turn_ttl_lru(self):
        workdir = _tmpdir("c2_mem_")
        self.addCleanup(shutil.rmtree, workdir, True)
        path = os.path.join(workdir, "session.json")
        mem = R19SessionMemory(state_path=path)
        mem.update_slot("threshold", 0.80)
        before = mem.record_snapshot("before", {"threshold": 0.80})
        mem.update_slot("threshold", 0.85)
        mem.update_slot("current_dataset", "golden_set_v2")
        after = mem.record_snapshot("after", {"threshold": 0.85,
                                              "current_dataset": "golden_set_v2"})
        diff = mem.diff_snapshots(before, after)
        self.assertEqual(diff["change_count"], 2)
        self.assertIn("current_dataset", diff["added"])

        multi = mem.resolve_multi_turn(["按第一套方案调整", "把阈值调高0.05", "把阈值调低0.02"])
        self.assertEqual(multi["conflict_count"], 1)
        self.assertEqual(multi["slots"]["threshold"], 0.88)
        self.assertEqual(multi["policy"], "last_write_wins")
        self.assertEqual(multi["provenance"]["threshold"]["turn"], 2)

        for i in range(7):
            mem.record_snapshot(f"bulk_{i}", {"threshold": 0.8 + i / 100})
        compact = mem.compact_snapshots(keep=3)
        self.assertEqual(compact["pruned_count"], 6)
        self.assertEqual(compact["remaining"], 3)

        mem.set_ttl("temp_slot", -1)
        purge = mem.purge_expired()
        self.assertEqual(purge["expired_count"], 1)


class TestL10ResilienceObservability(unittest.TestCase):
    def test_sliding_window_breaker(self):
        now = [0.0]
        br = SlidingWindowBreaker(window_sec=60, failure_rate_threshold=0.5,
                                  min_samples=6, recovery_timeout_sec=1.0,
                                  clock=lambda: now[0])
        for _ in range(3):
            br.record_success()
        for _ in range(3):
            br.record_failure()
        self.assertEqual(br.state, "OPEN")
        self.assertFalse(br.can_execute())
        now[0] = 1.0
        self.assertTrue(br.can_execute())
        self.assertEqual(br.state, "HALF_OPEN")
        br.record_failure()
        self.assertEqual(br.state, "OPEN")
        self.assertTrue(br.transitions)

    def test_aggregate_percentiles_and_traces(self):
        wd = R19TelemetryWatchdog()
        rows = [{"name": "gate.check", "duration_ms": float(v), "status": "OK"}
                for v in range(10, 101, 10)]
        agg = wd.aggregate_telemetry(rows)
        self.assertEqual(agg["total_spans"], 10)
        self.assertEqual(agg["by_name"]["gate.check"]["p50"], 55.0)
        self.assertEqual(agg["by_name"]["gate.check"]["p95"], 95.5)
        self.assertEqual(agg["overall"]["error_rate"], 0.0)

        traces = wd.reconstruct_traces([
            {"trace_id": "t1", "name": "a", "duration_ms": 10, "status": "OK"},
            {"trace_id": "t1", "name": "b", "duration_ms": 5, "status": "ERROR"},
            {"trace_id": "t2", "name": "c", "duration_ms": 1, "status": "OK"}])
        self.assertEqual(traces["trace_count"], 2)
        t1 = next(t for t in traces["traces"] if t["trace_id"] == "t1")
        self.assertEqual(t1["span_sequence"], ["a", "b"])
        self.assertEqual(t1["total_duration_ms"], 15.0)
        self.assertEqual(t1["status"], "DEGRADED")


class TestCycle2Metadata(unittest.TestCase):
    def test_ten_layers_and_capability_floor(self):
        stages = runner.EVOLUTION_STAGES_CYCLE2
        self.assertEqual(len(stages), 10)
        self.assertEqual([s["layer"] for s in stages],
                         [f"L{i:02d}" for i in range(1, 11)])
        total = sum(len(s["capabilities"]) for s in stages)
        self.assertGreaterEqual(total, 20)
        for s in stages:
            self.assertGreaterEqual(len(s["capabilities"]), 2)
            self.assertIn("cycle2", s["verify_cmd"][-1])
            self.assertTrue(all(a.startswith("workspace/") for a in s["artifacts_expected"]))
        for stage in (1, 2, 3):
            caps = sum(len(s["capabilities"]) for s in stages if s["stage"] == stage)
            self.assertGreaterEqual(caps, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)

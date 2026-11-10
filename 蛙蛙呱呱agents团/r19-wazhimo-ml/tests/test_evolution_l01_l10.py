# -*- coding: utf-8 -*-
"""tests/test_evolution_l01_l10.py — R19 蛙智模 十维演进双轨集成测试套件。

严格遵循《Universal Agent 10-Stage Evolution SOP v13.0》三批次 10 阶梯：
- Round 1 (Stage 1 / L01~L03 执行基石)：评估精算沙箱、5 阶段 Kahn DAG、红线审判与自愈；
- Round 2 (Stage 2 / L04~L06 专业深度)：ML_SPEC 账本与 8 维门禁、Anti-Slop、三维决策矩阵；
- Round 3 (Stage 3 / L07~L10 工业交付)：SARIF/Vega 资产包、RFC 6902 差量、会话记忆、熔断遥测。

运行：
    python -m unittest tests.test_evolution_l01_l10 -v
"""
from __future__ import annotations

import json
import os
import random
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = os.path.dirname(HERE)
REPO = os.path.dirname(AGENTS)
for _p in (HERE, AGENTS, REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Windows 中文控制台 GBK 防御
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

from engines import (  # noqa: E402
    R19RuntimeEngine, R19IntentCompiler, R19ReflexiveHealer, RedlineViolation,
    R19SpecLedger, MLSlopGuard, R19ScenarioMatrix, R19AssetBundle,
    R19DiffPatchEngine, PatchError, R19SessionMemory, R19TelemetryWatchdog,
    WatchdogBreaker,
)

TMP_ROOT = os.path.join(HERE, "workspace", "tmp")
os.makedirs(TMP_ROOT, exist_ok=True)


def _tmpdir(prefix: str) -> str:
    """SOP §5.7：临时目录必须落在角色 workspace/tmp 内，并显式传入 dir。"""
    return tempfile.mkdtemp(prefix=prefix, dir=TMP_ROOT)


class TestStage1Foundation(unittest.TestCase):
    """第 1 轮（L01~L03 执行基石）。"""

    # ------------------------------------------------------------------ #
    def test_l01_runtime_metric_sandbox(self):
        eng = R19RuntimeEngine()
        probe = eng.probe_health()
        self.assertEqual(probe["status"], "HEALTHY")
        self.assertEqual(probe["engine"], "R19RuntimeEngine")
        self.assertEqual(probe["metric_sandbox"], "OK")
        self.assertEqual(probe["latency_sandbox"], "OK")
        self.assertEqual(probe["artifact_sandbox"], "OK")

        records = [
            {"expected": "pass", "predicted": "pass"},
            {"expected": "pass", "predicted": "fail"},
            {"expected": "fail", "predicted": "fail"},
            {"expected": "fail", "predicted": "pass"},
        ]
        m = eng.compute_classification_metrics(records)
        self.assertEqual(m["n"], 4)
        self.assertEqual(m["confusion"], {"tp": 1, "fp": 1, "tn": 1, "fn": 1})
        self.assertEqual(m["accuracy"], 0.5)
        self.assertEqual(m["precision"], 0.5)
        self.assertEqual(m["recall"], 0.5)
        self.assertEqual(m["f1"], 0.5)
        self.assertTrue(m["is_conserved"])
        self.assertTrue(eng.verify_metric_conservation(m)["ok"])

        # 全对：accuracy=1.0；全部预测负例时 precision 零除安全 -> 0.0
        perfect = eng.compute_classification_metrics(
            [{"expected": "pass", "predicted": "pass"}] * 3)
        self.assertEqual(perfect["accuracy"], 1.0)
        self.assertEqual(perfect["precision"], 1.0)
        neg = eng.compute_classification_metrics(
            [{"expected": "fail", "predicted": "fail"}] * 2)
        self.assertEqual(neg["precision"], 0.0)
        self.assertEqual(neg["recall"], 0.0)

        lat = eng.compute_latency_percentiles([10, 20, 30, 40, 100])
        self.assertEqual(lat["p50"], 30.0)
        self.assertEqual(lat["p95"], 88.0)
        self.assertEqual(lat["max"], 100.0)

        art = eng.probe_artifact(os.path.join(HERE, "examples", "evaluation_dataset.json"))
        self.assertTrue(art["exists"] and art["bytes"] > 0)
        self.assertTrue(art["looks_like_json"])
        self.assertEqual(len(art["sha256"]), 64)
        missing = eng.probe_artifact(os.path.join(TMP_ROOT, "nope.json"))
        self.assertFalse(missing["exists"])

    # ------------------------------------------------------------------ #
    def test_l02_intent_compiler_dag(self):
        comp = R19IntentCompiler()
        text = "紧急评估客服助手模型，准确率>=0.9，P95<200ms，明天发布，500条样本"
        ent = comp.extract_entities(text)
        self.assertTrue(ent["is_urgent"])
        self.assertEqual(ent["metric_targets"].get("accuracy"), 0.9)
        self.assertEqual(ent["latency_p95_ms"], 200.0)
        self.assertEqual(ent["sample_size"], 500)

        stages = comp.compile_intent(text)
        self.assertEqual(len(stages), 5)
        self.assertEqual([s["id"] for s in stages],
                         ["audit", "track", "evaluate", "regression", "decide"])
        summary = comp.evaluate_budget_and_schedule(stages)
        self.assertTrue(summary["is_dag_valid"])
        self.assertEqual(len(summary["topological_sequence"]), 5)
        self.assertLessEqual(summary["critical_path_hours"], summary["total_estimated_hours"])
        self.assertTrue(summary["critical_path"])

        # 环路检测：a<->b 必须判非法
        cyclic = [{"id": "a", "deps": ["b"], "estimated_hours": 1},
                  {"id": "b", "deps": ["a"], "estimated_hours": 1}]
        bad = comp.evaluate_budget_and_schedule(cyclic)
        self.assertFalse(bad["is_dag_valid"])
        self.assertTrue(bad["cycle_nodes"])

        out = comp.compile_request(text)
        self.assertTrue(out["ok"])
        md = comp.render_markdown(out)
        self.assertIn("R19 模型工程交付 DAG", md)

    # ------------------------------------------------------------------ #
    def test_l03_reflexive_healer_redlines(self):
        healer = R19ReflexiveHealer()

        # 红线 1：凭据入工件
        a = healer.audit_redlines("训练时用了 api_key=sk-123 访问")
        self.assertTrue(a["blocked"])
        self.assertIn("RL-01", a["codes"])
        with self.assertRaises(RedlineViolation):
            healer.enforce_redlines("password=hunter2")

        # 红线 2：主观放行
        a = healer.audit_redlines("这个新版效果看起来不错，直接上线吧")
        self.assertTrue(a["blocked"])
        self.assertIn("RL-02", a["codes"])
        with self.assertRaises(RedlineViolation) as ctx:
            healer.enforce_redlines("这个新版效果看起来不错，直接上线吧")
        self.assertIn("[REDLINE BLOCKED]", str(ctx.exception))

        # 红线 3：统计/归因越界 -> 移交 R06
        a = healer.audit_redlines("给出模型效果与用户增长的业务归因")
        self.assertIn("RL-03", a["codes"])
        self.assertIn("R06", a["violations"][0]["handoff"])

        # 红线 4：结构性 —— PASS 无证据
        a = healer.audit_redlines("", {"verdict": "PASS", "evidence": []})
        self.assertIn("RL-04", a["codes"])

        # 干净动作不阻断
        a = healer.audit_redlines("按评估证据复核发布候选")
        self.assertFalse(a["blocked"])

        # 枚举/字段别名自愈
        healed = healer.heal_artifact({
            "verdict": "pass", "stage": "prod", "risk_tier": "Medium",
            "evidence": [], "records": [{"ground_truth": "pass", "prediction": "pass"}],
        })
        h = healed["healed"]
        self.assertEqual(h["verdict"], "NEEDS_REVIEW")  # PASS 无证据 -> 保守降级
        self.assertEqual(h["stage"], "production")
        self.assertEqual(h["risk_tier"], "medium")
        self.assertEqual(h["records"][0]["expected"], "pass")
        self.assertEqual(h["records"][0]["predicted"], "pass")
        self.assertGreaterEqual(healed["note_count"], 3)

        # Reflexion 有界闭环：先坏后好，2 轮收敛
        state = {"n": 0}

        def reviewer(data):
            state["n"] += 1
            return {"ok": state["n"] >= 2, "issues": [] if state["n"] >= 2 else ["缺证据"]}

        loop = healer.reflexion_loop({"x": 1}, reviewer=reviewer,
                                     healer=lambda d: ({**d, "healed": True}, ["补齐"]))
        self.assertTrue(loop["converged"])
        self.assertEqual(loop["iterations"], 2)


class TestStage2Professional(unittest.TestCase):
    """第 2 轮（L04~L06 专业深度）。"""

    # ------------------------------------------------------------------ #
    def test_l04_spec_ledger_and_gates(self):
        ledger = R19SpecLedger()
        spec = ledger.load_spec()
        self.assertEqual(spec["gates_count"], 8)
        self.assertEqual(len(spec["north_star_kpis"]), 5)
        self.assertIn("ERA", spec["north_star_kpis"])
        self.assertIn("CLR", spec["north_star_kpis"])
        self.assertTrue(spec["parse_ok"])
        self.assertEqual(len(spec["spec_hash"]), 64)

        good = {
            "records": [{"expected": "pass", "predicted": "pass"},
                        {"expected": "fail", "predicted": "fail"}],
            "verdict": "PASS",
            "evidence": ["evaluation_report.json"],
            "regression_id": "reg_001",
            "fail_before": True, "pass_after": True, "existing_green": True,
            "assets": [{"path": "artifacts/model.bin", "run_id": "run_001",
                        "sha256": "a" * 64}],
            "versions": [{"version": "1.0", "stage": "production"},
                         {"version": "1.1", "stage": "staging"}],
            "risk_tier": "medium", "license": "open_source",
            "handoff": "发布落地移交 R09 蛙联调",
        }
        res = ledger.verify_gate_compliance("release", good)
        self.assertTrue(res["compliant"], res["violations"])
        self.assertEqual(res["violations_count"], 0)
        self.assertEqual(res["gates_total"], 8)

        bad = {
            "records": [{"expected": "pass"}],
            "verdict": "PASS",
            "evidence": [],
            "fail_before": False,
            "assets": [{"path": "", "run_id": ""}],
            "summary": "训练时用了 api_key=sk-123 访问",
            "versions": [{"stage": "production"}, {"stage": "production"}],
            "risk_tier": "severe",
        }
        bad_res = ledger.verify_gate_compliance("release", bad)
        self.assertFalse(bad_res["compliant"])
        self.assertGreaterEqual(bad_res["violations_count"], 3)
        gates_hit = {v["gate"] for v in bad_res["violations"]}
        self.assertIn("GATE-05", gates_hit)

        export_dir = _tmpdir("r19_spec_")
        exported = ledger.export_gates(export_dir)
        self.assertTrue(os.path.exists(exported["json"]))
        self.assertTrue(os.path.exists(exported["markdown"]))

    # ------------------------------------------------------------------ #
    def test_l05_slop_guard(self):
        guard = MLSlopGuard()
        audit = guard.audit("模型评估整体良好，相关细节待定，持续关注。")
        self.assertTrue(audit["has_slop"])
        self.assertGreaterEqual(audit["slop_count"], 2)
        self.assertIn("R19 蛙智模", audit["cleaned_text"])
        self.assertGreater(audit["actionability_score"], 0)
        self.assertEqual(audit["status"], "SLOP_DETECTED")

        clean = guard.audit("评估准确率 0.91，F1 0.88，P95 200ms，500条样本，明确 DRI 为 R19 蛙智模。")
        self.assertFalse(clean["has_slop"])
        self.assertEqual(clean["status"], "PASS")
        self.assertTrue(clean["has_quantitative_evidence"])
        self.assertGreaterEqual(clean["actionability_score"], 60)

    # ------------------------------------------------------------------ #
    def test_l06_scenario_matrix(self):
        mat = R19ScenarioMatrix().compile_matrix("客服助手", 500)
        self.assertEqual(len(mat["scenarios"]), 3)
        ids = [s["id"] for s in mat["scenarios"]]
        self.assertEqual(ids, ["SCN_A_QUICK", "SCN_B_STEADY", "SCN_C_STRICT"])
        self.assertEqual(mat["recommended"], "SCN_B_STEADY")
        steady = next(s for s in mat["scenarios"] if s["id"] == "SCN_B_STEADY")
        self.assertTrue(steady["is_recommended"])
        self.assertGreater(steady["roi_score"], 8.0)
        self.assertTrue(mat["sensitivity"]["ranking_stable"])

        md = R19ScenarioMatrix().render_markdown(mat)
        self.assertIn("SCN_B_STEADY", md)
        self.assertIn("推荐", md)


class TestStage3Industrial(unittest.TestCase):
    """第 3 轮（L07~L10 工业交付）。"""

    # ------------------------------------------------------------------ #
    def test_l07_asset_bundle(self):
        out_dir = _tmpdir("r19_bundle_")
        bundle = R19AssetBundle(out_dir=out_dir)
        paths = bundle.compile_and_save("test_run_001")
        for key in ("bundle_file", "sarif_file", "vega_file"):
            self.assertTrue(os.path.exists(paths[key]), key)

        with open(paths["sarif_file"], encoding="utf-8") as f:
            sarif = json.load(f)
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertEqual(sarif["runs"][0]["tool"]["driver"]["name"], "R19-ML-Auditor")
        self.assertTrue(sarif["runs"][0]["invocations"][0]["executionSuccessful"])
        self.assertTrue(sarif["runs"][0]["results"])

        with open(paths["vega_file"], encoding="utf-8") as f:
            vega = json.load(f)
        self.assertTrue(vega["$schema"].startswith("https://vega.github.io/schema/vega-lite/"))

        with open(paths["bundle_file"], encoding="utf-8") as f:
            b = json.load(f)
        self.assertEqual(b["schema"], "r19.ml_bundle.v1")
        self.assertTrue(b["artifacts"])
        for a in b["artifacts"]:
            self.assertEqual(len(a["sha256"]), 64)
        self.assertEqual(len(b["lineage"]["nodes"]), 5)

    # ------------------------------------------------------------------ #
    def test_l08_diff_patch_engine(self):
        eng = R19DiffPatchEngine()
        old = {"accuracy": 0.80}
        new = {"accuracy": 0.86}
        patches = eng.create_patch(old, new)
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0]["op"], "replace")
        self.assertEqual(patches[0]["path"], "/accuracy")
        self.assertEqual(patches[0]["value"], 0.86)
        applied = eng.apply_patch(old, patches)
        self.assertEqual(applied["accuracy"], 0.86)

        old_eval = {"n": 4, "confusion": {"tp": 1, "fp": 1, "tn": 1, "fn": 1},
                    "accuracy": 0.5, "precision": 0.5, "recall": 0.5, "f1": 0.5}
        new_eval = {"n": 4, "confusion": {"tp": 2, "fp": 0, "tn": 1, "fn": 1},
                    "accuracy": 0.75}
        diff = eng.diff_evaluation(old_eval, new_eval)
        self.assertTrue(diff["ok"])
        self.assertEqual(diff["applied"]["accuracy"], 0.75)
        self.assertTrue(diff["recomputed"])
        self.assertIn("GATE-01", diff["gates_affected"])
        self.assertTrue(all(c["ok"] for c in diff["conservation"]))
        self.assertEqual(diff["applied"]["precision"], 1.0)

        with self.assertRaises(PatchError):
            eng.apply_patch({}, [{"op": "test", "path": "/x", "value": 1}])

    # ------------------------------------------------------------------ #
    def test_l09_session_memory(self):
        ws = _tmpdir("r19_session_")
        mem = R19SessionMemory(workspace_dir=ws)
        snap = mem.record_snapshot("initial_model",
                                   {"current_model": "客服助手", "threshold": 0.80})
        self.assertTrue(snap.startswith("snap_"))

        mem.update_slot("selected_scenario", "SCN_A_QUICK")
        self.assertEqual(mem.state["entities"]["selected_scenario"], "SCN_A_QUICK")
        self.assertEqual(mem.state["selected_scenario"], "SCN_A_QUICK")  # 双向同步

        resolved = mem.disambiguate_query("按刚才第二套方案调整")
        self.assertIn("SCN_B_STEADY", resolved["disambiguated"])
        self.assertEqual(resolved["referenced_context"]["selected_scenario"], "SCN_B_STEADY")

        mem.update_slot("threshold", 0.85)
        r2 = mem.disambiguate_query("把上次那个模型的阈值调高0.05")
        self.assertEqual(r2["referenced_context"]["threshold"], 0.90)
        self.assertEqual(r2["referenced_context"]["model_name"], "客服助手")

        restored = mem.rollback(snap)
        self.assertEqual(restored["current_model"], "客服助手")
        self.assertEqual(mem.get_slot("threshold"), 0.80)
        self.assertTrue(os.path.exists(mem.state_path))

    # ------------------------------------------------------------------ #
    def test_l10_telemetry_watchdog(self):
        ws = _tmpdir("r19_telemetry_")
        wd = R19TelemetryWatchdog(workspace_dir=ws)
        probe = wd.probe_health()
        self.assertEqual(probe["status"], "healthy")
        self.assertEqual(probe["layer"], "L10")
        self.assertTrue(os.path.exists(probe["log_path"]))

        # 用可注入时钟替身做确定性三态验证，避免真实 sleep 的时序抖动
        clock = {"t": 100.0}
        br = WatchdogBreaker(failure_threshold=2, recovery_timeout_sec=0.05,
                             clock=lambda: clock["t"])
        self.assertEqual(br.state, "CLOSED")
        self.assertTrue(br.can_execute())
        br.record_failure()
        self.assertEqual(br.state, "CLOSED")
        br.record_failure()
        self.assertEqual(br.state, "OPEN")
        self.assertFalse(br.can_execute())
        clock["t"] += 0.051                      # 恢复窗口到期
        self.assertTrue(br.can_execute())        # -> HALF_OPEN
        self.assertEqual(br.state, "HALF_OPEN")
        br.record_success()
        self.assertEqual(br.state, "CLOSED")

        # 重试：前两次失败、第三次成功（熔断阈值放宽，验证退避重试）
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("网络抖动")
            return {"status": "ok"}

        res = wd.execute_with_resilience(
            "flaky.evaluate", flaky, max_attempts=3, base_delay=0.001,
            rng=random.Random(7),
            breaker=WatchdogBreaker(failure_threshold=5, recovery_timeout_sec=0.05))
        self.assertTrue(res["ok"])
        self.assertEqual(res["attempts"], 3)
        self.assertEqual(res["result"]["status"], "ok")

        rows = wd.read_telemetry(10)
        self.assertTrue(rows)
        self.assertIn("trace_id", rows[0])
        self.assertIn("span_id", rows[0])
        self.assertTrue(rows[0]["sha256"])


class TestEvolutionWiring(unittest.TestCase):
    """十维演进接线：agent.py evolve 探针必须真实可跑并落盘。"""

    def test_evolve_cli_probes(self):
        import subprocess
        out = os.path.join(_tmpdir("r19_cli_"), "L01_probe.json")
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, "agent.py", "evolve", "probe", "--out", out],
            cwd=HERE, capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=env, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr[-1000:])
        self.assertTrue(os.path.exists(out))
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["status"], "HEALTHY")


if __name__ == "__main__":
    unittest.main(verbosity=2)

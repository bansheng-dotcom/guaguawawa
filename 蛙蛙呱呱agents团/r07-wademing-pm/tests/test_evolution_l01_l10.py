# -*- coding: utf-8 -*-
"""tests/test_evolution_l01_l10.py - R07 蛙得明·产品经理 十维演进元模型双轨集成测试套件。"""
from __future__ import annotations

import hashlib
import json
import os
from core.workspace import role_workspace  # noqa: E402

import random
import sys
import time
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(AGENTS)
for p in (HERE, AGENTS, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from engines import (
    PMRuntimeEngine,
    IntentDAGCompiler,
    PMReflexiveHealer,
    PMSpecLedger,
    PMSlopGuard,
    ScenarioMatrix,
    AssetBundleExporter,
    PRDASTBuilder,
    SARIFReporter,
    VegaChartBuilder,
    PRDPatchEngine,
    PatchError,
    PatchTestFailed,
    SessionMemory,
    CircuitBreaker,
    CircuitOpenError,
    TelemetryTracer,
    Watchdog,
    retry_with_backoff,
)
from engines.telemetry_watchdog import self_test as watchdog_self_test  # noqa: E402
from engines.telemetry_watchdog import CLOSED, HALF_OPEN, OPEN  # noqa: E402
from skills import s03_prd  # noqa: E402

TMP_ROOT = os.path.join(role_workspace(HERE), "tmp")


class TestEvolutionRound1(unittest.TestCase):
    """第 1 轮演进 (L01~L03) 单元与集成测试。"""

    def test_l01_runtime_probe(self):
        rt = PMRuntimeEngine()
        probe = rt.probe_health()
        self.assertEqual(probe["status"], "healthy")
        self.assertTrue(probe["rice_calculator_healthy"])
        self.assertTrue(probe["opportunity_calculator_healthy"])
        self.assertTrue(probe["ast_audit_healthy"])

    def test_l01_calculation_precision(self):
        rt = PMRuntimeEngine()
        items = [
            {"name": "FeatureA", "reach": 100, "impact": 2.0, "confidence": 0.8, "effort": 2.0},
            {"name": "FeatureB", "reach": 50, "impact": 3.0, "confidence": 0.9, "effort": 1.0},
        ]
        res = rt.score_priorities("rice", items)
        ranked = res["ranked_items"]
        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0]["name"], "FeatureB")
        self.assertEqual(ranked[0]["score"], 135.0)

    def test_l02_intent_dag_decompilation(self):
        compiler = IntentDAGCompiler()
        query = "提升企业客户协作效率，完成JTBD调研与PRD故事拆解，制定RICE优先级与里程碑路线图"
        res = compiler.decompile_intent(query)
        self.assertTrue(res["ok"])
        dag = res["dag"]
        self.assertTrue(dag["is_dag"])
        self.assertEqual(len(dag["topological_order"]), 5)
        self.assertIn("node_01_discovery", dag["topological_order"])
        self.assertIn("node_05_roadmap", dag["topological_order"])
        self.assertGreater(dag["total_estimated_hours"], 0)

    def test_l03_reflexive_healing_and_redlines(self):
        healer = PMReflexiveHealer()
        dirty_data = {
            "title": "测试违规需求",
            "executive_summary": "由我拍板决定必须在下周上线，无需审批立即执行。底层采用Redis分布式锁与Go重写实现",
            "metrics": {
                "north_star": "总注册用户数",
            },
            "acceptance_criteria": [],
        }
        violations = healer.audit_redlines(dirty_data)
        self.assertGreaterEqual(len(violations), 3)
        self.assertTrue(any("拍板决策" in v for v in violations))
        self.assertTrue(any("越界技术实现" in v for v in violations))

        healed = healer.audit_and_heal("prd", dirty_data)
        self.assertTrue(healed["is_healed"])
        self.assertIn("留存", healed["healed_data"]["metrics"]["north_star"])
        self.assertIn("telemetry", healed["healed_data"])


class TestEvolutionRound2(unittest.TestCase):
    """第 2 轮演进 (L04~L06) 单元与集成测试。"""

    def test_l04_pm_spec_ledger_load(self):
        ledger = PMSpecLedger()
        spec = ledger.load_spec()
        self.assertTrue(spec["spec_loaded"])
        self.assertIn("rules", spec)
        rules = spec["rules"]
        self.assertIn("jtbd", rules)
        self.assertIn("rice", rules)
        self.assertIn("prd_gates", rules)
        self.assertIn("okr_framework", rules)
        self.assertIn("telemetry_schema", rules)
        self.assertIn("release_gate_slas", rules)

        # 校验 8 门禁完整性
        gates = rules["prd_gates"]
        self.assertEqual(len(gates), 8)
        gate_ids = [g["id"] for g in gates]
        for expected in ["problem", "user", "value", "scope", "metric", "acceptance", "risk", "read"]:
            self.assertIn(expected, gate_ids)

    def test_l04_prd_validation_against_spec(self):
        ledger = PMSpecLedger()
        good_prd = {
            "title": "新用户新手引导",
            "problem": "新手注册后不懂如何建项目",
            "target_user": "初次试用 SaaS 的团队管理员",
            "value_prop": "提升 7 日激活率至 35%",
            "scope": {"p0": ["分步向导", "示例模板一键克隆"]},
            "metrics": {"north_star": "7日激活率", "guardrail": "引导跳出率"},
            "acceptance_criteria": [
                {"given": "新用户登录", "when": "点击创建项目", "then": "弹出四步向导"},
                {"given": "向导展示中", "when": "点击跳过", "then": "记录埋点并进入空白台"},
                {"given": "网络断开", "when": "提交表单", "then": "展示重试提示与草稿保存"},
                {"given": "输入非法字符", "when": "失焦", "then": "字段下方高亮报错"},
            ],
            "assumptions": [{"risk_type": "value", "hypothesis": "用户愿意花3分钟完成向导"}],
        }
        res = ledger.validate_prd_against_spec(good_prd)
        self.assertTrue(res["all_passed"])
        self.assertEqual(res["passed_count"], 8)
        self.assertEqual(res["sla_verdict"], "normal")

        # 缺失 scope 与 acceptance 时阻断
        broken_prd = {"title": "粗糙方案", "problem": "缺功能"}
        bad_res = ledger.validate_prd_against_spec(broken_prd)
        self.assertFalse(bad_res["all_passed"])
        self.assertIn(bad_res["sla_verdict"], ["blocker", "critical"])

    def test_l05_slop_guard_intercept_and_purify(self):
        guard = PMSlopGuard()
        slop_text = "本项目致力于提升用户体验，后续针对核心链路优化性能。关于移动端适配目前功能待定，根据实际情况再做调整。"
        audit = guard.audit_text(slop_text)
        self.assertFalse(audit["is_clean"])
        self.assertGreaterEqual(audit["issues_found"], 4)
        purified = audit["purified_text"]
        self.assertNotIn("提升用户体验", purified)
        self.assertNotIn("优化性能", purified)
        self.assertNotIn("功能待定", purified)
        self.assertNotIn("根据实际情况", purified)
        # 确保注入了量化行动指标
        self.assertTrue("耗时" in purified or "响应时间" in purified or "1.2s" in purified or "200ms" in purified)

    def test_l05_slop_guard_artifact_purification(self):
        guard = PMSlopGuard()
        artifact = {
            "feature": "数据导出",
            "goal": "提升用户体验",
            "steps": ["准备数据", "功能待定", "根据实际情况触发通知"],
            "meta": {"note": "优化性能"},
        }
        purified, count = guard.purify_prd_artifact(artifact)
        self.assertGreaterEqual(count, 4)
        self.assertNotIn("提升用户体验", purified["goal"])
        self.assertNotIn("功能待定", purified["steps"][1])
        self.assertNotIn("优化性能", purified["meta"]["note"])

    def test_l06_scenario_matrix_generation(self):
        matrix_engine = ScenarioMatrix()
        res = matrix_engine.generate_matrix("SaaS 协作多维看板", "提升团队项目透明度")
        self.assertTrue(res["ok"])
        scenarios = res["scenarios"]
        self.assertEqual(len(scenarios), 3)

        ids = [s["id"] for s in scenarios]
        self.assertIn("lean_mvp", ids)
        self.assertIn("commercial_standard", ids)
        self.assertIn("enterprise_flagship", ids)

        # 检查各层级属性
        mvp = next(s for s in scenarios if s["id"] == "lean_mvp")
        self.assertIn("快速试错", mvp["tier"])
        self.assertLessEqual(mvp["estimated_person_days"], 5.0)

        flagship = next(s for s in scenarios if s["id"] == "enterprise_flagship")
        self.assertIn("企业旗舰", flagship["tier"])
        self.assertGreaterEqual(flagship["estimated_person_days"], 25.0)

        # 检查权衡矩阵
        tradeoff = res["tradeoff_matrix"]
        self.assertIn("dimensions", tradeoff)
        self.assertIn("lean_mvp", tradeoff)
        self.assertIn("commercial_standard", tradeoff)
        self.assertIn("enterprise_flagship", tradeoff)


class TestEvolutionRound3(unittest.TestCase):
    """第 3 轮演进 (L07~L10)：伴生消费 / 局部差量 / 会话记忆 / 工业容灾。"""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "examples", "prd.json"), encoding="utf-8") as f:
            cls.prd = json.load(f)
        with open(os.path.join(HERE, "examples", "prd_dirty.json"), encoding="utf-8") as f:
            cls.dirty = json.load(f)
        os.makedirs(TMP_ROOT, exist_ok=True)

    def test_l07_ast_builder_gate_nodes(self):
        gate = s03_prd._validate_prd(self.prd)
        ast = PRDASTBuilder().build(self.prd, gate_ok=gate["gate_ok"],
                                    checks=gate["checks"],
                                    passed_gates=gate["passed_gates"])
        self.assertEqual(ast["schema"], "pm.prd.ast/v1")
        self.assertEqual(ast["summary"]["passed_gates"], 8)
        self.assertTrue(ast["summary"]["ok"])
        self.assertEqual(len(ast["root"]["gates"]), 8)
        ids = [g["id"] for g in ast["root"]["gates"]]
        self.assertEqual(ids, ["problem", "user", "value", "scope",
                               "metric", "acceptance", "risk", "read"])
        self.assertTrue(all(g["status"] == "PASS" for g in ast["root"]["gates"]))
        self.assertEqual(len(ast["ast_sha256"]), 64)

    def test_l07_sarif_clean_and_failed(self):
        gate = s03_prd._validate_prd(self.prd)
        clean = SARIFReporter().build(gate, artifact_uri="examples/prd.json")
        self.assertEqual(clean["version"], "2.1.0")
        self.assertEqual(clean["runs"][0]["results"], [])
        self.assertTrue(clean["runs"][0]["invocations"][0]["executionSuccessful"])
        rules = [r["id"] for r in clean["runs"][0]["tool"]["driver"]["rules"]]
        self.assertEqual(len(rules), 9)  # PM000 汇总 + PM001-PM008 八门禁
        self.assertIn("PM000", rules)

        dirty_gate = s03_prd._validate_prd(self.dirty)
        dirty = SARIFReporter().build(dirty_gate, artifact_uri="examples/prd_dirty.json")
        results = dirty["runs"][0]["results"]
        self.assertGreater(len(results), 0)
        self.assertTrue(all(r["level"] == "error" for r in results))
        declared = [r["id"] for r in dirty["runs"][0]["tool"]["driver"]["rules"]]
        for r in results:
            # 规则必须已声明，ruleIndex 必须与声明顺序一致（SARIF 2.1.0 硬约束）
            self.assertIn(r["ruleId"], declared)
            self.assertEqual(declared[r["ruleIndex"]], r["ruleId"])
            loc = r["locations"][0]
            self.assertEqual(loc["physicalLocation"]["artifactLocation"]["uri"],
                             "examples/prd_dirty.json")
            self.assertEqual(loc["logicalLocations"][0]["kind"], "gate")
            self.assertNotIn("region", loc["physicalLocation"],
                             "本引擎不解析源文件，不得伪造源码行号")
        self.assertEqual(dirty["runs"][0]["invocations"][0]["exitCode"], 1)

    def test_l07_vega_chart_spec(self):
        gate = s03_prd._validate_prd(self.prd)
        vega = VegaChartBuilder().build(gate)
        self.assertIn("vega-lite", vega["$schema"])
        self.assertEqual(len(vega["data"]["values"]), 8)
        self.assertEqual(vega["mark"]["type"], "bar")
        dirty_vega = VegaChartBuilder().build(s03_prd._validate_prd(self.dirty))
        self.assertTrue(all(v["pass"] == 0 for v in dirty_vega["data"]["values"]))

    def test_l07_bundle_export_physical_artifacts(self):
        out_dir = os.path.join(TMP_ROOT, "l07_bundle")
        gate = s03_prd._validate_prd(self.prd)
        out = AssetBundleExporter(out_dir=out_dir).export(
            self.prd, gate, out_dir=out_dir, artifact_uri="examples/prd.json")
        self.assertTrue(out["ok"])
        self.assertTrue(out["gate_ok"])
        self.assertEqual(out["layer"], "L07")
        self.assertEqual(len(out["files"]), 5)  # ast/sarif/vega/bundle/manifest
        for path in out["files"]:
            self.assertTrue(os.path.isfile(path), path)
            self.assertGreater(os.path.getsize(path), 100, path)

        with open(os.path.join(out_dir, "prd_bundle.json"), encoding="utf-8") as f:
            bundle = json.load(f)
        self.assertEqual(bundle["schema"], "pm.prd.bundle/v1")
        self.assertTrue(bundle["generated_at"])
        # manifest 只登记子工件（不含自身），逐件 SHA256 必须与磁盘内容一致
        self.assertEqual(len(bundle["artifacts"]), 3)
        for art in bundle["artifacts"]:
            with open(art["path"], "rb") as fh:
                raw = fh.read()
            self.assertEqual(len(art["sha256"]), 64)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), art["sha256"])
            self.assertEqual(len(raw), art["bytes"])
        self.assertEqual(bundle["summary"]["sarif_results"], 0)
        self.assertTrue(bundle["summary"]["ok"])

        with open(os.path.join(out_dir, "artifact_manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        with open(manifest["bundle"]["path"], "rb") as fh:
            bundle_raw = fh.read()
        self.assertEqual(manifest["bundle"]["sha256"],
                         hashlib.sha256(bundle_raw).hexdigest())

    def test_l07_refuses_dirty_gate_silently(self):
        out_dir = os.path.join(TMP_ROOT, "l07_bundle_dirty")
        gate = s03_prd._validate_prd(self.dirty)
        out = AssetBundleExporter(out_dir=out_dir).export(
            self.dirty, gate, out_dir=out_dir, artifact_uri="examples/prd_dirty.json")
        # 门禁未过的 PRD：允许落盘取证（exported=True），但 ok 必须为 False
        self.assertTrue(out["exported"])
        self.assertFalse(out["ok"])
        self.assertFalse(out["gate_ok"])
        self.assertGreater(out["sarif_results"], 0)


    def test_l08_rfc6902_operators(self):
        engine = PRDPatchEngine()
        doc = {"a": {"b": [1, 2]}, "keep": "x"}
        ops = [
            {"op": "test", "path": "/keep", "value": "x"},
            {"op": "replace", "path": "/a/b/0", "value": 9},
            {"op": "add", "path": "/a/b/-", "value": 3},
            {"op": "add", "path": "/a/c", "value": True},
            {"op": "remove", "path": "/a/b/1"},
            {"op": "copy", "from": "/keep", "path": "/copied"},
            {"op": "move", "from": "/copied", "path": "/a/moved"},
        ]
        patched, log = engine.apply(doc, ops)
        self.assertEqual(patched["a"]["b"], [9, 3])
        self.assertTrue(patched["a"]["c"])
        self.assertEqual(patched["a"]["moved"], "x")
        self.assertNotIn("copied", patched)
        self.assertEqual(doc, {"a": {"b": [1, 2]}, "keep": "x"}, "原文档必须零修改")
        self.assertTrue(all(item["ok"] for item in log))

    def test_l08_test_operator_blocks(self):
        engine = PRDPatchEngine()
        with self.assertRaises(PatchTestFailed):
            engine.apply({"v": 1}, [{"op": "test", "path": "/v", "value": 2}])
        with self.assertRaises(PatchError):
            engine.apply({"v": 1}, [{"op": "replace", "path": "/nope", "value": 2}])
        with self.assertRaises(PatchError):
            engine.apply({"v": 1}, [{"op": "unknown", "path": "/v"}])

    def test_l08_diff_roundtrip_and_local_patch(self):
        with open(os.path.join(HERE, "examples", "prd_patch_ops.json"), encoding="utf-8") as f:
            ops = json.load(f)["operations"]
        engine = PRDPatchEngine()
        patched, _ = engine.apply(self.prd, ops)
        # 差量 roundtrip：diff → apply 必须还原同一文档
        generated = engine.diff(self.prd, patched)
        rebuilt, _ = engine.apply(self.prd, generated)
        self.assertEqual(rebuilt, patched)
        # 未改动区域零漂移
        self.assertEqual(patched["problem_statement"], self.prd["problem_statement"])
        self.assertEqual(patched["risks"], self.prd["risks"])
        self.assertEqual(patched["metrics"], self.prd["metrics"])
        self.assertNotEqual(patched["acceptance_criteria"][0]["then"],
                            self.prd["acceptance_criteria"][0]["then"])
        stats = engine.stats(self.prd, patched, ops)
        # 字段级零漂移必须自证：未被算子覆盖的叶子改动一律为 0
        self.assertEqual(stats["untouched_drift_count"], 0, stats["untouched_drift"])
        self.assertGreaterEqual(stats["untouched_ratio"], 0.8)
        self.assertGreater(stats["bytes_saved_ratio"], 0.3)
        self.assertEqual(stats["common_leaves"], 29)
        self.assertEqual(stats["changed_common_leaves"], ["/acceptance_criteria/0/then"])

    def test_l08_patch_export_artifacts(self):
        out_dir = os.path.join(TMP_ROOT, "l08_patch")
        with open(os.path.join(HERE, "examples", "prd_patch_ops.json"), encoding="utf-8") as f:
            ops = json.load(f)["operations"]
        out = PRDPatchEngine().patch_and_export(
            self.prd, ops, out_dir=out_dir, validate=s03_prd._validate_prd)
        self.assertTrue(out["ok"])
        self.assertEqual(out["layer"], "L08")
        for path in (out["patched_path"], out["diff_path"]):
            self.assertTrue(os.path.isfile(path))
        with open(out["diff_path"], encoding="utf-8") as f:
            report = json.load(f)
        self.assertEqual(report["schema"], "pm.prd.patch/v1")
        self.assertIn("6902", report["rfc"])
        self.assertEqual(len(report["source_sha256"]), 64)
        self.assertTrue(report["gate_after_patch"]["ok"])
        self.assertEqual(report["gate_after_patch"]["passed_gates"], 8)
        self.assertEqual(report["stats"]["untouched_drift_count"], 0)
        self.assertTrue(report["generated_at"])

    def test_l09_slot_bidirectional_sync(self):
        path = os.path.join(TMP_ROOT, "l09_sync.json")
        if os.path.exists(path):
            os.remove(path)
        mem = SessionMemory(path=path)
        mem.update_slot("current_scenario", "lean_mvp")
        self.assertEqual(mem.data["slots"]["current_scenario"], "lean_mvp")
        self.assertEqual(mem.data["current_scenario"], "lean_mvp")
        mem2 = SessionMemory(path=path)
        mem2.update_slot("current_scenario", "enterprise_flagship")
        mem2.save()
        self.assertEqual(SessionMemory(path=path).get_slot("current_scenario"),
                         "enterprise_flagship")

    def test_l09_disambiguation_and_rollback(self):
        path = os.path.join(TMP_ROOT, "l09_memory.json")
        if os.path.exists(path):
            os.remove(path)
        mem = SessionMemory(path=path)
        r = mem.resolve_reference("按刚才第二套方案把 PRD 补全")
        self.assertEqual(r["resolved"][0]["value"], "commercial_standard")
        self.assertEqual(mem.get_slot("current_scenario"), "commercial_standard")
        before = mem.create_snapshot("before")
        r = mem.resolve_reference("切换到小红书投放渠道")
        self.assertEqual(mem.get_slot("channel"), "小红书")
        r = mem.resolve_reference("把它加上移动端适配")
        self.assertIn("移动端适配", mem.get_slot("pending_features"))
        self.assertFalse(r["needs_clarification"])
        after = mem.create_snapshot("after")
        self.assertEqual(after["parent"], before["version"])
        turns_before = [i["turn"] for i in mem.data["interactions"]]
        self.assertEqual(turns_before, [1, 2, 3])
        rolled = mem.rollback(before["version"])
        self.assertTrue(rolled["ok"])
        self.assertIsNone(mem.get_slot("channel"))
        self.assertIsNone(mem.get_slot("pending_features"))
        self.assertEqual(mem.get_slot("current_scenario"), "commercial_standard")
        # 对话历史 append-only：回滚只追加系统标记，不抹掉已发生的用户轮次
        self.assertEqual([i["turn"] for i in mem.data["interactions"]], [1, 2, 3, 4])
        self.assertEqual(mem.data["interactions"][-1]["role"], "system")
        self.assertEqual(mem.data["turn"], 4)
        self.assertIn("渠道", mem.data["interactions"][1]["text"])

    def test_l09_out_of_range_ordinal_requires_clarification(self):
        path = os.path.join(TMP_ROOT, "l09_ordinal.json")
        if os.path.exists(path):
            os.remove(path)
        mem = SessionMemory(path=path)
        out = mem.resolve_reference("把第 7 套方案写进 PRD")
        self.assertTrue(out["needs_clarification"])
        self.assertEqual(out["resolved"][0]["kind"], "unresolved")

    def test_l09_feature_append_without_pronoun(self):
        path = os.path.join(TMP_ROOT, "l09_feature.json")
        if os.path.exists(path):
            os.remove(path)
        mem = SessionMemory(path=path)
        mem.update_slot("current_scenario", "lean_mvp")
        out = mem.resolve_reference("这个方案再加一个埋点")
        self.assertFalse(out["needs_clarification"])
        self.assertEqual(out["resolved"][0]["kind"], "feature")
        self.assertTrue(any("埋点" in f for f in mem.get_slot("pending_features")))

    def test_l09_unresolved_pronoun_requires_clarification(self):
        path = os.path.join(TMP_ROOT, "l09_fresh.json")
        if os.path.exists(path):
            os.remove(path)
        fresh = SessionMemory(path=path)
        out = fresh.resolve_reference("它到底该怎么改")
        self.assertTrue(out["needs_clarification"])
        self.assertEqual(out["resolved"][0]["kind"], "unresolved")

    def test_l09_self_test_matrix(self):
        path = os.path.join(TMP_ROOT, "l09_selftest.json")
        if os.path.exists(path):
            os.remove(path)
        out = SessionMemory(path=path).self_test()
        self.assertTrue(out["ok"])
        steps = {s["step"]: s["ok"] for s in out["steps"]}
        self.assertTrue(steps["序数消歧（第二套方案）"])
        self.assertTrue(steps["一键回滚"])
        self.assertTrue(steps["跨进程重载（不失忆）"])


    def test_l10_retry_backoff_jitter(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise TimeoutError("timeout")
            return "done"

        out = retry_with_backoff(flaky, attempts=4, base_delay=0.05, max_delay=0.2,
                                 rng=random.Random(11), sleep=lambda _s: None)
        self.assertTrue(out["ok"])
        self.assertEqual(out["attempts"], 3)
        self.assertEqual(len(out["delays"]), 2)
        self.assertLessEqual(max(out["delays"]), 0.2)

        def always_fail():
            raise ValueError("boom")

        failed = retry_with_backoff(always_fail, attempts=3, base_delay=0.01,
                                    rng=random.Random(11), sleep=lambda _s: None)
        self.assertFalse(failed["ok"])
        self.assertEqual(failed["attempts"], 3)
        self.assertIn("ValueError", failed["last_error"])

    def test_l10_circuit_breaker_three_states(self):
        now = {"t": 500.0}
        breaker = CircuitBreaker("test", failure_threshold=2, recovery_timeout=10.0,
                                 clock=lambda: now["t"])
        self.assertEqual(breaker.state, CLOSED)

        def boom():
            raise ConnectionError("reset")

        for _ in range(2):
            with self.assertRaises(ConnectionError):
                breaker.call(boom)
        self.assertEqual(breaker.state, OPEN)
        with self.assertRaises(CircuitOpenError):
            breaker.call(lambda: 1)

        now["t"] += 11.0
        self.assertEqual(breaker.state, HALF_OPEN)
        self.assertEqual(breaker.call(lambda: "ok"), "ok")
        self.assertEqual(breaker.state, CLOSED)

        # 半开态试探失败 → 回到 OPEN；再失败达阈值 → OPEN → 冷却 → HALF_OPEN
        now["t"] += 11.0
        with self.assertRaises(ConnectionError):
            breaker.call(boom)          # CLOSED 下第 1 次失败
        with self.assertRaises(ConnectionError):
            breaker.call(boom)          # CLOSED 下第 2 次失败 → OPEN
        self.assertEqual(breaker.state, OPEN)
        now["t"] += 11.0
        self.assertEqual(breaker.state, HALF_OPEN)
        with self.assertRaises(ConnectionError):
            breaker.call(boom)          # 半开试探失败 → OPEN
        self.assertEqual(breaker.state, OPEN)
        tos = [t["to"] for t in breaker.stats()["transitions"]]
        self.assertEqual(tos, [OPEN, HALF_OPEN, CLOSED, OPEN, HALF_OPEN, OPEN])

    def test_l10_watchdog_timeout_and_isolation(self):
        wd = Watchdog(default_timeout=0.3)
        self.assertTrue(wd.run(lambda: 7)["ok"])
        slow = wd.run(lambda: time.sleep(0.3) or "late", timeout=0.05)
        self.assertEqual(slow["status"], "TIMEOUT")

        ok_iso = wd.run_isolated("print('alive')", timeout=10)
        self.assertTrue(ok_iso["ok"])
        self.assertIn("alive", ok_iso["stdout"])
        killed = wd.run_isolated("import time; time.sleep(3)", timeout=0.3)
        self.assertEqual(killed["status"], "TIMEOUT")
        self.assertTrue(killed["killed"] and killed["process_isolated"])

    def test_l10_telemetry_chain(self):
        path = os.path.join(TMP_ROOT, "l10_telemetry.jsonl")
        if os.path.exists(path):
            os.remove(path)
        tracer = TelemetryTracer(path=path)
        with tracer.span("outer", payload={"layer": "L10"}) as span:
            tracer.log("inner.1", payload={"a": 1}, duration_ms=1.0)
            tracer.log("inner.2", payload={"b": 2})
        chain = tracer.verify_chain()
        self.assertTrue(chain["ok"])
        self.assertEqual(chain["lines"], 3)
        self.assertEqual(len(chain["traces"]), 1)
        self.assertEqual(chain["unique_spans"], 3)
        with open(path, encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]
        outer = next(r for r in records if r["name"] == "outer")
        children = [r for r in records if r["name"].startswith("inner")]
        self.assertTrue(all(c["parent_span_id"] == outer["span_id"] for c in children))
        self.assertTrue(all(len(r["sha256"]) == 64 for r in records))

    def test_l10_self_test_matrix(self):
        path = os.path.join(TMP_ROOT, "l10_selftest_telemetry.jsonl")
        out = watchdog_self_test(telemetry_path=path)
        self.assertTrue(out["ok"])
        steps = {s["step"]: s["ok"] for s in out["steps"]}
        for name in ("指数退避重试", "熔断 OPEN", "OPEN 态硬拒绝",
                     "冷却进入 HALF_OPEN", "半开试探成功 → CLOSED",
                     "看门狗软超时", "子进程硬隔离 kill", "遥测 JSONL 链路完整"):
            self.assertTrue(steps.get(name), name)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R18 十维演进集成测试套件（第二轨 · SOP v13.0 §六.4 双轨门禁）。

与 run_tests.py（原有基准套件）并列，单独作为「演进集成门禁」：
    python -m unittest tests.test_evolution_l01_l10 -v

覆盖每一层元模型的真实能力断言（不是「文件存在即通过」）：
- L01 真实 SQL 执行、SQL 聚合出的空值/重复、增量守恒、确定性指纹；
- L02 自然语言实体抽取、5 阶段 Kahn 拓扑、环检测、工时与关键路径；
- L03 四条红线刚性拦截、字段别名自愈、有界反思重试。
L04~L10 随批次演进逐层追加，禁止未落地就伪造打卡。
"""
from __future__ import annotations

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, os.path.dirname(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engines import DataEngRuntimeEngine, DataEngIntentCompiler, DataEngReflexiveHealer  # noqa: E402


def _ws_tmp(*parts: str) -> str:
    """SOP §5.7/§5.4：临时目录约束在 workspace/tmp 内，禁止系统全局 tempfile。"""
    p = os.path.join(ROOT, "workspace", "tmp", *parts)
    os.makedirs(p, exist_ok=True)
    return p


# =========================================================================== #
# L01 工具实体层
# =========================================================================== #
class L01RuntimeEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DataEngRuntimeEngine(workspace_dir=_ws_tmp("l01"))

    def test_health_probe_roundtrip(self):
        h = self.engine.probe_health()
        self.assertEqual(h["status"], "HEALTHY")
        self.assertTrue(h["roundtrip"])
        self.assertIn(h["engine"], ("duckdb", "sqlite3"))
        self.assertEqual(h["probe_rows"], 3)

    def test_run_sql_executes_real_aggregate(self):
        rows = [{"id": 1, "amt": 10}, {"id": 2, "amt": 20}, {"id": 3, "amt": 30}]
        out = self.engine.run_sql({"orders": rows},
                                  "SELECT COUNT(*) AS n, SUM(amt) AS total FROM orders")
        self.assertTrue(out["ok"])
        self.assertEqual(out["rows"], [[3, 60]])
        self.assertEqual(out["columns"], ["n", "total"])
        self.assertEqual(len(out["sha256"]), 64)

    def test_run_sql_filters_real_rows(self):
        rows = [{"id": 1, "state": "ok"}, {"id": 2, "state": "failed"}]
        out = self.engine.run_sql({"runs": rows},
                                  "SELECT id FROM runs WHERE state = 'failed'")
        self.assertEqual(out["rows"], [[2]])

    def test_profile_computes_null_ratio_from_sql(self):
        rows = [{"id": 1, "note": "a"}, {"id": 2, "note": None},
                {"id": 3, "note": ""}, {"id": 4, "note": "d"}]
        p = self.engine.profile_table(rows, table="q")
        self.assertEqual(p["row_count"], 4)
        # 空串按 ELT 口径归一为 NULL：4 行中 2 行为空 → 0.5
        self.assertAlmostEqual(p["null_ratio"]["note"], 0.5, places=6)
        self.assertEqual(p["numeric_ranges"]["id"], {"min": 1, "max": 4})

    def test_profile_computes_dup_ratio(self):
        rows = [{"id": 1, "v": "x"}, {"id": 1, "v": "x"}, {"id": 2, "v": "y"}]
        p = self.engine.profile_table(rows, table="d")
        # 3 行去重后 2 行 → 重复率 1/3
        self.assertAlmostEqual(p["dup_ratio"], round(1 / 3, 6), places=6)

    def test_gate_passes_clean_rows(self):
        rows = [{"id": 1, "amt": 10}, {"id": 2, "amt": 20}]
        g = self.engine.gate_quality(rows, table="clean")
        self.assertTrue(g["ok"], [c for c in g["checks"] if not c["ok"]])
        self.assertEqual(g["grade"], "PASS")

    def test_gate_blocks_dirty_rows(self):
        rows = [{"id": 1, "name": None}, {"id": 2, "name": None}, {"id": 3, "name": "x"}]
        g = self.engine.gate_quality(rows, table="dirty")
        self.assertFalse(g["ok"])
        self.assertEqual(g["grade"], "FAIL")
        self.assertTrue(any(not c["ok"] and c["dim"] == "null_ratio" for c in g["checks"]))

    def test_gate_blocks_out_of_range(self):
        rows = [{"id": 1, "amt": 10}, {"id": 2, "amt": 9999}]
        g = self.engine.gate_quality(rows, table="range",
                                     ranges={"amt": {"min": 0, "max": 100}})
        self.assertFalse(g["ok"])
        self.assertEqual(g["out_of_range_rows"], 1)
        self.assertTrue(any(c["dim"] == "range" and not c["ok"] for c in g["checks"]))

    def test_incremental_conservation_holds(self):
        base = [{"id": 1, "v": 1}, {"id": 2, "v": 2}]
        incoming = [{"id": 2, "v": 22}, {"id": 3, "v": 3}]
        c = self.engine.incremental_conservation(base, incoming, key="id")
        self.assertTrue(c["conserved"], c)
        self.assertEqual((c["base_count"], c["updated_count"], c["inserted_count"]), (2, 1, 1))
        self.assertEqual(c["target_count"], 3)
        self.assertEqual(c["delta"], 0)

    def test_incremental_conservation_detects_duplicate_key_drift(self):
        base = [{"id": 1, "v": 1}]
        incoming = [{"id": 1, "v": 10}, {"id": 1, "v": 11}]
        c = self.engine.incremental_conservation(base, incoming, key="id")
        self.assertFalse(c["conserved"])
        self.assertNotEqual(c["delta"], 0)

    def test_fingerprint_is_deterministic(self):
        a = [{"id": 1, "v": "x"}, {"id": 2, "v": "y"}]
        b = [{"v": "y", "id": 2}, {"v": "x", "id": 1}]
        self.assertEqual(self.engine.fingerprint(a), self.engine.fingerprint(b))
        self.assertNotEqual(self.engine.fingerprint(a),
                            self.engine.fingerprint([{"id": 1, "v": "x"}]))


# =========================================================================== #
# L02 意图解构层
# =========================================================================== #
class L02IntentCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiler = DataEngIntentCompiler()

    def test_compiles_five_stage_dag(self):
        dag = self.compiler.compile_intent(
            "把 orders 和 dwd_orders 上最近3天的增量数据做成看板，2小时内要新鲜")
        self.assertEqual(dag["stage_count"], 5)
        self.assertEqual([n["id"] for n in dag["nodes"]],
                         ["01_profile", "02_model", "03_orchestrate", "04_gate", "05_publish"])
        self.assertEqual(len(dag["edges"]), 6)
        self.assertTrue(dag["acyclic"])

    def test_kahn_topological_order_is_valid(self):
        dag = self.compiler.compile_intent("把订单表做成看板")
        order = dag["topological_order"]
        pos = {n: i for i, n in enumerate(order)}
        for e in dag["edges"]:
            self.assertLess(pos[e["from"]], pos[e["to"]], e)

    def test_entities_extracted(self):
        dag = self.compiler.compile_intent(
            "把 orders 最近30天的增量数据同步成看板，空值率不超过0.05")
        e = dag["entities"]
        self.assertIn("orders", e["tables"])
        self.assertEqual(e["window_days"], 30)
        self.assertEqual(e["mode"], "incremental")
        self.assertEqual(e["destination"], "dashboard")
        self.assertAlmostEqual(e["thresholds"]["max_null_ratio"], 0.05)

    def test_sla_and_multiplier(self):
        fast = self.compiler.compile_intent("把 orders 最近7天增量做成看板，1小时内要新鲜")
        slow = self.compiler.compile_intent("把 orders 最近7天增量做成看板，48小时内要新鲜")
        self.assertEqual(fast["entities"]["sla_hours"], 1)
        self.assertGreater(fast["total_effort_h"], slow["total_effort_h"])

    def test_unspecified_mode_has_warning(self):
        dag = self.compiler.compile_intent("把 orders 处理一下")
        self.assertEqual(dag["entities"]["mode"], "unspecified")
        self.assertTrue(any("模式" in w for w in dag["warnings"]))

    def test_cycle_detection(self):
        out = DataEngIntentCompiler.topological_order(
            ["a", "b"], [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}])
        self.assertFalse(out["acyclic"])
        self.assertEqual(sorted(out["cycle_nodes"]), ["a", "b"])

    def test_critical_path_and_budget(self):
        dag = self.compiler.compile_intent("把 orders 最近90天全量重算做成报表")
        self.assertEqual(dag["critical_path"][0], "01_profile")
        self.assertEqual(dag["critical_path"][-1], "05_publish")
        self.assertGreater(dag["total_effort_h"], 0)
        self.assertAlmostEqual(dag["total_man_days"],
                               round(dag["total_effort_h"] / 8.0, 2), places=2)


# =========================================================================== #
# L03 自愈反思层
# =========================================================================== #
class L03ReflexiveHealerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.healer = DataEngReflexiveHealer()

    def test_four_redlines_detected(self):
        cases = [
            ("连接串是 jdbc:mysql://root@prod", "R18-RL-01"),
            ("我直接回填了 2026 全年数据", "R18-RL-02"),
            ("给出订单量的业务归因与显著性结论", "R18-RL-03"),
            ("这笔退款直接打款给客户", "R18-RL-04"),
        ]
        for text, rule_id in cases:
            hits = self.healer.scan_redlines(text)
            self.assertTrue(hits, text)
            self.assertEqual(hits[0]["rule_id"], rule_id, text)

    def test_clean_text_has_no_redline(self):
        self.assertEqual(self.healer.scan_redlines("orders 表质量门禁全部通过"), [])

    def test_statistical_claims_hit_redline(self):
        hits = self.healer.scan_redlines("环比 +1.8pp，95% CI [0.6, 3.0]pp")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["rule_id"], "R18-RL-03")

    def test_redline_raises_with_handoff(self):
        with self.assertRaises(ValueError) as ctx:
            self.healer.audit_redlines("api_key=sk-abc123")
        msg = str(ctx.exception)
        self.assertIn("[REDLINE BLOCKED]", msg)
        self.assertIn("R20", msg)

    def test_heal_maps_aliases_and_fills_skeleton(self):
        out = self.healer.heal_artifact({"table_name": "orders", "dag": "dag_1"})
        self.assertTrue(out["healed"])
        self.assertEqual(out["artifact"]["table"], "orders")
        self.assertEqual(out["artifact"]["dag_id"], "dag_1")
        self.assertEqual(out["artifact"]["owner"], "蛙数仓（R18）")
        self.assertTrue(out["needs_revalidation"])
        self.assertIn("owner", out["filled"])

    def test_heal_never_fabricates_checks(self):
        out = self.healer.heal_artifact({"table": "orders"})
        self.assertEqual(out["artifact"]["checks"], [])
        self.assertTrue(out["needs_revalidation"])

    def test_reflection_retry_recovers_from_alias_drift(self):
        def gate(payload):
            if "table" not in payload:
                raise KeyError("missing table")
            return {"table": payload["table"], "ok": True}

        out = self.healer.run_with_reflection(gate, {"table_name": "orders"}, max_attempts=3)
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["attempts"], 2)
        self.assertEqual(out["result"]["table"], "orders")

    def test_reflection_does_not_swallow_redline(self):
        def explode(_payload):
            raise ValueError("[REDLINE BLOCKED] R18-RL-02 未授权破坏性动作")

        out = self.healer.run_with_reflection(explode, {"table": "orders"}, max_attempts=3)
        self.assertFalse(out["ok"])
        self.assertTrue(out["blocked"])
        self.assertEqual(out["attempts"], 1)

    def test_reflection_bounded_gives_up(self):
        state = {"n": 0}

        def always_fail(_payload):
            state["n"] += 1
            raise RuntimeError(f"timeout boom #{state['n']}")

        out = self.healer.run_with_reflection(always_fail, {"table": "orders"}, max_attempts=2)
        self.assertFalse(out["ok"])
        self.assertEqual(out["attempts"], 2)
        self.assertTrue(out["reflections"])


# =========================================================================== #
# L04 领域账本层
# =========================================================================== #
class L04SpecLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from engines import DataEngSpecLedger
        cls.ledger = DataEngSpecLedger()

    def test_spec_ledger_is_ssot(self):
        spec = self.ledger.load_spec()
        self.assertEqual(spec["version"], "v1.0")
        self.assertEqual(spec["gates_count"], 8)
        self.assertEqual(spec["metrics_count"], 8)
        self.assertEqual(spec["redlines_count"], 4)
        self.assertIn("蛙数仓", spec["dri"])
        self.assertAlmostEqual(spec["thresholds"]["max_null_ratio"], 0.1)
        self.assertEqual(spec["metrics"]["PSR"]["target"]["op"], "≥")

    def test_missing_spec_fails_closed(self):
        from engines import DataEngSpecLedger
        with self.assertRaises(FileNotFoundError):
            DataEngSpecLedger(spec_path=_ws_tmp("l04") + "/nope.md").load_spec()

    def test_evaluate_all_pass(self):
        out = self.ledger.evaluate({
            "PSR": 0.996, "FSR": 0.991, "DQR": 0.985, "LCR": 1.0,
            "BCR": 1.0, "MTTD": 8, "DMR": 0.03, "ORT": 0,
        })
        self.assertTrue(out["ok"], {k: v for k, v in out["metrics"].items() if not v["ok"]})
        self.assertEqual(out["passed"], 8)

    def test_evaluate_missing_evidence_fails(self):
        out = self.ledger.evaluate({"PSR": 99.9})
        self.assertFalse(out["ok"])
        self.assertFalse(out["metrics"]["LCR"]["ok"])
        self.assertIn("缺证据", out["metrics"]["LCR"]["reason"])

    def test_evaluate_tolerance_boundary(self):
        # FSR 目标 99.0%，容差 0.010 → 98.5% 落在容差内仍算达标
        out = self.ledger.evaluate({"FSR": 0.985})
        self.assertTrue(out["metrics"]["FSR"]["ok"])
        out2 = self.ledger.evaluate({"FSR": 0.95})
        self.assertFalse(out2["metrics"]["FSR"]["ok"])

    def test_gate_blocker(self):
        spec = self.ledger.load_spec()
        all_pass = {g["name"]: True for g in spec["gates"]}
        self.assertTrue(self.ledger.evaluate_gates(all_pass)["ok"])
        all_pass["质量门禁"] = False
        blocked = self.ledger.evaluate_gates(all_pass)
        self.assertFalse(blocked["ok"])
        self.assertIn("质量门禁", blocked["blocked_by"])

    def test_export_three_artifacts(self):
        out = self.ledger.export(_ws_tmp("l04_export"))
        self.assertTrue(os.path.exists(out["json"]))
        self.assertTrue(os.path.exists(out["sql"]))
        self.assertTrue(os.path.exists(out["dbt_schema"]))
        with open(out["sql"], encoding="utf-8") as f:
            sql = f.read()
        self.assertIn("CHECK", sql)
        self.assertIn(str(self.ledger.load_spec()["thresholds"]["max_dup_ratio"]), sql)

    def test_thresholds_come_from_spec_ssot(self):
        """账本必须真正接管门禁阈值，而不是只做 spec_ref 标签。"""
        from skills import _common as c
        th = c.load_thresholds()
        self.assertEqual(th["_spec_source"], "DATAENG_SPEC.md v1.0")
        spec = self.ledger.load_spec()["thresholds"]
        self.assertEqual(th["quality"]["default_max_null_ratio"],
                         spec["max_null_ratio"])
        self.assertEqual(th["quality"]["default_max_dup_ratio"],
                         spec["max_dup_ratio"])
        self.assertEqual(th["quality"]["default_max_age_hours"],
                         spec["max_age_hours"])


# =========================================================================== #
# L05 质感去劣化
# =========================================================================== #
class L05SlopGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from engines import DataEngSlopGuard
        cls.guard = DataEngSlopGuard()

    def test_detects_slop_terms(self):
        out = self.guard.audit("数据管道整体良好，按需采购，视情况而定，相关细节待定，持续关注")
        self.assertTrue(out["has_slop"])
        self.assertGreaterEqual(len(out["terms_found"]), 4)
        self.assertLess(out["actionability_score"], 70)
        self.assertEqual(out["grade"], "FAIL")

    def test_longest_term_wins(self):
        out = self.guard.audit("相关细节待定")
        self.assertEqual(out["terms_found"], ["相关细节待定"])
        self.assertEqual(len(out["hits"]), 1)

    def test_clean_removes_all_slop(self):
        out = self.guard.clean("数据管道整体良好，按需采购，视情况而定，相关细节待定")
        self.assertTrue(out["ok"])
        self.assertFalse(out["after"]["has_slop"])
        self.assertGreaterEqual(out["after"]["actionability_score"], 70)
        self.assertIn("蛙数仓", out["cleaned"])
        self.assertRegex(out["cleaned"], r"\d")

    def test_clean_is_idempotent(self):
        once = self.guard.clean("整体正常，持续关注")["cleaned"]
        twice = self.guard.clean(once)["cleaned"]
        self.assertEqual(once, twice)

    def test_quantified_text_passes(self):
        text = "PSR=99.6%（近24h，目标≥99.5%），空值率0.004；DRI 蛙数仓（R18），T+1 10:00 闭环。"
        out = self.guard.audit(text)
        self.assertFalse(out["has_slop"])
        self.assertEqual(out["grade"], "PASS")
        self.assertGreaterEqual(out["actionability_score"], 70)

    def test_clean_never_fabricates_measurements(self):
        """清洗只做可行动重述：不得凭空生成 PSR/CI 等未实测数字。"""
        out = self.guard.clean("整体良好，显著提升，持续关注")
        for fabricated in ("99.6", "98.5", "DQR=", "CI [", "+1.8pp", "环比"):
            self.assertNotIn(fabricated, out["cleaned"], fabricated)
        self.assertTrue(out["ok"])

    def test_audit_requires_dri(self):
        out = self.guard.audit("PSR 目标 99.5%，门禁全部满足")
        self.assertFalse(out["has_dri"])
        self.assertFalse(out["ok"])
        self.assertTrue(any(c["dim"] == "slop.dri" and not c["ok"] for c in out["checks"]))


# =========================================================================== #
# L06 横向决策层
# =========================================================================== #
class L06ScenarioMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from engines import DataEngScenarioMatrix
        cls.matrix = DataEngScenarioMatrix()

    def test_three_scenarios(self):
        out = self.matrix.generate()
        self.assertEqual(out["scenario_count"], 3)
        self.assertEqual({r["id"] for r in out["scenarios"]},
                         {"fast", "balanced", "strict"})
        self.assertEqual([r["rank"] for r in out["scenarios"]], [1, 2, 3])

    def test_balanced_recommended_by_default(self):
        out = self.matrix.generate()
        self.assertEqual(out["recommended_id"], "balanced")

    def test_strict_context_promotes_strict(self):
        out = self.matrix.generate({"strict_consistency": True})
        self.assertEqual(out["recommended_id"], "strict")

    def test_budget_context_promotes_fast(self):
        out = self.matrix.generate({"budget_days": 1})
        self.assertEqual(out["recommended_id"], "fast")

    def test_roi_ratio_present(self):
        out = self.matrix.generate()
        for row in out["scenarios"]:
            self.assertGreater(row["roi_ratio"], 0)
            self.assertEqual(set(row["scores"]),
                             {"lead_time", "cost", "risk", "freshness",
                              "consistency", "weighted"})

    def test_scores_bounded_and_deterministic(self):
        a = self.matrix.generate({"sla_hours": 2})
        b = self.matrix.generate({"sla_hours": 2})
        self.assertEqual(a, b)
        for row in a["scenarios"]:
            self.assertGreaterEqual(row["total_score"], 0)
            self.assertLessEqual(row["total_score"], 100)
            self.assertAlmostEqual(row["effort_man_days"], row["lead_time_days"])

    def test_markdown_board(self):
        md = self.matrix.render_markdown(self.matrix.generate())
        self.assertIn("数据管道三维方案权衡矩阵", md)
        self.assertIn("稳健批流版", md)
        self.assertEqual(md.count("\n|"), 5)


# =========================================================================== #
# L07 伴生消费层
# =========================================================================== #
class L07AssetBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from engines import DataEngAssetBundle
        cls.bundle = DataEngAssetBundle(workspace_dir=_ws_tmp("l07"))
        cls.payload = {
            "pipeline": {"skill": "quality", "action": "check"},
            "gates": [
                {"id": "G1", "name": "结构门禁", "ok": True},
                {"id": "G2", "name": "连接门禁", "ok": True},
                {"id": "G3", "name": "转换门禁", "ok": True},
                {"id": "G4", "name": "质量门禁", "ok": False, "blocking": True,
                 "message": "空值率 0.12 > 0.10"},
            ],
            "delivery_dag": {
                "topological_order": ["01_profile", "02_model"],
                "nodes": [{"id": "01_profile", "stage": "audit", "title": "探查",
                           "owner": "蛙数仓"}],
                "edges": [{"from": "01_profile", "to": "02_model", "reason": "依赖"}],
            },
            "artifact_uri": "workspace/rounds/L02_dag.json",
        }

    def test_export_and_self_validate(self):
        out = self.bundle.export("t1", self.payload, out_dir=_ws_tmp("l07", "bundles"))
        self.assertTrue(out["ok"])
        check = self.bundle.validate_export(out)
        self.assertTrue(check["ok"], [c for c in check["checks"] if not c["ok"]])
        for key in ("bundle", "sarif", "vega", "ast"):
            self.assertTrue(os.path.exists(out[key]), key)

    def test_sarif_is_2_1_0_with_failed_gate(self):
        out = self.bundle.export("t2", self.payload, out_dir=_ws_tmp("l07", "b2"))
        with open(out["sarif"], encoding="utf-8") as f:
            sarif = json.load(f)
        self.assertEqual(sarif["version"], "2.1.0")
        results = sarif["runs"][0]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["ruleId"], "G4")
        self.assertEqual(results[0]["level"], "error")
        self.assertEqual(sarif["runs"][0]["tool"]["driver"]["name"],
                         "R18-Washucang-DataEng")
        self.assertFalse(sarif["runs"][0]["invocations"][0]["executionSuccessful"])

    def test_vega_and_ast(self):
        out = self.bundle.export("t3", self.payload, out_dir=_ws_tmp("l07", "b3"))
        with open(out["vega"], encoding="utf-8") as f:
            vega = json.load(f)
        self.assertEqual(vega["$schema"],
                         "https://vega.github.io/schema/vega-lite/v5.json")
        self.assertEqual(len(vega["data"]["values"]), 4)
        with open(out["ast"], encoding="utf-8") as f:
            ast = json.load(f)
        self.assertEqual(ast["kind"], "dataeng_pipeline_ast")
        self.assertEqual(ast["entry"], "01_profile")
        self.assertEqual(len(ast["edges"]), 1)

    def test_validation_rejects_missing_files(self):
        check = self.bundle.validate_export({"bundle": "", "sarif": "",
                                             "vega": "", "ast": ""})
        self.assertFalse(check["ok"])


# =========================================================================== #
# L08 局部差量层
# =========================================================================== #
class L08DiffPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from engines import DataEngDiffPatchEngine
        cls.engine = DataEngDiffPatchEngine()

    def test_create_apply_roundtrip(self):
        old = {"a": 1, "b": [1, 2], "c": {"d": 1}}
        new = {"a": 2, "b": [1, 3, 4], "c": {"d": 1, "e": 5}}
        patch = self.engine.create_patch(old, new)
        self.assertTrue(patch)
        self.assertEqual(self.engine.apply_patch(old, patch), new)
        # 原文档不得被就地篡改
        self.assertEqual(old, {"a": 1, "b": [1, 2], "c": {"d": 1}})

    def test_replace_missing_path_raises(self):
        with self.assertRaises(KeyError):
            self.engine.apply_patch({"a": 1},
                                    [{"op": "replace", "path": "/zzz", "value": 2}])

    def test_test_op_guards_value(self):
        with self.assertRaises(ValueError):
            self.engine.apply_patch({"a": 1},
                                    [{"op": "test", "path": "/a", "value": 2}])

    def test_add_remove_list_semantics(self):
        doc = {"xs": [1, 2, 3]}
        out = self.engine.apply_patch(doc, [
            {"op": "remove", "path": "/xs/1"},
            {"op": "add", "path": "/xs/-", "value": 9},
        ])
        self.assertEqual(out["xs"], [1, 3, 9])

    def test_incremental_revalidation_maps_gate(self):
        plan = self.engine.plan_incremental_revalidation(
            [{"op": "replace", "path": "/watermark_field", "value": "ts"}])
        self.assertEqual(plan["affected_gates"], ["G6"])
        self.assertIn("G1", plan["reuse_gates"])
        self.assertFalse(plan["requires_full_revalidation"])

    def test_metadata_only_reuses_all_gates(self):
        plan = self.engine.plan_incremental_revalidation(
            [{"op": "replace", "path": "/total_effort_h", "value": 12}])
        self.assertEqual(plan["affected_gates"], [])
        self.assertEqual(len(plan["reuse_gates"]), 8)

    def test_unknown_pointer_forces_full_revalidation(self):
        plan = self.engine.plan_incremental_revalidation(
            [{"op": "replace", "path": "/weird_key", "value": 1}])
        self.assertTrue(plan["requires_full_revalidation"])

    def test_agent_patch_entrypoint(self):
        """L08 必须能从主入口 agent.py patch 走通，而不是只在测试里可用。"""
        import agent
        tmp = _ws_tmp("l08")
        base_path = os.path.join(tmp, "base.json")
        patch_path = os.path.join(tmp, "patch.json")
        out_path = os.path.join(tmp, "out.json")
        with open(base_path, "w", encoding="utf-8") as f:
            json.dump({"watermark_field": "ts", "modes": ["a"]}, f)
        with open(patch_path, "w", encoding="utf-8") as f:
            json.dump([{"op": "replace", "path": "/watermark_field",
                        "value": "updated_at"}], f)
        out = agent._run_patch(agent._mkns(base=base_path, patch=patch_path,
                                           out=out_path))
        self.assertTrue(out["ok"])
        self.assertEqual(out["patched"]["watermark_field"], "updated_at")
        self.assertEqual(out["plan"]["affected_gates"], ["G6"])
        with open(out_path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["plan"]["affected_gates"], ["G6"])


# =========================================================================== #
# L09 会话记忆层
# =========================================================================== #
class L09SessionMemoryTests(unittest.TestCase):
    def _mem(self, sid="t"):
        from engines import DataEngSessionMemory
        return DataEngSessionMemory(workspace_dir=_ws_tmp("l09"), session_id=sid)

    def test_slot_bidirectional_sync_and_persistence(self):
        mem = self._mem("sync")
        out = mem.update_slot("sla_hours", 2)
        self.assertEqual(out["slots"], 2)
        self.assertEqual(out["active"], 2)
        self.assertEqual(out["mirror"], 2)
        reloaded = self._mem("sync")
        self.assertEqual(reloaded.get_slot("sla_hours"), 2)
        self.assertEqual(reloaded.state.get("active_sla_hours"), 2)

    def test_disambiguate_scenario_second(self):
        from engines import DataEngScenarioMatrix
        mem = self._mem("scn")
        mem.set_matrix(DataEngScenarioMatrix().generate())
        out = mem.disambiguate("按刚才第二套方案调整")
        self.assertTrue(out["resolved"])
        # ranking[1] 为 fast
        self.assertEqual(out["value"]["id"], "fast")

    def test_disambiguate_scenario_and_sla_together(self):
        from engines import DataEngScenarioMatrix
        mem = self._mem("both")
        mem.set_matrix(DataEngScenarioMatrix().generate())
        out = mem.disambiguate("第二套方案，SLA 改成 2 小时")
        kinds = {a["kind"] for a in out["applied"]}
        self.assertEqual(kinds, {"scenario", "sla"})
        self.assertEqual(mem.get_slot("sla_hours"), 2.0)

    def test_snapshot_rollback(self):
        mem = self._mem("rb")
        mem.update_slot("sla_hours", 2)
        mem.snapshot("before")
        mem.update_slot("sla_hours", 4)
        out = mem.rollback("before")
        self.assertEqual(out["slots"]["sla_hours"], 2)
        self.assertIn("sla_hours", out["changed"])

    def test_unknown_reference_is_unresolved(self):
        mem = self._mem("unknown")
        out = mem.disambiguate("帮我看看那个东西")
        self.assertFalse(out["resolved"])


# =========================================================================== #
# L10 工业容灾层
# =========================================================================== #
class L10TelemetryWatchdogTests(unittest.TestCase):
    def test_retry_backoff_recovers_and_logs(self):
        from engines import CircuitBreaker, DataEngTelemetryWatchdog
        telemetry = os.path.join(_ws_tmp("l10"), "retry.jsonl")
        if os.path.exists(telemetry):  # 隔离上一次运行残留，保证逐行断言确定性
            os.remove(telemetry)
        wd = DataEngTelemetryWatchdog(
            workspace_dir=_ws_tmp("l10"), telemetry_name="retry.jsonl",
            breaker=CircuitBreaker(failure_threshold=5))
        state = {"n": 0}

        def flaky():
            state["n"] += 1
            if state["n"] < 3:
                raise RuntimeError("jitter")
            return "ok"

        out = wd.execute_with_resilience(flaky, retries=3, base_delay=0.001)
        self.assertTrue(out["ok"])
        self.assertEqual(out["attempts"], 3)
        rows = wd.read_telemetry()
        self.assertEqual([r["status"] for r in rows], ["FAILED", "FAILED", "OK"])
        for row in rows:
            for key in ("trace_id", "span_id", "sha256", "duration_ms", "ts"):
                self.assertIn(key, row)

    def test_circuit_opens_and_rejects(self):
        from engines import CircuitBreaker, DataEngTelemetryWatchdog
        wd = DataEngTelemetryWatchdog(
            workspace_dir=_ws_tmp("l10"), telemetry_name="circuit.jsonl",
            breaker=CircuitBreaker(failure_threshold=2, recovery_timeout=60))

        def boom():
            raise TimeoutError("down")

        self.assertFalse(wd.execute_with_resilience(boom, retries=1)["ok"])
        self.assertFalse(wd.execute_with_resilience(boom, retries=1)["ok"])
        rejected = wd.execute_with_resilience(boom, retries=1)
        self.assertEqual(rejected["status"], "CIRCUIT_OPEN")
        self.assertEqual(wd.breaker.state, "OPEN")

    def test_half_open_recovery(self):
        from engines import CircuitBreaker
        import time as _t
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        breaker.record_failure()
        self.assertEqual(breaker.state, "OPEN")
        _t.sleep(0.02)
        self.assertTrue(breaker.allow())
        self.assertEqual(breaker.state, "HALF_OPEN")
        breaker.record_success()
        self.assertEqual(breaker.state, "CLOSED")

    def test_watchdog_timeout(self):
        from engines import CircuitBreaker, DataEngTelemetryWatchdog
        import time as _t
        wd = DataEngTelemetryWatchdog(
            workspace_dir=_ws_tmp("l10"), telemetry_name="wd.jsonl",
            breaker=CircuitBreaker())
        out = wd.watchdog(lambda: (_t.sleep(0.15), "late")[1], timeout_s=0.02)
        self.assertEqual(out["status"], "TIMEOUT")
        fast = wd.watchdog(lambda: 42, timeout_s=0.2)
        self.assertTrue(fast["ok"])
        self.assertEqual(fast["result"], 42)
        self.assertGreaterEqual(wd.health()["records"], 2)


# =========================================================================== #
# L01~L03 主链路接入（防「侧库漂亮、用户路径依旧 fail-open」）
# =========================================================================== #
class L01MainPathWiringTests(unittest.TestCase):
    def test_quality_recomputes_and_catches_fake_numbers(self):
        """自报 row_count=4，真实只有 2 行 → 必须被实测口径拦下。"""
        from skills import s04_quality
        rows = [{"id": 1, "amt": 10}, {"id": 2, "amt": 20}]
        data = {"table": "orders", "rows": rows, "row_count": 4,
                "null_ratio": 0.0, "dup_ratio": 0.0}
        out = s04_quality._validate_check(data)
        self.assertFalse(out["ok"])
        self.assertIn("runtime_engine", out["measured_by"] or "")
        self.assertTrue(any(c["dim"] == "quality.tamper" and not c["ok"]
                            for c in out["checks"]))
        self.assertEqual(out["row_count"], 2)

    def test_quality_measured_clean_rows_pass(self):
        from skills import s04_quality
        rows = [{"id": 1, "amt": 10}, {"id": 2, "amt": 20}]
        out = s04_quality._validate_check({"table": "orders", "rows": rows})
        self.assertTrue(out["ok"], [c for c in out["checks"] if not c["ok"]])
        self.assertEqual(out["measured"]["row_count"], 2)

    def test_quality_without_rows_keeps_legacy_contract(self):
        from skills import s04_quality
        out = s04_quality._validate_check({"table": "orders", "row_count": 1000,
                                           "null_ratio": 0.01, "dup_ratio": 0.0})
        self.assertTrue(out["ok"])
        self.assertIsNone(out["measured_by"])

    def test_incremental_conservation_blocks_duplicate_key(self):
        from skills import s05_incremental
        data = {
            "stream": "orders_inc", "mode": "incremental", "partition": "daily",
            "watermark_field": "updated_at", "idempotency_key": "id",
            "late_arrival_days": 1,
            "base_rows": [{"id": 1, "v": 1}],
            "incoming_rows": [{"id": 1, "v": 2}, {"id": 1, "v": 3}],
            "key": "id",
        }
        out = s05_incremental._validate_strategy(data)
        self.assertFalse(out["ok"])
        self.assertTrue(any(c["dim"] == "strategy.conservation" and not c["ok"]
                            for c in out["checks"]))
        self.assertFalse(out["conservation"]["conserved"])


class L02L03MainPathWiringTests(unittest.TestCase):
    def test_run_task_emits_delivery_dag_and_redline_scan(self):
        from core import workspace as ws_mod, protocol
        import agent

        ws = ws_mod.Workspace(os.path.join(os.path.dirname(ROOT), "workspace"))
        inp = protocol.Port(os.path.join(ROOT, "examples", "quality_check.json"),
                            "data", note="")
        task = protocol.Task(
            title="检查订单表质量", owner="r18",
            intent="帮我看看这批 orders 数据质量达不达标，空值率重复率有没有超",
            inputs=[inp], acceptance=["quality 门禁通过"])
        ws.create_task(task)
        res = agent.run_task(task.task_id)

        self.assertTrue(res.get("ok"), res.get("error"))
        self.assertEqual(res["delivery_dag"]["stage_count"], 5)
        self.assertIn("01_profile", res["delivery_dag"]["topological_order"])
        self.assertGreater(res["delivery_dag"]["total_effort_h"], 0)
        self.assertFalse(res["redline_scan"]["blocked"])
        self.assertTrue(os.path.exists(res["delivery_dag"]["path"]))
        # L04/L05/L06 也在主链路真实生效
        self.assertEqual(res["spec_ref"]["gates_count"], 8)
        self.assertEqual(res["spec_ref"]["thresholds_source"], "DATAENG_SPEC.md")
        self.assertEqual(res["scenario_matrix"]["recommended_id"], "balanced")
        self.assertEqual(len(res["scenario_matrix"]["ranking"]), 3)
        self.assertTrue(os.path.exists(res["scenario_matrix"]["path"]))
        self.assertIn("slop_audit", res)
        self.assertGreaterEqual(
            res["slop_audit"]["narrative"]["after"]["actionability_score"], 70)
        self.assertTrue(res["slop_audit"]["narrative"]["after"]["has_dri"])
        # L07 伴生工件 / L09 记忆 / L10 遥测也在主链路真实生效
        self.assertEqual(res["asset_bundle"]["validation"], "PASS")
        sarif_path = os.path.join(res["asset_bundle"]["dir"], res["asset_bundle"]["sarif"])
        self.assertTrue(os.path.exists(sarif_path))
        self.assertIn("resolved", res["memory"])
        self.assertEqual(res["trace"]["status"], "OK")
        self.assertGreaterEqual(res["trace"]["attempts"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

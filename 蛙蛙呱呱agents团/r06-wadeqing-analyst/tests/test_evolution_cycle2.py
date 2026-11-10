# -*- coding: utf-8 -*-
"""R06 蛙得清 · 三轮 SOP 自升级增量回归套件 (Cycle-2)。

严格遵循 SOP_AGENT_EVOLUTION_UNIVERSAL.md v13.0 双轨零破坏法则：
本套件只新增判据，不修改、不弱化 tests/test_engines_l01_l10.py 中的任何历史契约。
Round 1 (L01~L03) / Round 2 (L04~L06) / Round 3 (L07~L10) 各自独立用例类。
"""
import json
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
for _p in (_HERE, _PARENT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engines import (
    AnalysisEngineManager,
    AnalysisIntentDecompiler,
    AnalysisReflexiveHealer,
    DataSlopGuard,
    MetricsSpecLedgerParser,
    ScenarioComparativeMatrix,
)


class TestRound1ToolsIntentHeal(unittest.TestCase):
    """第 1 轮 SOP · 执行基石 (L01~L03)。"""

    def test_l01_duckdb_sql_sandbox_real_execution(self):
        """L01：DuckDB 嵌入式 SQL 真实执行与分组聚合下推。"""
        mgr = AnalysisEngineManager()
        self.assertTrue(mgr.has_sql_engine(), "duckdb 应可用")
        sandbox = mgr.get_sql_sandbox()
        rows = [
            {"channel": "抖音", "amount": 100.0},
            {"channel": "抖音", "amount": 50.0},
            {"channel": "微信", "amount": 30.0},
        ]
        self.assertEqual(sandbox.register_records("orders", rows), 3)
        res = sandbox.aggregate("orders", "amount", "channel")
        self.assertTrue(res.ok)
        self.assertEqual(res.data["row_count"], 2)
        top = res.data["rows"][0]
        self.assertEqual(top["dim"], "抖音")
        self.assertEqual(float(top["metric_sum"]), 150.0)
        self.assertEqual(int(top["rows"]), 2)

        probe = mgr.probe_all()
        self.assertTrue(probe["all_healthy"])
        self.assertIn("sql", probe["capabilities"]["duckdb"])
        self.assertFalse(probe["degraded"])

    def test_l01_deterministic_money_and_conservation(self):
        """L01：货币分位四舍五入与零容差守恒勾稽。"""
        eng = AnalysisEngineManager().get_engine("native")
        money = eng.execute("money_round", {"amounts": [0.1, 0.2]})
        self.assertTrue(money.ok)
        self.assertEqual(money.data["cent_total"], 0.3)
        self.assertTrue(money.data["cent_safe"])

        ok_cons = eng.execute("conservation_check", {"parts": [10.005, 20.005], "total": 30.01})
        self.assertTrue(ok_cons.data["balanced"])

        bad_cons = eng.execute("conservation_check", {"parts": [10.0, 20.0], "total": 30.5})
        self.assertFalse(bad_cons.data["balanced"])
        self.assertEqual(bad_cons.data["difference"], 0.5)

        dispersion = eng.execute("dispersion_metrics", {"values": [1, 2, 3, 4, 100]})
        self.assertEqual(dispersion.data["count"], 5)
        self.assertEqual(dispersion.data["p50"], 3.0)

    def test_l02_kahn_topology_waves_and_cycle_detection(self):
        """L02：Kahn 拓扑排序、并行波次与环路检测。"""
        dec = AnalysisIntentDecompiler()
        plan = dec.compile_intent(
            "分析上周抖音渠道GMV转化率为什么下滑，做个质检、归因和图表报告", data_rows=100000)
        self.assertTrue(plan["dag_validation"]["valid"])
        self.assertGreaterEqual(plan["step_count"], 4)
        order = plan["execution_order"]
        self.assertEqual(order[0], "step_1_quality")
        for step in plan["dag_steps"]:
            for dep in step["depends_on"]:
                self.assertLess(order.index(dep), order.index(step["step_id"]))
        self.assertGreaterEqual(len(plan["execution_waves"]), 2)
        self.assertGreater(plan["effort_budget"]["total_hours"], 0)
        self.assertGreaterEqual(plan["effort_budget"]["critical_path_hours"], 1.0)

        cyclic = [
            {"step_id": "a", "depends_on": ["b"]},
            {"step_id": "b", "depends_on": ["a"]},
        ]
        topo = dec._kahn_topo_sort(cyclic)
        self.assertFalse(topo["valid"])
        self.assertEqual(topo["cycle_nodes"], ["a", "b"])

    def test_l02_entity_normalization_and_time_conflict(self):
        """L02：指标/维度别名归一与时间窗冲突告警。"""
        plan = AnalysisIntentDecompiler().compile_intent("对比上周和上个月抖音渠道成交额与转化率变化，按城市看")
        self.assertIn("gmv", plan["extracted_entities"]["metrics"])
        self.assertIn("cvr", plan["extracted_entities"]["metrics"])
        self.assertIn("channel", plan["extracted_entities"]["dimensions"])
        self.assertIn("city", plan["extracted_entities"]["dimensions"])
        self.assertTrue(any("multiple_time_windows" in w for w in plan["entity_warnings"]))
        self.assertIsNotNone(plan["extracted_entities"]["time_window_semantic"])

    def test_l03_nested_redline_and_reflexion_loop(self):
        """L03：深层 NaN 定位、结构化红线阻断与 Reflexion 收敛。"""
        healer = AnalysisReflexiveHealer()
        dirty = {
            "conclusion": "必须立即拍板决定上线",
            "shares": [30.0, 20.0],
            "p_value": 0.03,
            "detail": {"segments": [{"name": "抖音", "variance": float("nan")}]},
        }
        report = healer.audit_report(dirty)
        self.assertFalse(report["ok"])
        self.assertTrue(report["redlines_blocked"])
        self.assertIn("R06-REDLINE-101", report["blocked_codes"])
        self.assertTrue(any(i["path"] == "/detail/segments/0/variance" for i in report["issues"]))

        healed = healer.reflect_and_heal(dirty, max_rounds=3)
        self.assertTrue(healed["_reflection_converged"])
        self.assertTrue(healed["_reflexive_healed"])
        self.assertNotIn("必须立即", healed["conclusion"])
        self.assertEqual(sum(healed["shares"]), 100.0)
        self.assertEqual(healed["detail"]["segments"][0]["variance"], 0.0)
        self.assertGreaterEqual(healed["_lesson_count"], 1)
        self.assertIn("decision_handoff", healed)

    def test_l03_sql_self_debug_rewrite(self):
        """L03：SQL 执行错误自愈重写 (Self-Debug)。"""
        healer = AnalysisReflexiveHealer()
        out = healer.rewrite_sql(
            'SELECT * FROM t WHERE a == 1 AND b = 10 / 0',
            'Binder Error: Referenced column "a" not found',
        )
        self.assertTrue(out["changed"])
        self.assertNotIn("==", out["rewritten_sql"])
        self.assertIn("NULLIF(0,0)", out["rewritten_sql"])
        self.assertTrue(out["rewritten_sql"].rstrip().endswith(";"))
        self.assertGreaterEqual(len(out["fixes"]), 2)


class TestRound2SpecSlopScenario(unittest.TestCase):
    """第 2 轮 SOP · 专业深度 (L04~L06)。"""

    def test_l04_ledger_integrity_and_schema(self):
        """L04：账本指纹、schema 校验与阈值统一读取。"""
        ledger = MetricsSpecLedgerParser()
        spec = ledger.parse()
        self.assertTrue(spec["rules_loaded"])
        self.assertEqual(len(spec["integrity"]["sha256"]), 64)
        self.assertTrue(spec["schema"]["valid"], spec["schema"]["missing_sections"])
        self.assertEqual(spec["stat_thresholds"]["alpha"], 0.05)
        self.assertEqual(spec["tam_variance_max"], 0.30)
        self.assertEqual(ledger.get_threshold("stat_thresholds.alpha"), 0.05)
        self.assertEqual(ledger.get_threshold("not.exist", default="fallback"), "fallback")

    def test_l04_drift_gate_and_rule_bundle_export(self):
        """L04：基线漂移门禁与下游规则包导出。"""
        with tempfile.TemporaryDirectory() as tmp:
            ledger = MetricsSpecLedgerParser(workspace_dir=tmp)
            first = ledger.detect_drift()
            self.assertTrue(first["baseline_created"])
            self.assertTrue(first["within_tolerance"])

            # 人为篡改基线 → 必须被门禁识别为口径漂移
            with open(ledger.baseline_path, "r", encoding="utf-8") as f:
                baseline = json.load(f)
            baseline["thresholds"]["stat_thresholds.alpha"] = 0.01
            with open(ledger.baseline_path, "w", encoding="utf-8") as f:
                json.dump(baseline, f, ensure_ascii=False)

            drift = ledger.detect_drift()
            self.assertFalse(drift["within_tolerance"])
            self.assertTrue(any(d["key"] == "stat_thresholds.alpha" for d in drift["drift"]))

            bundle_path = ledger.export_rule_bundle(os.path.join(tmp, "bundles"))
            self.assertTrue(os.path.exists(bundle_path))
            with open(bundle_path, "r", encoding="utf-8") as f:
                bundle = json.load(f)
            self.assertEqual(bundle["source_sha256"], ledger.parse()["integrity"]["sha256"])
            self.assertEqual(bundle["stat_thresholds"]["alpha"], 0.05)

    def test_l05_hallucination_and_attribution_gate(self):
        """L05：数字溯源幻觉审计与归因完整性门禁。"""
        guard = DataSlopGuard()
        trace = guard.trace_numbers("GMV 下滑 999%，客单价 12.5 元，同比 -2.1%", known_numbers=[12.5, -2.1])
        self.assertFalse(trace["hallucination_free"])
        self.assertIn(999.0, trace["unsourced_numbers"])
        self.assertEqual(trace["unsourced_numbers"], [999.0])

        good = guard.audit_attribution("抖音渠道贡献了 -1200 元，占总跌幅 65%，同比基准 -2.1pp")
        self.assertTrue(good["complete"])

        bad = guard.audit_attribution("转化率下降了")
        self.assertFalse(bad["complete"])
        self.assertIn("driver", bad["missing"])
        self.assertIn("comparison", bad["missing"])

        report = guard.audit_report(
            "渠道A贡献了-1200元，占总跌幅65%，同比基准-2.1pp",
            sections={"summary": "行业前景极其广阔"},
            known_numbers=[-1200, 65, -2.1],
        )
        self.assertTrue(report["attribution"]["complete"])
        self.assertIn("summary", report["section_reports"])
        self.assertLessEqual(report["score"], 100)

        tag = guard.inject_dri("结论正文", action="复核口径")
        self.assertIn("[DRI：", tag)
        self.assertEqual(guard.inject_dri(tag), tag)

    def test_l06_mcda_scores_and_confidence_band(self):
        """L06：MCDA 加权打分、置信带与推荐一致性。"""
        sc = ScenarioComparativeMatrix().generate_scenarios(200000.0, 0.20)
        self.assertEqual(sc["scenario_count"], 3)
        types = {s["type"] for s in sc["scenarios"]}
        self.assertEqual(types, {"conservative", "baseline", "aggressive"})
        for s in sc["scenarios"]:
            self.assertLess(s["forecast_low"], s["forecast_value"])
            self.assertLess(s["forecast_value"], s["forecast_high"])
            self.assertGreaterEqual(s["weighted_score"], 0.0)
            self.assertIn("roi", s["mcda_scores"])

        ranked = sorted(sc["scenarios"], key=lambda s: s["rank"])
        self.assertEqual(ranked[0]["weighted_score"], max(s["weighted_score"] for s in sc["scenarios"]))
        self.assertEqual(sc["recommended"], ranked[0]["label"])
        self.assertIn("基准稳健型", sc["comparison_matrix_md"])
        self.assertIn("ranking_stable", sc["sensitivity"])
        self.assertEqual(sc["sensitivity"]["base_winner"], ranked[0]["type"])
        self.assertEqual(sc["criteria_weights"]["roi"], 0.30)


class TestRound3BundlePatchMemoryResilience(unittest.TestCase):
    """第 3 轮 SOP · 工业交付 (L07~L10)。"""

    def test_l07_bundle_fingerprint_lineage_and_verify(self):
        """L07：Bundle 指纹/血缘、Vega 校验、SARIF 多规则与自校验。"""
        from engines import AnalysisAssetBundle
        with tempfile.TemporaryDirectory() as tmp:
            bundle_mgr = AnalysisAssetBundle(workspace_dir=tmp)
            report = {
                "engine": "analysis_engine_manager",
                "spec_sha256": "a" * 64,
                "query": "demo",
                "chart_data": [{"month": "2026-09", "gmv": 100}, {"month": "2026-10", "gmv": 130}],
                "issues": ["data quality blocker: 缺失 12%",
                           "anomaly: GMV 暴跌 35%",
                           "spec: 口径未对齐"],
            }
            paths = bundle_mgr.export_bundle("r07", report)
            for p in paths.values():
                self.assertTrue(os.path.exists(p))

            with open(paths["bundle_path"], "r", encoding="utf-8") as f:
                bundle = json.load(f)
            self.assertEqual(bundle["schema_version"], "2.0.0")
            self.assertEqual(bundle["lineage"]["producer"], "R06-Wadeqing-Analyst")
            self.assertEqual(len(bundle["artifacts"]), 2)
            for art in bundle["artifacts"]:
                self.assertEqual(len(art["sha256"]), 64)
                self.assertGreater(art["bytes"], 0)

            with open(paths["vega_spec_path"], "r", encoding="utf-8") as f:
                vega = json.load(f)
            self.assertTrue(vega["usermeta"]["validation"]["valid"])
            self.assertEqual(vega["encoding"]["x"]["type"], "temporal")
            self.assertEqual(vega["encoding"]["y"]["type"], "quantitative")

            with open(paths["sarif_path"], "r", encoding="utf-8") as f:
                sarif = json.load(f)
            run = sarif["runs"][0]
            self.assertEqual(len(run["tool"]["driver"]["rules"]), 4)
            self.assertTrue(run["invocations"][0]["executionSuccessful"])
            levels = [r["level"] for r in run["results"]]
            self.assertEqual(levels, ["error", "warning", "warning"])
            self.assertTrue(all("partialFingerprints" in r for r in run["results"]))

            verified = bundle_mgr.verify_bundle("r07")
            self.assertTrue(verified["ok"])
            with open(paths["vega_spec_path"], "a", encoding="utf-8") as f:
                f.write(" ")
            tampered = bundle_mgr.verify_bundle("r07")
            self.assertFalse(tampered["ok"])
            self.assertEqual(len(tampered["mismatches"]), 1)

    def test_l08_rfc6901_6902_full_operators(self):
        """L08：嵌套指针差量、全算子、test 断言与逆补丁回放。"""
        from engines import AnalysisDiffPatchEngine
        engine = AnalysisDiffPatchEngine()
        old = {"kpi": {"gmv": 100.0, "channels": ["抖音", "知乎"]},
               "a/b": {"~key": 1}}
        new = {"kpi": {"gmv": 130.0, "channels": ["抖音", "知乎", "小红书"]},
               "a/b": {"~key": 2}}
        patches = engine.create_patch(old, new)
        self.assertTrue(any(p["path"] == "/a~1b/~0key" for p in patches))
        self.assertTrue(any(p["path"] == "/kpi/channels/-" for p in patches))
        proof = engine.apply_and_verify(old, patches)
        self.assertEqual(proof["new_state"], new)
        self.assertTrue(proof["roundtrip_exact"])

        moved = engine.apply_patch({"a": 1, "b": []}, [
            {"op": "copy", "from": "/a", "path": "/b/-"},
            {"op": "move", "from": "/a", "path": "/b/0"},
        ])
        self.assertEqual(moved, {"b": [1, 1]})

        with self.assertRaises(Exception):
            engine.apply_patch({"a": 1}, [{"op": "test", "path": "/a", "value": 2}])

        with self.assertRaises(Exception):
            engine.apply_patch({"a": 1}, [{"op": "remove", "path": "/missing"}])

    def test_l09_file_lock_redo_and_scheme_memory(self):
        """L09：TTL 文件锁、方案槽位消歧、回滚与 redo。"""
        from engines import AnalysisSessionMemoryPool
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "session.json")
            pool = AnalysisSessionMemoryPool(state_file=path)
            summary = pool.update_slot("metric", "revenue", confidence=0.72)
            self.assertEqual(summary["slots"]["metric"], "revenue")
            self.assertAlmostEqual(summary["slot_confidences"]["metric"], 0.72, places=3)

            pool.set_scheme(2, {"metric": "gmv", "channel": "抖音"})
            self.assertIn("scheme_2", pool.get_slot_summary()["schemes"])
            resolved = pool.resolve_pronouns("按第二套方案看刚才的指标")
            self.assertEqual(resolved["resolved_scheme"]["metric"], "gmv")

            pool.record_turn("第一轮", {"metric": "gmv", "dimension": "channel"})
            pool.record_turn("第二轮", {"metric": "profit"})
            self.assertTrue(pool.rollback_turns(1))
            self.assertEqual(pool.get_slot_summary()["slots"]["metric"], "gmv")
            self.assertTrue(pool.redo())
            self.assertEqual(pool.get_slot_summary()["slots"]["metric"], "profit")

            compacted = pool.compact(ttl_days=0)
            self.assertIn("pruned", compacted)
            self.assertFalse(os.path.exists(pool.lock_path), "文件锁必须释放")

    def test_l10_window_breaker_process_isolation_and_trace(self):
        """L10：滑窗失败率熔断、子进程硬隔离、traceparent 与分位聚合。"""
        import sys
        from engines import AnalysisWatchdogBreaker, AnalysisTelemetryTracer
        breaker = AnalysisWatchdogBreaker(failure_threshold=99, window_size=6,
                                          failure_ratio_threshold=0.5,
                                          min_calls_in_window=4)
        for _ in range(4):
            with self.assertRaises(ValueError):
                breaker.execute_with_guard(lambda: (_ for _ in ()).throw(ValueError("boom")))
        self.assertEqual(breaker.state, "OPEN")
        stats = breaker.window_stats()
        self.assertEqual(stats["observed"], 4)
        self.assertEqual(stats["failure_ratio"], 1.0)

        iso = breaker.run_isolated(
            [sys.executable, "-c", "import time; time.sleep(2)"], timeout_sec=0.3)
        self.assertEqual(iso["status"], "TIMEOUT")
        self.assertTrue(iso["isolated"])

        with tempfile.TemporaryDirectory() as tmp:
            tracer = AnalysisTelemetryTracer(log_path=os.path.join(tmp, "t.jsonl"))
            header = tracer.new_traceparent()
            parsed = tracer.parse_traceparent(header)
            self.assertEqual(len(parsed["trace_id"]), 32)
            rec = tracer.record_span("op", 12.0, "SUCCESS", {"k": 1}, traceparent=header)
            self.assertTrue(rec["traceparent"].startswith("00-"))
            self.assertTrue(rec["sampled"])
            agg = tracer.aggregate_metrics()
            self.assertEqual(agg["span_count"], 1)
            self.assertIn("p95_ms", agg)
            with self.assertRaises(ValueError):
                tracer.parse_traceparent("bad-header")


if __name__ == "__main__":
    unittest.main()

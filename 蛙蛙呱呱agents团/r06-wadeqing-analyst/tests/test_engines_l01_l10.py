# -*- coding: utf-8 -*-
"""R06 蛙得清 · 数据分析师十轮演进集成测试套件 (L01~L10)。
严格遵循 SOP_AGENT_EVOLUTION_UNIVERSAL.md 规范与双轨零回归测试法则：
覆盖 L01 工具实体层 至 L10 工业容灾层全部架构能力。
"""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
for p in (_HERE, _PARENT):
    if p not in sys.path:
        sys.path.insert(0, p)

from engines import (
    AnalysisEngineManager,
    NativeAnalysisEngine,
    AnalysisIntentDecompiler,
    AnalysisReflexiveHealer,
    MetricsSpecLedgerParser,
    DataSlopGuard,
    ScenarioComparativeMatrix,
    AnalysisAssetBundle,
    AnalysisDiffPatchEngine,
    AnalysisSessionMemoryPool,
    AnalysisWatchdogBreaker,
    AnalysisTelemetryTracer,
)


class TestR06EvolutionSuite(unittest.TestCase):

    def test_l01_native_engine_and_manager(self):
        """L01 工具实体层：真实确定性分析引擎运算与健康探测。"""
        mgr = AnalysisEngineManager()
        probe = mgr.probe_all()
        self.assertTrue(probe["all_healthy"])
        self.assertGreaterEqual(probe["engine_count"], 1)

        eng = mgr.get_engine("native")
        self.assertIsNotNone(eng)

        # 1. 真实聚合度量
        res_agg = eng.execute("aggregate_metrics", {"values": [10.0, 20.0, 30.0, 40.0]})
        self.assertTrue(res_agg.ok)
        self.assertEqual(res_agg.data["count"], 4)
        self.assertEqual(res_agg.data["sum"], 100.0)
        self.assertEqual(res_agg.data["mean"], 25.0)

        # 2. 真实 HHI 集中度计算
        res_hhi = eng.execute("hhi_concentration", {"shares": [40.0, 30.0, 20.0, 10.0]})
        self.assertTrue(res_hhi.ok)
        self.assertEqual(res_hhi.data["grade"], "highly_concentrated")

        # 3. 真实归因分解
        res_attr = eng.execute("attribution_decomposition", {
            "uv_baseline": 1000, "uv_current": 1200,
            "cvr_baseline": 0.05, "cvr_current": 0.04,
            "atv_baseline": 50, "atv_current": 60,
        })
        self.assertTrue(res_attr.ok)
        self.assertTrue(res_attr.data["attribution_verified"])

    def test_l02_intent_decompiler(self):
        """L02 意图解构层：自然语言模糊诉求解构与 DAG Kahn 拓扑编排。"""
        decompiler = AnalysisIntentDecompiler()
        query = "看一下上周抖音渠道的GMV转化率为什么下降了，做个异常质检和归因分析报告"
        compiled = decompiler.compile_intent(query)
        self.assertIn("quality", compiled["matched_domains"])
        self.assertIn("rootcause", compiled["matched_domains"])
        self.assertGreaterEqual(compiled["step_count"], 2)
        self.assertTrue(compiled["is_complex_dag"])
        # 验证实体抽取
        self.assertIn("gmv", compiled["extracted_entities"]["metrics"])
        self.assertEqual(compiled["extracted_entities"]["time_window"], "上周")

    def test_l03_reflexive_healer(self):
        """L03 自愈反思层：异常识别、防越权拍板拦截与反思修复。"""
        healer = AnalysisReflexiveHealer()
        # 构造越权拍板、份额未归一的故障产物
        dirty_payload = {
            "conclusion": "数据表现优异，必须立即拍板决定全量上线！",
            "shares": [30.0, 20.0],  # 缺少归一化
            "p_value": 0.03,         # 缺少置信区间
        }
        ok, issues = healer.audit_findings(dirty_payload)
        self.assertFalse(ok)
        self.assertGreaterEqual(len(issues), 2)

        # 执行自愈反思
        healed = healer.heal_payload(dirty_payload, issues)
        self.assertTrue(healed["_reflexive_healed"])
        self.assertNotIn("必须立即", healed["conclusion"])
        self.assertIn("confidence_interval", healed)
        self.assertEqual(sum(healed["shares"]), 100.0)

    def test_l04_metrics_spec_ledger(self):
        """L04 领域账本层：METRICS_SPEC.md 动态基准解析。"""
        parser = MetricsSpecLedgerParser()
        spec = parser.parse()
        self.assertTrue(spec["rules_loaded"])
        self.assertEqual(spec["stat_thresholds"]["alpha"], 0.05)
        self.assertEqual(spec["stat_thresholds"]["power_min"], 0.80)
        self.assertEqual(spec["tam_variance_max"], 0.30)
        self.assertEqual(spec["reconciliation_tolerance"], 0.01)
        self.assertIn("GMV", spec["metric_definitions"])

    def test_l05_data_slop_guard(self):
        """L05 质感去劣化：假大空废话套话审计与物理量化精修。"""
        guard = DataSlopGuard()
        bad_text = "行业前景极其广阔，转化率大幅爆发，毫无疑问应当加大投入！"
        audit = guard.audit_text(bad_text)
        self.assertFalse(audit["is_clean"])
        self.assertLess(audit["score"], 80)

        polished, count = guard.polish(bad_text)
        self.assertGreaterEqual(count, 3)
        self.assertNotIn("前景极其广阔", polished)
        self.assertIn("置信度", polished)

    def test_l06_scenario_matrix(self):
        """L06 横向决策层：三维情景推演看板裂变。"""
        matrix = ScenarioComparativeMatrix()
        result = matrix.generate_scenarios(base_metric=10000.0, growth_rate=0.20)
        self.assertEqual(result["scenario_count"], 3)
        types = [s["type"] for s in result["scenarios"]]
        self.assertListEqual(types, ["conservative", "baseline", "aggressive"])
        self.assertIn("基准稳健型", result["comparison_matrix_md"])
        self.assertGreater(result["scenarios"][2]["forecast_value"], result["scenarios"][0]["forecast_value"])

    def test_l07_asset_bundle(self):
        """L07 伴生消费层：标准化机器消费工件（Bundle/Vega/SARIF）导出。"""
        bundle_exporter = AnalysisAssetBundle()
        report_mock = {
            "title": "渠道增长分析",
            "chart_data": [{"x": "W1", "y": 10}, {"x": "W2", "y": 25}],
            "issues": ["Warning: Conversion dropped in weekend"],
        }
        res = bundle_exporter.export_bundle(run_id="test_run_01", report_data=report_mock)
        self.assertTrue(os.path.exists(res["bundle_path"]))
        self.assertTrue(os.path.exists(res["vega_spec_path"]))
        self.assertTrue(os.path.exists(res["sarif_path"]))

    def test_l08_diff_patch_engine(self):
        """L08 局部差量层：RFC 6902 JSON Patch 与局部切片重算。"""
        patch_engine = AnalysisDiffPatchEngine()
        old_state = {"cvr": 0.05, "status": "active", "tag": "test"}
        new_state = {"cvr": 0.08, "status": "active", "tag": "prod", "new_key": 1}

        patches = patch_engine.create_patch(old_state, new_state)
        self.assertEqual(len(patches), 3)

        applied = patch_engine.apply_patch(old_state, patches)
        self.assertEqual(applied["cvr"], 0.08)
        self.assertEqual(applied["new_key"], 1)

        # 局部切片差量重算
        dataset = [
            {"channel": "抖音", "amount": 100},
            {"channel": "微信", "amount": 200},
            {"channel": "抖音", "amount": 300},
        ]
        slice_res = patch_engine.recalculate_slice(dataset, filter_col="channel", filter_val="抖音", metric_col="amount")
        self.assertEqual(slice_res["count"], 2)
        self.assertEqual(slice_res["sum"], 400.0)
        self.assertEqual(slice_res["mean"], 200.0)

    def test_l09_session_memory_pool(self):
        """L09 会话记忆层：上下文持久化、细粒度槽位记忆、多跳代词消歧与快照树回滚。"""
        import tempfile
        import time
        tmp_state = os.path.join(tempfile.gettempdir(), f"test_session_state_{int(time.time()*1000)}.json")
        try:
            memory = AnalysisSessionMemoryPool(state_file=tmp_state)
            snap1 = memory.record_turn("查看抖音渠道GMV", {"metric": "gmv", "dimension": "channel", "time_window": "2024-Q1", "filters": {"tag": "active"}})
            
            # 模糊代词消歧
            disambig = memory.resolve_pronouns("把刚才的指标换成上个月")
            self.assertTrue(disambig["had_ambiguity"])
            self.assertEqual(disambig["resolved_metric"], "gmv")
            self.assertEqual(disambig["resolved_time_window"], "2024-last-month")
            self.assertIn("metric", disambig["disambiguation_details"]["inherited_slots"])

            # 槽位重载消歧：换成按省份看刚才的指标
            disambig_dim = memory.resolve_pronouns("换成按省份看刚才的成交额")
            self.assertTrue(disambig_dim["had_ambiguity"])
            self.assertIn("province", disambig_dim["resolved_dimension"])

            # 记录新一轮
            snap2 = memory.record_turn("查看微信渠道收入", {"metric": "revenue", "dimension": "wechat", "time_window": "2024-Q2"})
            self.assertEqual(memory.current_state["last_active_metric"], "revenue")
            self.assertEqual(memory.current_state["slots"]["metric"], "revenue")

            # 快照树及列表概览
            snaps = memory.list_snapshots()
            self.assertTrue(len(snaps) >= 2)
            summary = memory.get_slot_summary()
            self.assertEqual(summary["slots"]["metric"], "revenue")

            # 快照版本回滚
            ok = memory.rollback_to("snap_v1")
            self.assertTrue(ok)
            self.assertEqual(memory.current_state["last_active_metric"], "gmv")
            self.assertEqual(memory.current_state["slots"]["metric"], "gmv")

            # 步数撤销 (rollback_turns)
            memory.record_turn("第三轮测试", {"metric": "profit", "dimension": "category"})
            self.assertEqual(memory.current_state["last_active_metric"], "profit")
            undo_ok = memory.rollback_turns(1)
            self.assertTrue(undo_ok)
            self.assertEqual(memory.current_state["last_active_metric"], "gmv")
        finally:
            if os.path.exists(tmp_state):
                try:
                    os.remove(tmp_state)
                except Exception:
                    pass

    def test_l10_watchdog_and_telemetry(self):
        """L10 工业容灾层：看门狗熔断、指数退避与全链路遥测追踪。"""
        breaker = AnalysisWatchdogBreaker(failure_threshold=2, reset_timeout_sec=0.2, half_open_success_threshold=1)

        def failing_func():
            raise ValueError("Upstream DB Timeout")

        with self.assertRaises(ValueError):
            breaker.execute_with_guard(failing_func)
        with self.assertRaises(ValueError):
            breaker.execute_with_guard(failing_func)

        # 达到阈值触发熔断
        with self.assertRaises(RuntimeError) as ctx:
            breaker.execute_with_guard(failing_func)
        self.assertIn("CircuitBreaker is OPEN", str(ctx.exception))
        self.assertEqual(breaker.get_state(), "OPEN")
        self.assertGreaterEqual(breaker.metrics["rejected_calls"], 1)

        # 测试超时硬熔断看门狗
        import time
        def slow_func():
            time.sleep(0.3)
            return "done"

        breaker.reset()
        from engines import TimeoutException
        with self.assertRaises(TimeoutException):
            breaker.execute_with_guard(slow_func, timeout_sec=0.05)

        # 测试指数退避与抖动重试
        retry_calls = 0
        def flappy_func():
            nonlocal retry_calls
            retry_calls += 1
            if retry_calls < 3:
                raise ConnectionResetError("network glitch")
            return "success_recovered"

        res = breaker.retry_with_backoff(flappy_func, max_retries=4, base_delay=0.01)
        self.assertEqual(res, "success_recovered")
        self.assertEqual(retry_calls, 3)

        # 遥测追踪落盘验证与离群告警、Span 上下文
        tracer = AnalysisTelemetryTracer(latency_alert_threshold_ms=50.0)
        rec = tracer.record_span("query_aggregate", 15.6, "SUCCESS", {"rows": 1000})
        self.assertIn("trace_id", rec)
        self.assertIsNone(rec["latency_alert"])
        self.assertTrue(os.path.exists(tracer.log_path))

        # 离群耗时告警验证
        outlier_rec = tracer.record_span("heavy_olap_cube", 150.2, "SUCCESS", {"rows": 500000})
        self.assertEqual(outlier_rec["latency_alert"], "LATENCY_OUTLIER")

        # start_span 上下文管理器验证
        with tracer.start_span("context_metric_eval", {"metric": "gmv"}) as ctx_span:
            self.assertIn("trace_id", ctx_span)
            time.sleep(0.01)

        recent = tracer.get_recent_spans(limit=3)
        self.assertTrue(len(recent) >= 3)
        self.assertEqual(recent[-1]["action"], "context_metric_eval")


if __name__ == "__main__":
    unittest.main()

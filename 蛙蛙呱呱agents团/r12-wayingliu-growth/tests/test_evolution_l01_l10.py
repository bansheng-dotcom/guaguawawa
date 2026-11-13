# -*- coding: utf-8 -*-
"""tests/test_evolution_l01_l10.py - R12 蛙引流 · 增长运营官 十维演进双轨集成测试套件。"""
from __future__ import annotations

import json
import os
from core.workspace import role_workspace  # noqa: E402

import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(AGENTS)
for p in (HERE, AGENTS, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from engines import (
    GrowthRuntimeEngine,
    IntentCompiler,
    ReflexiveHealer,
    SpecLedger,
    SlopGuard,
    ScenarioMatrix,
    GrowthAssetBundle,
    GrowthDiffPatchEngine,
    GrowthSessionMemory,
    GrowthTelemetryWatchdog,
)


class TestEvolutionRound1(unittest.TestCase):
    """第 1 轮升级 (L01~L03 基石阶段) 集成测试。"""

    def test_l01_runtime_probe_and_metrics(self):
        engine = GrowthRuntimeEngine()
        probe = engine.probe_health()
        self.assertEqual(probe["status"], "healthy")
        self.assertTrue(probe["metric_recalculator_healthy"])
        self.assertTrue(probe["ab_tester_healthy"])
        self.assertTrue(probe["funnel_analyzer_healthy"])
        self.assertTrue(probe["k_factor_engine_healthy"])

        # 复算单位经济学
        ue = engine.calculate_unit_economics(arpa=100.0, gross_margin=0.8, churn_rate=0.05, spend=5000.0, new_customers=50)
        self.assertAlmostEqual(ue["ltv"], 1600.0)
        self.assertAlmostEqual(ue["cac"], 100.0)
        self.assertAlmostEqual(ue["ltv_cac"], 16.0)
        self.assertTrue(ue["is_healthy"])

        # 病毒 K 因子
        kf = engine.calculate_k_factor(invites_per_customer=5.0, conversion_rate=0.25)
        self.assertAlmostEqual(kf["k_factor"], 1.25)
        self.assertTrue(kf["is_viral"])

    def test_l02_intent_decompilation(self):
        compiler = IntentCompiler()
        query = "设计一套冷启动获客方案，并通过 A/B 实验分析漏斗瓶颈"
        stages = compiler.compile_intent(query)
        self.assertIsInstance(stages, list)
        self.assertGreaterEqual(len(stages), 4)
        self.assertIn("A/B Test", stages)

    def test_l03_reflexive_healing_and_redlines(self):
        healer = ReflexiveHealer()
        # 违规红线拦截测试
        with self.assertRaises(ValueError):
            healer.check_redlines("cash subsidy with 100% bonus")

        # 合规行为放行
        ok = healer.check_redlines("optimized organic loop")
        self.assertTrue(ok)


class TestEvolutionRound2(unittest.TestCase):
    """第 2 轮升级 (L04~L06 深度阶段) 集成测试。"""

    def test_l04_spec_ledger(self):
        ledger = SpecLedger()
        spec = ledger.load_spec()
        self.assertTrue(spec.get("spec_loaded"))
        self.assertEqual(spec.get("north_star"), "WAU")
        self.assertIn("confidence_threshold", spec)
        self.assertEqual(spec.get("confidence_threshold"), 0.95)

    def test_l05_slop_guard(self):
        guard = SlopGuard()
        bad_text = "我们通过微信裂变让新用户获得了显著提升"
        cleaned = guard.clean(bad_text)
        self.assertNotIn("显著提升", cleaned)
        self.assertIn("p<0.05", cleaned)

    def test_l06_scenario_matrix(self):
        matrix = ScenarioMatrix()
        scenarios = matrix.generate()
        self.assertIsInstance(scenarios, list)
        self.assertGreaterEqual(len(scenarios), 3)


class TestEvolutionRound3(unittest.TestCase):
    """第 3 轮升级 (L07~L10 交付阶段) 集成测试。"""

    def test_l07_asset_bundle(self):
        tmp_dir = os.path.join(role_workspace(HERE), "tmp", "test_bundles")
        bundle_exporter = GrowthAssetBundle(workspace_dir=tmp_dir)
        growth_mock = {
            "title": "测试增长实验资产",
            "north_star": "WAU",
            "issues": ["建议扩大样本量"],
            "funnel": [
                {"stage": "曝光", "count": 1000},
                {"stage": "转化", "count": 100}
            ]
        }
        res = bundle_exporter.export_bundle("run_unit_test", growth_mock)
        self.assertTrue(os.path.exists(res["bundle_path"]))
        self.assertTrue(os.path.exists(res["sarif_path"]))
        self.assertTrue(os.path.exists(res["vega_charts_path"]))

        # 验证 SARIF 规范 v2.1.0
        with open(res["sarif_path"], "r", encoding="utf-8") as f:
            sarif = json.load(f)
            self.assertEqual(sarif["version"], "2.1.0")
            self.assertIn("runs", sarif)

        # 验证 Vega-Lite 图表元数据
        with open(res["vega_charts_path"], "r", encoding="utf-8") as f:
            vega = json.load(f)
            self.assertIn("$schema", vega)
            self.assertIn("vega-lite", vega["$schema"])
            self.assertEqual(vega["mark"], "bar")

    def test_l08_diff_patch_engine(self):
        engine = GrowthDiffPatchEngine()
        old_state = {"north_star": "WAU", "budget": 10000.0, "cac": 50.0}
        new_state = {"north_star": "WAU", "budget": 20000.0, "cac": 45.0, "new_metric": "LTV"}

        # 验证 RFC 6902 补丁生成
        patches = engine.create_patch(old_state, new_state)
        self.assertEqual(len(patches), 3)

        # 验证应用无损置换
        applied = engine.apply_patch(old_state, patches)
        self.assertEqual(applied["budget"], 20000.0)
        self.assertEqual(applied["cac"], 45.0)
        self.assertEqual(applied["new_metric"], "LTV")

        # 条目级差量热修
        patched_item = engine.patch_strategy_item(old_state, "budget", 15000.0)
        self.assertEqual(patched_item["budget"], 15000.0)
        self.assertEqual(patched_item["cac"], 50.0)

        # 差量弹性重算
        recalc = engine.recalculate_differential(base_budget=10000, target_cac=50, updated_budget=20000, updated_cac=40)
        self.assertEqual(recalc["base_acquisitions"], 200)
        self.assertEqual(recalc["new_acquisitions"], 500)
        self.assertEqual(recalc["delta_acquisitions"], 300)

    def test_l09_session_memory(self):
        tmp_file = os.path.join(role_workspace(HERE), "tmp", "test_session_state.json")
        mem = GrowthSessionMemory(state_file=tmp_file)
        snap1 = mem.record_turn("设计一套小红书获客方案", {"target_channel": "小红书", "budget": 30000.0})
        self.assertEqual(mem.current_state["slots"]["target_channel"], "小红书")

        # 代词消歧
        resolved = mem.resolve_pronouns("按刚才第二套稳健方案执行")
        self.assertTrue(resolved["had_ambiguity"])
        self.assertEqual(resolved["resolved_slots"]["scenario"], "steady_lean")
        self.assertEqual(resolved["resolved_slots"]["target_channel"], "小红书")

        # 快照记录与一键回滚
        snap2 = mem.record_turn("切换到微信公众号全量投放", {"target_channel": "微信公众号"})
        self.assertEqual(mem.current_state["slots"]["target_channel"], "微信公众号")
        self.assertTrue(mem.rollback(snap1))
        self.assertEqual(mem.current_state["slots"]["target_channel"], "小红书")

    def test_l10_telemetry_watchdog(self):
        tmp_telemetry = os.path.join(role_workspace(HERE), "tmp", "test_telemetry.jsonl")
        wd = GrowthTelemetryWatchdog(failure_threshold=2, reset_timeout_sec=0.5, telemetry_file=tmp_telemetry)
        self.assertEqual(wd.get_state(), "CLOSED")

        def normal_growth_task():
            return "GROWTH_OK"

        res = wd.execute_with_guard(normal_growth_task)
        self.assertEqual(res, "GROWTH_OK")
        self.assertTrue(os.path.exists(tmp_telemetry))

        # 触发熔断器变为 OPEN
        def broken_task():
            raise ConnectionResetError("API 调用超时")

        for _ in range(2):
            try:
                wd.execute_with_guard(broken_task)
            except ConnectionResetError:
                pass

        self.assertEqual(wd.get_state(), "OPEN")
        # 熔断开启下快速失败
        with self.assertRaises(RuntimeError):
            wd.execute_with_guard(normal_growth_task)


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""R05 蛙深远（战略研究官）十轮渐进式架构演进测试套件 (L01~L10)。"""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from engines import (
    ResearchEngineManager,
    NativeResearchEngine,
    ResearchPrompter,
    ResearchCritic,
    ResearchLedgerParser,
    ResearchSlopGuard,
    ScenarioMatrixExplorer,
    ResearchAssetBundle,
    ResearchPatchEditor,
    SessionMemoryPool,
    WatchdogCircuitBreaker,
    ProductionTelemetry
)


class TestR05EvolutionSuite(unittest.TestCase):

    def test_l01_native_engine_and_manager(self):
        """L01 工具实体层：真实确定性计算与健康巡检。"""
        mgr = ResearchEngineManager()
        probe_all = mgr.probe_all()
        self.assertTrue(probe_all["all_healthy"])
        self.assertGreaterEqual(probe_all["engine_count"], 1)

        engine = mgr.get_engine("native")
        self.assertIsNotNone(engine)
        # 测试 HHI 计算
        res_hhi = engine.execute("calc_hhi", {"shares": [30, 25, 20, 15, 10]})
        self.assertTrue(res_hhi.ok)
        self.assertEqual(res_hhi.data["hhi"], 900 + 625 + 400 + 225 + 100)
        self.assertEqual(res_hhi.data["structure"], "moderate")

        # 测试 TAM 方差计算
        res_var = engine.execute("verify_tam_variance", {"top_down": 100.0, "bottom_up": 110.0})
        self.assertTrue(res_var.ok)
        self.assertAlmostEqual(res_var.data["variance"], 0.1, places=2)
        self.assertTrue(res_var.data["converged"])

    def test_l02_intent_prompter(self):
        """L02 意图解构层：自然语言模糊诉求编译为 DAG。"""
        prompter = ResearchPrompter()
        res = prompter.compile_intent("我想调研下海外协同SaaS的市场规模TAM和竞争对手战斗卡，预算大约500万")
        self.assertEqual(res["primary_domain"], "sizing")
        self.assertIn("competitor", res["matched_domains"])
        self.assertGreaterEqual(res["step_count"], 2)
        self.assertTrue(any(s["action"] == "size" for s in res["dag_steps"]))
        self.assertTrue(any(s["action"] == "battlecard" for s in res["dag_steps"]))

    def test_l03_critic_and_auto_heal(self):
        """L03 自愈反思层：审校诊断与自愈修复。"""
        critic = ResearchCritic()
        # 脏数据：份额不归一、出现拍板越权词、无源断言
        dirty = {
            "shares": [30, 30],
            "conclusion": "我们必须进入这个赛道，绝对可行！",
            "claims": [{"id": "c1", "text": "行业增速40%"}]
        }
        ok, issues = critic.audit_findings(dirty)
        self.assertFalse(ok)
        self.assertGreaterEqual(len(issues), 2)

        # 自愈修复
        healed = critic.heal_payload(dirty, issues)
        self.assertAlmostEqual(sum(healed["shares"]), 100.0, places=1)
        self.assertNotIn("必须进入", healed["conclusion"])
        self.assertIn("default_ref:待核实", healed["claims"][0]["evidence_refs"])
        self.assertGreater(len(healed["_critic_reflections"]), 0)

    def test_l04_spec_ledger(self):
        """L04 领域账本层：RESEARCH_SPEC.md 动态账本解析。"""
        parser = ResearchLedgerParser()
        spec = parser.parse()
        self.assertTrue(spec["rules_loaded"])
        self.assertEqual(spec["tam_variance_max"], 0.30)
        self.assertEqual(spec["hhi_thresholds"]["moderate_max"], 2500)
        self.assertIn("tier_1", spec["evidence_tiers"])

    def test_l05_slop_guard(self):
        """L05 质感去劣化：假大空词汇审计与物理精修。"""
        guard = ResearchSlopGuard()
        bad_text = "行业前景极其广阔，业内公认这是颠覆式创新，我们将大力推进！"
        audit = guard.audit_text(bad_text)
        self.assertFalse(audit["is_clean"])
        self.assertLess(audit["score"], 80)

        polished, count = guard.polish(bad_text)
        self.assertGreaterEqual(count, 3)
        self.assertNotIn("前景极其广阔", polished)
        self.assertNotIn("业内公认", polished)
        self.assertNotIn("颠覆式创新", polished)

    def test_l06_scenario_matrix_explorer(self):
        """L06 横向决策层：三维情景规划与横向比选看板。"""
        explorer = ScenarioMatrixExplorer()
        matrix = explorer.generate_matrix({"tam": 100.0, "cogs": 300, "price": 1200})
        self.assertEqual(len(matrix["scenarios"]), 3)
        self.assertEqual(matrix["scenarios"][0]["name"], "保守防御型 (Downside)")
        self.assertEqual(matrix["scenarios"][1]["name"], "基准稳健型 (Base)")
        self.assertEqual(matrix["scenarios"][2]["name"], "乐观突击型 (Upside)")
        self.assertIn("三维情景横向比选看板", matrix["board_markdown"])

    def test_l07_asset_bundle(self):
        """L07 伴生消费层：下游机器消费规格与图表导出。"""
        bundle_exporter = ResearchAssetBundle()
        out_dir = os.path.join(_HERE, "workspace", "test_bundle")
        bundle = bundle_exporter.export_bundle({
            "tam": 120.0,
            "hhi": 2250,
            "cr4": 90,
            "structure": "moderate",
            "claims": [{"id": "c1", "sources": ["S1"]}]
        }, out_dir)

        self.assertTrue(os.path.exists(bundle["research_spec"]))
        self.assertTrue(os.path.exists(bundle["chart_spec"]))

    def test_l08_patch_editor(self):
        """L08 局部差量层：RFC 6902 差量微调与自然语言指令调优。"""
        editor = ResearchPatchEditor()
        base = {
            "model": "subscription",
            "pricing": {"unit_price": 1200.0, "cogs": 300.0},
            "sizing": {"tam": 120.0, "obtainable_share": 0.05}
        }
        # 1. 结构化 patch
        patched, logs = editor.apply_patch(base, [
            {"op": "replace", "path": "/pricing/unit_price", "value": 1500.0}
        ])
        self.assertEqual(patched["pricing"]["unit_price"], 1500.0)
        self.assertEqual(patched["pricing"]["cogs"], 300.0)

        # 2. 自然语言指令 patch
        patched2, logs2 = editor.patch_by_instruction(base, "把客单价改成 1800，同时把份额改成 0.08")
        self.assertEqual(patched2["pricing"]["unit_price"], 1800.0)
        self.assertEqual(patched2["sizing"]["obtainable_share"], 0.08)

    def test_l09_session_memory(self):
        """L09 会话记忆层：状态持久化、代词消歧与回滚。"""
        state_path = os.path.join(_HERE, "session_state.json")
        mem = SessionMemoryPool(state_path)
        mem.record_turn("调研下海外SaaS市场", {"tam": 120.0}, topic="海外SaaS市场")

        resolved = mem.resolve_reference("把刚才那个市场的TAM重新算下")
        self.assertEqual(resolved, "海外SaaS市场")

        ok = mem.rollback(1)
        self.assertTrue(ok)

    def test_l10_telemetry_and_watchdog(self):
        """L10 工业容灾层：看门狗熔断与全链路遥测。"""
        watchdog = WatchdogCircuitBreaker(timeout_sec=2.0, max_retries=2)

        def fast_calc(x):
            return x * 2

        val = watchdog.execute_with_guard(fast_calc, 21)
        self.assertEqual(val, 42)

        telemetry_file = os.path.join(_HERE, "telemetry.jsonl")
        telemetry = ProductionTelemetry(telemetry_file)
        span = telemetry.record_span("research:sizing", {"tam": 120.0}, latency_ms=12.5)
        self.assertEqual(span["status"], "SUCCESS")
        self.assertTrue(os.path.exists(telemetry_file))


if __name__ == "__main__":
    unittest.main()

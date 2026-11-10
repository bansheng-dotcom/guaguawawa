# -*- coding: utf-8 -*-
"""R03 蛙守线 CFO 智能体十轮演进集成验收套件。

执行 10 维演进元模型的端到端测试与物理工件落地查验：
L01: 工具实体层 - 财务算子与合规探针存活
L02: 意图解构层 - 金额、周期与红线实体自然语言解构
L03: 自愈反思层 - 勾稽破损与持牌红线缺陷反思自愈
L04: 领域账本层 - FINANCIAL_SPEC.md 账本读取与全局硬红线
L05: 质感去劣化 - 财务合规假大空伪影审查与物理精修
L06: 横向决策层 - 三维财务情景裂变与横向比选看板
L07: 伴生消费层 - 伴生导出 AST 与 Vega 图表规格
L08: 局部差量层 - 单科目局部差量修改且保证其余不变
L09: 会话记忆层 - 工作记忆持久化快照与版本回滚
L10: 工业容灾层 - 看门狗硬熔断与 telemetry.jsonl 遥测追踪
"""
from __future__ import annotations
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from engines.manager import FinancialEngineManager
from engines.prompter import FinancialPrompter
from engines.critic import FinancialCritic, FinancialAutoHealLoop
from engines.ledger import FinancialLedgerParser
from engines.slop_guard import FinancialSlopGuard
from engines.explorer import MultiScenarioExplorer
from engines.asset_bundle import FinancialAssetBundle
from engines.patch_editor import FinancialPatchEditor
from engines.memory import FinancialSessionMemoryPool
from engines.telemetry import WatchdogCircuitBreaker, ProductionTelemetry

class TestEvolutionSuite(unittest.TestCase):

    def test_l01_tool_entity(self):
        manager = FinancialEngineManager()
        probes = manager.probe_all()
        self.assertEqual(probes["status"], "ok")
        self.assertTrue(probes["engines"]["native"]["available"])
        self.assertTrue(probes["engines"]["compliance"]["available"])

    def test_l02_intent_deconstruction(self):
        prompt = "当前账户余额 $2,000,000，每月净烧钱 $150,000，核查 AML 申报与跑道预警"
        decomposed = FinancialPrompter.decompose_intent(prompt)
        self.assertEqual(decomposed["detected_skill"], "cfo")
        self.assertEqual(decomposed["detected_action"], "runway")
        self.assertIn("AML", decomposed["detected_entities"])
        self.assertIn(2000000.0, decomposed["extracted_amounts"])

    def test_l03_critic_auto_heal(self):
        def bad_runner(patch):
            if patch.get("strip_guarantee_words"):
                return {"ok": True, "skill": "financial", "action": "recon", "findings": "由财务核算确认，核对无误", "checks": [{"ok": True}]}
            return {"ok": False, "skill": "financial", "action": "recon", "findings": "稳赚不赔，逐步优化"}

        res = FinancialAutoHealLoop.run_with_heal(bad_runner)
        self.assertEqual(res["verdict"], "PASS")
        self.assertEqual(res["heal_attempts"], 2)

    def test_l04_ledger_rules(self):
        spec = FinancialLedgerParser.load_spec(force_reload=True)
        self.assertEqual(spec["BALANCE_DIFF_TOLERANCE"], 0.0)
        self.assertGreater(spec["RUNWAY_ALERT_MONTHS"], 0.0)
        self.assertEqual(spec["FINANCIAL_RECORD_RETENTION_YEARS"], 7)

    def test_l05_slop_guard(self):
        raw = "对于本轮现金流，我们要高度重视，逐步落实，加强沟通。"
        score, detected = FinancialSlopGuard.audit_text(raw)
        self.assertLess(score, 6.0)
        polished = FinancialSlopGuard.polish(raw, default_dri="CFO_Desk")
        self.assertNotIn("高度重视", polished)
        self.assertIn("CFO_Desk", polished)

    def test_l06_multi_scenario_explorer(self):
        res = MultiScenarioExplorer.explore_scenarios(base_runway_months=10.0, base_burn_rate=120000.0, cash_balance=1200000.0)
        self.assertEqual(len(res["scenarios"]), 3)
        self.assertIn("conservative", res["scenarios"])
        self.assertIn("baseline", res["scenarios"])
        self.assertIn("aggressive", res["scenarios"])
        self.assertIn("| 策略情景 |", res["comparison_board_md"])

    def test_l07_asset_bundle(self):
        out_dir = os.path.join(HERE, "workspace", "test_bundle")
        files = FinancialAssetBundle.bundle(out_dir, "test_cfo_spec", {"kpi": "arr", "chart_data": [{"label": "Q1", "value": 100}]})
        self.assertTrue(os.path.exists(files["ast"]))
        self.assertTrue(os.path.exists(files["vega"]))

    def test_l08_patch_editor(self):
        budget = {"opex": {"rent": 10000.0, "cloud_server": 5000.0}}
        patched = FinancialPatchEditor.apply_patch(budget, "把 rent 压缩 30%")
        self.assertEqual(patched["opex"]["rent"], 7000.0)
        self.assertEqual(patched["opex"]["cloud_server"], 5000.0)

    def test_l09_memory_rollback(self):
        pool = FinancialSessionMemoryPool()
        s1 = pool.commit_snapshot("V1", {"tax_rate": 0.20})
        s2 = pool.commit_snapshot("V2", {"tax_rate": 0.25})
        self.assertEqual(pool.get_working_memory()["tax_rate"], 0.25)
        pool.rollback(s1)
        self.assertEqual(pool.get_working_memory()["tax_rate"], 0.20)

    def test_l10_telemetry_watchdog(self):
        def quick():
            return 42
        val = WatchdogCircuitBreaker.execute_with_guard(quick, timeout_s=1.0)
        self.assertEqual(val, 42)

        tele = ProductionTelemetry()
        tid = tele.record_trace("cfo.deep_analysis", {"status": "start"}, "SUCCESS", 20.4)
        self.assertTrue(os.path.exists(tele.log_path))
        self.assertTrue(len(tid) > 10)

if __name__ == "__main__":
    unittest.main()

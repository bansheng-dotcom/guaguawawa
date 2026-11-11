# -*- coding: utf-8 -*-
"""R01 蛙全局 CEO 十轮渐进自升级演进全量测试套件 (Evolution 10-Stage Test Suite)。

对齐 SOP_AGENT_EVOLUTION_UNIVERSAL.md 规范与验收标准。
"""
import os
import sys
import json
import shutil
import tempfile
import unittest

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 角色根（tests/ 的上一级）
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from engines.base import BaseDecisionEngine, EngineProbeResult, ExecutionResult
from engines.manager import ExecutiveEngineManager, NativeExecutiveEngine
from engines.prompter import ExecutivePrompter
from engines.critic import ExecutiveCritic
from engines.ledger import ExecutiveLedgerParser
from engines.slop_guard import ExecutiveSlopGuard
from engines.explorer import ExecutiveStrategyExplorer
from engines.asset_bundle import ExecutiveAssetBundle
from engines.patch_editor import ExecutivePatchEditor
from engines.memory import ExecutiveMemoryPool
from engines.telemetry import ExecutiveWatchdog, ExecutiveTelemetry

class TestExecutiveEvolutionSuite(unittest.TestCase):

    def test_r01_reality_audit_and_engines(self):
        """R01: 真实外置手脚接管与探针感知"""
        mgr = ExecutiveEngineManager()
        probes = mgr.probe_all()
        self.assertIn("native", probes)
        self.assertTrue(probes["native"].available)
        self.assertEqual(probes["native"].status_code, 200)

        # 真实调度执行
        res = mgr.execute("orchestrate_macro_decision", {"initiative": "海外扩张"})
        self.assertTrue(res.ok)
        self.assertEqual(res.data.get("status"), "COMPLETED")

    def test_r02_dynamic_brain_prompter(self):
        """R02: 动态战略意图编译器与多维归一化"""
        intent = "针对 SaaS 自助版提价 149 元方案，要求 60 天内必须完成并严控流失率"
        spec = ExecutivePrompter.decompose_strategic_intent(intent)
        self.assertEqual(spec["strategic_category"], "pricing")
        self.assertEqual(spec["timebox_days"], 60)
        self.assertEqual(spec["reversibility_hypothesis"], "不可逆")
        self.assertIn("r01", spec["stakeholders"])
        self.assertIn("r06", spec["stakeholders"])

    def test_r03_critic_and_auto_heal_loop(self):
        """R03: 真实决策审校法则与 Auto-Heal 自愈闭环"""
        # 脏输入：不可逆且缺少回滚和杀死标准
        dirty_card = {
            "topic": "全面下线免费版",
            "reversibility": "不可逆",
            "owner": "",
            "success_criteria": [],
            "kill_criteria": []
        }
        passed, score, checks = ExecutiveCritic.audit_decision_card(dirty_card)
        self.assertFalse(passed)
        self.assertLess(score, 70.0)

        # 执行自愈循环
        heal_res = ExecutiveCritic.auto_heal(dirty_card, max_retries=3)
        self.assertTrue(heal_res["ok"])
        self.assertGreaterEqual(heal_res["final_score"], 70.0)
        self.assertTrue(len(heal_res["card"]["kill_criteria"]) > 0)
        self.assertTrue(bool(heal_res["card"]["rollback_plan"]))

    def test_r04_persistent_governance_ledger(self):
        """R04: 持久化治理规范账本解析"""
        spec = ExecutiveLedgerParser.load_spec()
        constants = spec["constants"]
        self.assertEqual(constants.get("FREEZE_DAYS_PRICING"), 60)
        self.assertEqual(constants.get("FREEZE_DAYS_PIVOT"), 90)
        self.assertTrue(len(spec["prohibited_phrases"]) >= 3)

    def test_r05_slop_guard_and_polish(self):
        """R05: 反伪影审计与行动项精修"""
        slop_text = "针对当前市场变化，各部门高度重视并积极研究，后续尽快推进，逐步优化商业化效率。"
        passed, score, issues = ExecutiveSlopGuard.audit_text(slop_text)
        self.assertFalse(passed)
        self.assertGreater(score, 0)
        self.assertTrue(len(issues) >= 3)

        polished = ExecutiveSlopGuard.polish_text(slop_text, default_owner="r02", default_days=7)
        self.assertNotIn("尽快推进", polished)
        self.assertIn("r02", polished)

    def test_r06_multi_strategy_explorer(self):
        """R06: 3向战略分支裂变与画廊看板"""
        branches = ExecutiveStrategyExplorer.explore_branches("2027年度商业化策略", {})
        self.assertEqual(len(branches), 3)
        b_names = [b["branch_id"] for b in branches]
        self.assertIn("branch_alpha_aggressive", b_names)
        self.assertIn("branch_beta_conservative", b_names)
        self.assertIn("branch_gamma_lean_mvp", b_names)

        dashboard = ExecutiveStrategyExplorer.generate_comparison_dashboard("2027年度商业化策略", branches)
        self.assertIn("战略决策多向对比看板", dashboard)
        self.assertIn("极速突进", dashboard)

    def test_r07_asset_bundle(self):
        """R07: 伴生结构化治理资产包导出"""
        card = {
            "topic": "企业级私有化交付红线",
            "owner": "r01",
            "reversibility": "不可逆",
            "kill_criteria": ["交付周期超45天自动退单"],
            "success_criteria": ["毛利 >= 65%"]
        }
        spec = ExecutiveAssetBundle.build_executive_spec(card)
        self.assertIn("governance_ast", spec)
        self.assertEqual(spec["metadata"]["topic"], "企业级私有化交付红线")

        tmp_dir = tempfile.mkdtemp()
        try:
            exported = ExecutiveAssetBundle.export_bundle(tmp_dir, spec)
            self.assertTrue(os.path.exists(exported))
            with open(exported, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["version"], "1.0.0")
        finally:
            shutil.rmtree(tmp_dir)

    def test_r08_incremental_patch_editor(self):
        """R08: 局部差量修改与结构无损锁定"""
        original = {
            "topic": "Q3预算平衡",
            "owner": "r01",
            "freeze_days": 30,
            "reversibility": "可逆",
            "kill_criteria": ["老客流失 > 5%"]
        }
        instruction = "将责任人改为 r02，并将冷却天数调整为 60 天"
        patched, ops = ExecutivePatchEditor.apply_patch(original, instruction)
        self.assertEqual(patched["owner"], "r02")
        self.assertEqual(patched["freeze_days"], 60)
        # 保证原有结构不被破坏
        self.assertEqual(patched["topic"], "Q3预算平衡")
        self.assertEqual(patched["kill_criteria"], ["老客流失 > 5%"])
        self.assertEqual(len(ops), 2)

    def test_r09_memory_pool_and_rollback(self):
        """R09: 会话状态记忆与历史版本快照回滚"""
        tmp_file = os.path.join(tempfile.gettempdir(), "test_ceo_memory.json")
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        try:
            pool = ExecutiveMemoryPool(tmp_file)
            v1 = pool.commit("init", {"plan": "A", "budget": 100})
            self.assertEqual(v1, 1)

            v2 = pool.commit("update", {"plan": "B", "budget": 200})
            self.assertEqual(v2, 2)
            self.assertEqual(pool.current_state["plan"], "B")

            # 回滚至 v1
            restored = pool.rollback(1)
            self.assertEqual(restored["plan"], "A")
            self.assertEqual(pool.current_state["plan"], "A")

            # 代词解析
            ref = pool.resolve_reference("把刚才那个决策找出来")
            self.assertIsNotNone(ref)
        finally:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

    def test_r10_watchdog_and_telemetry(self):
        """R10: 看门狗熔断、指数退避与遥测追踪"""
        tmp_log = os.path.join(tempfile.gettempdir(), "test_ceo_telemetry.jsonl")
        if os.path.exists(tmp_log):
            os.remove(tmp_log)
        try:
            telemetry = ExecutiveTelemetry(tmp_log)
            trace_id = telemetry.record_trace("test_action", {"foo": "bar"}, "PASS", 3.5)
            self.assertTrue(trace_id.startswith("trace_ceo_"))
            self.assertTrue(os.path.exists(tmp_log))

            # 看门狗弹性容灾测试（降级熔断）
            def faulty_func():
                raise ConnectionError("External API Timeout")

            res = ExecutiveWatchdog.execute_with_resilience(
                faulty_func,
                max_retries=2,
                base_delay_sec=0.01,
                fallback_func=lambda: {"fallback": True}
            )
            self.assertTrue(res["ok"])
            self.assertTrue(res.get("degraded"))
            self.assertTrue(res["result"]["fallback"])
        finally:
            if os.path.exists(tmp_log):
                os.remove(tmp_log)

if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""tests/test_evolution_l01_l10.py - R17 蛙织网 · 自动化与集成工程师 十维演进双轨集成测试套件。

严格遵循 Universal Agent 10-Stage Evolution SOP v13.0 三大阶段 10 个演进阶梯：
- TestEvolutionRound1 (Stage 1 / L01~L03 基石阶段): 工作流拓扑沙箱、意图解构 5 阶段 Kahn DAG、自愈反思红线拦截与补平
- TestEvolutionRound2 (Stage 2 / L04~L06 深度阶段): AUTOMATION_SPEC 领域账本、Anti-Slop 质感去劣化、横向架构决策三维看板
- TestEvolutionRound3 (Stage 3 / L07~L10 交付阶段): 伴生资产包与 SARIF/Vega 导出、RFC 6902 差量热修、会话记忆代词消歧、看门狗熔断与遥测
"""
from __future__ import annotations

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(AGENTS)
for p in (HERE, AGENTS, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from engines import (
    AutomationRuntimeEngine,
    AutomationIntentCompiler,
    AutomationReflexiveHealer,
    AutomationSpecLedger,
    AutomationSlopGuard,
    AutomationScenarioMatrix,
    AutomationAssetBundle,
    AutomationDiffPatchEngine,
    AutomationSessionMemory,
    AutomationTelemetryWatchdog,
    WatchdogBreaker,
    TelemetryTracer,
)


class TestEvolutionRound1(unittest.TestCase):
    """第 1 轮升级 (Stage 1 / L01~L03 基石阶段) 集成测试。"""

    def test_l01_runtime_probe_and_topology_sandbox(self):
        engine = AutomationRuntimeEngine()
        probe = engine.probe_health()
        self.assertEqual(probe["status"], "HEALTHY")
        self.assertEqual(probe["engine"], "AutomationRuntimeEngine")
        self.assertEqual(probe["topology_sandbox"], "OK")
        self.assertEqual(probe["dry_run_simulator"], "OK")
        self.assertEqual(probe["idempotency_sandbox"], "OK")

        # 1. 拓扑 DAG 分析与悬空边检测
        demo_wf = {
            "nodes": [
                {"id": "n1", "name": "webhook", "type": "webhook_trigger"},
                {"id": "n2", "name": "mapping", "type": "mapping_transform"},
                {"id": "n3", "name": "http", "type": "http_request"}
            ],
            "connections": [
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "n3"}
            ]
        }
        res = engine.analyze_topology(demo_wf)
        self.assertTrue(res["ok"])
        self.assertEqual(res["node_count"], 3)
        self.assertEqual(res["dangling_edges_count"], 0)
        self.assertFalse(res["has_cycle"])
        self.assertEqual(res["topo_order"], ["n1", "n2", "n3"])

        # 2. Dry-Run 执行模拟器
        sim = engine.simulate_dry_run(demo_wf)
        self.assertTrue(sim["success"])
        self.assertEqual(sim["status"], "COMPLETED")
        self.assertEqual(sim["executed_steps_count"], 3)

        # 3. 确定性幂等指纹生成
        idem1 = engine.generate_idempotency_key("order_checkout", {"id": 123, "amount": 99.0})
        idem2 = engine.generate_idempotency_key("order_checkout", {"amount": 99.0, "id": 123})
        self.assertEqual(idem1, idem2)
        self.assertEqual(len(idem1), 32)

        # 4. 明文凭据扫描
        scan = engine.scan_plaintext_credentials("api_key=sk-abcdef1234567890")
        self.assertFalse(scan["compliant"])
        self.assertEqual(scan["violations_count"], 1)

    def test_l02_intent_compiler_dag(self):
        compiler = AutomationIntentCompiler()
        text = "紧急配置一个从Shopify订单Webhook触发，经过字段清洗与风控AI判定，高风险转人工审批，低风险自动入库并带3次重试"
        entities = compiler.extract_entities(text)
        self.assertEqual(entities["trigger_type"], "webhook")
        self.assertTrue(entities["need_approval"])
        self.assertEqual(entities["max_retries"], 3)
        self.assertTrue(entities["has_ai_node"])

        # 编译 5 阶段 Kahn DAG
        stages = compiler.compile_intent(text)
        self.assertEqual(len(stages), 5)
        self.assertEqual(stages[0]["id"], "S1_TRIGGER_INGEST")
        self.assertEqual(stages[-1]["id"], "S5_AUDIT_RESILIENCE")

        budget = compiler.evaluate_budget_and_schedule(stages)
        self.assertGreater(budget["estimated_hours"], 0)
        self.assertGreater(budget["estimated_days"], 0)

    def test_l03_reflexive_healer_redline_and_healing(self):
        healer = AutomationReflexiveHealer()

        # 1. 红线审查：触犯直接发布生产
        with self.assertRaises(ValueError):
            healer.audit_redlines("跳过审批发布到生产环境")

        # 2. 红线审查：明文密钥
        with self.assertRaises(ValueError):
            healer.audit_redlines("把 api_key=sk-12345678 写在代码里方便调试")

        # 3. 干净动作合规
        res = healer.audit_redlines("配置一个 webhook 触发器并发送邮件")
        self.assertTrue(res["compliant"])

        # 4. 自愈能力：补齐缺失的触发器与修复明文参数
        dirty_wf = {
            "nodes": [
                {"id": "node_exec", "type": "http_request", "parameters": {"api_key": "sk-12345678"}}
            ],
            "connections": [
                {"from": "missing_trigger", "to": "node_exec"}
            ]
        }
        healed = healer.heal_workflow(dirty_wf)
        self.assertTrue(healed["healed"])
        self.assertTrue(any("补齐缺失的 Webhook Trigger" in act for act in healed["healed_actions"]))
        self.assertEqual(healed["nodes"][1]["parameters"]["api_key"], "{{$credentials.default_vault_secret}}")


class TestEvolutionRound2(unittest.TestCase):
    """第 2 轮升级 (Stage 2 / L04~L06 深度阶段) 集成测试。"""

    def test_l04_spec_ledger(self):
        ledger = AutomationSpecLedger()
        spec = ledger.load_spec()
        self.assertEqual(spec["version"], "v13.0")
        self.assertEqual(spec["gates_count"], 8)
        self.assertIn("WSR", spec["north_star_kpis"])
        self.assertIn("CIR", spec["north_star_kpis"])

        # 门禁合规检查
        good_data = {
            "dangling_edges": [],
            "is_dag": True,
            "credential_violations": 0,
            "is_write_action": True,
            "has_idempotency_key": True,
            "is_production_publish": True,
            "is_approved": True,
            "max_retries": 3,
            "has_dlq": True,
            "mapping_reserved_conflict": False,
            "ai_node_unprotected": False,
            "audit_complete": True,
        }
        v_res = ledger.verify_gate_compliance("workflow", good_data)
        self.assertEqual(v_res["verdict"], "PASS")
        self.assertEqual(v_res["passed_gates"], 8)

        # 故意破损门禁
        bad_data = dict(good_data)
        bad_data["has_idempotency_key"] = False
        bad_res = ledger.verify_gate_compliance("workflow", bad_data)
        self.assertEqual(bad_res["verdict"], "FAIL")
        self.assertEqual(bad_res["violations_count"], 1)

    def test_l05_slop_guard(self):
        guard = AutomationSlopGuard()
        slop_text = "该自动化流程整体运行平稳，视情况进行重试，流程基本跑通，相关细节待定。"
        audit_res = guard.audit(slop_text)
        self.assertTrue(audit_res["has_slop"])
        self.assertGreater(audit_res["slop_hits_count"], 0)
        self.assertLess(audit_res["actionability_score"], 100)

        cleaned = guard.clean(slop_text)
        self.assertNotIn("整体运行平稳", cleaned)
        self.assertIn("99.98%", cleaned)
        self.assertIn("(DRI): R17", cleaned)

    def test_l06_scenario_matrix(self):
        matrix = AutomationScenarioMatrix()
        scenarios = matrix.generate("订单数据双向流转", daily_events=20000)
        self.assertEqual(len(scenarios), 3)

        rec = [s for s in scenarios if s.get("recommended")]
        self.assertEqual(len(rec), 1)
        self.assertEqual(rec[0]["id"], "SCN_RESILIENT_BUFFERED")

        md = matrix.render_markdown(scenarios)
        self.assertIn("稳健队列缓冲版", md)
        self.assertIn("极速轻量同步版", md)


class TestEvolutionRound3(unittest.TestCase):
    """第 3 轮升级 (Stage 3 / L07~L10 交付阶段) 集成测试。"""

    def test_l07_asset_bundle(self):
        bundle_eng = AutomationAssetBundle()
        paths = bundle_eng.compile_and_save("test_r17_run_001", {"wf": "order_sync"}, violations=["GATE-01 破损示例"])
        self.assertTrue(os.path.exists(paths["bundle"]))
        self.assertTrue(os.path.exists(paths["sarif"]))
        self.assertTrue(os.path.exists(paths["vega"]))

        with open(paths["sarif"], "r", encoding="utf-8") as f:
            sarif = json.load(f)
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertEqual(len(sarif["runs"][0]["results"]), 1)

    def test_l08_diff_patch_engine(self):
        diff_eng = AutomationDiffPatchEngine()
        old_wf = {
            "name": "Sync",
            "retry_policy": {"max_retries": 3, "backoff": 2},
            "nodes": {"n1": {"type": "webhook"}}
        }
        new_wf = {
            "name": "Sync V2",
            "retry_policy": {"max_retries": 5, "backoff": 2},
            "nodes": {"n1": {"type": "webhook"}, "n2": {"type": "transform"}}
        }
        patch = diff_eng.create_patch(old_wf, new_wf)
        self.assertGreater(len(patch), 0)

        applied = diff_eng.apply_patch(old_wf, patch)
        self.assertEqual(applied["name"], "Sync V2")
        self.assertEqual(applied["retry_policy"]["max_retries"], 5)
        self.assertIn("n2", applied["nodes"])

    def test_l09_session_memory(self):
        mem = AutomationSessionMemory()
        # 记录快照
        snap1 = mem.record_snapshot("v1_config", {"retries": 3})
        self.assertIsNotNone(snap1)

        snap2 = mem.record_snapshot("v2_config", {"retries": 5})
        self.assertIsNotNone(snap2)

        # 代词消歧
        disamb = mem.disambiguate_query("把刚才第二套方案生成工作流")
        self.assertTrue(disamb["resolved"])
        self.assertIn("selected_scenario", disamb["params"])

        # 回退测试
        restored = mem.rollback()
        self.assertIsNotNone(restored)

    def test_l10_telemetry_watchdog(self):
        wd = AutomationTelemetryWatchdog()

        # 正常弹性执行
        res = wd.execute_with_resilience(lambda: 100, action_name="test_resilience")
        self.assertEqual(res, 100)

        # 触发重试与熔断
        breaker = WatchdogBreaker(failure_threshold=2, recovery_timeout_sec=0.1)
        self.assertTrue(breaker.can_execute())
        breaker.record_failure()
        self.assertTrue(breaker.can_execute())
        breaker.record_failure()
        self.assertFalse(breaker.can_execute())
        self.assertEqual(breaker.state, "OPEN")


if __name__ == "__main__":
    unittest.main()

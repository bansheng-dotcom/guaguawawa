# -*- coding: utf-8 -*-
"""tests/test_evolution_l01_l10.py - R13 蛙客成 · 客户成功与销售运营官 十维演进双轨集成测试套件。

覆盖 SOP v11.0 三大阶段 10 个演进阶梯：
- TestEvolutionRound1 (Stage 1 / L01~L03 基石阶段): 工具实体沙箱、意图解构 Kahn DAG、自愈反思红线拦截
- TestEvolutionRound2 (Stage 2 / L04~L06 深度阶段): CSM_SPEC 领域账本、Anti-Slop 质感去劣化、横向三维挽留决策看板
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
    CsmRuntimeEngine,
    IntentCompiler,
    ReflexiveHealer,
    SpecLedger,
    SlopGuard,
    ScenarioMatrix,
    CsmAssetBundle,
    CsmDiffPatchEngine,
    CsmSessionMemory,
    CsmTelemetryWatchdog,
    WatchdogBreaker,
    TelemetryTracer,
)


class TestEvolutionRound1(unittest.TestCase):
    """第 1 轮升级 (L01~L03 基石阶段) 集成测试。"""

    def test_l01_runtime_probe_and_metrics(self):
        engine = CsmRuntimeEngine()
        probe = engine.probe_health()
        self.assertEqual(probe["status"], "healthy")
        self.assertEqual(probe["layer"], "L01")
        self.assertIn("nps_calculator", probe["probes"])

        # 1. 测试 NPS 计算沙箱
        # 10个样本: 9, 10, 10, 9 (4个推荐) / 7, 8 (2个中立) / 5, 4, 6, 2 (4个贬损) -> NPS = 0.0
        nps_res = engine.calculate_nps([9, 10, 10, 9, 7, 8, 5, 4, 6, 2])
        self.assertTrue(nps_res["valid"])
        self.assertTrue(nps_res["sample_size_ok"])
        self.assertEqual(nps_res["promoters"], 4)
        self.assertEqual(nps_res["detractors"], 4)
        self.assertAlmostEqual(nps_res["nps"], 0.0)

        # 2. 测试客户四维健康综合加权
        health_res = engine.calculate_health_score({
            "usage": 80.0,
            "quality": 85.0,
            "relationship": 90.0,
            "commercial": 75.0,
        })
        # 80*0.3 + 85*0.25 + 90*0.25 + 75*0.2 = 24 + 21.25 + 22.5 + 15 = 82.75
        self.assertAlmostEqual(health_res["overall_health_score"], 82.75)
        self.assertEqual(health_res["health_level"], "HEALTHY")
        self.assertTrue(health_res["is_healthy"])

        # 3. 测试管道 HHI 集中度风险
        opps = [
            {"amount": 800000.0, "name": "巨型订单"},
            {"amount": 100000.0, "name": "中型订单"},
            {"amount": 100000.0, "name": "小型订单"},
        ]
        hhi_res = engine.calculate_pipeline_hhi(opps)
        # 80%^2 + 10%^2 + 10%^2 = 6400 + 100 + 100 = 6600 > 2500 -> HIGH
        self.assertGreater(hhi_res["hhi"], 2500.0)
        self.assertEqual(hhi_res["risk_level"], "HIGH")

        # 4. 测试流失风险预测模型
        churn_res = engine.predict_churn_risk({
            "health_score": 85.0,
            "ticket_reopen_rate": 0.05,
            "days_since_last_touch": 10,
            "overdue_commitments": 0,
        })
        self.assertFalse(churn_res["requires_intervention"])
        self.assertLess(churn_res["churn_risk_score"], 35.0)

    def test_l02_intent_decompilation(self):
        compiler = IntentCompiler()
        query = "A公司出现流失预警，急需开展客户健康度体检，排查工单积压并输出续约挽留方案"
        stages = compiler.compile_intent(query)
        self.assertEqual(len(stages), 5)
        self.assertEqual(stages[0]["id"], "s01_crm_audit")
        self.assertEqual(stages[4]["id"], "s05_automation_dispatch")

        summary = compiler.get_dag_summary(stages)
        self.assertTrue(summary["is_valid_dag"])
        self.assertGreater(summary["total_estimated_hours"], 10.0)

    def test_l03_reflexive_healing_and_redlines(self):
        healer = ReflexiveHealer()

        # 1. 红线拦截：越界处理退款 (移交 R14)
        with self.assertRaises(ValueError) as ctx:
            healer.check_redlines("为客户申请全额退款并原路打款")
        self.assertIn("R14", str(ctx.exception))

        # 2. 红线拦截：私下违规承诺
        with self.assertRaises(ValueError) as ctx:
            healer.check_redlines("私下承诺免单一年")
        self.assertIn("违规承诺", str(ctx.exception))

        # 3. 合规放行
        ok_res = healer.check_redlines("为客户安排高管现场 QBR 拜访")
        self.assertFalse(ok_res["blocked"])

        # 4. 双门槛准入校验
        dual_pass, _ = healer.evaluate_renewal_gate(75.0, 30.0)
        self.assertTrue(dual_pass)
        dual_fail, reason = healer.evaluate_renewal_gate(55.0, 65.0)
        self.assertFalse(dual_fail)
        self.assertIn("破损", reason)

        # 5. 自愈不完整档案与承诺三件套
        dirty_record = {
            "name": "测试网络公司",
            "commitments": ["修复导出故障", {"what": "更新培训文档"}],
        }
        healed = healer.heal_client_record(dirty_record)
        self.assertEqual(healed["company_name"], "测试网络公司")
        self.assertIn("health_score", healed)
        self.assertEqual(len(healed["commitments"]), 2)
        self.assertEqual(healed["commitments"][0]["owner"], "蛙客成")
        self.assertEqual(healed["commitments"][0]["due"], "2026-12-31")


class TestEvolutionRound2(unittest.TestCase):
    """第 2 轮升级 (L04~L06 深度阶段) 集成测试。"""

    def test_l04_spec_ledger(self):
        ledger = SpecLedger()
        spec = ledger.load_spec()
        self.assertEqual(spec["version"], "v11.0")
        self.assertIn("GRR", spec["north_star"])
        self.assertIn("GATE-01", spec["gates"])
        self.assertEqual(spec["health_weights"]["usage"], 30.0)

        # 门禁合规审计
        audit_ok = ledger.audit_client_metrics({
            "first_response_min": 60.0,
            "reopen_rate": 0.08,
            "nps_sample_size": 15,
            "health_score": 85.0,
            "risk_score": 25.0,
        })
        self.assertTrue(audit_ok["all_gates_passed"])

        audit_bad = ledger.audit_client_metrics({
            "first_response_min": 300.0,  # 超标 > 240
            "reopen_rate": 0.20,         # 超标 > 0.15
        })
        self.assertFalse(audit_bad["all_gates_passed"])

    def test_l05_slop_guard(self):
        guard = SlopGuard()
        bad_text = "客户关系整体良好，值得重点关注，服务体验稳步提升，相关功能待定"
        audit_res = guard.audit(bad_text)
        self.assertFalse(audit_res["is_clean"])
        self.assertGreaterEqual(audit_res["slop_count"], 3)

        cleaned = guard.clean(bad_text)
        self.assertNotIn("整体良好", cleaned)
        self.assertNotIn("值得重点关注", cleaned)
        self.assertIn("四维健康分", cleaned)
        self.assertIn("DRI 蛙客成", cleaned)

    def test_l06_scenario_matrix(self):
        matrix = ScenarioMatrix()
        scenarios = matrix.generate("A公司", 300000.0)
        self.assertEqual(len(scenarios), 3)

        ids = [s["id"] for s in scenarios]
        self.assertIn("minimal_defensive", ids)
        self.assertIn("steady_standard", ids)
        self.assertIn("strategic_enterprise", ids)

        # 检查各方案属性
        self.assertGreater(scenarios[2]["expected_retained_arr"], scenarios[0]["expected_retained_arr"])
        self.assertGreater(scenarios[2]["person_days"], scenarios[0]["person_days"])

        md = matrix.render_markdown_matrix(scenarios)
        self.assertIn("极简防御型", md)
        self.assertIn("稳健运营型", md)


class TestEvolutionRound3(unittest.TestCase):
    """第 3 轮升级 (L07~L10 交付阶段) 集成测试。"""

    def test_l07_asset_bundle(self):
        bundle_eng = CsmAssetBundle()
        run_id = "test_run_unit_01"
        res = bundle_eng.export_bundle(
            run_id,
            {
                "company_name": "A公司",
                "health_score": 82.5,
                "health_breakdown": {"usage": 85, "quality": 80, "relationship": 80, "commercial": 75},
            },
            issues=[{"rule_id": "CSM001", "level": "warning", "message": "首响轻微波动"}],
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(res["bundle_path"]))
        self.assertTrue(os.path.exists(res["sarif_path"]))
        self.assertTrue(os.path.exists(res["vega_path"]))

        with open(res["sarif_path"], "r", encoding="utf-8") as f:
            sarif = json.load(f)
            self.assertEqual(sarif["version"], "2.1.0")

    def test_l08_diff_patch_engine(self):
        patch_eng = CsmDiffPatchEngine()
        old_profile = {"company_name": "A公司", "tier": "standard", "health": {"usage": 80, "quality": 70}}
        new_profile = {"company_name": "A公司", "tier": "enterprise", "health": {"usage": 90, "quality": 70}}

        patch = patch_eng.create_patch(old_profile, new_profile)
        self.assertEqual(len(patch), 2)

        applied = patch_eng.apply_patch(old_profile, patch)
        self.assertEqual(applied["tier"], "enterprise")
        self.assertEqual(applied["health"]["usage"], 90)

        # 差量分数计算
        weights = {"usage": 50.0, "quality": 50.0}
        delta_res = patch_eng.calculate_health_delta(old_profile["health"], [{"op": "replace", "path": "/usage", "value": 90}], weights)
        self.assertAlmostEqual(delta_res["delta"], 5.0)
        self.assertEqual(delta_res["direction"], "IMPROVED")

    def test_l09_session_memory(self):
        mem = CsmSessionMemory()
        mem.update_context(client="甲骨文软件", scenario="steady_standard")

        # 代词消歧
        resolved = mem.resolve_pronouns("按刚才第二套方案推进甲骨文客户的续约")
        self.assertTrue(resolved["had_ambiguity"])
        self.assertIn("steady_standard", resolved["resolved_query"])

        # 快照与回滚
        snap_id = mem.create_snapshot("test_checkpoint")
        mem.update_context(client="新客B", scenario="minimal_defensive")
        self.assertEqual(mem.state["current_client"], "新客B")

        ok = mem.rollback(snap_id)
        self.assertTrue(ok)
        self.assertEqual(mem.state["current_client"], "甲骨文软件")

    def test_l10_telemetry_watchdog(self):
        # 1. 熔断测试
        breaker = WatchdogBreaker(failure_threshold=2, recovery_time_sec=0.5)

        def failing_func():
            raise ValueError("simulated network error")

        with self.assertRaises(ValueError):
            breaker.call(failing_func)
        with self.assertRaises(ValueError):
            breaker.call(failing_func)

        # 达到阈值后熔断为 OPEN
        self.assertEqual(breaker.state, "OPEN")
        with self.assertRaises(RuntimeError) as ctx:
            breaker.call(lambda: 42)
        self.assertIn("CIRCUIT BREAKER OPEN", str(ctx.exception))

        # 2. 遥测日志测试
        tracer = TelemetryTracer()
        entry = tracer.record_span("unit_test_span", 5.5, "OK", {"test": True})
        self.assertEqual(entry["span_name"], "unit_test_span")
        self.assertEqual(entry["status"], "OK")


if __name__ == "__main__":
    unittest.main()

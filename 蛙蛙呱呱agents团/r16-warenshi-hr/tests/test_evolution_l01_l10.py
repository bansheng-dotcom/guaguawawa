# -*- coding: utf-8 -*-
"""tests/test_evolution_l01_l10.py - R16 蛙人事 · 人力资源与组织运营官 十维演进双轨集成测试套件。

严格遵循 Universal Agent 10-Stage Evolution SOP v13.0 三大阶段 10 个演进阶梯：
- TestEvolutionRound1 (Stage 1 / L01~L03 基石阶段): 人事精算沙箱、意图解构 5 阶段 Kahn DAG、自愈反思红线拦截与补平
- TestEvolutionRound2 (Stage 2 / L04~L06 深度阶段): HR_SPEC 领域账本、Anti-Slop 质感去劣化、横向用工决策三维看板
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
    HRRuntimeEngine,
    HRIntentCompiler,
    HRReflexiveHealer,
    HRSpecLedger,
    HRSlopGuard,
    HRScenarioMatrix,
    HRAssetBundle,
    HRDiffPatchEngine,
    HRSessionMemory,
    HRTelemetryWatchdog,
    WatchdogBreaker,
    TelemetryTracer,
)


class TestEvolutionRound1(unittest.TestCase):
    """第 1 轮升级 (Stage 1 / L01~L03 基石阶段) 集成测试。"""

    def test_l01_runtime_probe_and_payroll_sandbox(self):
        engine = HRRuntimeEngine()
        probe = engine.probe_health()
        self.assertEqual(probe["status"], "HEALTHY")
        self.assertEqual(probe["engine"], "HRRuntimeEngine")
        self.assertEqual(probe["payroll_sandbox"], "OK")
        self.assertEqual(probe["attendance_sandbox"], "OK")
        self.assertEqual(probe["funnel_sandbox"], "OK")

        # 1. 测试真实薪酬净额平衡精算 (gross 10000)
        pay_res = engine.calculate_net_payroll(
            gross_pay=10000.0,
            statutory_base=10000.0,
            special_additional_deduction=1000.0,
        )
        self.assertTrue(pay_res["is_conserved"])
        self.assertEqual(pay_res["gross_pay"], 10000.0)
        self.assertGreater(pay_res["net_pay"], 0)
        self.assertEqual(pay_res["net_pay"], round(pay_res["gross_pay"] - pay_res["total_deductions"], 2))

        # 2. 测试工时折算与请假扣减
        att_res = engine.calculate_attendance_hours(
            standard_daily_hours=8.0,
            work_days=21.75,
            overtime_hours=10.0,
            leave_hours=8.0,
        )
        self.assertEqual(att_res["status"], "OK")
        self.assertEqual(att_res["net_payable_hours"], 176.0)

        # 3. 测试招聘漏斗转化率
        funnel_res = engine.calculate_recruitment_funnel([
            {"stage": "applicants", "count": 100},
            {"stage": "screening", "count": 40},
            {"stage": "interview", "count": 10},
            {"stage": "offer", "count": 3},
            {"stage": "onboard", "count": 2},
        ])
        self.assertEqual(funnel_res["total_applicants"], 100)
        self.assertEqual(funnel_res["overall_conversion_rate"], 0.02)

        # 4. 测试 PII 敏感度扫描
        pii_check = engine.scan_pii_compliance("员工身份证号：110101199003072345，银行卡号：6222021234567890123")
        self.assertFalse(pii_check["compliant"])
        self.assertGreater(pii_check["violations_count"], 0)

    def test_l02_intent_compiler_dag(self):
        compiler = HRIntentCompiler()
        text = "紧急为前端团队招募2名资深工程师，需要安排面试、发Offer并签署劳动合同"
        entities = compiler.extract_entities(text)
        self.assertTrue(entities["is_urgent"])
        self.assertEqual(entities["headcount"], 2)
        self.assertTrue(entities["need_contract"])

        # 编译 5 阶段 Kahn DAG
        stages = compiler.compile_intent(text)
        self.assertEqual(len(stages), 5)

        summary = compiler.evaluate_budget_and_schedule(stages)
        self.assertTrue(summary["is_dag_valid"])
        self.assertEqual(len(summary["topological_sequence"]), 5)
        self.assertGreater(summary["total_estimated_hours"], 0)

    def test_l03_reflexive_healer_and_redline(self):
        healer = HRReflexiveHealer()

        # 1. 人事四大红线刚性拦截
        with self.assertRaises(ValueError):
            healer.audit_redlines("代发工资并立即划扣款项")

        with self.assertRaises(ValueError):
            healer.audit_redlines("身份证原件扫描并明文存储")

        with self.assertRaises(ValueError):
            healer.audit_redlines("出具正式法律意见书担保胜诉")

        # 2. 自愈反思补平薪酬分位微小差异
        broken_payroll = {
            "gross_pay": 10000.0,
            "total_deductions": 2000.0,
            "net_pay": 7999.0,  # 差异 1 元
        }
        healed, notes = healer.heal_payroll_balance(broken_payroll)
        self.assertEqual(healed["net_pay"], 8000.0)
        self.assertTrue(any("补平" in n for n in notes))


class TestEvolutionRound2(unittest.TestCase):
    """第 2 轮升级 (Stage 2 / L04~L06 深度阶段) 集成测试。"""

    def test_l04_spec_ledger(self):
        ledger = HRSpecLedger()
        spec = ledger.load_spec()
        self.assertEqual(spec["role"], "R16 蛙人事 · 人力资源与组织运营官")
        self.assertEqual(spec["version"], "v13.0")
        self.assertEqual(spec["gates_count"], 8)
        self.assertIn("PRA", spec["north_star_kpis"])
        self.assertIn("OTA", spec["north_star_kpis"])

        # 验证门禁合规检查通过
        good_artifact = {
            "gross_pay": 10000.0,
            "total_deductions": 2000.0,
            "net_pay": 8000.0,
            "pii_violations": 0,
            "stage": "Offer",
            "previous_stage": "Shortlisted",
            "requested_days": 3.0,
            "leave_balance": 5.0,
            "overlap_count": 0,
            "policy_source": "COMPANY_HR_POLICY_2026",
            "claim_total": 500.0,
            "claim_items": [{"amount": 500.0}],
            "requires_handoff": False,
        }
        res = ledger.verify_gate_compliance("payroll", good_artifact)
        self.assertTrue(res["compliant"])
        self.assertEqual(res["violations_count"], 0)

        # 验证门禁违规拦截
        bad_artifact = {
            "gross_pay": 10000.0,
            "total_deductions": 2000.0,
            "net_pay": 5000.0,  # 净额不恒等
            "pii_violations": 2,  # PII 泄露
            "requested_days": 10.0,
            "leave_balance": 2.0,  # 超额请假
            "requires_handoff": True,
            "handoff_declared": False,  # 缺少移交
        }
        bad_res = ledger.verify_gate_compliance("payroll", bad_artifact)
        self.assertFalse(bad_res["compliant"])
        self.assertGreaterEqual(bad_res["violations_count"], 3)

    def test_l05_slop_guard(self):
        guard = HRSlopGuard()
        slop_text = "整体表现良好，相关细节待定，基本符合要求。"
        audit = guard.audit(slop_text)
        self.assertTrue(audit["has_slop"])
        self.assertGreaterEqual(audit["slop_count"], 2)
        self.assertIn("蛙人事", audit["cleaned_text"])
        self.assertGreater(audit["actionability_score"], 0)

        # 干净量化文本直接通过
        clean_text = "综合绩效考核得分 92.5 分，核心 KPI 达成率 105.0%，明确 DRI 为 R16 蛙人事。"
        clean_audit = guard.audit(clean_text)
        self.assertFalse(clean_audit["has_slop"])
        self.assertEqual(clean_audit["status"], "PASS")

    def test_l06_scenario_matrix(self):
        matrix = HRScenarioMatrix()
        scenarios = matrix.generate(role_title="算法科学家", headcount=2, base_monthly_salary=40000.0)
        self.assertEqual(len(scenarios), 3)

        sc_ids = [s["id"] for s in scenarios]
        self.assertIn("SCN_A_CONTINGENT", sc_ids)
        self.assertIn("SCN_B_FTE", sc_ids)
        self.assertIn("SCN_C_GRADUATE", sc_ids)

        # 验证方案 B 为推荐方案
        fte = next(s for s in scenarios if s["id"] == "SCN_B_FTE")
        self.assertTrue(fte["is_recommended"])
        self.assertEqual(fte["roi_score"], 9.5)

        # 验证 Markdown 渲染输出
        md = matrix.render_markdown(scenarios)
        self.assertIn("SCN_B_FTE", md)
        self.assertIn("⭐ 推荐", md)


class TestEvolutionRound3(unittest.TestCase):
    """第 3 轮升级 (Stage 3 / L07~L10 交付阶段) 集成测试。"""

    def test_l07_asset_bundle(self):
        bundle = HRAssetBundle()
        paths = bundle.compile_and_save("test_hr_bundle_001")
        self.assertTrue(os.path.exists(paths["bundle_file"]))
        self.assertTrue(os.path.exists(paths["sarif_file"]))
        self.assertTrue(os.path.exists(paths["vega_file"]))

        # 验证 SARIF 规范有效性 (OASIS SARIF v2.1.0)
        with open(paths["sarif_file"], "r", encoding="utf-8") as f:
            sarif = json.load(f)
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertEqual(sarif["runs"][0]["tool"]["driver"]["name"], "R16-HR-Auditor")

    def test_l08_diff_patch_engine(self):
        patcher = HRDiffPatchEngine()
        old_record = {
            "employee_id": "EMP001",
            "gross": 15000.0,
            "deductions": 3000.0,
            "net": 12000.0,
        }
        # 修改 gross 为 18000.0
        new_record = dict(old_record)
        new_record["gross"] = 18000.0

        patches = patcher.create_patch(old_record, new_record)
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0]["op"], "replace")
        self.assertEqual(patches[0]["path"], "/gross")
        self.assertEqual(patches[0]["value"], 18000.0)

        # 应用补丁并触发增量守恒净额重算 (18000 - 3000 = 15000.0)
        applied = patcher.apply_patch(old_record, patches)
        self.assertEqual(applied["gross"], 18000.0)
        self.assertEqual(applied["net"], 15000.0)
        self.assertTrue(applied["is_conserved"])

    def test_l09_session_memory(self):
        memory = HRSessionMemory()
        # 记录快照
        snap_id = memory.record_snapshot("initial_role", {"role_name": "前端工程师", "employee_id": "EMP_20261110_01"})
        self.assertTrue(snap_id.startswith("snap_"))

        # 代词消歧测试
        resolved = memory.disambiguate_query("按刚才第二套方案招人")
        self.assertIn("SCN_B", resolved["disambiguated"])
        self.assertEqual(resolved["referenced_context"]["selected_scenario"], "SCN_B")

        # 薪资上浮消歧
        resolved_sal = memory.disambiguate_query("把上次那个前端岗薪酬上限调高2k")
        self.assertEqual(resolved_sal["referenced_context"]["role_name"], "前端工程师")
        self.assertEqual(resolved_sal["referenced_context"]["salary_increment"], 2000.0)

        # 快照回退
        restored = memory.rollback(snap_id)
        self.assertEqual(restored["role_name"], "前端工程师")

    def test_l10_telemetry_and_watchdog(self):
        wd = HRTelemetryWatchdog()
        probe = wd.probe_health()
        self.assertEqual(probe["status"], "healthy")
        self.assertEqual(probe["layer"], "L10")
        self.assertTrue(os.path.exists(probe["log_path"]))

        # 测试三态熔断器
        breaker = WatchdogBreaker(failure_threshold=2, recovery_timeout_sec=0.1)
        self.assertEqual(breaker.state, "CLOSED")
        self.assertTrue(breaker.can_execute())

        breaker.record_failure()
        self.assertEqual(breaker.state, "CLOSED")
        breaker.record_failure()
        self.assertEqual(breaker.state, "OPEN")
        self.assertFalse(breaker.can_execute())

        # 弹性执行器执行成功
        res = wd.execute_with_resilience("test_safe_hr_call", lambda: {"status": "ok"})
        self.assertTrue(res["ok"])
        self.assertEqual(res["result"]["status"], "ok")


if __name__ == "__main__":
    unittest.main()

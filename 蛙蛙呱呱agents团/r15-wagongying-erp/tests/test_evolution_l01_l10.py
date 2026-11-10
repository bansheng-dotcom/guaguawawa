# -*- coding: utf-8 -*-
"""tests/test_evolution_l01_l10.py - R15 蛙供应 · ERP与供应链运营官 十维演进双轨集成测试套件。

严格遵循 Universal Agent 10-Stage Evolution SOP v12.0 三大阶段 10 个演进阶梯：
- TestEvolutionRound1 (Stage 1 / L01~L03 基石阶段): 工具实体沙箱、意图解构 Kahn DAG、自愈反思红线拦截
- TestEvolutionRound2 (Stage 2 / L04~L06 深度阶段): ERP_SPEC 领域账本、Anti-Slop 质感去劣化、横向三维决策看板
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
    ERPRuntimeEngine,
    IntentCompiler,
    ReflexiveHealer,
    SpecLedger,
    SupplySlopGuard,
    SupplyScenarioMatrix,
    ERPAssetBundle,
    ERPDiffPatchEngine,
    ERPSessionMemory,
    ERPTelemetryWatchdog,
    WatchdogBreaker,
    TelemetryTracer,
)


class TestEvolutionRound1(unittest.TestCase):
    """第 1 轮升级 (Stage 1 / L01~L03 基石阶段) 集成测试。"""

    def test_l01_runtime_probe_and_conservation_sandbox(self):
        engine = ERPRuntimeEngine()
        probe = engine.probe_health()
        self.assertEqual(probe["status"], "healthy")
        self.assertEqual(probe["layer"], "L01")
        self.assertTrue(probe["probes"]["inventory_conservation_sandbox"])
        self.assertTrue(probe["probes"]["bom_explosion_sandbox"])
        self.assertTrue(probe["probes"]["procurement_over_receipt_sandbox"])

        # 1. 测试库存预计可用量守恒精算 (actual 100 + ordered 50 + planned 20 - reserved 30 = 140)
        cons = engine.calculate_inventory_conservation(100, 50, 20, 30)
        self.assertTrue(cons["is_conserved"])
        self.assertEqual(cons["projected_available"], 140.0)
        self.assertEqual(cons["diff"], 0.0)
        self.assertFalse(cons["has_negative_stock"])

        # 2. 测试负库存刚性拦截判定
        neg = engine.calculate_inventory_conservation(-5, 10, 0, 0, allow_negative_stock=False)
        self.assertTrue(neg["has_negative_stock"])
        self.assertTrue(neg["negative_blocked"])
        self.assertEqual(neg["status"], "BLOCKED")

        # 3. 测试多阶 BOM 展开
        bom_lines = [
            {"item_code": "RAW_A", "qty": 2.0, "scrap_rate": 0.05},
            {"item_code": "RAW_B", "qty": 1.5, "scrap_rate": 0.00},
        ]
        # 成品 10 件：RAW_A = 10 * 2 * 1.05 = 21.0, RAW_B = 10 * 1.5 = 15.0 -> total 36.0
        bom_res = engine.calculate_bom_requirements(bom_lines, finished_good_qty=10.0)
        self.assertTrue(bom_res["valid"])
        self.assertEqual(bom_res["total_gross_material_qty"], 36.0)

        # 4. 采购超收容差刚性判定 (容差 0)
        over = engine.verify_procurement_over_receipt(po_qty=100, receipt_qty=105, tolerance_rate=0.0)
        self.assertTrue(over["is_over_receipt"])
        self.assertFalse(over["allowed"])

    def test_l02_intent_compiler_dag(self):
        compiler = IntentCompiler()
        text = "紧急采购200件芯片物料，需要询价两家供应商并安排排产领料入库"
        entities = compiler.extract_entities(text)
        self.assertTrue(entities["is_urgent"])
        self.assertEqual(entities["quantity"], 200.0)
        self.assertTrue(entities["need_sourcing"])
        self.assertTrue(entities["need_production"])

        # 编译 5 阶段 Kahn DAG
        stages = compiler.compile_intent(text)
        self.assertEqual(len(stages), 5)

        summary = compiler.get_dag_summary(stages)
        self.assertTrue(summary["is_valid_dag"])
        self.assertFalse(summary["has_cycles"])
        self.assertEqual(len(summary["execution_order"]), 5)
        self.assertGreater(summary["total_estimated_hours"], 0)

    def test_l03_reflexive_healer_and_redline(self):
        healer = ReflexiveHealer()

        # 1. 供应链四大红线刚性拦截
        with self.assertRaises(ValueError):
            healer.check_redlines("替客户直接代付款")

        with self.assertRaises(ValueError):
            healer.check_redlines("修改历史账目清空差异")

        with self.assertRaises(ValueError):
            healer.check_redlines("强制超收入库并忽略告警")

        # 2. 自愈反思补齐预计量
        broken_record = {"actual_qty": 50, "ordered_qty": 20, "reserved_qty": 10}
        healed, notes = healer.heal_inventory_record(broken_record)
        self.assertIn("projected_available", healed)
        self.assertEqual(healed["projected_available"], 60.0)
        self.assertTrue(any("重算预计可用量" in n for n in notes))

        # 3. 自愈付款声明注入 handoff
        payment_record = {"amount": 50000, "supplier": "SUP001"}
        healed_p, p_notes = healer.heal_payment_request(payment_record)
        self.assertFalse(healed_p["authorized"])
        self.assertTrue(healed_p["handoff"]["required"])
        self.assertEqual(healed_p["status"], "PENDING_APPROVAL")


class TestEvolutionRound2(unittest.TestCase):
    """第 2 轮升级 (Stage 2 / L04~L06 深度阶段) 集成测试。"""

    def test_l04_spec_ledger(self):
        ledger = SpecLedger()
        spec = ledger.load_spec()
        self.assertEqual(spec["role"], "R15 蛙供应 · ERP 与供应链运营官")
        self.assertEqual(spec["version"], "v12.0")
        self.assertEqual(spec["gates_count"], 8)
        self.assertIn("IRA", spec["north_star_kpis"])
        self.assertIn("BPC", spec["north_star_kpis"])

        # 验证门禁合规检查通过
        good_artifact = {
            "actual_qty": 100,
            "ordered_qty": 50,
            "planned_qty": 20,
            "reserved_qty": 30,
            "projected_available": 140,
            "po_qty": 100,
            "receipt_qty": 100,
            "payment_terms_days": 60,
        }
        res = ledger.verify_gate_compliance("inventory", good_artifact)
        self.assertTrue(res["compliant"])
        self.assertEqual(res["violations_count"], 0)

        # 验证门禁违规拦截
        bad_artifact = {
            "actual_qty": -10,  # 负库存
            "ordered_qty": 0,
            "planned_qty": 0,
            "reserved_qty": 0,
            "projected_available": 50,  # 不守恒
            "po_qty": 100,
            "receipt_qty": 120,  # 超收且无特批
            "payment_terms_days": 200,  # 超账期
        }
        bad_res = ledger.verify_gate_compliance("inventory", bad_artifact)
        self.assertFalse(bad_res["compliant"])
        self.assertGreaterEqual(bad_res["violations_count"], 3)

    def test_l05_slop_guard(self):
        guard = SupplySlopGuard()
        slop_text = "目前库存整体良好，本月按需采购，供应商表现良好，相关细节待定。"
        audit = guard.audit(slop_text)
        self.assertTrue(audit["has_slop"])
        self.assertGreaterEqual(audit["slop_count"], 3)
        self.assertIn("IRA", audit["cleaned_text"])
        self.assertIn("蛙供应", audit["cleaned_text"])
        self.assertGreater(audit["actionability_score"], 0)

        # 干净量化文本直接通过
        clean_text = "经抽盘核验 IRA 达成 99.85%，当前在库安全天数为 15 天，由 R15 蛙供应负责维护。"
        clean_audit = guard.audit(clean_text)
        self.assertFalse(clean_audit["has_slop"])
        self.assertEqual(clean_audit["status"], "PASS")

    def test_l06_scenario_matrix(self):
        matrix = SupplyScenarioMatrix()
        scenarios = matrix.generate(item_code="CPU_SERVER", target_demand_qty=2000.0, base_unit_cost=100.0)
        self.assertEqual(len(scenarios), 3)

        sc_ids = [s["id"] for s in scenarios]
        self.assertIn("SCN_A_JIT", sc_ids)
        self.assertIn("SCN_B_EOQ", sc_ids)
        self.assertIn("SCN_C_BUFFER", sc_ids)

        # 验证方案 B 为推荐方案
        eoq = next(s for s in scenarios if s["id"] == "SCN_B_EOQ")
        self.assertTrue(eoq["is_recommended"])
        self.assertEqual(eoq["roi_score"], 9.4)

        # 验证 Markdown 渲染输出
        md = matrix.render_markdown(scenarios)
        self.assertIn("SCN_B_EOQ", md)
        self.assertIn("⭐ 推荐", md)


class TestEvolutionRound3(unittest.TestCase):
    """第 3 轮升级 (Stage 3 / L07~L10 交付阶段) 集成测试。"""

    def test_l07_asset_bundle(self):
        bundle = ERPAssetBundle()
        paths = bundle.compile_and_save("test_run_bundle_001")
        self.assertTrue(os.path.exists(paths["bundle_file"]))
        self.assertTrue(os.path.exists(paths["sarif_file"]))
        self.assertTrue(os.path.exists(paths["vega_file"]))

        # 验证 SARIF 规范有效性 (OASIS SARIF v2.1.0)
        with open(paths["sarif_file"], "r", encoding="utf-8") as f:
            sarif = json.load(f)
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertEqual(sarif["runs"][0]["tool"]["driver"]["name"], "R15-SupplyChain-Auditor")

    def test_l08_diff_patch_engine(self):
        patcher = ERPDiffPatchEngine()
        old_record = {
            "item_code": "MEM_16G",
            "actual_qty": 100.0,
            "ordered_qty": 50.0,
            "planned_qty": 20.0,
            "reserved_qty": 10.0,
            "projected_available": 160.0,
        }
        # 修改 actual_qty 为 120.0
        new_record = dict(old_record)
        new_record["actual_qty"] = 120.0

        patches = patcher.create_patch(old_record, new_record)
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0]["op"], "replace")
        self.assertEqual(patches[0]["path"], "/actual_qty")
        self.assertEqual(patches[0]["value"], 120.0)

        # 应用补丁并触发增量守恒重算 (120 + 50 + 20 - 10 = 180.0)
        applied = patcher.apply_patch(old_record, patches)
        self.assertEqual(applied["actual_qty"], 120.0)
        self.assertEqual(applied["projected_available"], 180.0)

    def test_l09_session_memory(self):
        memory = ERPSessionMemory()
        # 记录快照
        snap_id = memory.record_snapshot("initial_order", {"item_code": "CPU_XEON", "last_order_id": "PO_20261110_01"})
        self.assertTrue(snap_id.startswith("snap_"))

        # 代词消歧测试
        resolved = memory.disambiguate_query("按刚才第二套方案补货")
        self.assertIn("SCN_B_EOQ", resolved["disambiguated"])
        self.assertEqual(resolved["referenced_context"]["selected_scenario"], "SCN_B_EOQ")

        # 数量追加消歧
        resolved_add = memory.disambiguate_query("把刚才那个订单追加50件")
        self.assertEqual(resolved_add["referenced_context"]["item_code"], "CPU_XEON")
        self.assertEqual(resolved_add["referenced_context"]["added_qty"], 50.0)

        # 快照回退
        restored = memory.rollback(snap_id)
        self.assertEqual(restored["item_code"], "CPU_XEON")

    def test_l10_telemetry_and_watchdog(self):
        wd = ERPTelemetryWatchdog()
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
        res = wd.execute_with_resilience("test_safe_call", lambda: {"status": "ok"})
        self.assertTrue(res["ok"])
        self.assertEqual(res["result"]["status"], "ok")


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""tests/test_evolution_l01_l10.py - R14 蛙交易 · 交易与收入履约官 十维演进双轨集成测试套件。

严格遵循 SOP v12.0 三大阶段 10 个演进阶梯：
- TestEvolutionRound1 (Stage 1 / L01~L03 基石阶段): 工具实体沙箱、意图解构 Kahn DAG、自愈反思红线拦截
- TestEvolutionRound2 (Stage 2 / L04~L06 深度阶段): COMMERCE_SPEC 领域账本、Anti-Slop 质感去劣化、横向三维结算决策看板
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
    CommerceRuntimeEngine,
    IntentCompiler,
    ReflexiveHealer,
    SpecLedger,
    SlopGuard,
    ScenarioMatrix,
    CommerceAssetBundle,
    CommerceDiffPatchEngine,
    CommerceSessionMemory,
    CommerceTelemetryWatchdog,
    WatchdogBreaker,
    TelemetryTracer,
)


class TestEvolutionRound1(unittest.TestCase):
    """第 1 轮升级 (Stage 1 / L01~L03 基石阶段) 集成测试。"""

    def test_l01_runtime_probe_and_balance_sandbox(self):
        engine = CommerceRuntimeEngine()
        probe = engine.probe_health()
        self.assertEqual(probe["status"], "healthy")
        self.assertEqual(probe["layer"], "L01")
        self.assertTrue(probe["probes"]["balance_sandbox"])

        # 1. 测试勾稽平衡沙箱 (Subtotal + Tax - Discount + Shipping)
        items = [
            {"id": "item_1", "price": 100.0, "quantity": 2},
            {"id": "item_2", "price": 50.0, "quantity": 1},
        ]
        # subtotal = 250, tax = 250 * 0.06 = 15, discount = 20, shipping = 10 -> total = 255.0
        bal = engine.calculate_order_balance(items, tax_rate=0.06, discount_amount=20.0, shipping_fee=10.0)
        self.assertTrue(bal["is_balanced"])
        self.assertEqual(bal["subtotal"], 250.0)
        self.assertEqual(bal["tax"], 15.0)
        self.assertEqual(bal["discount"], 20.0)
        self.assertEqual(bal["shipping"], 10.0)
        self.assertEqual(bal["total"], 255.0)
        self.assertEqual(bal["tolerance"], 0.0)

        # 2. 累进计费沙箱测试
        tiers = [
            {"up_to": 100, "unit_amount": 10.0},
            {"up_to": 500, "unit_amount": 8.0},
            {"up_to": None, "unit_amount": 5.0},
        ]
        # 250 units: 100 * 10 + 150 * 8 = 1000 + 1200 = 2200
        grad_res = engine.calculate_graduated_pricing(tiers, 250)
        self.assertEqual(grad_res["total_price"], 2200.0)
        self.assertAlmostEqual(grad_res["effective_unit_price"], 8.8)

        # 3. 计量用量聚合测试与负数防御
        events = [
            {"quantity": 10, "user_id": "u1"},
            {"quantity": 25, "user_id": "u2"},
            {"quantity": 15, "user_id": "u1"},
        ]
        sum_agg = engine.aggregate_usage(events, "sum")
        self.assertEqual(sum_agg["aggregated_value"], 50.0)
        uniq_agg = engine.aggregate_usage(events, "unique_count")
        self.assertEqual(uniq_agg["aggregated_value"], 2.0)

        with self.assertRaises(ValueError):
            engine.aggregate_usage([{"quantity": -5}], "sum")

        # 4. 电子签审计信封校验
        doc_meta = {"document_id": "doc_101", "raw_content": "标准交易服务合同协议"}
        signers = [{"id": "s1", "status": "signed"}, {"id": "s2", "status": "signed"}]
        audit_res = engine.audit_signature_envelope(doc_meta, signers)
        self.assertTrue(audit_res["is_enforceable"])
        self.assertTrue(audit_res["all_signed"])

        # 5. 退款额度测算沙箱
        ref_res = engine.calculate_refund_limits(1000.0, [200.0, 100.0], 500.0)
        self.assertTrue(ref_res["is_allowed"])
        self.assertEqual(ref_res["remaining_refundable"], 700.0)
        self.assertTrue(ref_res["requires_authorization"])

    def test_l02_intent_decompilation(self):
        compiler = IntentCompiler()
        query = "客户准备下单企业版50000元年度订阅套餐，需要签署SLA协议并预约实施会议进行履约"
        stages = compiler.compile_intent(query)
        self.assertEqual(len(stages), 5)
        self.assertEqual(stages[0]["id"], "s01_catalog_pricing")
        self.assertEqual(stages[4]["id"], "s05_fulfillment_workflow")

        summary = compiler.get_dag_summary(stages)
        self.assertTrue(summary["is_valid_dag"])
        self.assertGreater(summary["total_estimated_hours"], 5.0)

        # 提取实体校验
        entities = compiler.extract_entities(query)
        self.assertEqual(entities["amount"], 50000.0)
        self.assertTrue(entities["needs_signature"])
        self.assertTrue(entities["needs_appointment"])
        self.assertTrue(entities["is_subscription"])

    def test_l03_reflexive_healing_and_redlines(self):
        healer = ReflexiveHealer()

        # 1. 越权改账红线拦截 (移交 R03)
        with self.assertRaises(ValueError) as ctx:
            healer.check_redlines("私改结算流水并覆写财务报表")
        self.assertIn("R03", str(ctx.exception))

        # 2. 非法负数红线拦截
        with self.assertRaises(ValueError) as ctx:
            healer.check_redlines("生成负数单价恶意冲正")
        self.assertIn("合规红线", str(ctx.exception))

        # 3. 合规操作放行
        ok_res = healer.check_redlines("为订单生成支付意图并发送电子签信封")
        self.assertFalse(ok_res["blocked"])

        # 4. 退款门禁准入校验
        gate_ok, msg = healer.evaluate_refund_gate(100.0, 15.0)
        self.assertTrue(gate_ok)
        gate_need_auth, msg = healer.evaluate_refund_gate(100.0, 50.0, has_authorization=False)
        self.assertFalse(gate_need_auth)

        # 5. 订单反思自愈
        dirty_order = {
            "currency": "RMB",
            "items": [{"price": 100.0, "quantity": 1}],
            "total": 999.0,  # 破损总额
        }
        healed_order, actions = healer.heal_order_payload(dirty_order)
        self.assertIn("idempotency_key", healed_order)
        self.assertEqual(healed_order["currency"], "CNY")
        self.assertEqual(healed_order["total"], 100.0)
        self.assertGreaterEqual(len(actions), 2)


class TestEvolutionRound2(unittest.TestCase):
    """第 2 轮升级 (Stage 2 / L04~L06 深度阶段) 集成测试。"""

    def test_l04_commerce_spec_ledger(self):
        ledger = SpecLedger()
        spec = ledger.load_spec()
        self.assertEqual(spec["version"], "v12.0")
        self.assertIn("SRR", spec["north_star"])
        self.assertIn("BTA", spec["north_star"])
        self.assertIn("GATE-01", spec["gates"])
        self.assertIn("GATE-08", spec["gates"])

        # 门禁合规检测
        valid_data = {
            "idempotency_key": "idem_12345",
            "subtotal": 100.0,
            "tax": 6.0,
            "discount": 0.0,
            "shipping": 0.0,
            "total": 106.0,
            "currency": "CNY",
            "refund_ratio": 0.15,
            "quantity": 10,
        }
        val_res = ledger.validate_commerce_gate("order", valid_data)
        self.assertTrue(val_res["passed"])
        self.assertEqual(val_res["score"], 100.0)

        # 门禁违规检测
        invalid_data = {
            "idempotency_key": "",
            "subtotal": 100.0,
            "total": 500.0,
            "currency": "XYZ",
            "refund_ratio": 1.5,
            "quantity": -10,
        }
        bad_res = ledger.validate_commerce_gate("order", invalid_data)
        self.assertFalse(bad_res["passed"])
        self.assertGreaterEqual(bad_res["issues_count"], 4)

    def test_l05_slop_guard_and_actionability(self):
        guard = SlopGuard()
        slop_text = "整体正常，交易平稳，退款合规，相关细节待定，视情况而定。"
        audit_res = guard.audit(slop_text)
        self.assertFalse(audit_res["is_clean"])
        self.assertGreaterEqual(audit_res["slop_count"], 3)

        cleaned = guard.clean(slop_text)
        self.assertNotIn("整体正常", cleaned)
        self.assertNotIn("相关细节待定", cleaned)
        self.assertIn("蛙交易", cleaned)
        self.assertIn("99.85%", cleaned)

    def test_l06_scenario_matrix_generation(self):
        sc_matrix = ScenarioMatrix()
        scenarios = sc_matrix.generate("ORD_TEST_001", 50000.0)
        self.assertEqual(len(scenarios), 3)

        ids = [s["id"] for s in scenarios]
        self.assertIn("minimal_instant", ids)
        self.assertIn("steady_milestone", ids)
        self.assertIn("flexible_metered", ids)

        # Markdown 看板渲染
        md = sc_matrix.render_markdown(scenarios)
        self.assertIn("steady_milestone", md)
        self.assertIn("蛙交易", md)


class TestEvolutionRound3(unittest.TestCase):
    """第 3 轮升级 (Stage 3 / L07~L10 交付阶段) 集成测试。"""

    def test_l07_asset_bundle_and_sarif_export(self):
        bundle_eng = CommerceAssetBundle()
        sarif = bundle_eng.generate_sarif([
            {"rule_id": "COMM001", "level": "error", "message": "缺失交易幂等键", "target": "order_meta"},
            {"rule_id": "COMM002", "level": "error", "message": "财务勾稽平衡破损", "target": "order_meta"},
        ])
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertEqual(len(sarif["runs"][0]["results"]), 2)

        vega = bundle_eng.generate_vega_spec()
        self.assertEqual(vega["$schema"], "https://vega.github.io/schema/vega-lite/v5.json")

        # 真实落盘导出
        exported = bundle_eng.export_bundle("test_run_bundle", {"order_id": "ORD_TEST_999", "total": 1000.0})
        self.assertTrue(os.path.exists(exported["bundle"]))
        self.assertTrue(os.path.exists(exported["sarif"]))
        self.assertTrue(os.path.exists(exported["vega"]))

    def test_l08_diff_patch_engine(self):
        diff_eng = CommerceDiffPatchEngine()
        old_order = {
            "order_id": "ORD_001",
            "items": [{"price": 100.0, "quantity": 1}],
            "tax": 6.0,
            "discount": 0.0,
            "shipping": 0.0,
            "total": 106.0,
        }
        updates = {"discount": 10.0}
        patch_res = diff_eng.patch_order_items(old_order, updates)
        patched = patch_res["patched_order"]
        self.assertEqual(patched["discount"], 10.0)
        self.assertEqual(patched["total"], 96.0)
        self.assertEqual(patch_res["patch_ops_count"], 1)

    def test_l09_session_memory_and_disambiguation(self):
        mem = CommerceSessionMemory()
        mem.update_slot("current_order_id", "ORD_20261110_888")

        res1 = mem.disambiguate_query("按刚才第二套方案推进订单")
        self.assertEqual(res1["resolved_scenario"], "steady_milestone")

        res2 = mem.disambiguate_query("把刚才那个订单增加一件商品")
        self.assertIn("ORD_20261110_888", res2["resolved_query"])

        # 快照与回滚测试
        snap_id = mem.create_snapshot("pre_change")
        mem.update_slot("current_order_id", "ORD_MODIFIED")
        self.assertEqual(mem.state["slots"]["current_order_id"], "ORD_MODIFIED")

        ok = mem.rollback(snap_id)
        self.assertTrue(ok)
        self.assertEqual(mem.state["slots"]["current_order_id"], "ORD_20261110_888")

    def test_l10_telemetry_and_watchdog_breaker(self):
        breaker = WatchdogBreaker(failure_threshold=2, recovery_time_sec=0.1)

        def fail_func():
            raise ValueError("simulated network error")

        # 连续失败触发熔断
        with self.assertRaises(ValueError):
            breaker.call(fail_func)
        with self.assertRaises(ValueError):
            breaker.call(fail_func)

        self.assertEqual(breaker.state, "OPEN")
        # 熔断打开后快速失败
        with self.assertRaises(RuntimeError) as ctx:
            breaker.call(fail_func)
        self.assertIn("快速失败", str(ctx.exception))

        # 遥测追踪落盘测试
        wd = CommerceTelemetryWatchdog()
        span = wd.tracer.record_span("test_span", 15.2, "OK", {"test": True})
        self.assertEqual(span["status"], "OK")
        self.assertTrue(os.path.exists(wd.tracer.log_file))


if __name__ == "__main__":
    unittest.main()

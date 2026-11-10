# -*- coding: utf-8 -*-
"""tests/test_evolution_l01_l10.py - R08 十维演进元模型配套双轨集成测试套件。"""
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
    PrototypeRuntimeEngine,
    IntentCompiler,
    PrototypeReflexiveHealer,
)


class TestEvolutionRound1(unittest.TestCase):
    """第 1 轮演进 (L01~L03) 单元与集成测试。"""

    def test_l01_runtime_probe(self):
        eng = PrototypeRuntimeEngine()
        probe = eng.probe_health()
        self.assertEqual(probe["status"], "healthy")
        self.assertEqual(probe["layer"], "L01")
        self.assertEqual(probe["capability_status"], "real")

    def test_l01_html_verification(self):
        eng = PrototypeRuntimeEngine()
        good_html = """<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 助手落地页</title>
</head>
<body>
    <h1>极速构建原型</h1>
    <form action="https://formspree.io/f/xyz" method="POST">
        <input type="email" name="email" required placeholder="请输入您的邮箱" aria-label="用户邮箱">
        <button type="submit">立即加入等候名单</button>
    </form>
</body>
</html>"""
        res = eng.verify_html_artifact(good_html)
        self.assertTrue(res["ok"])
        self.assertEqual(res["form_count"], 1)
        self.assertEqual(res["input_count"], 1)
        self.assertTrue(res["has_viewport"])

        # 缺少 CTA 与表单端点不合规拦截
        bad_html = "<html><body><form action='http://insecure.site'></form></body></html>"
        bad_res = eng.verify_html_artifact(bad_html)
        self.assertFalse(bad_res["ok"])

    def test_l02_intent_decompilation(self):
        compiler = IntentCompiler()
        query = "请帮我实现一个 AI 写作助手落地页，需要收集邮箱并适配移动端"
        res = compiler.decompile(query)
        self.assertTrue(res["ok"])
        self.assertTrue(res["dag"]["is_dag"])
        self.assertIn("stage_01_slice", res["dag"]["topological_order"])
        self.assertIn("stage_05_qa_handoff", res["dag"]["topological_order"])
        self.assertGreater(res["dag"]["total_estimated_hours"], 5.0)

    def test_l03_reflexive_healing(self):
        healer = PrototypeReflexiveHealer()
        # 缺少 fail criteria 和 handoff 的缺陷输入
        broken_mvp = {
            "assumption": {"risk_type": "value", "statement": "用户愿意付费"},
            "mvp": {"goal": "收集邮箱"},
            "experiment": [{"method": "landing", "metric": "emails"}],
            "criteria": {"success": "3天10个邮箱"},
        }
        res = healer.audit_and_heal("mvp", broken_mvp)
        self.assertTrue(res["ok"])
        self.assertGreater(res["healed_count"], 0)
        self.assertIn("fail", res["healed_data"]["criteria"])
        self.assertIn("handoff", res["healed_data"])

        # 触犯边界红线（生产工程且不声明 handoff）
        violated_mvp = {
            "title": "生产级高可用跨机房容灾部署方案",
        }
        v_res = healer.audit_and_heal("mvp", violated_mvp)
        self.assertFalse(v_res["ok"])
        self.assertEqual(v_res["reflexion_grade"], "REJECTED_BY_CRITIC")


class TestEvolutionRound2(unittest.TestCase):
    """第 2 轮演进 (L04~L06) 单元与集成测试。"""

    def test_l04_tech_spec_ledger(self):
        from engines.tech_spec_ledger import TechSpecLedger
        ledger = TechSpecLedger()
        spec = ledger.load_spec()
        self.assertTrue(spec["tokens"]["colors"])
        self.assertIn("primary", spec["tokens"]["colors"])
        self.assertIn("mobile", spec["tokens"]["breakpoints"])
        css = ledger.export_css_variables()
        self.assertIn("--color-primary", css)
        flutter = ledger.export_flutter_theme()
        self.assertIn("ThemeData", flutter)

    def test_l05_prototype_slopguard(self):
        from engines.prototype_slop_guard import PrototypeSlopGuard
        guard = PrototypeSlopGuard()
        dirty_text = "核心表单正在研发，此处界面稍后补充，敬请期待！"
        res = guard.audit_text(dirty_text)
        self.assertFalse(res["is_clean"])
        self.assertGreater(res["issues_found"], 0)
        self.assertNotIn("稍后补充", res["purified_text"])

        # 嵌套 JSON 工件递归净化
        dirty_artifact = {
            "title": "AI 助手",
            "sections": [
                {"name": "主功能", "desc": "视情况而定"},
                {"name": "附录", "desc": "TODO: 实现业务逻辑"},
            ]
        }
        purified, cnt = guard.purify_artifact(dirty_artifact)
        self.assertEqual(cnt, 2)
        self.assertNotIn("视情况而定", str(purified))

    def test_l06_scenario_matrix(self):
        from engines.scenario_matrix import ScenarioMatrix
        mat = ScenarioMatrix()
        res = mat.generate_matrix("智能营销H5")
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["scenarios"]), 3)
        self.assertEqual(res["recommended_scenario"], "standard_component")
        self.assertIn("tradeoff_matrix", res)


class TestEvolutionRound3(unittest.TestCase):
    """第 3 轮演进 (L07~L10) 单元与集成测试。"""

    def test_l07_asset_bundle(self):
        from engines.asset_bundle import AssetBundle
        bundle_eng = AssetBundle()
        res = bundle_eng.export_bundle("test_run_bundle", {"components": [{"name": "Header"}]})
        self.assertTrue(res["ok"])
        self.assertTrue(os.path.exists(res["bundle_path"]))
        self.assertTrue(os.path.exists(res["ast_path"]))
        self.assertTrue(os.path.exists(res["sarif_path"]))

    def test_l08_diff_patch_engine(self):
        from engines.diff_patch_engine import DiffPatchEngine
        patch_eng = DiffPatchEngine()
        doc1 = {"theme": {"color": "blue", "radius": "4px"}}
        doc2 = {"theme": {"color": "green", "radius": "4px", "shadow": "md"}}
        patch = patch_eng.create_patch(doc1, doc2)
        self.assertGreaterEqual(len(patch), 2)
        # 补丁应用还原测试
        applied = patch_eng.apply_patch(doc1, patch)
        self.assertEqual(applied["theme"]["color"], "green")
        self.assertEqual(applied["theme"]["shadow"], "md")

    def test_l09_session_memory(self):
        from engines.session_memory import PrototypeSessionMemory
        mem = PrototypeSessionMemory()
        # 快照保存与回滚
        v = mem.save_snapshot("v1.0", {"layout": "grid"})
        mem.save_snapshot("v2.0", {"layout": "flex"})
        rolled = mem.rollback_to("v1.0")
        self.assertIsNotNone(rolled)
        self.assertEqual(rolled["layout"], "grid")
        # 代词消歧
        resolved = mem.resolve_pronouns("把刚才的落地页加上移动端适配")
        self.assertTrue(resolved["had_ambiguity"])
        self.assertIn("基于上下文已锁定实体", resolved["disambiguated_query"])

    def test_l10_watchdog_and_telemetry(self):
        from engines.telemetry_watchdog import WatchdogBreaker, TelemetryTracer
        breaker = WatchdogBreaker(failure_threshold=2)
        tracer = TelemetryTracer()

        # 遥测记录落盘
        rec = tracer.record_span("r08_test_span", 12.5, "SUCCESS")
        self.assertEqual(rec["name"], "r08_test_span")
        self.assertEqual(rec["status"], "SUCCESS")

        # 熔断器正常调用
        res = breaker.call(lambda x: x * 2, 21)
        self.assertEqual(res, 42)

        # 模拟重试机制
        attempts = 0
        def flake():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ValueError("transient failure")
            return "recovered"

        retry_res = breaker.execute_with_retry(flake, max_retries=3, base_delay=0.01)
        self.assertEqual(retry_res, "recovered")


if __name__ == "__main__":
    unittest.main()

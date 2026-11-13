# -*- coding: utf-8 -*-
"""tests/test_evolution_l01_l10.py - R10 视觉设计官 · 十维演进元模型配套双轨集成测试套件。"""
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
    VisualRuntimeEngine,
    VisualIntentCompiler,
    VisualReflexiveHealer,
    DesignSpecLedger,
    SlopGuard,
    VisualScenarioMatrix,
    VisualAssetBundle,
    VisualDiffPatchEngine,
    VisualSessionMemory,
    WatchdogBreaker,
    TelemetryTracer,
)


class TestEvolutionRound1(unittest.TestCase):
    """第 1 轮演进 (L01~L03) 单元与集成测试。"""

    def test_l01_runtime_probe(self):
        eng = VisualRuntimeEngine()
        probe = eng.probe_health()
        self.assertEqual(probe["status"], "healthy")
        self.assertEqual(probe["layer"], "L01")
        self.assertEqual(probe["capability_status"], "real")
        self.assertTrue(probe["preferred_engine"])

    def test_l01_visual_artifact_verification(self):
        eng = VisualRuntimeEngine()
        spec_dict = {"concept": "商业耳机", "style": "cyberpunk"}
        res = eng.verify_visual_artifact(spec_dict)
        self.assertTrue(res["ok"])
        self.assertEqual(res["style"], "cyberpunk")

        # 缺少核心要素拦截
        bad_res = eng.verify_visual_artifact({})
        self.assertFalse(bad_res["ok"])

    def test_l02_intent_decompilation(self):
        compiler = VisualIntentCompiler()
        query = "为降噪耳机设计一张赛博科技风的宣传海报，突出质感"
        res = compiler.decompile(query)
        self.assertTrue(res["ok"])
        self.assertEqual(res["layer"], "L02")
        self.assertEqual(res["extracted_entities"]["style"], "cyberpunk")
        self.assertEqual(res["extracted_entities"]["aspect_ratio"], "9:16")

        dag = res["dag"]
        self.assertTrue(dag["is_dag"])
        self.assertEqual(dag["node_count"], 5)
        self.assertIn("stage_01_brief_analysis", dag["topological_order"])
        self.assertIn("stage_05_vlm_critic", dag["topological_order"])
        self.assertGreater(dag["total_estimated_hours"], 3.0)

    def test_l03_reflexive_healing(self):
        healer = VisualReflexiveHealer()
        # 1. 缺陷工件自愈
        broken_prompt = {"prompt": "高端耳机海报"}
        res = healer.audit_and_heal("prompt", broken_prompt)
        self.assertTrue(res["ok"])
        self.assertGreater(res["healed_count"], 0)
        self.assertIn("negative_prompt", res["healed_data"])
        self.assertIn("style_locks", res["healed_data"])
        self.assertEqual(res["healed_data"]["media"], "image")

        # 2. 职能越界硬红线拦截
        violated_data = {
            "title": "生产级高可用跨机房容灾部署方案",
            "prompt": "微服务与k8s集群架构图"
        }
        v_res = healer.audit_and_heal("prompt", violated_data)
        self.assertFalse(v_res["ok"])
        self.assertEqual(v_res["reflexion_grade"], "REJECTED_BY_CRITIC")
        self.assertGreater(len(v_res["violations"]), 0)


class TestEvolutionRound2(unittest.TestCase):
    """第 2 轮演进 (L04~L06) 单元与集成测试。"""

    def test_l04_spec_ledger(self):
        ledger = DesignSpecLedger()
        spec = ledger.load_spec()
        self.assertTrue(spec["tokens"]["colors"])
        self.assertIn("primary", spec["tokens"]["colors"])
        self.assertIn("accent", spec["tokens"]["colors"])
        self.assertIn("mobile", spec["tokens"]["breakpoints"])

        css = ledger.export_css_variables()
        self.assertIn("--color-primary", css)
        self.assertIn("--color-accent", css)

        flutter = ledger.export_flutter_theme()
        self.assertIn("ThemeData", flutter)

    def test_l05_slop_guard(self):
        dirty_text = "核心表单正在设计，此处界面稍后补充，敬请期待！"
        res = SlopGuard.audit_text(dirty_text)
        self.assertFalse(res["is_clean"])
        self.assertGreater(res["issues_found"], 0)
        self.assertNotIn("稍后补充", res["purified_text"])

        # 递归净化测试
        dirty_artifact = {
            "title": "海报配置",
            "desc": "视情况而定",
            "sections": ["TODO: 补充文字", "此处界面稍后补充"]
        }
        purified, cnt = SlopGuard.purify_artifact(dirty_artifact)
        self.assertGreaterEqual(cnt, 2)
        self.assertNotIn("视情况而定", str(purified))

    def test_l06_scenario_matrix(self):
        matrix_eng = VisualScenarioMatrix()
        res = matrix_eng.generate_matrix("智能数码降噪耳机")
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["scenarios"]), 3)
        self.assertEqual(res["recommended_scenario"], "commercial_editorial")
        self.assertIn("tradeoff_matrix", res)


class TestEvolutionRound3(unittest.TestCase):
    """第 3 轮演进 (L07~L10) 单元与集成测试。"""

    def test_l07_asset_bundle(self):
        bundle_eng = VisualAssetBundle()
        res = bundle_eng.export_bundle("r10_test_run", {"tokens": {"primary": "#0F172A"}})
        self.assertTrue(res["ok"])
        self.assertTrue(os.path.exists(res["bundle_path"]))
        self.assertTrue(os.path.exists(res["ast_path"]))
        self.assertTrue(os.path.exists(res["sarif_path"]))

    def test_l08_diff_patch_engine(self):
        patch_eng = VisualDiffPatchEngine()
        doc1 = {"theme": {"primary": "#0F172A", "radius": "4px"}}
        doc2 = {"theme": {"primary": "#22D3EE", "radius": "4px", "shadow": "md"}}
        patch = patch_eng.create_patch(doc1, doc2)
        self.assertGreaterEqual(len(patch), 2)

        applied = patch_eng.apply_patch(doc1, patch)
        self.assertEqual(applied["theme"]["primary"], "#22D3EE")
        self.assertEqual(applied["theme"]["shadow"], "md")

    def test_l09_session_memory(self):
        mem = VisualSessionMemory()
        v1 = mem.save_snapshot("v1.0", {"layout": "grid", "color": "dark"})
        v2 = mem.save_snapshot("v2.0", {"layout": "flex", "color": "light"})
        rolled = mem.rollback_to("v1.0")
        self.assertIsNotNone(rolled)
        self.assertEqual(rolled["layout"], "grid")

        # 代词消歧
        resolved = mem.resolve_pronouns("把刚才第二套方案调整")
        self.assertTrue(resolved["had_ambiguity"])
        self.assertIn("基于上下文已锁定实体", resolved["disambiguated_query"])

    def test_l10_watchdog_and_telemetry(self):
        breaker = WatchdogBreaker(failure_threshold=2)
        tracer = TelemetryTracer()

        span = tracer.record_span("r10_unit_test", 15.6, "SUCCESS")
        self.assertEqual(span["name"], "r10_unit_test")
        self.assertEqual(span["status"], "SUCCESS")

        res = breaker.call(lambda x: x + 10, 32)
        self.assertEqual(res, 42)

        attempts = 0
        def flake():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ValueError("temporary error")
            return "recovered"

        retry_res = breaker.execute_with_retry(flake, max_retries=3, base_delay=0.01)
        self.assertEqual(retry_res, "recovered")


if __name__ == "__main__":
    unittest.main()

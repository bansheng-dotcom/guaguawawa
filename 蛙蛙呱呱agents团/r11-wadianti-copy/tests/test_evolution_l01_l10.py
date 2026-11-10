# -*- coding: utf-8 -*-
"""tests/test_evolution_l01_l10.py - R11 蛙点题 · 内容主笔与文案运营 十维演进双轨集成测试套件。"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(AGENTS)
for p in (HERE, AGENTS, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from engines import (
    CopyRuntimeEngine,
    IntentDAGCompiler,
    CopyReflexiveHealer,
    CopySpecLedger,
    CopySlopGuard,
    ScenarioMatrix,
    ContentAssetBundle,
    ContentDiffPatchEngine,
    ContentSessionMemory,
    ContentTelemetryWatchdog,
)


class TestEvolutionRound1(unittest.TestCase):
    """第 1 轮升级 (L01~L03 基石阶段) 集成测试。"""

    def test_l01_runtime_probe_and_ast(self):
        engine = CopyRuntimeEngine()
        probe = engine.probe_health()
        self.assertEqual(probe["status"], "healthy")
        self.assertTrue(probe["ast_parser_healthy"])
        self.assertTrue(probe["linter_healthy"])
        self.assertTrue(probe["counter_healthy"])
        self.assertTrue(probe["sensitive_filter_healthy"])

        sample_md = "# 黄金标题\n\n> 核心引述\n\n这是正文第一段，包含 English 单词。\n\n* 列表1\n* 列表2"
        ast_res = engine.parse_ast(sample_md)
        self.assertEqual(ast_res["total_nodes"], 5)
        self.assertTrue(ast_res["has_headings"])

    def test_l01_typography_lint_and_format(self):
        engine = CopyRuntimeEngine()
        raw = "这里有English单词和标点,需要规范化!!!"
        lint = engine.lint_typography(raw)
        self.assertFalse(lint["clean"])
        self.assertGreaterEqual(lint["issues_count"], 2)

        formatted = engine.format_typography("这里有English单词和中文，紧贴123数字。")
        self.assertIn("English", formatted)

        counts = engine.count_metrics("这是一段测试中文，大约二十个字左右。")
        self.assertGreater(counts["chinese_chars"], 10)
        self.assertGreater(counts["estimated_silent_reading_minutes"], 0)

    def test_l02_intent_decompilation(self):
        compiler = IntentDAGCompiler()
        query = "写一篇关于企业AI工具落地的长文，提炼小红书和微信公众号的核心卖点与金句"
        res = compiler.decompile_intent(query)
        self.assertTrue(res["ok"])
        self.assertIn("小红书", res["detected_channels"])
        self.assertIn("微信公众号", res["detected_channels"])

        dag = res["dag"]
        self.assertTrue(dag["is_dag"])
        self.assertEqual(len(dag["topological_order"]), 5)
        self.assertEqual(dag["topological_order"][0], "node_01_strategy")
        self.assertEqual(dag["topological_order"][-1], "node_05_platform_adapt")
        self.assertGreater(dag["total_estimated_hours"], 0)

    def test_l03_reflexive_healing_and_redlines(self):
        healer = CopyReflexiveHealer()
        dirty_packet = {
            "title": "测试违规文案",
            "content": "我们是国家级最佳第一品牌，提供100%收益方案！此处待定，稍后补充正文。这篇文章可以发布了。",
        }
        violations = healer.audit_redlines(dirty_packet)
        self.assertGreaterEqual(len(violations), 3)
        self.assertTrue(any("publish_unauthorized" in v for v in violations))
        self.assertTrue(any("forbidden_advertising_terms" in v for v in violations))
        self.assertTrue(any("ai_placeholder" in v for v in violations))

        healed = healer.audit_and_heal("article", dirty_packet)
        self.assertTrue(healed["is_healed"])
        self.assertTrue(healed["is_clean"])
        self.assertNotIn("国家级", healed["healed_data"]["content"])
        self.assertNotIn("可以发布了", healed["healed_data"]["content"])
        self.assertIn("【行动建议】", healed["healed_data"]["content"])


class TestEvolutionRound2(unittest.TestCase):
    """第 2 轮升级 (L04~L06 深度阶段) 集成测试。"""

    def test_l04_spec_ledger(self):
        ledger = CopySpecLedger()
        spec = ledger.load_spec()
        self.assertTrue(spec["spec_loaded"])
        self.assertEqual(len(spec["rules"]["release_gates"]), 8)
        self.assertIn("微信公众号", spec["rules"]["platform_matrix"])

        # 校验文案门禁
        clean_article = "这是用于测试发布的专业合规长文。\n\n" * 120 + "欢迎大家点击关注并留言交流。"
        val_res = ledger.validate_content(clean_article, title="专业长文测试标题", channel="微信公众号")
        self.assertEqual(val_res["total_gates"], 8)
        self.assertTrue(val_res["all_passed"], f"Failed: {val_res['failed_gates']}")

    def test_l05_slop_guard(self):
        guard = CopySlopGuard()
        bad_text = "总而言之，毋庸置疑，随着科技的飞速发展，转化率得到了大幅提升！"
        audit = guard.audit_text(bad_text)
        self.assertFalse(audit["is_clean"])
        self.assertEqual(audit["slop_count"], 3)
        self.assertLess(audit["slop_score"], 80.0)

        polished, count = guard.polish(bad_text)
        self.assertEqual(count, 3)
        self.assertNotIn("总而言之", polished)
        self.assertNotIn("毋庸置疑", polished)
        self.assertNotIn("随着科技的飞速发展", polished)
        self.assertIn("核心结论是：", polished)

    def test_l06_scenario_matrix(self):
        matrix = ScenarioMatrix()
        res = matrix.generate_matrix("AI内容运营与知识沉淀")
        self.assertEqual(res["scenario_count"], 3)
        ids = [s["id"] for s in res["scenarios"]]
        self.assertListEqual(ids, ["lean_datacopy", "story_empathy", "viral_conversion"])
        self.assertIn("极简数据流", res["comparison_matrix_md"])
        self.assertIn("爆款转化流", res["comparison_matrix_md"])


class TestEvolutionRound3(unittest.TestCase):
    """第 3 轮升级 (L07~L10 交付阶段) 集成测试。"""

    def test_l07_asset_bundle(self):
        tmp_dir = os.path.join(HERE, "workspace", "tmp", "test_bundles")
        bundle_exporter = ContentAssetBundle(workspace_dir=tmp_dir)
        content_mock = {
            "title": "测试文案资产",
            "content": "测试正文长文内容",
            "issues": ["建议优化排版"],
            "tags": ["#测试", "#运营"],
        }
        res = bundle_exporter.export_bundle("run_unit_test", content_mock)
        self.assertTrue(os.path.exists(res["bundle_path"]))
        self.assertTrue(os.path.exists(res["sarif_path"]))
        self.assertTrue(os.path.exists(res["platform_meta_path"]))

        with open(res["sarif_path"], "r", encoding="utf-8") as f:
            sarif = json.load(f)
            self.assertEqual(sarif["version"], "2.1.0")

    def test_l08_diff_patch_engine(self):
        engine = ContentDiffPatchEngine()
        old_state = {"title": "旧标题", "tone": "商务", "cta": "点击购买"}
        new_state = {"title": "爆款新标题", "tone": "情感", "cta": "点击购买", "new_tag": "vip"}

        patches = engine.create_patch(old_state, new_state)
        self.assertEqual(len(patches), 3)

        applied = engine.apply_patch(old_state, patches)
        self.assertEqual(applied["title"], "爆款新标题")
        self.assertEqual(applied["new_tag"], "vip")

        # 段落局部更新
        full_text = "段落一\n\n段落二\n\n段落三"
        patched = engine.patch_paragraph(full_text, 1, "更新后的第二段")
        self.assertEqual(patched, "段落一\n\n更新后的第二段\n\n段落三")

    def test_l09_session_memory(self):
        tmp_file = os.path.join(HERE, "workspace", "tmp", "test_session_state.json")
        mem = ContentSessionMemory(state_file=tmp_file)
        snap1 = mem.record_turn("写一篇小红书种草文案", {"topic": "智能体", "channel": "小红书笔记"})
        self.assertEqual(mem.current_state["slots"]["topic"], "智能体")

        # 代词消歧
        resolved = mem.resolve_pronouns("按刚才第二套故事风格改写")
        self.assertTrue(resolved["had_ambiguity"])
        self.assertEqual(resolved["resolved_slots"]["style"], "故事共鸣流")
        self.assertEqual(resolved["resolved_slots"]["topic"], "智能体")

        # 快照与回滚
        snap2 = mem.record_turn("换成微信公众号长文", {"channel": "微信公众号"})
        self.assertEqual(mem.current_state["slots"]["channel"], "微信公众号")
        self.assertTrue(mem.rollback(snap1))
        self.assertEqual(mem.current_state["slots"]["channel"], "小红书笔记")

    def test_l10_telemetry_watchdog(self):
        tmp_telemetry = os.path.join(HERE, "workspace", "tmp", "test_telemetry.jsonl")
        wd = ContentTelemetryWatchdog(failure_threshold=2, reset_timeout_sec=0.5, telemetry_file=tmp_telemetry)
        self.assertEqual(wd.get_state(), "CLOSED")

        def normal_task():
            return "OK"

        res = wd.execute_with_guard(normal_task)
        self.assertEqual(res, "OK")
        self.assertTrue(os.path.exists(tmp_telemetry))

        # 触发熔断
        def broken_task():
            raise ValueError("下游接口故障")

        for _ in range(2):
            try:
                wd.execute_with_guard(broken_task)
            except ValueError:
                pass

        self.assertEqual(wd.get_state(), "OPEN")


if __name__ == "__main__":
    unittest.main()

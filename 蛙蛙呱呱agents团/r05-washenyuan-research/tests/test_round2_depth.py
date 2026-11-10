# -*- coding: utf-8 -*-
"""R05 第 2 轮升级验收契约（专业深度阶段 L04~L06）。

本轮契约针对 R05 蛙深远真实体检病灶：
- L04：RESEARCH_SPEC.md 只是给人看的散文，ledger.py 把阈值写死在代码里，
  没有机器可读 SSOT、没有 8 维发布门禁与可评估算子；
- L05：SlopGuard 只有 5 条正则、无量化证据密度/行动力/等级，也无法阻断
  “相关细节待定”等占位套话与缺失 DRI 的研报；
- L06：情景矩阵的三档份额全部硬编码，没有 MCDA 权重、ROI 矩阵与推荐序，
  人类仍拿不到可横向权衡的决策看板。
"""
import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
for _p in (_HERE, _ROLE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engines.spec_ledger import ResearchSpecLedger  # noqa: E402
from engines.slop_guard import ResearchSlopGuard  # noqa: E402
from engines.scenario_matrix import ScenarioMatrixExplorer  # noqa: E402

TMP = os.path.join(_ROLE, "workspace", "tmp")


class TestL04SpecLedger(unittest.TestCase):
    """L04 领域账本层：机器可读 SSOT + 8 维发布门禁。"""

    def test_default_spec_is_machine_readable(self):
        spec = ResearchSpecLedger().load()
        self.assertEqual(spec["version"], "2.0.0")
        self.assertAlmostEqual(spec["tam_variance_max"], 0.30, places=2)
        self.assertEqual(spec["hhi"]["moderate_max"], 2500)
        self.assertAlmostEqual(spec["evidence_tiers"]["tier_1"]["min_confidence"], 0.90, places=2)
        self.assertEqual(spec["north_star"]["target"], 1.0)

    def test_gates_are_eight_and_weighted(self):
        ledger = ResearchSpecLedger()
        gates = ledger.gates()
        self.assertEqual(len(gates), 8)
        ids = {g["id"] for g in gates}
        self.assertEqual(ids, {
            "evidence_coverage", "tier0_free", "tam_convergence", "hhi_declared",
            "scenario_three", "redline_clean", "slop_score", "bundle_manifest",
        })
        self.assertAlmostEqual(sum(g["weight"] for g in gates), 1.0, places=6)
        for g in gates:
            self.assertIn(g["rule"], ("min", "max"))
            self.assertIn(g["metric"], g)

    def test_spec_is_dynamic_not_hardcoded(self):
        os.makedirs(TMP, exist_ok=True)
        spec_path = os.path.join(TMP, "spec_override.md")
        payload = {
            "version": "9.9.9",
            "tam_variance_max": 0.18,
            "hhi": {"competitive_max": 1400, "moderate_max": 2400, "oligopoly_min": 2400},
            "evidence_tiers": {"tier_1": {"sources_required": 1, "min_confidence": 0.9}},
            "gates": [],
        }
        with open(spec_path, "w", encoding="utf-8") as f:
            f.write("# override\n\n```json\n" +
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n```\n")
        spec = ResearchSpecLedger(spec_path).load()
        self.assertEqual(spec["version"], "9.9.9")
        self.assertAlmostEqual(spec["tam_variance_max"], 0.18, places=2)
        self.assertEqual(spec["hhi"]["moderate_max"], 2400)

    def test_evaluate_and_export(self):
        ledger = ResearchSpecLedger()
        good = ledger.evaluate({"metrics": {
            "evidence_coverage": 1.0, "tier0_count": 0, "tam_variance": 0.1,
            "hhi_declared": 1, "scenario_count": 3, "redline_clean": 1,
            "slop_score": 92, "bundle_manifest": 1,
        }})
        self.assertTrue(good["passed"])
        self.assertAlmostEqual(good["score"], 100.0, places=2)
        self.assertEqual(good["verdict"], "PASS")
        self.assertEqual(len(good["gates"]), 8)

        bad = ledger.evaluate({"metrics": {
            "evidence_coverage": 0.4, "tier0_count": 2, "tam_variance": 0.55,
            "hhi_declared": 0, "scenario_count": 1, "redline_clean": 0,
            "slop_score": 40, "bundle_manifest": 0,
        }})
        self.assertFalse(bad["passed"])
        self.assertLess(bad["score"], 100.0)
        failed = {g["id"] for g in bad["gates"] if not g["ok"]}
        self.assertEqual(failed, {
            "evidence_coverage", "tier0_free", "tam_convergence", "hhi_declared",
            "scenario_three", "redline_clean", "slop_score", "bundle_manifest",
        })

        os.makedirs(TMP, exist_ok=True)
        out = os.path.join(TMP, "spec_snapshot.json")
        ledger.export_json(out)
        self.assertTrue(os.path.exists(out))
        with open(out, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
        self.assertEqual(snapshot["version"], "2.0.0")


class TestL05SlopGuard(unittest.TestCase):
    """L05 质感去劣化：套话清洗 + 量化证据 + DRI 强制绑定。"""

    def test_audit_reports_quality_dimensions(self):
        guard = ResearchSlopGuard()
        audit = guard.audit_text(
            "市场整体良好，未来可期。TAM 120 亿元，增速 18.5%（来源 S1/S2）。")
        self.assertFalse(audit["is_clean"])
        self.assertGreater(audit["evidence_density"], 0)
        self.assertLess(audit["score"], 100)
        self.assertIn(audit["grade"], ("A", "B", "C", "D"))
        self.assertGreaterEqual(audit["slop_hits"], 2)
        self.assertIn("actionability", audit)

    def test_enforce_blocks_placeholders_and_missing_evidence(self):
        guard = ResearchSlopGuard()
        report = guard.enforce_quality("市场整体良好，相关细节待定。")
        self.assertFalse(report["ok"])
        self.assertIn("PENDING_PLACEHOLDER", report["blocking_issues"])
        self.assertIn("NO_QUANTIFIED_EVIDENCE", report["blocking_issues"])
        self.assertNotIn("整体良好", report["polished"])
        self.assertNotIn("相关细节待定", report["polished"])
        self.assertEqual(report["dri"], "蛙深远")

    def test_enforce_passes_quantified_report_with_dri(self):
        guard = ResearchSlopGuard()
        text = ("TAM 120 亿元（来源 S1/S2），重点城市渗透率 8.5%，"
                "获客成本回收期 7.5 个月，责任人 DRI：蛙深远。")
        report = guard.enforce_quality(text)
        self.assertTrue(report["ok"], report["blocking_issues"])
        self.assertEqual(report["blocking_issues"], [])
        self.assertGreaterEqual(report["score"], 80)
        self.assertIn("DRI", report["polished"])

    def test_backward_compatible_polish(self):
        guard = ResearchSlopGuard()
        polished, count = guard.polish("前景极其广阔，业内公认，颠覆式创新，大力推进！")
        self.assertGreaterEqual(count, 3)
        self.assertNotIn("前景极其广阔", polished)


class TestL06ScenarioMatrix(unittest.TestCase):
    """L06 横向决策层：MCDA 权重 + ROI 矩阵 + 推荐序。"""

    def test_mcda_weights_and_scores(self):
        matrix = ScenarioMatrixExplorer().generate_matrix(
            {"tam": 120.0, "cogs": 300.0, "price": 1200.0})
        self.assertEqual(len(matrix["scenarios"]), 3)
        self.assertEqual([s["name"] for s in matrix["scenarios"]],
                         ["保守防御型 (Downside)", "基准稳健型 (Base)",
                          "乐观突击型 (Upside)"])
        self.assertAlmostEqual(sum(matrix["weights"].values()), 1.0, places=6)
        self.assertEqual(set(matrix["weights"]),
                         {"market_upside", "margin", "cost_risk", "speed"})
        for scenario in matrix["scenarios"]:
            self.assertGreaterEqual(scenario["score"], 0)
            self.assertLessEqual(scenario["score"], 100)
            self.assertIn("roi", scenario)
            self.assertIn("ltv_cac_ratio", scenario)
            self.assertGreater(scenario["payback_months"], 0)

    def test_ranking_and_recommendation(self):
        matrix = ScenarioMatrixExplorer().generate_matrix(
            {"tam": 120.0, "cogs": 300.0, "price": 1200.0})
        ranking = matrix["ranking"]
        self.assertEqual(len(ranking), 3)
        self.assertGreaterEqual(ranking[0]["score"], ranking[-1]["score"])
        top = max(matrix["scenarios"], key=lambda s: s["score"])
        self.assertEqual(matrix["recommended"], top["name"])
        self.assertIn("ROI", matrix["board_markdown"])
        self.assertIn("推荐", matrix["board_markdown"])

    def test_input_driven_shares(self):
        matrix = ScenarioMatrixExplorer().generate_matrix({
            "tam": 200.0, "cogs": 300.0, "price": 1200.0,
            "obtainable_shares": [0.02, 0.06, 0.12],
        })
        self.assertEqual([s["obtainable_share"] for s in matrix["scenarios"]],
                         [0.02, 0.06, 0.12])


if __name__ == "__main__":
    unittest.main(verbosity=2)

# -*- coding: utf-8 -*-
"""R05 第 1 轮升级验收契约（执行基石阶段 L01~L03）。

本轮契约针对 R05 蛙深远（战略研究官）真实体检病灶：
- L01：原生研究引擎只有 calc_hhi / verify_tam_variance 两个算子，缺少证据链
  分级校验、单位经济精算与敏感性摆动排序的确定性沙箱；
- L02：意图解构只输出一条固定线性链，depends_on 为伪造的 S{i-1}，没有真正的
  Kahn 拓扑排序、五阶段研究标准与工时估算，也无法识别环；
- L03：Critic 只能改顶层字符串，缺少跨角色越权硬红线阻断（代付款须移交 R03）、
  深层嵌套工件自愈与自愈后复检。

本文件为第 1 轮硬门禁：全部通过才算本轮升级完成。
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

from engines.runtime_engine import ResearchRuntimeEngine, EvidenceTierValidator  # noqa: E402
from engines.intent_compiler import ResearchIntentCompiler, DagCycleError  # noqa: E402
from engines.reflexive_healer import ReflexiveResearchHealer, RedlineBlocked  # noqa: E402


class TestL01RuntimeEngine(unittest.TestCase):
    """L01 工具实体层：真实确定性研究算子沙箱。"""

    def test_operator_registry_and_probe(self):
        engine = ResearchRuntimeEngine()
        ops = engine.available_operators()
        for op in ("calc_hhi", "verify_tam_variance", "evidence_chain",
                   "unit_economics", "sensitivity_swing", "tam_triangulate"):
            self.assertIn(op, ops, f"缺失确定性算子 {op}")

        probe = engine.probe()
        self.assertTrue(probe.available)
        self.assertGreaterEqual(probe.details["operator_count"], 6)
        self.assertIn("evidence_chain", probe.details["operators"])

    def test_evidence_chain_validation(self):
        claims = [
            {"id": "c1", "tier": "tier_1", "confidence": 0.95,
             "sources": ["S1"], "kind": "fact"},
            {"id": "c2", "tier": "tier_3", "confidence": 0.55,
             "sources": ["S2"], "kind": "estimate"},
            {"id": "c3", "tier": "tier_0", "confidence": 0.0,
             "sources": [], "kind": "rumor"},
        ]
        res = ResearchRuntimeEngine().execute("evidence_chain", {"claims": claims})
        self.assertTrue(res.ok, res.errors)
        data = res.data
        self.assertEqual(data["tier_distribution"]["tier_1"], 1)
        self.assertEqual(data["tier_distribution"]["tier_0"], 1)
        self.assertEqual(data["tier0_blocked"], ["c3"])
        self.assertIn("c3", data["orphan_claims"])
        self.assertIn("c2", data["low_confidence"])
        self.assertAlmostEqual(data["coverage_rate"], round(1 / 3, 4), places=4)
        self.assertFalse(data["gate_ok"])
        self.assertEqual(data["claim_count"], 3)

        validator = EvidenceTierValidator()
        direct = validator.validate(claims)
        self.assertEqual(direct["gate_ok"], False)
        self.assertAlmostEqual(validator.tier_min("tier_2"), 0.75, places=2)

    def test_unit_economics_zero_drift(self):
        res = ResearchRuntimeEngine().execute("unit_economics", {
            "arpu": 99.99, "gross_margin": 0.8, "churn_rate": 0.02, "cac": 300.0,
        })
        self.assertTrue(res.ok, res.errors)
        gp = round(99.99 * 0.8, 2)
        ltv = round(gp / 0.02, 2)
        self.assertAlmostEqual(res.data["gross_profit_per_user"], gp, places=2)
        self.assertAlmostEqual(res.data["ltv"], ltv, places=2)
        self.assertAlmostEqual(res.data["ltv_cac_ratio"], round(ltv / 300.0, 2), places=2)
        self.assertAlmostEqual(res.data["payback_months"], round(300.0 / gp, 2), places=2)
        self.assertTrue(res.data["healthy"])

    def test_sensitivity_swing_ranking(self):
        res = ResearchRuntimeEngine().execute("sensitivity_swing", {
            "base_value": 1000.0,
            "drivers": [
                {"name": "价格", "low_pct": -0.10, "high_pct": 0.10, "weight": 1.2},
                {"name": "流失率", "low_pct": -0.05, "high_pct": 0.05, "weight": 0.8},
            ],
        })
        self.assertTrue(res.ok, res.errors)
        drivers = res.data["drivers"]
        self.assertEqual(len(drivers), 2)
        self.assertEqual(res.data["top_driver"], "价格")
        self.assertAlmostEqual(drivers[0]["swing_abs"], 240.0, places=2)
        self.assertEqual(drivers[0]["rank"], 1)
        self.assertAlmostEqual(res.data["swing_total"], 320.0, places=2)
        self.assertIn("价格", res.data["deadly_point"])

    def test_tam_triangulation(self):
        res = ResearchRuntimeEngine().execute("tam_triangulate", {
            "top_down": {"components": [{"name": "A", "value": 60.0},
                                        {"name": "B", "value": 40.0}]},
            "bottom_up": {"customer_count": 200, "addressable_fraction": 0.5,
                          "annual_quantity": 1, "price_per_unit": 1.2},
        })
        self.assertTrue(res.ok, res.errors)
        self.assertAlmostEqual(res.data["tam_top"], 100.0, places=2)
        self.assertAlmostEqual(res.data["tam_bottom"], 120.0, places=2)
        self.assertAlmostEqual(res.data["variance"], 0.2, places=4)
        self.assertTrue(res.data["converged"])
        self.assertAlmostEqual(res.data["tolerance"], 0.30, places=2)

    def test_unknown_operator_fails_closed(self):
        res = ResearchRuntimeEngine().execute("no_such_op", {})
        self.assertFalse(res.ok)
        self.assertTrue(res.errors)


class TestL02IntentCompiler(unittest.TestCase):
    """L02 意图解构层：五阶段研究标准 Kahn DAG 与工时预算。"""

    QUERY = ("调研海外AI协同SaaS市场，预算500万人民币，"
             "对比3家竞品并给出TAM与进入情景")

    def test_five_stage_dag_and_kahn_order(self):
        res = ResearchIntentCompiler().compile(self.QUERY)
        self.assertEqual(res["stage_count"], 5)
        self.assertEqual([s["stage"] for s in res["stages"]],
                         ["audit", "sourcing", "analysis", "validation", "delivery"])
        self.assertEqual(res["topological_order"],
                         ["audit", "sourcing", "analysis", "validation", "delivery"])
        self.assertFalse(res["cycle_detected"])
        order = res["topological_order"]
        for edge in res["dag_edges"]:
            self.assertLess(order.index(edge["from"]), order.index(edge["to"]))
        for stage in res["stages"]:
            self.assertTrue(stage["tasks"])
            self.assertGreater(stage["hours"], 0)
        self.assertGreater(res["estimated_hours"], 0)
        self.assertAlmostEqual(sum(s["hours"] for s in res["stages"]),
                               res["estimated_hours"], places=2)
        self.assertAlmostEqual(res["estimated_person_days"],
                               round(res["estimated_hours"] / 8.0, 2), places=2)

    def test_entity_and_domain_extraction(self):
        res = ResearchIntentCompiler().compile(self.QUERY)
        self.assertIn("sizing", res["matched_domains"])
        self.assertIn("competitor", res["matched_domains"])
        self.assertTrue(any("500" in str(f) for f in res["entities"]["figures"]))
        self.assertIn(res["complexity"], ("medium", "high"))

    def test_kahn_sort_and_cycle_detection(self):
        compiler = ResearchIntentCompiler()
        self.assertEqual(
            compiler.kahn_sort(["delivery", "audit"], [{"from": "audit", "to": "delivery"}]),
            ["audit", "delivery"],
        )
        with self.assertRaises(DagCycleError):
            compiler.kahn_sort(["a", "b"], [{"from": "a", "to": "b"},
                                            {"from": "b", "to": "a"}])


class TestL03ReflexiveHealer(unittest.TestCase):
    """L03 自愈反思层：深层自愈 + 跨角色硬红线移交。"""

    DIRTY = {
        "shares": [40, 40],
        "conclusion": "我们必须进入这个赛道，绝对可行",
        "claims": [{"id": "c1", "text": "行业增速40%"}],
        "tam_top": 100.0,
        "tam_bottom": 160.0,
        "payment": {"action": "代付款给供应商", "amount": 50000},
    }

    def test_audit_detects_real_breakpoints(self):
        findings = ReflexiveResearchHealer().audit(self.DIRTY)
        codes = {f["code"] for f in findings}
        for expected in ("UNSOURCED_CLAIM", "SHARE_NOT_NORMALIZED",
                         "DECISION_REDLINE", "TAM_VARIANCE_WIDE",
                         "CROSS_ROLE_PAYMENT"):
            self.assertIn(expected, codes)
        payment = [f for f in findings if f["code"] == "CROSS_ROLE_PAYMENT"][0]
        self.assertEqual(payment["handoff"], "R03")
        self.assertEqual(payment["severity"], "critical")

    def test_redline_blocks_with_handoff(self):
        with self.assertRaises(RedlineBlocked) as ctx:
            ReflexiveResearchHealer().assert_redlines(self.DIRTY)
        msg = str(ctx.exception)
        self.assertIn("[REDLINE BLOCKED]", msg)
        self.assertIn("R03", msg)

    def test_deep_heal_and_verify(self):
        result = ReflexiveResearchHealer().heal_and_verify(self.DIRTY)
        healed = result["healed"]
        self.assertAlmostEqual(sum(healed["shares"]), 100.0, places=2)
        dumped = json.dumps(healed, ensure_ascii=False)
        self.assertNotIn("必须进入", dumped)
        self.assertNotIn("绝对可行", dumped)
        self.assertIn("default_ref:待核实", healed["claims"][0]["evidence_refs"])
        self.assertTrue(result["reflections"])
        self.assertFalse(result["clean"])
        residual = {f["code"] for f in result["residual_findings"]}
        self.assertIn("CROSS_ROLE_PAYMENT", residual)
        self.assertNotIn("DECISION_REDLINE", residual)
        self.assertTrue(any(h["to"] == "R03" for h in result["handoff"]))
        self.assertGreaterEqual(result["iterations"], 1)

    def test_nested_artifact_healing_is_idempotent(self):
        artifact = {
            "shares": [10, 10, 10],
            "sections": [{"body": "我们必须进入这个赛道，绝对可行"}],
        }
        healer = ReflexiveResearchHealer()
        first = healer.heal_and_verify(artifact)
        self.assertNotIn("必须进入", json.dumps(first["healed"], ensure_ascii=False))
        self.assertAlmostEqual(sum(first["healed"]["shares"]), 100.0, places=2)
        second = healer.heal_and_verify(first["healed"])
        self.assertAlmostEqual(sum(second["healed"]["shares"]), 100.0, places=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

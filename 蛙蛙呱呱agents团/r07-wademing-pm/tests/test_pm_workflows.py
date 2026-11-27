# -*- coding: utf-8 -*-
"""R07 PM 工作流回归：5 条工作流门禁 + 经验门 + 3 条端到端 + 3 条误用拦截。

运行：
    python -m pytest r07-wademing-pm/tests -q -p no:cacheprovider
    python r07-wademing-pm/run_tests.py
"""
from __future__ import annotations

import copy
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = os.path.dirname(HERE)
for _p in (HERE, AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from pm_workflows import (acceptance, briefing, discovery, experience,  # noqa: E402
                          prd, priority, runner)
from pm_workflows import common as wc  # noqa: E402
from skills import s03_prd, s08_decision  # noqa: E402

FIX = os.path.join(HERE, "pm_workflows", "fixtures")
MISUSE = os.path.join(HERE, "misuse")
GOLDEN = os.path.join(HERE, "golden")


def _fix(name: str) -> dict:
    return wc.read_json(os.path.join(FIX, name))


def _misuse(name: str) -> dict:
    return wc.read_json(os.path.join(MISUSE, name))


def _errors(gate: dict) -> str:
    return " ".join(gate.get("errors") or [])


class TestDiscoveryGate(unittest.TestCase):
    def setUp(self):
        self.data = _fix("bundle_new_product.json")["discovery"]

    def test_valid_passes(self):
        pack = discovery.build(self.data)
        self.assertTrue(pack["gate"]["ok"], pack["gate"]["errors"])
        self.assertEqual(pack["gate"]["grade"], "PASS")

    def test_missing_interviews_blocked(self):
        bad = dict(self.data, interviews=self.data["interviews"][:1])
        self.assertFalse(discovery.build(bad)["gate"]["ok"])

    def test_desire_only_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["interviews"] = [
            {"persona": "用户", "quote": "用户想要更炫的首页", "date": "2026-10-01"},
            {"persona": "用户", "quote": "希望能加背景", "date": "2026-10-02"},
            {"persona": "用户", "quote": "最好有转场", "date": "2026-10-03"},
        ]
        gate = discovery.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("not_desire_only", _errors(gate))

    def test_hypothesis_without_threshold_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["hypotheses"][0]["disproof"] = "如果效果不好就不成立"
        gate = discovery.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("hypothesis.falsifiable", _errors(gate))


class TestPrdGate(unittest.TestCase):
    def setUp(self):
        self.data = _fix("bundle_new_product.json")["prd"]

    def test_valid_eight_gates(self):
        pack = prd.build(self.data)
        self.assertTrue(pack["gate"]["ok"], pack["gate"]["errors"])
        self.assertEqual(pack["eight_gates"]["passed"], 8)

    def test_missing_non_goals_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["prd"]["scope"]["non_goals"] = []
        bad["non_goals"] = []
        gate = prd.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("scope.non_goals", _errors(gate))

    def test_premortem_needs_five(self):
        bad = copy.deepcopy(self.data)
        bad["premortem"]["failure_reasons"] = bad["premortem"]["failure_reasons"][:4]
        gate = prd.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("premortem.count", _errors(gate))

    def test_premortem_needs_owner(self):
        bad = copy.deepcopy(self.data)
        bad["premortem"]["failure_reasons"][0]["owner"] = ""
        gate = prd.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("premortem.owner", _errors(gate))

    def test_story_acceptance_band(self):
        bad = copy.deepcopy(self.data)
        bad["user_stories"][0]["acceptance_criteria"] = ["a", "b", "c"]
        self.assertFalse(prd.build(bad)["gate"]["ok"])


class TestPriorityGate(unittest.TestCase):
    def setUp(self):
        self.data = _fix("bundle_feature.json")["priority"]

    def test_valid_sorted(self):
        pack = priority.build(self.data)
        self.assertTrue(pack["gate"]["ok"], pack["gate"]["errors"])
        scores = [b["score"] for b in pack["backlog"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(b["source"] for b in pack["backlog"]))

    def test_missing_source_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["items"][0]["source"] = ""
        gate = priority.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("score.source", _errors(gate))

    def test_roadmap_must_be_outcome_oriented(self):
        bad = copy.deepcopy(self.data)
        bad["roadmap"][0]["outcome"] = ""
        gate = priority.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("roadmap.outcome", _errors(gate))


class TestAcceptanceGate(unittest.TestCase):
    def setUp(self):
        self.data = _fix("bundle_feature.json")["acceptance"]

    def test_valid(self):
        pack = acceptance.build(self.data)
        self.assertTrue(pack["gate"]["ok"], pack["gate"]["errors"])
        self.assertEqual(pack["scenario_counts"]["main"], 1)
        self.assertEqual(pack["scenario_counts"]["boundary"], 1)
        self.assertEqual(pack["scenario_counts"]["failure"], 1)

    def test_missing_boundary_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["scenarios"] = [s for s in bad["scenarios"] if s["type"] != "boundary"]
        gate = acceptance.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("scenario.boundary", _errors(gate))

    def test_release_gate_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["release_gate"]["checks"][0]["status"] = "block"
        gate = acceptance.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("release.decision", _errors(gate))


class TestBriefingGate(unittest.TestCase):
    def setUp(self):
        self.data = _fix("bundle_briefing.json")["briefing"]

    def test_valid(self):
        pack = briefing.build(self.data)
        self.assertTrue(pack["gate"]["ok"], pack["gate"]["errors"])
        self.assertTrue(pack["archive"]["recorded"])

    def test_single_option_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["options"] = bad["options"][:1]
        self.assertFalse(briefing.build(bad)["gate"]["ok"])

    def test_self_decision_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["recommendation"]["decision_owner"] = "r07"
        gate = briefing.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("decision_owner", _errors(gate))

    def test_decision_words_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["recommendation"]["rationale"] = "我决定就做方案 A。"
        gate = briefing.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("no_decision", _errors(gate))

    def test_missing_backlink_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["backlinks"] = []
        gate = briefing.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("backlink", _errors(gate))


class TestExperienceGate(unittest.TestCase):
    def setUp(self):
        self.data = _fix("experience_cards.json")

    def test_l2_valid(self):
        pack = experience.build(self.data)
        self.assertTrue(pack["gate"]["ok"], pack["gate"]["errors"])
        self.assertLessEqual(len(pack["cards"]), 5)
        self.assertTrue(pack["writeback"])

    def test_l0_no_retrieval(self):
        pack = experience.build({"level": "L0", "query": "新手引导", "as_of": "2026-11-27"})
        self.assertTrue(pack["gate"]["ok"], pack["gate"]["errors"])
        self.assertEqual(pack["cards"], [])

    def test_l0_with_cards_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["level"] = "L0"
        self.assertFalse(experience.build(bad)["gate"]["ok"])

    def test_l1_index_only(self):
        pack = experience.build({"level": "L1", "query": "新手引导",
                                 "as_of": "2026-11-27", "index": self.data["index"]})
        self.assertTrue(pack["gate"]["ok"], pack["gate"]["errors"])
        self.assertTrue(pack["index"])
        self.assertEqual(pack["cards"], [])

    def test_card_count_cap(self):
        bad = copy.deepcopy(self.data)
        bad["cards"] = bad["cards"] * 2
        gate = experience.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("experience.cards", _errors(gate))

    def test_low_credibility_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["cards"][0]["credibility"] = "low"
        gate = experience.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("experience.credibility", _errors(gate))

    def test_stale_card_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["cards"][0]["updated_at"] = "2024-01-01"
        gate = experience.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("experience.recency", _errors(gate))

    def test_illegal_writeback_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["writeback"] = [{"card_id": "exp-onboarding-1", "from": "observed", "to": "validated"}]
        gate = experience.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("experience.writeback", _errors(gate))

    def test_same_rank_conflict_blocked(self):
        bad = copy.deepcopy(self.data)
        bad["cards"][1]["status"] = "validated"
        bad["cards"][1]["trigger"] = bad["cards"][0]["trigger"]
        bad["cards"][1]["scope"] = bad["cards"][0]["scope"]
        bad["cards"][1]["rule"] = "首屏引导可以放到 8 步"
        gate = experience.build(bad)["gate"]
        self.assertFalse(gate["ok"])
        self.assertIn("experience.conflict", _errors(gate))


class TestEndToEnd(unittest.TestCase):
    def _run(self, bundle: str, flow: str = "all"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        manifest = runner.run(flow, _fix(bundle), tmp.name, html_title=bundle)
        return tmp.name, manifest

    def test_new_product_discovery_prd(self):
        out, man = self._run("bundle_new_product.json")
        self.assertTrue(man["ok"], man["gate"]["errors"])
        self.assertEqual(man["stage_order"], ["discovery", "prd"])
        self.assertTrue(man["handoffs"])
        self.assertTrue(os.path.exists(os.path.join(out, "workflow_manifest.json")))
        self.assertTrue(runner.audit(out)["ok"])

    def test_feature_prd_priority_acceptance(self):
        out, man = self._run("bundle_feature.json")
        self.assertTrue(man["ok"], man["gate"]["errors"])
        self.assertEqual(man["stage_order"], ["prd", "priority", "acceptance"])
        self.assertTrue(runner.audit(out)["ok"])

    def test_briefing(self):
        out, man = self._run("bundle_briefing.json")
        self.assertTrue(man["ok"], man["gate"]["errors"])
        self.assertEqual(man["stage_order"], ["briefing"])
        self.assertTrue(runner.audit(out)["ok"])

    def test_deterministic(self):
        a, man_a = self._run("bundle_feature.json")
        b, man_b = self._run("bundle_feature.json")
        self.assertEqual([s["sha256"] for s in man_a["stages"]],
                         [s["sha256"] for s in man_b["stages"]])
        for item in man_a["stages"]:
            pa = os.path.join(a, item["file"])
            pb = os.path.join(b, item["file"])
            self.assertEqual(open(pa, "rb").read(), open(pb, "rb").read())


class TestMisuseIntercepted(unittest.TestCase):
    def test_no_demand_card_blocked(self):
        data = _misuse("no_demand_card.json")
        out = s08_decision._validate_demand(data)
        self.assertFalse(out["ok"])
        joined = " ".join(c["msg"] for c in out["checks"] if not c["ok"])
        self.assertIn("non_goals", joined)

    def test_prd_without_non_goals_blocked(self):
        data = _misuse("prd_no_non_goals.json")
        out = prd.build(data)
        self.assertFalse(out["gate"]["ok"])
        self.assertIn("scope.non_goals", _errors(out["gate"]))
        # 同时确认八门禁本身也拦截
        self.assertFalse(s03_prd._validate_prd(data["prd"])["ok"])

    def test_user_wants_blocked(self):
        data = _misuse("discovery_user_wants.json")
        out = discovery.build(data)
        self.assertFalse(out["gate"]["ok"])
        self.assertIn("problem_real", _errors(out["gate"]))


class TestGoldenSamples(unittest.TestCase):
    def test_three_golden_html(self):
        files = [f for f in os.listdir(GOLDEN) if f.endswith(".html")] \
            if os.path.isdir(GOLDEN) else []
        self.assertGreaterEqual(len(files), 3, files)
        self.assertTrue(os.path.exists(os.path.join(GOLDEN, "README.md")))

    def test_misuse_three_json(self):
        files = [f for f in os.listdir(MISUSE) if f.endswith(".json")] \
            if os.path.isdir(MISUSE) else []
        self.assertGreaterEqual(len(files), 3, files)


if __name__ == "__main__":
    unittest.main(verbosity=2)

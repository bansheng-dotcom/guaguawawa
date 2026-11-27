# -*- coding: utf-8 -*-
"""T7 工程链回归：各段门禁 + 三份端到端 + 三份误用拦截 + 确定性。

运行：
    python -m pytest r09-wawenma-engineer/tests/test_eng_chain.py -q
    python r09-wawenma-engineer/run_tests.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
for _p in (HERE, ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from eng_chain import (adr, api, common, debug, feature, incident,  # noqa: E402
                       performance, release, review, runner, security, testing)
from skills import s09_eng_chain  # noqa: E402

FIX = os.path.join(HERE, "eng_chain", "fixtures")
CLEAN = os.path.join(FIX, "tiny-notes.json")
MISUSE = os.path.join(HERE, "misuse")


def _brief() -> dict:
    return common.load_brief(CLEAN)


class TestStageGates(unittest.TestCase):
    """十段各跑一次干净 brief，门禁必须 PASS 且关键字段存在。"""

    @classmethod
    def setUpClass(cls):
        cls.b = _brief()
        cls.arts = {
            "adr": adr.build(cls.b), "api": api.build(cls.b),
            "feature": feature.build(cls.b), "testing": testing.build(cls.b),
            "debug": debug.build(cls.b), "release": release.build(cls.b),
            "security": security.build(cls.b), "performance": performance.build(cls.b),
            "incident": incident.build(cls.b), "review": review.build(cls.b),
        }

    def test_all_stage_gates_pass(self):
        for name, art in self.arts.items():
            self.assertTrue(art["gate"]["ok"], f"{name}: {art['gate']['errors']}")
            self.assertEqual(art["stage"], name)

    def test_adr_shape(self):
        a = self.arts["adr"]
        self.assertEqual(len(a["options"]), 3)
        self.assertTrue(a["boundaries"][0]["does_not_own"])

    def test_api_contract(self):
        a = self.arts["api"]
        self.assertEqual(a["openapi"]["openapi"], "3.1.0")
        self.assertIn("#/components/schemas/Problem",
                      json.dumps(a["openapi"]))

    def test_testing_maps_acceptance(self):
        t = self.arts["testing"]
        self.assertEqual(set(t["scenario_ids"]), {"AC-1", "AC-2", "AC-3", "AC-4"})

    def test_security_error_codes(self):
        s = self.arts["security"]
        self.assertEqual(s["api_error_codes"], s["handled_error_codes"])


class TestNegativeGates(unittest.TestCase):
    """逐个破坏关键条件，确认对应具名门禁变红。"""

    @classmethod
    def setUpClass(cls):
        cls.b = _brief()

    def _contains(self, art, dim):
        self.assertFalse(art["gate"]["ok"])
        self.assertTrue(any(x["dim"] == dim and not x["ok"]
                            for x in art["gate"]["checks"]), art["gate"]["errors"])

    def test_adr_options(self):
        a = adr.build(self.b)
        a["options"] = a["options"][:1]
        self._contains(dict(a, gate=adr.check(a)), "adr:options")

    def test_api_irreversible(self):
        a = api.build(self.b)
        a["migration"]["reversible"] = False
        a["migration"]["approved_irreversible"] = False
        a["migration"]["rollback"] = []
        self._contains(dict(a, gate=api.check(a)), "api:migration_reversible")

    def test_feature_acceptance(self):
        f = feature.build(self.b)
        f["acceptance"] = []
        self._contains(dict(f, gate=feature.check(f)), "feature:acceptance")

    def test_testing_pyramid_and_skip(self):
        t = testing.build(self.b)
        t["pyramid"]["e2e"] = 0
        self._contains(dict(t, gate=testing.check(t)), "testing:pyramid")
        t2 = testing.build(self.b)
        t2["suites"]["skipped"] = 1
        self._contains(dict(t2, gate=testing.check(t2)), "testing:no_skipped")

    def test_testing_acceptance_mapping(self):
        t = testing.build(self.b)
        t["scenario_ids"] = ["AC-1"]
        self._contains(dict(t, gate=testing.check(t)), "testing:acceptance_mapping")

    def test_debug_root_cause(self):
        d = debug.build(self.b)
        d["root_cause"] = "unknown"
        self._contains(dict(d, gate=debug.check(d)), "debug:root_cause")

    def test_release_no_tests(self):
        r = release.build(self.b)
        r["tests"] = {"passed": 0, "failed": 0, "skipped": 3, "coverage": 0.0}
        self._contains(dict(r, gate=release.check(r)), "release:tests_green")

    def test_security_leak_and_codes(self):
        s = security.build(self.b)
        s["secret_scan"] = {"tool": "gitleaks", "findings": 1, "leaked": 1}
        self._contains(dict(s, gate=security.check(s)), "security:no_leaked_secrets")
        s2 = security.build(self.b)
        s2["handled_error_codes"] = s2["handled_error_codes"][:-1]
        self._contains(dict(s2, gate=security.check(s2)), "security:error_codes")

    def test_performance_budget(self):
        p = performance.build(self.b)
        p["budget"]["p95_ms"] = 999
        self._contains(dict(p, gate=performance.check(p)), "performance:budget")

    def test_incident_budget(self):
        i = incident.build(self.b)
        i["slo"]["consumed_min"] = 99
        self._contains(dict(i, gate=incident.check(i)), "incident:error_budget")

    def test_review_all_pass(self):
        r = review.build(self.b)
        r["checklist"][0]["status"] = "fail"
        self._contains(dict(r, gate=review.check(r)), "review:all_pass")


class TestEndToEnd(unittest.TestCase):
    """三份夹具端到端：十段 PASS、跨段一致、工件齐全、audit 通过、确定性。"""

    def _run(self, fixture):
        tmp = tempfile.TemporaryDirectory(prefix="r09_chain_")
        m = runner.run(os.path.join(FIX, fixture), tmp.name)
        return tmp, m

    def test_three_fixtures_pass(self):
        for fixture in ("tiny-notes.json", "incident-outage.json",
                        "security-audit.json"):
            tmp, m = self._run(fixture)
            with tmp:
                self.assertTrue(m["ok"], (fixture, m["blockers"]))
                self.assertEqual(m["grade"], "PASS")
                self.assertEqual(len(m["stages"]), 10)
                self.assertTrue(all(c["ok"] for c in m["cross_checks"]), fixture)
                for s in m["stages"]:
                    self.assertTrue(os.path.exists(os.path.join(
                        tmp.name, s["file"])), s["file"])
                    self.assertTrue(os.path.exists(os.path.join(
                        tmp.name, s["md"])), s["md"])
                self.assertTrue(os.path.exists(os.path.join(tmp.name, "eng_manifest.json")))
                audit = runner.audit(tmp.name)
                self.assertTrue(audit["ok"], audit["errors"])

    def test_deterministic(self):
        d1, m1 = self._run("tiny-notes.json")
        d2, m2 = self._run("tiny-notes.json")
        with d1, d2:
            self.assertEqual([s["sha256"] for s in m1["stages"]],
                             [s["sha256"] for s in m2["stages"]])


class TestMisuse(unittest.TestCase):
    """三份误用夹具分别被具名门禁拦下。"""

    def test_named_gates_block(self):
        for name in ("no-tests-release.json", "irreversible-migration.json",
                     "secret-in-repo.json"):
            path = os.path.join(MISUSE, name)
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            expected = raw["expect_block"]
            tmp = tempfile.TemporaryDirectory(prefix="r09_misuse_")
            with tmp:
                m = runner.run(path, tmp.name)
                self.assertFalse(m["ok"], name)
                self.assertTrue(any(expected in b for b in m["blockers"]),
                                f"{name} 未被 {expected} 拦下：{m['blockers']}")


class TestSkillModule(unittest.TestCase):
    """s09 子命令面：12 个动作 + 单段产出 + audit。"""

    def test_actions_and_run(self):
        self.assertEqual(len(s09_eng_chain.ACTIONS), 12)
        for a in ("adr", "api", "feature", "testing", "debug", "release",
                  "security", "performance", "incident", "review", "run", "audit"):
            self.assertIn(a, s09_eng_chain.ACTIONS)
        with tempfile.TemporaryDirectory(prefix="r09_s09_") as tmp:
            ap = argparse.ArgumentParser()
            sub = ap.add_subparsers(dest="cmd", required=True)
            s09_eng_chain.add_parser(sub)
            args = ap.parse_args(["eng_chain", "adr", "--brief", CLEAN,
                                  "--out", os.path.join(tmp, "adr.json")])
            out = s09_eng_chain.run(args)
            self.assertTrue(out["ok"], out)
            self.assertTrue(os.path.exists(os.path.join(tmp, "adr.json")))
            args2 = ap.parse_args(["eng_chain", "run", "--brief", CLEAN,
                                   "--out-dir", os.path.join(tmp, "chain")])
            out2 = s09_eng_chain.run(args2)
            self.assertTrue(out2["ok"], out2)
            args3 = ap.parse_args(["eng_chain", "audit", "--dir",
                                   os.path.join(tmp, "chain")])
            self.assertTrue(s09_eng_chain.run(args3)["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

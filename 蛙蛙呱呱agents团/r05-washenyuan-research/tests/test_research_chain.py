# -*- coding: utf-8 -*-
"""R05 研究链回归：8 段门禁 + 3 条端到端 + 3 条误用拦截。

运行：
    python -m pytest r05-washenyuan-research/tests/test_research_chain.py -q
    python r05-washenyuan-research/run_tests.py
"""
from __future__ import annotations

import copy
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

from research_chain import collect, compete, report, scope, size, source, triangulate, verify  # noqa: E402
from research_chain.runner import audit, run_fixture  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "pet_smart_hardware.json")
MISUSE = os.path.join(HERE, "misuse")
STAGES = ["scope", "source", "collect", "verify", "triangulate", "size", "compete", "report"]

_CHECKERS = {
    "scope": scope.check_scope,
    "source": source.check_source_map,
    "collect": collect.check_ledger,
    "verify": verify.check_verification,
    "triangulate": triangulate.check_synthesis,
    "size": size.check_sizing,
    "compete": compete.check_competition,
    "report": report.check_report,
}


def _load(path: str) -> dict:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


class TestStageGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="r05-chain-test-")
        cls.manifest = run_fixture(FIXTURE, cls.tmp)
        cls.arts = {s: _load(os.path.join(cls.tmp, "%s.json" % s)) for s in STAGES}

    def test_all_stage_gates_green(self):
        for stage in STAGES:
            result = _CHECKERS[stage](self.arts[stage])
            self.assertTrue(result["ok"], "%s 门禁失败：%s" % (stage, result["failed"]))

    def test_scope_gate(self):
        art = copy.deepcopy(self.arts["scope"])
        art["decision_use"] = ""
        self.assertFalse(scope.check_scope(art)["ok"])
        art = copy.deepcopy(self.arts["scope"])
        art["subquestions"][1]["category"] = art["subquestions"][0]["category"]
        art["mece"]["mutually_exclusive"] = False
        self.assertIn("scope:mece_exclusive", scope.check_scope(art)["failed"])

    def test_source_gate(self):
        art = copy.deepcopy(self.arts["source"])
        for entry in art["entries"]:
            for cand in entry["candidates"]:
                cand["type"] = "secondary"
        failed = source.check_source_map(art)["failed"]
        self.assertIn("source:type_diversity", failed)
        self.assertIn("source:tier_coverage", failed)

    def test_collect_gate(self):
        art = copy.deepcopy(self.arts["collect"])
        art["entries"][0]["url"] = ""
        self.assertIn("collect:three_elements", collect.check_ledger(art)["failed"])
        art = copy.deepcopy(self.arts["collect"])
        art["entries"][0]["source_id"] = "S99"
        self.assertIn("collect:source_known", collect.check_ledger(art)["failed"])

    def test_verify_gate(self):
        art = copy.deepcopy(self.arts["verify"])
        art["unverified_ids"] = []
        art["results"][0]["status"] = "unverified"
        self.assertIn("verify:disclosure", verify.check_verification(art)["failed"])
        art = copy.deepcopy(self.arts["verify"])
        art["results"][0]["recompute"]["status"] = "skipped"
        self.assertIn("verify:recompute_done", verify.check_verification(art)["failed"])

    def test_triangulate_gate(self):
        art = copy.deepcopy(self.arts["triangulate"])
        target = next(c for c in art["conclusions"] if not c["single_source"])
        target["single_source"] = True
        target["confidence"] = "high"
        self.assertIn("tri:single_source_low_confidence",
                      triangulate.check_synthesis(art)["failed"])
        art = copy.deepcopy(self.arts["triangulate"])
        art["contradictions"] = []
        self.assertIn("tri:contradictions_recorded",
                      triangulate.check_synthesis(art)["failed"])

    def test_size_gate(self):
        art = copy.deepcopy(self.arts["size"])
        art["monte_carlo"]["p10"] = art["monte_carlo"]["p90"] + 1
        self.assertIn("size:order", size.check_sizing(art)["failed"])
        art = copy.deepcopy(self.arts["size"])
        art["assumptions"][0]["evidence_id"] = ""
        self.assertIn("size:assumption_evidence", size.check_sizing(art)["failed"])

    def test_compete_gate(self):
        art = copy.deepcopy(self.arts["compete"])
        first = art["competitors"][0]
        first["cells"][art["dimensions"][0]]["source_id"] = "S99"
        self.assertIn("compete:cell_source", compete.check_competition(art)["failed"])
        art = copy.deepcopy(self.arts["compete"])
        art["shares"] = art["shares"][:4]
        self.assertIn("compete:shares", compete.check_competition(art)["failed"])

    def test_report_gate(self):
        art = copy.deepcopy(self.arts["report"])
        art["ledger_source_ids"] = []
        self.assertIn("report:traceability", report.check_report(art)["failed"])
        art = copy.deepcopy(self.arts["report"])
        art["markdown"] = art["markdown"].replace("## 4 证据附录", "## 附录")
        self.assertIn("report:structure", report.check_report(art)["failed"])


class TestEndToEnd(unittest.TestCase):
    def test_run_all_stages_and_manifest(self):
        tmp = tempfile.mkdtemp(prefix="r05-chain-e2e-")
        manifest = run_fixture(FIXTURE, tmp)
        self.assertTrue(manifest["ok"], manifest)
        self.assertEqual(manifest["grade"], "A")
        self.assertEqual(len(manifest["stage_order"]), 8)
        for stage in STAGES:
            path = os.path.join(tmp, "%s.json" % stage)
            self.assertTrue(os.path.isfile(path), path)
        for name in ("research_report.md", "research_report.html",
                     "research_manifest.json"):
            self.assertTrue(os.path.isfile(os.path.join(tmp, name)), name)
        self.assertTrue(manifest["cross_checks"]["ok"])

    def test_audit_detects_tamper(self):
        tmp = tempfile.mkdtemp(prefix="r05-chain-audit-")
        run_fixture(FIXTURE, tmp)
        clean = audit(tmp)
        self.assertTrue(clean["ok"], clean)
        path = os.path.join(tmp, "scope.json")
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n")
        dirty = audit(tmp)
        self.assertFalse(dirty["ok"])
        self.assertIn("audit:sha256:scope.json", dirty["failed"])

    def test_determinism(self):
        a = tempfile.mkdtemp(prefix="r05-chain-det-a-")
        b = tempfile.mkdtemp(prefix="r05-chain-det-b-")
        run_fixture(FIXTURE, a)
        run_fixture(FIXTURE, b)
        sa = _load(os.path.join(a, "size.json"))
        sb = _load(os.path.join(b, "size.json"))
        self.assertEqual(sa["monte_carlo"], sb["monte_carlo"])
        self.assertEqual(sa["top_down"], sb["top_down"])
        self.assertEqual(sa["bottom_up"], sb["bottom_up"])
        ra = _load(os.path.join(a, "report.json"))["markdown"]
        rb = _load(os.path.join(b, "report.json"))["markdown"]
        self.assertEqual(ra, rb)


class TestMisuse(unittest.TestCase):
    def _blocked(self, name: str, checker, expected: str):
        art = _load(os.path.join(MISUSE, name))
        result = checker(art)
        self.assertFalse(result["ok"], "%s 应被拦下" % name)
        self.assertIn(expected, result["failed"], "%s 未命中 %s" % (name, expected))

    def test_no_sources_blocked(self):
        self._blocked("no_sources.json", report.check_report, "report:traceability")

    def test_secondary_only_blocked(self):
        self._blocked("secondary_only.json", source.check_source_map,
                      "source:type_diversity")

    def test_overclaim_blocked(self):
        self._blocked("overclaim.json", triangulate.check_synthesis,
                      "tri:two_sources_or_single")


if __name__ == "__main__":
    unittest.main()

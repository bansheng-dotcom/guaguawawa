# -*- coding: utf-8 -*-
"""R11 七段内容链回归：各段门禁 + 3 条端到端 + 3 条误用拦截。"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from content_chain import (draft, final, outline, research, review,  # noqa: E402
                           rewrite, runner, topic)
from content_chain.common import FILES, read_json  # noqa: E402

FIXTURES = HERE / "fixtures"
MISUSE = HERE / "misuse"
TMP = Path(tempfile.mkdtemp(prefix="r11_chain_"))


def _load(name: str):
    return read_json(str(FIXTURES / name))


def _build_chain(name: str = "knowledge.json"):
    brief = _load(name)
    t = topic.build(brief)
    r = research.build(t, brief)
    o = outline.build(r, brief)
    d = draft.build(o, r, brief)
    rv = review.build(d)
    rq = rewrite.build(d, rv, brief)
    text = final.compose(d, rq, r, brief)
    fa = final.audit(text, o, r, brief)
    return {"brief": brief, "topic": t, "research": r, "outline": o,
            "draft": d, "review": rv, "rewrite": rq, "text": text, "final": fa}


class TestTopic(unittest.TestCase):
    def test_gate_pass(self):
        c = _build_chain()
        self.assertTrue(c["topic"]["gate"]["ok"])
        self.assertEqual(len(c["topic"]["candidates"]), 10)
        self.assertEqual(len(c["topic"]["top3"]), 3)

    def test_missing_score_blocked(self):
        art = _build_chain()["topic"]
        art["candidates"][0]["scores"].pop("writability")
        self.assertFalse(topic.check(art)["ok"])


class TestResearch(unittest.TestCase):
    def test_gate_pass(self):
        art = _build_chain()["research"]
        self.assertTrue(art["gate"]["ok"])
        self.assertGreaterEqual(len(art["sources"]), 8)
        self.assertTrue(all(art["tier_counts"].get(k) is not None
                            for k in ("primary", "secondary", "tertiary")))

    def test_short_quote_blocked(self):
        art = _build_chain()["research"]
        art["sources"][0]["quote"] = "太短"
        g = research.check(art)
        self.assertFalse(g["ok"])
        self.assertIn("research.source_fields", g["blockers"][0])


class TestOutline(unittest.TestCase):
    def test_gate_pass(self):
        art = _build_chain()["outline"]
        self.assertTrue(art["gate"]["ok"])
        self.assertTrue(all(all(str(s.get(f, "")).strip() for f in outline.FIELDS)
                            for s in art["sections"]))

    def test_missing_field_blocked(self):
        art = _build_chain()["outline"]
        art["sections"][0]["example"] = ""
        g = outline.check(art)
        self.assertFalse(g["ok"])


class TestDraft(unittest.TestCase):
    def test_gate_pass(self):
        art = _build_chain()["draft"]
        self.assertTrue(art["gate"]["ok"])
        for s in art["sections"]:
            self.assertGreaterEqual(s["diversity"], 0.6)
            self.assertGreaterEqual(s["selected_score"], 85)
            self.assertTrue(s["selected_reason"])

    def test_common_track_blocked(self):
        art = _build_chain()["draft"]
        art["sections"][0]["candidates"][0]["text"] = "需要指出的是，" + art["sections"][0]["candidates"][0]["text"]
        self.assertFalse(draft.check(art)["ok"])


class TestReview(unittest.TestCase):
    def test_gate_pass_and_traceable(self):
        c = _build_chain()
        self.assertTrue(c["review"]["gate"]["ok"])
        self.assertEqual(len(c["review"]["findings"]), 5)
        self.assertTrue(review.verify_quotes(c["review"], c["draft"])["ok"])

    def test_missing_dim_blocked(self):
        art = _build_chain()["review"]
        art["findings"] = [f for f in art["findings"] if f["dim"] != "logic"]
        self.assertFalse(review.check(art)["ok"])


class TestRewrite(unittest.TestCase):
    def test_gate_pass(self):
        c = _build_chain()
        self.assertTrue(c["rewrite"]["gate"]["ok"])
        for s in c["rewrite"]["sections"]:
            self.assertEqual(s["coverage"], 1.0)
            for u in s["units"]:
                self.assertTrue(200 <= len(u["original"]) <= 400)
                self.assertTrue(2 <= len(u["candidates"]) <= 4)

    def test_number_drift_blocked(self):
        art = _build_chain()["rewrite"]
        u = art["sections"][0]["units"][0]
        u["candidates"][0]["text"] = u["candidates"][0]["text"].replace("3", "300", 1)
        g = rewrite.recheck_facts(art)
        self.assertFalse(g["ok"])
        self.assertIn("rewrite.facts", g["blockers"][0])


class TestFinal(unittest.TestCase):
    def test_gate_pass(self):
        art = _build_chain()["final"]
        self.assertTrue(art["gate"]["ok"])
        self.assertGreater(art["char_len"], 0)

    def test_fake_number_blocked(self):
        c = _build_chain()
        text = c["text"] + "\n\n## 附加\n增长 300%。\n"
        g = final.audit(text, c["outline"], c["research"], c["brief"])["gate"]
        self.assertFalse(g["ok"])
        self.assertTrue(any("final.fact_check" in b for b in g["blockers"]))

    def test_fluff_blocked(self):
        c = _build_chain()
        text = c["text"] + "\n\n## 附加\n综上所述，这一切都值得注意。\n"
        g = final.audit(text, c["outline"], c["research"], c["brief"])["gate"]
        self.assertFalse(g["ok"])
        self.assertTrue(any("final.ai_fluff" in b for b in g["blockers"]))


class TestEndToEnd(unittest.TestCase):
    def _run(self, name: str):
        out = TMP / name
        m = runner.run(str(FIXTURES / name), str(out))
        self.assertEqual(m["gate"]["grade"], "PASS", m["gate"]["blockers"])
        for f in list(FILES.values()) + ["final.md", "final.html", "chain_manifest.json"]:
            self.assertTrue((out / f).is_file(), f)
        audit = runner.audit_dir(str(out))
        self.assertTrue(audit["gate"]["ok"], audit["gate"]["blockers"])
        html = (out / "final.html").read_text(encoding="utf-8")
        self.assertIn("</html>", html)
        return m

    def test_knowledge(self):
        m = self._run("knowledge.json")
        self.assertEqual([s["grade"] for s in m["stages"]], ["PASS"] * 7)

    def test_tutorial(self):
        m = self._run("tutorial.json")
        self.assertEqual([s["grade"] for s in m["stages"]], ["PASS"] * 7)

    def test_opinion(self):
        m = self._run("opinion.json")
        self.assertEqual([s["grade"] for s in m["stages"]], ["PASS"] * 7)


class TestMisuse(unittest.TestCase):
    def test_all_fluff(self):
        d = read_json(str(MISUSE / "all-fluff.json"))
        g = final.audit(d["markdown"], d["outline"], d["research"], d["brief"])["gate"]
        self.assertFalse(g["ok"])
        self.assertTrue(any("final.ai_fluff" in b for b in g["blockers"]))

    def test_conclusion_without_evidence(self):
        d = read_json(str(MISUSE / "conclusion-without-evidence.json"))
        g = research.check(d["artifact"])
        self.assertFalse(g["ok"])
        self.assertTrue(any("research.claim_sources" in b for b in g["blockers"]))

    def test_rewrite_adds_fact(self):
        d = read_json(str(MISUSE / "rewrite-adds-fact.json"))
        g = rewrite.recheck_facts(d["artifact"], d.get("entities") or [])
        self.assertFalse(g["ok"])
        self.assertTrue(any("rewrite.facts" in b for b in g["blockers"]))


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)

# -*- coding: utf-8 -*-
"""T8b 报告链回归：CoV / 图表必绘 / 文字包评审 / deliver / 三数据集端到端。

运行：
    python -m pytest r06-wadeqing-analyst/tests/test_report_chain.py -q
"""
from __future__ import annotations

import copy
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
for _p in (HERE, ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis_chain import (chart_pack, deliver, material_pack, report_runner,
                            runner, text_pack, verify)  # noqa: E402
from analysis_chain import common  # noqa: E402

CASES = os.path.join(HERE, "cases")
RETAIL = os.path.join(CASES, "analysis-retail", "data.csv")
SAAS = os.path.join(CASES, "analysis-saas", "data.csv")
SELFMEDIA = os.path.join(CASES, "analysis-selfmedia", "data.csv")


class TestReportStages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = cls.tmp.name
        cls.chain = runner.run("9月利润为什么下滑", RETAIL, cls.dir,
                               "2026-06-01", "2026-09-28", "2026-07-31",
                               dimensions=["channel", "category"], metric="profit",
                               domain="profit", qty="qty")
        cls.pack = material_pack.build(cls.dir)
        cls.ver = verify.build(cls.pack,
                               common.read_json(os.path.join(cls.dir, "findings.json")),
                               common.read_json(os.path.join(cls.dir, "explanation.json")),
                               common.read_json(os.path.join(cls.dir, "data_profile.json")))
        cls.charts = chart_pack.build(
            cls.pack, common.read_json(os.path.join(cls.dir, "findings.json")), cls.ver)
        cls.text = text_pack.build(
            cls.pack, cls.ver, cls.charts,
            common.read_json(os.path.join(cls.dir, "explanation.json")),
            common.read_json(os.path.join(cls.dir, "data_profile.json")),
            common.read_json(os.path.join(cls.dir, "stats.json")))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_chain_ok(self):
        self.assertTrue(self.chain["ok"])

    def test_material_ok(self):
        self.assertTrue(self.pack["gate"]["ok"], self.pack["gate"]["errors"])
        self.assertTrue(self.pack["claims"])
        for c in self.pack["claims"]:
            self.assertTrue(c["numbers"])
            self.assertTrue(c["evidence"])

    def test_verify_six_questions(self):
        self.assertTrue(self.ver["gate"]["ok"], self.ver["gate"]["errors"])
        for u in self.ver["units"]:
            self.assertEqual({a["question"] for a in u["cov"]},
                             {"metric_state", "denominator", "baseline", "driver",
                              "counter_evidence", "boundary"})
            self.assertIn(u["route"], ("pass", "analysis", "text", "chart", "drop"))

    def test_chart_ok(self):
        self.assertTrue(self.charts["gate"]["ok"], self.charts["gate"]["errors"])
        for c in self.charts["charts"]:
            self.assertEqual(c["series_completeness"]["ratio"], 1.0)
            self.assertTrue(c["annotation_plan"]["avoid_overlap"])
            self.assertIn("required_series", c["fail_if_missing"])

    def test_chart_missing_series_rejected(self):
        bad = copy.deepcopy(self.charts)
        bad["charts"][1]["series_completeness"]["ratio"] = 0.5
        bad["charts"][1]["series_completeness"]["missing"] = ["缺"]
        self.assertFalse(chart_pack.check(bad, {}, set())["ok"])

    def test_text_ok(self):
        self.assertTrue(self.text["gate"]["ok"], self.text["gate"]["errors"])
        self.assertTrue(self.text["review"]["ok"])

    def test_text_overreach_rejected(self):
        bad = copy.deepcopy(self.text)
        bad["units"][0]["paragraphs"].append("必须全量上线，保证稳赚。")
        self.assertFalse(text_pack._review(bad, self.pack)["ok"])

    def test_deliver_ok(self):
        rep = report_runner.run_report(self.dir, os.path.join(self.dir, "report"))
        self.assertTrue(rep["ok"], rep["gate"]["errors"])
        self.assertTrue(os.path.exists(os.path.join(self.dir, "report", "report.html")))
        self.assertTrue(os.path.exists(os.path.join(self.dir, "report", "manifest.json")))
        events = open(os.path.join(self.dir, "report", "run_events.jsonl"),
                      encoding="utf-8").read().strip().splitlines()
        self.assertGreaterEqual(len(events), 4)
        m = common.read_json(os.path.join(self.dir, "report", "manifest.json"))
        self.assertEqual(m["author_role"], "r01")
        self.assertFalse(m["publishable"])
        self.assertEqual(m["trace"]["rate"], 1.0)
        self.assertTrue(m["quality"]["ok"])

    def test_trace_rejects_unknown_number(self):
        rep = report_runner.run_report(self.dir, os.path.join(self.dir, "report"))
        html = open(rep["report_html"], encoding="utf-8").read()
        bad = html.replace("</body>", "<p>额外数字 987654。</p></body>")
        self.assertFalse(deliver.audit_trace(bad, self.pack)["ok"])


class TestReportEndToEnd(unittest.TestCase):
    def _run(self, name, question, data, start, end, split, kwargs):
        out = tempfile.mkdtemp(prefix=f"report_{name}_")
        rep = report_runner.run_all(question, data, out, start, end, split, **kwargs)
        self.assertTrue(rep.get("ok"), rep.get("errors"))
        html = os.path.join(out, "report", "report.html")
        self.assertTrue(os.path.exists(html))
        m = common.read_json(os.path.join(out, "report", "manifest.json"))
        self.assertTrue(m["quality"]["ok"], m["quality"])
        self.assertEqual(m["trace"]["rate"], 1.0)
        self.assertFalse(m["publishable"])
        return rep, out

    def test_retail(self):
        rep, _ = self._run("retail", "9月利润为什么下滑", RETAIL,
                           "2026-06-01", "2026-09-28", "2026-07-31",
                           dict(dimensions=["channel", "category"], metric="profit",
                                domain="profit", qty="qty"))
        self.assertEqual(len(rep["charts"]), 3)

    def test_saas(self):
        self._run("saas", "客户流失风险为什么上升", SAAS, "2025-01", "2026-12",
                  "2025-12", dict(dimensions=["onboarding", "plan"],
                                  metric="churn_flag", domain="churn", date="month"))

    def test_selfmedia(self):
        self._run("selfmedia", "播放量为什么增长", SELFMEDIA,
                  "2026-07-01", "2026-09-28", "2026-08-15",
                  dict(dimensions=["platform", "account"], metric="views",
                       domain="growth", qty="posts"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

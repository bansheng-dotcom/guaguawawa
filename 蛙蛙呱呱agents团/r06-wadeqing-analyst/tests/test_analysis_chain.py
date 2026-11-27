# -*- coding: utf-8 -*-
"""T8a 分析链回归：单段门禁 + 三数据集端到端 + 误用拦截 + 确定性。

运行：
    python -m pytest r06-wadeqing-analyst/tests/test_analysis_chain.py -q
    python r06-wadeqing-analyst/run_tests.py
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

from analysis_chain import common, explain, explore, frame, plan, profile, runner, stats_test  # noqa: E402
from skills import _common as c  # noqa: E402

CASES = os.path.join(HERE, "cases")
DIMS = ["channel", "category"]


def _retail():
    return os.path.join(CASES, "analysis-retail", "data.csv")


def _saas():
    return os.path.join(CASES, "analysis-saas", "data.csv")


def _selfmedia():
    return os.path.join(CASES, "analysis-selfmedia", "data.csv")


def _write(path: str, text: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


class TestFrame(unittest.TestCase):
    def test_frame_ok(self):
        f = frame.build("9月利润为什么下滑", dimensions=DIMS)
        self.assertTrue(f["gate"]["ok"], f["gate"]["errors"])
        self.assertEqual(len(f["hypotheses"]), 5)
        self.assertTrue(f["mece"]["collectively_exhaustive"])

    def test_time_as_cause_rejected(self):
        f = frame.build("收入为什么下滑", dimensions=["channel"])
        f["hypotheses"][0]["driver"] = "time"
        g = frame.check(f)
        self.assertFalse(g["ok"])
        self.assertTrue(any("时间" in e for e in g["errors"]))

    def test_missing_decision_rejected(self):
        f = frame.build("利润为什么下滑", dimensions=DIMS)
        f["hypotheses"][1]["decision_if_true"] = ""
        g = frame.check(f)
        self.assertFalse(g["ok"])


class TestPlan(unittest.TestCase):
    def _frame(self):
        return frame.build("利润为什么下滑", dimensions=DIMS)

    def test_plan_ok(self):
        p = plan.build(self._frame(), "2026-06-01", "2026-09-28", "2026-07-31")
        self.assertTrue(p["gate"]["ok"], p["gate"]["errors"])
        self.assertTrue(p["preregistered"])
        self.assertFalse(p["data_read_before_plan"])
        self.assertEqual(len(p["rounds"]), 5)

    def test_plan_after_data_rejected(self):
        p = plan.build(self._frame(), "2026-06-01", "2026-09-28", "2026-07-31")
        p["data_read_before_plan"] = True
        self.assertFalse(plan.check(p)["ok"])

    def test_missing_stop_condition_rejected(self):
        p = plan.build(self._frame(), "2026-06-01", "2026-09-28", "2026-07-31")
        p["rounds"][0]["stop_condition"] = {}
        self.assertFalse(plan.check(p)["ok"])


class TestProfile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        f = frame.build("利润为什么下滑", dimensions=["channel"])
        self.plan = plan.build(f, "2026-01-01", "2026-01-20", "2026-01-10")

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_data_fails(self):
        lines = ["date,channel,profit"]
        for i in range(10):
            profit = "" if i < 4 else str(10 + i)
            lines.append(f"2026-01-{1 + i:02d},A,{profit}")
        path = _write(os.path.join(self.dir, "dirty.csv"), "\n".join(lines) + "\n")
        p = profile.profile(path, self.plan, date="date")
        self.assertFalse(p["gate"]["ok"])
        self.assertEqual(p["dimensions"]["completeness"]["status"], "FAIL")

    def test_clean_data_passes(self):
        lines = ["date,channel,profit"]
        for i in range(20):
            lines.append(f"2026-01-{1 + i:02d},{'A' if i % 2 else 'B'},{10 + i}")
        path = _write(os.path.join(self.dir, "clean.csv"), "\n".join(lines) + "\n")
        p = profile.profile(path, self.plan, date="date")
        self.assertTrue(p["gate"]["ok"], p["gate"]["errors"])
        self.assertEqual(p["overall_score"] >= 60, True)


class TestExploreExplain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.f = frame.build("利润为什么下滑", dimensions=DIMS)
        cls.p = plan.build(cls.f, "2026-06-01", "2026-09-28", "2026-07-31")
        cls.fd = explore.build(_retail(), cls.p, qty="qty", cost="cost")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_explore_ok(self):
        self.assertTrue(self.fd["gate"]["ok"], self.fd["gate"]["errors"])
        self.assertTrue(any(x["type"] == "overall" for x in self.fd["findings"]))
        self.assertTrue(any(x["type"] == "unit_economics" for x in self.fd["findings"]))

    def test_zero_denominator_rejected(self):
        bad = copy.deepcopy(self.fd)
        overall = next(x for x in bad["findings"] if x["type"] == "overall")
        overall["denominator_value"] = 0
        self.assertFalse(explore.check(bad, self.p)["ok"])

    def test_explain_ok_and_top_driver(self):
        ex = explain.build(_retail(), self.p, self.fd, qty="qty")
        self.assertTrue(ex["gate"]["ok"], ex["gate"]["errors"])
        self.assertIn("抖音", ex["top_driver"])
        self.assertFalse(ex["causal_claim"])

    def test_causal_claim_rejected(self):
        ex = explain.build(_retail(), self.p, self.fd, qty="qty")
        ex["causal_claim"] = True
        self.assertFalse(explain.check(ex, self.fd, self.p)["ok"])

    def test_additivity_rejected(self):
        ex = explain.build(_retail(), self.p, self.fd, qty="qty")
        ex["driver_tree"]["additivity"]["error_pct"] = 20.0
        self.assertFalse(explain.check(ex, self.fd, self.p)["ok"])


class TestStats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = frame.build("利润为什么下滑", dimensions=DIMS)
        cls.p = plan.build(cls.f, "2026-06-01", "2026-09-28", "2026-07-31")
        cls.fd = explore.build(_retail(), cls.p, qty="qty")
        cls.st = stats_test.build(_retail(), cls.p, cls.fd)

    def test_stats_ok(self):
        self.assertTrue(self.st["gate"]["ok"], self.st["gate"]["errors"])
        self.assertIsNotNone(self.st["headline"]["ci"]["lo"])
        self.assertTrue(self.st["segments"]["tests"])
        self.assertTrue(all("p_adjusted" in t for t in self.st["segments"]["tests"]))

    def test_small_sample_rejected(self):
        st = copy.deepcopy(self.st)
        st["assumptions"]["sample_ok"] = False
        self.assertFalse(stats_test.check(st)["ok"])

    def test_missing_ci_rejected(self):
        st = copy.deepcopy(self.st)
        st["headline"]["ci"] = {}
        self.assertFalse(stats_test.check(st)["ok"])


class TestMisuseFixtures(unittest.TestCase):
    """misuse/*.json 是给评审看的反例文件，不是只存在于测试代码里。"""

    def test_frame_time_as_cause(self):
        data = c.load_json(os.path.join(HERE, "misuse", "frame-time-as-cause.json"))
        g = frame.check(data)
        self.assertFalse(g["ok"])
        self.assertTrue(any("时间" in e for e in g["errors"]))

    def test_plan_after_data(self):
        data = c.load_json(os.path.join(HERE, "misuse", "plan-after-data.json"))
        g = plan.check(data)
        self.assertFalse(g["ok"])
        self.assertTrue(any("data_read_before_plan" in e or "数据证据" in e for e in g["errors"]))

    def test_explain_causal_claim(self):
        data = c.load_json(os.path.join(HERE, "misuse", "explain-causal-claim.json"))
        g = explain.check(data, {"findings": [{"type": "overall", "delta": -200.0}]}, {})
        self.assertFalse(g["ok"])
        self.assertTrue(any("因果" in e for e in g["errors"]))


class TestEndToEnd(unittest.TestCase):
    """三份数据集端到端：全链 PASS + 预埋真因必须被指出。"""

    def _run(self, name, question, data, start, end, split, dims, metric,
             domain, date="date", qty=None):
        out = tempfile.mkdtemp(prefix=f"chain_{name}_")
        manifest = runner.run(question, data, out, start, end, split,
                              dimensions=dims, metric=metric, domain=domain,
                              date=date, qty=qty)
        self.assertTrue(manifest["ok"], [s for s in manifest["stages"]
                                         if not s["ok"]])
        self.assertEqual(manifest["stage_order"],
                         ["frame", "plan", "profile", "explore", "explain", "test"])
        ex = common.read_json(os.path.join(out, "explanation.json"))
        return out, ex

    def test_retail_profit(self):
        out, ex = self._run("retail", "9月利润为什么下滑", _retail(),
                            "2026-06-01", "2026-09-28", "2026-07-31", DIMS,
                            "profit", "profit", qty="qty")
        self.assertIn("抖音", ex["top_driver"])

    def test_saas_churn(self):
        out, ex = self._run("saas", "客户流失风险为什么上升", _saas(),
                            "2025-01", "2026-12", "2025-12",
                            ["onboarding", "plan"], "churn_flag", "churn", date="month")
        self.assertIn("pending", ex["top_driver"])

    def test_selfmedia_growth(self):
        out, ex = self._run("selfmedia", "播放量为什么增长", _selfmedia(),
                            "2026-07-01", "2026-09-28", "2026-08-15",
                            ["platform", "account"], "views", "growth", qty="posts")
        self.assertIn("抖音", ex["top_driver"])

    def test_deterministic(self):
        d1 = tempfile.mkdtemp(prefix="chain_det1_")
        d2 = tempfile.mkdtemp(prefix="chain_det2_")
        for d in (d1, d2):
            runner.run("播放量为什么增长", _selfmedia(), d,
                       "2026-07-01", "2026-09-28", "2026-08-15",
                       dimensions=["platform", "account"], metric="views",
                       domain="growth", qty="posts")
        a = common.read_json(os.path.join(d1, "explanation.json"))["root"]
        b = common.read_json(os.path.join(d2, "explanation.json"))["root"]
        self.assertEqual(a, b)
        sa = common.read_json(os.path.join(d1, "stats.json"))["headline"]
        sb = common.read_json(os.path.join(d2, "stats.json"))["headline"]
        self.assertEqual(sa["diff"], sb["diff"])
        self.assertEqual(sa["ci"], sb["ci"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

# -*- coding: utf-8 -*-
"""P4 唯一入口的纯函数回归（不跑完整产线）。"""
from __future__ import annotations

from core import report_build


PROFILE = {
    "facts": 37,
    "channels": {"retail": 1404, "wholesale": 468, "origin": 108},
    "kinds": {"long_panel": 3, "metric_json": 3},
    "tables": 0,
}


def test_select_questions_market_has_at_least_three():
    qs = report_build.select_questions("内蒙古三城水果市场调研", PROFILE, "market")
    assert 3 <= len(qs) <= 10
    assert all(q["capability"] and q["text"] for q in qs)
    assert all(q["id"].startswith("q.") for q in qs)


def test_questions_from_findings_maps_known_keys():
    trace = {"findings": [{"key": "structure"}, {"key": "economics"},
                          {"key": "coverage"}, {"key": "not_a_method"}]}
    qs = report_build.questions_from_findings(trace)
    assert [q["id"] for q in qs] == ["q.r06.structure", "q.r15.tco", "q.r05.sources"]


def test_questions_from_findings_dedupes():
    trace = {"findings": [{"key": "transmission"}, {"key": "arbitrage"}]}
    qs = report_build.questions_from_findings(trace)
    assert [q["id"] for q in qs] == ["q.r15.chain"]

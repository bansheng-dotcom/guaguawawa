# -*- coding: utf-8 -*-
"""决策契约与决策优先产线的单元测试（不跑完整渲染）。"""
from __future__ import annotations

import json
import os

import pytest

from core import decision


def _q(i=1, finding="structure", kind="compare_categories", ctype="hbar", **kw):
    q = {
        "id": f"dq{i}", "text": f"问题{i}？", "decision": "做一个决定",
        "finding": finding, "falsifier": "方向反转即作废",
        "comparison": {"kind": kind, "left": "A", "right": "B",
                       "metric": "变化率", "unit": "%"},
        "chart": {"type": ctype},
    }
    q.update(kw)
    return q


def _ctr(qs, **kw):
    c = {"schema": decision.SCHEMA, "decision": "决定", "auto": False,
         "questions": qs}
    c.update(kw)
    return c


def test_draft_five_questions_and_unique_comparisons():
    ctr = decision.draft("经营诊断", ["structure", "trajectory", "momentum",
                                      "contribution", "economics", "risk"])
    assert len(ctr["questions"]) == 5
    kinds = [q["comparison"]["kind"] for q in ctr["questions"]]
    assert len(set(kinds)) >= 4, kinds          # 不选五个同型对照
    assert decision.validate(ctr)["ok"]


def test_validate_rejects_too_few_questions():
    r = decision.validate(_ctr([_q(1), _q(2)]))
    assert not r["ok"]
    assert any("3–5" in e for e in r["errors"])


def test_validate_rejects_chart_that_cannot_encode_comparison():
    # 时间趋势不能用横条排名表达
    r = decision.validate(_ctr([_q(1), _q(2, "momentum", "compare_two_points",
                                   "grouped_bar"),
                                _q(3, "trajectory", "change_over_time", "line")]))
    bad = _ctr([_q(1, "structure", "compare_categories", "hbar"),
                _q(2, "trajectory", "change_over_time", "hbar"),
                _q(3, "momentum", "compare_two_points", "grouped_bar")])
    r = decision.validate(bad)
    assert not r["ok"]
    assert any("不能表达 change_over_time" in e for e in r["errors"])


def test_validate_rejects_unknown_chart_type():
    bad = _ctr([_q(1), _q(2, "trajectory", "change_over_time", "line"),
                _q(3, "momentum", "compare_two_points", "nope")])
    r = decision.validate(bad)
    assert not r["ok"]
    assert any("48 型" in e for e in r["errors"])


def test_choose_chart_follows_comparison_and_fills_contract():
    q = _q(1, "structure", "compare_categories", "hbar")
    chart = decision.choose_chart({"bars": [{"label": "a", "value": 1.0},
                                            {"label": "b", "value": -1.0}],
                                   "title": "a 1.0、b -1.0",
                                   "unit_meta": "%", "source": "证据包"}, q)
    assert chart["type"] in decision.CHART_POLICY["compare_categories"]
    assert chart["policy"]["comparison"] == "compare_categories"
    assert decision.chart_contract_ok(chart)["ok"]


def test_choose_chart_adapts_items_to_a_bar():
    """只有 items 的 payload：v11 起会适配成 hbar（画出真数据），而不是拒绝。

    旧行为是「要求 grouped_bar 就只画 grouped_bar」，于是同一份 items 在
    compare_two_points 下被判定「无法编码」而丢图；P4 扩了 allowed 列表后
    应该退到能表达 items 的图型，而不是不画。
    """
    q = _q(1, "momentum", "compare_two_points", "grouped_bar")
    chart = decision.choose_chart({"items": [{"label": "a", "value": 1.0},
                                             {"label": "b", "value": 2.0}],
                                   "title": "a 1.0、b 2.0", "unit_meta": "%",
                                   "source": "证据包"}, q)
    assert chart["type"] == "hbar"
    assert chart["policy"]["fallback"] is True     # 换了图型就要留痕
    assert chart.get("bars")


def test_choose_chart_refuses_when_payload_cannot_be_encoded():
    """连一个数据点都没有 → 不硬画，标 unsupported。"""
    q = _q(1, "momentum", "compare_two_points", "grouped_bar")
    chart = decision.choose_chart({"items": [], "title": "t"}, q)
    assert chart["policy"]["fallback"] is True
    assert chart["policy"]["unsupported"] is True
    assert chart["type"] == ""


def test_bind_counts_declared_not_answered():
    ctr = _ctr([_q(1, "structure"), _q(2, "economics"), _q(3, "headcount")])
    findings = {"structure": object(), "economics": object()}
    plan = {"skipped": [{"key": "headcount", "missing": ["table.headcount"]}]}
    b = decision.bind(ctr, findings, plan)
    assert (b["declared"], b["answered"]) == (3, 2)
    assert b["binding"] == pytest.approx(0.667, abs=1e-3)
    assert b["unanswered"][0]["finding"] == "headcount"
    assert b["unanswered"][0]["reason"] == "no_data"
    assert b["verdict"] == "PARTIAL"


def test_chart_contract_rejects_missing_proof_fields():
    r = decision.chart_contract_ok({"type": "hbar", "title": "t"})
    assert not r["ok"]
    assert any("claim_to_prove" in e for e in r["errors"])


def test_synth_from_table_only_uses_existing_numbers():
    table = {"caption": "c", "columns": [{"text": "品类"}, {"text": "值"}],
             "rows": [[{"text": "a"}, {"text": "1.5 元"}],
                      [{"text": "b"}, {"text": "-2.5 元"}],
                      [{"text": "c"}, {"text": "3.5 元"}]]}
    c = decision.synth_from_table(table)
    assert [i["value"] for i in c["items"]] == [1.5, -2.5, 3.5]
    assert decision.synth_from_table({"rows": []}) is None


@pytest.mark.skipif(os.environ.get("GUAGUA_DECISION_IT") != "1",
                    reason="需要完整项目与 r01 子进程；设 GUAGUA_DECISION_IT=1 才跑")
def test_decision_build_end_to_end(tmp_path):
    from core import decision_report
    proj = os.environ.get("GUAGUA_DECISION_PROJECT")
    if not proj or not os.path.isdir(proj):
        pytest.skip("缺 GUAGUA_DECISION_PROJECT")
    res = decision_report.build("经营诊断", proj, str(tmp_path / "out"))
    assert res["declared"] >= 3
    assert res["binding"] == pytest.approx(res["answered"] / res["declared"], abs=1e-3)
    man = json.loads((tmp_path / "out" / "manifest.json").read_text(encoding="utf-8"))
    assert man["gates"]["binding"] in ("pass", "block")

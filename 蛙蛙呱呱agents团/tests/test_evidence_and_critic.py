# -*- coding: utf-8 -*-
"""证据图 / 论证规划 / 盲评的硬规则。"""
from __future__ import annotations

from core import argument_plan, evidence_graph, prose_critic, spec_extract


def _graph():
    return evidence_graph.build(
        [{"id": "S01", "title": "测试来源", "url": "https://example.com", "grade": "A"}],
        [{"id": "C1", "section": "s1", "text": "规模 100 亿元，同比 10%",
          "evidence": [{"source_id": "S01", "stance": "supports",
                        "quote": "规模 100 亿元，同比 10%", "span": "p.1"}],
          "rival": "只是促销", "discriminator": "下一期是否 10%",
          "action": "先做 1 个 SKU", "boundary": "全国口径"}])


def test_evidence_graph_valid():
    g = _graph()
    assert not evidence_graph.validate(g)
    assert evidence_graph.traceability(g)["rate"] == 1.0


def test_evidence_graph_missing_quote():
    g = _graph()
    g["claims"][0]["evidence"][0]["quote"] = ""
    assert evidence_graph.validate(g)


def test_audit_text_catches_unquoted_number():
    g = _graph()
    r = evidence_graph.audit_text("规模 100 亿元，新增 7 亿元", g)
    assert "7" in r["missing"]


def test_spec_extract():
    sp = spec_extract.extract(_graph())
    assert sp["s1"]["verdict"].startswith("规模")
    assert sp["s1"]["boundary"] == "全国口径"


def test_argument_plan_types_and_validation():
    sections = [{"id": f"s{i}", "kicker": k} for i, k in
                enumerate(["规模", "覆盖", "渠道", "竞争", "风险", "情景", "路径"], 1)]
    p = argument_plan.plan(sections, _graph())
    assert len({x["type"] for x in p["sections"]}) >= 5
    p1 = argument_plan.plan([sections[0]], _graph())
    assert not [e for e in argument_plan.validate(p1) if "缺" in e]


def test_critic_scores_and_repeats():
    body = ("判断：先做分拨。事实：2024 年 6871 亿元，同比 16.0%。"
            "解释：因为渠道费用 25%，所以先做轻资产。"
            "判别：如果单店月销低于 3000 元，就停；反方是价格战。"
            "边界：只覆盖家庭零售。") * 8
    r = prose_critic.score(body)
    assert r["score"] >= 85
    rep = prose_critic.repeats([body, body, body], min_count=3)
    assert rep

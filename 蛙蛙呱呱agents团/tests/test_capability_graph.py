# -*- coding: utf-8 -*-
"""能力图与问题库的回归测试（升级 P2）。"""
from __future__ import annotations

from core import capability_graph as cg
from core import question_library as ql


def test_graph_has_20_roles_and_expected_blocked():
    g = cg.build()
    assert g["counts"]["roles"] == 20
    assert g["counts"]["report_roles"] == 16
    assert set(g["counts"]["blocked_roles"]) == {"r08", "r09", "r10", "r17"}
    assert set(g["counts"]["simulated_roles"]) == {"r11", "r14"}
    assert g["roles"]["r09"]["status"] == "blocked"
    assert g["roles"]["r06"]["status"] == "real"


def test_every_capability_has_valid_status():
    g = cg.build()
    allowed = {"real", "simulated", "blocked", "missing"}
    for key, cap in g["capabilities"].items():
        assert cap["status"] in allowed, (key, cap["status"])
        assert cap["providers"], key


def test_known_capability_status():
    g = cg.build()
    assert g["capabilities"]["market.trend"]["status"] == "real"
    assert g["capabilities"]["tech.spec"]["status"] == "blocked"
    assert g["capabilities"]["brand.consistency"]["status"] == "simulated"


def test_question_library_each_role_has_3_to_5():
    assert len(ql.QUESTIONS) >= 60
    for role in ql.ROLE_QUESTIONS:
        n = len(ql.by_role(role))
        assert 3 <= n <= 5, (role, n)


def test_question_ids_unique_and_groups_valid():
    ids = [q["id"] for q in ql.QUESTIONS]
    assert len(ids) == len(set(ids))
    groups = {"demand", "supply", "competition", "finance", "risk"}
    for q in ql.QUESTIONS:
        assert q["group"] in groups, q
        assert q["capability"]
        assert q["text"]


def test_every_capability_has_v9_dimension():
    from core import report_framework as rf
    assert ql.summary()["without_v9_dimension"] == []
    dims = {d["key"] for d in rf.DIMENSIONS}
    assert {"org", "tech", "reliability", "transaction", "content", "data"} <= dims
    for q in ql.QUESTIONS:
        assert q["dimension"] in dims, q

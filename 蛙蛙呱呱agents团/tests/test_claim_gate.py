# -*- coding: utf-8 -*-
"""P9：ClaimCard 头条门禁。"""
from __future__ import annotations

from core import claim_gate


def _pack(grade="A", status="ok"):
    return {"source_records": [{"id": "S01", "grade": grade,
                               "quote_status": status}]}


def _draft():
    return {"intent": "是否继续做", "standfirst": "苹果涨了 3%",
            "falsifier": "若苹果跌幅超过 5%，本节作废",
            "sections": [{"refs": ["S01"]}]}


def test_headline_actionable_passes():
    d = _draft()
    info = claim_gate.apply(d, _pack())
    assert info["actionable"] is True
    assert d["standfirst"] == "苹果涨了 3%"


def test_headline_grade_c_demoted():
    d = _draft()
    info = claim_gate.apply(d, _pack(grade="C"))
    assert info["actionable"] is False and info["demoted"] is True
    assert d["standfirst"] == claim_gate.SAFE_HEADLINE
    assert "来源等级 > B" in " ".join(info["reasons"])


def test_headline_unverified_demoted():
    d = _draft()
    info = claim_gate.apply(d, _pack(status="unverified"))
    assert info["demoted"] is True
    assert "来源未核验" in " ".join(info["reasons"])


def test_headline_without_falsifier_demoted():
    d = _draft()
    d["falsifier"] = ""
    info = claim_gate.apply(d, _pack())
    assert info["demoted"] is True
    assert "没有 falsifier" in info["reasons"]


def test_section_falsifier_counts():
    d = _draft()
    d["falsifier"] = ""
    d["sections"][0]["falsifier"] = "若下期方向反转，本节作废"
    info = claim_gate.apply(d, _pack())
    assert info["actionable"] is True
    assert info["demoted"] is False

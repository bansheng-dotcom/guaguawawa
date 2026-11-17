# -*- coding: utf-8 -*-
"""ClaimCard schema 的回归测试（升级 P1）。"""
from __future__ import annotations

from core import claim_card as cc


def base_card(**over):
    card = {
        "id": "C01",
        "statement": "A 比 B 高 20%",
        "refs": ["S01#A=1.20", "S03#B=1.00"],
        "values": {"a": 1.20, "b": 1.00, "unit": "元/公斤"},
        "comparability": {
            "same_product": "yes",
            "same_period": "yes",
            "same_unit": "yes",
            "same_channel": "yes",
        },
        "rivals": [
            {"name": "等级差异", "status": "ruled", "evidence": "同等级"},
            {"name": "时点差异", "status": "partially_ruled", "evidence": "同日"},
        ],
        "falsifier": "同等级同规格价差 < 10%",
        "confidence": "medium",
        "grade": "B",
        "actionable": True,
        "headline": True,
        "decision": "是否做跨城套利",
        "owner": "r01",
        "expiry": "2026-12-31",
        "kind": "general",
    }
    card.update(over)
    return card


def test_valid_actionable_card_passes():
    r = cc.validate(base_card())
    assert r["ok"], r["errors"]
    assert r["normalized"]["comparability"]["same_product"] == "yes"


def test_headline_must_be_actionable():
    r = cc.validate(base_card(actionable=False))
    assert not r["ok"]
    assert any("headline" in e for e in r["errors"])


def test_actionable_rejects_unknown_comparability():
    c = base_card()
    c["comparability"]["same_product"] = "unknown"
    r = cc.validate(c)
    assert not r["ok"]
    assert any("same_product" in e for e in r["errors"])


def test_actionable_rejects_unruled_rival():
    c = base_card()
    c["rivals"].append({"name": "市场势力", "status": "unruled", "evidence": ""})
    r = cc.validate(c)
    assert not r["ok"]
    assert any("市场势力" in e for e in r["errors"])


def test_actionable_requires_falsifier():
    r = cc.validate(base_card(falsifier=""))
    assert not r["ok"]
    assert any("falsifier" in e for e in r["errors"])


def test_forecast_requires_expiry():
    r = cc.validate(base_card(expiry="", kind="forecast"))
    assert not r["ok"]
    assert any("expiry" in e for e in r["errors"])


def test_audit_counts_and_headline_gate():
    cards = [
        base_card(id="C01"),
        base_card(id="C02", headline=False, actionable=False),
        base_card(id="C03", headline=True, actionable=False),  # 应被 error 抓出
    ]
    a = cc.audit(cards)
    assert a["total"] == 3
    assert a["actionable"] == 1
    assert a["unidentified"] == 2
    assert a["headline_total"] == 2
    assert a["headline_actionable"] == 1
    assert not a["ok"]
    assert any(x["id"] == "C03" for x in a["errors"])

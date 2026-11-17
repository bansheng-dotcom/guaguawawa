# -*- coding: utf-8 -*-
"""覆盖度（替代 A/B 分支）的回归测试（升级 P2）。"""
from __future__ import annotations

from core import capability_graph as cg
from core import coverage


FRUIT = [
    {"id": "Q1", "text": "趋势", "capability": "market.trend"},
    {"id": "Q2", "text": "结构", "capability": "market.structure"},
    {"id": "Q3", "text": "节奏", "capability": "market.momentum"},
    {"id": "Q4", "text": "轨迹", "capability": "market.trajectory"},
    {"id": "Q5", "text": "贡献", "capability": "market.contribution"},
]


def test_fruit_five_questions_are_complete():
    res = coverage.compute(FRUIT, cg.build())
    assert res["coverage"] == 1.0
    assert res["verdict"] == "COMPLETE"
    assert res["summary"]["gaps"] == 0
    assert res["summary"]["covered_real"] == 5


def test_missing_capability_is_a_gap():
    res = coverage.compute([{"id": "Q1", "text": "不存在", "capability": "does.not.exist"}],
                           cg.build())
    assert res["verdict"] == "INCOMPLETE"
    assert res["coverage"] == 0.0
    assert res["questions"][0]["status"] == "missing"
    assert res["questions"][0]["gap"] is True


def test_simulated_scores_half_and_blocks_complete():
    res = coverage.compute([{"id": "Q1", "text": "品牌", "capability": "brand.consistency"}],
                           cg.build())
    assert res["coverage"] == 0.5
    assert res["verdict"] == "INCOMPLETE"
    assert res["questions"][0]["status"] == "simulated"
    assert res["questions"][0]["partial"] is True


def test_mixed_real_simulated_blocked_coverage():
    qs = FRUIT + [
        {"id": "Q6", "text": "品牌", "capability": "brand.consistency"},   # 0.5
        {"id": "Q7", "text": "技术", "capability": "tech.spec"},           # 0.0
    ]
    res = coverage.compute(qs, cg.build())
    assert res["coverage"] == round(5.5 / 7, 3)
    assert res["verdict"] == "INCOMPLETE"
    assert set(res["summary"]["gap_questions"]) == {"Q7"}

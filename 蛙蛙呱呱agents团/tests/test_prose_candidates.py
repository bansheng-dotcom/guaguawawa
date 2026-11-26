# -*- coding: utf-8 -*-
"""表达候选器（core/prose_candidates.py）回归。

守住三条：数字一致是硬判据、结果是确定性的、规则模式如实标降级。
"""
from __future__ import annotations

import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core import prose_candidates as pc  # noqa: E402
from core.report_prose_gen import generate  # noqa: E402

UNIT = {
    "id": "s1", "kicker": "礼盒",
    "verdict": "判断：先做礼盒而不是散装。",
    "fact": "2024 年礼盒 6871 万元、同比 16.0%。",
    "evidence": "比散装快 11.5pp。",
    "mechanism": "客户要送礼，包装即决策。",
    "alternative": "不是总量扩张，而是结构迁移。",
    "signal": "下一期礼盒占比是否继续上升。",
    "implication": "先保住礼盒陈列。",
    "action": "先上 1 个 SKU。",
    "stop": "毛利低于 25%。",
    "boundary": "只覆盖家庭零售。",
    "review_points": ["礼盒", "毛利"],
}


def test_numbers_multiset_and_equality():
    assert pc.norm_numbers("1,000 元与 2 个") == ["1000", "2"]
    assert pc.same_numbers("同比 16.0%，规模 6871", "规模 6871，同比 16.0%")
    assert not pc.same_numbers("同比 16.0%", "同比 17.0%")


def test_render_is_deterministic_and_keeps_blocks():
    a = pc.render(UNIT, 1, 2)
    b = pc.render(UNIT, 1, 2)
    assert a == b
    for word in ("结论", "事实", "机理", "反例", "所以"):
        assert word in a


def test_rule_candidates_share_numbers():
    cands = pc.rule_candidates(UNIT, n=3)
    assert len(cands) == 3
    base = pc.render(UNIT, 0, 0)
    for c in cands:
        assert pc.same_numbers(c["text"], base)
        assert pc.jaccard(c["text"], base) > 0  # 同源，必然有重合


def test_select_rule_mode_marks_degraded_honestly():
    res = pc.select(UNIT)
    assert res["mode"] == "rule"
    assert "no_model_single_variant" in res["degraded_reasons"]
    assert res["text"] == res["chosen"]["text"]
    assert pc.same_numbers(res["text"], pc.render(UNIT, 0, 0))
    assert 0.0 <= res["similarity_median"] <= 1.0


def test_numbers_mismatch_candidate_is_rejected():
    def bad_client(prompt: str) -> str:
        return "结论：规模 9999 万元。\n===\n结论：先做礼盒。\n===\n结论：先做礼盒，但毛利低于 25% 就停。"

    res = pc.select(UNIT, client=bad_client)
    reasons = [r["reason"] for r in res["rejected"]]
    assert "numbers_mismatch" in reasons
    assert res["mode"] == "llm"
    # 选中的正文仍然与基准数字一致（不会把模型编的数带出去）
    assert pc.same_numbers(res["text"], pc.render(UNIT, 0, 0))


def test_ban_orders_avoids_prev_structure():
    res = pc.select(UNIT, ban_orders=(0, 2))
    assert res["chosen"]["order"] not in (0, 2)


def test_generate_records_candidates(tmp_path):
    sections = [{"id": "s1", "kicker": "礼盒", "verdict": UNIT["verdict"]}]
    specs = {"s1": {k: UNIT[k] for k in (
        "verdict", "fact", "evidence", "mechanism", "alternative",
        "signal", "implication", "action", "stop", "boundary")}}
    rec = tmp_path / "cands.json"
    bodies = generate(sections, specs, record_path=str(rec))
    assert bodies["s1"]
    assert rec.is_file()
    import json
    doc = json.loads(rec.read_text(encoding="utf-8"))
    assert doc["s1"]["mode"] in ("rule", "llm")
    assert doc["s1"]["chosen"]

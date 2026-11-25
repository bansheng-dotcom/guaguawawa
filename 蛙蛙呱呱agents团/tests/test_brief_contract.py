# -*- coding: utf-8 -*-
"""expert_brief v2 契约：七层、五门槛、18 条上限、卡不写验收。"""
from __future__ import annotations

import tempfile
from pathlib import Path

from shared.knowledge import brief as B


def _card(task_type: str | None = None) -> dict:
    return {"task_id": "t-r06", "owner": "r06", "title": "测试卡",
            "goal": "测试 brief 契约", "question": "测试 brief 契约",
            "task_type": task_type, "skills": [], "non_goals": ["不编事实"]}


def test_build_covers_all_task_types():
    for task_type in B.TASK_LAYERS:
        eb = B.build_brief(_card(task_type), "r06")
        assert eb["task_type"] == task_type
        assert not B.validate_brief(eb, task_type), (task_type, eb)


def test_cap_18_and_parking_lot():
    eb = B.build_brief(_card("决策型"), "r06")
    assert len(eb["must_answer"]) <= B.MAX_MUST_ANSWER
    assert eb["parking_lot"], "决策型超过上限的部分应进 parking_lot"
    total = len(eb["must_answer"]) + len(eb["parking_lot"])
    assert total == 19, "被裁掉的问题不能凭空消失"


def test_five_gates_present():
    eb = B.build_brief(_card("诊断型"), "r06")
    for m in eb["must_answer"]:
        for key in ("answerable_by", "evidence", "owner",
                    "failure_impact", "check"):
            assert str(m.get(key) or "").strip(), (m["id"], key)
        assert m["answerable_by"] in B.ANSWERABLE


def test_card_must_not_carry_acceptance():
    eb = B.build_brief(_card("诊断型"), "r06")
    bad = {"brief_ref": "x", "brief_version": "v2", "acceptance": ["有图"]}
    assert B.validate_bundle(bad, eb), "卡写 acceptance 必须被拒收"
    ok = {"brief_ref": "x", "brief_version": "v2"}
    assert not B.validate_bundle(ok, eb)


def test_brief_rejects_facts():
    eb = B.build_brief(_card("诊断型"), "r06")
    dirty = dict(eb, standards=list(eb["standards"]) + ["市场规模 1200 亿元"])
    assert B.validate_brief(dirty, "诊断型")


def test_issue_bundle_without_project():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "cards" / "r06"
        res = B.issue_bundle(d, "r06", "t-r06", "测试")
        assert not res["problems"]
        assert (d / "bundle.json").is_file()
        assert res["bundle"]["card"]["brief_ref"].endswith("bundle.json#brief")

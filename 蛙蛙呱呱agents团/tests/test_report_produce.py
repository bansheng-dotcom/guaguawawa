# -*- coding: utf-8 -*-
"""v3 报告产线：技能注册表 / 章节计划 / 证据图 / 评测 的单元测试。"""
from __future__ import annotations

import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
for _p in (str(TEAM), str(TEAM.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core import report_produce, skill_graph  # noqa: E402


def test_skill_graph_covers_20_roles():
    rows = skill_graph.load()
    roles = {r["role"] for r in rows}
    assert len(roles) == 20
    assert len(rows) >= 180
    c = skill_graph.contract("r05", "sizing", "size")
    assert c["ok"] and "size" in c["actions"]
    assert skill_graph.contract("r06", "describe")["ok"]


def test_plan_declares_needs_and_inputs():
    p = report_produce.plan("market_research", str(TEAM.parent / "家居百货内蒙调研_2026-11-15"))
    assert len(p["sections"]) >= 3
    skills = {n["skill"] for s in p["sections"] for n in s["needs"]}
    assert "sizing" in skills and "describe" in skills
    assert all("question" in s for s in p["sections"])


def test_claims_and_conflicts_from_synthetic_runs():
    runs = [
        {"need": {"role": "r05", "skill": "sizing", "action": "size"}, "ok": True,
         "result": {"tam": 301.94, "variance": 0.0002,
                    "by_scenario": [{"scenario": "base", "sam": 271.74, "som": 13.59}],
                    "provenance": {"input_hash": "abc"}}},
        {"need": {"role": "r06", "skill": "describe"}, "ok": True,
         "result": {"describe": {"growth": {"mean": 0.0745, "median": 0.047}},
                    "provenance": {"input_hash": "def"}}},
        {"need": {"role": "r06", "skill": "correlate"}, "ok": False,
         "gap": "缺输入", "result": {}},
    ]
    c = report_produce.build_claims(runs)
    assert c["real"] >= 3
    assert c["gaps"] == 1
    assert all(x["id"].startswith("C") for x in c["claims"] if x["id"])
    assert any("均值" in x["text"] for x in c["claims"])


def test_draft_and_judge():
    plan = report_produce.plan("market_research", str(TEAM))
    runs = [
        {"need": {"role": "r06", "skill": "describe"}, "ok": True,
         "result": {"describe": {"growth": {"mean": 0.0745, "median": 0.047}},
                    "provenance": {"input_hash": "x"}}},
        {"need": {"role": "r06", "skill": "describe"}, "ok": True,
         "result": {"describe": {"share": {"mean": 0.125, "median": 0.0961}},
                    "provenance": {"input_hash": "y"}}},
    ]
    claims = report_produce.build_claims(runs)
    draft = report_produce.draft_from_claims(plan, claims, {"numbers": []})
    assert draft["sections"] and draft["standfirst"]
    trace = {"covered": {"skills": 2, "roles": 1}}
    j = report_produce.judge(draft, claims, trace, min_roles=1)
    assert j["score"] >= 60 and j["pass"]

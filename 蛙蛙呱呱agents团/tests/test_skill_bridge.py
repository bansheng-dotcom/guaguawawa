# -*- coding: utf-8 -*-
"""技能接入：领域方法必须落到现有技能，不能另起一套。"""
from __future__ import annotations

import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core import skill_bridge  # noqa: E402


def test_all_methods_have_landing():
    c = skill_bridge.coverage()
    assert c["total"] == 120
    assert not c["missing"], c["missing"]
    assert c["coverage_rate"] >= 0.95
    assert c["counts"]["exact"] >= 50
    assert c["counts"]["new"] <= 5


def test_statistics_methods_use_r06_skills():
    assert skill_bridge.info("r06", "DiD")["skill"] == "did"
    assert skill_bridge.info("r06", "DiD")["fit"] == "exact"
    assert skill_bridge.info("r06", "A/B 检验")["skill"] == "abtest"
    assert skill_bridge.info("r06", "弹性")["skill"] == "elasticity"
    assert skill_bridge.info("r06", "队列留存")["action"] == "cohort"


def test_supply_methods_use_r15_skills():
    assert skill_bridge.info("r15", "TCO")["skill"] == "tco"
    assert skill_bridge.info("r15", "安全库存")["skill"] == "safety-stock"


def test_two_new_methods_are_declared():
    new = [(r, m) for r, items in skill_bridge.skill_map()["roles"].items()
           for m, x in items.items() if x["fit"] == "new"]
    assert len(new) <= 5
    assert all(skill_bridge.info(r, m)["note"] for r, m in new)


def test_commands_are_real_cli():
    cmds = skill_bridge.commands("r06")
    assert any("call r06 -- did" in c for c in cmds)
    assert any("call r06 -- abtest" in c for c in cmds)

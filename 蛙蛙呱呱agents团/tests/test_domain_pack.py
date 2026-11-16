# -*- coding: utf-8 -*-
"""领域包与业务线编排：20 角色、行业匹配、任务编队、作战计划。"""
from __future__ import annotations

import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core import domain_pack  # noqa: E402


def test_twenty_role_packs_are_complete():
    roles = domain_pack.load_roles()
    assert len(roles) == 20
    for rid, r in roles.items():
        assert len(r["books"]) >= 5
        assert any(b["lang"] == "en" for b in r["books"])
        assert any(b["lang"] == "zh" for b in r["books"])
        assert len(r["methods"]) >= 6
        assert len(r["kpis"]) >= 6 and len(r["decisions"]) >= 4
        assert len(r["failure_modes"]) >= 4 and len(r["report_sections"]) >= 6


def test_industry_match_for_energy_retail():
    ind = domain_pack.match_industry("县域加油站非油业务增长")
    assert ind["name"].startswith("能源零售")
    assert "进站率" in "".join(ind["kpis"])


def test_task_force_for_gas_station():
    roles = domain_pack.load_roles()
    ind = domain_pack.match_industry("县域加油站非油业务增长")
    picked = domain_pack.score_roles("县域加油站非油业务增长", roles, ind)
    ids = {p["role"] for p in picked}
    assert {"r01", "r06", "r14", "r15"} <= ids
    assert len(picked) <= 5


def test_plan_contains_methods_and_design():
    p = domain_pack.plan("社区母婴连锁增长")
    assert p["industry"]["hypothesis"]
    methods = {m["method"] for m in p["analysis_design"]}
    assert {"decompose_mix_rate", "ab_proportion / ab_mean", "did_twfe + event_study + placebo"} <= methods
    md = domain_pack.to_markdown(p)
    for token in ("任务编队", "指标树", "分析设计", "三种情景", "90 天验证", "数据清单", "停止条件"):
        assert token in md
    # 不编项目数字：行业基准必须带「校准」
    assert "需校准" in md or "需按" in md

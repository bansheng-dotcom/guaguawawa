# -*- coding: utf-8 -*-
"""v12：调研交付契约（不含行业清单）。

历史的错法（两次）：
    1. 每个行业一个方法包（market.py / cheese.py / seasoning.py）——换行业要写代码；
    2. 一张固定的研究模块表（盘子/结构/玩家/渠道/价格/需求/政策/进入）——
       换任务要挑模块，本质还是「预先列举」。
现在的做法：只规定「怎么算合格」（结论字段、来源等级、四段结构、交叉质询），
「研究什么」交给执行者按任务判断。测试断言这个边界，防止清单再长回来。
"""
from __future__ import annotations

from core import claim_consistency as CC
from core import research_protocol as RP


def test_plan_has_no_module_list():
    """不许再有研究模块清单：这是本版的核心约束。"""
    p = RP.plan("内蒙古调味料市场调研")
    assert "modules" not in p, "研究模块清单已删除，不许恢复"
    assert p["what_to_research"].startswith("由执行者")


def test_claim_contract_is_complete():
    p = RP.plan("任意业务线")
    fields = [c["field"] for c in p["claim_contract"]]
    for must in ("claim", "value", "quote", "url", "grade", "falsifier",
                 "boundary"):
        assert must in fields, f"结论契约缺 {must}"


def test_report_shape_serves_four_readers():
    """一人公司：老板/团队/客户/自己 四类用途必须同时被覆盖。"""
    p = RP.plan("任意业务线")
    parts = {s["part"] for s in p["report_shape"]}
    assert {"决策页", "判断", "执行清单", "证据", "边界"} <= parts


def test_review_rules_cover_conflict_and_grade():
    p = RP.plan("任意业务线")
    ids = {r["id"] for r in p["review_rules"]}
    assert {"C1", "C2", "C3", "C4"} == ids


def test_lane_switches_when_data_given():
    assert RP.plan("x").get("data_lane") == "web"
    assert RP.plan("x", project_dir=".")["data_lane"] == "given"
    assert "清洗" in RP.plan("x", project_dir=".")["lane_note"]


def test_markdown_contains_contract_not_industries():
    md = RP.to_markdown(RP.plan("内蒙古预制菜"))
    assert "一条结论必须长这样" in md
    assert "盘子多大" not in md, "方法论清单不该再出现在任务书里"


def _claims(**kw):
    base = {
        "numbers": [
            {"id": "N1", "name": "全国规模", "value": 4850, "period": "2024",
             "source_file": "S1"},
        ],
        "sources": [{"file": "S1", "grade": "B"}],
        "standfirst": "规模 4850 亿元。",
        "sections": [{"refs": ["N1"]}],
        "boundaries": ["没有省级实测值"],
    }
    base.update(kw)
    return base


def test_consistency_passes_on_clean_claims():
    res = CC.check(_claims())
    assert res["ok"] is True


def test_consistency_blocks_unexplained_conflict():
    """同一指标同期两个值，不解释口径差就不许过。"""
    c = _claims()
    c["numbers"].append({"id": "N2", "name": "全国规模", "value": 6831.6,
                         "period": "2024", "source_file": "S1"})
    res = CC.check(c)
    assert res["ok"] is False
    assert res["issues"]["C1_unexplained_conflict"] == 1


def test_consistency_allows_explained_conflict():
    c = _claims()
    c["numbers"].append({"id": "N2", "name": "全国规模", "value": 6831.6,
                         "period": "2024", "source_file": "S1"})
    c["conflicts"] = [{"name": "全国规模", "reason": "艾媒 vs 网经社，口径不同"}]
    res = CC.check(c)
    assert res["ok"] is True
    assert res["conflicts_resolved"]


def test_consistency_blocks_missing_boundary():
    res = CC.check(_claims(boundaries=[]))
    assert res["issues"]["C4_no_boundary"] == 1


def test_consistency_different_period_is_not_conflict():
    c = _claims()
    c["numbers"].append({"id": "N3", "name": "全国规模", "value": 3626,
                         "period": "2023", "source_file": "S1"})
    assert CC.check(c)["issues"]["C1_unexplained_conflict"] == 0

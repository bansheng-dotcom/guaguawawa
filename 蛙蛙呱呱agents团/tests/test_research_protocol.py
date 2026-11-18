# -*- coding: utf-8 -*-
"""v12：一句话 → 研究方案；结论 → 交叉质询。

这两件是「不用用户定义研究问题、也不许报告自相矛盾」的实现。
测试只断言契约，不断言具体文案。
"""
from __future__ import annotations

from core import claim_consistency as CC
from core import research_protocol as RP


def test_plan_covers_professional_modules():
    """任何业务线都必须覆盖：盘子/玩家/渠道/价格/政策/进入 六个基础模块。"""
    p = RP.plan("内蒙古调味料市场调研")
    keys = [m["key"] for m in p["modules"]]
    for must in ("market_size", "players", "channel", "price_band",
                 "policy", "entry"):
        assert must in keys, f"缺基础模块 {must}"
    assert p["business_line"] == "调味料"
    assert p["data_lane"] == "web"
    assert "r04" in p["experts"], "必须有独立评审角色"


def test_plan_is_stable_and_extends_by_keyword():
    """同一意图两次生成必须一致；关键词只加模块，不减模块。"""
    a = RP.plan("内蒙古调味料市场调研")
    b = RP.plan("内蒙古调味料市场调研")
    assert [m["key"] for m in a["modules"]] == [m["key"] for m in b["modules"]]

    base = [m["key"] for m in a["modules"]]
    more = RP.plan("内蒙古调味料渠道竞争格局、毛利与消费场景分析")
    keys = [m["key"] for m in more["modules"]]
    assert set(base) <= set(keys), "关键词只能加模块，不能删"
    assert "structure" in keys and "demand" in keys


def test_plan_lane_switches_when_data_given():
    p = RP.plan("内蒙古调味料", project_dir=".")
    assert p["data_lane"] == "given"
    assert "清洗" in p["lane_note"]


def test_plan_markdown_has_every_module():
    md = RP.to_markdown(RP.plan("内蒙古预制菜，做不做"))
    for m in RP.plan("内蒙古预制菜，做不做")["modules"]:
        assert m["name"] in md


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
    assert res["issues"]["C1_unexplained_conflict"] == 0


def test_consistency_blocks_unexplained_conflict():
    """同一指标同期两个值，不解释口径差就不许过（这是真实发生过的事故）。"""
    c = _claims()
    c["numbers"].append({"id": "N2", "name": "全国规模", "value": 6831.6,
                         "period": "2024", "source_file": "S1"})
    res = CC.check(c)
    assert res["ok"] is False
    assert res["issues"]["C1_unexplained_conflict"] == 1


def test_consistency_allows_explained_conflict():
    """解释了口径差就放行——冲突本身不是错，沉默才是。"""
    c = _claims()
    c["numbers"].append({"id": "N2", "name": "全国规模", "value": 6831.6,
                         "period": "2024", "source_file": "S1"})
    c["conflicts"] = [{"name": "全国规模",
                       "reason": "艾媒 4850 亿元 vs 网经社 6831.6 亿元，口径不同"}]
    res = CC.check(c)
    assert res["ok"] is True
    assert res["conflicts_resolved"], "已解释的冲突要留痕"


def test_consistency_blocks_missing_boundary():
    res = CC.check(_claims(boundaries=[]))
    assert res["ok"] is False
    assert res["issues"]["C4_no_boundary"] == 1


def test_consistency_flags_d_only_numbers():
    c = _claims()
    c["sources"] = [{"file": "S1", "grade": "D"}]
    res = CC.check(c)
    assert res["issues"]["C2_d_only_numbers"] == 1


def test_consistency_different_period_is_not_conflict():
    c = _claims()
    c["numbers"].append({"id": "N3", "name": "全国规模", "value": 3626,
                         "period": "2023", "source_file": "S1"})
    res = CC.check(c)
    assert res["issues"]["C1_unexplained_conflict"] == 0

# -*- coding: utf-8 -*-
"""P2：专家编排的硬规矩（意图绑定 / 数据齐备 / BLOCKED / 兜底）。

这是修「问招聘答水果」的回归测试：三条断言必须在 CI 里常绿。
"""
from __future__ import annotations

from core import orchestrator as O
from core.methods.spec import Caps


def _method_plan(mounted=(), skipped=()):
    return {"mounted": [{"key": k} for k in mounted],
            "skipped": [{"key": k, "missing": list(m)} for k, m in skipped]}


def test_experts_file_exists_and_has_twenty_roles():
    ex = O.load_experts()
    roles = ex.get("roles") or {}
    assert len(roles) == 20
    for rid in ("r06", "r15", "r16"):
        assert roles[rid]["methods"], f"{rid} 没有声明可答方法"


def test_hiring_intent_with_price_data_is_unbound():
    """问招聘 + 只有价格数据 → 必须 unbound，且说出缺 table.headcount。"""
    plan = _method_plan(mounted=["structure", "trajectory", "economics"],
                        skipped=[("headcount", ["table.headcount"])])
    d = O.plan("招聘编制与组织设计", method_plan=plan)
    assert d["mode"] == "unbound"
    assert "headcount" in d["reason"]
    blocked = {r["role"] for r in d["blocked"]}
    assert "r16" in blocked


def test_price_intent_selects_price_experts():
    """水果经营诊断 + 价格数据 → 命中 r06（且不被 r16 抢走）。"""
    plan = _method_plan(mounted=["structure", "trajectory", "momentum",
                                 "contribution", "economics", "transmission",
                                 "arbitrage", "breakeven"])
    d = O.plan("内蒙古三城水果经营诊断", method_plan=plan)
    assert d["mode"] == "intent"
    assert [r["role"] for r in d["roster"]] == ["r06"]


def test_procurement_intent_pulls_supply_expert():
    """停采换源/提价 → r15 必须出场，且相关度高于「只命中水果」的 r06。"""
    plan = _method_plan(mounted=["structure", "economics", "transmission",
                                 "arbitrage", "breakeven"])
    d = O.plan("内蒙古三城水果：停采换源还是提价", method_plan=plan)
    roles = [r["role"] for r in d["roster"]]
    assert "r15" in roles
    by_role = {r["role"]: r for r in d["rows"]}
    assert by_role["r15"]["relevance"] > by_role["r06"]["relevance"]
    assert {"停采", "换源", "提价"} & set(by_role["r15"]["hits"])


def test_refuses_are_excluded_even_if_keywords_match():
    """r16 声明不答「价格行情」→ 提到价格也不能让它出场。"""
    plan = _method_plan(mounted=["headcount", "structure"])
    d = O.plan("价格行情分析", method_plan=plan)
    assert "r16" not in [r["role"] for r in d["roster"]]


def test_unrelated_intent_falls_back_to_data_mode():
    """完全不相关的一句话 → data 兜底（auto），而不是硬塞专家。"""
    d = O.plan("帮我写一首关于秋天的诗", method_plan=_method_plan(mounted=["structure"]))
    assert d["mode"] == "data"
    assert d["roster"] == []


def test_readiness_uses_method_plan():
    ex = O.load_experts()["roles"]["r06"]
    full = O.readiness(ex, _method_plan(mounted=ex["methods"]))
    none = O.readiness(ex, _method_plan(skipped=[(k, ["price.series2"]) for k in ex["methods"]]))
    assert full["readiness"] == 1.0
    assert none["readiness"] == 0.0
    assert "price.series2" in none["missing"]


def test_role_without_methods_is_review_only_not_selected():
    """无方法的角色不许进数据 roster（2026-11-19 体检：它会被选中却答不了）。

    旧病：r11/r19/r03 readiness=1.0 → 选中 → 出题 0 个 → 静默回退数据题库。
    新规矩：标 review_only + blocked；命中的专家全答不了 → 整份 unbound。
    """
    ex = O.load_experts()["roles"]["r11"]
    assert not ex["methods"], "r11 若新增了方法，这条用例要改成换一个无方法角色"
    d = O.plan("小红书笔记怎么写才能带货",
               method_plan=_method_plan(mounted=["structure", "trajectory"]))
    rows = {r["role"]: r for r in d["rows"]}
    assert rows["r11"]["status"] == "blocked"
    assert rows["r11"].get("review_only") is True
    assert rows["r11"]["why"].startswith("该角色没有可进报告的方法")
    assert d["mode"] == "unbound"
    assert "r11" in d["reason"]

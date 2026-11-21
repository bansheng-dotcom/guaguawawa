# -*- coding: utf-8 -*-
"""v12.2：名册生成 + 发卡/收卡流水线。

断言三件事：
    1. 名册从角色目录生成，带技能与动作（不是手写清单）；
    2. 发卡给每个可进报告的角色一张，卡里只带契约不带题目；
    3. 收卡会验完整性：缺数字/缺来源/缺证伪的卡不合并。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from core import dispatch, roster

TMP = Path("workspace/_test_dispatch")


def setup_module(module):
    shutil.rmtree(TMP, ignore_errors=True)


def test_roster_is_generated_with_skills():
    r = roster.build()
    assert r["count"] == 20
    assert r["totals"]["actions"] > 150
    assert r["totals"]["skills"] > 100
    assert r["totals"]["report_roles"] == 16
    r05 = r["roles"]["r05"]
    assert r05["enters_report"] is True
    assert r05["actions"], "名册必须带动作，否则调不到技能"
    assert r05["skills"], "名册必须带技能包"


def test_roster_find_action_reverse_lookup():
    r = roster.build()
    hits = roster.find_action(r, "研究")
    assert hits, "反查「研究」应能找到角色"
    assert all(h["role"] for h in hits)


def test_brief_writes_one_card_per_report_role():
    res = dispatch.write_cards("测试用：某行业怎么做", str(TMP))
    assert res["cards"] == 16
    r05 = TMP / "cards" / "r05" / "TASK.md"
    assert r05.is_file()
    text = r05.read_text(encoding="utf-8")
    assert "你要判断什么（自己定" in text
    assert "claims.json" in text
    # 卡里不许出现预设题目
    assert "盘子多大" not in text


def test_collect_rejects_incomplete_card():
    dispatch.write_cards("测试用", str(TMP))
    bad = TMP / "cards" / "r05" / "claims.json"
    bad.write_text(json.dumps({"role": "r05", "numbers": [],
                               "sources": [], "sections": []},
                              ensure_ascii=False), encoding="utf-8")
    merged, problems = dispatch.collect(str(TMP))
    assert problems, "空卡必须被拒"
    assert any("r05" in p for p in problems)


def test_collect_flags_missing_cards_when_strict():
    """覆盖门禁：发了 16 张卡只交 1 张，严格模式必须失败（2026-11-19 体检）。"""
    shutil.rmtree(TMP, ignore_errors=True)
    dispatch.write_cards("测试用", str(TMP))
    card = {
        "role": "r05",
        "numbers": [{"id": "N1", "name": "规模", "value": 100.0,
                     "unit": "亿元", "period": "2024", "source_file": "S1"}],
        "sources": [{"file": "S1", "title": "t", "org": "o",
                     "url": "https://example.com/s1", "date": "2026-11-19",
                     "grade": "A", "quote": "原文：规模 100.0 亿元，同比 12.0%。"}],
        "sections": [{"title": "规模 100.0 亿元", "refs": ["N1"],
                      "reading": [{"text": "观察：100.0 亿元", "refs": ["N1"]},
                                  {"text": "机理：判别方法是…", "refs": ["N1"]}],
                      "falsifier": "若偏离超过 10.0% 则作废"}],
        "boundaries": ["没有省级数据"],
    }
    (TMP / "cards" / "r05" / "claims.json").write_text(
        json.dumps(card, ensure_ascii=False), encoding="utf-8")

    merged, problems = dispatch.collect(str(TMP), require_all=True)
    assert merged["coverage"]["expected"] == 16
    assert merged["coverage"]["delivered"] == 1
    assert any("缺卡" in p for p in problems), problems
    assert "r16" in merged["coverage"]["missing"]

    # 2026-11-22：默认已改为硬门（没 issued.json 就拒收）。
    blocked, probs_blocked = dispatch.collect(str(TMP))
    assert any("没有 issued.json" in p for p in probs_blocked), probs_blocked

    # 显式 legacy 才回到「只留痕」的老行为，并在产物上标降级。
    lenient, problems2 = dispatch.collect(str(TMP), allow_legacy=True)
    assert not problems2, "显式 legacy 时只在 coverage 留痕"
    assert lenient["coverage"]["missing"]
    assert "legacy_no_issued" in lenient["degraded"]


def test_collect_namespaces_and_merges():
    shutil.rmtree(TMP, ignore_errors=True)
    dispatch.write_cards("测试用", str(TMP))
    card = {
        "role": "r05",
        "numbers": [{"id": "N1", "name": "规模", "value": 100.0,
                     "unit": "亿元", "period": "2024", "source_file": "S1"}],
        "derived": [{"id": "D1", "formula": "N1*2", "value": 200.0,
                     "unit": "亿元", "note": "翻倍"}],
        "sources": [{"file": "S1", "title": "t", "org": "o",
                     "url": "https://example.com/s1", "date": "2026-11-19",
                     "grade": "A", "quote": "原文：规模 100.0 亿元，同比 12.0%。"}],
        "sections": [{"title": "规模 100.0 亿元",
                      "refs": ["N1"],
                      "reading": [{"text": "观察：100.0 亿元", "refs": ["N1"]},
                                  {"text": "机理：判别方法是…", "refs": ["D1"]}],
                      "falsifier": "若偏离超过 10.0% 则作废"}],
        "boundaries": ["没有省级数据"],
        "missing": ["查不到 A"],
    }
    (TMP / "cards" / "r05" / "claims.json").write_text(
        json.dumps(card, ensure_ascii=False), encoding="utf-8")
    merged, problems = dispatch.collect(str(TMP), allow_legacy=True)
    assert not problems, problems
    assert merged["numbers"][0]["id"] == "r05:N1"
    assert merged["numbers"][0]["source_file"] == "r05:S1"
    assert merged["derived"][0]["formula"] == "r05:N1*2"
    assert merged["sections"][0]["refs"] == ["r05:N1"]
    assert merged["boundaries"], "卡里的边界必须带上来"
    assert merged["standfirst"].startswith("规模")


def _card(**over):
    card = {
        "role": "r05",
        "numbers": [{"id": "N1", "name": "规模", "value": 100.0,
                     "unit": "亿元", "period": "2024", "source_file": "S1"}],
        "sources": [{"file": "S1", "title": "t", "org": "o",
                     "url": "https://example.com/s1", "date": "2026-11-19",
                     "grade": "A", "quote": "原文：规模 100.0 亿元，同比 12.0%。"}],
        "sections": [{"title": "规模 100.0 亿元", "refs": ["N1"],
                      "reading": [{"text": "观察：100.0 亿元", "refs": ["N1"]},
                                  {"text": "机理：判别方法是…", "refs": ["N1"]}],
                      "falsifier": "若偏离超过 10.0% 则作废"}],
        "boundaries": ["没有省级数据"],
    }
    card.update(over)
    return card


def test_collect_rejects_source_without_quote():
    """缺 quote 的来源等于没查：整张卡拒收，且说明缺什么。"""
    shutil.rmtree(TMP, ignore_errors=True)
    dispatch.write_cards("测试用", str(TMP))
    card = _card()
    card["sources"][0]["quote"] = ""
    (TMP / "cards" / "r05" / "claims.json").write_text(
        json.dumps(card, ensure_ascii=False), encoding="utf-8")
    merged, problems = dispatch.collect(str(TMP))
    assert any("quote" in p for p in problems), problems
    assert any(r["role"] == "r05" for r in merged["coverage"]["rejected"])
    assert not merged["sources"], "被拒的卡不能把来源合进来"


def test_min_sources_gate():
    """50 源门槛：不到就失败；--min-sources 0 关闭。"""
    shutil.rmtree(TMP, ignore_errors=True)
    dispatch.write_cards("测试用", str(TMP))
    (TMP / "cards" / "r05" / "claims.json").write_text(
        json.dumps(_card(), ensure_ascii=False), encoding="utf-8")
    merged, problems = dispatch.collect(str(TMP), min_sources=50, allow_legacy=True)
    assert any("低于门槛 50" in p for p in problems), problems
    assert merged["gaps"] == {} or merged["gaps"]["source_shortfall"] == 49
    merged2, problems2 = dispatch.collect(str(TMP), min_sources=0, allow_legacy=True)
    assert not problems2, problems2
    assert merged2["evidence"]["sources"] == 1

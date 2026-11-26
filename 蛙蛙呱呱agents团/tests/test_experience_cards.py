# -*- coding: utf-8 -*-
"""项目级经验卡（shared/experience_cards.py）回归。"""
from __future__ import annotations

import datetime as dt
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from shared import experience_cards as ec  # noqa: E402
from shared import prompt_pack  # noqa: E402

CARD = {
    "id": "c1", "title": "没有证据不写 PRD",
    "trigger": "PRD 需求 证据 用户",
    "wrong_once": "凭一句话就写完整 PRD",
    "do_instead": "先要访谈原话或行为数据",
    "boundary": "紧急合规需求可豁免",
    "last_verified": "2026-11-26",
    "confidence": "high", "roles": ["r07"], "source": "test",
}


def _write(p: Path, card: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(card, allow_unicode=True), encoding="utf-8")


def test_validate_requires_boundary():
    bad = dict(CARD)
    bad.pop("boundary")
    assert "boundary" in ec.validate(bad)
    assert ec.validate(CARD) == []


def test_load_project_overrides_role(tmp_path, monkeypatch):
    role = tmp_path / "role"
    proj = tmp_path / "proj"
    _write(role / "experience" / "cards" / "a.yaml", CARD)
    _write(proj / "experience" / "cards" / "a.yaml", dict(CARD, title="项目版标题"))
    monkeypatch.setattr(ec, "_role_dir", lambda r: str(role))
    cards, errors = ec.load_cards("r07", str(proj))
    assert not errors and len(cards) == 1
    assert cards[0]["title"] == "项目版标题"


def test_role_filter_and_tier(tmp_path, monkeypatch):
    role = tmp_path / "role"
    _write(role / "experience" / "cards" / "a.yaml", CARD)
    _write(role / "experience" / "cards" / "b.yaml",
           dict(CARD, id="c2", roles=["r05"], trigger="市场规模 来源"))
    monkeypatch.setattr(ec, "_role_dir", lambda r: str(role))
    res = ec.retrieve("r07", "PRD 需求")
    assert res["tier"] == "L1"
    assert [c["id"] for c in res["cards"]] == ["c1"]
    assert ec.retrieve("r07", "完全无关的词")["tier"] == "L0"


def test_ttl_decay_lowers_score(tmp_path, monkeypatch):
    role = tmp_path / "role"
    _write(role / "experience" / "cards" / "new.yaml", CARD)
    _write(role / "experience" / "cards" / "old.yaml",
           dict(CARD, id="c-old", last_verified="2020-01-01"))
    monkeypatch.setattr(ec, "_role_dir", lambda r: str(role))
    today = dt.date(2026, 11, 26)
    res = ec.retrieve("r07", "PRD 需求 证据", today=today)
    scores = {c["id"]: c["_score"] for c in res["cards"]}
    assert scores["c1"] > scores["c-old"]


def test_prompt_injection_with_project(tmp_path, monkeypatch):
    role = tmp_path / "role"
    _write(role / "experience" / "cards" / "a.yaml", CARD)
    monkeypatch.setattr(ec, "_role_dir", lambda r: str(role))
    pack = prompt_pack.build("r07", "prd", {"topic": "PRD 需求 证据"}, project=str(tmp_path))
    text = "\n".join(m.get("content", "") for m in pack["messages"])
    assert "【经验卡】" in text and "没有证据不写 PRD" in text
    assert pack["experience"]["tier"] == "L1"
    # 不传 project 时不注入，保持旧行为
    plain = prompt_pack.build("r07", "prd", {"topic": "PRD 需求 证据"})
    assert "【经验卡】" not in "\n".join(m["content"] for m in plain["messages"])
    assert plain["experience"]["tier"] == "L0"


def test_bad_card_reported_not_crashing(tmp_path, monkeypatch):
    role = tmp_path / "role"
    _write(role / "experience" / "cards" / "bad.yaml", {"id": "x", "title": "缺字段"})
    monkeypatch.setattr(ec, "_role_dir", lambda r: str(role))
    res = ec.retrieve("r07", "任何")
    assert res["tier"] == "L0"
    assert res["errors"]


# ---------------------------------------------------------------- 治理

def test_conflicts_only_when_do_instead_differs():
    a = dict(CARD, id="c1")
    b = dict(CARD, id="c2", do_instead="直接写 PRD，先上线再说")
    same = dict(CARD, id="c3")
    assert len(ec.conflicts([a, b])) == 1
    assert ec.conflicts([a, same]) == []


def test_project_card_cap_trims_and_reports(tmp_path, monkeypatch):
    empty = tmp_path / "role"
    empty.mkdir()
    monkeypatch.setattr(ec, "_role_dir", lambda r: str(empty))
    proj = tmp_path / "proj"
    for i in range(ec.MAX_PER_PROJECT + 3):
        _write(proj / "experience" / "cards" / f"{i:02d}.yaml",
               dict(CARD, id=f"c{i:02d}", last_verified="2026-11-26"))
    cards, errors = ec.load_cards("r07", str(proj))
    assert len(cards) == ec.MAX_PER_PROJECT
    assert any("超过上限" in e for e in errors)


def test_add_card_requires_source_and_reviewer(tmp_path):
    scope = tmp_path / "proj"
    bad = dict(CARD, source="")
    res = ec.add_card(str(scope), bad, reviewer="")
    assert not res["ok"]
    assert any("reviewed_by" in e for e in res["errors"])
    ok = ec.add_card(str(scope), dict(CARD), reviewer="r04")
    assert ok["ok"] and Path(ok["path"]).is_file()
    again = ec.add_card(str(scope), dict(CARD), reviewer="r04")
    assert not again["ok"]  # 同 id 不许静默覆盖


def test_brief_truncated_to_budget(tmp_path, monkeypatch):
    role = tmp_path / "role"
    long_card = dict(CARD, wrong_once="错" * 400, do_instead="改" * 400,
                     boundary="边界" * 100)
    _write(role / "experience" / "cards" / "a.yaml", long_card)
    monkeypatch.setattr(ec, "_role_dir", lambda r: str(role))
    res = ec.retrieve("r07", "PRD 需求")
    assert res["brief_chars"] <= ec.BRIEF_MAX_CHARS
    assert res["truncated"] is True


def test_stats_reports_stale_ratio(tmp_path, monkeypatch):
    role = tmp_path / "role"
    _write(role / "experience" / "cards" / "a.yaml", CARD)
    _write(role / "experience" / "cards" / "b.yaml",
           dict(CARD, id="c-old", last_verified="2020-01-01"))
    monkeypatch.setattr(ec, "_role_dir", lambda r: str(role))
    st = ec.stats("r07", today=dt.date(2026, 11, 26))
    assert st["loaded"] == 2 and st["stale"] == 1
    assert st["stale_ratio"] == 0.5
    assert st["brief_chars"] > 0


def test_knowledge_items_carry_hash():
    items = ec.to_knowledge_items([dict(CARD)])
    assert items[0]["id"] == "c1" and len(items[0]["hash"]) == 12
    assert "适用边界" in items[0]["text"]


# ---------------------------------------------------------------- brief 注入

class _Proj:
    def __init__(self, root):
        self.root = root


def test_brief_records_experience_refs(tmp_path, monkeypatch):
    role = tmp_path / "role"
    _write(role / "experience" / "cards" / "a.yaml", CARD)
    monkeypatch.setattr(ec, "_role_dir", lambda r: str(role))
    from shared.knowledge import brief as B
    eb = B.build_brief({"task_id": "t1", "question": "PRD 需求 证据"},
                       "r07", _Proj(tmp_path))
    refs = eb["experience_refs"]
    assert refs["tier"] == "L1" and refs["ids"] == ["c1"]
    # 只记引用，不内联卡片正文（正文属「怎么想」，事实必须来自本期证据）
    assert "wrong_once" not in eb and "do_instead" not in eb
    assert B.validate_brief(eb, "诊断型") == []

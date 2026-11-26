# -*- coding: utf-8 -*-
"""共享硬规则（shared/gate_digest.json）与提示词注入回归。"""
from __future__ import annotations

import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from shared import prompt_pack  # noqa: E402


def _text(role: str, action: str, inputs: dict) -> str:
    r = prompt_pack.build(role, action, inputs)
    return "\n".join(m.get("content", "") for m in r.get("messages", []))


def test_global_rules_apply_to_every_role():
    for rid in ("r01", "r06", "r11", "r20"):
        names = {r["name"] for r in prompt_pack.gate_digest(rid)}
        assert {"证据可回溯", "隐私不入稿"} <= names


def test_role_specific_rules():
    assert "结构不重复" in {r["name"] for r in prompt_pack.gate_digest("r11")}
    assert "结构不重复" not in {r["name"] for r in prompt_pack.gate_digest("r06")}
    assert "图有出处" in {r["name"] for r in prompt_pack.gate_digest("r06")}
    assert "经验带边界" in {r["name"] for r in prompt_pack.gate_digest("r07")}


def test_rules_injected_into_prompt():
    t = _text("r11", "hook", {"topic": "冷凉蔬菜", "platform": "公众号", "voice": "克制"})
    assert "【共享硬规则】" in t
    assert "结构不重复" in t
    assert "候选写作" in t  # 角色级方法块也要在


def test_analyst_gets_chart_rule_but_not_writing_rule():
    t = _text("r06", "explore", {"dataset": "x", "metrics_spec": "y"})
    assert "图有出处" in t
    assert "结构不重复" not in t

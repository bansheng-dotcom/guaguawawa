# -*- coding: utf-8 -*-
"""结构同构门禁（core.structure_guard）回归。

守三条：
1. 连续 3 节以上「标签序列 + 段数」完全一致 → 必须报；
2. 只连续 2 节一样 → 不报（避免把正常的一致性误判成模板）；
3. 论证顺序不同 → 不报。
"""
from __future__ import annotations

import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core import structure_guard  # noqa: E402

TEMPLATE = ["结论：A", "事实：B", "机理：C", "反例：D", "所以：E"]
OTHER = ["事实：B", "反例：D", "结论：A", "机理：C", "所以：E"]


def _pol(**kw):
    p = dict(structure_guard.DEFAULTS)
    p.update(kw)
    return p


def test_three_identical_sections_blocked():
    issues = structure_guard.audit([TEMPLATE] * 4, policy=_pol())
    assert len(issues) == 1
    assert "完全同构" in issues[0]


def test_two_identical_sections_allowed():
    assert structure_guard.audit([TEMPLATE] * 2, policy=_pol()) == []


def test_varied_order_allowed():
    assert structure_guard.audit([TEMPLATE, OTHER, TEMPLATE, OTHER], policy=_pol()) == []


def test_disabled_policy_passes():
    assert structure_guard.audit([TEMPLATE] * 5, policy=_pol(enabled=False)) == []


def test_claims_helper_reads_reading():
    claims = {"sections": [
        {"title": f"章{i}", "reading": [{"text": t} for t in TEMPLATE]}
        for i in range(3)
    ]}
    paras, titles = structure_guard.paragraphs_from_claims(claims)
    assert len(paras) == 3 and titles[0] == "章0"
    assert structure_guard.audit(paras, titles, _pol())


def test_html_helper_extracts_paragraphs():
    html = "".join(
        f'<section class="sec"><h2>第{i}节</h2>'
        + "".join(f"<p>{t}</p>" for t in TEMPLATE)
        + "</section>"
        for i in range(3)
    )
    paras, titles = structure_guard.paragraphs_from_html(html)
    assert len(paras) == 3
    assert structure_guard.audit(paras, titles, _pol())

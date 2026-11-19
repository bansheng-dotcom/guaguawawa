# -*- coding: utf-8 -*-
"""prose_style：字数/段块/禁用词/数字密度门禁。"""
from __future__ import annotations

from core import prose_style


def _good() -> str:
    body = (
        "结论：这不是需求扩张，而是结构升级。"
        "事实：2024 年规模 6871 亿元，同比 16.0%；本地社零 4.5%，差 11.5 个百分点。"
        "解释：一种解释是品类替代，另一种解释是渠道下沉；判别方法是看下一期酱油份额是否继续上升。"
        "如果份额继续上升，说明替代成立；如果回落，说明只是促销。"
        "所以：先守超市陈列，再做低钠 SKU；毛利低于 25% 就停。"
        "边界：只覆盖家庭零售与餐饮渠道，不含工业原料。"
    )
    extra = ("补充：2022 年 5133 亿元、2023 年 5925 亿元、2024 年 6871 亿元；"
             "渠道费用 15%–25%，账期 60–90 天；如果费用率超过 25%，"
             "毛利低于 25% 就停。")
    return body + extra * 10


def test_good_section_passes():
    r = prose_style.audit_section(_good())
    assert r["score"] >= 85
    assert r["hard"] is False


def test_short_section_fails():
    r = prose_style.audit_section("事实：很短。解释：没有。所以：没有。")
    assert r["hard"] is True
    assert r["score"] < 85


def test_banned_phrase_hard_fails():
    r = prose_style.audit_section(_good() + "这张表回答一切。")
    assert r["hard"] is True


def test_audit_html_sections():
    html = ('<section class="page sec" id="s1">' + _good() + "</section>"
            '<section class="page sec" id="s2">' + _good() + "</section>")
    out = prose_style.audit_html(html)
    assert out["sections"] == 2
    assert out["ok"] is True

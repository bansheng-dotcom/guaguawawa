# -*- coding: utf-8 -*-
"""flow renderer：HTML 一条流，页脚小签名。"""
from __future__ import annotations

from core.report_theme.flow import flowify


def _pages_like() -> str:
    return (
        '<!doctype html><html><head></head><body>'
        '<div class="page cover"><div class="inner"><h1>标题</h1></div></div>'
        '<section class="page sec" id="s1"><div class="rh">眉</div>'
        '<div class="head"><h2>01</h2></div><p>正文</p>'
        '<div class="rf">脚</div></section>'
        '<section class="page back" id="back"><div class="inner"><img src="x.png"></div></section>'
        '</body></html>'
    )


def test_flowify_removes_page_wrappers():
    html = flowify(_pages_like())
    assert "flow-cover" in html
    assert "flow-block" in html
    assert 'class="page ' not in html
    assert "flow-footer" in html


def test_flowify_strips_header_footer():
    html = flowify(_pages_like())
    assert ">眉<" not in html
    assert ">脚<" not in html


def test_flowify_keeps_body():
    html = flowify(_pages_like())
    assert "正文" in html
    assert "标题" in html


def test_flowify_compact_sources():
    html = _pages_like().replace(
        '</body>',
        '<section class="page appendix" id="appendix"><table><tr><td>old</td></tr></table></section></body>')
    out = flowify(html, [("S01", "来源一", "2024"), ("S02", "来源二", "2025")])
    assert "src-grid" in out
    assert "来源一" in out
    assert "old" not in out


def test_footer_html():
    from core.report_theme.blocks import footer_html
    assert "flow-footer" in footer_html()
    assert "蛙蛙呱呱专家团" in footer_html()


def test_flowify_is_responsive():
    html = flowify(_pages_like())
    assert 'name="viewport"' in html
    assert "max-width:900px" in html
    assert "width:100%" in html

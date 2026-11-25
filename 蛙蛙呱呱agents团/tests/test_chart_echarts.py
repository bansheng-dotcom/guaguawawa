# -*- coding: utf-8 -*-
"""P5-4：ECharts 交互后端（可选），静态 SVG 仍是兜底。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core.report_theme.charts_pro import interactive, layout  # noqa: E402


def _prep(chart):
    from core.report_theme.charts_pro import compat
    s = compat.to_spec(chart)
    assert s
    return layout.prepare(s)


def test_hbar_option_keeps_values_and_unit():
    opt = interactive.to_option(_prep({
        "type": "hbar", "title": "t", "unit_meta": "件",
        "bars": [{"label": "甲", "value": 12}, {"label": "乙", "value": 7}]}))
    assert opt and opt["series"][0]["type"] == "bar"
    vals = [d["value"] for d in opt["series"][0]["data"]]
    assert vals == [12.0, 7.0]
    assert "件" in opt["tooltip"]["valueFormatter"]


def test_line_option_has_series_and_axis():
    opt = interactive.to_option(_prep({
        "type": "line", "xlabels": ["p1", "p2", "p3"],
        "series": [{"name": "甲", "values": [1, 2, 3]}]}))
    assert opt["xAxis"]["data"] == ["p1", "p2", "p3"]
    assert opt["series"][0]["data"] == [1.0, 2.0, 3.0]


def test_pie_and_heatmap_options():
    pie = interactive.to_option(_prep({
        "type": "donut", "bars": [{"label": "a", "value": 3},
                                  {"label": "b", "value": 5}]}))
    assert pie["series"][0]["type"] == "pie"
    hm = interactive.to_option(_prep({
        "type": "heatmap", "rows": ["r1", "r2"], "cols": ["c1", "c2"],
        "matrix": [[1, -2], [3, 4]]}))
    assert hm["series"][0]["type"] == "heatmap"
    assert [d[2] for d in hm["series"][0]["data"]] == [1.0, -2.0, 3.0, 4.0]


def test_unsupported_type_returns_none():
    assert interactive.supported("network") is False
    assert interactive.to_option({"type": "network", "_layout": {"decimals": 1}}) is None
    assert interactive.render_chart({"type": "network"}) is None


def test_render_html_contains_cdn_init_and_svg_fallback():
    html = interactive.render_chart({
        "type": "hbar", "title": "t", "unit_meta": "件",
        "bars": [{"label": "甲", "value": 12}]})
    assert html and "echarts.min.js" in html and "echarts.init" in html
    assert "echart-fallback" in html and "<svg" in html
    assert "12" in html


def test_render_spec_accepts_canonical_chart_spec():
    html = interactive.render_spec({
        "type": "hbar", "unit_meta": "件",
        "items": [{"label": "甲", "value": 3}, {"label": "乙", "value": 5}]})
    assert html and "echarts.init" in html and "echart-fallback" in html
    assert "5" in html


def test_pages_backend_switch(monkeypatch):
    from core.report_theme import pages
    monkeypatch.setenv("GUAGUA_CHART_BACKEND", "echarts")
    body, engine = pages._render_svg({
        "type": "hbar", "title": "t", "bars": [{"label": "甲", "value": 1}]})
    assert engine == "echarts" and "echarts.init" in body
    monkeypatch.delenv("GUAGUA_CHART_BACKEND", raising=False)
    body2, engine2 = pages._render_svg({
        "type": "hbar", "title": "t", "bars": [{"label": "甲", "value": 1}]})
    assert engine2 in ("pro", "legacy") and "<svg" in body2

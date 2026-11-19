# -*- coding: utf-8 -*-
"""editorial 三张样图。"""
from __future__ import annotations

from core.charts import editorial as ed


def test_dot_change_has_labels_and_source():
    svg = ed.dot_change("标题", "K", [{"label": "酱油", "value": 0.26, "note": "n"}], "来源")
    assert "<svg" in svg and "酱油" in svg and "来源" in svg


def test_cost_bridge_has_total():
    svg = ed.cost_bridge("标题", "K", [{"label": "原料", "value": 3.0},
                                       {"label": "合计", "value": 3.0, "total": True}], "来源")
    assert "合计 3 元" in svg


def test_flow_nodes_has_cities():
    svg = ed.flow_nodes("标题", "K", ["佛山"], "呼市", ["包头"], "来源")
    assert "呼市" in svg and "包头" in svg

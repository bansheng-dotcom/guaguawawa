# -*- coding: utf-8 -*-
"""T10 图表审计用例：48 型最小可渲染 payload。

复用 `samples.SAMPLE` 的 40 型；其余 8 型（分组/堆叠/山脊/K 线/流图/符号地图/
双栏/KPI 卡）在此补齐。只服务审计与黄金样本生成，不参与渲染产线。
"""

from __future__ import annotations

from typing import Any, Dict

from samples import samples

#: samples.SAMPLE 未覆盖的 8 型
EXTRA: Dict[str, Dict[str, Any]] = {
    "grouped_bar": {
        "groups": [{"label": "Q1", "values": [10, 8]},
                   {"label": "Q2", "values": [12, 11]}],
        "series": [{"name": "A"}, {"name": "B"}],
    },
    "stacked_bar": {
        "categories": ["2024", "2025"],
        "series": [{"name": "x", "values": [10, 6]},
                   {"name": "y", "values": [5, 4]}],
    },
    "ridgeline": {
        "groups": [{"label": "A", "values": [1, 2, 2, 3, 3, 4]},
                   {"label": "B", "values": [2, 2, 3, 4, 4, 5]}],
    },
    "candlestick": {
        "ohlc": [{"label": "D1", "o": 10, "h": 12, "l": 9, "c": 11},
                 {"label": "D2", "o": 11, "h": 13, "l": 10, "c": 10}],
    },
    "streamgraph": {
        "series": [{"name": "a", "points": [3, 4, 5]},
                   {"name": "b", "points": [2, 2, 3]}],
    },
    "symbol_map": {"values": {"北京": 10, "上海": 8}},
    "dual_axis": {
        "top": [{"label": "1", "value": 10}, {"label": "2", "value": 12},
                {"label": "3", "value": 9}],
        "bottom": [{"label": "1", "value": 5}, {"label": "2", "value": 5.2},
                   {"label": "3", "value": 5.5}],
    },
    "kpi_break": {
        "items": [{"label": "营收", "value": 120, "delta": "+8%"},
                  {"label": "利润", "value": 25, "delta": "-3%"}],
    },
}


def cases() -> Dict[str, Dict[str, Any]]:
    """返回 48 型的 payload（键为目录 key）。"""
    out: Dict[str, Dict[str, Any]] = {}
    from core.charts.chart_capabilities import CATALOG
    for item in CATALOG:
        key = item["key"]
        payload = EXTRA.get(key) or samples.SAMPLE.get(key)
        if payload is not None:
            out[key] = payload
    return out

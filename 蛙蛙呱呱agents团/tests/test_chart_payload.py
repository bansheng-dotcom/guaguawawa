# -*- coding: utf-8 -*-
"""test_chart_payload —— payload 构建器单测。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.chart_payload import build_payload  # noqa: E402

FACTS = [
    {"id": "F1", "metric": "采购价", "entity": "大白菜", "value": 1.2, "unit": "元"},
    {"id": "F2", "metric": "运费", "entity": "大白菜", "value": 0.3, "unit": "元"},
    {"id": "F3", "metric": "采购价", "entity": "土豆", "value": 1.0, "unit": "元"},
    {"id": "F4", "metric": "运费", "entity": "土豆", "value": 0.4, "unit": "元"},
]


def test_items_payload():
    p = build_payload("treemap", FACTS)
    assert len(p["items"]) == 4
    assert p["items"][0] == {"label": "大白菜", "value": 1.2}


def test_histogram_payload():
    p = build_payload("histogram", FACTS)
    assert p["values"] == [1.2, 0.3, 1.0, 0.4]


def test_box_groups_by_entity():
    p = build_payload("box", FACTS)
    labels = {g["label"] for g in p["groups"]}
    assert labels == {"大白菜", "土豆"}
    for g in p["groups"]:
        assert len(g["values"]) == 2


def test_stacked_categories_series():
    p = build_payload("stacked", FACTS)
    assert set(p["categories"]) == {"大白菜", "土豆"}
    assert {s["name"] for s in p["series"]} == {"采购价", "运费"}
    # 每系列值数与 categories 对齐
    for s in p["series"]:
        assert len(s["values"]) == len(p["categories"])


def test_line_payload():
    p = build_payload("line", FACTS)
    assert len(p["points"]) == 4


def test_unknown_type_empty():
    assert build_payload("nonsense", FACTS) == {}

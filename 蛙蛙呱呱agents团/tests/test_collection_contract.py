# -*- coding: utf-8 -*-
"""test_collection_contract —— 采集契约单测。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import collection_contract as cc  # noqa: E402


def _grid():
    return {"cells": [
        {"cell_id": "Q1.空间.全国", "dim": "空间", "entity": "全国",
         "measure": "retail_sales", "grain": "G_category_year"},
        {"cell_id": "Q1.对象.纸尿裤", "dim": "对象", "entity": "纸尿裤",
         "measure": "share", "grain": "G_category_year"},
    ]}


def _sem():
    return {"case": {
        "entities": [{"id": "category", "levels": ["大类", "子类"]},
                     {"id": "year", "levels": []}],
        "measures": [{"id": "retail_sales", "type": "simple", "unit": "亿元",
                      "caliber": {"scope": "平台内成交额"}},
                     {"id": "share", "type": "ratio", "unit": "%",
                      "expr": "brand_sales/retail_sales"}],
    }}


def test_build_has_required_fields():
    c = cc.build(_grid(), _sem(), {"asks": [{"must": True, "text": "首推哪个品类"}]})
    assert c["apiVersion"] == cc.SCHEMA
    assert c["grain"] == ["category"]
    assert c["rows_expected"] == 2
    assert c["acquisition"]["availability"] in cc.AVAILABILITY


def test_validate_ok():
    c = cc.build(_grid(), _sem())
    assert cc.validate(c) == []


def test_validate_missing_grain():
    c = cc.build(_grid(), _sem())
    c["grain"] = []
    assert any("grain" in e for e in cc.validate(c))


def test_validate_bad_availability():
    c = cc.build(_grid(), _sem())
    c["acquisition"]["availability"] = "maybe"
    assert any("availability" in e for e in cc.validate(c))


def test_availability_percent_is_medium():
    assert cc.availability_estimate(["share"], _sem()) == "medium"


def test_empty_grid_returns_none():
    assert cc.build({"cells": []}, _sem()) is None

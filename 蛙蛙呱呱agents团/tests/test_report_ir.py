# -*- coding: utf-8 -*-
"""test_report_ir —— S0 富 IR 校验器 + 关系推断单测。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import report_ir  # noqa: E402


def _valid_ir():
    return {
        "schema": "dsh.report_ir/v1",
        "meta": {"title": "超市销售", "audience": "业务负责人"},
        "facts": [
            {"id": "F1", "metric": "电子配件营收", "entity": "B市",
             "period": "2026-01", "value": 48.2, "unit": "万元", "source": "S01"},
            {"id": "F2", "metric": "电子配件营收", "entity": "A市",
             "period": "2026-01", "value": 40.1, "unit": "万元", "source": "S01",
             "derived_from": []},
        ],
        "sections": [
            {"title": "电子配件 B 市比 A 市高 8.1 万",
             "question": "电子配件两城营收差多大？",
             "outline": "两城对比电子配件营收",
             "chart": {"data_refs": ["F1", "F2"]}},
        ],
    }


def test_valid_ir_passes():
    assert report_ir.validate(_valid_ir()) == []


def test_missing_schema():
    ir = _valid_ir(); ir["schema"] = "x"
    assert any("schema" in e for e in report_ir.validate(ir))


def test_fact_missing_source():
    ir = _valid_ir(); ir["facts"][0].pop("source")
    assert any("source" in e for e in report_ir.validate(ir))


def test_chart_refs_unknown_fact():
    ir = _valid_ir(); ir["sections"][0]["chart"]["data_refs"] = ["NOPE"]
    assert any("不存在的 fact" in e for e in report_ir.validate(ir))


def test_infer_relation_from_question():
    assert report_ir.infer_relation("两地价差多大") == "deviation"
    assert report_ir.infer_relation("哪个产品线最贵") == "ranking"
    assert report_ir.infer_relation("月度营收走势") == "change_over_time"
    assert report_ir.infer_relation("电子配件占比") == "composition"

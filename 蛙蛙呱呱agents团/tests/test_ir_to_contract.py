# -*- coding: utf-8 -*-
"""test_ir_to_contract —— IR → contract 转换器单测。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import ir_to_contract, report_renderer  # noqa: E402
from core.semantic_pipeline import resolve  # noqa: E402


def _model():
    ir = {
        "schema": "dsh.report_ir/v1",
        "meta": {"title": "超市销售", "audience": "业务负责人",
                 "subtitle": "三个月", "standfirst": "电子配件最高"},
        "facts": [
            {"id": "F1", "metric": "电子配件", "entity": "B市", "period": "2026-01",
             "value": 48.2, "unit": "万元", "source": "S1"},
            {"id": "F2", "metric": "食品饮料", "entity": "B市", "period": "2026-01",
             "value": 32.5, "unit": "万元", "source": "S1"},
            {"id": "F3", "metric": "运动旅行", "entity": "B市", "period": "2026-01",
             "value": 12.1, "unit": "万元", "source": "S1"},
        ],
        "sources": [{"file": "S1", "title": "交易数据", "org": "本地", "url": ""}],
        "sections": [{
            "title": "电子配件 48.2 万最高", "question": "哪个品类最高",
            "outline": "品类排名",
            "readings": [{"strong": "事实　", "text": "电子配件 48.2 万", "refs": ["F1"]}],
            "boundary": "b", "falsifier": "f",
            "chart": {"relation": "ranking", "chosen": "hbar",
                      "data_refs": ["F1", "F2", "F3"],
                      "dims": [{"name": "entity", "type": "categorical"}]},
        }],
    }
    return resolve(ir)


def test_contract_valid():
    c = ir_to_contract.build(_model())
    assert report_renderer.validate_contract(c) == []


def test_title_and_summary():
    c = ir_to_contract.build(_model())
    assert c["title_lines"][0] == "超市销售"
    assert c["summary"][0]["text"] == "电子配件最高"


def test_section_and_chart():
    c = ir_to_contract.build(_model())
    assert len(c["sections"]) == 1
    ch = c["sections"][0]["chart"]
    assert ch["type"] == "hbar"
    assert len(ch["items"]) == 3
    assert ch["unit_meta"] == "万元"


def test_metric_strip():
    c = ir_to_contract.build(_model())
    assert len(c["metric_strip"]) == 3
    assert all("label" in m and "value" in m and "note" in m for m in c["metric_strip"])

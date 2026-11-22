# -*- coding: utf-8 -*-
"""test_decision_frontend —— S3 decision→IR 前端单测。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.ir_adapters import decision_to_ir  # noqa: E402
from core.report_ir import validate  # noqa: E402


def _draft_pack():
    draft = {
        "title_lines": ["超市销售分析"], "intent": "超市销售",
        "standfirst": "s",
        "sections": [{
            "title": "电子配件 48.2 万最高", "question": "哪个产品线最高",
            "reading": [{"strong": "事实　", "text": "电子配件 48.2",
                         "refs": ["csv:r:电子配件:last"]}],
            "boundary": "b", "falsifier": "f",
            "chart": {"type": "hbar", "refs": ["csv:r:电子配件:last"]},
        }],
    }
    pack = {
        "numbers": [
            {"id": "csv:r:电子配件:last", "name": "电子配件(last)",
             "value": 48.2, "unit": "万元", "period": "", "region": "B市",
             "source_file": "data/sales.csv", "inputs": ""},
        ],
        "sources": [{"file": "data/sales.csv", "title": "sales", "org": "o", "url": "u"}],
    }
    return draft, pack


def test_decision_to_ir_valid():
    ir, _ = decision_to_ir(*_draft_pack())
    assert validate(ir) == []


def test_region_mapped_to_entity():
    ir, _ = decision_to_ir(*_draft_pack())
    assert ir["facts"][0]["entity"] == "B市"


def test_derived_from_from_inputs():
    d, p = _draft_pack()
    p["numbers"][0]["inputs"] = "csv:r:营收:sum"
    ir, _ = decision_to_ir(d, p)
    assert ir["facts"][0]["derived_from"] == ["csv:r:营收:sum"]


def test_relation_inferred_from_question():
    ir, _ = decision_to_ir(*_draft_pack())
    assert ir["sections"][0]["chart"]["relation"] == "ranking"

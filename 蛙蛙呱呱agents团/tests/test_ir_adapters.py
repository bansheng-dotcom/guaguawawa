# -*- coding: utf-8 -*-
"""test_ir_adapters —— S2 claims 前端单测。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.ir_adapters import claims_to_ir  # noqa: E402
from core.report_ir import validate  # noqa: E402


def _claims():
    return {
        "meta": {"title": "t", "audience": "a"},
        "numbers": [
            {"id": "N1", "name": "包头价", "value": 9.0, "unit": "元/公斤",
             "source_file": "S1"},
            {"id": "N2", "name": "呼市价", "value": 16.0, "unit": "元/公斤",
             "source_file": "S1"},
        ],
        "sources": [{"file": "S1", "title": "s", "org": "o", "url": "u"}],
        "sections": [{
            "title": "价差 7 元", "question": "两地价差多大",
            "reading": [{"strong": "事实　", "text": "9 vs 16", "refs": ["N1", "N2"]}],
            "boundary": "b", "falsifier": "f",
            "chart": {"type": "dumbbell", "refs": ["N1", "N2"]},
        }],
    }


def test_claims_to_ir_valid():
    ir, _ = claims_to_ir(_claims())
    assert validate(ir) == []


def test_facts_and_sources_count():
    ir, _ = claims_to_ir(_claims())
    assert len(ir["facts"]) == 2
    assert len(ir["sources"]) == 1
    assert len(ir["sections"]) == 1


def test_relation_inferred_from_question():
    ir, _ = claims_to_ir(_claims())
    assert ir["sections"][0]["chart"]["relation"] == "deviation"


def test_outline_degradation_recorded():
    _, degraded = claims_to_ir(_claims())
    assert any("outline" in d["field"] for d in degraded)

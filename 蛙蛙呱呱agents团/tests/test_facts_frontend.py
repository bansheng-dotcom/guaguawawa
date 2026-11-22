# -*- coding: utf-8 -*-
"""test_facts_frontend —— S4 声明式 facts.yaml→IR 前端单测。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.ir_adapters import facts_to_ir  # noqa: E402
from core.report_ir import validate  # noqa: E402


def _facts():
    return {
        "schema": "dsh.facts_authoring/v1",
        "meta": {"title": "超市销售", "audience": "业务负责人", "one_thing": "先拆电子配件"},
        "facts": [
            {"id": "F1", "metric": "电子配件营收", "entity": "B市",
             "period": "2026-01", "value": 48.2, "unit": "万元", "source": "S1"},
            {"id": "F2", "metric": "电子配件营收", "entity": "A市",
             "period": "2026-01", "value": 40.1, "unit": "万元", "source": "S1"},
        ],
        "sources": [{"file": "S1", "title": "sales", "org": "o", "url": "u"}],
        "sections": [{
            "title": "电子配件 B 市比 A 市高 8.1 万",
            "question": "两地价差多大",
            "outline": "两城对比电子配件营收",
            "actions": ["拆电子配件 B 市溢价"],
            "chart": {"data_refs": ["F1", "F2"]},
        }],
    }


def test_facts_to_ir_valid():
    ir, _ = facts_to_ir(_facts())
    assert validate(ir) == []


def test_relation_inferred_when_absent():
    ir, _ = facts_to_ir(_facts())
    assert ir["sections"][0]["chart"]["relation"] == "deviation"


def test_relation_explicit_overrides():
    f = _facts(); f["sections"][0]["chart"]["relation"] = "ranking"
    ir, _ = facts_to_ir(f)
    assert ir["sections"][0]["chart"]["relation"] == "ranking"


def test_dims_from_facts():
    ir, _ = facts_to_ir(_facts())
    names = {d["name"] for d in ir["sections"][0]["chart"]["dims"]}
    assert names == {"entity", "period"}


def test_actions_passthrough():
    ir, _ = facts_to_ir(_facts())
    assert ir["sections"][0]["actions"] == ["拆电子配件 B 市溢价"]

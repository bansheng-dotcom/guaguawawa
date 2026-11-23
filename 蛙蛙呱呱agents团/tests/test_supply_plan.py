# -*- coding: utf-8 -*-
"""test_supply_plan —— 数据供给方案（SUPPLY-SOP v7.0）。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import collection_contract  # noqa: E402
from core import supply_plan as sup  # noqa: E402


def _doc(**kw):
    base = {
        "schema": sup.SCHEMA,
        "business": "测试业务",
        "sources": [
            {"layer": "A", "name": "统计局", "gives": ["规模"], "cost": 0},
            {"layer": "B", "name": "行业报告", "gives": ["结构"], "cost": 0},
        ],
        "levels": {"L1_possible": True, "L2_possible": False,
                   "L2_condition": "需采购第三方数据"},
        "reviewed_at": "2026-11-23",
    }
    base.update(kw)
    return base


# ---------------- validate ----------------

def test_valid_l1_plan():
    assert sup.validate(_doc()) == []


def test_missing_doc():
    assert sup.validate({})


def test_missing_business():
    assert any("business" in e for e in sup.validate(_doc(business="")))


def test_no_sources():
    assert any("sources" in e for e in sup.validate(_doc(sources=[])))


def test_bad_layer():
    d = _doc()
    d["sources"][0]["layer"] = "Z"
    assert any("layer" in e for e in sup.validate(d))


def test_l2_needs_condition():
    d = _doc(levels={"L1_possible": True, "L2_possible": False})
    assert any("L2_condition" in e for e in sup.validate(d))


def test_l2_requires_c_layer():
    """声称能做 L2 却没有 C 层源——自相矛盾。"""
    d = _doc(levels={"L1_possible": True, "L2_possible": True})
    assert any("C 层" in e for e in sup.validate(d))


def test_l2_with_c_layer_ok():
    d = _doc(sources=[
        {"layer": "A", "name": "a", "gives": ["x"]},
        {"layer": "C", "name": "c", "gives": ["y"]},
    ], levels={"L1_possible": True, "L2_possible": True})
    assert sup.validate(d) == []


def test_planned_rows_must_be_positive():
    d = _doc(levels={"L1_possible": True, "L2_possible": False,
                     "L2_condition": "x", "planned_rows": 0})
    assert any("planned_rows" in e for e in sup.validate(d))


# ---------------- planned ----------------

def test_planned_level_l2():
    d = _doc(sources=[{"layer": "C", "name": "c", "gives": ["y"]}],
             levels={"L1_possible": True, "L2_possible": True})
    assert sup.planned_level(d) == "L2"


def test_planned_level_l1():
    assert sup.planned_level(_doc()) == "L1"


def test_planned_level_l0():
    assert sup.planned_level({}) == "L0"


def test_planned_rows():
    d = _doc(levels={"L1_possible": True, "L2_possible": False,
                     "L2_condition": "x", "planned_rows": 144})
    assert sup.planned_rows(d) == 144


def test_planned_rows_absent():
    assert sup.planned_rows(_doc()) is None


# ---------------- actual / capability ----------------

def test_actual_level_l2_from_mart():
    assert sup.actual_level({"mart_rows": {"a": 72}}) == "L2"


def test_actual_level_l1_from_numbers():
    assert sup.actual_level({"numbers": [1, 2]}) == "L1"


def test_actual_level_l0():
    assert sup.actual_level({}) == "L0"


def test_capability_no_degrade_when_plan_is_l1():
    """计划就是 L1，交付 L1 → 正常交付，不叫降级。"""
    cap = sup.capability_of(_doc(), {"numbers": [1, 2]})
    assert cap["planned"] == "L1"
    assert cap["actual"] == "L1"
    assert cap["degraded"] is False
    assert "按计划交付" in cap["why"]


def test_capability_degrade_when_plan_l2_actual_l1():
    d = _doc(sources=[{"layer": "C", "name": "c", "gives": ["y"]}],
             levels={"L1_possible": True, "L2_possible": True,
                     "L2_condition": "需采购"})
    cap = sup.capability_of(d, {"numbers": [1]})
    assert cap["planned"] == "L2"
    assert cap["actual"] == "L1"
    assert cap["degraded"] is True
    assert cap["degraded_from"] == "L2"


def test_capability_gate_ok_when_on_plan():
    g = sup.gate(_doc(), {"numbers": [1]})
    assert g["ok"] is True
    assert g["id"] == "G-CAPABILITY"


def test_capability_gate_flags_missing_supply():
    g = sup.gate({}, {"numbers": [1]})
    assert g["ok"] is False


# ---------------- 契约接线：rows_expected 不再等于格子数 ----------------

def _grid(n=4):
    return {"cells": [
        {"cell_id": "c%d" % i, "measure": "asp", "grain": "G_brand_month",
         "entity": "e%d" % i} for i in range(n)
    ]}


def test_contract_rows_expected_uses_supply():
    """84 个格子 ≠ 84 行；行数由供给方案定。"""
    c = collection_contract.build(
        _grid(4), {"measures": [], "entities": []},
        supply=_doc(levels={"L1_possible": True, "L2_possible": False,
                            "L2_condition": "x", "planned_rows": 144}))
    assert c["rows_expected"] == 144
    assert c["rows_expected_source"] == "supply.yaml"


def test_contract_rows_expected_falls_back_to_cells():
    c = collection_contract.build(_grid(4), {"measures": [], "entities": []})
    assert c["rows_expected"] == 4
    assert c["rows_expected_source"] == "cell_count(fallback)"


def test_contract_carries_planned_level():
    c = collection_contract.build(_grid(3), {"measures": [], "entities": []},
                                  supply=_doc())
    assert c["acquisition"]["planned_level"] == "L1"
    assert "A" in c["acquisition"]["supply_layers"]

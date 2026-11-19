# -*- coding: utf-8 -*-
"""覆盖自动化：TaskFrame / SourceLedger / CoveragePlan / 双门禁。"""
from __future__ import annotations

from core import coverage_plan, task_frame, task_research


def _units():
    return [{"id": f"U{i}", "name": f"单元{i}", "level": "category", "sources": ["S01"]}
            for i in range(1, 4)]


def _dims():
    return [{"id": "D1", "name": "规模", "sources": ["S01"], "required": True},
            {"id": "D2", "name": "链路", "sources": ["S02"], "required": True}]


def _frame():
    return task_frame.build(
        {"task_id": "t1", "brief": "测试任务"},
        {"question": "做不做？", "type": "inferred"},
        _units(), _dims(),
        {"core_units": ["U1", "U2", "U3"], "deep_dimensions": ["D1", "D2"],
         "long_tail_policy": "context_red"},
        [{"level": "national", "required": True}, {"level": "regional", "required": True}],
        21, {"cited_min": 50}, {"cited": 50, "reached": True, "no_new_streak": 15},
    )


def test_frame_valid():
    f = _frame()
    assert task_frame.validate(f) == []
    assert task_frame.frame_hash(f).startswith("sha256:")


def test_source_saturation():
    led = task_research.SourceLedger(no_new_streak=15)
    for i in range(50):
        led.add({"id": f"S{i}", "grade": "A", "new_dimensions": ["D1"] if i == 0 else []})
    assert led.status()["reached"] is True
    led2 = task_research.SourceLedger(no_new_streak=15)
    for i in range(49):
        led2.add({"id": f"S{i}", "grade": "A", "new_dimensions": []})
    assert led2.status()["reached"] is False


def test_pre_gate_core_missing_blocks():
    f = _frame()
    cells = [{"unit": u, "dimension": d, "status": "verified"}
             for u in ("U1", "U2", "U3") for d in ("D1", "D2")]
    cells[0]["status"] = "missing"
    p = coverage_plan.build(f, cells, 21, ["national", "regional"])
    conf = {"plan_hash": coverage_plan.plan_hash(p)}
    r = coverage_plan.pre_gate(f, p, {"cited": 50, "reached": True, "no_new_streak": 15},
                               conf, {"coverage": {"cited_sources_min": 50,
                                                   "maps_required": ["national", "regional"],
                                                   "page_floor": 21}})
    assert r["ok"] is False
    assert "G4_core_missing" in r["hard_fail"]


def test_pre_gate_pass_and_confirm_hash():
    f = _frame()
    cells = [{"unit": u, "dimension": d, "status": "verified"}
             for u in ("U1", "U2", "U3") for d in ("D1", "D2")]
    p = coverage_plan.build(f, cells, 21, ["national", "regional"])
    conf = {"plan_hash": coverage_plan.plan_hash(p)}
    r = coverage_plan.pre_gate(f, p, {"cited": 50, "reached": True, "no_new_streak": 15},
                               conf, {"coverage": {"cited_sources_min": 50,
                                                   "maps_required": ["national", "regional"],
                                                   "page_floor": 21}})
    assert r["ok"] is True
    bad = {"plan_hash": "sha256:bad"}
    r2 = coverage_plan.pre_gate(f, p, {"cited": 50, "reached": True, "no_new_streak": 15},
                                bad, {"coverage": {"cited_sources_min": 50,
                                                   "maps_required": ["national", "regional"],
                                                   "page_floor": 21}})
    assert r2["ok"] is False and "G3_confirmed" in r2["hard_fail"]


def test_data_shape_fit():
    from core import data_shape
    assert data_shape.fits("dumbbell", "pair")
    assert not data_shape.fits("dumbbell", "scalar")
    assert "hbar" in data_shape.candidates("scalar")
    bad = data_shape.audit_sections([{"id": "s1", "chart": "dumbbell", "shape": "scalar"}])
    assert bad["ok"] is False

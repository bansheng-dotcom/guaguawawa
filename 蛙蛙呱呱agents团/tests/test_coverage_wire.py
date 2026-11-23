# -*- coding: utf-8 -*-
"""test_coverage_wire —— 覆盖矩阵/饱和接进主链路的派生层。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import coverage_wire  # noqa: E402


def _w(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _project(tmp_path: Path, filled=True):
    proj = tmp_path / "proj"
    _w(proj / "plan" / "grid.json", {"cells": [
        {"cell_id": "Q1.对象.飞鹤", "qid": "Q1", "dim": "对象",
         "entity": "飞鹤", "measure": "share", "depth_target": 3},
        {"cell_id": "Q1.空间.全国", "qid": "Q1", "dim": "空间",
         "entity": "全国", "measure": "retail_sales"},
        {"cell_id": "Q1.机制.份额变化", "qid": "Q1", "dim": "机制",
         "entity": "飞鹤", "measure": "share", "depth_target": 3},
    ]})
    if filled:
        _w(proj / "out_v3" / "cells_filled.json", {"cells": [
            {"cell_id": "Q1.对象.飞鹤", "status": "filled", "value": 20.0},
            {"cell_id": "Q1.空间.全国", "status": "filled", "value": 100.0},
            {"cell_id": "Q1.机制.份额变化", "status": "open"},
        ]})
    _w(proj / "out" / "claims_merged.json", {"sources": [
        {"file": "S1"}, {"file": "S2"}, {"file": "S2"},
    ]})
    return proj


def test_derive_ok(tmp_path):
    d = coverage_wire.derive(str(_project(tmp_path)))
    assert d["ok"] is True
    assert d["cells"] == 3
    assert d["filled"] == 2
    assert len(d["frame"]["dimensions"]) == 6
    assert "飞鹤" in d["frame"]["depth"]["core_units"]


def test_derive_missing_grid(tmp_path):
    d = coverage_wire.derive(str(tmp_path))
    assert d["ok"] is False
    assert "grid" in d["why"]


def test_derive_marks_missing_cells(tmp_path):
    d = coverage_wire.derive(str(_project(tmp_path)))
    statuses = {(c["unit"], c["dimension"]): c["status"] for c in d["plan"]["cells"]}
    assert statuses[("飞鹤", "对象")] == "verified"
    assert statuses[("飞鹤", "机制")] == "missing"


def test_gate_runs_and_reports(tmp_path):
    g = coverage_wire.gate(str(_project(tmp_path)))
    assert g.get("skipped") is not True
    ids = {c["id"] for c in g["checks"]}
    assert "G4_core_missing" in ids
    assert "G2_saturation" in ids


def test_gate_skipped_without_grid(tmp_path):
    g = coverage_wire.gate(str(tmp_path))
    assert g.get("skipped") is True
    assert g.get("ok") is True

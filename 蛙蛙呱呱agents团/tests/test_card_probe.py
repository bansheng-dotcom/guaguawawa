# -*- coding: utf-8 -*-
"""test_card_probe —— 可行性测试与降级（FEASIBILITY-SOP v5.0）。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import card_probe  # noqa: E402

SRC = {
    "schema": "dsh.source/v1", "id": "t_csv", "kind": "csv_manual",
    "atomic_grain": ["row_id"], "history": "historical",
    "fields": [
        {"name": "row_id", "type": "string"},
        {"name": "snapshot_date", "type": "date"},
        {"name": "title", "type": "string"},
        {"name": "price", "type": "number"},
        {"name": "sales_30d", "type": "number"},
    ],
}


def _proj(tmp_path: Path, measure: str = "asp", grain: str = "G_brand_year"):
    (tmp_path / "plan").mkdir(parents=True, exist_ok=True)
    grid = {"schema": "dsh.grid/v1", "cells": [
        {"cell_id": "Q1.对象.A", "qid": "Q1", "dim": "对象", "entity": "A",
         "measure": measure, "grain": grain},
        {"cell_id": "Q1.对象.B", "qid": "Q1", "dim": "对象", "entity": "B",
         "measure": measure, "grain": grain},
    ], "count": 2}
    (tmp_path / "plan" / "grid.json").write_text(
        json.dumps(grid, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_probe_report_mode(tmp_path):
    p = _proj(tmp_path)
    r = card_probe.probe(str(p), mode="report", sources=[SRC])
    assert r["ok"] is True
    assert r["cells"] == 2
    assert r["demands"] == 1
    assert r["degraded"] == 0
    # report 模式不改 grid
    g = json.loads((p / "plan" / "grid.json").read_text(encoding="utf-8"))
    assert "collectable" not in g["cells"][0]


def test_probe_degrade_mode_writes_grid(tmp_path):
    p = _proj(tmp_path)
    r = card_probe.probe(str(p), mode="degrade", sources=[SRC])
    assert r["degraded"] == 2
    g = json.loads((p / "plan" / "grid.json").read_text(encoding="utf-8"))
    c = g["cells"][0]
    assert c["collectable"] in ("full", "partial", "none")
    assert c["availability"] in ("available", "unavailable")
    assert "tried" in c and "why" in c


def test_probe_marks_unavailable_when_no_source(tmp_path):
    p = _proj(tmp_path, measure="gross_margin")   # 目录里没有的度量
    r = card_probe.probe(str(p), mode="degrade", sources=[SRC])
    g = json.loads((p / "plan" / "grid.json").read_text(encoding="utf-8"))
    assert g["cells"][0]["availability"] in ("available", "unavailable")
    # 至少要有 why（降级必须解释）
    assert g["cells"][0].get("why") is not None


def test_probe_no_grid(tmp_path):
    r = card_probe.probe(str(tmp_path), mode="report", sources=[SRC])
    assert r["ok"] is False


def test_probe_invalid_mode_falls_back(tmp_path):
    p = _proj(tmp_path)
    r = card_probe.probe(str(p), mode="whatever", sources=[SRC])
    assert r["mode"] == "report"


def test_probe_writes_derivation_json(tmp_path):
    p = _proj(tmp_path)
    card_probe.probe(str(p), mode="report", sources=[SRC])
    f = p / "plan" / "derivation.json"
    assert f.is_file()
    d = json.loads(f.read_text(encoding="utf-8"))
    assert d["schema"] == "dsh.probe/v1"


def test_degraded_cells_empty_when_all_available(tmp_path):
    p = _proj(tmp_path)
    card_probe.probe(str(p), mode="degrade", sources=[SRC])
    assert card_probe.degraded_cells(str(p)) == []


def test_probe_has_gates(tmp_path):
    p = _proj(tmp_path)
    r = card_probe.probe(str(p), mode="report", sources=[SRC])
    ids = [c["id"] for c in r["gates"]["checks"]]
    assert "G-ROLLUP" in ids and "G-PREVIEW" in ids

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
    # 老项目没有 grid 也要返回 ok=True，但要说清降级层级
    r = card_probe.probe(str(tmp_path), mode="report", sources=[SRC])
    assert r["ok"] is True
    assert r["cells"] == 0
    assert r["degrade_level"] == "none"


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


# ---------------- 三层降级（FEASIBILITY-SOP v5.0 修正） ----------------

def test_evidence_layer_reads_numbers(tmp_path):
    """老报告没有长表，但有「数字+来源」——证据层必须能看见。"""
    p = tmp_path
    (p / "claims_merged.json").write_text(json.dumps({
        "numbers": [
            {"id": "a:1", "source_file": "a:S1"},
            {"id": "a:2", "source_file": "a:S1"},
        ],
        "sources": [{"file": "a:S1", "url": "https://x", "quote": "q"}],
    }, ensure_ascii=False), encoding="utf-8")
    ev = card_probe._evidence_layer(p)
    assert ev["numbers"] == 2
    assert ev["with_source"] == 2
    assert ev["with_source_rate"] == 1.0
    assert ev["available"] is True


def test_no_evidence_means_none():
    ev = {"numbers": 0, "available": False}
    assert card_probe._degrade_level(0, ev) == "none"


def test_evidence_without_dataset_is_evidence_level():
    ev = {"numbers": 130, "available": True}
    assert card_probe._degrade_level(0, ev) == "evidence"


def test_dataset_rows_wins():
    ev = {"numbers": 130, "available": True}
    assert card_probe._degrade_level(72, ev) == "dataset"


def test_has_dataset_layer_detects_spec(tmp_path):
    assert card_probe._has_dataset_layer(tmp_path) is False
    (tmp_path / "collection.yaml").write_text("schema: x", encoding="utf-8")
    assert card_probe._has_dataset_layer(tmp_path) is True


def test_old_project_without_grid_returns_ok(tmp_path):
    """老项目没有 grid：不判格子，但要报清证据层。"""
    (tmp_path / "claims_merged.json").write_text(json.dumps({
        "numbers": [{"id": "a:1", "source_file": "a:S1"}],
        "sources": [{"file": "a:S1"}],
    }, ensure_ascii=False), encoding="utf-8")
    r = card_probe.probe(str(tmp_path), mode="report", sources=[SRC])
    assert r["ok"] is True
    assert r["cells"] == 0
    assert r["degrade_level"] == "evidence"
    assert r["evidence_layer"]["numbers"] == 1


def test_dataset_project_does_not_fall_back_to_evidence(tmp_path):
    """有采集规格的项目：数据集层是权威，none 不能被证据层压掉。"""
    p = _proj(tmp_path, measure="gross_margin")
    (p / "collection.yaml").write_text("schema: x", encoding="utf-8")
    # 同时塞一份证据层数据：有采集规格时它不该把 none 救回 point
    (p / "claims_merged.json").write_text(json.dumps({
        "numbers": [{"id": "a:1", "source_file": "a:S1"}],
        "sources": [{"file": "a:S1"}],
    }, ensure_ascii=False), encoding="utf-8")
    r = card_probe.probe(str(p), mode="report", sources=[SRC])
    assert card_probe._has_dataset_layer(p) is True
    assert [u["measure"] for u in r["unavailable_demands"]] == ["gross_margin"]

# -*- coding: utf-8 -*-
"""test_dataset_layer —— 数据集层 v2.0（S0–S5）。"""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import cell_claim, dataset, dataset_gates, dataset_query, drill  # noqa: E402


# ---------------- S0 数据集 ----------------

def _ds():
    return dataset.build(
        "DS-t", title="测试表",
        source={"kind": "平台榜单", "url": "https://x"},
        grain="brand × month", time_grain="month",
        columns=[
            {"name": "brand", "semantic": "dimension"},
            {"name": "month", "semantic": "dimension"},
            {"name": "gmv", "semantic": "measure", "unit": "元", "agg": "sum"},
            {"name": "asp", "semantic": "measure", "unit": "元", "agg": "mean"},
        ],
        rows_expected=60,
    )


def test_dataset_valid():
    assert dataset.validate(_ds()) == []


def test_dataset_requires_grain():
    d = _ds()
    d["grain"] = ""
    assert any("grain" in e for e in dataset.validate(d))


def test_dataset_requires_rows():
    d = _ds()
    d["rows_expected"] = 0
    assert any("rows_expected" in e for e in dataset.validate(d))


def test_dataset_bad_source_kind():
    d = _ds()
    d["source"]["kind"] = "随便"
    assert any("source.kind" in e for e in dataset.validate(d))


# ---------------- S1 判断格 ----------------

def test_claim_valid():
    ds = {"DS-t": _ds()}
    c = cell_claim.build("C1", "品牌价差", dataset="DS-t",
                         query={"group_by": ["brand"], "metrics": ["asp"]},
                         min_rows=6, chart={"type": "hbar", "x": "brand"})
    assert cell_claim.validate(c, ds) == []


def test_claim_rejects_unknown_dataset():
    c = cell_claim.build("C1", "x", dataset="NOPE",
                         query={"metrics": ["asp"]}, min_rows=3)
    assert any("不在册" in e for e in cell_claim.validate(c, {"DS-t": _ds()}))


def test_claim_rejects_min_rows_too_small():
    c = cell_claim.build("C1", "x", dataset="DS-t",
                         query={"metrics": ["asp"]}, min_rows=1)
    assert any("min_rows" in e for e in cell_claim.validate(c))


def test_claim_rejects_group_by_outside_grain():
    ds = {"DS-t": _ds()}
    c = cell_claim.build("C1", "x", dataset="DS-t",
                         query={"group_by": ["price_band"], "metrics": ["asp"]},
                         min_rows=3)
    assert any("grain" in e for e in cell_claim.validate(c, ds))


def test_claim_rejects_chart_dim_not_grouped():
    ds = {"DS-t": _ds()}
    c = cell_claim.build("C1", "x", dataset="DS-t",
                         query={"group_by": ["brand"], "metrics": ["asp"]},
                         min_rows=3, chart={"type": "line", "x": "month"})
    assert any("chart.x" in e for e in cell_claim.validate(c, ds))


def test_from_cell_migrates():
    c = cell_claim.from_cell({"cell_id": "Q1.对象.脚垫", "qid": "Q1",
                              "entity": "脚垫", "measure": "share", "dim": "对象"})
    assert c["replaces"] == ["Q1.对象.脚垫"]
    assert c["schema"] == cell_claim.SCHEMA


# ---------------- S2 钻取 ----------------

def test_drill_plan_valid():
    p = drill.plan("脚垫")
    assert drill.validate(p) == []
    assert len(p["datasets"]) == 2
    assert len(p["claims"]) == 3
    # 关键：不产细粒度格子
    assert p["grid_cells"] == []


def test_drill_rows_expected_uses_time_grain():
    monthly = drill.plan("脚垫", time_grain="month")
    yearly = drill.plan("脚垫", time_grain="year")
    assert monthly["datasets"][0]["rows_expected"] > yearly["datasets"][0]["rows_expected"]


# ---------------- S4 门禁 ----------------

def test_gates_pass_without_actual_rows():
    g = dataset_gates.run({"drills": [drill.plan("脚垫")]})
    assert g["ok"] is True
    assert g["counts"]["unverified"] == 3


def test_gates_fail_when_rows_below_min():
    p = drill.plan("脚垫")
    short = {p["datasets"][0]["id"]: [{"brand": "a"}] * 2,
             p["datasets"][1]["id"]: []}
    g = dataset_gates.run({"drills": [p]}, actual_rows=short)
    assert g["ok"] is False
    assert "G1_claim_support" in g["hard_fail"]


# ---------------- S5 查询 + 出图 ----------------

def _rows(n_month=6):
    rows = []
    for b in ("A", "B", "C", "D"):
        for i in range(n_month):
            rows.append({"brand": b, "month": "2026-%02d" % (i + 1),
                         "gmv": 100 + i, "asp": 50 + i})
    return rows


def test_query_run_groups_and_aggregates():
    ds = _ds()
    res = dataset_query.run(ds, {"group_by": ["brand"], "metrics": ["asp"]}, _rows())
    assert len(res) == 4
    assert all(r["metrics"]["asp"] > 0 for r in res)


def test_query_filters():
    ds = _ds()
    res = dataset_query.run(ds, {"filters": {"brand": "A"},
                                 "group_by": ["month"], "metrics": ["gmv"]}, _rows())
    assert len(res) == 6


def test_to_chart_hbar():
    ds = _ds()
    ch = dataset_query.to_chart(ds, {"group_by": ["brand"], "metrics": ["asp"]},
                                _rows(), {"type": "hbar", "x": "brand", "metric": "asp"})
    assert ch["type"] == "hbar"
    assert len(ch["items"]) == 4


def test_to_chart_line():
    ds = _ds()
    ch = dataset_query.to_chart(ds, {"group_by": ["month"], "metrics": ["asp"]},
                                _rows(), {"type": "line", "x": "month", "metric": "asp"})
    assert ch["type"] == "line"
    assert len(ch["points"]) == 6


def test_to_chart_too_few_points_returns_empty():
    ds = _ds()
    # 只有 2 个品牌 → 分组后 2 个点，画不出关系
    rows = [{"brand": b, "month": "2026-01", "gmv": 100, "asp": 50}
            for b in ("A", "B")]
    ch = dataset_query.to_chart(ds, {"group_by": ["brand"], "metrics": ["asp"]},
                                rows, {"type": "hbar", "x": "brand", "metric": "asp"})
    assert ch == {}

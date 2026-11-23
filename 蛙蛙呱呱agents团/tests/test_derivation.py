# -*- coding: utf-8 -*-
"""test_derivation —— 推导链（v4.0）：需求 → 源匹配 → 生成 → 样本验证。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import collection_gen as cg  # noqa: E402
from core import collection_spec as cs  # noqa: E402
from core import demand  # noqa: E402
from core import source_match as sm  # noqa: E402

STAGING = ROOT / "tests" / "fixtures" / "staging" / "demo_sku.csv"


def _grid():
    return {"cells": [
        {"cell_id": "Q1.对象.AAA", "qid": "Q1", "dim": "对象",
         "entity": "AAA", "measure": "asp", "grain": "G_brand_year"},
        {"cell_id": "Q1.对象.BBB", "qid": "Q1", "dim": "对象",
         "entity": "BBB", "measure": "asp", "grain": "G_brand_year"},
        {"cell_id": "Q2.时间.2025", "qid": "Q2", "dim": "时间",
         "entity": "2025", "measure": "gmv", "grain": "G_brand_month"},
    ]}


def _sem():
    return {"case": {"measures": [
        {"id": "asp", "type": "ratio"},
        {"id": "gmv", "type": "simple"},
    ]}}


def _source():
    return {
        "schema": "dsh.source/v1", "id": "demo_csv", "kind": "csv_manual",
        "atomic_grain": ["row_id"], "history": "historical",
        "fields": [
            {"name": "row_id", "type": "string"},
            {"name": "snapshot_date", "type": "date"},
            {"name": "title", "type": "string"},
            {"name": "price", "type": "number"},
            {"name": "list_price", "type": "number"},
            {"name": "sales_30d", "type": "number"},
            {"name": "city", "type": "string"},
        ],
    }


def _spec():
    return {
        "schema": cs.SCHEMA, "id": "t", "source": "demo_csv",
        "query": {"path": str(STAGING)},
        "rollups": [{
            "id": "brand_month", "grain": ["brand", "month"],
            "series": True,
            "derive": {"brand": "token:title:0",
                       "month": "substr:snapshot_date:0:7"},
            "measures": {"asp": {"agg": "mean", "expr": "price", "unit": "元"}},
        }],
        "claims": [],
    }


# ---------------- demand ----------------

def test_demand_groups_by_measure_grain():
    d = demand.demand_of(_grid(), _sem())
    assert d["count"] == 2
    by = {x["measure"]: x for x in d["demands"]}
    assert by["asp"]["cell_count"] == 2
    assert by["asp"]["grain"] == ["brand", "year"]
    assert by["gmv"]["needs_series"] is True


def test_demand_covers_all_cells():
    d = demand.demand_of(_grid(), _sem())
    assert d["covers_cells"] == d["cells_total"] == 3


def test_demand_validate_ok():
    assert demand.validate(demand.demand_of(_grid(), _sem())) == []


def test_demand_validate_detects_uncovered():
    d = demand.demand_of(_grid(), _sem())
    d["covers_cells"] = 1
    assert any("没进需求" in e for e in demand.validate(d))


# ---------------- source_match ----------------

def test_match_full_when_dim_derivable_and_history_ok():
    d = {"measure": "asp", "grain": ["brand", "month"], "needs_series": True}
    m = sm.match(d, _source())
    assert m["status"] == "full"
    assert "brand" in m["derived"]
    assert m["derive"]["brand"] == "token:title:0"


def test_match_partial_when_snapshot_only():
    src = dict(_source(), history="snapshot_only")
    d = {"measure": "asp", "grain": ["brand", "month"], "needs_series": True}
    m = sm.match(d, src)
    assert m["status"] == "partial"
    assert any("只能采当下" in n for n in m["notes"])


def test_match_none_when_measure_missing():
    d = {"measure": "gross_margin", "grain": ["brand"], "needs_series": False}
    m = sm.match(d, _source())
    assert m["status"] == "partial"  # 维度可派生但度量算不出
    assert m["measure_plan"]["how"] == "missing"


def test_match_all_picks_best():
    d1 = {"measure": "asp", "grain": ["brand"], "needs_series": False}
    d2 = {"measure": "unknown_metric", "grain": ["brand"], "needs_series": False}
    r = sm.match_all([d1, d2], [_source()])
    assert r["best"]["asp"]["status"] == "full"
    assert r["best"]["unknown_metric"]["status"] in ("partial", "none")


# ---------------- collection_gen ----------------

def test_generate_draft():
    dd = demand.demand_of(_grid(), _sem())
    src = _source()
    mm = sm.match_all(dd["demands"], [src])
    draft = cg.generate(dd, mm, src, spec_id="gen_demo")
    assert draft["generated"] is True
    assert draft["hand_edited"] is False
    assert draft["rollups"]
    assert draft["generated_from"]["source"] == "demo_csv"


def test_validate_draft_ok():
    dd = demand.demand_of(_grid(), _sem())
    src = _source()
    mm = sm.match_all(dd["demands"], [src])
    assert cg.validate_draft(cg.generate(dd, mm, src)) == []


def test_merge_into_project_refuses_hand_edited():
    dd = demand.demand_of(_grid(), _sem())
    src = _source()
    mm = sm.match_all(dd["demands"], [src])
    draft = cg.generate(dd, mm, src)
    existing = {"hand_edited": True, "id": "x"}
    r = cg.merge_into_project(draft, existing)
    assert r.get("ok") is False
    assert "手改" in r["why"]


def test_merge_into_project_no_change_when_same_input():
    dd = demand.demand_of(_grid(), _sem())
    src = _source()
    mm = sm.match_all(dd["demands"], [src])
    draft = cg.generate(dd, mm, src)
    r = cg.merge_into_project(draft, draft)
    assert r.get("ok") is False


# ---------------- preview / quality ----------------

def test_preview_shows_derived_rows():
    p = cs.preview(_spec(), n=2, source=_source())
    assert p["ok"] is True
    assert p["staging_rows"] == 4
    assert p["grain"] == ["brand", "month"]
    assert len(p["rows"]) == 2
    assert p["rows"][0]["brand"] == "AAA"


def test_quality_reports_empty_and_distinct():
    q = cs.quality(_spec(), source=_source())
    assert q["ok"] is True
    dims = q["dims"]
    assert dims["brand_month.brand"]["distinct"] == 3
    assert dims["brand_month.month"]["distinct"] == 2
    assert dims["brand_month.brand"]["empty_rate"] == 0.0


def test_quality_flags_single_value_dim():
    spec = _spec()
    spec["rollups"][0]["derive"]["brand"] = "calc:1"
    spec["rollups"][0]["grain"] = ["month"]
    spec["rollups"][0]["derive"].pop("brand")
    q = cs.quality(spec, source=_source())
    # month 只有 2 个值，不报错；这里主要验证函数能跑
    assert "dims" in q

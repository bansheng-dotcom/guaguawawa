# -*- coding: utf-8 -*-
"""data_layer 域测试（合并自 7 个文件）。

源文件：
    test_data_standard.py —— 四份数据契约：校验 / 画像 / 双向适配。
    test_dataset_layer.py —— test_dataset_layer —— 数据集层 v2.0（S0–S5）。
    test_grain.py —— test_grain —— 采集层 v3（S0–S6）：源画像 / 粒度校验 / rollup / 三业务回归。
    test_derivation.py —— test_derivation —— 推导链（v4.0）：需求 → 源匹配 → 生成 → 样本验证。
    test_two_stage.py —— P1-2 两段式接线：探源卡是 bundle；探测结论不被第二段拆卡冲掉。
    test_method_params.py —— 方法参数（P1-7）：缺省走中性默认，项目文件覆盖；不内置任何业务线口径。
    test_analysis_unit.py —— core.data.analysis_unit 单测（DATA-LAYER-SOP v3.0 · S0）。
"""
from __future__ import annotations
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
ROOT = TEAM
REPO = TEAM.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))


from core.data import data_standard as ds
from core.data import data_model
import random
from core.claims import cell_claim
from core.data import dataset, dataset_gates, dataset_query
from core import drill
from core.sources import collection_spec as cs
from core import grain as g
from core.sources import source_profile as sp
from core.sources import collection_gen as cg
from core import demand
from core.sources import source_match as sm
import json
import tempfile
from core.cards import pipeline as card_issue
from core.report import report_clarify
from core import method_params, analysis_methods
from core.data import analysis_desk
import pytest
from core.data import analysis_unit as au

from core.data import data_model as dm



# ====================================================================
# 合并自 test_data_standard.py：四份数据契约：校验 / 画像 / 双向适配。
# ====================================================================
# -*- coding: utf-8 -*-


def _obs(**kw):
    base = {"metric_id": "m_price", "entity": "甲", "period": "2025-01",
            "value": 10.0, "unit": "元"}
    base.update(kw)
    return ds.Observation.from_dict(base)


def test_record_requires_values():
    ok = ds.Record(record_id="r1", source_id="s1", values={"price": "10"})
    assert ds.validate_record(ok) == []
    assert ds.validate_record({"record_id": "r1", "source_id": "s1", "values": {}})
    assert ds.validate_record({"record_id": "", "source_id": "s1",
                               "values": {"a": 1}})


def test_observation_requires_unit_even_when_unknown():
    assert ds.validate_observation(_obs()) == []
    assert any("unit" in e for e in ds.validate_observation(_obs(unit="")))
    assert any("value" in e for e in ds.validate_observation(
        {"metric_id": "m", "entity": "甲", "period": "2025",
         "value": "不是数", "unit": "元"}))


def test_observation_base_value_uses_normalized_when_present():
    o = _obs(value=12.0, unit="万元", value_base=120000.0, unit_base="元", scale=1e4)
    assert o.base_value() == 120000.0
    raw = _obs(value=12.0, unit="万元")
    assert raw.base_value() == 12.0


def test_dataset_rejects_duplicate_primary_key():
    a = _obs()
    b = _obs(value=11.0)
    assert ds.validate_dataset(ds.Dataset(name="d", grain=["entity", "period"],
                                          observations=[a, b]))
    d = ds.Dataset(name="d", grain=["entity", "period"], observations=[a])
    assert ds.validate_dataset(d) == []


def test_chart_spec_rejects_unknown_type_and_missing_refs():
    good = ds.ChartSpec(chart_type="hbar", data_ref={"dataset": "d", "metric": "m"},
                        encode={"label": "entity", "value": "value"})
    assert ds.validate_chart_spec(good) == []
    assert ds.validate_chart_spec(ds.ChartSpec(chart_type="3d_globe", data_ref={},
                                               encode={}))
    assert any("data_ref" in e for e in ds.validate_chart_spec(
        ds.ChartSpec(chart_type="hbar", data_ref={}, encode={"value": "v"})))


def test_profile_reports_time_and_categories():
    obs = [_obs(period="2025-01"), _obs(period="2025-02", entity="乙", value=0.0)]
    p = ds.profile_observations(obs)
    assert p["rows"] == 2
    assert p["time_like"] is True
    assert "entity" in p["categorical"]
    assert p["value"]["zero_rate"] == 0.5


def test_roundtrip_with_legacy_row():
    raw = data_model.build_raw([
        {"id": "n1", "name": "甲市销售额", "value": 3.5, "unit": "亿元",
         "period": "2025", "entity": "甲市", "source_file": "s.csv"}])
    row = raw["rows"][0]
    o = ds.observation_from_row(row)
    assert o.metric_id == row["metric_id"] and o.unit == "亿元"
    back = ds.row_from_observation(o)
    for k in data_model.ROW_FIELDS:
        assert k in back
    assert back["value_base"] == row["value_base"]


def test_dataset_from_raw_keeps_conflicts_in_manifest():
    raw = data_model.build_raw([
        {"id": "a", "name": "销量", "value": 1, "unit": "件", "period": "2025",
         "entity": "甲", "source_file": "a.csv", "grade": "A"},
        {"id": "b", "name": "销量", "value": 2, "unit": "件", "period": "2025",
         "entity": "甲", "source_file": "b.csv", "grade": "B"}])
    d = ds.dataset_from_raw(raw, name="sales")
    assert len(d.observations) == 1
    assert d.manifest["conflicts"]
    assert d.dq["rows"] == 1


def test_dataset_from_records_skips_bad_rows():
    recs = [ds.Record(record_id="1", source_id="s", values={
        "entity": "甲", "period": "2025", "value": "10"}),
        ds.Record(record_id="2", source_id="s", values={
            "entity": "", "period": "2025", "value": "10"}),
        ds.Record(record_id="3", source_id="s", values={
            "entity": "乙", "period": "2025", "value": "坏"})]
    d = ds.dataset_from_records(recs)
    assert len(d.observations) == 1
    assert ds.validate_dataset(d) == []


def test_conflict_prefers_higher_grade():
    raw = data_model.build_raw([
        {"id": "a", "name": "销量", "value": 1, "unit": "件", "period": "2025",
         "entity": "甲", "source_file": "c.csv"},
        {"id": "b", "name": "销量", "value": 2, "unit": "件", "period": "2025",
         "entity": "甲", "source_file": "a.csv"}],
        sources=[{"file": "c.csv", "grade": "C"}, {"file": "a.csv", "grade": "A"}])
    assert raw["rows"][0]["value"] == 2
    assert raw["conflicts"][0]["verdict"] == "kept_high_grade"
    assert raw["coverage"]["conflicts_needs_human"] == 0


def test_conflict_same_grade_needs_human():
    raw = data_model.build_raw([
        {"id": "a", "name": "销量", "value": 1, "unit": "件", "period": "2025",
         "entity": "甲", "source_file": "a.csv"},
        {"id": "b", "name": "销量", "value": 2, "unit": "件", "period": "2025",
         "entity": "甲", "source_file": "b.csv"}],
        sources=[{"file": "a.csv", "grade": "B"}, {"file": "b.csv", "grade": "B"}])
    assert raw["rows"][0]["value"] == 1
    assert raw["conflicts"][0]["verdict"] == "needs_human"
    assert raw["coverage"]["conflicts_needs_human"] == 1


def test_unknown_unit_is_counted_not_silently_scaled():
    raw = data_model.build_raw([
        {"id": "a", "name": "箱数", "value": 3, "unit": "箱", "period": "2025",
         "entity": "甲", "source_file": "a.csv"}])
    assert raw["coverage"]["unit_unverified"] == 1
    assert raw["metrics"][0]["unit_verified"] is False


# ====================================================================
# 合并自 test_dataset_layer.py：test_dataset_layer —— 数据集层 v2.0（S0–S5）。
# ====================================================================
# -*- coding: utf-8 -*-


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


# ====================================================================
# 合并自 test_grain.py：test_grain —— 采集层 v3（S0–S6）：源画像 / 粒度校验 / rollup / 三业务回归。
# ====================================================================
# -*- coding: utf-8 -*-


def _src(**kw):
    base = {
        "schema": sp.SCHEMA, "id": "s1", "kind": "csv_manual",
        "atomic_grain": ["row_id"], "history": "historical",
        "fields": [
            {"name": "row_id", "type": "string"},
            {"name": "snapshot_date", "type": "date"},
            {"name": "title", "type": "string"},
            {"name": "price", "type": "number"},
            {"name": "volume", "type": "number"},
        ],
    }
    base.update(kw)
    return base


def _rollup(**kw):
    base = {
        "id": "r1",
        "grain": ["brand", "month"],
        "derive": {"brand": "token:title:0", "month": "substr:snapshot_date:0:7"},
        "measures": {"asp": {"agg": "mean", "expr": "price"}},
    }
    base.update(kw)
    return base


# ---------------- S0 源画像 ----------------

def test_source_valid():
    assert sp.validate(_src()) == []


def test_source_requires_atomic_grain():
    assert any("atomic_grain" in e for e in sp.validate(_src(atomic_grain=[])))


def test_source_history_enum():
    assert any("history" in e for e in sp.validate(_src(history="whatever")))


def test_source_field_type():
    s = _src()
    s["fields"][0]["type"] = "nope"
    assert any("type" in e for e in sp.validate(s))


def test_source_atomic_grain_must_be_field():
    assert any("不在 fields" in e for e in sp.validate(_src(atomic_grain=["nope"])))


# ---------------- S1 粒度校验 ----------------

def test_grain_ok():
    assert g.check(_src(), _rollup()) == []


def test_grain_g_a_missing_atomic():
    errs = g.check(_src(atomic_grain=[]), _rollup())
    assert any("G-A" in e for e in errs)


def test_grain_g_b_undeducible():
    r = _rollup(grain=["brand", "unknown_dim"])
    assert any("G-B" in e for e in g.check(_src(), r))


def test_grain_g_c_bad_expr_column():
    r = _rollup(measures={"asp": {"agg": "mean", "expr": "nope"}})
    assert any("G-C" in e for e in g.check(_src(), r))


def test_grain_g_d_missing_grain():
    r = _rollup(grain=[])
    assert any("G-D" in e for e in g.check(_src(), r))


def test_grain_g_e_needs_history():
    # 源只能采当下 + rollup 要序列 → 必须被拦
    errs = g.check(_src(history="snapshot_only"), _rollup(series=True))
    assert any("G-E" in e for e in errs)


def test_grain_g_e_ok_with_history():
    assert g.check(_src(history="historical"), _rollup(series=True)) == []


# ---------------- S1 rollup 运算 ----------------

def _rows_grain():
    return [
        {"row_id": "1", "snapshot_date": "2025-01-15", "title": "AAA 脚垫",
         "price": 100, "volume": 2},
        {"row_id": "2", "snapshot_date": "2025-01-20", "title": "AAA 脚垫",
         "price": 200, "volume": 3},
        {"row_id": "3", "snapshot_date": "2025-02-10", "title": "BBB 脚垫",
         "price": 150, "volume": 1},
    ]


def test_rollup_rows_mean_sum():
    out = g.rollup_rows(_rows_grain(), _rollup())
    by = {(r["brand"], r["month"]): r for r in out}
    assert by[("AAA", "2025-01")]["asp"] == 150.0
    assert by[("AAA", "2025-01")]["_rows"] == 2
    assert by[("BBB", "2025-02")]["asp"] == 150.0


def test_rollup_rows_arithmetic_expr():
    r = _rollup(measures={"revenue": {"agg": "sum", "expr": "price * volume"}})
    out = g.rollup_rows(_rows_grain(), r)
    by = {(x["brand"], x["month"]): x for x in out}
    assert by[("AAA", "2025-01")]["revenue"] == 800.0


def test_rollup_bucket():
    r = _rollup(grain=["price_band", "month"],
                derive={"price_band": "bucket:price:120,180:低,中,高",
                        "month": "substr:snapshot_date:0:7"})
    out = g.rollup_rows(_rows_grain(), r)
    assert {x["price_band"] for x in out} == {"低", "中", "高"}


def test_safe_eval_rejects_calls():
    try:
        g._safe_eval("__import__('os').system('x')", {})
    except Exception:
        return
    raise AssertionError("应该拒绝函数调用")


# ---------------- S3 采集规格 + S6 三业务回归 ----------------

def test_three_businesses_same_code():
    """同一套代码，三套 YAML，都合法——这就是「适配各种业务」的证据。

    业务 YAML 放在 tests/fixtures/，**不进 configs/**：
    源码里不许有业务线，业务只活在项目目录（或测试夹具）里。
    """
    for name in ("auto_interior", "demo_maternal", "demo_vegetable"):
        spec = cs.load(str(ROOT / "tests" / "fixtures" / "collections"
                           / (name + ".yaml")))
        assert spec, name
        errs = cs.validate(spec)
        assert not errs, (name, errs)


def test_spec_rejects_unknown_dataset():
    spec = {
        "schema": cs.SCHEMA, "id": "x", "source": "manual_csv",
        "query": {"path": "a.csv"},
        "rollups": [_rollup()],
        "claims": [{"id": "c1", "dataset": "nope",
                    "query": {"group_by": ["brand"], "metrics": ["asp"]},
                    "min_rows": 5}],
    }
    assert any("不在 rollups" in e for e in cs.validate(spec, _src()))


def test_spec_rejects_bad_claim_query():
    spec = {
        "schema": cs.SCHEMA, "id": "x", "source": "manual_csv",
        "query": {"path": "a.csv"},
        "rollups": [_rollup()],
        "claims": [{"id": "c1", "dataset": "r1",
                    "query": {"group_by": ["nope"], "metrics": ["asp"]},
                    "min_rows": 5}],
    }
    assert any("group_by" in e for e in cs.validate(spec, _src()))


# ====================================================================
# 合并自 test_derivation.py：test_derivation —— 推导链（v4.0）：需求 → 源匹配 → 生成 → 样本验证。
# ====================================================================
# -*- coding: utf-8 -*-


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
    # 度量算不出来 = 无数据（status=none），不能在报告里编数字
    d = {"measure": "gross_margin", "grain": ["brand"], "needs_series": False}
    m = sm.match(d, _source())
    assert m["status"] == "none"
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


# ====================================================================
# 合并自 test_two_stage.py：P1-2 两段式接线：探源卡是 bundle；探测结论不被第二段拆卡冲掉。
# ====================================================================
# -*- coding: utf-8 -*-


INTENT = "区域市场的品类规模、份额与价格趋势"
SEM = """schema: dsh.semantic/v3
generated: false
entities:
- id: region
  type: spatial
  levels: [全国, 省]
- id: category
  type: hierarchy
  levels: [大类, 子类]
- id: period
  type: time
  grain: year
grain_declarations:
- id: G_region_year
  dims: [region, year]
measures:
- id: gmv
  type: simple
  agg: sum
  expr: gmv
  unit: 亿元
  grain: G_region_year
- id: share
  type: ratio
  numerator: gmv
  denominator: gmv@total
  unit: '%'
  grain: G_region_year
boundaries:
- id: B1
  text: 测试口径
  affects: [gmv]
fingerprint:
  key: [measure_id, entity_scope, period]
"""


def _project() -> Path:
    base = Path(tempfile.mkdtemp(prefix="guagua_two_stage_"))
    assert report_clarify.write(INTENT, str(base))["ok"]
    assert report_clarify.confirm(str(base),
                                  user_said="用户确认：按这个意图做，先出格子再探源")["ok"]
    (base / "semantic_layer.yaml").write_text(SEM, encoding="utf-8")
    return base


def test_probe_card_is_bundle_with_probe_task_type():
    base = _project()
    assert card_issue.prepare(base)["ok"]
    res = card_issue.prepare_probe_cards(base)
    assert res["ok"]
    bundle = json.loads((base / "cards" / "r18" / "bundle.json")
                        .read_text(encoding="utf-8"))
    assert bundle["brief"]["task_type"] == "探源型"
    assert bundle["card"]["owner"] == "r18"
    layers = {m["id"].split(".")[0] for m in bundle["brief"]["must_answer"]}
    assert {"L0", "L1", "L2"} <= layers and "L3" not in layers


def test_second_pass_keeps_probe_state_until_semantics_change():
    base = _project()
    assert card_issue.prepare(base)["ok"]
    gp = base / "plan" / "grid.json"
    grid = json.loads(gp.read_text(encoding="utf-8"))
    cid = grid["cells"][0]["cell_id"]
    grid["cells"][0]["collectable"] = "partial"
    grid["cells"][0]["availability"] = "available"
    gp.write_text(json.dumps(grid, ensure_ascii=False), encoding="utf-8")

    assert card_issue.prepare(base)["ok"]
    again = json.loads(gp.read_text(encoding="utf-8"))
    got = next(c for c in again["cells"] if c["cell_id"] == cid)
    assert got.get("collectable") == "partial"
    assert again.get("merged_fields", 0) > 0

    # 语义层一变 → 指纹变 → 重建，旧状态不再保留
    sem = (base / "semantic_layer.yaml").read_text(encoding="utf-8")
    (base / "semantic_layer.yaml").write_text(sem.replace("测试口径", "改口径"),
                                              encoding="utf-8")
    assert card_issue.prepare(base)["ok"]
    rebuilt = json.loads(gp.read_text(encoding="utf-8"))
    got2 = next(c for c in rebuilt["cells"] if c["cell_id"] == cid)
    assert "collectable" not in got2


# ====================================================================
# 合并自 test_method_params.py：方法参数（P1-7）：缺省走中性默认，项目文件覆盖；不内置任何业务线口径。
# ====================================================================
# -*- coding: utf-8 -*-


def teardown_function(_):
    method_params.reset()


def test_default_is_neutral():
    p = method_params.load(None)
    assert p["missing"] is True
    assert p["loss_default"] == 0.0 and p["cold_default"] == 0.0
    assert p["freight"] == 0.0 and p["categories"] == []
    assert "未提供 method_params" in method_params.footnote(p)


def test_project_file_overrides(tmp_path):
    (tmp_path / "method_params.yaml").write_text(
        "schema: dsh.method_params/v1\n"
        "price_unit: 元/件\n"
        "unit_scales: {公斤: 0.5}\n"
        "freight: 0.3\n"
        "categories:\n  - {key: 甲, loss: 0.02, cold: 0.1, shelf: 3}\n",
        encoding="utf-8")
    p = method_params.configure(tmp_path)
    assert p["missing"] is False and p["price_unit"] == "元/件"
    assert analysis_methods.rule_of("甲类")["loss"] == 0.02
    assert analysis_methods.cat_key("甲类") == "甲"
    # 单位换算来自项目参数
    assert analysis_desk._unit_scale("元/公斤") == (0.5, "元/件")


def test_missing_params_do_not_apply_business_defaults():
    method_params.reset()
    assert method_params.current()["missing"] is True
    assert analysis_desk._unit_scale("元/公斤") == (1.0, "元/公斤")
    assert analysis_methods.rule_of("任意品类")["loss"] == 0.0


def test_validate_catches_bad_values(tmp_path):
    bad = {"schema": "dsh.method_params/v1", "freight": -1,
           "unit_scales": {"公斤": "x"}, "categories": [{}],
           "channel_hints": {"retail": "不是列表"},
           "metric_roles": []}
    errs = method_params.validate(bad)
    assert len(errs) >= 4


def test_metric_roles_are_project_declared(tmp_path):
    (tmp_path / "method_params.yaml").write_text(
        "schema: dsh.method_params/v1\n"
        "metric_roles:\n  market_size: demo_market\n  shares: demo_share\n",
        encoding="utf-8")
    p = method_params.configure(tmp_path)
    assert p["metric_roles"] == {"market_size": "demo_market",
                                "shares": "demo_share"}


def test_channel_hints_can_be_extended_by_project(tmp_path):
    # 项目自己的列名口径写在项目配置里；团内代码只认中性默认词
    (tmp_path / "method_params.yaml").write_text(
        "channel_hints:\n  retail: [\"示例列名A\"]\n", encoding="utf-8")
    method_params.configure(tmp_path)
    hints = dict(analysis_desk._channel_hints())
    assert "示例列名A" in hints["retail"]
    assert "终端" in hints["retail"]


def test_research_methods_do_not_mount_without_roles():
    """没有 metric_roles 时研究类方法不挂载——不许退回某条业务线的默认口径。"""
    from core.methods import research
    class Caps:
        desk = type("D", (), {"facts": [], "assumptions": []})()
    assert research._facts(Caps, "market_size") == []
    assert research._metric("shares") == ""


# ====================================================================
# 合并自 test_analysis_unit.py：core.data.analysis_unit 单测（DATA-LAYER-SOP v3.0 · S0）。
# ====================================================================
# -*- coding: utf-8 -*-


def _sem_unit(**over):
    base = {
        "entities": [
            {"id": "region", "type": "spatial", "levels": ["山东", "河北", "河南"]},
            {"id": "category", "type": "hierarchy", "levels": ["叶菜类", "茄果类"]},
            {"id": "period", "type": "time", "grain": "year"},
        ],
        "grain_declarations": [
            {"id": "G_region_category_month", "dims": ["region", "category", "month"]},
            {"id": "G_region_year", "dims": ["region", "year"]},
            {"id": "G_ghost", "dims": ["region", "brand"]},
        ],
        "measures": [
            {"id": "asp", "agg": "avg", "unit": "元/公斤", "grain": "G_region_category_month"},
            {"id": "size", "agg": "sum", "unit": "万吨", "grain": "G_region_year"},
            {"id": "bad", "agg": "sum", "unit": "元", "grain": "G_ghost"},
            {"id": "noenum", "agg": "sum", "unit": "元", "grain": "G_region_category_month"},
        ],
    }
    base.update(over)
    # 走 load 的统一结构
    return {
        "entities": au._index(base["entities"]),
        "grain_declarations": au._index(base["grain_declarations"]),
        "measures": au._index(base["measures"]),
    }


def test_unit_dims_and_time_grain():
    u = au.from_measure("asp", _sem_unit())
    assert u["dims"] == ["region", "category"]
    assert u["time_grain"] == "month"          # 取自 grain 声明，不是全局 period.grain
    assert u["unit"] == "元/公斤"


def test_rows_expected_is_cardinality_times_periods():
    sem = _sem_unit()
    u = au.from_measure("size", sem)           # region 3 × year 3
    assert au.rows_expected(u, sem) == 3 * 3
    u2 = au.from_measure("asp", sem)           # region 3 × category 2 × month 36
    assert au.rows_expected(u2, sem) == 3 * 2 * 36


def test_missing_entity_raises_not_defaults():
    """维度不在 sem 里 → 抛错；绝不能像 v2 那样套品牌模板。"""
    with pytest.raises(KeyError) as e:
        au.from_measure("bad", _sem_unit())
    assert "MISSING_ENTITY" in str(e.value)


def test_no_enumeration_raises():
    sem = _sem_unit()
    sem["entities"]["category"] = {"id": "category", "type": "hierarchy"}   # 无 levels
    u = au.from_measure("noenum", sem)
    with pytest.raises(KeyError) as e:
        au.rows_expected(u, sem)
    assert "NO_CARDINALITY" in str(e.value)


def test_missing_section_raises(tmp_path):
    p = tmp_path / "sem.yaml"
    p.write_text("schema: dsh.semantic/v3\nentities: []\n", encoding="utf-8")
    with pytest.raises(KeyError) as e:
        au.load(p)
    assert "SEM_MISSING" in str(e.value)


def test_plan_units_keeps_errors_visible():
    units = au.plan_units(_sem_unit())
    errs = [u for u in units if "error" in u]
    assert any("MISSING_ENTITY" in u["error"] for u in errs)
    ok = [u for u in units if "error" not in u]
    assert ok and all("dataset_id" in u for u in ok)


def test_dataset_id_has_no_business_word():
    u = au.from_measure("asp", _sem_unit())
    did = au.dataset_id(u)
    assert did == "DS-asp-region-category-month"
    for bad in ("品牌", "gmv", "价格带", "长尾"):
        assert bad not in did


# ====================================================================
# 合并自 test_data_model.py（原为无 pytest 的脚本式自测，2026-11-25 转正）
# ====================================================================
def test_data_model_build_raw_and_export(tmp_path):
    nums = [
        {"id": "r05:N1", "name": "中国宠物消费市场规模（城镇犬猫）",
         "value": 3126, "unit": "亿元", "period": "2025", "source_file": "r05:S1"},
        {"id": "r05:N2", "name": "中国宠物消费市场规模（城镇犬猫）",
         "value": 3002, "unit": "亿元", "period": "2024", "source_file": "r05:S1"},
        {"id": "r06:N1", "name": "北京宠物店数量（走访口径）",
         "value": 1.2, "unit": "万家", "period": "2025", "source_file": "r06:S3"},
        # 同键冲突：同指标同城同期不同值
        {"id": "r06:N2", "name": "北京宠物店数量（走访口径）",
         "value": 1.5, "unit": "万家", "period": "2025", "source_file": "r06:S4"},
        {"id": "r03:N1", "name": "毛利率", "value": 45, "unit": "%",
         "period": "2025", "source_file": "r03:S1"},
    ]
    srcs = [{"file": "r05:S1", "grade": "A"}, {"file": "r06:S3", "grade": "B"},
            {"file": "r06:S4", "grade": "C"}, {"file": "r03:S1", "grade": "B"}]
    raw = dm.build_raw(nums, srcs)
    cov = raw["coverage"]
    assert cov["rows"] == 4
    assert cov["conflicts"] == 1
    assert cov["metrics"] == 3
    assert {r["role"] for r in raw["rows"]} == {"r05", "r06", "r03"}
    assert any(r["unit_base"] == "元" and r["scale"] == 1e8 for r in raw["rows"])
    # 地名只认 configs/geo_tokens.yaml 里登记过的（「中国」）；
    # 未登记的城市（「北京」）不得被臆造成 entity（2026-11-22 中性化后的契约）。
    assert any(r["entity"] == "中国" for r in raw["rows"])
    assert all(r["entity"] != "北京" for r in raw["rows"])
    assert any(r["grade"] == "A" for r in raw["rows"])
    assert all(r["source_id"] for r in raw["rows"])
    assert "高等级优先" in raw["conflicts"][0]["rule"]

    paths = dm.export(raw, tmp_path, srcs, title="自测")
    assert Path(paths["raw.xlsx"]).is_file()
    assert Path(paths["raw.csv"]).is_file()
    assert Path(paths["raw.json"]).is_file()
    from openpyxl import load_workbook
    wb = load_workbook(paths["raw.xlsx"], read_only=True)
    names = list(wb.sheetnames)
    wb.close()
    assert len(names) == 6 and "01 原始数据" in names

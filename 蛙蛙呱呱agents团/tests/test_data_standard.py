# -*- coding: utf-8 -*-
"""四份数据契约：校验 / 画像 / 双向适配。"""
from __future__ import annotations

import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core import data_standard as ds  # noqa: E402
from core import data_model  # noqa: E402


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

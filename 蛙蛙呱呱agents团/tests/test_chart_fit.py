# -*- coding: utf-8 -*-
"""P4：数据画像 → 候选图型；图型契约同源审计。"""
from __future__ import annotations

import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core import chart_field_contract as chart_contract  # noqa: E402
from core import chart_fit, data_standard as ds  # noqa: E402


def _ds(pairs, unit="元"):
    obs = [ds.Observation(metric_id="m", entity=e, period=p, value=v, unit=unit)
           for e, p, v in pairs]
    d = ds.Dataset(name="demo", grain=["entity", "period"], observations=obs)
    d.profile = ds.profile_observations(obs)
    return d


def test_empty_dataset_degrades_to_text():
    out = chart_fit.fit(_ds([]))
    assert out["recommended"] == "text"
    assert out["candidates"][0]["fallback"] == "table"


def test_time_series_picks_line_family():
    out = chart_fit.fit(_ds([("甲", "2025-0%d" % i, float(i)) for i in (1, 2, 3, 4)]))
    rec = out["recommended"]
    assert rec in ("line", "multi_line", "area")


def test_negative_values_flag_diverging():
    out = chart_fit.fit(_ds([("甲", "2025", -2.0), ("乙", "2025", 3.0),
                             ("丙", "2025", 1.0)]))
    assert "diverging" in [c["type"] for c in out["candidates"]]


def test_flat_values_refuse_to_chart():
    out = chart_fit.fit(_ds([("甲", "2025", 0.0), ("乙", "2025", 0.0)]))
    assert out["recommended"] == "text"


def test_share_unit_offers_pie():
    out = chart_fit.fit(_ds([("甲", "2025", 35.0), ("乙", "2025", 25.0),
                             ("丙", "2025", 40.0)], unit="%"))
    assert "pie" in [c["type"] for c in out["candidates"]]


def test_required_of_resolves_alias():
    assert chart_contract.required_of("share") == chart_contract.required_of("share_bar")


def test_contract_audit_detects_missing_field():
    bad = {"hbar": {"type": "hbar"}}
    a = chart_contract.contract_audit(bad)
    assert not a["ok"] and a["mismatch"][0]["missing_in_sample"] == ["items"]


def test_build_spec_does_not_embed_numbers():
    d = _ds([("甲", "2025-01", 1.0), ("乙", "2025-02", 2.0)])
    cs = chart_contract.build_spec(d, "line", title="趋势")
    assert cs.chart_type == "line"
    assert cs.data_ref["dataset"] == "demo"
    assert "values" not in cs.to_dict()
    assert ds.validate_chart_spec(cs) == []


def test_real_samples_match_contract_if_available():
    try:
        from samples import samples  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return
    a = chart_contract.contract_audit(samples.SAMPLE)
    assert a["ok"], a["mismatch"][:3]

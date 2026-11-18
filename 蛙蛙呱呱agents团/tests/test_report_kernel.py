# -*- coding: utf-8 -*-
"""report_kernel 单元测试：契约、规格、一致性、序列、交付门禁。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.report_kernel import consistency, contract as C, gate, series, specs

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT.parent / "内蒙古肉禽蛋调研_2026-11-12"


def _good_contract():
    c = C.template("RPT-TEST-01", "测试报告")
    c.update({
        "decision": "决定是否上线",
        "audience": "创始人",
        "questions": ["问题一", "问题二", "问题三"],
        "data_cutoff": "2026-11-16",
        "owner": "R01",
        "reviewer": "R04",
        "source_count": 30,
        "series_periods": 12,
    })
    return c


def test_contract_requires_six_fields():
    assert C.validate(_good_contract())["ok"]
    bad = _good_contract()
    bad["questions"] = ["只有一个"]
    res = C.validate(bad)
    assert not res["ok"]
    assert any("questions" in e for e in res["errors"])


def test_contract_blocks_trend_without_series():
    c = _good_contract()
    c["trend_required"] = True
    c["series_periods"] = 4
    res = C.validate(c)
    assert not res["ok"]
    assert any("12" in e for e in res["errors"])


def test_contract_blocks_cross_day_without_alignment():
    c = _good_contract()
    c["time_span_days"] = 5
    res = C.validate(c)
    assert not res["ok"]
    c["alignment_note"] = "已按同日对齐，剩余时点差已标注"
    assert C.validate(c)["ok"]


def test_table_specs_units_tone_total():
    tb = {
        "caption": "价格与变化（元/斤）",
        "columns": ["品类", "批发价", "变化率"],
        "rows": [["牛肉", "36.00", "+3.6%"], ["合计", "36.00", "+3.6%"]],
    }
    out, st = specs.infer_table(tb)
    assert out["columns"][1].get("num")
    assert "元/斤" in out["columns"][1]["text"]
    assert out["rows"][0][2].get("tone") == "up"
    assert out.get("total_row")
    assert st["with_unit"] >= 1


def test_chart_specs_fill_ref_and_subtitle():
    ch = {
        "type": "hbar", "title": "牛肉 36.00 元", "unit_meta": "元/斤",
        "source": "测试", "bars": [{"label": "a", "value": 30},
                                  {"label": "b", "value": 40}],
    }
    out, st, errs = specs.complete_chart(ch)
    assert not errs
    assert out["ref"]["value"] == 35
    assert out["subtitle"]
    assert st["ref_added"] == 1


def test_chart_specs_reject_title_without_number():
    ch = {"type": "hbar", "title": "牛肉价格", "unit_meta": "元/斤",
          "source": "测试", "bars": [{"label": "a", "value": 1}]}
    _, _, errs = specs.complete_chart(ch)
    assert any("数字" in e for e in errs)


def test_consistency_detects_conflict():
    reg = {"metrics": [
        {"id": "markup", "value": 4.0, "unit": "倍"},
        {"id": "markup", "value": 11.3, "unit": "倍"},
    ]}
    res = consistency.check_registry(reg)
    assert not res["ok"]
    assert any("markup" in e for e in res["errors"])


def test_series_blocks_short_trend():
    c = _good_contract()
    c["sections"] = [{"title": "趋势：未来两个月 +7%"}]
    c["series_periods"] = 4
    assert not series.check_series(c)["ok"]


@pytest.mark.skipif(not (PROJECT / "报告质量根因分析_2026-11-16.html").exists(),
                    reason="缺少根因报告交付件")
def test_gate_positive_on_delivered_report():
    html = PROJECT / "报告质量根因分析_2026-11-16.html"
    if not html.with_suffix(".ship.json").exists():
        pytest.skip("缺少 ship 契约")
    res = gate.run_gate(html)
    assert res["ok"], res["errors"]
    assert res["level"] == "L4"


@pytest.mark.skipif(not (PROJECT / "_archive_2026-11-12").exists(),
                    reason="缺少归档旧版")
def test_gate_negative_on_old_report():
    old = PROJECT / "_archive_2026-11-12" / "内蒙古肉禽蛋市场调研与数据分析报告.html"
    if not old.exists():
        pytest.skip("缺少旧版文件")
    res = gate.run_gate(old, strict=False)
    assert not res["ok"]
    failed = {c["id"] for c in res["checks"] if not c["ok"]}
    assert {"C2_level", "C4_figures", "C5_table_units"}.issubset(failed)

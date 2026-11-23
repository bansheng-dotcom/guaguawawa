# -*- coding: utf-8 -*-
"""test_shape_gate —— 数据形状门禁（SOP §2.5）。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import shape_gate  # noqa: E402


def _rows(per_metric):
    rows = []
    for m, n in per_metric.items():
        for i in range(n):
            rows.append({"metric_id": m, "value": i, "entity": f"e{i}"})
    return rows


def test_pass_when_most_metrics_have_3_rows():
    r = shape_gate.gate(_rows({"a": 3, "b": 4, "c": 3, "d": 1}))
    assert r["ratio"] == 0.75
    assert r["verdict"] == "pass"
    assert r["allowed_charts"] == "2d"


def test_1d_only_in_middle_band():
    r = shape_gate.gate(_rows({"a": 3, "b": 1, "c": 1, "d": 1}))
    assert r["ratio"] == 0.25
    assert r["verdict"] == "fail"
    assert r["allowed_charts"] == "none"


def test_fail_below_floor_and_lists_thin_metrics():
    r = shape_gate.gate(_rows({"a": 1, "b": 1, "c": 2, "d": 1, "e": 1}))
    assert r["verdict"] == "fail"
    assert {t["metric"] for t in r["thin_metrics"]} >= {"a", "b", "d", "e"}


def test_empty_rows_is_fail():
    r = shape_gate.gate([])
    assert r["ratio"] == 0.0
    assert r["verdict"] == "fail"


def test_ratio_boundary_at_half():
    # 2/4 = 0.5 → pass（SOP: ≥0.5 通过）
    r = shape_gate.gate(_rows({"a": 3, "b": 3, "c": 1, "d": 1}))
    assert r["ratio"] == 0.5
    assert r["verdict"] == "pass"


def test_ratio_boundary_at_03():
    # 1/3 ≈ 0.333 → 1d_only
    r = shape_gate.gate(_rows({"a": 3, "b": 1, "c": 1}))
    assert r["verdict"] == "1d_only"
    assert r["allowed_charts"] == "1d"

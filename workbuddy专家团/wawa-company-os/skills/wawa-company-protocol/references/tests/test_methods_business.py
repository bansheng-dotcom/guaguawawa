# -*- coding: utf-8 -*-
"""业务定量技能测试。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.methods import business  # noqa: E402


def test_expected_value() -> None:
    r = business.expected_value([
        {"name": "A", "p": 0.6, "good": 100, "bad": -50, "cost": 10},
        {"name": "B", "p": 0.9, "good": 30, "bad": -10, "cost": 5},
    ])
    assert r["best"] in ("A", "B")
    assert r["ranking"][0]["ev"] >= r["ranking"][1]["ev"]
    assert r["breakeven_p_vs_second"] is not None


def test_queue() -> None:
    r = business.queue_wait(8, 10, 1.0, 1.0)
    assert abs(r["utilization"] - 0.8) < 1e-6
    assert r["wait_days"] > 0
    assert r["cycle_days"] > r["wait_days"]


def test_tam_mc() -> None:
    r = business.tam_mc(1000, 0.1, 0.3, 50, 100, n=2000)
    assert r["p10"] <= r["p50"] <= r["p90"]
    assert r["mean"] > 0


def test_rice() -> None:
    r = business.rice([
        {"name": "A", "reach": 100, "impact": 3, "confidence": 0.8, "effort": 5},
        {"name": "B", "reach": 50, "impact": 5, "confidence": 0.9, "effort": 2},
    ])
    assert len(r["ranking"]) == 2
    assert r["sensitivity"][0]["top"]


def test_data_profile() -> None:
    rows = [{"x": 1, "t": "2026-01"}, {"x": None, "t": "2026-02"},
            {"x": 3, "t": "2026-03"}, {"x": 4, "t": "2026-04"}]
    r = business.data_profile(rows, ["x"], "t")
    assert r["columns"]["x"]["missing_pct"] == 25.0
    assert "psi" in r["columns"]["x"]


def test_slo_budget() -> None:
    r = business.slo_budget(99.0, 30, 1_000_000, 200)
    assert abs(r["allowed_downtime_min"] - 432.0) < 0.1
    assert r["status"] in ("正常", "预警", "超预算")


def test_experiment_power() -> None:
    r = business.experiment_power(0.10, 0.02)
    assert r["n_per_group"] > 1000
    assert r["n_total"] == r["n_per_group"] * 2


def test_hiring_funnel() -> None:
    r = business.hiring_funnel(1000, 300, 100, 20, 10)
    assert r["overall_pct"] == 1.0
    assert r["bottleneck"] is not None


def test_eval_ci() -> None:
    r = business.eval_ci(8, 10)
    assert r["ci95"][0] < 80 < r["ci95"][1]


def test_retry_reliability() -> None:
    r = business.retry_reliability(0.5, 3)
    assert abs(r["eventual_success_pct"] - 87.5) < 0.1

# -*- coding: utf-8 -*-
"""分析引擎回归：归因闭合、A/B、DiD、弹性、队列。

这些断言不检查文案，只检查数学：
- 归因必须闭合到总变化（误差 <1e-8）；
- A/B 的 z/p/CI 与手算一致；
- DiD 必须能复原合成数据里的已知效应；
- 弹性必须能复原 -1.5；
- 事件研究前趋势系数接近 0。
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core import analysis_lab as L  # noqa: E402


def test_mix_rate_closes_exactly():
    w0 = [0.6, 0.4]
    r0 = [10.0, 20.0]
    w1 = [0.5, 0.5]
    r1 = [11.0, 18.0]
    r = L.decompose_mix_rate(w0, r0, w1, r1, ["A", "B"])
    delta = (w1[0] * r1[0] + w1[1] * r1[1]) - (w0[0] * r0[0] + w0[1] * r0[1])
    assert abs(r["delta"] - delta) < 1e-9
    assert r["diagnostics"]["closure_ok"]
    assert abs(r["rate_effect"] + r["mix_effect"] + r["interaction"] - delta) < 1e-9


def test_ab_proportion_known_result():
    r = L.ab_proportion(5000, 500, 5000, 600)
    assert abs(r["p_a"] - 0.10) < 1e-9 and abs(r["p_b"] - 0.12) < 1e-9
    assert 3.0 < r["z"] < 3.4
    assert r["p_value"] < 0.01
    assert abs(r["rel_lift"] - 0.2) < 1e-9
    lo, hi = r["ci95"]
    assert lo < 0.02 < hi and lo > 0


def test_sample_size_and_mde_are_inverse():
    n = L.sample_size_proportion(0.10, 0.12)
    assert 3000 < n < 5000
    mde = L.mde_proportion(n, 0.10)
    assert 0.015 < mde < 0.025


def test_ab_mean_welch():
    r = L.ab_mean(200, 10.0, 3.0, 200, 11.0, 3.0)
    assert r["p_value"] < 0.01
    assert 3.0 < r["t"] < 4.0
    assert r["level"] == "L3"


def test_bh_correction():
    out = L.bh_correction([0.001, 0.02, 0.5])
    assert out[0]["reject"] and out[1]["reject"] and not out[2]["reject"]
    assert all(0 <= x["q"] <= 1 for x in out)


def _panel(effect=2.0, noise=0.3, seed=7, n_units=60, periods=8, start=4):
    rng = random.Random(seed)
    rows = []
    for u in range(n_units):
        treat = 1 if u < n_units // 2 else 0
        ufe = rng.gauss(0, 1)
        for t in range(periods):
            post = 1 if t >= start else 0
            y = 10 + ufe + 0.5 * t + 1.5 * treat + effect * treat * post + rng.gauss(0, noise)
            rows.append({"unit": u, "period": f"P{t}", "treat": treat, "y": y})
    return rows


def test_did_recovers_known_effect():
    rows = _panel()
    r = L.did_twfe(rows, post_period="P4")
    assert abs(r["estimate"] - 2.0) < 0.35, r
    assert r["p_value"] < 0.01
    assert r["groups"] == 60


def test_event_study_pretrend_is_flat():
    rows = _panel(noise=0.2)
    r = L.event_study(rows, base_period="P0")
    pre = [c for c in r["coefficients"] if c["period"] < "P4"]
    assert all(abs(c["coef"]) < 0.6 for c in pre), pre


def test_placebo_not_significant():
    rows = _panel(effect=0.0, noise=0.5, seed=11)
    r = L.placebo_did(rows, "P2")
    assert r["p_value"] > 0.05, r


def test_elasticity_recovers_minus_1_5():
    prices = [1 + 0.2 * i for i in range(12)]
    qty = [100 * p ** -1.5 for p in prices]
    r = L.elasticity(prices, qty)
    assert abs(r["elasticity"] + 1.5) < 0.01
    assert r["r2"] > 0.999


def test_cohort_retention_weighted_rate():
    cohorts = ["2026-01", "2026-02"]
    periods = [0, 1, 2]
    retained = [[1000, 500, 300], [2000, 1200, 600]]
    r = L.cohort_retention(cohorts, periods, retained)
    # 加权：1/3*0.5 + 2/3*0.6 = 0.5667
    assert abs(r["weighted_rate"][1] - (1 / 3 * 0.5 + 2 / 3 * 0.6) ) < 1e-3
    assert r["decay_slope"] is not None

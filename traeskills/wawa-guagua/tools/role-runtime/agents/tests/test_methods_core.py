# -*- coding: utf-8 -*-
"""可执行方法库测试：匹配差分/DID/弹性/库存/LTV/跑道/利特尔/MMM/RDD/仿真。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.methods import advanced, core  # noqa: E402


def test_matched_diff() -> None:
    r = core.matched_diff([10, 11, 12], [8, 8.5, 9])
    assert abs(r["diff"] - 2.5) < 0.05
    assert r["ci95"][0] <= r["diff"] <= r["ci95"][1]


def test_did() -> None:
    y = [10, 10, 14, 14, 10, 10, 12, 12]
    treat = [1, 1, 1, 1, 0, 0, 0, 0]
    post = [0, 0, 1, 1, 0, 0, 1, 1]
    assert core.did(y, treat, post)["did"] == 2.0


def test_elasticity() -> None:
    r = core.elasticity([1, 2, 4], [100, 50, 25])
    assert abs(r["elasticity"] + 1.0) < 0.01
    assert r["r2"] > 0.99


def test_safety_stock() -> None:
    assert abs(core.safety_stock(2, 9, 1.65)["safety_stock"] - 9.9) < 0.05


def test_ltv_cac() -> None:
    r = core.ltv_cac(60, 0.3, 0.05, 120)
    assert abs(r["ltv"] - 360) < 0.1
    assert abs(r["ltv_cac"] - 3.0) < 0.01
    assert r["verdict"] == "健康"


def test_runway_and_little() -> None:
    assert core.runway(300000, 55000)["runway_months"] == 6
    assert core.littles_law(200, 1.2)["wip"] == 240.0


def test_mmm() -> None:
    ch = [[i, (i * 7) % 11] for i in range(24)]
    y = [100 + 2 * a + 1.5 * b for a, b in ch]
    r = advanced.mmm(ch, y, ["tv", "search"])
    assert abs(r["coef"]["tv"] - 2) < 0.01
    assert abs(r["coef"]["search"] - 1.5) < 0.01
    assert r["r2"] > 0.99


def test_rdd() -> None:
    x = list(range(40, 100))
    y = [50 + 0.5 * v + (2 if v >= 60 else 0) for v in x]
    r = advanced.rdd(y, x, 60, bandwidth=20)
    assert abs(r["estimate"] - 2) < 0.01
    assert r["n_left"] >= 4 and r["n_right"] >= 4


def test_fulfillment() -> None:
    r = advanced.fulfillment_sim(100, 20, 3, 500, days=30, n_sim=200)
    assert 0 <= r["fill_rate"] <= 100
    assert r["avg_inventory"] > 0

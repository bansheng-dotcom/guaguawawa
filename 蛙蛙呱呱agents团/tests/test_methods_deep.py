# -*- coding: utf-8 -*-
"""深度方法测试：PSM/TWFE/带控制弹性/RDD 敏感性/MMM/履约 (s,S)。"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.methods import deep  # noqa: E402


def test_psm_recovers_effect_and_balances() -> None:
    rng = random.Random(11)
    tx, cx, ty, cy = [], [], [], []
    for _ in range(400):
        x1, x2 = rng.gauss(0, 1), rng.gauss(0, 1)
        p = 1 / (1 + math.exp(-(0.8 * x1 + 0.4 * x2)))
        t = rng.random() < p
        y = 2 * t + 1.5 * x1 + 0.5 * x2 + rng.gauss(0, 0.3)
        (tx if t else cx).append([x1, x2])
        (ty if t else cy).append(y)
    r = deep.psm_att(ty, cy, tx, cx)
    assert abs(r["att"] - 2) < 0.2
    assert r["smd_after_max"] < 0.1


def test_twfe_recovers_effect_and_pretrend() -> None:
    rng = random.Random(12)
    y, treat, post, unit, time = [], [], [], [], []
    for u in range(60):
        ufe = rng.gauss(0, 1)
        for p in range(6):
            is_post = 1 if p >= 3 else 0
            is_t = 1 if u < 30 else 0
            y.append(ufe + 0.3 * p + 2 * is_t * is_post + rng.gauss(0, 0.4))
            treat.append(is_t)
            post.append(is_post)
            unit.append(u)
            time.append(p)
    r = deep.twfe_did(y, treat, post, unit, time)
    assert abs(r["att"] - 2) < 0.2
    assert r["pretrend"]["passed"] is True


def test_elasticity_with_controls() -> None:
    rng = random.Random(13)
    price = [1 + 0.2 * i for i in range(40)]
    qty = [100 * p ** -1.5 * math.exp(rng.gauss(0, 0.05)) for p in price]
    r = deep.elasticity_ols(price, qty)
    assert abs(r["elasticity"] + 1.5) < 0.1
    assert r["ci95"][0] < r["elasticity"] < r["ci95"][1]


def test_rdd_sensitivity() -> None:
    x = list(range(0, 101))
    y = [50 + 0.5 * v + (2 if v >= 60 else 0) for v in x]
    r = deep.rdd_sensitivity(y, x, 60)
    assert abs(r["estimate"] - 2) < 0.1
    assert r["p_placebo"] is not None


def test_mmm_deep() -> None:
    rng = random.Random(14)
    n = 60
    ch1 = [max(0, 20 + 10 * math.sin(i / 5) + rng.gauss(0, 3)) for i in range(n)]
    ch2 = [max(0, 15 + 8 * math.cos(i / 7) + rng.gauss(0, 3)) for i in range(n)]
    a1 = deep._hill(deep._adstock(ch1, 0.3), 1.0, 20)
    a2 = deep._hill(deep._adstock(ch2, 0.3), 1.0, 15)
    y = [100 + 120 * a + 90 * b + 0.2 * i for i, (a, b) in enumerate(zip(a1, a2))]
    r = deep.mmm_deep([ch1, ch2], y, ["tv", "search"])
    assert r["r2_train"] > 0.95
    assert r["r2_holdout"] > 0.8


def test_fulfillment_deep() -> None:
    r = deep.fulfillment_deep(30, 6, 3, 0.5, 100, 300, days=60, sims=200)
    assert 0 <= r["fill_rate"] <= 100
    assert 0 <= r["cycle_service_level"] <= 100
    assert r["avg_inventory"] > 0

# -*- coding: utf-8 -*-
"""深度方法测试（进阶）：PSM 反驳、事件研究、置换、交错、FE/IV、预算/CI、RDD 校正、预热。"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.methods import deep  # noqa: E402


def _panel(effect: float = 2.0, units: int = 40, periods: int = 8, adopt: int = 4):
    rng = random.Random(21)
    y, treat, post, unit, time = [], [], [], [], []
    for u in range(units):
        ufe = rng.gauss(0, 1)
        is_t = u < units // 2
        for p in range(periods):
            is_post = 1 if (is_t and p >= adopt) else 0
            y.append(ufe + 0.3 * p + effect * is_post + rng.gauss(0, 0.4))
            treat.append(1 if is_t else 0)
            post.append(is_post)
            unit.append(u)
            time.append(p)
    return y, treat, post, unit, time


def test_psm_refute() -> None:
    rng = random.Random(22)
    tx, cx, ty, cy = [], [], [], []
    for _ in range(200):
        x1, x2 = rng.gauss(0, 1), rng.gauss(0, 1)
        t = rng.random() < 1 / (1 + math.exp(-(0.8 * x1)))
        y = 2 * t + 1.5 * x1 + 0.5 * x2 + rng.gauss(0, 0.3)
        (tx if t else cx).append([x1, x2])
        (ty if t else cy).append(y)
    r = deep.psm_refute(ty, cy, tx, cx)
    assert r["original_att"] > 1.0
    assert r["placebo_att"] is None or abs(r["placebo_att"]) < 1.0


def test_event_study_and_placebo() -> None:
    y, t, p, u, tm = _panel()
    es = deep.event_study(y, t, p, u, tm)
    assert "0" in es["coefficients"]
    assert abs(es["coefficients"]["0"]["coef"] - 2) < 0.6
    pb = deep.did_placebo(y, t, p, u, tm, n_perm=20)
    assert pb["main_att"] > 1.0
    assert pb["p_perm"] is None or 0 <= pb["p_perm"] <= 1


def test_staggered_att() -> None:
    rng = random.Random(23)
    y, treat, post, unit, time = [], [], [], [], []
    for u in range(30):
        adopt = 3 if u < 10 else (5 if u < 20 else None)
        for p in range(8):
            is_t = adopt is not None
            is_post = 1 if (is_t and p >= adopt) else 0
            y.append(rng.gauss(0, 1) + 0.2 * p + 2 * is_post)
            treat.append(1 if is_t else 0)
            post.append(is_post)
            unit.append(u)
            time.append(p)
    r = deep.staggered_att(y, treat, post, unit, time)
    assert abs(r["att"] - 2) < 0.6
    assert r["n_cells"] > 0


def test_elasticity_fe_and_iv() -> None:
    rng = random.Random(24)
    y, price, unit, time, z = [], [], [], [], []
    for u in range(25):
        for p in range(8):
            inst = rng.gauss(0, 1)
            pr = 2 + 0.5 * inst + rng.gauss(0, 0.1)
            q = 100 * pr ** -1.5 * math.exp(rng.gauss(0, 0.05))
            price.append(pr)
            y.append(q)
            unit.append(u)
            time.append(p)
            z.append(inst)
    fe = deep.elasticity_fe(price, y, unit, time)
    assert abs(fe["elasticity"] + 1.5) < 0.2
    iv = deep.elasticity_iv(price, y, z)
    assert abs(iv["elasticity"] + 1.5) < 0.3
    assert iv["first_stage_F"] > 10


def test_mmm_budget_and_ci() -> None:
    rng = random.Random(25)
    n = 60
    ch1 = [max(0, 20 + 10 * math.sin(i / 5) + rng.gauss(0, 3)) for i in range(n)]
    ch2 = [max(0, 15 + 8 * math.cos(i / 7) + rng.gauss(0, 3)) for i in range(n)]
    a1 = deep._hill(deep._adstock(ch1, 0.3), 1.0, 20)
    a2 = deep._hill(deep._adstock(ch2, 0.3), 1.0, 15)
    y = [100 + 120 * a + 90 * b + 0.2 * i for i, (a, b) in enumerate(zip(a1, a2))]
    b = deep.mmm_budget([ch1, ch2], y, ["tv", "search"], total_budget=100)
    assert abs(sum(b["allocation"].values()) - 100) < 1
    ci = deep.mmm_contribution_ci([ch1, ch2], y, ["tv", "search"], n_boot=10)
    assert "tv" in ci["contribution"]


def test_rdd_correction_and_balance() -> None:
    rng = random.Random(26)
    x = list(range(0, 101))
    y = [50 + 0.5 * v + (2 if v >= 60 else 0) + rng.gauss(0, 0.3) for v in x]
    cov = [[rng.gauss(0, 1)] for _ in x]
    r = deep.rdd_sensitivity(y, x, 60, covariates=cov)
    assert abs(r["estimate"] - 2) < 0.4
    assert r["quadratic_estimate"] is not None
    assert r["covariate_balance"]["balanced"] is True


def test_fulfillment_warmup() -> None:
    r = deep.fulfillment_deep(30, 6, 3, 0.5, 100, 300, days=60, sims=100)
    assert r["warmup_days"] > 0
    assert 0 <= r["fill_rate"] <= 100

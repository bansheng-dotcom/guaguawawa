# -*- coding: utf-8 -*-
"""可执行方法库（零依赖）：匹配差分、DID、弹性、安全库存、LTV/CAC、跑道、利特尔法则。

这些是「20 角色深度地图」里点名的方法；以前只有文字，现在有可跑的函数与 CLI。
"""
from __future__ import annotations

import math
import random
import statistics as st
from typing import Sequence


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def matched_diff(treat: Sequence[float], control: Sequence[float],
                 n_boot: int = 2000, seed: int = 42) -> dict:
    """匹配后差分 + 自助法置信区间 + 置换检验 p 值。"""
    if len(treat) < 2 or len(control) < 2:
        raise ValueError("两组各至少 2 个观测")
    obs = _mean(treat) - _mean(control)
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        t = [rng.choice(treat) for _ in treat]
        c = [rng.choice(control) for _ in control]
        boots.append(_mean(t) - _mean(c))
    boots.sort()
    lo, hi = boots[int(n_boot * 0.025)], boots[int(n_boot * 0.975)]
    pool = list(treat) + list(control)
    n = len(treat)
    cnt = 0
    for _ in range(n_boot):
        rng.shuffle(pool)
        if abs(_mean(pool[:n]) - _mean(pool[n:])) >= abs(obs):
            cnt += 1
    return {"diff": round(obs, 4), "ci95": [round(lo, 4), round(hi, 4)],
            "p_perm": round(cnt / n_boot, 4), "n_treat": len(treat), "n_control": len(control)}


def did(y: Sequence[float], treated: Sequence[int], post: Sequence[int]) -> dict:
    """2×2 双重差分：y 为结果，treated/post 为 0/1。"""
    if not (len(y) == len(treated) == len(post)):
        raise ValueError("y/treated/post 长度不一致")
    cells = {}
    for yy, tt, pp in zip(y, treated, post):
        cells.setdefault((tt, pp), []).append(yy)
    for k in ((0, 0), (0, 1), (1, 0), (1, 1)):
        if k not in cells:
            raise ValueError(f"缺单元格 {k}")
    m = {k: _mean(v) for k, v in cells.items()}
    est = (m[(1, 1)] - m[(1, 0)]) - (m[(0, 1)] - m[(0, 0)])
    return {"did": round(est, 4), "treated_change": round(m[(1, 1)] - m[(1, 0)], 4),
            "control_change": round(m[(0, 1)] - m[(0, 0)], 4),
            "cells": {f"{k[0]}{k[1]}": round(v, 4) for k, v in m.items()}}


def elasticity(price: Sequence[float], qty: Sequence[float]) -> dict:
    """log-log OLS：ln(q) = a + b ln(p)，b 即价格弹性。"""
    if len(price) != len(qty) or len(price) < 3:
        raise ValueError("价格与销量等长且至少 3 个点")
    x = [math.log(p) for p in price]
    y = [math.log(q) for q in qty]
    mx, my = _mean(x), _mean(y)
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
    varx = sum((a - mx) ** 2 for a in x)
    vary = sum((b - my) ** 2 for b in y)
    slope = cov / varx if varx else float("nan")
    r2 = (cov * cov) / (varx * vary) if varx and vary else 0.0
    return {"elasticity": round(slope, 4), "r2": round(r2, 4),
            "n": len(price), "note": "弹性 <-1 为富有弹性；仅线性近似"}


def safety_stock(sigma_daily: float, lead_days: float, z: float = 1.65) -> dict:
    """安全库存 = z × σ_d × √LT。"""
    ss = z * sigma_daily * math.sqrt(lead_days)
    return {"safety_stock": round(ss, 3), "z": z, "sigma_daily": sigma_daily, "lead_days": lead_days}


def ltv_cac(arpu: float, gross_margin: float, churn: float, cac: float) -> dict:
    """LTV = ARPU × 毛利率 ÷ 流失率；返回 LTV/CAC 与回收月数。"""
    if churn <= 0 or cac <= 0:
        raise ValueError("churn 与 cac 必须 > 0")
    ltv = arpu * gross_margin / churn
    ratio = ltv / cac
    payback = cac / (arpu * gross_margin)
    return {"ltv": round(ltv, 2), "cac": cac, "ltv_cac": round(ratio, 2),
            "payback_months": round(payback, 1),
            "verdict": "健康" if ratio >= 3 and payback <= 12 else "需改善"}


def runway(cash: float, monthly_burn: float, growth: float = 0.0) -> dict:
    """现金跑道（月）；growth 为净烧钱月增速（0.05 = 每月多烧 5%）。"""
    if monthly_burn <= 0:
        raise ValueError("monthly_burn 必须 > 0")
    months, left = 0, cash
    burn = monthly_burn
    while left > 0 and months < 120:
        left -= burn
        months += 1
        burn *= 1 + growth
    return {"runway_months": months, "cash": cash,
            "monthly_burn": monthly_burn, "growth": growth}


def littles_law(arrival_rate: float, cycle_time: float) -> dict:
    """WIP = 到达率 × 周期；到达率单位：件/天，周期单位：天。"""
    return {"wip": round(arrival_rate * cycle_time, 2),
            "arrival_rate": arrival_rate, "cycle_time": cycle_time,
            "note": "用于验证瓶颈判断，不替代时间戳"}

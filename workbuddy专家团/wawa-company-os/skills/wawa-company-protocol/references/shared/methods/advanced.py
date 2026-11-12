# -*- coding: utf-8 -*-
"""追加：MMM（多元回归）、RDD（断点回归）、履约仿真（蒙特卡洛）。"""
from __future__ import annotations

import math
import random
from typing import Sequence


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """高斯消元（部分主元）。"""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            raise ValueError("矩阵奇异：渠道间可能完全共线")
        m[col], m[piv] = m[piv], m[col]
        for r in range(col + 1, n):
            f = m[r][col] / m[col][col]
            for c in range(col, n + 1):
                m[r][c] -= f * m[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (m[r][n] - sum(m[r][c] * x[c] for c in range(r + 1, n))) / m[r][r]
    return x


def mmm(channels: Sequence[Sequence[float]], y: Sequence[float],
        names: Sequence[str] | None = None) -> dict:
    """营销组合模型（简化 OLS）：y = a + Σ b_j·channel_j。

    返回系数、R²、各渠道贡献占比。样本少时只作方向，不作因果。
    """
    n = len(y)
    if n < len(channels[0]) + 2:
        raise ValueError("样本太少：至少 渠道数+2")
    k = len(channels[0])
    names = list(names or [f"ch{i+1}" for i in range(k)])
    X = [[1.0] + [float(channels[i][j]) for j in range(k)] for i in range(n)]
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k + 1)] for a in range(k + 1)]
    Xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(k + 1)]
    beta = _solve(XtX, Xty)
    fitted = [sum(X[i][j] * beta[j] for j in range(k + 1)) for i in range(n)]
    my = sum(y) / n
    ss_res = sum((y[i] - fitted[i]) ** 2 for i in range(n))
    ss_tot = sum((v - my) ** 2 for v in y) or 1e-12
    r2 = 1 - ss_res / ss_tot
    means = [sum(channels[i][j] for i in range(n)) / n for j in range(k)]
    contrib = [beta[j + 1] * means[j] for j in range(k)]
    pos = sum(max(0, c) for c in contrib) or 1e-12
    return {
        "intercept": round(beta[0], 4),
        "coef": {names[j]: round(beta[j + 1], 4) for j in range(k)},
        "r2": round(r2, 4), "n": n,
        "contribution_pct": {names[j]: round(max(0, contrib[j]) / pos * 100, 1) for j in range(k)},
        "note": "OLS 关联，不等于因果；渠道共线时系数不稳",
    }


def _ols_at(x: Sequence[float], y: Sequence[float]) -> tuple[float, float, float, float]:
    """返回 (截距, 斜率, 截距标准误, 残差标准差)。"""
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((v - mx) ** 2 for v in x)
    if sxx == 0:
        raise ValueError("running 变量无变异")
    slope = sum((x[i] - mx) * (y[i] - my) for i in range(n)) / sxx
    intercept = my - slope * mx
    resid = [y[i] - (intercept + slope * x[i]) for i in range(n)]
    sigma2 = sum(r * r for r in resid) / max(1, n - 2)
    se_int = math.sqrt(sigma2 * (1 / n + mx * mx / sxx))
    return intercept, slope, se_int, math.sqrt(sigma2)


def rdd(y: Sequence[float], running: Sequence[float], cutoff: float,
        bandwidth: float | None = None) -> dict:
    """断点回归（局部线性，左右各拟合一条线，取断点处跳跃）。"""
    if len(y) != len(running) or len(y) < 8:
        raise ValueError("y/running 等长且至少 8 个点")
    span = max(running) - min(running)
    bw = bandwidth or span / 2
    left = [(r, v) for r, v in zip(running, y) if cutoff - bw <= r < cutoff]
    right = [(r, v) for r, v in zip(running, y) if cutoff <= r <= cutoff + bw]
    if len(left) < 4 or len(right) < 4:
        raise ValueError("断点两侧各至少 4 个点（可放宽 bandwidth）")
    xl = [r - cutoff for r, _ in left]
    yl = [v for _, v in left]
    xr = [r - cutoff for r, _ in right]
    yr = [v for _, v in right]
    a_l, b_l, se_l, _ = _ols_at(xl, yl)
    a_r, b_r, se_r, _ = _ols_at(xr, yr)
    est = a_r - a_l
    se = math.sqrt(se_l ** 2 + se_r ** 2) or 1e-12
    return {"estimate": round(est, 4), "se": round(se, 4),
            "t": round(est / se, 2), "bandwidth": round(bw, 3),
            "n_left": len(left), "n_right": len(right),
            "slope_left": round(b_l, 4), "slope_right": round(b_r, 4),
            "note": "局部线性；带宽越小越局部，但样本越少"}


def fulfillment_sim(demand_mean: float, demand_sd: float, lead_time: float,
                    capacity: float, days: int = 30, n_sim: int = 1000,
                    seed: int = 42) -> dict:
    """履约仿真：日需求正态、固定提前期、按预测补货，算履约率与缺货天数。

    假设：每日下单量为 demand_mean（预测值），lead_time 天后到货；初始库存 1.2×均值×LT。
    """
    if demand_mean <= 0 or lead_time <= 0:
        raise ValueError("demand_mean 与 lead_time 必须 > 0")
    rng = random.Random(seed)
    fills, stocks, avgs = [], [], []
    for _ in range(n_sim):
        stock = demand_mean * lead_time * 1.2
        pipeline: list[tuple[int, float]] = []
        served = total = 0.0
        stockout_days = 0
        inv_sum = 0.0
        for d in range(days):
            for arr, qty in list(pipeline):
                if arr == d:
                    stock = min(capacity, stock + qty)
                    pipeline.remove((arr, qty))
            demand = max(0.0, rng.gauss(demand_mean, demand_sd))
            total += demand
            s = min(stock, demand)
            served += s
            stock -= s
            if s < demand:
                stockout_days += 1
            inv_sum += stock
            pipeline.append((d + int(round(lead_time)), demand_mean))
        fills.append(served / total if total else 1.0)
        stocks.append(stockout_days)
        avgs.append(inv_sum / days)
    return {"fill_rate": round(sum(fills) / n_sim * 100, 2),
            "avg_stockout_days": round(sum(stocks) / n_sim, 2),
            "avg_inventory": round(sum(avgs) / n_sim, 2),
            "n_sim": n_sim, "days": days,
            "note": "假设按预测补货；实际有促销/断货时需重跑"}

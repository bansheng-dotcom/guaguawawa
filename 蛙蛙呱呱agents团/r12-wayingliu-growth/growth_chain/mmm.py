# -*- coding: utf-8 -*-
"""第 7 段 · MMM：adstock + 饱和 + ridge（numpy）+ 留出验证 + 贡献 CI。

口径：
- adstock（几何衰减）：a_t = x_t + decay·a_{t-1}；
- 饱和（Hill，α=1）：s = a / (a + K)，K 取训练期正值的均值；
- ridge：特征标准化后闭式解 (XᵀX + λI)⁻¹Xᵀy，截距不惩罚；
- 留出验证：前 70% 拟合、后 30% 计算 R²；
- 贡献 CI：基于训练残差方差与 (XᵀX+λI)⁻¹ 的解析 90% 区间。
门禁：留出 R² ≥ 阈值（留出验证不过即失败）；每渠道贡献与 CI 必须可算。
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np

from . import common as c


CHANNELS = ("tv", "search", "social", "display")


def adstock(values: np.ndarray, decay: float = 0.5) -> np.ndarray:
    """几何 adstock：本期 + decay×上期累积。"""
    out = np.zeros_like(values, dtype=float)
    carry = 0.0
    for i, v in enumerate(values):
        carry = float(v) + decay * carry
        out[i] = carry
    return out


def saturation(values: np.ndarray, k: float) -> np.ndarray:
    """Hill 饱和（α=1）：x/(x+K)，值域 [0,1)。"""
    k = max(k, 1e-9)
    return values / (values + k)


def _design(rows: List[Dict[str, str]], train_n: int,
            decay: float) -> Tuple[np.ndarray, np.ndarray, Dict[str, float]]:
    cols, params = [], {}
    for ch in CHANNELS:
        raw = np.array([c.num(r.get(ch)) or 0.0 for r in rows], dtype=float)
        ad = adstock(raw, decay)
        k = float(np.mean(ad[:train_n][ad[:train_n] > 0])) if train_n else 0.0
        if k <= 0:
            k = float(np.mean(ad[ad > 0])) if np.any(ad > 0) else 1.0
        params[ch] = c.rnd(k, 4)
        cols.append(saturation(ad, k))
    x = np.column_stack(cols) if cols else np.zeros((len(rows), 0))
    y = np.array([c.num(r.get("revenue")) or 0.0 for r in rows], dtype=float)
    return x, y, params


def build(weekly_path: str, decay: float = 0.5,
          ridge_lambda: float = 1.0, holdout_r2_min: float = 0.5,
          train_ratio: float = 0.7) -> Dict[str, Any]:
    """跑 MMM 段并返回带门禁的工件。"""
    rows = c.read_csv_rows(weekly_path)
    n = len(rows)
    train_n = max(4, int(round(n * train_ratio)))
    x, y, params = _design(rows, train_n, decay)

    x_train, y_train = x[:train_n], y[:train_n]
    x_test, y_test = x[train_n:], y[train_n:]

    mu = x_train.mean(axis=0)
    sd = x_train.std(axis=0)
    sd[sd == 0] = 1.0
    xc_train = (x_train - mu) / sd
    xc_all = (x - mu) / sd
    a_train = np.column_stack([np.ones(len(xc_train)), xc_train])
    a_all = np.column_stack([np.ones(len(xc_all)), xc_all])

    penalty = np.eye(a_train.shape[1]) * ridge_lambda
    penalty[0, 0] = 0.0
    xtx = a_train.T @ a_train + penalty
    cov = np.linalg.pinv(xtx)
    beta = cov @ (a_train.T @ y_train)

    pred_train = a_train @ beta
    pred_test = a_all[train_n:] @ beta
    sse = float(np.sum((y_test - pred_test) ** 2))
    sst = float(np.sum((y_test - y_test.mean()) ** 2))
    holdout_r2 = 1 - sse / sst if sst > 0 else 0.0

    pred_all = a_all @ beta
    denom = float(np.sum(pred_all)) or 1.0
    resid = y_train - pred_train
    dof = max(len(y_train) - a_train.shape[1], 1)
    sigma2 = float(np.sum(resid ** 2)) / dof

    contributions = {}
    for idx, ch in enumerate(CHANNELS):
        coef = float(beta[idx + 1])
        amount = coef * float(np.sum(xc_all[:, idx]))
        se = (sigma2 * float(cov[idx + 1, idx + 1])) ** 0.5 * abs(
            float(np.sum(xc_all[:, idx])))
        contributions[ch] = {
            "beta": c.rnd(coef, 6),
            "contribution": c.rnd(amount, 2),
            "share": c.rnd(amount / denom, 6),
            "ci90": [c.rnd(amount - 1.645 * se, 2),
                     c.rnd(amount + 1.645 * se, 2)],
            "adstock_decay": decay,
            "saturation_k": params[ch],
        }
    intercept = float(beta[0])

    checks = [
        c.check("留出验证不过即失败", holdout_r2 >= holdout_r2_min,
                f"holdout_r2={holdout_r2:.4f} min={holdout_r2_min}"),
        c.check("adstock 参数有效", 0 <= decay < 1, f"decay={decay}"),
        c.check("贡献 CI 可算", all(v["ci90"][0] is not None for v in contributions.values()),
                f"channels={len(contributions)}"),
        c.check("训练/留出不重叠", 0 < train_n < n, f"train={train_n} n={n}"),
        c.check("样本量足够", n >= 20 and train_n >= 8, f"n={n}"),
    ]

    return c.stage_artifact("mmm", {
        "weeks": n,
        "train_weeks": train_n,
        "holdout_weeks": n - train_n,
        "holdout_r2": c.rnd(holdout_r2, 6),
        "holdout_r2_min": holdout_r2_min,
        "ridge_lambda": ridge_lambda,
        "intercept": c.rnd(intercept, 4),
        "channels": contributions,
        "fitted_total": c.rnd(denom, 2),
    }, checks)

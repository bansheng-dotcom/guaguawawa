# -*- coding: utf-8 -*-
"""共享统计数学层（纯标准库）。

把「统计量计算」与「阈值判读」分离：数值在这里算，决策阈值读
experience/thresholds.json 的 statistics 段。ttest/chi2/anova/regression/
abtest 等单功能模块都从这里复用，避免每个模块重复实现 Welch/卡方/effect size。

整合自 scipy.stats（Welch t、卡方、ANOVA）+ statsmodels power（效应量分级）+
DoWhy（随机化/SRM 判据），全部用 math/statistics 近似实现。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

from . import _common as c

try:
    from shared import stats_exact  # 精确 p（scipy 可选）
except Exception:  # noqa: BLE001
    stats_exact = None

# 卡方临界值表（alpha=0.05，df=1..10）
CHI2_CRIT = [0, 3.841, 5.991, 7.815, 9.488, 11.070,
             12.592, 14.067, 15.507, 16.919, 18.307]


def stat_thresholds() -> Dict[str, Any]:
    """读取全局统计阈值（含效应量分级），改写阈值不改代码。"""
    return c.load_thresholds().get("statistics", {})


def var(vals: List[float]) -> float:
    """样本方差（无偏，n-1）。"""
    m = sum(vals) / len(vals)
    return sum((v - m) ** 2 for v in vals) / (len(vals) - 1)


def normal_two_sided_p(abs_z: float) -> float:
    """标准正态双尾 p 值，用 math.erf 近似（大 df 适用）。"""
    return math.erfc(abs_z / math.sqrt(2.0))


def effect_grade(x: float, levels: List[float]) -> str:
    """按 |x| 对照 [small, medium, large] 三级阈值分级。"""
    ax = abs(x)
    if ax < levels[0]:
        return "small"
    if ax < levels[1]:
        return "medium"
    if ax < levels[2]:
        return "large"
    return "very_large"


def welch_t(a: List[float], b: List[float], la: str, lb: str) -> Dict[str, Any]:
    """两独立样本 Welch t 检验 + Cohen's d（合并标准差）。"""
    if len(a) < 2 or len(b) < 2:
        return {"group_a": la, "group_b": lb, "error": "样本量不足(<2)"}
    th = stat_thresholds()
    alpha = th.get("alpha", 0.05)
    coh = th.get("cohens_d", {"small": 0.2, "medium": 0.5, "large": 0.8})

    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = var(a) / len(a)
    vb = var(b) / len(b)
    se = math.sqrt(va + vb)
    t = (ma - mb) / se if se > 0 else 0.0
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    p = normal_two_sided_p(abs(t))

    sp = math.sqrt((var(a) + var(b)) / 2)
    d = (ma - mb) / sp if sp else 0.0
    return {"group_a": la, "group_b": lb, "n_a": len(a), "n_b": len(b),
            "mean_a": round(ma, 4), "mean_b": round(mb, 4),
            "diff": round(ma - mb, 4), "t": round(t, 4), "df": round(df, 2),
            "cohens_d": round(d, 4),
            "effect_grade": effect_grade(d, [coh.get("small", 0.2),
                                             coh.get("medium", 0.5),
                                             coh.get("large", 0.8)]),
            "p_value_approx": round(p, 6),
            "p_exact": (stats_exact.ttest_ind(a, b) or {}).get("p") if stats_exact else None,
            "p_method": "exact" if (stats_exact and stats_exact.available()) else "approx",
            "significant": p < alpha, "alpha": alpha,
            "note": "p 值为正态近似（大 df 适用），精确值需 scipy.stats.ttest_ind"}


def eta_squared(ssb: float, sst: float) -> float:
    """ANOVA 效应量 η² = SS_between / SS_total。"""
    return ssb / sst if sst else 0.0


def cramers_v(chi2: float, n: int, r: int, c: int) -> float:
    """卡方效应量 Cramér's V = sqrt(χ² / (n · min(r-1, c-1)))。"""
    denom = n * min(r - 1, c - 1)
    return math.sqrt(chi2 / denom) if denom > 0 else 0.0


def linear_regression(xs: List[float], ys: List[float]) -> Dict[str, Any]:
    """一元 OLS 线性回归：斜率/截距/R²/斜率标准误/t/p/标准化 beta/残差。

    纯标准库实现；不调用 numpy。样本量 < 3 时返回 error。
    """
    n = len(xs)
    if n < 3:
        return {"error": "回归至少需要 3 个观测点"}
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx if sxx else 0.0
    intercept = my - slope * mx

    # SSR / SST / R²
    sse = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    sst = sum((y - my) ** 2 for y in ys)
    r2 = 1 - sse / sst if sst else 0.0
    r = math.sqrt(max(0.0, r2)) * (1 if slope >= 0 else -1)

    # 斜率标准误 + t + p（正态近似）
    dof = n - 2
    mse = sse / dof if dof > 0 else 0.0
    se_slope = math.sqrt(mse / sxx) if sxx else 0.0
    t = slope / se_slope if se_slope else 0.0
    p = normal_two_sided_p(abs(t))

    # 标准化 beta = slope * (sd_x / sd_y)
    sdx = math.sqrt(var(xs))
    sdy = math.sqrt(var(ys))
    beta = slope * (sdx / sdy) if sdy else 0.0

    resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    resid_sd = math.sqrt(sum(v * v for v in resid) / dof) if dof > 0 else 0.0

    th = stat_thresholds()
    r2t = th.get("r2", {"small": 0.02, "medium": 0.13, "large": 0.26})
    return {"n": n, "x_mean": round(mx, 4), "y_mean": round(my, 4),
            "slope": round(slope, 6), "intercept": round(intercept, 6),
            "pearson_r": round(r, 4), "r_squared": round(r2, 4),
            "r2_grade": effect_grade(r2, [r2t.get("small", 0.02),
                                          r2t.get("medium", 0.13),
                                          r2t.get("large", 0.26)]),
            "std_beta": round(beta, 4),
            "slope_se": round(se_slope, 6), "t": round(t, 4), "df": dof,
            "p_value_approx": round(p, 6),
            "p_exact": stats_exact.t_p(t, dof) if stats_exact else None,
            "p_method": "exact" if (stats_exact and stats_exact.available()) else "approx",
            "significant": p < th.get("alpha", 0.05),
            "residual_sd": round(resid_sd, 4),
            "note": "p 值为正态近似；斜率显著 ≠ 因果，需排除混杂"}

def chi2_p_exact(stat: float, df: int):
    return stats_exact.chi2_p(stat, df) if stats_exact else None


def f_p_exact(F: float, dfn: int, dfd: int):
    return stats_exact.f_p(F, dfn, dfd) if stats_exact else None

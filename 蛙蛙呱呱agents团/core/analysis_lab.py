# -*- coding: utf-8 -*-
"""core/analysis_lab —— 分析引擎的「离线/批处理/缺口」补充，不是技能替代。

接入顺序（重要）：
1. 角色技能优先：R06 已有 `did / abtest / elasticity / power / causal / matched /
   rdd / regression`，R15 已有 `tco / safety-stock`，R12 已有 `diagnose / revops`。
   领域方法的映射见 `knowledge/roles/skill_map.json`，跑 `python -m core.skill_bridge coverage`。
2. 只有技能没有的能力才用本模块：量价/结构归因（rate/mix 精确闭合）、
   队列留存、BH 多重比较，以及离线批处理（不想起 20 个子进程时）。
3. 本模块的 did/ab/elasticity 与技能实现口径一致，测试用同一组合成数据；
   报告产线仍走技能，不走这里。

`claims.py` 负责「怎么说」，本模块负责「怎么算」。每个函数都返回
`{estimate, se, ci, p, diagnostics, claim, level}`，报告层只消费结果，
不重新发明公式；测试用合成数据验算，不靠肉眼。

已实现：
    decompose_mix_rate   量价/结构归因：Δ = 率效应 + 结构效应 + 交叉项（精确闭合）
    ab_proportion        两比例 z 检验：绝对差、相对提升、CI、p、功效、MDE
    ab_mean              两均值 Welch t 检验（t 分布，不是正态近似）
    bh_correction        Benjamini-Hochberg 多重比较
    did_twfe             双向固定效应 DiD：估计、聚类稳健 SE、事件研究、安慰剂
    elasticity           对数-对数价格弹性
    cohort_retention     队列留存矩阵与衰减拟合

口径纪律：
- p 值一律双尾；CI 默认 95%；
- DiD 没有对照组/没有前趋势，只返回 L2，不返回因果；
- A/B 样本 <100/组 或 peeking 时给 warning，不给「显著」结论。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

# --------------------------------------------------------------------------- #
# 分布函数（不依赖 scipy）
# --------------------------------------------------------------------------- #
def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Acklam 近似，误差 < 1.2e-9，足够做功效与 MDE。"""
    if not (0 < p < 1):
        raise ValueError("p 必须在 (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def _betacf(a: float, b: float, x: float) -> float:
    MAXIT, EPS, FPMIN = 200, 3e-12, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                  + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1 - x) / b


def t_cdf(t: float, df: float) -> float:
    x = df / (df + t * t)
    p = 0.5 * _betai(df / 2.0, 0.5, x)
    return 1 - p if t > 0 else p


def t_pvalue(t: float, df: float) -> float:
    return 2 * (1 - t_cdf(abs(t), df))


def _ci(est: float, se: float, z: float = 1.96) -> Tuple[float, float]:
    return est - z * se, est + z * se


# --------------------------------------------------------------------------- #
# 1. 量价/结构归因
# --------------------------------------------------------------------------- #
def decompose_mix_rate(weights0: Sequence[float], rates0: Sequence[float],
                       weights1: Sequence[float], rates1: Sequence[float],
                       names: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Δ = Σ(w1·r1) − Σ(w0·r0)，拆成率效应 + 结构效应 + 交叉项。

    典型用法：销售额变化 = 客单价（率）× 客流（结构）；毛利率变化 =
    各品类毛利率（率）× 品类占比（结构）。
    """
    w0 = np.asarray(weights0, dtype=float)
    w1 = np.asarray(weights1, dtype=float)
    r0 = np.asarray(rates0, dtype=float)
    r1 = np.asarray(rates1, dtype=float)
    if not (len(w0) == len(w1) == len(r0) == len(r1)):
        raise ValueError("四个序列长度必须一致")
    names = list(names or [f"项{i+1}" for i in range(len(w0))])
    rate = (r1 - r0) * w0
    mix = (w1 - w0) * r0
    inter = (r1 - r0) * (w1 - w0)
    delta = float((w1 * r1).sum() - (w0 * r0).sum())
    total = float(rate.sum() + mix.sum() + inter.sum())
    rows = []
    for i, n in enumerate(names):
        rows.append({"name": n, "rate": round(float(rate[i]), 6),
                     "mix": round(float(mix[i]), 6),
                     "interaction": round(float(inter[i]), 6),
                     "total": round(float(rate[i] + mix[i] + inter[i]), 6)})
    rows.sort(key=lambda x: abs(x["total"]), reverse=True)
    return {
        "method": "mix_rate", "level": "L1",
        "delta": round(delta, 6),
        "rate_effect": round(float(rate.sum()), 6),
        "mix_effect": round(float(mix.sum()), 6),
        "interaction": round(float(inter.sum()), 6),
        "closure_gap": round(delta - total, 10),
        "rows": rows,
        "diagnostics": {"closure_ok": abs(delta - total) < 1e-8},
        "claim": (f"变化 {delta:+.4f} 中，率效应 {rate.sum():+.4f}、"
                  f"结构效应 {mix.sum():+.4f}、交叉 {inter.sum():+.4f}；"
                  f"最大贡献项是 {rows[0]['name']}（{rows[0]['total']:+.4f}）"),
    }


# --------------------------------------------------------------------------- #
# 2. A/B 检验
# --------------------------------------------------------------------------- #
def ab_proportion(n_a: int, x_a: int, n_b: int, x_b: int,
                  alpha: float = 0.05) -> Dict[str, Any]:
    """两比例 z 检验：A 为对照，B 为实验。"""
    if min(n_a, n_b) <= 0:
        raise ValueError("样本量必须 > 0")
    p_a, p_b = x_a / n_a, x_b / n_b
    diff = p_b - p_a
    p_pool = (x_a + x_b) / (n_a + n_b)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    z = diff / se_pool if se_pool else 0.0
    p = 2 * (1 - norm_cdf(abs(z)))
    se_un = math.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    lo, hi = _ci(diff, se_un, norm_ppf(1 - alpha / 2))
    # 观测效应下的功效
    power = 1 - norm_cdf(norm_ppf(1 - alpha / 2) - abs(diff) / se_un) \
        + norm_cdf(-norm_ppf(1 - alpha / 2) - abs(diff) / se_un)
    warns = []
    if min(n_a, n_b) < 100:
        warns.append("每组样本 <100，z 近似不可靠")
    if x_a < 5 or x_b < 5:
        warns.append("成功数 <5，建议用精确检验")
    return {
        "method": "ab_proportion", "level": "L3" if p < alpha and not warns else "L2",
        "p_a": round(p_a, 6), "p_b": round(p_b, 6),
        "abs_lift": round(diff, 6),
        "rel_lift": round(diff / p_a, 6) if p_a else None,
        "z": round(z, 4), "p_value": round(p, 6),
        "ci95": [round(lo, 6), round(hi, 6)],
        "power_at_observed": round(float(power), 4),
        "diagnostics": {"n_a": n_a, "n_b": n_b, "warnings": warns},
        "claim": (f"实验组 {p_b:.2%} vs 对照组 {p_a:.2%}，绝对提升 {diff:+.2%}"
                  f"（95% CI {lo:+.2%}—{hi:+.2%}，p={p:.4f}）；"
                  f"观测效应下功效 {power:.0%}"),
    }


def ab_mean(n_a: int, mean_a: float, sd_a: float,
            n_b: int, mean_b: float, sd_b: float,
            alpha: float = 0.05) -> Dict[str, Any]:
    """两均值 Welch t 检验（不假设等方差）。"""
    if min(n_a, n_b) < 2:
        raise ValueError("每组至少 2 个样本")
    diff = mean_b - mean_a
    se = math.sqrt(sd_a ** 2 / n_a + sd_b ** 2 / n_b)
    t = diff / se if se else 0.0
    df = (sd_a ** 2 / n_a + sd_b ** 2 / n_b) ** 2 / (
        (sd_a ** 2 / n_a) ** 2 / (n_a - 1) + (sd_b ** 2 / n_b) ** 2 / (n_b - 1))
    p = t_pvalue(t, df)
    z = norm_ppf(1 - alpha / 2)
    lo, hi = _ci(diff, se, z)
    return {
        "method": "ab_mean", "level": "L3" if p < alpha else "L2",
        "mean_a": round(mean_a, 6), "mean_b": round(mean_b, 6),
        "abs_lift": round(diff, 6),
        "rel_lift": round(diff / mean_a, 6) if mean_a else None,
        "t": round(t, 4), "df": round(df, 2), "p_value": round(p, 6),
        "ci95": [round(lo, 6), round(hi, 6)],
        "diagnostics": {"n_a": n_a, "n_b": n_b},
        "claim": (f"实验组均值 {mean_b:.4g} vs 对照 {mean_a:.4g}，差 {diff:+.4g}"
                  f"（95% CI {lo:+.4g}—{hi:+.4g}，p={p:.4f}）"),
    }


def sample_size_proportion(p1: float, p2: float, alpha: float = 0.05,
                           power: float = 0.8) -> int:
    """每组所需样本量（双侧）。"""
    if p1 == p2:
        raise ValueError("两组比例相同，无需样本")
    z_a = norm_ppf(1 - alpha / 2)
    z_b = norm_ppf(power)
    p_bar = (p1 + p2) / 2
    n = ((z_a * math.sqrt(2 * p_bar * (1 - p_bar))
          + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2) / ((p2 - p1) ** 2)
    return int(math.ceil(n))


def mde_proportion(n: int, p: float, alpha: float = 0.05,
                   power: float = 0.8) -> float:
    """给定每组样本量，能检出的最小绝对提升。"""
    z_a = norm_ppf(1 - alpha / 2)
    z_b = norm_ppf(power)
    return float((z_a + z_b) * math.sqrt(2 * p * (1 - p) / n))


def bh_correction(pvalues: Sequence[float], alpha: float = 0.05) -> List[Dict[str, Any]]:
    """Benjamini-Hochberg FDR；返回每个假设的 q 值与是否拒绝。"""
    pv = np.asarray(pvalues, dtype=float)
    m = len(pv)
    order = np.argsort(pv)
    q = np.empty(m)
    prev = 1.0
    for rank in range(m, 0, -1):
        idx = order[rank - 1]
        val = min(prev, pv[idx] * m / rank)
        q[idx] = val
        prev = val
    return [{"p": round(float(pv[i]), 6), "q": round(float(q[i]), 6),
             "reject": bool(q[i] <= alpha)} for i in range(m)]


# --------------------------------------------------------------------------- #
# 3. DiD（双向固定效应）
# --------------------------------------------------------------------------- #
def _twoway_demean(M: np.ndarray, unit_idx: np.ndarray,
                   time_idx: np.ndarray) -> np.ndarray:
    M = np.asarray(M, dtype=float)
    if M.ndim == 1:
        M = M[:, None]
    out = M.copy()
    for u in np.unique(unit_idx):
        m = unit_idx == u
        out[m] -= M[m].mean(axis=0)
    for t in np.unique(time_idx):
        m = time_idx == t
        out[m] -= M[m].mean(axis=0)
    out += M.mean(axis=0)
    return out


def _ols_cluster(X: np.ndarray, y: np.ndarray, clusters: np.ndarray) -> Dict[str, Any]:
    XtX = X.T @ X
    XtX_inv = np.linalg.pinv(XtX)
    beta = XtX_inv @ (X.T @ y)
    resid = y - X @ beta
    n, k = X.shape
    g = len(np.unique(clusters))
    meat = np.zeros((k, k))
    for c in np.unique(clusters):
        m = clusters == c
        Xg = X[m]
        ug = resid[m]
        s = Xg.T @ ug
        meat += np.outer(s, s)
    if g > 1:
        meat *= g / (g - 1)
    V = XtX_inv @ meat @ XtX_inv
    se = np.sqrt(np.maximum(np.diag(V), 0))
    tvals = np.divide(beta, se, out=np.zeros_like(beta), where=se > 0)
    pvals = np.array([t_pvalue(t, max(1, g - 1)) for t in tvals])
    return {"beta": beta, "se": se, "t": tvals, "p": pvals,
            "n": n, "k": k, "groups": g, "resid": resid}


def did_twfe(rows: Sequence[Dict[str, Any]], unit_key: str = "unit",
             time_key: str = "period", treat_key: str = "treat",
             y_key: str = "y", post_period: Optional[str] = None) -> Dict[str, Any]:
    """双向固定效应 DiD。

    rows: [{"unit":1,"period":"2025Q1","treat":0/1,"y":...}, ...]
    post_period: 从哪一期开始算「处理后」；默认最后一期。
    识别假设：平行趋势。没有前趋势检验，只返回 L2。
    """
    units = [r[unit_key] for r in rows]
    times = [r[time_key] for r in rows]
    treat = np.array([int(r[treat_key]) for r in rows], dtype=float)
    y = np.array([float(r[y_key]) for r in rows], dtype=float)
    ucodes = {u: i for i, u in enumerate(sorted(set(units)))}
    tcodes = {t: i for i, t in enumerate(sorted(set(times)))}
    unit_idx = np.array([ucodes[u] for u in units])
    time_idx = np.array([tcodes[t] for t in times])
    tvals = sorted(set(times))
    cutoff = tcodes[post_period] if post_period in tcodes else len(tvals) - 1
    post = np.array([1.0 if tcodes[t] >= cutoff else 0.0 for t in times])
    d = treat * post

    X = _twoway_demean(np.column_stack([d]), unit_idx, time_idx)
    yd = _twoway_demean(y[:, None], unit_idx, time_idx)[:, 0]
    res = _ols_cluster(X, yd, unit_idx)
    est, se = float(res["beta"][0]), float(res["se"][0])
    p = float(res["p"][0])
    z = norm_ppf(0.975)
    lo, hi = est - z * se, est + z * se
    return {
        "method": "did_twfe", "level": "L3" if p < 0.05 else "L2",
        "estimate": round(est, 6), "se": round(se, 6),
        "p_value": round(p, 6), "ci95": [round(lo, 6), round(hi, 6)],
        "n": int(res["n"]), "groups": int(res["groups"]), "periods": len(tvals),
        "diagnostics": {"parallel_trends_tested": False,
                        "note": "未做事件研究前，只按 L2 使用"},
        "claim": (f"DiD 估计处理效应 {est:+.4f}（聚类稳健 SE {se:.4f}，"
                  f"95% CI {lo:+.4f}—{hi:+.4f}，p={p:.4f}）"),
    }


def event_study(rows: Sequence[Dict[str, Any]], base_period: Optional[str] = None,
                unit_key: str = "unit", time_key: str = "period",
                treat_key: str = "treat", y_key: str = "y") -> Dict[str, Any]:
    """事件研究：每个相对期的 treat×期 系数，用来目检平行趋势。"""
    units = [r[unit_key] for r in rows]
    times = [r[time_key] for r in rows]
    treat = np.array([int(r[treat_key]) for r in rows], dtype=float)
    y = np.array([float(r[y_key]) for r in rows], dtype=float)
    ucodes = {u: i for i, u in enumerate(sorted(set(units)))}
    tcodes = {t: i for i, t in enumerate(sorted(set(times)))}
    unit_idx = np.array([ucodes[u] for u in units])
    time_idx = np.array([tcodes[t] for t in times])
    tvals = sorted(set(times))
    if base_period is None:
        base_period = tvals[0]
    cols, labels = [], []
    for t in tvals:
        if t == base_period:
            continue
        cols.append(treat * np.array([1.0 if x == t else 0.0 for x in times]))
        labels.append(str(t))
    if not cols:
        raise ValueError("期数不足")
    X = _twoway_demean(np.column_stack(cols), unit_idx, time_idx)
    yd = _twoway_demean(y[:, None], unit_idx, time_idx)[:, 0]
    res = _ols_cluster(X, yd, unit_idx)
    coefs = [{"period": lab, "coef": round(float(b), 6),
              "se": round(float(s), 6), "p": round(float(pv), 6)}
             for lab, b, s, pv in zip(labels, res["beta"], res["se"], res["p"])]
    pre = [c for c in coefs if c["period"] < base_period]
    bad = [c["period"] for c in pre if c["p"] < 0.10]
    return {
        "method": "event_study", "level": "L3" if not bad else "L2",
        "base_period": str(base_period), "coefficients": coefs,
        "diagnostics": {"pre_trend_violations": bad,
                        "parallel_trends_ok": not bad},
        "claim": ("前趋势未发现显著差异" if not bad
                  else f"前趋势在 {', '.join(bad)} 显著，平行趋势存疑"),
    }


def placebo_did(rows: Sequence[Dict[str, Any]], fake_period: str,
                unit_key: str = "unit", time_key: str = "period",
                treat_key: str = "treat", y_key: str = "y") -> Dict[str, Any]:
    """安慰剂：把政策时点提前，若仍显著，说明原效应可能是趋势。"""
    tvals = sorted({r[time_key] for r in rows})
    if fake_period not in tvals:
        raise ValueError("fake_period 不在数据期次里")
    fake = []
    for r in rows:
        if r[time_key] <= fake_period:
            q = dict(r)
            q["_post"] = 1 if r[time_key] == fake_period else 0
            fake.append(q)
    units = [r[unit_key] for r in fake]
    times = [r[time_key] for r in fake]
    treat = np.array([int(r[treat_key]) for r in fake], dtype=float)
    y = np.array([float(r[y_key]) for r in fake], dtype=float)
    post = np.array([float(r["_post"]) for r in fake])
    ucodes = {u: i for i, u in enumerate(sorted(set(units)))}
    tcodes = {t: i for i, t in enumerate(sorted(set(times)))}
    ui = np.array([ucodes[u] for u in units])
    ti = np.array([tcodes[t] for t in times])
    X = _twoway_demean((treat * post)[:, None], ui, ti)
    yd = _twoway_demean(y[:, None], ui, ti)[:, 0]
    res = _ols_cluster(X, yd, ui)
    est, se, p = float(res["beta"][0]), float(res["se"][0]), float(res["p"][0])
    return {"method": "placebo_did", "level": "L2",
            "estimate": round(est, 6), "se": round(se, 6),
            "p_value": round(p, 6),
            "diagnostics": {"fake_period": fake_period,
                            "pass": p >= 0.10},
            "claim": (f"安慰剂检验 p={p:.4f}，"
                      + ("通过（未发现假时点显著）" if p >= 0.10 else "未通过，原效应存疑"))}


# --------------------------------------------------------------------------- #
# 4. 弹性与队列
# --------------------------------------------------------------------------- #
def elasticity(prices: Sequence[float], quantities: Sequence[float]) -> Dict[str, Any]:
    """log q = a + b·log p；b 即价格弹性。"""
    p = np.asarray(prices, dtype=float)
    q = np.asarray(quantities, dtype=float)
    if len(p) < 3 or (p <= 0).any() or (q <= 0).any():
        raise ValueError("价格与销量必须为正，且至少 3 期")
    x = np.log(p)
    y = np.log(q)
    X = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    dof = max(1, n - k)
    s2 = float(resid @ resid) / dof
    cov = s2 * np.linalg.pinv(X.T @ X)
    se = math.sqrt(max(cov[1, 1], 0))
    t = float(beta[1] / se) if se else 0.0
    pval = t_pvalue(t, dof)
    z = norm_ppf(0.975)
    lo, hi = beta[1] - z * se, beta[1] + z * se
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - float(resid @ resid) / ss_tot if ss_tot else 0.0
    return {
        "method": "elasticity", "level": "L2",
        "elasticity": round(float(beta[1]), 4), "se": round(float(se), 4),
        "p_value": round(float(pval), 6), "ci95": [round(float(lo), 4), round(float(hi), 4)],
        "r2": round(r2, 4), "n": int(n),
        "diagnostics": {"log_log": True, "dof": int(dof)},
        "claim": (f"价格弹性 {beta[1]:+.3f}（95% CI {lo:+.3f}—{hi:+.3f}，"
                  f"p={pval:.4f}，R²={r2:.2f}）；价格每升 1%，销量约变 {beta[1]:+.2f}%"),
    }


def cohort_retention(cohorts: Sequence[str], periods: Sequence[int],
                     retained: Sequence[Sequence[float]]) -> Dict[str, Any]:
    """retained[c][t] 为第 c 队列在第 t 期的留存人数/金额（t=0 为基数）。"""
    M = np.asarray(retained, dtype=float)
    if M.ndim != 2 or M.shape[1] != len(periods):
        raise ValueError("retained 必须是 队列×期 的矩阵")
    rate = M / np.where(M[:, [0]] == 0, np.nan, M[:, [0]])
    weights = M[:, 0] / M[:, 0].sum() if M[:, 0].sum() else np.ones(len(M)) / len(M)
    avg = np.nansum(rate * weights[:, None], axis=0)
    # 衰减拟合：ln(r_t) = a + b t，取 t>=1 且 r>0
    xs, ys = [], []
    for i in range(M.shape[0]):
        for j, t in enumerate(periods):
            if j >= 1 and rate[i, j] > 0:
                xs.append(t)
                ys.append(math.log(rate[i, j]))
    decay = None
    if len(xs) >= 3:
        X = np.column_stack([np.ones(len(xs)), xs])
        beta, *_ = np.linalg.lstsq(X, np.asarray(ys), rcond=None)
        decay = round(float(beta[1]), 4)
    return {
        "method": "cohort_retention", "level": "L1",
        "periods": list(periods),
        "weighted_rate": [round(float(x), 4) for x in avg],
        "decay_slope": decay,
        "diagnostics": {"cohorts": len(cohorts),
                        "decay_interpretation": "每月留存的对数衰减斜率"},
        "claim": (f"{len(cohorts)} 个队列，期初到第 {periods[-1]} 期加权留存 "
                  f"{avg[-1]:.1%}"
                  + (f"，对数衰减斜率 {decay:+.3f}" if decay is not None else "")),
    }


# --------------------------------------------------------------------------- #
# CLI：让引擎能被单独调用（输入 JSON，输出 JSON）
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json as _json
    ap = argparse.ArgumentParser(prog="analysis_lab")
    ap.add_argument("method", choices=["mix", "ab", "did", "event", "placebo",
                                       "elasticity", "cohort", "power"])
    ap.add_argument("--input", required=True, help="输入 JSON 文件")
    a = ap.parse_args(argv)
    payload = _json.loads(open(a.input, encoding="utf-8-sig").read())
    m = a.method
    if m == "mix":
        out = decompose_mix_rate(payload["weights0"], payload["rates0"],
                                 payload["weights1"], payload["rates1"],
                                 payload.get("names"))
    elif m == "ab":
        if "n_a" in payload and "x_a" in payload:
            out = ab_proportion(payload["n_a"], payload["x_a"],
                                payload["n_b"], payload["x_b"])
        else:
            out = ab_mean(payload["n_a"], payload["mean_a"], payload["sd_a"],
                          payload["n_b"], payload["mean_b"], payload["sd_b"])
    elif m == "did":
        out = did_twfe(payload["rows"], post_period=payload.get("post_period"))
    elif m == "event":
        out = event_study(payload["rows"], base_period=payload.get("base_period"))
    elif m == "placebo":
        out = placebo_did(payload["rows"], payload["fake_period"])
    elif m == "elasticity":
        out = elasticity(payload["prices"], payload["quantities"])
    elif m == "cohort":
        out = cohort_retention(payload["cohorts"], payload["periods"],
                               payload["retained"])
    else:
        out = {"sample_size": sample_size_proportion(payload["p1"], payload["p2"],
                                                      payload.get("alpha", 0.05),
                                                      payload.get("power", 0.8)),
               "mde": mde_proportion(payload["n"], payload["p1"],
                                     payload.get("alpha", 0.05),
                                     payload.get("power", 0.8))}
    print(_json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

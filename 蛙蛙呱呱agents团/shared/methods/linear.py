# -*- coding: utf-8 -*-
"""多元 OLS / Logit + 稳健/聚类标准误（numpy 实现，statsmodels 仅用于对照测试）。

设计：不引入 statsmodels 运行时依赖；numpy 可用即可。系数与 SE 与
statsmodels 的 HC1 / cluster 口径一致，供 R06 从"一元相关"走向"控混杂"。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

try:
    import numpy as np

    HAS_NUMPY = True
except Exception:  # noqa: BLE001
    np = None
    HAS_NUMPY = False

try:
    from shared import stats_exact
except Exception:  # noqa: BLE001
    stats_exact = None


def _num(v: Any) -> Optional[float]:
    try:
        if str(v).strip() == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def design_matrix(rows: Sequence[Dict[str, Any]], xs: Sequence[str],
                  categorical: Sequence[str] = ()) -> Dict[str, Any]:
    """构造设计矩阵：截距 + 连续变量 + 类别哑变量（drop first）。"""
    if not HAS_NUMPY:
        raise RuntimeError("numpy 不可用：多元回归需要 numpy")
    names: List[str] = ["const"]
    data: List[List[float]] = []
    cats: Dict[str, List[str]] = {}
    for c in categorical:
        vals = sorted({str(r.get(c, "")) for r in rows})
        cats[c] = vals[1:]  # drop first 作为基准
        names += [f"{c}={v}" for v in cats[c]]
    kept_rows = []
    for r in rows:
        vec = [1.0]
        ok = True
        for c in xs:
            v = _num(r.get(c))
            if v is None:
                ok = False
                break
            vec.append(v)
        if not ok:
            continue
        for c in categorical:
            base = sorted({str(x.get(c, "")) for x in rows})[0]
            for v in cats[c]:
                vec.append(1.0 if str(r.get(c, "")) == v else 0.0)
            if str(r.get(c, "")) == base:
                pass
        kept_rows.append(r)
        data.append(vec)
    names = ["const"] + list(xs) + [f"{c}={v}" for c in categorical for v in cats[c]]
    return {"X": np.asarray(data, dtype=float), "names": names,
            "rows": kept_rows, "categorical_levels": cats}


def _ols_cov(X, resid, se: str, cluster: Optional[Sequence[Any]]):
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    if se == "classic":
        sigma2 = float(resid @ resid) / max(n - k, 1)
        return sigma2 * XtX_inv
    if cluster is not None:
        meat = np.zeros((k, k))
        groups: Dict[Any, List[int]] = {}
        for i, g in enumerate(cluster):
            groups.setdefault(g, []).append(i)
        for idx in groups.values():
            Xg = X[idx]
            eg = resid[idx]
            s = Xg.T @ eg
            meat += np.outer(s, s)
        return XtX_inv @ meat @ XtX_inv
    # HC1
    meat = (X * (resid ** 2)[:, None]).T @ X
    scale = n / max(n - k, 1)
    return scale * (XtX_inv @ meat @ XtX_inv)


def fit_ols(y: Sequence[float], X, names: Sequence[str],
            cluster: Optional[Sequence[Any]] = None, se: str = "HC1") -> Dict[str, Any]:
    if not HAS_NUMPY:
        raise RuntimeError("numpy 不可用")
    yv = np.asarray(y, dtype=float)
    n, k = X.shape
    if n <= k:
        raise ValueError(f"样本量不足：n={n} <= k={k}")
    beta, *_ = np.linalg.lstsq(X, yv, rcond=None)
    fitted = X @ beta
    resid = yv - fitted
    sst = float(((yv - yv.mean()) ** 2).sum())
    sse = float((resid ** 2).sum())
    r2 = 1 - sse / sst if sst else 0.0
    adj = 1 - (1 - r2) * (n - 1) / max(n - k, 1)

    cov = _ols_cov(X, resid, se, cluster)
    se_vec = np.sqrt(np.maximum(np.diag(cov), 0.0))
    t_vec = beta / np.where(se_vec == 0, np.nan, se_vec)
    coefs = []
    for i, nm in enumerate(names):
        p = stats_exact.t_p(float(t_vec[i]), n - k) if stats_exact else None
        coefs.append({"name": nm, "est": round(float(beta[i]), 8),
                      "se": round(float(se_vec[i]), 8),
                      "t": round(float(t_vec[i]), 4) if not math.isnan(float(t_vec[i])) else None,
                      "p": round(p, 8) if p is not None else None,
                      "ci95": [round(float(beta[i] - 1.96 * se_vec[i]), 8),
                               round(float(beta[i] + 1.96 * se_vec[i]), 8)]})

    # VIF：x_j ~ 其余变量
    vif = {}
    for j in range(1, k):
        Xo = np.delete(X, j, axis=1)
        b, *_ = np.linalg.lstsq(Xo, X[:, j], rcond=None)
        e = X[:, j] - Xo @ b
        sst_j = float(((X[:, j] - X[:, j].mean()) ** 2).sum())
        r2j = 1 - float(e @ e) / sst_j if sst_j else 0.0
        vif[names[j]] = None if r2j >= 0.999 else round(1 / (1 - r2j), 3)

    warnings = []
    if any(v is not None and v > 10 for v in vif.values()):
        warnings.append("存在 VIF>10 的共线变量，系数不稳定")
    try:
        Z = X[:, 1:]
        Z = (Z - Z.mean(axis=0)) / np.where(Z.std(axis=0) == 0, 1, Z.std(axis=0))
        cond = float(np.linalg.cond(np.column_stack([np.ones(n), Z])))
        if cond > 30:
            warnings.append(f"标准化设计矩阵条件数 {cond:.1f} > 30，可能共线")
    except Exception:  # noqa: BLE001
        cond = None

    # F 检验（整体显著性）
    k_ = k - 1
    f_stat = (r2 / k_) / ((1 - r2) / max(n - k, 1)) if k_ and r2 < 1 else None
    f_p = stats_exact.f_p(f_stat, k_, n - k) if (stats_exact and f_stat) else None

    return {"model": "ols", "n": n, "k": k_,
            "coef": coefs, "r2": round(r2, 6), "adj_r2": round(adj, 6),
            "f_stat": round(f_stat, 4) if f_stat is not None else None,
            "f_p": f_p, "vif": vif, "condition_number": round(cond, 2) if cond else None,
            "se_method": "cluster" if cluster is not None else se,
            "warnings": warnings}


def fit_logit(y: Sequence[int], X, names: Sequence[str],
              cluster: Optional[Sequence[Any]] = None, max_iter: int = 100) -> Dict[str, Any]:
    if not HAS_NUMPY:
        raise RuntimeError("numpy 不可用")
    yv = np.asarray(y, dtype=float)
    n, k = X.shape
    beta = np.zeros(k)
    for _ in range(max_iter):
        eta = X @ beta
        mu = 1 / (1 + np.exp(-np.clip(eta, -30, 30)))
        W = np.clip(mu * (1 - mu), 1e-8, None)
        grad = X.T @ (yv - mu)
        H = X.T @ (X * W[:, None])
        step = np.linalg.pinv(H) @ grad
        beta = beta + step
        if np.max(np.abs(step)) < 1e-8:
            break
    eta = X @ beta
    mu = 1 / (1 + np.exp(-np.clip(eta, -30, 30)))
    W = np.clip(mu * (1 - mu), 1e-8, None)
    H = X.T @ (X * W[:, None])
    Hinv = np.linalg.pinv(H)
    if cluster is not None:
        meat = np.zeros((k, k))
        groups = {}
        for i, g in enumerate(cluster):
            groups.setdefault(g, []).append(i)
        for idx in groups.values():
            Xg = X[idx]
            eg = (yv - mu)[idx]
            sc = Xg.T @ eg
            meat += np.outer(sc, sc)
        cov = Hinv @ meat @ Hinv
    else:
        cov = Hinv
    se_vec = np.sqrt(np.maximum(np.diag(cov), 0.0))

    ll = float(np.sum(yv * np.log(np.clip(mu, 1e-12, 1)) +
                      (1 - yv) * np.log(np.clip(1 - mu, 1e-12, 1))))
    p0 = float(np.clip(yv.mean(), 1e-6, 1 - 1e-6))
    ll0 = float(n * (p0 * math.log(p0) + (1 - p0) * math.log(1 - p0)))
    pseudo_r2 = 1 - ll / ll0 if ll0 else 0.0

    # AUC（简单秩和）
    pos = mu[yv == 1]
    neg = mu[yv == 0]
    auc = None
    if len(pos) and len(neg):
        auc = float(np.mean([[1.0 if a > b else 0.5 if a == b else 0.0 for b in neg] for a in pos]))

    coefs = []
    for i, nm in enumerate(names):
        z = float(beta[i] / se_vec[i]) if se_vec[i] else float("nan")
        p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2)))) if not math.isnan(z) else None
        coefs.append({"name": nm, "est": round(float(beta[i]), 6),
                      "se": round(float(se_vec[i]), 6),
                      "z": round(z, 4) if not math.isnan(z) else None,
                      "p": round(p, 8) if p is not None else None,
                      "odds_ratio": round(float(math.exp(beta[i])), 4)})
    return {"model": "logit", "n": n, "k": k - 1, "coef": coefs,
            "pseudo_r2": round(pseudo_r2, 6), "auc": round(auc, 4) if auc is not None else None,
            "log_likelihood": round(ll, 4), "warnings": []}

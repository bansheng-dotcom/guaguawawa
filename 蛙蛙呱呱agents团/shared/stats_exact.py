# -*- coding: utf-8 -*-
"""精确 p 值与多重比较校正（scipy 可选，不可用则返回 None 由调用方回退）。

设计原则：
- 只做"包装"，不重写统计公式；scipy 可用就用精确分布。
- scipy 不可用时**不抛错**，返回 None，调用方保留 `p_value_approx` 并标 `approx`。
- BH 校正与 scipy 无关，纯标准库实现。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

try:  # scipy 是可选重型后端
    from scipy import stats as _st  # type: ignore

    AVAILABLE = True
except Exception:  # noqa: BLE001
    _st = None
    AVAILABLE = False


def available() -> bool:
    return AVAILABLE


def ttest_ind(a: Sequence[float], b: Sequence[float]) -> Optional[Dict[str, float]]:
    """Welch t 检验（不等方差），返回 t / p / df。"""
    if not AVAILABLE or len(a) < 2 or len(b) < 2:
        return None
    r = _st.ttest_ind(a, b, equal_var=False)
    return {"t": float(r.statistic), "p": float(r.pvalue),
            "df": float(getattr(r, "df", float("nan")))}


def t_p(t: float, df: float) -> Optional[float]:
    """双侧 t 分布 p 值。"""
    if not AVAILABLE or df is None or df <= 0:
        return None
    return float(2 * _st.t.sf(abs(t), df))


def chi2_p(stat: float, df: int) -> Optional[float]:
    if not AVAILABLE or df <= 0:
        return None
    return float(_st.chi2.sf(stat, df))


def f_p(F: float, dfn: int, dfd: int) -> Optional[float]:
    if not AVAILABLE or dfn <= 0 or dfd <= 0:
        return None
    return float(_st.f.sf(F, dfn, dfd))


def f_oneway(groups: Sequence[Sequence[float]]) -> Optional[Dict[str, float]]:
    if not AVAILABLE or len(groups) < 2:
        return None
    r = _st.f_oneway(*[list(g) for g in groups])
    return {"F": float(r.statistic), "p": float(r.pvalue)}


def bh_adjust(pvals: Sequence[float], alpha: float = 0.05) -> Dict[str, List]:
    """Benjamini–Hochberg step-up。返回 p_adj / reject / alpha / m。

    单调化：p_adj(i) = min_{k>=i} (m/k * p_(k))，保证排序后不反转。
    """
    m = len(pvals)
    if m == 0:
        return {"p_adj": [], "reject": [], "alpha": alpha, "m": 0}
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [1.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        idx = order[rank - 1]
        val = pvals[idx] * m / rank
        prev = min(prev, val)
        adj[idx] = min(1.0, prev)
    reject = [adj[i] <= alpha for i in range(m)]
    return {"p_adj": [round(x, 6) for x in adj], "reject": reject,
            "alpha": alpha, "m": m}

# -*- coding: utf-8 -*-
"""S05h A/B 设计功效计算 —— 能力域 5（统计域 · 拆细之八）。

从 s05_statistics 拆出，整合自 statsmodels.stats.power（NormalIndPower 的比例检验口径）。
单功能：给定基线率与最小可检测提升（MDE），算「每个分组所需样本量」与「达成功效」；
或给定样本量反解 MDE。纯标准库（erf 有理逼近 + 二分求逆），确定性可复算。

能力域表「A/B 设计和功效说明」的执行落点：先算样本量再开实验，而不是事后补检验。
"""
from __future__ import annotations

import argparse  # noqa: F401
from typing import Any, Dict

from . import _common as c


NAME = "power"
DESC = "A/B 设计功效：样本量/MDE/达成功效（能力域5拆细）"


def _norm_cdf(z: float) -> float:
    """标准正态 CDF（Abramowitz-Stegun 7.1.26 有理逼近，|ε|<7.5e-8）。"""
    import math
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    d = 0.3989422804014327 * math.exp(-z * z / 2.0)
    p = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 +
         t * (-1.821255978 + t * 1.330274429))))
    return 1.0 - p if z > 0 else p


def _norm_ppf(p: float) -> float:
    """正态分位数：[1e-9, 1-1e-9] 内二分求逆（确定性）。"""
    if not (1e-9 < p < 1 - 1e-9):
        raise ValueError(f"概率越界: {p}")
    lo, hi = -8.0, 8.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if _norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--baseline", type=float, required=True,
                   help="基线率（如转化率 0.05）或基线均值")
    p.add_argument("--mde", type=float, default=None,
                   help="最小可检测提升（绝对量）；与 --n-per-group 至少给一个")
    p.add_argument("--n-per-group", type=int, default=None,
                   help="每组已有样本量；给定时反解 MDE")
    p.add_argument("--alpha", type=float, default=0.05, help="双侧显著性水平")
    p.add_argument("--power", type=float, default=0.80, help="目标功效（1−β）")
    p.add_argument("--sigma", type=float, default=None,
                   help="均值类指标的组内标准差；给定时按均值口径计算")


def _n_proportion(p1: float, p2: float, alpha: float, power: float) -> float:
    """双比例 z 检验正态近似的每组样本量。"""
    import math
    z_a = _norm_ppf(1 - alpha / 2)
    z_b = _norm_ppf(power)
    pbar = (p1 + p2) / 2
    num = (z_a * math.sqrt(2 * pbar * (1 - pbar)) +
           z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return num / (p2 - p1) ** 2


def _power_proportion(p1: float, p2: float, n: int, alpha: float) -> float:
    """给定样本量与真实差，算功效（正态近似）。"""
    import math
    z_a = _norm_ppf(1 - alpha / 2)
    se = math.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / n)
    return _norm_cdf(abs(p2 - p1) / se - z_a)


def run(args) -> Dict[str, Any]:
    if args.baseline is None:
        return {"error": "缺 --baseline"}
    p1 = float(args.baseline)
    if args.mde is None and args.n_per_group is None:
        return {"error": "需给 --mde（算样本量）或 --n-per-group（反解 MDE）之一"}
    if args.mde is not None:
        if p1 + args.mde >= 1 or p1 + args.mde <= 0:
            return {"error": f"基线 {p1} + MDE {args.mde} 越出 (0,1) 比例区间"}
        n_raw = _n_proportion(p1, p1 + args.mde, args.alpha, args.power)
        n = int(n_raw) + 1
        achieved = _power_proportion(p1, p1 + args.mde, n, args.alpha)
        return {
            "power": {
                "mode": "proportion",
                "baseline": p1, "mde": args.mde,
                "expected_rate_treatment": round(p1 + args.mde, 6),
                "alpha": args.alpha, "target_power": args.power,
                "required_n_per_group": n,
                "required_n_total": 2 * n,
                "achieved_power_at_n": round(achieved, 4),
                "formula": "双比例 z 检验正态近似（statsmodels NormalIndPower 同口径）",
                "note": f"每组至少 {n} 个样本才能以 {args.power:.0%} 功效检出 "
                        f"{args.mde:.4f} 的绝对提升；低于该样本量的实验只能给出方向，"
                        f"不能承诺检验结论。"},
        }
    # 反解 MDE：在给定样本量下，目标功效能检出的最小绝对提升
    n = int(args.n_per_group)
    import math
    lo, hi = 1e-6, 1 - p1 - 1e-6
    if hi <= 0:
        return {"error": "基线率过高，无提升空间"}
    for _ in range(60):
        mid = (lo + hi) / 2
        if _power_proportion(p1, p1 + mid, n, args.alpha) < args.power:
            lo = mid
        else:
            hi = mid
    mde = (lo + hi) / 2
    return {
        "power": {
            "mode": "proportion",
            "baseline": p1, "n_per_group": n,
            "alpha": args.alpha, "target_power": args.power,
            "mde_solvable": round(mde, 6),
            "note": f"每组 {n} 个样本在 {args.power:.0%} 功效下，最小可检测绝对提升为 "
                    f"{mde:.4f}（相对提升 {mde / p1:.1%}）；小于该量级的效果 "
                    f"即使真实存在也大概率检不出来。"},
    }

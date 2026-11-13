# -*- coding: utf-8 -*-
"""业务定量技能：决策期望值、排队、TAM 蒙特卡洛、RICE、数据画像、SLO 预算。

这些不是统计推断，而是经营决策常用的「可算 + 可敏感性 + 可解释」模型。
"""
from __future__ import annotations

import math
import random
from typing import Sequence


def expected_value(options: Sequence[dict]) -> dict:
    """决策期望值：EV = p*good + (1-p)*bad - cost；附盈亏平衡 p 与敏感性。"""
    rows = []
    for o in options:
        p = float(o["p"])
        ev = p * float(o["good"]) + (1 - p) * float(o["bad"]) - float(o.get("cost", 0))
        rows.append({"name": o["name"], "ev": round(ev, 2), "p": p})
    rows.sort(key=lambda r: r["ev"], reverse=True)
    best = rows[0]
    # 与第二名的盈亏平衡概率（只变 best 的 p）
    breakeven = None
    if len(rows) > 1:
        second = rows[1]["ev"]
        o = next(x for x in options if x["name"] == best["name"])
        good, bad = float(o["good"]), float(o["bad"])
        if good != bad:
            breakeven = (second + float(o.get("cost", 0)) - bad) / (good - bad)
    sens = []
    for d in (-0.1, 0.1):
        p = min(1.0, max(0.0, best["p"] + d))
        o = next(x for x in options if x["name"] == best["name"])
        ev = p * float(o["good"]) + (1 - p) * float(o["bad"]) - float(o.get("cost", 0))
        sens.append({"delta_p": d, "ev": round(ev, 2)})
    return {"ranking": rows, "best": best["name"],
            "breakeven_p_vs_second": round(breakeven, 4) if breakeven is not None else None,
            "sensitivity": sens,
            "note": "EV 只对给定概率成立；p 来自判断时需标注来源"}


def queue_wait(arrivals_per_day: float, service_per_day: float,
               cv_arrival: float = 1.0, cv_service: float = 1.0) -> dict:
    """Kingman 近似：Wq ≈ (cv_a²+cv_s²)/2 × ρ/(1-ρ) × (1/μ)。"""
    if service_per_day <= arrivals_per_day:
        raise ValueError("服务能力必须大于到达率，否则队列无界")
    rho = arrivals_per_day / service_per_day
    wq = (cv_arrival ** 2 + cv_service ** 2) / 2 * rho / (1 - rho) / service_per_day
    w = wq + 1 / service_per_day
    return {"utilization": round(rho, 3), "wait_days": round(wq, 3),
            "cycle_days": round(w, 3), "wip": round(arrivals_per_day * w, 1),
            "note": "Kingman 近似；高利用率时对变异敏感"}


def tam_mc(population: float, pen_low: float, pen_high: float,
           arpu_low: float, arpu_high: float, n: int = 10000, seed: int = 42) -> dict:
    """TAM 蒙特卡洛：渗透率 × ARPU 三角分布，输出分位与达标概率。"""
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        pen = rng.triangular(pen_low, pen_high, (pen_low + pen_high) / 2)
        arpu = rng.triangular(arpu_low, arpu_high, (arpu_low + arpu_high) / 2)
        vals.append(population * pen * arpu)
    vals.sort()
    mean = sum(vals) / n
    return {"mean": round(mean, 1), "p10": round(vals[int(n * 0.1)], 1),
            "p50": round(vals[int(n * 0.5)], 1), "p90": round(vals[int(n * 0.9)], 1),
            "n": n, "note": "三角分布假设；区间来自判断，不能替代抽样"}


def rice(items: Sequence[dict]) -> dict:
    """RICE 排序：Reach×Impact×Confidence/Effort；附 confidence 敏感性。"""
    rows = []
    for it in items:
        score = (float(it["reach"]) * float(it["impact"]) * float(it["confidence"])
                 / max(1e-9, float(it["effort"])))
        rows.append({"name": it["name"], "score": round(score, 2),
                     "confidence": float(it["confidence"])})
    rows.sort(key=lambda r: r["score"], reverse=True)
    sens = []
    for d in (-0.1, 0.1):
        tmp = []
        for it in items:
            conf = min(1.0, max(0.0, float(it["confidence"]) + d))
            tmp.append({"name": it["name"],
                        "score": round(float(it["reach"]) * float(it["impact"]) * conf
                                       / max(1e-9, float(it["effort"])), 2)})
        tmp.sort(key=lambda r: r["score"], reverse=True)
        sens.append({"delta_confidence": d, "top": [x["name"] for x in tmp[:3]]})
    return {"ranking": rows, "sensitivity": sens,
            "note": "RICE 是排序工具，不是价值证明；confidence 需有依据"}


def _psi(expected: Sequence[float], actual: Sequence[float], bins: int = 10) -> float:
    if not expected:
        return 0.0
    lo, hi = min(expected), max(expected)
    if hi == lo:
        return 0.0
    edges = [lo + (hi - lo) * i / bins for i in range(bins + 1)]
    e = [0] * bins
    a = [0] * bins
    for v in expected:
        i = min(bins - 1, max(0, int((v - lo) / (hi - lo) * bins)))
        e[i] += 1
    for v in actual:
        if lo <= v <= hi:
            i = min(bins - 1, max(0, int((v - lo) / (hi - lo) * bins)))
            a[i] += 1
    total_e, total_a = max(1, len(expected)), max(1, len(actual))
    psi = 0.0
    for i in range(bins):
        pe, pa = e[i] / total_e, a[i] / total_a
        if pe > 0 and pa > 0:
            psi += (pa - pe) * math.log(pa / pe)
    return psi


def data_profile(rows: Sequence[dict], columns: Sequence[str],
                 time_col: str | None = None) -> dict:
    """数据画像：缺失率、基数、重复行、数值分布；按时间切半分 PSI。"""
    n = len(rows)
    out = {"rows": n, "duplicate_rows": n - len({tuple(sorted(r.items())) for r in rows}),
           "columns": {}}
    for c in columns:
        vals = [r.get(c) for r in rows]
        miss = sum(1 for v in vals if v in (None, ""))
        nonnull = [v for v in vals if v not in (None, "")]
        out["columns"][c] = {"missing_pct": round(miss / max(1, n) * 100, 2),
                             "distinct": len(set(map(str, nonnull)))}
    if time_col and n >= 4:
        ordered = sorted(rows, key=lambda r: str(r.get(time_col, "")))
        half = n // 2
        for c in columns:
            try:
                a = [float(r[c]) for r in ordered[:half] if r.get(c) not in (None, "")]
                b = [float(r[c]) for r in ordered[half:] if r.get(c) not in (None, "")]
            except (ValueError, TypeError):
                continue
            if a and b:
                out["columns"][c]["psi"] = round(_psi(a, b), 4)
    out["note"] = "PSI>0.2 提示分布漂移；缺失/基数只描述，不替代业务口径"
    return out


def slo_budget(slo_pct: float, window_days: int, requests: float,
               downtime_minutes: float) -> dict:
    """SLO 错误预算：允许停机、已用、剩余、燃尽率。"""
    allowed = window_days * 24 * 60 * (1 - slo_pct / 100)
    used = max(0.0, downtime_minutes)
    remaining = allowed - used
    burn = used / allowed if allowed else float("inf")
    return {"slo_pct": slo_pct, "window_days": window_days,
            "allowed_downtime_min": round(allowed, 1),
            "used_min": round(used, 1), "remaining_min": round(remaining, 1),
            "burn_rate": round(burn, 3),
            "status": "正常" if burn < 0.8 else "预警" if burn < 1 else "超预算",
            "note": "错误预算按时间口径；请求量只用于换算影响面"}


def experiment_power(baseline: float, mde: float, alpha: float = 0.05,
                     power: float = 0.8) -> dict:
    """两比例 A/B 样本量：n = (zα√(2p̄(1-p̄)) + zβ√(p1(1-p1)+p2(1-p2)))² / mde²。"""
    p1 = baseline
    p2 = min(0.999, max(0.001, baseline + mde))
    if mde <= 0:
        raise ValueError("MDE 必须 > 0")
    z_alpha = 1.96 if abs(alpha - 0.05) < 1e-9 else 1.645 if alpha >= 0.1 else 2.576
    z_beta = 0.84 if abs(power - 0.8) < 1e-9 else 1.28 if power >= 0.9 else 0.52
    pbar = (p1 + p2) / 2
    n = ((z_alpha * math.sqrt(2 * pbar * (1 - pbar))
          + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2) / (mde ** 2)
    return {"n_per_group": math.ceil(n), "n_total": math.ceil(n) * 2,
            "baseline": p1, "mde": mde, "alpha": alpha, "power": power,
            "note": "两比例、双侧；实际还需按分流比与沟壑调整"}


def hiring_funnel(applied: float, screened: float, interviewed: float,
                  offers: float, hires: float) -> dict:
    """招聘漏斗：逐级转化率、整体产出、瓶颈环节。"""
    if min(applied, screened, interviewed, offers, hires) < 0:
        raise ValueError("漏斗各层不能为负")
    stages = [("投递→筛选", applied, screened), ("筛选→面试", screened, interviewed),
              ("面试→Offer", interviewed, offers), ("Offer→入职", offers, hires)]
    rates = {}
    for name, a, b in stages:
        rates[name] = round(b / a * 100, 2) if a else None
    overall = hires / applied * 100 if applied else None
    valid = [(name, r) for name, r in rates.items() if r is not None]
    bottleneck = min(valid, key=lambda x: x[1])[0] if valid else None
    return {"conversion_pct": rates, "overall_pct": round(overall, 2) if overall is not None else None,
            "bottleneck": bottleneck,
            "hires_per_100_applicants": round(overall, 1) if overall is not None else None,
            "note": "转化率只描述漏斗；瓶颈需结合周期与成本再判断"}


def eval_ci(successes: float, n: float) -> dict:
    """评测成功率 Wilson 95% CI。"""
    if n <= 0:
        raise ValueError("n 必须 > 0")
    p = successes / n
    z = 1.96
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return {"p": round(p * 100, 2),
            "ci95": [round(max(0, centre - half) * 100, 2),
                     round(min(1, centre + half) * 100, 2)],
            "n": n, "note": "Wilson 区间；小样本比正态近似稳"}


def retry_reliability(success_prob: float, max_attempts: int) -> dict:
    """重试可靠性：最终成功率、期望尝试次数、失败概率。"""
    if not (0 < success_prob <= 1) or max_attempts < 1:
        raise ValueError("success_prob∈(0,1]，max_attempts≥1")
    p = success_prob
    eventual = 1 - (1 - p) ** max_attempts
    expected = sum(k * (1 - p) ** (k - 1) * p for k in range(1, max_attempts + 1)) \
        + max_attempts * (1 - p) ** max_attempts
    return {"eventual_success_pct": round(eventual * 100, 3),
            "expected_attempts": round(expected, 3),
            "failure_pct": round((1 - eventual) * 100, 3),
            "note": "假设每次独立同分布；非幂等重试会放大副作用"}

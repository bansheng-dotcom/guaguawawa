# -*- coding: utf-8 -*-
"""第 4 段 · 留存：队列矩阵 + 留存曲线 + 激活 / 推荐。

门禁：每个队列分母固定且期初留存=分母；留存随周期单调不增；
流失逐期可解释（各期流失之和 = 期初 - 末期）；激活/推荐率可复算。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import common as c


def build(cohort_path: str) -> Dict[str, Any]:
    """跑留存段并返回带门禁的工件。"""
    rows = c.read_csv_rows(cohort_path)
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        cohort = str(row.get("cohort_month") or "").strip()
        period = c.num(row.get("period"))
        retained = c.num(row.get("retained"))
        size = c.num(row.get("cohort_size"))
        if not cohort or period is None or retained is None or size is None:
            continue
        buckets.setdefault(cohort, []).append({
            "period": int(period), "retained": retained, "cohort_size": size,
            "activated": c.num(row.get("activated")) or 0.0,
            "referrals": c.num(row.get("referrals")) or 0.0,
        })

    cohorts: Dict[str, Any] = {}
    denominator_fixed = True
    monotonic = True
    churn_ok = True
    rates_ok = True

    for name in sorted(buckets):
        items = sorted(buckets[name], key=lambda r: r["period"])
        sizes = {r["cohort_size"] for r in items}
        size = items[0]["cohort_size"]
        fixed = len(sizes) == 1 and size > 0
        denominator_fixed = denominator_fixed and fixed and items[0]["period"] == 0
        base_ok = bool(items) and items[0]["period"] == 0 and items[0]["retained"] == size

        rates = []
        prev = size
        drops = []
        for it in items:
            rate = c.safe_div(it["retained"], size)
            rates.append({"period": it["period"], "retained": it["retained"],
                          "retention_rate": c.rnd(rate, 6)})
            if it["retained"] > prev:
                monotonic = False
            if it["period"] > 0:
                drops.append(prev - it["retained"])
            prev = it["retained"]

        total_drop = size - items[-1]["retained"]
        explained = abs(sum(drops) - total_drop) < 1e-6
        churn_ok = churn_ok and explained
        act = c.safe_div(items[0]["activated"], size)
        ref = c.safe_div(items[0]["referrals"], size)
        rates_ok = rates_ok and act is not None and ref is not None

        cohorts[name] = {
            "cohort_size": c.rnd(size, 2),
            "activation_rate": c.rnd(act, 6),
            "referral_rate": c.rnd(ref, 6),
            "curve": rates,
            "churn_steps": [c.rnd(d, 2) for d in drops],
            "total_churn": c.rnd(total_drop, 2),
            "base_period_ok": base_ok,
        }
        denominator_fixed = denominator_fixed and base_ok

    # 汇总留存曲线：按队列规模加权，只取所有队列都覆盖的周期。
    periods = None
    for value in cohorts.values():
        keys = {r["period"] for r in value["curve"]}
        periods = keys if periods is None else (periods & keys)
    overall = []
    for period in sorted(periods or []):
        num = sum(cohorts[n]["cohort_size"] * next(
            r["retention_rate"] for r in cohorts[n]["curve"] if r["period"] == period)
            for n in cohorts)
        den = sum(cohorts[n]["cohort_size"] for n in cohorts)
        overall.append({"period": period, "retention_rate": c.rnd(c.safe_div(num, den), 6)})

    total_users = sum(v["cohort_size"] for v in cohorts.values())
    checks = [
        c.check("分母固定", denominator_fixed,
                f"cohorts={len(cohorts)}"),
        c.check("留存单调", monotonic, "retained 不应回升"),
        c.check("流失可解释", churn_ok, "逐期流失之和应等于期初减末期"),
        c.check("激活/推荐可算", rates_ok and bool(cohorts), f"cohorts={len(cohorts)}"),
        c.check("队列分母为正", total_users > 0, f"users={total_users}"),
    ]

    return c.stage_artifact("retention", {
        "cohorts": cohorts,
        "overall_curve": overall,
        "total_cohort_size": c.rnd(total_users, 2),
        "matrix": [[n, v["cohort_size"],
                    [r["retention_rate"] for r in v["curve"]]]
                   for n, v in cohorts.items()],
    }, checks)

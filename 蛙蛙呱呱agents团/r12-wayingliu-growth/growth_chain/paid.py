# -*- coding: utf-8 -*-
"""第 5 段 · 付费投放：CAC / LTV / 回收月 / 贡献毛利。

口径（月）：贡献毛利 = ARPA × 毛利率；LTV = 贡献毛利 / 月流失率；
CAC = 花费 / 新客；回收月 = CAC / 贡献毛利。
门禁：回收月 ≤ 阈值；分母为正；贡献毛利为正；LTV/CAC 可算。
"""
from __future__ import annotations

from typing import Any, Dict

from . import common as c


def build(paid_path: str, payback_max: float = 18.0) -> Dict[str, Any]:
    """跑付费段并返回带门禁的工件。"""
    rows = c.read_csv_rows(paid_path)
    channels: Dict[str, Any] = {}
    for row in rows:
        name = str(row.get("channel") or "").strip()
        spend = c.num(row.get("spend"))
        new = c.num(row.get("new_customers"))
        arpa = c.num(row.get("arpa"))
        margin = c.num(row.get("gross_margin"))
        churn = c.num(row.get("churn_rate"))
        if not name or None in (spend, new, arpa, margin, churn):
            continue
        cac = c.safe_div(spend, new)
        contribution = arpa * margin if arpa is not None and margin is not None else None
        ltv = c.safe_div(contribution, churn)
        payback = c.safe_div(cac, contribution)
        channels[name] = {
            "spend": c.rnd(spend, 2),
            "new_customers": c.rnd(new, 2),
            "cac": c.rnd(cac, 2),
            "arpa": c.rnd(arpa, 2),
            "gross_margin": c.rnd(margin, 4),
            "contribution_margin": c.rnd(contribution, 2),
            "ltv": c.rnd(ltv, 2),
            "ltv_cac": c.rnd(c.safe_div(ltv, cac), 4),
            "payback_months": c.rnd(payback, 2),
            "payback_ok": payback is not None and payback <= payback_max,
        }

    total_spend = sum(v["spend"] for v in channels.values())
    total_new = sum(v["new_customers"] for v in channels.values())
    total_cac = c.safe_div(total_spend, total_new)
    avg_contribution = (sum(v["contribution_margin"] * v["new_customers"]
                            for v in channels.values()) / total_new
                        if total_new else None)
    avg_payback = c.safe_div(total_cac, avg_contribution)
    total = {
        "spend": c.rnd(total_spend, 2),
        "new_customers": c.rnd(total_new, 2),
        "cac": c.rnd(total_cac, 2),
        "contribution_margin": c.rnd(avg_contribution, 2),
        "payback_months": c.rnd(avg_payback, 2),
        "payback_threshold": payback_max,
    }

    all_payback = all(v["payback_ok"] for v in channels.values()) and bool(channels)
    denominators_ok = all(v["new_customers"] > 0 for v in channels.values())
    contribution_ok = all(v["contribution_margin"] > 0 for v in channels.values())
    ltv_ok = all(v["ltv"] is not None and v["ltv_cac"] is not None
                 for v in channels.values())

    payback_text = ", ".join(f"{k}={v['payback_months']}" for k, v in channels.items())
    checks = [
        c.check("回收月≤阈值", all_payback,
                f"threshold={payback_max} {payback_text}"),
        c.check("分母为正", denominators_ok and total_new > 0,
                f"new_customers={total_new}"),
        c.check("贡献毛利为正", contribution_ok, ""),
        c.check("LTV/CAC 可算", ltv_ok and bool(channels), f"channels={len(channels)}"),
    ]

    return c.stage_artifact("paid", {
        "channels": channels,
        "totals": total,
        "cac_recompute": {
            "spend": c.rnd(total_spend, 2),
            "new_customers": c.rnd(total_new, 2),
            "cac": c.rnd(c.safe_div(total_spend, total_new), 2),
        },
    }, checks)

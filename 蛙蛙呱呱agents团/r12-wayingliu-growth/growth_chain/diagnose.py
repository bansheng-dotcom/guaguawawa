# -*- coding: utf-8 -*-
"""第 1 段 · 增长诊断：指标树 + 漏斗 + 异常检测。

输入：CSV（按日）或 JSON 行数组；必需列 visits/signups/activations/orders/revenue。
输出：北极星指标树（可拆到驱动）、漏斗转化、z 分数与环比异常。
门禁：指标树 ≥2 个驱动且 ≥2 层；漏斗逐级单调；异常必须带规则；分母为正。
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from . import common as c


SERIES = ("visits", "signups", "activations", "orders", "revenue")


def _load_rows(path: str) -> List[Dict[str, Any]]:
    """CSV 或 JSON 行数组统一入口。"""
    if path.lower().endswith(".json"):
        data = c.load_json(path)
        rows = data.get("rows", data) if isinstance(data, dict) else data
        return [dict(r) for r in rows]
    return c.read_csv_rows(path)


def _daily(rows: List[Dict[str, Any]]) -> List[Tuple[str, Dict[str, float]]]:
    """按日期聚合；缺失指标不补 0，整日缺失该指标会显式记 None。"""
    buckets: Dict[str, Dict[str, List[float]]] = {}
    for row in rows:
        day = str(row.get("date") or "").strip()
        if not day:
            continue
        slot = buckets.setdefault(day, {k: [] for k in SERIES})
        for key in SERIES:
            v = c.num(row.get(key))
            if v is not None:
                slot[key].append(v)
    out: List[Tuple[str, Dict[str, float]]] = []
    for day in sorted(buckets):
        out.append((day, {k: c.rnd(sum(v), 2) if v else None
                          for k, v in buckets[day].items()}))
    return out


def _series(daily: List[Tuple[str, Dict[str, float]]],
            key: str) -> List[float]:
    return [float(v[key]) for _, v in daily if v.get(key) is not None]


def _anomalies(daily: List[Tuple[str, Dict[str, float]]]) -> List[Dict[str, Any]]:
    """z 分数 >=2.5 或末段 vs 中段变化 >=20% 记为异常。"""
    found: List[Dict[str, Any]] = []
    for key in SERIES:
        vals = _series(daily, key)
        if len(vals) < 6:
            continue
        mu, sd = c.mean(vals), c.std(vals)
        k = len(vals) // 3
        mid = c.mean(vals[-2 * k:-k]) if k else mu
        last = c.mean(vals[-k:]) if k else mu
        delta = c.pct_change(last, mid)
        for idx, day in enumerate([d for d, row in daily if row.get(key) is not None]):
            z = (vals[idx] - mu) / sd if sd > 0 else 0.0
            if abs(z) >= 2.5:
                found.append({
                    "date": day, "metric": key, "rule": "z>=2.5",
                    "z": c.rnd(z, 3), "value": c.rnd(vals[idx], 2),
                    "direction": "up" if z > 0 else "down",
                })
        if delta is not None and abs(delta) >= 0.20:
            found.append({
                "period": "last_third_vs_mid_third", "metric": key,
                "rule": "period_delta>=20%", "delta_pct": c.rnd(delta, 4),
                "direction": "up" if delta > 0 else "down",
            })
    return found


def build(path: str) -> Dict[str, Any]:
    """跑诊断段并返回带门禁的工件。"""
    rows = _load_rows(path)
    daily = _daily(rows)
    totals = {k: c.rnd(sum(_series(daily, k)), 2) for k in SERIES}

    visits = totals["visits"] or 0.0
    signups = totals["signups"] or 0.0
    activations = totals["activations"] or 0.0
    orders = totals["orders"] or 0.0
    revenue = totals["revenue"] or 0.0

    aov = c.safe_div(revenue, orders)
    order_cvr = c.safe_div(orders, visits)
    signup_cvr = c.safe_div(signups, visits)
    activation_cvr = c.safe_div(activations, signups)

    tree = {
        "north_star": {"metric": "revenue", "value": c.rnd(revenue, 2),
                       "formula": "orders × aov"},
        "levels": [
            {"id": "revenue", "parents": [], "drivers": ["orders", "aov"],
             "formula": "orders × aov"},
            {"id": "orders", "parents": ["revenue"], "drivers": ["visits", "order_cvr"],
             "formula": "visits × order_cvr"},
            {"id": "aov", "parents": ["revenue"], "drivers": ["revenue", "orders"],
             "formula": "revenue / orders"},
            {"id": "signups", "parents": ["orders"], "drivers": ["visits", "signup_cvr"],
             "formula": "visits × signup_cvr"},
            {"id": "activations", "parents": ["signups"], "drivers": ["signups", "activation_cvr"],
             "formula": "signups × activation_cvr"},
        ],
        "drivers": {
            "visits": c.rnd(visits, 2), "signups": c.rnd(signups, 2),
            "activations": c.rnd(activations, 2), "orders": c.rnd(orders, 2),
            "aov": c.rnd(aov, 2), "order_cvr": c.rnd(order_cvr, 6),
            "signup_cvr": c.rnd(signup_cvr, 6),
            "activation_cvr": c.rnd(activation_cvr, 6),
        },
    }

    stages = [("visits", visits), ("signups", signups),
              ("activations", activations), ("orders", orders)]
    funnel = []
    for idx, (name, value) in enumerate(stages):
        prev = stages[idx - 1][1] if idx else None
        funnel.append({
            "stage": name, "value": c.rnd(value, 2),
            "step_cvr": c.rnd(c.safe_div(value, prev), 6) if idx else 1.0,
            "of_top": c.rnd(c.safe_div(value, visits), 6),
        })

    anomalies = _anomalies(daily)
    driven = len([d for d in tree["drivers"].values() if d is not None])
    monotonic = all(funnel[i]["value"] is None or funnel[i - 1]["value"] is None
                    or funnel[i]["value"] <= funnel[i - 1]["value"]
                    for i in range(1, len(funnel)))
    rules_ok = all(a.get("rule") for a in anomalies)

    checks = [
        c.check("指标树可拆到驱动", driven >= 6 and len(tree["levels"]) >= 2,
                f"drivers={driven} levels={len(tree['levels'])}"),
        c.check("漏斗单调", monotonic, str([f["value"] for f in funnel])),
        c.check("异常检测有规则", rules_ok, f"anomalies={len(anomalies)}"),
        c.check("分母为正", visits > 0 and orders > 0,
                f"visits={visits} orders={orders}"),
    ]

    return c.stage_artifact("diagnose", {
        "metric": "revenue",
        "window": {"start": daily[0][0] if daily else None,
                   "end": daily[-1][0] if daily else None,
                   "days": len(daily)},
        "totals": totals,
        "metric_tree": tree,
        "funnel": funnel,
        "anomalies": anomalies,
    }, checks)

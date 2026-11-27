# -*- coding: utf-8 -*-
"""第 3 段 · 多渠道归因：首触 / 末触 / 线性 / 位置 + 增量。

口径：分母固定为「转化用户数」，四种模型各自把 1 个转化分配给用户路径；
所有模型的转化总量必须等于分母。增量结论只能来自实验证据，
没有实验就只能是相关，禁止当因果。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import common as c


MODELS = ("first_touch", "last_touch", "linear", "position_based")


def _journeys(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """按 user_id 还原触点序列（按 time 排序，空渠道丢弃）。"""
    buckets: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        uid = str(row.get("user_id") or "").strip()
        channel = str(row.get("channel") or "").strip()
        if not uid or not channel:
            continue
        buckets.setdefault(uid, []).append(row)
    journeys = []
    for uid in sorted(buckets):
        touches = sorted(buckets[uid], key=lambda r: str(r.get("touch_time") or ""))
        converted = any((c.num(r.get("converted")) or 0) >= 1 for r in touches)
        revenue = sum(c.num(r.get("revenue")) or 0 for r in touches
                      if (c.num(r.get("converted")) or 0) >= 1)
        journeys.append({
            "user_id": uid,
            "channels": [t["channel"].strip() for t in touches],
            "converted": converted,
            "revenue": revenue,
        })
    return journeys


def _allocate(channels: List[str], weights: List[float],
              revenue: float, out: Dict[str, Dict[str, float]]) -> None:
    for ch, w in zip(channels, weights):
        slot = out.setdefault(ch, {"conversions": 0.0, "revenue": 0.0})
        slot["conversions"] += w
        slot["revenue"] += revenue * w


def _finish(raw: Dict[str, Dict[str, float]], total_conv: float,
            total_rev: float) -> Dict[str, Any]:
    channels = {}
    for ch in sorted(raw):
        v = raw[ch]
        channels[ch] = {
            "conversions": c.rnd(v["conversions"], 4),
            "revenue": c.rnd(v["revenue"], 2),
            "conv_share": c.rnd(c.safe_div(v["conversions"], total_conv), 6),
            "revenue_share": c.rnd(c.safe_div(v["revenue"], total_rev), 6),
        }
    return {"channels": channels,
            "sum_conversions": c.rnd(sum(v["conversions"] for v in raw.values()), 4),
            "sum_revenue": c.rnd(sum(v["revenue"] for v in raw.values()), 2)}


def check(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """独立门禁复核（误用工件拦截）。"""
    models = artifact.get("models") or {}
    den = (artifact.get("denominator") or {}).get("value") or 0
    consistent = bool(models) and all(
        abs(float(m.get("sum_conversions") or 0) - float(den)) < 1e-6
        for m in models.values())
    inc = artifact.get("incrementality") or {}
    claim = bool(artifact.get("causal_claim"))
    established = bool(inc.get("established")) and inc.get("method") not in (
        None, "not_run")
    checks = [
        c.check("归因分母与模型一致", consistent, f"denominator={den}"),
        c.check("禁止把相关当因果", (not claim) or established,
                f"causal_claim={claim} method={inc.get('method')}"),
        c.check("增量需实验证据", established or not claim,
                str(inc.get("method"))),
        c.check("分母为正", float(den) > 0, f"denominator={den}"),
    ]
    return c.gate(checks)


def build(touches_path: str, evidence_path: Optional[str] = None,
          budget_total: float = 100000.0,
          causal_claim: bool = False) -> Dict[str, Any]:
    """跑归因段并返回带门禁的工件。"""
    rows = c.read_csv_rows(touches_path)
    journeys = _journeys(rows)
    converts = [j for j in journeys if j["converted"]]
    total_conv = len(converts)
    total_rev = sum(j["revenue"] for j in converts)

    raw = {m: {} for m in MODELS}
    for j in converts:
        chs = j["channels"]
        weights = {
            "first_touch": [1.0] + [0.0] * (len(chs) - 1),
            "last_touch": [0.0] * (len(chs) - 1) + [1.0],
            "linear": [1.0 / len(chs)] * len(chs),
        }
        pos = [0.0] * len(chs)
        if len(chs) == 1:
            pos[0] = 1.0
        elif len(chs) == 2:
            pos[0], pos[1] = 0.5, 0.5
        else:
            pos[0], pos[-1] = 0.4, 0.4
            for i in range(1, len(chs) - 1):
                pos[i] = 0.2 / (len(chs) - 2)
        weights["position_based"] = pos
        for model in MODELS:
            _allocate(chs, weights[model], j["revenue"], raw[model])

    models = {m: _finish(raw[m], total_conv, total_rev) for m in MODELS}
    consistent = all(abs(models[m]["sum_conversions"] - total_conv) < 1e-6
                     for m in MODELS)

    evidence = None
    if evidence_path:
        evidence = c.load_json(evidence_path)
    incrementality = {
        "established": bool(evidence and evidence.get("lift") is not None),
        "lift": evidence.get("lift") if evidence else None,
        "ci": evidence.get("ci") if evidence else None,
        "method": evidence.get("method") if evidence else "not_run",
    }
    causal_ok = (not causal_claim) or incrementality["established"]
    increment_ok = incrementality["established"] or not causal_claim

    # 预算建议：按末触收入份额分配，最小 5%，总和守恒。
    paid = models["last_touch"]["channels"]
    shares = {ch: max(v["revenue_share"] or 0, 0.05) for ch, v in paid.items()}
    norm = sum(shares.values()) or 1.0
    budget = {}
    allocated = 0.0
    ordered = sorted(shares)
    for idx, ch in enumerate(ordered):
        if idx == len(ordered) - 1:
            amount = round(budget_total - allocated, 2)
        else:
            amount = round(budget_total * shares[ch] / norm, 2)
            allocated += amount
        budget[ch] = amount

    checks = [
        c.check("归因分母与模型一致", consistent,
                f"denominator={total_conv} sums="
                f"{[models[m]['sum_conversions'] for m in MODELS]}"),
        c.check("每用户至少一次触点", all(j["channels"] for j in journeys),
                f"journeys={len(journeys)}"),
        c.check("禁止把相关当因果", causal_ok,
                f"causal_claim={causal_claim} established={incrementality['established']}"),
        c.check("增量需实验证据", increment_ok,
                str(incrementality["method"])),
        c.check("分母为正", total_conv > 0, f"converting_users={total_conv}"),
    ]

    return c.stage_artifact("attribution", {
        "denominator": {"name": "converting_users", "value": total_conv},
        "journeys": {"users": len(journeys), "touches": len(rows),
                     "converting_users": total_conv},
        "models": models,
        "incrementality": incrementality,
        "causal_claim": bool(causal_claim),
        "budget_recommendation": {"total": c.rnd(budget_total, 2),
                                  "by_channel": budget,
                                  "basis": "last_touch_revenue_share"},
    }, checks)

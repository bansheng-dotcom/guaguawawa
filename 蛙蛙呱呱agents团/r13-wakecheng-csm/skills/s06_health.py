# -*- coding: utf-8 -*-
"""S06 客户健康与续约输入 —— 能力域 6。

整合 twenty 的使用/互动数据 + chatwoot 的工单/CSAT + formbricks 的反馈，
把「客户健康表」转成确定性实算：四维加权健康分（usage/support/voc/engagement，
权重外置）、风险分带（healthy/watch/at_risk）、续约窗口与续约候选、流失预警。

健康分口径：每个维度 0-100 分，加权求和；权重在 thresholds.health.weights。
风险分带：≥75 healthy、50-74 watch、<50 at_risk（bands 外置）。
续约候选：距续约日 ≤ renewal_window_days 且健康分 ≥ renewal_score_min。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "health"
DESC = "客户健康与续约输入：health/risk"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("health", help="校验客户健康表与续约候选")
    a.add_argument("--input", required=True)
    b = act.add_parser("risk", help="校验单个客户的健康与风险")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "health":
        return _validate_health(data)
    if args.action == "risk":
        return _validate_risk(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _num(v) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def _band(score: float, bands: Dict[str, float]) -> str:
    if score >= bands["healthy"]:
        return "healthy"
    if score >= bands["watch"]:
        return "watch"
    return "at_risk"


def _score(cust: Dict[str, Any], weights: Dict[str, float]) -> float:
    score = 0.0
    for dim, w in weights.items():
        score += c.clamp(_num(cust.get(dim)), 0, 100) * w / 100.0
    return round(score, 1)


# --------------------------------------------------------------------------- #
def _validate_health(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    hth = c.load_thresholds()["health"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", customer_count=0)

    customers = data.get("customers")
    if not isinstance(customers, list) or not customers:
        return c.result([_ck(False, "customers 必须是非空列表", "health.list")],
                        ok=False, verdict="FAIL", customer_count=0)

    weights = hth["weights"]
    bands = hth["risk_bands"]
    rows = []
    for cst in customers:
        if not isinstance(cst, dict):
            continue
        s = _score(cst, weights)
        rows.append({"name": cst.get("name", "?"), "score": s,
                     "band": _band(s, bands), "renewal_in_days":
                     cst.get("renewal_in_days")})
    # 每行必须有 name（健康表不能有匿名行）
    nameless = [i for i, cst in enumerate(customers)
                if not isinstance(cst, dict) or not str(cst.get("name", "")).strip()]
    checks.append(_ck(not nameless, f"健康表无匿名行（缺名下标 {nameless or '无'}）",
                      "health.name"))

    # 权重完整性：四维权重必须和为 100（口径恒等）
    wsum = sum(weights.values())
    checks.append(_ck(abs(wsum - 100) < 0.01, f"四维权重和={wsum} = 100", "health.weights"))

    # 续约候选：renewal_in_days ≤ window 且 score ≥ min
    window = hth["renewal_window_days"]
    rmin = hth["renewal_score_min"]
    renewal_candidates = [r for r in rows
                          if r["renewal_in_days"] is not None
                          and _num(r["renewal_in_days"]) <= window]
    at_risk = [r for r in rows if r["band"] == "at_risk"]
    checks.append(_ck(True,
                      f"续约窗口 {len(renewal_candidates)} 名、风险名单 {len(at_risk)} 名",
                      "health.summary"))

    # 高风险必须有原因（不能只给分不给归因）
    risk_no_reason = [cst.get("name") for cst in customers if isinstance(cst, dict)
                      and _band(_score(cst, weights), bands) == "at_risk"
                      and not str(cst.get("risk_reason", "")).strip()]
    checks.append(_ck(not risk_no_reason, f"风险客户均写归因（缺 {risk_no_reason or '无'}）",
                      "health.risk_reason"))

    ok = all(x["ok"] for x in checks)
    avg = round(sum(r["score"] for r in rows) / len(rows), 1) if rows else 0.0
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        customer_count=len(customers), avg_health=avg,
        at_risk_count=len(at_risk),
        renewal_candidates=[r["name"] for r in renewal_candidates if r["score"] >= rmin],
        health_rows=rows,
        narrative=(f"客户 {len(customers)} 名、平均健康分 {avg}、"
                   f"at_risk {len(at_risk)} 名、续约候选 "
                   f"{len([r for r in renewal_candidates if r['score'] >= rmin])} 名"))


# --------------------------------------------------------------------------- #
def _validate_risk(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    hth = c.load_thresholds()["health"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", customer_count=0)

    name = str(data.get("name", "")).strip()
    checks.append(_ck(bool(name), "客户名非空", "risk.name"))

    weights = hth["weights"]
    score = _score(data, weights)
    band = _band(score, hth["risk_bands"])
    checks.append(_ck(True, f"健康分={score}、分带={band}", "risk.score"))

    # 分带一致性：四维里任一 ≤ low_csat_max 的分带不得判 healthy（防「高分掩盖单维崩坏」）
    low_dims = [d for d in weights if _num(data.get(d)) <= hth["low_csat_max"]]
    if band == "healthy" and low_dims:
        checks.append(_ck(False, f"单维崩坏却判 healthy：{low_dims} ≤ "
                                 f"{hth['low_csat_max']}", "risk.band_consistency"))
    else:
        checks.append(_ck(True, "分带与单维一致", "risk.band_consistency"))

    if band == "at_risk":
        reason = str(data.get("risk_reason", "")).strip()
        checks.append(_ck(bool(reason), "at_risk 必须写归因", "risk.reason"))
    else:
        checks.append(_ck(True, f"{band} 不强制归因", "risk.reason"))

    ok = all(x["ok"] for x in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    customer_count=1, health_score=score, band=band,
                    narrative=f"{name} 健康分 {score}（{band}）")

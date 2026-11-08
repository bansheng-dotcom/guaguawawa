# -*- coding: utf-8 -*-
"""S01 增长诊断与基线 —— 能力域 1。

整合自 coreyhaines31__marketingskills（marketing-plan / analytics / revops 的基线）。
把「增长诊断」从口头判断转成确定性校验：北极星指标一主一辅、漏斗五阶段枚举、
PMF 信号、单位经济算术实算（LTV/CAC/回收期）。本角色不做统计显著性（交 R06），
只做可复算的单位经济与基线口径。

动作：
  diagnose  增长诊断（北极星/漏斗/PMF 信号）
  unit      单位经济（LTV/CAC/回收期 实算）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "diagnose"
DESC = "增长诊断与基线：diagnose/unit"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    b = act.add_parser("diagnose", help="校验增长诊断")
    b.add_argument("--input", required=True)
    u = act.add_parser("unit", help="校验单位经济")
    u.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "diagnose":
        return _validate_diagnose(data)
    if args.action == "unit":
        return _validate_unit(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_diagnose(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    ns = data.get("northstar")
    ok_ns = isinstance(ns, dict) and all(
        str(ns.get(k, "")).strip() for k in th["diagnose"]["northstar_required"])
    checks.append(_ck(ok_ns, "北极星指标一主一辅齐备", "diagnose.northstar"))

    funnel = data.get("funnel")
    stages = th["diagnose"]["funnel_stages"]
    ok_funnel = isinstance(funnel, list) and len(funnel) > 0
    checks.append(_ck(ok_funnel,
                      f"漏斗阶段 ≥1（实际 {len(funnel) if isinstance(funnel, list) else 0}）",
                      "diagnose.funnel"))
    if ok_funnel:
        bad_stage = [s for s in funnel if s not in stages]
        checks.append(_ck(not bad_stage, f"漏斗阶段在白名单（越界 {bad_stage or '无'}）",
                          "diagnose.funnel_enum"))
    else:
        checks.append(_ck(False, "漏斗阶段缺失", "diagnose.funnel_enum"))

    signals = data.get("pmf_signals")
    known = th["diagnose"]["pmf_signals"]
    ok_sig = isinstance(signals, list) and len(signals) > 0
    checks.append(_ck(ok_sig,
                      f"PMF 信号 ≥1（实际 {len(signals) if isinstance(signals, list) else 0}）",
                      "diagnose.pmf"))
    if ok_sig:
        bad_sig = [s for s in signals if s not in known]
        checks.append(_ck(not bad_sig, f"PMF 信号在白名单（越界 {bad_sig or '无'}）",
                          "diagnose.pmf_enum"))
    else:
        checks.append(_ck(False, "PMF 信号缺失", "diagnose.pmf_enum"))

    bad_stage = [s for s in (funnel or []) if s not in stages]
    bad_sig = [s for s in (signals or []) if s not in known]
    ok = ok_ns and ok_funnel and ok_sig and not bad_stage and not bad_sig
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    funnel_count=len(funnel) if isinstance(funnel, list) else 0,
                    signal_count=len(signals) if isinstance(signals, list) else 0)


# --------------------------------------------------------------------------- #
def _validate_unit(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    def num(k):
        v = data.get(k)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    arpa, gm, churn = num("arpa"), num("gross_margin"), num("churn_rate")
    spend, new_customers = num("spend"), num("new_customers")

    ok_nums = all(v is not None for v in (arpa, gm, churn, spend, new_customers))
    checks.append(_ck(ok_nums, "单位经济数字字段齐备", "unit.fields"))
    if not ok_nums:
        return c.result(checks, ok=False, verdict="FAIL", ltv=None, cac=None,
                        payback_months=None, ltv_cac=None)

    ltv = c.safe_div(arpa * gm, churn)
    cac = c.safe_div(spend, new_customers)
    payback = c.safe_div(cac, (arpa * gm)) if (arpa and gm) else None
    ltv_cac = c.safe_div(ltv, cac)

    checks.append(_ck(churn > 0, f"churn_rate={churn} 为正", "unit.churn"))
    checks.append(_ck(new_customers > 0, f"new_customers={new_customers} 为正",
                      "unit.customers"))

    healthy = th["diagnose"]["ltv_cac_healthy"]
    ok_ltvcac = ltv_cac >= healthy
    checks.append(_ck(ok_ltvcac,
                      f"LTV:CAC={ltv_cac} ≥ {healthy}（健康）", "unit.ltv_cac"))

    pmax = th["diagnose"]["payback_months_max"]
    ok_payback = payback is not None and payback <= pmax
    checks.append(_ck(ok_payback,
                      f"回收期={payback} 月 ≤ {pmax}", "unit.payback"))

    ok = ok_nums and ok_ltvcac and ok_payback
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    ltv=ltv, cac=cac, payback_months=payback, ltv_cac=ltv_cac)

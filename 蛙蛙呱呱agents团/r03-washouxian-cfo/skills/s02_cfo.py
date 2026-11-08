# -*- coding: utf-8 -*-
"""S02 CFO 经营诊断（能力域 2）。

来源：alirezarezvani__claude-skills cfo-advisor
（burn_rate_calculator：月度现金模拟 + runway 决策触发器 9/6/4/3 个月
+ burn multiple = 总净烧钱/净新增 ARR；
unit_economics_analyzer：LTV=ARPA×GM/churn、CAC payback=CAC/(ARPA×GM)、
churn 由队列收入反推 (M12/M1)^(1/11)）
+ JoelLewis__finance_skills financial-statements（三表勾稽恒等式）。

确定性口径：runway 触发器、burn multiple、LTV:CAC、payback、勾稽恒等式全部外置。
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c

NAME = "cfo"
DESC = "CFO 经营诊断：runway/unitecon/healthcheck"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("runway", "烧钱率与跑道模拟（月度现金流 + 决策触发器）"),
                 ("unitecon", "单位经济（LTV/CAC/回本/LTV:CAC 门禁）"),
                 ("healthcheck", "三表勾稽恒等式校验（资产/现金/毛利）")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"runway": _runway, "unitecon": _unitecon,
          "healthcheck": _healthcheck}[args.action]
    return fn(data)


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------------------------------- #
def _runway(data: Any) -> Dict[str, Any]:
    """按月模拟：mrr 增长 → 毛利 → 人力+运营 → 净烧 → 现金 → runway；
    触发器 = runway 跌破 9/6/4/3 个月的最早月份（来源 burn_rate_calculator）。"""
    th = c.load_thresholds()["cfo"]
    cash = _num(data.get("starting_cash"))
    mrr = _num(data.get("starting_mrr"))
    headcount_cost = _num(data.get("monthly_headcount_cost"))
    other_opex = _num(data.get("monthly_other_opex"))
    gm = _num(data.get("gross_margin_pct"))
    growth = _num(data.get("mrr_growth_rate"))
    months = int(data.get("model_months", 24))
    if not (0 <= gm <= 1 and 0 <= growth <= 1):
        return c.result([c.ck(False, "gross_margin_pct / mrr_growth_rate "
                                     "须在 [0,1]", "input", "CRITICAL")],
                        next="修正输入口径后重跑")
    starting_mrr = mrr
    rows: List[Dict[str, Any]] = []
    triggers: List[Dict[str, Any]] = []
    fired = set()
    cash_out_month = None
    total_net_burn = 0.0
    for m in range(1, months + 1):
        mrr = mrr * (1 + growth)
        gross_profit = mrr * gm
        gross_burn = headcount_cost + other_opex
        net_burn = gross_burn - gross_profit
        cash_start = cash
        cash = cash - net_burn
        total_net_burn += max(net_burn, 0.0)
        runway = cash / net_burn if net_burn > 0 else None
        for label, months_thr in th["runway_triggers"].items():
            if runway is not None and runway <= months_thr \
                    and label not in fired:
                fired.add(label)
                triggers.append({"month": m, "trigger": label,
                                 "runway_months": round(runway, 1)})
        rows.append({"month": m, "mrr": round(mrr, 0),
                     "net_burn": round(net_burn, 0),
                     "cash_end": round(cash, 0),
                     "runway_months": None if runway is None
                     else round(runway, 1)})
        if cash <= 0:
            cash_out_month = m
            break
    new_arr = (mrr - starting_mrr) * 12
    burn_multiple = (total_net_burn / new_arr
                     if new_arr > 0 else None)
    checks: List[Dict[str, Any]] = []
    checks.append(c.ck(cash_out_month is None,
                       f"模拟期现金{'耗尽于第 ' + str(cash_out_month) + ' 个月' if cash_out_month else '未耗尽'}",
                       "cash_out", "CRITICAL" if cash_out_month else "OK",
                       cash_out_month=cash_out_month))
    checks.append(c.ck(not any(t["trigger"] in ("cost_reduction",
                                                "execute_cuts", "emergency")
                               for t in triggers),
                       f"触发器 {[t['trigger'] + '@M' + str(t['month']) for t in triggers] or '无'}",
                       "triggers", "HIGH" if triggers else "OK"))
    if burn_multiple is not None:
        checks.append(c.ck(burn_multiple <= th["burn_multiple_max"],
                           f"burn multiple {burn_multiple:.2f}x"
                           f"（≤ {th['burn_multiple_max']}x）",
                           "burn_multiple", "HIGH"
                           if burn_multiple > th["burn_multiple_max"] else "OK"))
    return c.result(checks, rows=rows[:24], trigger_count=len(triggers),
                    triggers=triggers,
                    burn_multiple=None if burn_multiple is None
                    else round(burn_multiple, 2),
                    cash_out_month=cash_out_month,
                    next="触发器命中即启动融资/降本预案（决策交 R01）")


# --------------------------------------------------------------------------- #
def _unitecon(data: Any) -> Dict[str, Any]:
    """LTV/CAC/回本/LTV:CAC；队列 churn 反推 (M12/M1)^(1/11) 并夹紧。"""
    th = c.load_thresholds()["cfo"]
    cohorts = data.get("cohorts", []) or []
    checks: List[Dict[str, Any]] = []
    if not cohorts:
        checks.append(c.ck(False, "cohorts 为空", "structure", "CRITICAL"))
        return c.result(checks, next="按获客期补队列收入")
    lo, hi = th["churn_clamp"]
    rows: List[Dict[str, Any]] = []
    for i, co in enumerate(cohorts):
        label = str(co.get("label", f"cohort-{i + 1}"))
        n = int(co.get("customers_acquired", 0))
        if n <= 0:
            checks.append(c.ck(False, f"{label} customers_acquired=0",
                               "customers", "CRITICAL", cohort=label))
            continue
        cac = _num(co.get("total_cac_spend")) / n
        rev = [ _num(x) for x in (co.get("monthly_revenue", []) or []) ]
        m1 = rev[0] if rev else 0.0
        arpa = m1 / n
        gm = _num(co.get("gross_margin_pct", 0.70))
        churn = th["churn_default"]
        if len(rev) >= 12 and rev[0] > 0 and rev[11] > 0:
            churn = 1 - (rev[11] / rev[0]) ** (1 / 11)
        elif len(rev) >= 6 and rev[0] > 0 and rev[5] > 0:
            churn = 1 - (rev[5] / rev[0]) ** (1 / 5)
        churn = max(lo, min(hi, churn))
        ltv = arpa * gm / churn if churn > 0 else None
        payback = cac / (arpa * gm) if arpa * gm > 0 else None
        ratio = ltv / cac if (ltv is not None and cac > 0) else None
        rows.append({"label": label, "cac": round(cac, 2),
                     "arpa": round(arpa, 2),
                     "monthly_churn": round(churn, 4),
                     "ltv": None if ltv is None else round(ltv, 2),
                     "payback_months": None if payback is None
                     else round(payback, 1),
                     "ltv_cac": None if ratio is None else round(ratio, 2)})
        if ratio is not None and ratio < th["ltv_cac_min"]:
            checks.append(c.ck(False,
                               f"{label} LTV:CAC={ratio:.2f}"
                               f"（< {th['ltv_cac_min']}）",
                               "ltv_cac", "HIGH", cohort=label))
        if payback is not None and payback > th["payback_max_months"]:
            checks.append(c.ck(False,
                               f"{label} CAC 回本 {payback:.1f} 月"
                               f"（> {th['payback_max_months']}）",
                               "payback", "HIGH", cohort=label))
    worst = min((r["ltv_cac"] for r in rows if r["ltv_cac"] is not None),
                default=None)
    checks.append(c.ck(worst is None or worst >= th["ltv_cac_min"],
                       f"最差队列 LTV:CAC {worst}",
                       "overall", "OK"))
    return c.result(checks, cohort_count=len(rows), cohorts=rows,
                    next="不达标渠道冻结投放，改口径须先改 thresholds")


# --------------------------------------------------------------------------- #
def _healthcheck(data: Any) -> Dict[str, Any]:
    """三表勾稽：资产=负债+权益；期末现金=期初+经营+投资+融资；
    毛利=收入−COGS（来源 financial-statements）。"""
    th = c.load_thresholds()["cfo"]
    bs = data.get("balance_sheet", {}) or {}
    cf = data.get("cash_flow", {}) or {}
    pl = data.get("income_statement", {}) or {}
    tol = 0.01
    checks: List[Dict[str, Any]] = []
    assets = _num(bs.get("assets"))
    le = _num(bs.get("liabilities")) + _num(bs.get("equity"))
    checks.append(c.ck(abs(assets - le) <= tol,
                       f"资产 {assets:.2f} = 负债+权益 {le:.2f}",
                       "balance_sheet", "CRITICAL"
                       if abs(assets - le) > tol else "OK",
                       identity=th["identities"][0]))
    cash_end_calc = (_num(cf.get("cash_begin")) + _num(cf.get("operating"))
                     + _num(cf.get("investing")) + _num(cf.get("financing")))
    cash_end_rep = _num(cf.get("cash_end"))
    checks.append(c.ck(abs(cash_end_calc - cash_end_rep) <= tol,
                       f"现金勾稽：推算 {cash_end_calc:.2f} = 申报 "
                       f"{cash_end_rep:.2f}", "cash_flow",
                       "CRITICAL" if abs(cash_end_calc - cash_end_rep) > tol
                       else "OK", identity=th["identities"][1]))
    gp_calc = _num(pl.get("revenue")) - _num(pl.get("cogs"))
    gp_rep = _num(pl.get("gross_profit"))
    checks.append(c.ck(abs(gp_calc - gp_rep) <= tol,
                       f"毛利勾稽：推算 {gp_calc:.2f} = 申报 {gp_rep:.2f}",
                       "income_statement",
                       "CRITICAL" if abs(gp_calc - gp_rep) > tol else "OK",
                       identity=th["identities"][2]))
    if bs and abs(assets) <= tol and not bs.get("assets"):
        checks.append(c.ck(False, "balance_sheet 缺 assets", "structure",
                           "CRITICAL"))
    return c.result(checks,
                    next="三表恒等式全绿才可进月结包（s01.rollforward）")

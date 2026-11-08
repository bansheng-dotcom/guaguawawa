# -*- coding: utf-8 -*-
"""S03 税务与申报边界（能力域 3）。

来源：JoelLewis__finance_skills equity-compensation（ISO 合格处置
= 授予日起 >2 年 且 行权日起 >1 年；$100,000 首次可行权限额；
TMT = 26%×断点内 + 28%×超出，AMT = max(0, TMT − 常规税)；
离职后 3 个月行权窗口）
+ retirement-decumulation（RMD 73 岁、2033 起 75 岁；
Uniform Lifetime Table 除数 73→26.5/75→24.6/80→20.2/85→16.0/90→12.2；
漏缴 25% 消费税、更正窗口 10%）
+ 税务预估安全港（90% 当年 / 100% 上年 / 高 AGI 110%；
补充工资预扣 22% / 超 $1M 37%）。

所有法定数字走 thresholds（T9），逐年核实口径不改代码。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from skills import _common as c

NAME = "tax"
DESC = "税务与申报边界：iso/rmd/safeharbor"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("iso", "ISO 合格处置判定 + AMT 交叉计算 + $100K 限额"),
                 ("rmd", "RMD 计算 + 消费税罚金 + 最低分配缺口"),
                 ("safeharbor", "预估税安全港 + 补充工资预扣缺口")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"iso": _iso, "rmd": _rmd, "safeharbor": _safeharbor}[args.action]
    return fn(data)


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _d(v: Any) -> date:
    if isinstance(v, str) and len(v) >= 10:
        try:
            return date.fromisoformat(v[:10])
        except ValueError:
            return date(1970, 1, 1)
    return date(1970, 1, 1)


def _yrs(a: date, b: date) -> float:
    return (b - a).days / 365.25


# --------------------------------------------------------------------------- #
def _iso(data: Any) -> Dict[str, Any]:
    """ISO 处置判定 + AMT 交叉计算（来源 equity-compensation 算例口径）。"""
    th = c.load_thresholds()["tax"]
    grants = data.get("exercises", []) or []
    checks: List[Dict[str, Any]] = []
    if not grants:
        checks.append(c.ck(False, "exercises 为空", "structure", "CRITICAL"))
        return c.result(checks, next="补行权/处置记录")
    # $100,000 首次可行权限额（按授予日 FMV 计）
    by_year: Dict[int, float] = {}
    for g in grants:
        y = _d(g.get("grant_date")).year
        by_year[y] = by_year.get(y, 0.0) + \
            _num(g.get("shares")) * _num(g.get("grant_fmv"))
    for y, v in sorted(by_year.items()):
        if v > th["iso_first_exercisable_limit"]:
            checks.append(c.ck(False,
                               f"{y} 年首次可行权 ISO 授予日 FMV 合计 "
                               f"{v:,.0f} > ${th['iso_first_exercisable_limit']:,}"
                               f"（超出部分按 NSO 处理）",
                               "iso_limit", "HIGH", year=y,
                               excess=round(v - th["iso_first_exercisable_limit"], 2)))
    rows: List[Dict[str, Any]] = []
    amt_adjustment_total = 0.0
    for i, g in enumerate(grants):
        label = str(g.get("label", f"iso-{i + 1}"))
        grant, exercise, sale = (_d(g.get("grant_date")),
                                 _d(g.get("exercise_date")),
                                 _d(g.get("sale_date", date.today())))
        held_grant = _yrs(grant, sale)
        held_ex = _yrs(exercise, sale)
        qualifying = (held_grant > th["iso_grant_holding_years"]
                      and held_ex > th["iso_exercise_holding_years"])
        spread = (_num(g.get("shares"))
                  * (_num(g.get("exercise_fmv")) - _num(g.get("strike"))))
        amt_adjustment_total += spread
        rows.append({"label": label,
                     "holding_grant_years": round(held_grant, 2),
                     "holding_exercise_years": round(held_ex, 2),
                     "qualifying": qualifying,
                     "amt_adjustment": round(spread, 2)})
        if not qualifying and g.get("sale_date"):
            checks.append(c.ck(False,
                               f"{label} 持有期不合格（授予 {held_grant:.2f} 年 / "
                               f"行权 {held_ex:.2f} 年）→ 不合格处置，"
                               f"价差按普通收入计税",
                               "iso_qualifying", "MEDIUM", grant=label))
        # 离职行权窗口：termination_date 存在时，行权须在 3 个月内
        term = g.get("termination_date")
        if term:
            months = (_d(exercise) - _d(term)).days / 30.44
            if months > th["iso_termination_window_months"]:
                checks.append(c.ck(False,
                                   f"{label} 离职后 {months:.1f} 个月才行权"
                                   f"（> {th['iso_termination_window_months']} 个月）"
                                   f"→ ISO 身份失效",
                                   "iso_termination", "HIGH", grant=label))
    # AMT 交叉计算：TMT = 26%×断点内 + 28%×超出；AMT = max(0, TMT−常规税)
    amti = _num(data.get("regular_income")) + amt_adjustment_total
    base = amti - th["amt_exemption"]
    tmt = 0.0
    if base > 0:
        tmt = (min(base, th["amt_breakpoint"]) * th["amt_rate_low"]
               + max(0.0, base - th["amt_breakpoint"])
               * th["amt_rate_high"])
    regular_tax = _num(data.get("regular_tax"))
    amt_due = max(0.0, tmt - regular_tax)
    if amt_adjustment_total > 0:
        checks.append(c.ck(amt_due <= _num(data.get("amt_budget", 0)),
                           f"AMT 交叉：AMTI {amti:,.0f} → TMT {tmt:,.0f}，"
                           f"增量 AMT {amt_due:,.0f}"
                           + (f"（超预算 {amt_due - _num(data.get('amt_budget', 0)):,.0f}）"
                              if amt_due > _num(data.get("amt_budget", 0)) else ""),
                           "amt", "HIGH" if amt_due > _num(data.get("amt_budget", 0))
                           else "OK", amt_due=round(amt_due, 2)))
    return c.result(checks, exercises=rows,
                    amt_adjustment_total=round(amt_adjustment_total, 2),
                    amt_base=round(max(base, 0), 2), tmt=round(tmt, 2),
                    amt_due=round(amt_due, 2),
                    next="AMT 为预付非永久成本，可结转抵免；行权前算交叉点")


# --------------------------------------------------------------------------- #
def _rmd(data: Any) -> Dict[str, Any]:
    """RMD = 上年 12/31 余额 ÷ 除数；漏缴罚 25%（更正窗口内 10%）。"""
    th = c.load_thresholds()["tax"]
    accounts = data.get("accounts", []) or []
    checks: List[Dict[str, Any]] = []
    if not accounts:
        checks.append(c.ck(False, "accounts 为空", "structure", "CRITICAL"))
        return c.result(checks, next="补退休账户余额")
    divisors = {int(k): v for k, v in th["rmd_divisors"].items()}
    rmd_age = th["rmd_age_2033"] if _num(data.get("year", 0)) >= 2033 \
        else th["rmd_age_years"]
    rows: List[Dict[str, Any]] = []
    total_required = total_withdrawn = 0.0
    for i, a in enumerate(accounts):
        label = str(a.get("label", f"acct-{i + 1}"))
        if a.get("roth"):
            rows.append({"label": label, "roth": True, "rmd": 0.0})
            continue
        age = int(_num(a.get("age", rmd_age)))
        bal = _num(a.get("prior_year_dec31_balance"))
        if age < rmd_age:
            rows.append({"label": label, "age": age,
                         "rmd": 0.0,
                         "note": f"未到 {rmd_age} 岁，无 RMD"})
            continue
        # 取不超过当前年龄的最大除数键（表内插值口径：用最接近的已知年龄）
        known = sorted(divisors)
        key = min(known, key=lambda k: (abs(k - age), k))
        divisor = divisors[key]
        rmd = bal / divisor if divisor else 0.0
        withdrawn = _num(a.get("withdrawn_ytd", 0))
        shortfall = max(0.0, rmd - withdrawn)
        excise = shortfall * (th["rmd_excise_corrected_rate"]
                              if a.get("corrected_in_window")
                              else th["rmd_excise_rate"])
        total_required += rmd
        total_withdrawn += withdrawn
        rows.append({"label": label, "age": age, "divisor": divisor,
                     "balance": round(bal, 2), "rmd": round(rmd, 2),
                     "withdrawn": round(withdrawn, 2),
                     "shortfall": round(shortfall, 2),
                     "excise_penalty": round(excise, 2)})
        if shortfall > 0:
            checks.append(c.ck(False,
                               f"{label} RMD 缺口 {shortfall:,.0f}"
                               f"（应提 {rmd:,.0f}，已提 {withdrawn:,.0f}）"
                               f"→ 消费税 {excise:,.0f}",
                               "rmd_shortfall", "CRITICAL",
                               account=label, shortfall=round(shortfall, 2)))
    checks.append(c.ck(total_withdrawn >= total_required,
                       f"RMD 合计：应提 {total_required:,.0f} / "
                       f"已提 {total_withdrawn:,.0f}", "rmd_total",
                       "CRITICAL" if total_withdrawn < total_required
                       else "OK"))
    return c.result(checks, rmd_age=rmd_age, accounts=rows,
                    total_required=round(total_required, 2),
                    total_withdrawn=round(total_withdrawn, 2),
                    next="缺口年底前补提；超额可再投资或 QCD")


# --------------------------------------------------------------------------- #
def _safeharbor(data: Any) -> Dict[str, Any]:
    """预估税安全港：90% 当年税 或 100%/110% 上年税；补充预扣 22%/37%。"""
    th = c.load_thresholds()["tax"]
    current_tax = _num(data.get("current_year_tax"))
    prior_tax = _num(data.get("prior_year_tax"))
    agi = _num(data.get("prior_year_agi", prior_tax))
    paid = _num(data.get("withholding_and_estimates_paid"))
    checks: List[Dict[str, Any]] = []
    prior_pct = (th["safe_harbor_prior_high_agi_pct"]
                 if agi > th["high_agi_threshold"]
                 else th["safe_harbor_prior_pct"])
    target = min(th["safe_harbor_current_pct"] * current_tax,
                 prior_pct * prior_tax)
    gap = target - paid
    checks.append(c.ck(gap <= 0,
                       f"安全港目标 {target:,.0f}"
                       f"（90% 当年 {th['safe_harbor_current_pct'] * current_tax:,.0f}"
                       f" vs 上年 {prior_pct * 100:.0f}% {prior_pct * prior_tax:,.0f}）"
                       f"；已缴 {paid:,.0f}"
                       + (f"，缺口 {gap:,.0f}" if gap > 0 else ""),
                       "safe_harbor", "CRITICAL" if gap > 0 else "OK",
                       gap=round(gap, 2)))
    # RSU/补充工资预扣缺口
    rsus = data.get("rsu_vests", []) or []
    shortfall_total = 0.0
    for i, r in enumerate(rsus):
        income = _num(r.get("shares")) * _num(r.get("vest_fmv"))
        marginal = _num(r.get("marginal_rate", 0.32))
        rate = (th["supplemental_rate_over_1m"]
                if income > th["supplemental_threshold"]
                else th["supplemental_rate"])
        withheld = income * rate
        need = income * marginal
        shortfall = need - withheld
        if shortfall > 0:
            shortfall_total += shortfall
            checks.append(c.ck(False,
                               f"RSU 归属 #{i + 1} 收入 {income:,.0f}：预扣 "
                               f"{rate * 100:.0f}% = {withheld:,.0f}，"
                               f"边际 {marginal * 100:.0f}% 需 {need:,.0f}，"
                               f"缺口 {shortfall:,.0f}",
                               "rsu_gap", "HIGH", vest=i + 1,
                               shortfall=round(shortfall, 2)))
    if rsus and shortfall_total == 0:
        checks.append(c.ck(True, f"RSU 预扣无缺口（{len(rsus)} 笔归属）",
                           "rsu_gap", "OK"))
    return c.result(checks, safe_harbor_target=round(target, 2),
                    rsu_shortfall_total=round(shortfall_total, 2),
                    next="缺口进季度预估缴款，避免少缴罚金")

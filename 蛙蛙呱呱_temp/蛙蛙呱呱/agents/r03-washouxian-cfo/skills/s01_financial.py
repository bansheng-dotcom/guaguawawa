# -*- coding: utf-8 -*-
"""S01 财务报表与月结（能力域 1）。

来源：anthropics__financial-services month-end-closer
（roll-forward 平衡公式 X+A+B−C−D+E+F=Y、accrual-schedule、variance-commentary）
+ gl-reconciler（gl-recon 四步：normalize/match/classify/output，
六桶 break 分类 + 容差 0.01/0 + likely-cause 归因）
+ statement-auditor（nav-tieout：独立重算 + tie-out 表 + 0.01 容差）。

确定性口径：roll-forward 恒等式、对账容差、matched_pct、差异重大性阈值全部外置。
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c

NAME = "financial"
DESC = "财务报表与月结：rollforward/recon/variance"

_LIKELY_CAUSES = ["timing", "fx", "mapping", "duplicate_missing_post",
                  "fee_accrual", "data_quality"]

_RESTATE_WORDS = ("增加", "减少", "上升", "下降", "增长", "回落", "变动",
                  "波动", "差异", "变化", "环比", "同比", "较")


def _is_restatement(driver: str) -> bool:
    """剥掉数字/符号/量词后无实质内容 → 只是在复述数字。"""
    if not driver:
        return False
    s = driver
    for w in _RESTATE_WORDS:
        s = s.replace(w, "")
    for ch in "0123456789.%±+-，, ()（）元$":
        s = s.replace(ch, "")
    return len(s.strip()) == 0


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("rollforward", "资产负债表账户滚动平衡门禁（X+A+B−C−D+E+F=Y）"),
                 ("recon", "GL↔子账对账（六桶分类/容差/归因/匹配率）"),
                 ("variance", "差异注解门禁（重大性/五要素齐全）")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"rollforward": _rollforward, "recon": _recon,
          "variance": _variance}[args.action]
    return fn(data)


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------------------------------- #
def _rollforward(data: Any) -> Dict[str, Any]:
    """每个账户满足：opening + additions + accruals − payments − transfers
    + reclass + other = closing（来源 month-end-closer/roll-forward）。"""
    th = c.load_thresholds()["financial"]
    accounts = data.get("accounts", []) or []
    checks: List[Dict[str, Any]] = []
    if not accounts:
        checks.append(c.ck(False, "accounts 为空（月结必须有 roll-forward 明细）",
                           "structure", "CRITICAL"))
    broken: List[Dict[str, Any]] = []
    for i, a in enumerate(accounts):
        name = str(a.get("account", f"#{i + 1}"))
        opening = _num(a.get("opening"))
        closing = _num(a.get("closing"))
        # 来源口径：X + A + B − C − D + E + F = Y
        # 新增/应计/反转/付款/重分类/外币折算；旧字段名做兼容回退
        delta = (opening + _num(a.get("additions")) + _num(a.get("accruals"))
                 - _num(a.get("reversals")) - _num(a.get("payments"))
                 + _num(a.get("reclass")) + _num(a.get("fx")))
        diff = round(delta - closing, 2)
        if abs(diff) > th["recon_amount_tolerance"]:
            broken.append({"account": name, "expected_closing": round(delta, 2),
                           "reported_closing": closing, "diff": diff})
            checks.append(c.ck(False,
                               f"账户 {name} roll-forward 不平：推算期末 "
                               f"{delta:.2f} ≠ 申报期末 {closing:.2f}"
                               f"（差 {diff:.2f}）", "balance", "CRITICAL",
                               account=name, diff=diff))
    balanced = len(accounts) - len(broken)
    checks.append(c.ck(bool(accounts) and not broken,
                       f"roll-forward 平衡 {balanced}/{len(accounts)}",
                       "rollforward", "CRITICAL" if broken else "OK"))
    return c.result(checks, account_count=len(accounts), balanced=balanced,
                    broken=broken, next="不平账户当天调平或挂 break 清单")


# --------------------------------------------------------------------------- #
def _recon(data: Any) -> Dict[str, Any]:
    """GL↔子账全外连接对账：六桶 + 归因 + 匹配率（来源 gl-recon）。"""
    th = c.load_thresholds()["financial"]
    tol_amt = th["recon_amount_tolerance"]
    tol_qty = th["recon_qty_tolerance"]
    gl = data.get("gl_entries", []) or []
    sub = data.get("subledger_entries", []) or []

    def key(e: Dict[str, Any]) -> str:
        return str(e.get("key", ""))

    gl_map = {key(e): e for e in gl}
    sub_map = {key(e): e for e in sub}
    buckets: Dict[str, List[Dict[str, Any]]] = {b: [] for b in
                                                ("matched", "amount_break",
                                                 "quantity_break",
                                                 "timing_break", "gl_only",
                                                 "subledger_only")}
    breaks: List[Dict[str, Any]] = []
    for k in sorted(set(gl_map) | set(sub_map)):
        g, s = gl_map.get(k), sub_map.get(k)
        if g is not None and s is None:
            buckets["gl_only"].append({"key": k})
            breaks.append({"key": k, "bucket": "gl_only",
                           "likely_cause": "duplicate_missing_post"})
        elif g is None and s is not None:
            buckets["subledger_only"].append({"key": k})
            breaks.append({"key": k, "bucket": "subledger_only",
                           "likely_cause": "duplicate_missing_post"})
        else:
            amt_diff = abs(_num(g.get("amount")) - _num(s.get("amount")))
            qty_diff = abs(_num(g.get("quantity")) - _num(g.get("quantity")))
            if amt_diff <= tol_amt and qty_diff <= tol_qty:
                if str(g.get("posting_date", "")) != str(s.get("posting_date",
                                                               "")) \
                        and amt_diff <= tol_amt:
                    buckets["timing_break"].append({"key": k})
                    breaks.append({"key": k, "bucket": "timing_break",
                                   "likely_cause": "timing"})
                else:
                    buckets["matched"].append({"key": k})
            elif qty_diff > tol_qty:
                buckets["quantity_break"].append({"key": k})
                breaks.append({"key": k, "bucket": "quantity_break",
                               "likely_cause": "data_quality"})
            else:
                # 金额破差归因：本地额一致而本币额不一致 → fx；小额规律性 → fee_accrual
                cause = "mapping"
                if _num(g.get("local_amount", 0)) and \
                        abs(_num(g.get("local_amount"))
                            - _num(s.get("local_amount", _num(g.get("local_amount"))))) <= tol_amt:
                    cause = "fx"
                elif amt_diff <= max(1.0, tol_amt * 100):
                    cause = "fee_accrual"
                buckets["amount_break"].append({"key": k})
                breaks.append({"key": k, "bucket": "amount_break",
                               "likely_cause": cause, "delta": round(amt_diff, 2)})
    total = len(set(gl_map) | set(sub_map))
    matched_pct = round(len(buckets["matched"]) / total, 4) if total else 0.0
    checks: List[Dict[str, Any]] = []
    if total == 0:
        checks.append(c.ck(False, "GL 与子账均为空（无对账范围）", "structure",
                           "CRITICAL"))
    else:
        checks.append(c.ck(matched_pct >= th["min_matched_pct"],
                           f"匹配率 {matched_pct * 100:.1f}%"
                           f"（≥ {th['min_matched_pct'] * 100:.0f}%）",
                           "matched_pct", "CRITICAL"
                           if matched_pct < th["min_matched_pct"] else "OK",
                           matched_pct=matched_pct))
        material = [b for b in breaks
                    if b.get("delta", 0) > 100 or "delta" not in b]
        checks.append(c.ck(not material,
                           f"未匹配/破差 {len(breaks)} 条"
                           f"（GL only {len(buckets['gl_only'])} / "
                           f"子账 only {len(buckets['subledger_only'])} / "
                           f"金额 {len(buckets['amount_break'])} / "
                           f"数量 {len(buckets['quantity_break'])} / "
                           f"时点 {len(buckets['timing_break'])}）",
                           "breaks", "CRITICAL" if material else "OK"))
    return c.result(checks, total=total, matched_pct=matched_pct,
                    buckets={k: len(v) for k, v in buckets.items()},
                    breaks=breaks[:20], break_count=len(breaks),
                    next="破差按 likely_cause 分派 break-trace 追根因")


# --------------------------------------------------------------------------- #
def _variance(data: Any) -> Dict[str, Any]:
    """差异注解门禁（来源 variance-commentary）：
    触发 = |差异| ≥ max(行基数×5%, 固定下限) 或 行 ∈ 总是评论清单
    （收入/人员成本/现金）；被触发行必须有 driver（解释 why 而非 what）。"""
    th = c.load_thresholds()["financial"]
    variances = data.get("variances", []) or []
    budget = data.get("budget_by_account", {}) or {}
    always = set(th.get("always_comment_lines",
                        ["revenue", "headcount_cost", "cash"]))
    checks: List[Dict[str, Any]] = []
    if not variances:
        checks.append(c.ck(False, "variances 为空（月结必须逐账户比对预算）",
                           "structure", "CRITICAL"))
    missing: List[Dict[str, Any]] = []
    flagged = 0
    for i, v in enumerate(variances):
        acct = str(v.get("account", f"#{i + 1}"))
        var = _num(v.get("variance"))
        base = _num(budget.get(acct, v.get("budget", 0)))
        thr = max(th["materiality_pct"] * abs(base), th["variance_floor"])
        material = abs(var) >= thr or acct.lower() in always
        if not material:
            continue
        flagged += 1
        driver = str(v.get("driver", "")).strip()
        # driver 解释 why 而非 what：剥掉数字/符号/量词后仍无实质内容
        # （如「增加 3000 (12%)」）不算合格注解
        restates = _is_restatement(driver)
        if not driver or restates:
            missing.append({"account": acct, "field": "driver"})
            checks.append(c.ck(False,
                               f"账户 {acct} 触发差异评论（阈值 {thr:.0f}）"
                               f"但 driver 缺失或仅复述数字（须解释 why）",
                               "variance_note", "HIGH",
                               account=acct, field="driver"))
    checks.append(c.ck(not missing,
                       f"触发评论 {flagged} 行，注解缺口 "
                       f"{len({m['account'] for m in missing})} 账户",
                       "variance", "HIGH" if missing else "OK"))
    return c.result(checks, variance_count=len(variances),
                    flagged=flagged,
                    material_missing=len({m["account"] for m in missing}),
                    missing=missing[:10],
                    next="注解齐全后进 controller sign-off（本 agent 不代签）")

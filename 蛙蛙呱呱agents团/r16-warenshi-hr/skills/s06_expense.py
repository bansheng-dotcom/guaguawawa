# -*- coding: utf-8 -*-
"""S06 费用与福利业务 —— 能力域 6。

整合自 frappe__hrms：`hr/doctype/expense_claim/expense_claim.json`
（approval_status = Draft | Approved | Rejected | Cancelled；
status = Draft | Paid | Partially Paid | Unpaid | Rejected | Submitted |
Cancelled；expense_details 明细）、`hr/doctype/employee_benefit_application/
employee_benefit_application.json`（绑定 payroll_period + 福利额度）。
把「报销单 → 审批 → 福利申领」转成确定性校验：必填、金额正数、明细非空、
审批状态白名单、福利不超上限、报销金额=明细求和。

关键立场：**报销是费用凭证，不是付款指令**。本角色校验报销单与福利申领的
**合法性与一致性**，绝不代付、绝不打款（红线 1）；金额求和恒等与福利上限是
L4 幻觉防护的延伸——「看起来合理的数字」必须能被明细逐笔印证。

动作：
  claim     报销单校验（明细 + 金额恒等 + 审批状态）
  benefit   福利申领校验（周期绑定 + 额度上限）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "expense"
DESC = "费用与福利：claim/benefit"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("claim", "校验报销单"), ("benefit", "校验福利申领")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "claim":
        return _validate_claim(data)
    if args.action == "benefit":
        return _validate_benefit(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_claim(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["expense"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", claim_count=0)

    emp = str(data.get("employee", "")).strip()
    checks.append(_ck(bool(emp), "报销关联人员非空", "claim.employee"))

    approval = data.get("approval_status")
    checks.append(_ck(approval in th["approval_statuses"],
                      f"审批状态={approval!r} 在白名单", "claim.approval_status"))

    status = data.get("status")
    checks.append(_ck(status in th["statuses"],
                      f"单据状态={status!r} 在白名单", "claim.status"))

    details = data.get("expense_details") or []
    ok_details = isinstance(details, list) and len(details) > 0
    checks.append(_ck(ok_details,
                      f"报销明细 ≥1（实际 "
                      f"{len(details) if isinstance(details, list) else 0}）",
                      "claim.details"))

    # 明细逐项金额须 > 0
    bad_amt: List[str] = []
    for d in details if isinstance(details, list) else []:
        if not isinstance(d, dict):
            continue
        if c.money(d.get("amount")) <= 0:
            bad_amt.append(str(d.get("expense_type", "?")))
    checks.append(_ck(not bad_amt,
                      f"明细金额均 > 0（异常 {bad_amt or '无'}）",
                      "claim.detail_amount"))

    # 金额恒等：总额 = Σ明细
    detail_sum = round(sum(c.money(d.get("amount")) for d in details
                           if isinstance(d, dict)), 2)
    total = c.money(data.get("total_claimed_amount"))
    checks.append(_ck(abs(total - detail_sum) <= 0.01,
                      f"报销金额恒等：总额 {total:g} = 明细和 {detail_sum:g}",
                      "claim.total"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        claim_count=1, total_amount=total, approval_status=approval,
        narrative=(f"报销 {emp}（{approval}）合计 {total:g}"
                   "（凭证，非付款指令）"))


# --------------------------------------------------------------------------- #
def _validate_benefit(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", benefit_count=0)

    emp = str(data.get("employee", "")).strip()
    checks.append(_ck(bool(emp), "福利关联人员非空", "benefit.employee"))

    period = str(data.get("payroll_period", "")).strip()
    checks.append(_ck(bool(period), "福利绑定薪酬周期", "benefit.period"))

    benefit_type = str(data.get("benefit", "")).strip()
    checks.append(_ck(bool(benefit_type), "福利类型非空", "benefit.type"))

    # 额度不超上限（金额 > 0 且 ≤ 上限）
    amount = c.money(data.get("amount"))
    checks.append(_ck(amount > 0, f"福利金额 {amount:g} > 0", "benefit.amount"))
    if data.get("max_amount") is not None:
        cap = c.money(data.get("max_amount"))
        checks.append(_ck(amount <= cap,
                          f"福利 {amount:g} ≤ 上限 {cap:g}", "benefit.cap"))
    else:
        checks.append(_ck(True, "未提供上限，跳过额度检查", "benefit.cap"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        benefit_count=1, amount=amount, payroll_period=period,
        narrative=f"福利 {emp}（{benefit_type}）{amount:g} 周期 {period}")

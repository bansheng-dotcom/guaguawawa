# -*- coding: utf-8 -*-
"""S05 ERP 财务业务接口 —— 能力域 5。

整合自 frappe__erpnext 的 accounts 模块：
  - `accounts/doctype/sales_invoice/`（status: Draft/Return/Credit Note Issued/
    Submitted/Paid/Partly Paid/Unpaid/Overdue/Cancelled）
  - `accounts/doctype/purchase_invoice/`（同上状态集）
  - `accounts/doctype/payment_entry/`（status: Draft/Submitted/Cancelled +
    party/paid_amount/paid_to）

关键立场：**财务业务接口只登记「已发生的应收应付」，不代做财务结论、不代付
款**。发票必须能复算（total == Σ qty×rate），付款单必须有对方 + 金额 + 收款账户。
税务结论 / 财务报表口径归 R03（蛙守线）；本角色只做业务凭证的确定性门禁。

动作：
  invoice   销售/采购发票校验（状态 + 金额恒等式）
  payment   付款单校验（不代付款，只做凭证门禁）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "finance"
DESC = "ERP财务业务接口：invoice/payment"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("invoice", help="校验销售/采购发票")
    a.add_argument("--input", required=True)
    b = act.add_parser("payment", help="校验付款单凭证")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"invoice": _validate_invoice, "payment": _validate_payment}.get(args.action)
    if fn is None:
        return {"error": f"未知动作: {args.action}"}
    return fn(data)


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _inv_total(items: List[Any]) -> float:
    return round(sum(c.money(i.get("qty")) * c.money(i.get("rate"))
                     for i in items if isinstance(i, dict)), 2)


# --------------------------------------------------------------------------- #
def _validate_invoice(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["finance"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", invoice_count=0)

    kind = data.get("kind")
    checks.append(_ck(kind in ("sales", "purchase"),
                      f"发票类型={kind!r} 在 {['sales', 'purchase']}",
                      "invoice.kind"))

    missing = [k for k in th["invoice_required"] if not data.get(k)]
    checks.append(_ck(not missing, f"发票必填齐备（缺 {missing or '无'}）",
                      "invoice.required"))

    status = data.get("status")
    checks.append(_ck(status in th["invoice_status"],
                      f"发票状态={status!r} 在白名单", "invoice.status"))

    items = data.get("line_items") or []
    if not isinstance(items, list) or not items:
        checks.append(_ck(False, "发票行项目必须非空", "invoice.line_items"))
        items = []
    else:
        checks.append(_ck(True, f"发票行项目 {len(items)} 条", "invoice.line_items"))

    bad_line = [i.get("item_code") for i in items if isinstance(i, dict)
                and any(not str(i.get(k, "")).strip()
                        for k in th["invoice_line_required"])]
    checks.append(_ck(not bad_line, f"发票行项目必填齐备（缺 {bad_line or '无'}）",
                      "invoice.line_required"))

    total = _inv_total(items)
    declared = c.money(data.get("total"))
    checks.append(_ck(abs(declared - total) < th["reconcile_tolerance"],
                      f"发票恒等式：声明 {declared} = Σ(qty×rate) {total}",
                      "invoice.total"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        invoice_count=1, total=total, line_item_count=len(items),
        narrative=(f"{kind or '?'} 发票 {data.get('id', '?')}（{data.get('party', '?')}）："
                   f"{status}、{len(items)} 行、合计 {total}"))


# --------------------------------------------------------------------------- #
def _validate_payment(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["finance"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", payment_count=0)

    missing = [k for k in th["payment_required"] if not data.get(k)]
    checks.append(_ck(not missing, f"付款单必填齐备（缺 {missing or '无'}）",
                      "payment.required"))

    status = data.get("status")
    checks.append(_ck(status in th["payment_status"],
                      f"付款状态={status!r} 在白名单", "payment.status"))

    paid = c.money(data.get("paid_amount"))
    checks.append(_ck(paid >= th["currency_min"],
                      f"付款金额 {paid} ≥ {th['currency_min']}", "payment.amount"))

    # 红线：本角色不代付款，付款单必须声明授权（handoff/authorized 键）
    authorized = bool(data.get("handoff") or data.get("authorized")
                      or data.get("approved_by"))
    checks.append(_ck(authorized,
                      "付款单声明授权（不擅自付款，凭证需人工授权）",
                      "payment.authorized"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        payment_count=1, paid_amount=paid,
        narrative=(f"付款单 {data.get('id', '?')}（{data.get('party', '?')}）："
                   f"{status}、金额 {paid}、授权={authorized}"))

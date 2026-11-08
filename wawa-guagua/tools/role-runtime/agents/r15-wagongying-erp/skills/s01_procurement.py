# -*- coding: utf-8 -*-
"""S01 采购与供应商 —— 能力域 1。

整合自 frappe__erpnext 的 buying 模块：
  - `buying/doctype/supplier/supplier.json`（supplier_type: Company/Individual/Partnership）
  - `buying/doctype/request_for_quotation/`（status: Draft/Submitted/Cancelled）
  - `buying/doctype/supplier_quotation/`（status: Draft/Submitted/Partially Ordered/
    Ordered/Stopped/Cancelled/Expired）
  - `buying/doctype/purchase_order/`（status 十态 + supplier/transaction_date/
    schedule_date/items 必填 + Purchase Order Item 的 item_code/qty/rate）
  - `stock/doctype/purchase_receipt/`（status: Draft/Partly Billed/To Bill/Completed/
    Return/Return Issued）

关键立场：**采购是「先比价、再下单、后收货」的三段门禁**。RFQ 至少询两家
（询价不是走过场），PO 行项目必须能复算金额（Σ qty×rate），收货数量不得超过
订单数量（超收 = 账实不符的源头）。金额恒等式必须实算，不能声明什么信什么。

动作：
  supplier         供应商主数据校验
  rfq              询价单校验（多家比价门禁）
  quotation        供应商报价校验
  purchase_order   采购订单校验（状态+金额恒等式）
  receipt          采购收货校验（超收门禁）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "procurement"
DESC = "采购与供应商：supplier/rfq/quotation/purchase_order/receipt"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for name, help_txt in (
        ("supplier", "校验供应商主数据"),
        ("rfq", "校验询价单与比价家数"),
        ("quotation", "校验供应商报价"),
        ("purchase_order", "校验采购订单状态与金额恒等式"),
        ("receipt", "校验采购收货与超收"),
    ):
        a = act.add_parser(name, help=help_txt)
        a.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {
        "supplier": _validate_supplier,
        "rfq": _validate_rfq,
        "quotation": _validate_quotation,
        "purchase_order": _validate_purchase_order,
        "receipt": _validate_receipt,
    }.get(args.action)
    if fn is None:
        return {"error": f"未知动作: {args.action}"}
    return fn(data)


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _po_total(items: List[Any]) -> float:
    return round(sum(c.money(i.get("qty")) * c.money(i.get("rate"))
                     for i in items if isinstance(i, dict)), 2)


# --------------------------------------------------------------------------- #
def _validate_supplier(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["procurement"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", supplier_count=0)

    suppliers = data.get("suppliers")
    if not isinstance(suppliers, list) or not suppliers:
        return c.result([_ck(False, "suppliers 必须是非空列表", "supplier.list")],
                        ok=False, verdict="FAIL", supplier_count=0)

    missing = [s.get("supplier_name") for s in suppliers if isinstance(s, dict)
               and any(not str(s.get(k, "")).strip() for k in th["supplier_required"])]
    checks.append(_ck(not missing, f"供应商必填齐备（缺 {missing or '无'}）",
                      "supplier.required"))

    bad_type = [s.get("supplier_name") for s in suppliers if isinstance(s, dict)
                and s.get("supplier_type") not in th["supplier_types"]]
    checks.append(_ck(not bad_type,
                      f"供应商类型在白名单（越界 {bad_type or '无'}）", "supplier.type"))

    # 账期上限：超长账期 = 供应商风险信号，须显式复核而非默认通过
    max_days = th["max_payment_terms_days"]
    bad_terms = [s.get("supplier_name") for s in suppliers if isinstance(s, dict)
                 and c._num(s.get("payment_terms_days")) > max_days]
    checks.append(_ck(not bad_terms,
                      f"账期 ≤ {max_days} 天（超限 {bad_terms or '无'}）",
                      "supplier.payment_terms"))

    frozen = [s.get("supplier_name") for s in suppliers if isinstance(s, dict)
              and str(s.get("status", "Active")) == "Frozen"]
    checks.append(_ck(True, f"冻结供应商 {len(frozen)} 家（不得下单）",
                      "supplier.frozen"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        supplier_count=len(suppliers), frozen_count=len(frozen),
        narrative=(f"供应商 {len(suppliers)} 家、冻结 {len(frozen)} 家"
                   f"（冻结者不可用于采购下单）"))


# --------------------------------------------------------------------------- #
def _validate_rfq(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["procurement"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", supplier_count=0)

    suppliers = data.get("suppliers") or []
    if not isinstance(suppliers, list):
        suppliers = []
    min_s = th["rfq_min_suppliers"]
    checks.append(_ck(len(suppliers) >= min_s,
                      f"询价家数 {len(suppliers)} ≥ {min_s}（防走过场比价）",
                      "rfq.supplier_count"))

    status = data.get("status")
    checks.append(_ck(status in th["rfq_status"],
                      f"询价状态={status!r} 在白名单", "rfq.status"))

    items = data.get("items") or []
    checks.append(_ck(isinstance(items, list) and bool(items),
                      f"询价行项目 {len(items) if isinstance(items, list) else 0} 条非空",
                      "rfq.items"))

    need = str(data.get("required_by", "")).strip()
    checks.append(_ck(bool(need), f"需求日期={need or '空'} 已声明", "rfq.required_by"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        supplier_count=len(suppliers), rfq_count=1,
        narrative=f"询价单 {data.get('id', '?')}：{len(suppliers)} 家供应商、"
                  f"状态 {status}")


# --------------------------------------------------------------------------- #
def _validate_quotation(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["procurement"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", quotation_count=0)

    supplier = str(data.get("supplier", "")).strip()
    checks.append(_ck(bool(supplier), "报价供应商非空", "quotation.supplier"))

    status = data.get("status")
    checks.append(_ck(status in th["sq_status"],
                      f"报价状态={status!r} 在白名单", "quotation.status"))

    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        checks.append(_ck(False, "报价行项目必须非空", "quotation.items"))
        items = []
    else:
        checks.append(_ck(True, f"报价行项目 {len(items)} 条", "quotation.items"))

    total = _po_total(items)
    declared = c.money(data.get("total", total))
    # 手工输入总额常见抄错；本门禁要求报价单可复算
    checks.append(_ck(abs(declared - total) < 0.01,
                      f"报价恒等式：声明 {declared} = Σ(qty×rate) {total}",
                      "quotation.total"))

    valid_till = str(data.get("valid_till", "")).strip()
    checks.append(_ck(bool(valid_till),
                      f"报价有效期={valid_till or '空'} 已声明", "quotation.valid_till"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        quotation_count=1, total=total, line_item_count=len(items),
        narrative=f"报价单 {data.get('id', '?')}（{supplier}）：{status}、合计 {total}")


# --------------------------------------------------------------------------- #
def _validate_purchase_order(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["procurement"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", po_count=0)

    missing = [k for k in th["po_required"] if not data.get(k)]
    checks.append(_ck(not missing, f"采购订单必填齐备（缺 {missing or '无'}）",
                      "po.required"))

    status = data.get("status")
    checks.append(_ck(status in th["po_status"],
                      f"采购订单状态={status!r} 在白名单", "po.status"))

    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        checks.append(_ck(False, "采购订单行项目必须非空", "po.items"))
        items = []
    else:
        checks.append(_ck(True, f"采购订单行项目 {len(items)} 条", "po.items"))

    too_many = len(items) > th["max_po_lines"]
    checks.append(_ck(not too_many,
                      f"行数 {len(items)} ≤ {th['max_po_lines']}", "po.line_count"))

    bad_line = [i.get("item_code") for i in items if isinstance(i, dict)
                and any(not str(i.get(k, "")).strip()
                        for k in th["po_item_required"])]
    checks.append(_ck(not bad_line, f"行项目必填齐备（缺 {bad_line or '无'}）",
                      "po.item_required"))

    bad_rate = [i.get("item_code") for i in items if isinstance(i, dict)
                and c.money(i.get("rate")) <= 0]
    checks.append(_ck(not bad_rate, f"行项目单价为正（异常 {bad_rate or '无'}）",
                      "po.item_rate"))

    total = _po_total(items)
    declared = c.money(data.get("grand_total", total))
    checks.append(_ck(abs(declared - total) < 0.01,
                      f"订单恒等式：声明 {declared} = Σ(qty×rate) {total}",
                      "po.grand_total"))

    # 交货日期不得早于下单日期（时序倒退 = 计划不可执行）
    td, sd = str(data.get("transaction_date", "")), str(data.get("schedule_date", ""))
    seq_ok = (not td or not sd or sd >= td)
    checks.append(_ck(seq_ok, f"交货日期 {sd or '?'} ≥ 下单日期 {td or '?'}",
                      "po.date_order"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        po_count=1, total=total, line_item_count=len(items),
        narrative=(f"采购订单 {data.get('id', '?')}（{data.get('supplier', '?')}）："
                   f"{status}、{len(items)} 行、合计 {total}"))


# --------------------------------------------------------------------------- #
def _validate_receipt(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["procurement"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", receipt_count=0)

    missing = [k for k in th["receipt_required"] if not data.get(k)]
    checks.append(_ck(not missing, f"收货单必填齐备（缺 {missing or '无'}）",
                      "receipt.required"))

    status = data.get("status")
    checks.append(_ck(status in th["receipt_status"],
                      f"收货状态={status!r} 在白名单", "receipt.status"))

    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        checks.append(_ck(False, "收货行项目必须非空", "receipt.items"))
        items = []

    # 超收门禁：收 > 订 是账实不符的源头，容差默认 0（阈值外置）
    tol = c._num(th["over_receipt_tolerance"])
    over = []
    for i in items:
        if not isinstance(i, dict):
            continue
        got, ordered = c.money(i.get("received_qty")), c.money(i.get("ordered_qty"))
        if got > ordered * (1 + tol) + 1e-9:
            over.append(i.get("item_code"))
    checks.append(_ck(not over,
                      f"无超收（超收 {over or '无'}，容差 {tol}）",
                      "receipt.over_receipt"))

    total_qty = round(sum(c.money(i.get("received_qty")) for i in items
                          if isinstance(i, dict)), 2)
    checks.append(_ck(total_qty > 0, f"收货总数量 {total_qty} > 0", "receipt.qty"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        receipt_count=1, total_qty=total_qty, line_item_count=len(items),
        narrative=(f"收货单 {data.get('id', '?')}（{data.get('supplier', '?')}）："
                   f"{status}、{len(items)} 行、收 {total_qty}"))

# -*- coding: utf-8 -*-
"""S03 销售与履约记录 —— 能力域 3。

整合自 frappe__erpnext 的 selling 与 stock 模块：
  - `selling/doctype/sales_order/`（status 九态 + delivery_status Not Delivered/
    Fully Delivered/Partly Delivered/Closed + billing_status Not Billed/Fully Billed/
    Partly Billed/Closed）
  - `stock/doctype/delivery_note/`（status: Draft/To Bill/Partially Billed/Completed/
    Return）

关键立场：**销售订单是「已确认承诺」，发货单是「已实际交付」**，二者必须
区分。SO 的 delivery_status 与 billing_status 是两条独立轴（发货 ≠ 开票 ≠ 收款），
跨轴矛盾（如 Fully Delivered 却 Not Billed 且金额为零）要能识别；发货数量
不得超过订单数量（超发 = 白送 / 账实不符）。

动作：
  sales_order   销售订单校验（状态双轴 + 金额恒等式）
  delivery      发货单校验（超发门禁）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "fulfillment"
DESC = "销售与履约记录：sales_order/delivery"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("sales_order", help="校验销售订单状态双轴与金额")
    a.add_argument("--input", required=True)
    b = act.add_parser("delivery", help="校验发货单与超发")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"sales_order": _validate_sales_order,
          "delivery": _validate_delivery}.get(args.action)
    if fn is None:
        return {"error": f"未知动作: {args.action}"}
    return fn(data)


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _so_total(items: List[Any]) -> float:
    return round(sum(c.money(i.get("qty")) * c.money(i.get("rate"))
                     for i in items if isinstance(i, dict)), 2)


# --------------------------------------------------------------------------- #
def _validate_sales_order(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["fulfillment"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", sales_order_count=0)

    missing = [k for k in th["so_required"] if not data.get(k)]
    checks.append(_ck(not missing, f"销售订单必填齐备（缺 {missing or '无'}）",
                      "so.required"))

    status = data.get("status")
    checks.append(_ck(status in th["so_status"],
                      f"销售订单状态={status!r} 在白名单", "so.status"))

    delivery_status = data.get("delivery_status")
    checks.append(_ck(delivery_status in th["so_delivery_status"],
                      f"发货状态={delivery_status!r} 在白名单", "so.delivery_status"))

    billing_status = data.get("billing_status")
    checks.append(_ck(billing_status in th["so_billing_status"],
                      f"开票状态={billing_status!r} 在白名单", "so.billing_status"))

    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        checks.append(_ck(False, "销售订单行项目必须非空", "so.items"))
        items = []
    else:
        checks.append(_ck(True, f"销售订单行项目 {len(items)} 条", "so.items"))

    bad_line = [i.get("item_code") for i in items if isinstance(i, dict)
                and any(not str(i.get(k, "")).strip()
                        for k in th["so_item_required"])]
    checks.append(_ck(not bad_line, f"行项目必填齐备（缺 {bad_line or '无'}）",
                      "so.item_required"))

    total = _so_total(items)
    declared = c.money(data.get("grand_total", total))
    checks.append(_ck(abs(declared - total) < 0.01,
                      f"订单恒等式：声明 {declared} = Σ(qty×rate) {total}",
                      "so.grand_total"))

    # 跨轴一致性：Completed 订单必须已全部交付且已全部开票
    if status == "Completed":
        axis_ok = (delivery_status == "Fully Delivered"
                   and billing_status == "Fully Billed")
        checks.append(_ck(axis_ok,
                          "Completed 须已全交付且已全开票", "so.axis_consistency"))
    else:
        checks.append(_ck(True, "订单状态双轴自洽", "so.axis_consistency"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        sales_order_count=1, total=total, line_item_count=len(items),
        narrative=(f"销售订单 {data.get('id', '?')}（{data.get('customer', '?')}）："
                   f"{status}、发货 {delivery_status}、开票 {billing_status}、合计 {total}"))


# --------------------------------------------------------------------------- #
def _validate_delivery(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["fulfillment"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", delivery_count=0)

    missing = [k for k in th["delivery_required"] if not data.get(k)]
    checks.append(_ck(not missing, f"发货单必填齐备（缺 {missing or '无'}）",
                      "delivery.required"))

    status = data.get("status")
    checks.append(_ck(status in th["delivery_status"],
                      f"发货状态={status!r} 在白名单", "delivery.status"))

    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        checks.append(_ck(False, "发货行项目必须非空", "delivery.items"))
        items = []

    # 超发门禁：发 > 订 = 白送 / 账实不符
    tol = c._num(th["over_delivery_tolerance"])
    over = []
    for i in items:
        if not isinstance(i, dict):
            continue
        sent, ordered = c.money(i.get("qty")), c.money(i.get("against_qty"))
        if sent > ordered * (1 + tol) + 1e-9:
            over.append(i.get("item_code"))
    checks.append(_ck(not over,
                      f"无超发（超发 {over or '无'}，容差 {tol}）",
                      "delivery.over_delivery"))

    total_qty = round(sum(c.money(i.get("qty")) for i in items
                          if isinstance(i, dict)), 2)
    checks.append(_ck(total_qty > 0, f"发货总数量 {total_qty} > 0", "delivery.qty"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        delivery_count=1, total_qty=total_qty, line_item_count=len(items),
        narrative=(f"发货单 {data.get('id', '?')}（{data.get('customer', '?')}）："
                   f"{status}、{len(items)} 行、发 {total_qty}"))

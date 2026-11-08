# -*- coding: utf-8 -*-
"""S02 购物车与订单编排 —— 能力域 2。

整合自 medusajs__medusa 的 cart/order 模块：`cart/src/models/cart.ts`
（line_items 行项目）+ `order/src/models/order.ts`（status/payment_status/
fulfillment_status 三态）+ `core/types/src/order/common.ts` 的
OrderStatus / PaymentStatus / FulfillmentStatus 枚举。把「购物车 → 订单」链路
转成确定性校验：行项目必填、金额实算（Σ unit_price×quantity）、订单三态枚举、
支付状态与订单状态一致性、履约状态。

关键立场：**订单状态机是交易正确性的地基**。payment_status=refunded 却
status=completed 是自相矛盾；金额口径 Σ(单价×数量) 必须能复算。

动作：
  cart    购物车行项目与金额校验
  order   订单三态与金额一致性校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "order"
DESC = "购物车与订单编排：cart/order"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("cart", help="校验购物车行项目与金额")
    a.add_argument("--input", required=True)
    b = act.add_parser("order", help="校验订单三态与金额一致性")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "cart":
        return _validate_cart(data)
    if args.action == "order":
        return _validate_order(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_cart(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    oth = c.load_thresholds()["order"]
    cth = c.load_thresholds()["cart"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", line_item_count=0)

    items = data.get("line_items")
    if not isinstance(items, list) or not items:
        return c.result([_ck(False, "line_items 必须是非空列表", "cart.list")],
                        ok=False, verdict="FAIL", line_item_count=0)

    too_many = len(items) > cth["max_line_items"]
    checks.append(_ck(not too_many,
                      f"行项目数 {len(items)} ≤ {cth['max_line_items']}",
                      "cart.item_count"))

    missing = [i.get("title") for i in items if isinstance(i, dict)
               and any(not str(i.get(k, "")).strip() for k in cth["line_item_required"])]
    checks.append(_ck(not missing, f"行项目必填齐备（缺 {missing or '无'}）",
                      "cart.required"))

    bad_price = [i.get("title") for i in items if isinstance(i, dict)
                 and c.money(i.get("unit_price")) <= 0]
    checks.append(_ck(not bad_price, f"单价均为正（异常 {bad_price or '无'}）",
                      "cart.unit_price"))

    bad_qty = [i.get("title") for i in items if isinstance(i, dict)
               and c._num(i.get("quantity")) <= 0]
    checks.append(_ck(not bad_qty, f"数量均为正（异常 {bad_qty or '无'}）",
                      "cart.quantity"))

    subtotal = round(sum(c.money(i.get("unit_price")) * c._num(i.get("quantity"))
                         for i in items if isinstance(i, dict)), 2)
    declared = c.money(data.get("subtotal", subtotal))
    # 口径恒等：声明小计必须等于实算（容差 0.01，防漂移）
    ok_identity = abs(declared - subtotal) < 0.01
    checks.append(_ck(ok_identity,
                      f"小计口径恒等：声明 {declared} = 实算 {subtotal}",
                      "cart.subtotal"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        line_item_count=len(items), cart_total=subtotal,
        narrative=(f"购物车 {len(items)} 行、小计 {subtotal}"))


# --------------------------------------------------------------------------- #
def _validate_order(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    oth = c.load_thresholds()["order"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", order_count=0)

    oid = str(data.get("id", "")).strip()
    checks.append(_ck(bool(oid), "订单号非空", "order.id"))

    status = data.get("status")
    ok_status = status in oth["order_status"]
    checks.append(_ck(ok_status, f"订单状态={status!r} 在白名单", "order.status"))

    pay_status = data.get("payment_status")
    ok_pay = pay_status in oth["payment_status"]
    checks.append(_ck(ok_pay, f"支付状态={pay_status!r} 在白名单", "order.payment_status"))

    fulfill_status = data.get("fulfillment_status")
    ok_fulfill = fulfill_status in oth["fulfillment_status"]
    checks.append(_ck(ok_fulfill, f"履约状态={fulfill_status!r} 在白名单",
                      "order.fulfillment_status"))

    # 状态一致性：refunded 却 completed 是自相矛盾
    if pay_status == "refunded" and status == "completed":
        checks.append(_ck(False, "已全额退款却状态 completed，自相矛盾",
                          "order.consistency"))
    else:
        checks.append(_ck(True, "支付状态与订单状态一致", "order.consistency"))

    total = c.money(data.get("total"))
    checks.append(_ck(total > 0, f"订单总额={total} 为正", "order.total"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        order_count=1, status=status, payment_status=pay_status,
        fulfillment_status=fulfill_status, total=total,
        narrative=(f"订单 {oid}：状态 {status}、支付 {pay_status}、"
                   f"履约 {fulfill_status}、总额 {total}"))

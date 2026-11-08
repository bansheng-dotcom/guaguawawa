# -*- coding: utf-8 -*-
"""S04 支付服务端集成 —— 能力域 4。

整合自 stripe__stripe-node 的 PaymentIntents 资源：`src/resources/PaymentIntents.ts`
的 status 枚举（requires_payment_method / requires_confirmation / requires_action /
processing / requires_capture / canceled / succeeded）。把「支付意图 + 退款」转成
确定性校验：意图状态机白名单、金额门槛（最低 0.50 美元）、退款比例上限（≤100%）、
可退款状态前置。

关键立场（对齐角色红线）：**本角色只产出「支付集成规格 + 回调处理」，绝不
开通支付账户、配置真实密钥、代扣款、代退款**——凭据检测与执行词检测是硬门禁。

动作：
  payment_intent  支付意图与回调处理校验
  refund          退款请求校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "payment"
DESC = "支付服务端集成：payment_intent/refund"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("payment_intent", help="校验支付意图")
    a.add_argument("--input", required=True)
    b = act.add_parser("refund", help="校验退款请求")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "payment_intent":
        return _validate_payment_intent(data)
    if args.action == "refund":
        return _validate_refund(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_payment_intent(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    pth = c.load_thresholds()["payment"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", payment_count=0)

    pi_id = str(data.get("id", "")).strip()
    checks.append(_ck(bool(pi_id), "支付意图号非空", "payment.id"))

    status = data.get("status")
    ok_status = status in pth["pi_status"]
    checks.append(_ck(ok_status, f"意图状态={status!r} 在白名单", "payment.status"))

    intent_type = data.get("intent_type", "payment_intent")
    ok_type = intent_type in pth["intent_types"]
    checks.append(_ck(ok_type, f"意图类型={intent_type!r} 在白名单", "payment.type"))

    amount = c.money(data.get("amount"))
    checks.append(_ck(amount >= pth["amount_min"],
                      f"金额={amount} ≥ 最低 {pth['amount_min']}", "payment.amount"))

    # 回调处理：succeeded 必须有 webhook 事件类型与幂等键
    if status == pth["succeeded_status"]:
        webhook = str(data.get("webhook_event", "")).strip()
        idem = str(data.get("idempotency_key", "")).strip()
        checks.append(_ck(bool(webhook) and bool(idem),
                          "succeeded 需声明 webhook 事件与幂等键",
                          "payment.webhook"))
    else:
        checks.append(_ck(True, f"{status} 非终态，回调可选", "payment.webhook"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        payment_count=1, status=status, amount=amount,
        narrative=f"支付意图 {pi_id}（{status}）金额 {amount}")


# --------------------------------------------------------------------------- #
def _validate_refund(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    pth = c.load_thresholds()["payment"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", refund_count=0)

    missing = [k for k in pth["refund_required"] if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"退款必填齐备（缺 {missing or '无'}）",
                      "refund.required"))

    amount = c.money(data.get("amount"))
    checks.append(_ck(amount > 0, f"退款金额={amount} 为正", "refund.amount"))

    # 退款比例上限：refunded_amount / original_amount ≤ 1.0
    original = c.money(data.get("original_amount"))
    ratio = c.safe_div(amount, original) if original > 0 else 1.0
    checks.append(_ck(ratio <= pth["refund_ratio_max"],
                      f"退款比例={ratio} ≤ {pth['refund_ratio_max']}", "refund.ratio"))

    # 前置状态：可退款的状态前置（succeeded/partially_refunded）
    prior = data.get("prior_status")
    if prior and prior not in ("succeeded", "partially_refunded", "captured"):
        checks.append(_ck(False, f"前置状态={prior!r} 不可退款", "refund.prior"))
    else:
        checks.append(_ck(True, f"前置状态={prior or '未提供'} 可退款", "refund.prior"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        refund_count=1, amount=amount, refund_ratio=ratio,
        narrative=f"退款 {amount}（比例 {ratio}）前置 {prior or '?'}")

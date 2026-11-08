# -*- coding: utf-8 -*-
"""S08 收入数据接口与交易自动化 —— 能力域 8。

整合自五个来源的交易事件口径：Medusa 订单事件、Lago 账单事件、Stripe 支付/退款
事件、Documenso 签署完成事件、EasyAppointments 预约事件。把「向 R06/R18 提供收入
数据口径」与「向 R17 提供自动化需求」落成确定性校验：事件类型白名单、必填三要素、
金额非负、事件排序单调。

关键立场：**收入数据接口是 R06/R18 的输入地基**。事件缺 entity_id 或 amount
会让下游分析无从对账；事件时序倒挂会让「收入口径」失真。R17 自动化由 R17 实现，
本角色只产事件表与回调需求（与 R13 的 automation 需求卡同源）。

动作：
  events     交易事件表校验（收入数据接口）
  webhook    回调/重试/对账需求校验（交易自动化接口）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "revenue"
DESC = "收入数据接口与交易自动化：events/webhook"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("events", help="校验交易事件表")
    a.add_argument("--input", required=True)
    b = act.add_parser("webhook", help="校验回调/重试/对账需求")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "events":
        return _validate_events(data)
    if args.action == "webhook":
        return _validate_webhook(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_events(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    eth = c.load_thresholds()["event"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", event_count=0)

    events = data.get("events")
    if not isinstance(events, list) or not events:
        return c.result([_ck(False, "events 必须是非空列表", "revenue.list")],
                        ok=False, verdict="FAIL", event_count=0)

    bad_type = [e.get("entity_id") for e in events if isinstance(e, dict)
                and e.get("type") not in eth["event_types"]]
    checks.append(_ck(not bad_type,
                      f"事件类型在白名单（越界 {bad_type or '无'}）", "revenue.type"))

    missing = [e.get("entity_id") for e in events if isinstance(e, dict)
               and any(not str(e.get(k, "")).strip() for k in eth["event_required"])]
    checks.append(_ck(not missing, f"事件三要素齐备（缺 {missing or '无'}）",
                      "revenue.required"))

    # 注意：此处必须用 _num 而非 money——money() 会把负数钳为 0，钳后再判 < amount_min
    # 永远为假（该门禁形同虚设）。事件金额的"非负"判定必须在钳制前做。
    bad_amount = [e.get("entity_id") for e in events if isinstance(e, dict)
                  and c._num(e.get("amount")) < eth["amount_min"]]
    checks.append(_ck(not bad_amount,
                      f"事件金额非负（异常 {bad_amount or '无'}）", "revenue.amount"))

    # 时序单调：ts 序列必须等于排序结果（收入口径依赖事件顺序）
    ts_list = [str(e.get("ts", "")) for e in events if isinstance(e, dict)]
    ok_mono = ts_list == sorted(ts_list) and all(ts_list)
    checks.append(_ck(ok_mono, f"事件时序单调（{len(ts_list)} 条）", "revenue.order"))

    total = round(sum(c.money(e.get("amount")) for e in events
                      if isinstance(e, dict)), 2)
    checks.append(_ck(True, f"事件总额 {total}", "revenue.total"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        event_count=len(events), total_amount=total,
        narrative=f"交易事件 {len(events)} 条、总额 {total}")


# --------------------------------------------------------------------------- #
def _validate_webhook(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", event_count=0)

    event = str(data.get("event", "")).strip()
    checks.append(_ck(bool(event), "回调事件类型非空", "webhook.event"))

    endpoint = str(data.get("endpoint", "")).strip()
    checks.append(_ck(bool(endpoint), "回调端点非空", "webhook.endpoint"))

    # 对账规则：必填
    recon = str(data.get("reconciliation", "")).strip()
    checks.append(_ck(bool(recon), "对账规则非空", "webhook.reconciliation"))

    # 重试策略：重试次数必须为数值且 ≤ 上限
    retries = data.get("retries")
    ok_retries = isinstance(retries, (int, float)) and not isinstance(retries, bool) \
        and 0 <= retries <= 5
    checks.append(_ck(ok_retries,
                      f"重试次数={retries!r} 在 0-5 区间", "webhook.retries"))

    # 人工审批点：高危回调（退款/取消）必须声明审批
    high_risk = any(w in event.lower() for w in ("refund", "cancel"))
    approval = str(data.get("approval", "")).strip()
    if high_risk:
        checks.append(_ck(bool(approval),
                          f"高危回调「{event}」必须声明人工审批", "webhook.approval"))
    else:
        checks.append(_ck(True, "非高危回调，审批可选", "webhook.approval"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        event_count=1, event=event,
        narrative=f"回调 {event} → {endpoint}（重试 {retries}）")

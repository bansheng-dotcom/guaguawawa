# -*- coding: utf-8 -*-
"""S07 交易状态编排 —— 能力域 7。

整合自 medusajs__medusa 的订单状态机（pending → completed / draft → archived /
canceled / requires_action）与 Stripe/Lago/Documenso/EasyAppointments 各交易域的状态
边界，把「下单、支付、签署、预约、履约、取消和退款」的状态迁移规则落成确定性校验。

关键立场：**交易状态机的非法迁移比字段缺失更危险**。refunded 不能回 completed、
canceled 不能再 captured、已签署完成的文档不能退回 DRAFT。

动作：
  state      交易状态机（多实体状态一致性）
  transition 单次状态迁移合法性
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "workflow"
DESC = "交易状态编排：state/transition"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("state", help="校验交易状态机")
    a.add_argument("--input", required=True)
    b = act.add_parser("transition", help="校验单次状态迁移")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "state":
        return _validate_state(data)
    if args.action == "transition":
        return _validate_transition(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# 合法状态迁移（交易状态机）
_VALID_TRANSITIONS = {
    "order": {
        "pending": ["completed", "canceled", "requires_action"],
        "draft": ["pending", "archived"],
        "requires_action": ["completed", "canceled"],
        "completed": [],           # 终态：completed 不可再迁移
        "canceled": [],            # 终态
        "archived": [],            # 终态
    },
    "payment": {
        "requires_payment_method": ["requires_confirmation", "canceled"],
        "requires_confirmation": ["requires_action", "processing", "canceled"],
        "requires_action": ["processing", "succeeded", "canceled"],
        "processing": ["succeeded", "canceled"],
        "requires_capture": ["succeeded", "canceled"],
        "succeeded": ["partially_refunded"],   # 只能往退款方向
        "partially_refunded": ["refunded"],
        "refunded": [],            # 终态
        "canceled": [],            # 终态
    },
    "signature": {
        "DRAFT": ["PENDING"],
        "PENDING": ["COMPLETED"],
        "COMPLETED": [],           # 终态
    },
    "appointment": {
        "pending": ["booked", "rejected", "canceled"],
        "booked": ["canceled", "no_show"],
        "approved": ["booked", "canceled"],
        "rejected": [],            # 终态
        "canceled": [],            # 终态
        "no_show": [],             # 终态
    },
}


# --------------------------------------------------------------------------- #
def _validate_state(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", event_count=0)

    entities = data.get("entities") or []
    if not isinstance(entities, list) or not entities:
        return c.result([_ck(False, "entities 必须是非空列表", "workflow.list")],
                        ok=False, verdict="FAIL", event_count=0)

    known = set(_VALID_TRANSITIONS.keys())
    bad_entity = [e.get("kind") for e in entities if isinstance(e, dict)
                  and e.get("kind") not in known]
    checks.append(_ck(not bad_entity,
                      f"实体类型在白名单（越界 {bad_entity or '无'}）",
                      "workflow.entity"))

    # 状态一致性：终态实体不得再有后续迁移动作
    illegal = [f"{e.get('kind')}:{e.get('status')}" for e in entities
               if isinstance(e, dict) and e.get("kind") in _VALID_TRANSITIONS
               and e.get("status") in _VALID_TRANSITIONS[e.get("kind")]
               and not _VALID_TRANSITIONS[e.get("kind")].get(e.get("status"))
               and e.get("pending_action")]
    checks.append(_ck(not illegal, f"终态实体不得有后续动作（异常 {illegal or '无'}）",
                      "workflow.terminal"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        event_count=len(entities),
        narrative=f"交易状态机 {len(entities)} 个实体，终态违规 {len(illegal)} 处")


# --------------------------------------------------------------------------- #
def _validate_transition(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", event_count=0)

    kind = str(data.get("kind", "")).strip()
    ok_kind = kind in _VALID_TRANSITIONS
    checks.append(_ck(ok_kind, f"实体类型={kind!r} 在白名单", "transition.kind"))

    from_status = str(data.get("from_status", "")).strip()
    to_status = str(data.get("to_status", "")).strip()

    if ok_kind:
        allowed = _VALID_TRANSITIONS[kind].get(from_status)
        ok_from = from_status in _VALID_TRANSITIONS[kind]
        checks.append(_ck(ok_from, f"起始状态={from_status!r} 合法", "transition.from"))
        ok_to = allowed is not None and to_status in (allowed or [])
        checks.append(_ck(ok_to,
                          f"迁移 {from_status} → {to_status} 合法"
                          f"（允许 {allowed or '无'}）", "transition.to"))
        # 终态不可再迁出
        if from_status in _VALID_TRANSITIONS[kind] and not allowed and allowed is not None:
            checks.append(_ck(False, f"终态 {from_status} 不可再迁移",
                              "transition.terminal"))
        else:
            checks.append(_ck(True, "非终态或已判迁移合法性", "transition.terminal"))
    else:
        checks.append(_ck(False, "实体类型未知，无法判迁移", "transition.from"))
        checks.append(_ck(False, "实体类型未知，无法判迁移", "transition.to"))
        checks.append(_ck(False, "实体类型未知", "transition.terminal"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        event_count=1, kind=kind, from_status=from_status, to_status=to_status,
        narrative=f"迁移 {kind}:{from_status} → {to_status}")

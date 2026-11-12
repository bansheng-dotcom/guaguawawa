# -*- coding: utf-8 -*-
"""R14 技能契约登记表：8 技能 × 17 动作契约。

- 输入 schema：validate_input(skill, action, data)，缺必填字段即 fail。
- 输出 schema：validate_output(skill, action, result)，供 verify_loop 闭环。
- CLI：`python agent.py contract validate --skill S --action A --output result.json`。
口径：所有输出必须有 ok:boolean 与 checks:array（对齐 r05..r13 模板）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c

# --------------------------------------------------------------------------- #
# 通用构造
# --------------------------------------------------------------------------- #
_REQ = lambda props, required: {"type": "object", "required": required,  # noqa: E731
                               "properties": props}
_ARR = lambda items: {"type": "array", "items": items}                  # noqa: E731
_STR = {"type": "string"}
_BOOL = {"type": "boolean"}
_NUM = {"type": "number"}
# 主键类字段：DB 自增主键是 int，API 序列化后可能是 str，两者都合法
# （来源仓库 easyappointments 的 customer_id/provider_id/service_id 均为 int PK）。
_ID = {"type": ["string", "integer"]}


def _out(required: List[str]) -> Dict[str, Any]:
    """输出通用：ok/checks 必填 + 动作专属必填字段。"""
    props: Dict[str, Any] = {"ok": _BOOL, "checks": _ARR({"type": "object"}),
                             "next": _STR,
                             "verdict": {"type": "string",
                                         "enum": ["PASS", "FAIL"]}}
    for k in required:
        props[k] = {}
    return {"type": "object", "required": ["ok", "checks"] + required,
            "properties": props}


# --------------------------------------------------------------------------- #
# 各技能契约
# --------------------------------------------------------------------------- #
CONTRACTS: Dict[str, Dict[str, Any]] = {
    "elasticity": {
        "desc": "价格弹性：log-log OLS + R²",
        "input": {},
        "output": {"elasticity": _out(["elasticity"])},
    },
    "catalog": {
        "desc": "商品与电商后端：product/price/image",
        "input": {
            "product": _REQ({
                "products": _ARR(_REQ({"title": _STR, "status": _STR,
                                       "price": _NUM},
                                      ["title", "status", "price"])),
            }, ["products"]),
            "price": _REQ({"title": _STR, "status": _STR, "price": _NUM},
                          ["title", "status", "price"]),
            "image": _REQ({"need": _STR}, ["need"]),
        },
        "output": {
            "product": _out(["product_count", "sellable_count"]),
            "price": _out(["product_count"]),
            "image": _out(["prompt", "delegated_to"]),
        },
    },
    "order": {
        "desc": "购物车与订单编排：cart/order",
        "input": {
            "cart": _REQ({
                "line_items": _ARR(_REQ({"title": _STR, "unit_price": _NUM,
                                         "quantity": _NUM},
                                        ["title", "unit_price", "quantity"])),
            }, ["line_items"]),
            "order": _REQ({"id": _STR, "status": _STR, "payment_status": _STR,
                           "fulfillment_status": _STR, "total": _NUM},
                          ["id", "status", "payment_status",
                           "fulfillment_status", "total"]),
        },
        "output": {
            "cart": _out(["line_item_count", "cart_total"]),
            "order": _out(["order_count", "total"]),
        },
    },
    "billing": {
        "desc": "订阅与计量计费：plan/usage/invoice",
        "input": {
            "plan": _REQ({"code": _STR, "interval": _STR,
                          "charges": _ARR({"type": "object"})},
                         ["code", "interval", "charges"]),
            "usage": _REQ({"usage": _ARR({"type": "object"})}, ["usage"]),
            "invoice": _REQ({"id": _STR, "status": _STR, "total": _NUM,
                             "line_items": _ARR({"type": "object"})},
                            ["id", "status", "total", "line_items"]),
        },
        "output": {
            "plan": _out(["plan_count", "charge_count"]),
            "usage": _out(["usage_count", "total_quantity"]),
            "invoice": _out(["invoice_count", "total"]),
        },
    },
    "payment": {
        "desc": "支付服务端集成：payment_intent/refund",
        "input": {
            "payment_intent": _REQ({"id": _STR, "status": _STR, "amount": _NUM},
                                   ["id", "status", "amount"]),
            "refund": _REQ({"payment_intent": _STR, "amount": _NUM},
                           ["payment_intent", "amount"]),
        },
        "output": {
            "payment_intent": _out(["payment_count", "amount"]),
            "refund": _out(["refund_count", "amount"]),
        },
    },
    "signature": {
        "desc": "电子签与签署审计：document/signing",
        "input": {
            "document": _REQ({
                "title": _STR, "status": _STR,
                "recipients": _ARR(_REQ({"email": _STR, "role": _STR},
                                        ["email", "role"])),
            }, ["title", "status", "recipients"]),
            "signing": _REQ({"status": _STR,
                             "recipients": _ARR({"type": "object"})},
                            ["status", "recipients"]),
        },
        "output": {
            "document": _out(["document_count", "recipient_count"]),
            "signing": _out(["document_count", "recipient_count"]),
        },
    },
    "appointment": {
        "desc": "服务预约：appointment/calendar",
        "input": {
            "appointment": _REQ({"customer_id": _ID, "provider_id": _ID,
                                 "service_id": _ID, "start_datetime": _STR,
                                 "end_datetime": _STR},
                                ["customer_id", "provider_id", "service_id",
                                 "start_datetime", "end_datetime"]),
            "calendar": _REQ({"events": _ARR({"type": "object"})}, ["events"]),
        },
        "output": {
            "appointment": _out(["appointment_count"]),
            "calendar": _out(["appointment_count"]),
        },
    },
    "workflow": {
        "desc": "交易状态编排：state/transition",
        "input": {
            "state": _REQ({"entities": _ARR({"type": "object"})}, ["entities"]),
            "transition": _REQ({"kind": _STR, "from_status": _STR,
                                "to_status": _STR},
                               ["kind", "from_status", "to_status"]),
        },
        "output": {
            "state": _out(["event_count"]),
            "transition": _out(["event_count"]),
        },
    },
    "revenue": {
        "desc": "收入数据接口与交易自动化：events/webhook",
        "input": {
            "events": _REQ({"events": _ARR({"type": "object"})}, ["events"]),
            "webhook": _REQ({"event": _STR, "endpoint": _STR,
                             "reconciliation": _STR},
                            ["event", "endpoint", "reconciliation"]),
        },
        "output": {
            "events": _out(["event_count", "total_amount"]),
            "webhook": _out(["event_count"]),
        },
    },
    "selection": {
        "desc": "选品评分：score/profit（五维加权 + 利润红线）",
        "input": {
            "score": _REQ({"products": _ARR(_REQ({"name": _STR, "dims": {"type": "object"}},
                                                ["name", "dims"]))},
                          ["products"]),
            "profit": _REQ({"price": _NUM, "cost": _NUM},
                           ["price", "cost"]),
        },
        "output": {
            "score": _out(["ranked"]),
            "profit": _out(["margin_pct"]),
        },
    },
}


def skill_names() -> List[str]:
    return list(CONTRACTS.keys())


def get(skill: str) -> Dict[str, Any]:
    return CONTRACTS.get(skill, {})


def actions(skill: str) -> List[str]:
    return list(CONTRACTS[skill]["output"].keys())


def input_schema(skill: str, action: str) -> Dict[str, Any]:
    return CONTRACTS[skill]["input"][action]


def output_schema(skill: str, action: str) -> Dict[str, Any]:
    return CONTRACTS[skill]["output"][action]


def validate_input(skill: str, action: str, data: Any) -> Dict[str, Any]:
    if skill not in CONTRACTS or action not in CONTRACTS[skill]["input"]:
        return {"ok": False, "errors": [f"未登记的契约：{skill}/{action}"]}
    errs = c.validate_schema(data, input_schema(skill, action))
    return {"ok": not errs, "errors": errs}


def validate_output(skill: str, action: str, result: Any) -> Dict[str, Any]:
    if skill not in CONTRACTS or action not in CONTRACTS[skill]["output"]:
        return {"ok": False, "errors": [f"未登记的契约：{skill}/{action}"]}
    errs = c.validate_schema(result, output_schema(skill, action))
    return {"ok": not errs, "errors": errs}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cli() -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="R14 技能契约校验器")
    sub = ap.add_subparsers(dest="cmd", required=True)
    vp = sub.add_parser("validate", help="校验一份输出 result.json 是否符合契约")
    vp.add_argument("--skill", required=True, choices=skill_names())
    vp.add_argument("--action", required=True)
    vp.add_argument("--output", required=True, help="待校验的 result.json 路径")
    ip = sub.add_parser("list", help="列出全部登记的 skill/action")
    args = ap.parse_args()
    if args.cmd == "list":
        rows = [(s, a) for s in skill_names() for a in actions(s)]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    data = json.load(open(args.output, encoding="utf-8"))
    v = validate_output(args.skill, args.action, data)
    print(json.dumps(v, ensure_ascii=False, indent=2))
    return 0 if v["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())

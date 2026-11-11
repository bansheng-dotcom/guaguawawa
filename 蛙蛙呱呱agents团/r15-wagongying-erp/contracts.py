# -*- coding: utf-8 -*-
"""R15 技能契约登记表：7 技能 × 18 动作契约。

- 输入 schema：validate_input(skill, action, data)，缺必填字段即 fail。
- 输出 schema：validate_output(skill, action, result)，供 verify_loop 闭环。
- CLI：`python agent.py contract validate --skill S --action A --output result.json`。
口径：所有输出必须有 ok:boolean 与 checks:array（对齐 r05..r14 模板）。
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
# （来源仓库 erpnext 的 item_code/supplier/customer 等字段均可能 int 或 str）。
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
    "procurement": {
        "desc": "采购与供应商：supplier/rfq/quotation/purchase_order/receipt",
        "input": {
            "supplier": _REQ({
                "suppliers": _ARR(_REQ({"supplier_name": _STR, "supplier_type": _STR},
                                       ["supplier_name", "supplier_type"])),
            }, ["suppliers"]),
            "rfq": _REQ({"id": _STR, "status": _STR, "required_by": _STR,
                         "suppliers": _ARR({"type": "object"}),
                         "items": _ARR({"type": "object"})},
                        ["status", "suppliers", "items"]),
            "quotation": _REQ({"id": _STR, "supplier": _STR, "status": _STR,
                               "items": _ARR({"type": "object"}),
                               "valid_till": _STR},
                              ["supplier", "status", "items"]),
            "purchase_order": _REQ({
                "id": _STR, "supplier": _STR, "transaction_date": _STR,
                "schedule_date": _STR, "status": _STR,
                "items": _ARR(_REQ({"item_code": _ID, "qty": _NUM, "rate": _NUM},
                                   ["item_code", "qty", "rate"])),
            }, ["supplier", "transaction_date", "schedule_date", "items"]),
            "receipt": _REQ({
                "id": _STR, "supplier": _STR, "status": _STR,
                "items": _ARR(_REQ({"item_code": _ID, "received_qty": _NUM,
                                    "ordered_qty": _NUM},
                                   ["item_code", "received_qty", "ordered_qty"])),
            }, ["supplier", "items"]),
        },
        "output": {
            "supplier": _out(["supplier_count"]),
            "rfq": _out(["supplier_count"]),
            "quotation": _out(["quotation_count", "total"]),
            "purchase_order": _out(["po_count", "total"]),
            "receipt": _out(["receipt_count", "total_qty"]),
        },
    },
    "inventory": {
        "desc": "库存与仓库：item/warehouse/bin/stock_entry",
        "input": {
            "item": _REQ({
                "items": _ARR(_REQ({"item_code": _ID, "item_name": _STR},
                                   ["item_code", "item_name"])),
            }, ["items"]),
            "warehouse": _REQ({
                "warehouses": _ARR(_REQ({"warehouse_name": _STR},
                                        ["warehouse_name"])),
            }, ["warehouses"]),
            "bin": _REQ({
                "bins": _ARR(_REQ({"warehouse": _STR, "item_code": _ID,
                                   "actual_qty": _NUM},
                                  ["warehouse", "item_code", "actual_qty"])),
            }, ["bins"]),
            "stock_entry": _REQ({"id": _STR, "purpose": _STR,
                                 "items": _ARR({"type": "object"})},
                                ["purpose", "items"]),
        },
        "output": {
            "item": _out(["item_count"]),
            "warehouse": _out(["warehouse_count"]),
            "bin": _out(["bin_count", "stock_value"]),
            "stock_entry": _out(["entry_count", "total_qty"]),
        },
    },
    "fulfillment": {
        "desc": "销售与履约记录：sales_order/delivery",
        "input": {
            "sales_order": _REQ({
                "id": _STR, "customer": _STR, "status": _STR,
                "delivery_status": _STR, "billing_status": _STR,
                "items": _ARR(_REQ({"item_code": _ID, "qty": _NUM, "rate": _NUM},
                                   ["item_code", "qty", "rate"])),
            }, ["customer", "status", "items"]),
            "delivery": _REQ({
                "id": _STR, "customer": _STR, "status": _STR,
                "items": _ARR(_REQ({"item_code": _ID, "qty": _NUM,
                                    "against_qty": _NUM},
                                   ["item_code", "qty", "against_qty"])),
            }, ["customer", "status", "items"]),
        },
        "output": {
            "sales_order": _out(["sales_order_count", "total"]),
            "delivery": _out(["delivery_count", "total_qty"]),
        },
    },
    "production": {
        "desc": "生产/服务资源：bom/material_request",
        "input": {
            "bom": _REQ({
                "id": _STR, "item": _STR, "quantity": _NUM,
                "items": _ARR(_REQ({"item_code": _ID, "qty": _NUM},
                                   ["item_code", "qty"])),
            }, ["item", "quantity", "items"]),
            "material_request": _REQ({"id": _STR, "purpose": _STR, "status": _STR,
                                      "items": _ARR({"type": "object"})},
                                     ["purpose", "status", "items"]),
        },
        "output": {
            "bom": _out(["bom_count", "line_item_count"]),
            "material_request": _out(["material_request_count", "line_item_count"]),
        },
    },
    "finance": {
        "desc": "ERP财务业务接口：invoice/payment",
        "input": {
            "invoice": _REQ({
                "id": _STR, "kind": _STR, "party": _STR, "status": _STR,
                "total": _NUM,
                "line_items": _ARR(_REQ({"item_code": _ID, "qty": _NUM,
                                         "rate": _NUM},
                                        ["item_code", "qty", "rate"])),
            }, ["party", "total", "line_items"]),
            "payment": _REQ({"id": _STR, "party": _STR, "paid_amount": _NUM,
                             "paid_to": _STR, "status": _STR},
                            ["party", "paid_amount", "paid_to"]),
        },
        "output": {
            "invoice": _out(["invoice_count", "total"]),
            "payment": _out(["payment_count", "paid_amount"]),
        },
    },
    "masterdata": {
        "desc": "主数据与权限：master_data/permission",
        "input": {
            "master_data": _REQ({
                "records": _ARR(_REQ({"type": _STR, "code": _STR},
                                     ["type", "code"])),
            }, ["records"]),
            "permission": _REQ({
                "matrix": _ARR(_REQ({"role": _STR, "doctype": _STR,
                                     "action": _STR},
                                    ["role", "doctype", "action"])),
            }, ["matrix"]),
        },
        "output": {
            "master_data": _out(["master_count"]),
            "permission": _out(["matrix_count"]),
        },
    },
    "report": {
        "desc": "运营报表：report",
        "input": {
            "report": _REQ({"report_type": _STR, "period": _STR,
                            "kpis": _ARR({"type": "object"})},
                           ["report_type", "period", "kpis"]),
        },
        "output": {
            "report": _out(["report_count", "kpi_count"]),
        },
    },
    "tco": {
        "desc": "采购总拥有成本：compare/lifecycle",
        "input": {
            "compare": _REQ({"quotes": _ARR(_REQ({"supplier": _STR, "unit_price": _NUM,
                                                  "qty": _NUM},
                                                 ["supplier", "unit_price", "qty"]))},
                            ["quotes"]),
            "lifecycle": _REQ({"acquisition": _NUM}, ["acquisition"]),
        },
        "output": {
            "compare": _out(["ranked"]),
            "lifecycle": _out(["tco"]),
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
    ap = argparse.ArgumentParser(description="R15 技能契约校验器")
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

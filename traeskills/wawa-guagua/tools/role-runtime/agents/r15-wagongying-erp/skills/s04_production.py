# -*- coding: utf-8 -*-
"""S04 生产/服务资源 —— 能力域 4。

整合自 frappe__erpnext 的 manufacturing 与 stock 模块：
  - `manufacturing/doctype/bom/bom.json`（item/quantity/is_active/is_default/
    with_operations + BOM Item 的 item_code/qty）
  - `stock/doctype/material_request/`（status 十一态 + purpose: Purchase/
    Material Transfer/Material Issue/Manufacture/Customer Provided）

关键立场：**BOM 是「生产一件成品要哪些料」的配方**，物料请求是「缺口怎么补」。
BOM 必须能逐层展开（行项目必填 + 父物料必填），材料请求的 purpose 决定后续
走采购还是调拨还是领料。配方不闭合（成品无行项目 / 行项目无用量）会导致
MRP 全错，必须确定性拦截。

动作：
  bom             物料清单校验（配方结构 + 用量）
  material_request 物料请求校验（用途 + 状态）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "production"
DESC = "生产/服务资源：bom/material_request"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("bom", help="校验物料清单配方")
    a.add_argument("--input", required=True)
    b = act.add_parser("material_request", help="校验物料请求")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"bom": _validate_bom,
          "material_request": _validate_material_request}.get(args.action)
    if fn is None:
        return {"error": f"未知动作: {args.action}"}
    return fn(data)


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_bom(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["production"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", bom_count=0)

    missing = [k for k in th["bom_required"] if not data.get(k)]
    checks.append(_ck(not missing, f"BOM 必填齐备（缺 {missing or '无'}）",
                      "bom.required"))

    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        checks.append(_ck(False, "BOM 行项目必须非空（配方不闭合）", "bom.items"))
        items = []
    else:
        checks.append(_ck(True, f"BOM 行项目 {len(items)} 条", "bom.items"))

    too_many = len(items) > th["max_bom_depth_items"]
    checks.append(_ck(not too_many,
                      f"BOM 行数 {len(items)} ≤ {th['max_bom_depth_items']}",
                      "bom.line_count"))

    bad_line = [i.get("item_code") for i in items if isinstance(i, dict)
                and any(not str(i.get(k, "")).strip()
                        for k in th["bom_item_required"])]
    checks.append(_ck(not bad_line, f"BOM 行项目必填齐备（缺 {bad_line or '无'}）",
                      "bom.item_required"))

    bad_qty = [i.get("item_code") for i in items if isinstance(i, dict)
               and c._num(i.get("qty")) <= 0]
    checks.append(_ck(not bad_qty, f"BOM 用量为正（异常 {bad_qty or '无'}）",
                      "bom.qty"))

    # 父物料数量：生产一件成品的基准批量，必须为正
    parent_qty = c._num(data.get("quantity"))
    checks.append(_ck(parent_qty > 0, f"父物料基准批量 {parent_qty} > 0",
                      "bom.parent_qty"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        bom_count=1, line_item_count=len(items),
        narrative=(f"BOM {data.get('id', '?')}（{data.get('item', '?')}）："
                   f"{len(items)} 行配方，基准批量 {parent_qty}"))


# --------------------------------------------------------------------------- #
def _validate_material_request(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["production"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", material_request_count=0)

    missing = [k for k in th["mr_required"] if not data.get(k)]
    checks.append(_ck(not missing, f"物料请求必填齐备（缺 {missing or '无'}）",
                      "mr.required"))

    purpose = data.get("purpose")
    checks.append(_ck(purpose in th["mr_purpose"],
                      f"物料请求用途={purpose!r} 在白名单", "mr.purpose"))

    status = data.get("status")
    checks.append(_ck(status in th["mr_status"],
                      f"物料请求状态={status!r} 在白名单", "mr.status"))

    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        checks.append(_ck(False, "物料请求行项目必须非空", "mr.items"))
        items = []

    bad_qty = [i.get("item_code") for i in items if isinstance(i, dict)
               and c._num(i.get("qty")) <= 0]
    checks.append(_ck(not bad_qty, f"请求数量为正（异常 {bad_qty or '无'}）",
                      "mr.qty"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        material_request_count=1, line_item_count=len(items),
        narrative=(f"物料请求 {data.get('id', '?')}：{purpose}、{status}、"
                   f"{len(items)} 行"))

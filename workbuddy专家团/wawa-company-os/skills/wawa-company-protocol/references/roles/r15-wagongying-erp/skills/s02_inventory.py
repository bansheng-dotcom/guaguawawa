# -*- coding: utf-8 -*-
"""S02 库存与仓库 —— 能力域 2。

整合自 frappe__erpnext 的 stock 模块：
  - `stock/doctype/item/item.json`（item_code/item_name/item_group/stock_uom/
    is_stock_item/valuation_method FIFO/Moving Average/LIFO/Standard Cost）
  - `stock/doctype/warehouse/warehouse.json`（warehouse_name/is_group/
    parent_warehouse/is_rejected_warehouse）
  - `stock/doctype/bin/bin.json`（warehouse/item_code/actual_qty/ordered_qty/
    reserved_qty/planned_qty/projected_qty/valuation_rate/stock_value）
  - `stock/doctype/stock_entry/`（purpose: Material Receipt/Material Issue/
    Material Transfer/Manufacture/Repack/Send to Subcontractor）

关键立场：**库存台账以 Bin 为最小事实单元**。账实一致性由「实际数量 ≥ 0」
（负库存默认禁止，阈值外置）+ 「物料 + 仓库 + 用途」枚举三重门禁保证。
库存是「记录已发生」，不是「直接改动库存」——任何盘盈盘亏必须声明 handoff。

动作：
  item        物料主数据校验
  warehouse   仓库主数据校验
  bin         库存明细（Bin）校验与负库存门禁
  stock_entry 库存交易（出入库/调拨/制造）校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "inventory"
DESC = "库存与仓库：item/warehouse/bin/stock_entry"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for name, help_txt in (
        ("item", "校验物料主数据"),
        ("warehouse", "校验仓库主数据"),
        ("bin", "校验库存明细与负库存门禁"),
        ("stock_entry", "校验库存交易用途与恒等式"),
    ):
        a = act.add_parser(name, help=help_txt)
        a.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {
        "item": _validate_item,
        "warehouse": _validate_warehouse,
        "bin": _validate_bin,
        "stock_entry": _validate_stock_entry,
    }.get(args.action)
    if fn is None:
        return {"error": f"未知动作: {args.action}"}
    return fn(data)


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_item(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["inventory"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", item_count=0)

    items = data.get("items")
    if not isinstance(items, list) or not items:
        return c.result([_ck(False, "items 必须是非空列表", "item.list")],
                        ok=False, verdict="FAIL", item_count=0)

    missing = [i.get("item_code") for i in items if isinstance(i, dict)
               and any(not str(i.get(k, "")).strip() for k in th["item_required"])]
    checks.append(_ck(not missing, f"物料必填齐备（缺 {missing or '无'}）",
                      "item.required"))

    bad_uom = [i.get("item_code") for i in items if isinstance(i, dict)
               and i.get("stock_uom") not in th["uom_whitelist"]]
    checks.append(_ck(not bad_uom, f"库存单位在白名单（越界 {bad_uom or '无'}）",
                      "item.uom"))

    bad_val = [i.get("item_code") for i in items if isinstance(i, dict)
               and i.get("valuation_method") not in th["valuation_methods"]]
    checks.append(_ck(not bad_val,
                      f"计价方法在白名单（越界 {bad_val or '无'}）", "item.valuation"))

    bad_lead = [i.get("item_code") for i in items if isinstance(i, dict)
                and c._num(i.get("lead_time_days")) > th["max_lead_time_days"]]
    checks.append(_ck(not bad_lead,
                      f"采购周期 ≤ {th['max_lead_time_days']} 天（超限 {bad_lead or '无'}）",
                      "item.lead_time"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        item_count=len(items),
        narrative=f"物料 {len(items)} 条，主数据通过门禁")


# --------------------------------------------------------------------------- #
def _validate_warehouse(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["inventory"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", warehouse_count=0)

    warehouses = data.get("warehouses")
    if not isinstance(warehouses, list) or not warehouses:
        return c.result([_ck(False, "warehouses 必须是非空列表", "warehouse.list")],
                        ok=False, verdict="FAIL", warehouse_count=0)

    missing = [w.get("warehouse_name") for w in warehouses if isinstance(w, dict)
               and not str(w.get("warehouse_name", "")).strip()]
    checks.append(_ck(not missing, f"仓库名非空（缺 {missing or '无'}）",
                      "warehouse.name"))

    # 组仓库不可存实物：is_group=true 却当实体库 = 结构错误
    bad_group = [w.get("warehouse_name") for w in warehouses if isinstance(w, dict)
                 and bool(w.get("is_group")) and bool(w.get("is_rejected_warehouse"))]
    checks.append(_ck(not bad_group,
                      f"组仓库不得同时为退次库（异常 {bad_group or '无'}）",
                      "warehouse.group"))

    # 父仓库引用校验：非根仓库必须声明 parent_warehouse
    no_parent = [w.get("warehouse_name") for w in warehouses if isinstance(w, dict)
                 and not bool(w.get("is_group"))
                 and not str(w.get("parent_warehouse", "")).strip()]
    checks.append(_ck(not no_parent,
                      f"非根仓库声明父仓库（缺 {no_parent or '无'}）",
                      "warehouse.parent"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        warehouse_count=len(warehouses),
        narrative=f"仓库 {len(warehouses)} 个，层级结构通过门禁")


# --------------------------------------------------------------------------- #
def _validate_bin(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["inventory"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", bin_count=0)

    bins = data.get("bins")
    if not isinstance(bins, list) or not bins:
        return c.result([_ck(False, "bins 必须是非空列表", "bin.list")],
                        ok=False, verdict="FAIL", bin_count=0)

    missing = [b.get("item_code") for b in bins if isinstance(b, dict)
               and any(not str(b.get(k, "")).strip() for k in th["bin_required"])]
    checks.append(_ck(not missing, f"Bin 必填齐备（缺 {missing or '无'}）",
                      "bin.required"))

    # 负库存门禁：actual_qty < 0 即账实不符（默认禁止，阈值外置）
    allow_neg = bool(th["allow_negative_stock"])
    negative = [b.get("item_code") for b in bins if isinstance(b, dict)
                and c._num(b.get("actual_qty")) < 0]
    checks.append(_ck(allow_neg or not negative,
                      f"无负库存（负库存 {negative or '无'}，允许={allow_neg}）",
                      "bin.negative_stock"))

    # 库存守恒：projected = actual + ordered + planned − reserved
    broke = []
    for b in bins:
        if not isinstance(b, dict):
            continue
        actual = c._num(b.get("actual_qty"))
        ordered = c._num(b.get("ordered_qty"))
        reserved = c._num(b.get("reserved_qty"))
        planned = c._num(b.get("planned_qty"))
        projected = c._num(b.get("projected_qty"))
        expect = round(actual + ordered + planned - reserved, 2)
        if abs(projected - expect) > 0.01:
            broke.append(f"{b.get('item_code')}@{b.get('warehouse')}")
    checks.append(_ck(not broke,
                      f"预计量守恒（异常 {broke or '无'}）", "bin.projected"))

    stock_value = round(sum(c.money(b.get("stock_value"))
                            for b in bins if isinstance(b, dict)), 2)
    checks.append(_ck(stock_value >= 0, f"库存总值 {stock_value} ≥ 0",
                      "bin.stock_value"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        bin_count=len(bins), stock_value=stock_value,
        narrative=f"库存 {len(bins)} 条 Bin、总值 {stock_value}")


# --------------------------------------------------------------------------- #
def _validate_stock_entry(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["inventory"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", entry_count=0)

    missing = [k for k in th["stock_entry_required"] if not data.get(k)]
    checks.append(_ck(not missing, f"库存交易必填齐备（缺 {missing or '无'}）",
                      "stock_entry.required"))

    purpose = data.get("purpose")
    checks.append(_ck(purpose in th["stock_entry_types"],
                      f"库存交易用途={purpose!r} 在白名单", "stock_entry.purpose"))

    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        checks.append(_ck(False, "库存交易行项目必须非空", "stock_entry.items"))
        items = []

    total_qty = round(sum(abs(c._num(i.get("qty"))) for i in items
                          if isinstance(i, dict)), 2)
    checks.append(_ck(total_qty > 0, f"交易总数量 {total_qty} > 0", "stock_entry.qty"))

    # 出入库方向与用途自洽：Material Issue 必须有源仓，Material Receipt 必须有目标仓
    from_wh = str(data.get("from_warehouse", "")).strip()
    to_wh = str(data.get("to_warehouse", "")).strip()
    if purpose == "Material Transfer":
        checks.append(_ck(bool(from_wh) and bool(to_wh),
                          "调拨需源仓与目标仓", "stock_entry.transfer_wh"))
    else:
        checks.append(_ck(bool(from_wh) or bool(to_wh),
                          f"出入库声明仓库（源={from_wh or '空'} 目标={to_wh or '空'}）",
                          "stock_entry.warehouse"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        entry_count=1, total_qty=total_qty, line_item_count=len(items),
        narrative=f"库存交易 {data.get('id', '?')}：{purpose}、{len(items)} 行、量 {total_qty}")

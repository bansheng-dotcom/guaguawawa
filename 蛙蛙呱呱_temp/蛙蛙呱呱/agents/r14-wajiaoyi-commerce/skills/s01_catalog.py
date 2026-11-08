# -*- coding: utf-8 -*-
"""S01 商品与电商后端 —— 能力域 1。

整合自 medusajs__medusa 的商品模块：`packages/modules/product/src/models/product.ts`
（title/status/price 标准字段）+ `packages/core/types/src/product/common.ts` 的
`ProductStatus = draft | proposed | published | rejected`。把「商品目录」从堆字段
转成确定性校验：商品必填、状态白名单、金额非负、类型白名单。

关键立场：**商品状态是「能不能卖」的开关**。draft/proposed 未上架不进购物车
（是否可售由 R14 判定，R11 内容 / R10 视觉负责商品呈现，口径不重叠）。

动作：
  product   商品目录与定价校验
  price     单品价格与状态校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "catalog"
DESC = "商品与电商后端：product/price"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("product", help="校验商品目录与定价")
    a.add_argument("--input", required=True)
    b = act.add_parser("price", help="校验单品价格与状态")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "product":
        return _validate_product(data)
    if args.action == "price":
        return _validate_price(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_product(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    cth = c.load_thresholds()["catalog"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", product_count=0)

    products = data.get("products")
    if not isinstance(products, list) or not products:
        return c.result([_ck(False, "products 必须是非空列表", "catalog.list")],
                        ok=False, verdict="FAIL", product_count=0)

    missing = [p.get("title") for p in products if isinstance(p, dict)
               and any(not str(p.get(k, "")).strip() for k in cth["product_required"])]
    checks.append(_ck(not missing,
                      f"商品必填齐备（缺 {missing or '无'}）", "catalog.required"))

    bad_status = [p.get("title") for p in products if isinstance(p, dict)
                  and p.get("status") not in cth["product_status"]]
    checks.append(_ck(not bad_status,
                      f"商品状态在白名单（越界 {bad_status or '无'}）", "catalog.status"))

    bad_type = [p.get("title") for p in products if isinstance(p, dict)
                and p.get("type") not in cth["product_types"]]
    checks.append(_ck(not bad_type,
                      f"商品类型在白名单（越界 {bad_type or '无'}）", "catalog.type"))

    bad_price = [p.get("title") for p in products if isinstance(p, dict)
                 and c.money(p.get("price")) <= 0]
    checks.append(_ck(not bad_price,
                      f"价格均为正数（异常 {bad_price or '无'}）", "catalog.price"))

    # 可售判定：published 才进购物车（draft/proposed/rejected 不可售）
    sellable = [p for p in products if isinstance(p, dict)
                and p.get("status") == "published"]
    checks.append(_ck(True, f"可售商品 {len(sellable)} / 共 {len(products)}",
                      "catalog.sellable"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        product_count=len(products), sellable_count=len(sellable),
        narrative=(f"商品 {len(products)} 个、可售 {len(sellable)} 个、"
                   f"总价 {round(sum(c.money(p.get('price')) for p in products if isinstance(p, dict)), 2)}"))


# --------------------------------------------------------------------------- #
def _validate_price(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    cth = c.load_thresholds()["catalog"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", product_count=0)

    title = str(data.get("title", "")).strip()
    checks.append(_ck(bool(title), "商品名非空", "price.title"))

    status = data.get("status")
    ok_status = status in cth["product_status"]
    checks.append(_ck(ok_status, f"状态={status!r} 在白名单", "price.status"))

    price = c.money(data.get("price"))
    checks.append(_ck(price > 0, f"价格={price} 为正", "price.price"))

    ok = all(x["ok"] for x in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    product_count=1, status=status, price=price,
                    narrative=f"{title or '?'}（{status}）价格 {price}")

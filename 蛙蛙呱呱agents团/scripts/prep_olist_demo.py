# -*- coding: utf-8 -*-
"""生成 Olist 演示项目目录：把公开数据集拼成「订单宽表 + 漏斗阶段表」。

这不是产线的一部分，只做一次 join + 抽样，方便验证「非价格类报告」
也能走同一条产线（漏斗/留存/RFM/评价/履约/支付）。

抽样方式：按 customer_unique_id 抽客户、保留其全部订单，
这样复购率不会被抽样打散。

数据来源：Olist Brazilian E-Commerce Public Dataset（Kaggle，公开）。
输出：workspace/olist_v4_demo/{orders.csv,funnel_stages.csv,README.md}
"""
from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path

SRC = Path(r"D:\蛙蛙呱呱\workspace\olist_data")
DST = Path(r"D:\蛙蛙呱呱\workspace\olist_v4_demo")
CUSTOMERS = 20000
SEED = 42


def read(name):
    with open(SRC / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    random.seed(SEED)
    orders = read("olist_orders_dataset.csv")
    customers = {r["customer_id"]: r for r in read("olist_customers_dataset.csv")}
    reviews = {}
    for r in read("olist_order_reviews_dataset.csv"):
        reviews.setdefault(r["order_id"], r["review_score"])
    pay = defaultdict(lambda: {"value": 0.0, "type": "", "inst": 0})
    for r in read("olist_order_payments_dataset.csv"):
        p = pay[r["order_id"]]
        try:
            p["value"] += float(r["payment_value"] or 0)
        except ValueError:
            pass
        p["type"] = p["type"] or r["payment_type"]
        try:
            p["inst"] = max(p["inst"], int(float(r["payment_installments"] or 0)))
        except ValueError:
            pass
    items = {}
    for r in read("olist_order_items_dataset.csv"):
        items.setdefault(r["order_id"], r["product_id"])
    prods = {r["product_id"]: r["product_category_name"]
             for r in read("olist_products_dataset.csv")}

    by_cust = defaultdict(list)
    for o in orders:
        c = customers.get(o["customer_id"], {})
        by_cust[c.get("customer_unique_id", o["customer_id"])].append(o)
    uniq = random.sample(sorted(by_cust), min(CUSTOMERS, len(by_cust)))
    sample = [o for k in uniq for o in by_cust[k]]

    DST.mkdir(parents=True, exist_ok=True)
    cols = ["order_id", "customer_id", "customer_unique_id", "order_status",
            "purchase_ts", "approved_ts", "carrier_ts", "delivered_ts",
            "estimated_ts", "payment_value", "payment_type", "installments",
            "review_score", "category", "state"]
    with open(DST / "orders.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for o in sample:
            c = customers.get(o["customer_id"], {})
            p = pay.get(o["order_id"], {})
            pid = items.get(o["order_id"], "")
            w.writerow([
                o["order_id"], o["customer_id"], c.get("customer_unique_id", ""),
                o["order_status"], o["order_purchase_timestamp"],
                o["order_approved_at"], o["order_delivered_carrier_date"],
                o["order_delivered_customer_date"], o["order_estimated_delivery_date"],
                round(p.get("value", 0.0), 2), p.get("type", ""), p.get("inst", 0),
                reviews.get(o["order_id"], ""),
                prods.get(pid, ""), c.get("customer_state", ""),
            ])

    stages = [
        ("下单", sum(1 for o in sample if o["order_purchase_timestamp"])),
        ("已审批", sum(1 for o in sample if o["order_approved_at"])),
        ("已交承运", sum(1 for o in sample if o["order_delivered_carrier_date"])),
        ("已签收", sum(1 for o in sample if o["order_delivered_customer_date"])),
    ]
    with open(DST / "funnel_stages.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stage", "count"])
        w.writerows(stages)

    (DST / "README.md").write_text(
        "# Olist 演示项目（产线 v5 用）\n\n"
        "- 来源：Olist Brazilian E-Commerce Public Dataset（Kaggle 公开数据）\n"
        f"- 抽样：按客户抽 {len(uniq)} 人、保留其全部订单，共 {len(sample)} 单（seed={SEED}）\n"
        "- 拼表：订单 + 支付 + 评价 + 商品类目 + 客户州；另出 funnel_stages.csv（四段漏斗）\n"
        "- 用途：验证非价格类报告（漏斗/留存/RFM/评价/履约/支付）走同一条产线\n"
        "- 生成脚本：scripts/prep_olist_demo.py\n",
        encoding="utf-8")
    print(f"wrote {len(sample)} rows / {len(uniq)} customers -> {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

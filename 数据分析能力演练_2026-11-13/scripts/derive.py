# -*- coding: utf-8 -*-
"""从订单明细派生分析输入：周度价格-销量、图表规格、viz 指标包。"""
from __future__ import annotations

import csv
import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
D = HERE / "data"
R = HERE / "results"
R.mkdir(exist_ok=True)


def read(name):
    with (D / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def weekly():
    rows = [r for r in read("orders.csv") if r["category"] == "洗护发"]
    agg = defaultdict(lambda: {"price": 0.0, "units": 0, "rev": 0.0, "orders": 0})
    for r in rows:
        d = dt.date.fromisoformat(r["order_date"])
        iso = d.isocalendar()
        key = f"{iso[0]}-W{iso[1]:02d}"
        a = agg[key]
        a["price"] += float(r["unit_price"])
        a["units"] += int(r["qty"])
        a["rev"] += float(r["revenue"])
        a["orders"] += 1
    out = []
    for key in sorted(agg):
        a = agg[key]
        out.append([key, round(a["price"] / a["orders"], 2), a["units"],
                    round(a["rev"], 2), a["orders"]])
    with (D / "price_qty_weekly.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["week", "avg_price", "units", "revenue", "orders"])
        w.writerows(out)
    print("price_qty_weekly", len(out), "周")


def chart_spec():
    rows = read("price_qty_weekly.csv")
    spec = {
        "chart_type": "line",
        "title": "洗护发周度成交均价与销量（2026）",
        "x_field": "week",
        "y_field": "units",
        "data": [{"week": r["week"], "units": int(r["units"]), "avg_price": float(r["avg_price"])} for r in rows],
        "notes": "价格下行周销量上行，方向与弹性估计一致",
    }
    (D / "chart_spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print("chart_spec written")


def viz_metrics():
    orders = read("orders.csv")
    cat = Counter(r["category"] for r in orders)
    rev = defaultdict(float)
    for r in orders:
        rev[r["category"]] += float(r["revenue"])
    gmv = sum(rev.values())
    metrics = {
        "conclusion": "2026 年 1—9 月模拟订单 2 万单，GMV 与客单价由订单明细直接汇总；品类结构决定客单价差异。",
        "gmv": {"value": round(gmv, 2), "unit": "元"},
        "aov": {"value": round(gmv / len(orders), 2), "unit": "元"},
        "category": {k: {"orders": cat[k], "gmv": round(rev[k], 2)} for k in sorted(cat)},
    }
    (R / "metrics_for_viz.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print("viz metrics written")


if __name__ == "__main__":
    weekly()
    chart_spec()
    viz_metrics()

# -*- coding: utf-8 -*-
"""Olist L3 metrics for R13（客户成功）与 R07（产品需求）代理报告。"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

D = Path(r"D:\蛙蛙呱呱\workspace\olist_data")
OUT = Path(r"D:\蛙蛙呱呱\workspace\olist_l3")
OUT.mkdir(parents=True, exist_ok=True)

orders = pd.read_csv(D / "olist_orders_dataset.csv", parse_dates=[
    "order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"])
items = pd.read_csv(D / "olist_order_items_dataset.csv")
reviews = pd.read_csv(D / "olist_order_reviews_dataset.csv")
customers = pd.read_csv(D / "olist_customers_dataset.csv")
products = pd.read_csv(D / "olist_products_dataset.csv")
cat = pd.read_csv(D / "product_category_name_translation.csv")

orders["delivered"] = orders.order_status.eq("delivered")
orders["late"] = orders.order_delivered_customer_date > orders.order_estimated_delivery_date
orders["delivery_days"] = (orders.order_delivered_customer_date - orders.order_purchase_timestamp).dt.total_seconds() / 86400
orders["month"] = orders.order_purchase_timestamp.dt.to_period("M").astype(str)
orders["customer_unique_id"] = orders.customer_id.map(customers.set_index("customer_id")["customer_unique_id"])
rev = reviews.groupby("order_id").agg(review=("review_score", "mean"), reviews=("review_id", "count")).reset_index()
orders = orders.merge(rev, on="order_id", how="left")
it = items.merge(orders[["order_id", "month", "delivered", "late", "delivery_days", "customer_unique_id", "review"]], on="order_id", how="left")
it["gmv"] = it.price + it.freight_value
itf = it[it.delivered].copy()

# ---------- R13 客户成功 ----------
od = orders[orders.delivered & orders.customer_unique_id.notna()].copy()
asof = pd.Timestamp("2018-08-31")
cust = od.groupby("customer_unique_id").agg(
    orders=("order_id", "nunique"), spend=("order_id", lambda s: float(od.loc[s.index, "order_id"].map(od.groupby("order_id").size()).sum())) if False else ("order_id", "nunique"),
    first=("order_purchase_timestamp", "min"), last=("order_purchase_timestamp", "max"),
    review=("review", "mean"), late=("late", "mean")).reset_index()
# spend from items
spend = itf.groupby("customer_unique_id").gmv.sum().reset_index().rename(columns={"gmv": "spend"})
cust = cust.drop(columns=["spend"]).merge(spend, on="customer_unique_id", how="left").fillna({"spend": 0})
cust["recency"] = (asof - cust.last).dt.days
cust["freq"] = cust.orders
p75 = cust.spend.quantile(.75)
def seg(r):
    if r.recency > 180:
        return "流失风险"
    if r.freq >= 2 and r.spend >= p75:
        return "高价值忠诚"
    if r.freq >= 2:
        return "复购待提升"
    if r.spend >= p75:
        return "高潜新客"
    return "一次性低客单"
cust["segment"] = cust.apply(seg, axis=1)
seg = cust.groupby("segment").agg(customers=("customer_unique_id", "count"), spend=("spend", "sum"),
                                  freq=("freq", "mean"), recency=("recency", "mean"),
                                  review=("review", "mean"), late=("late", "mean")).reset_index()
seg["share"] = seg.customers / len(cust)
repeat_rate = float((cust.freq >= 2).mean())
# 90 天复购
first = od.groupby("customer_unique_id").order_purchase_timestamp.min().rename("first_ts")
od2 = od.merge(first, on="customer_unique_id")
od2["repeat90"] = (od2.order_purchase_timestamp > od2.first_ts) & ((od2.order_purchase_timestamp - od2.first_ts).dt.days <= 90)
repeat90 = od2.groupby("customer_unique_id").repeat90.max().mean()
# monthly cohort
coh = od2.groupby(od2.first_ts.dt.to_period("M").astype(str)).agg(
    customers=("customer_unique_id", "nunique"), repeat90=("repeat90", "mean")).reset_index().rename(columns={"first_ts": "cohort"})
coh = coh[coh.cohort.between("2017-01", "2018-01")]
# review vs repeat
rv = cust.assign(repeat=cust.freq >= 2).groupby("repeat").agg(customers=("customer_unique_id", "count"),
                                                              review=("review", "mean"), spend=("spend", "mean"),
                                                              recency=("recency", "mean")).reset_index()
rv["repeat_label"] = rv.repeat.map({True: "复购", False: "一次性"})
# state
st = od.merge(customers[["customer_id", "customer_state"]], on="customer_id", how="left")
stg = st.groupby("customer_state").agg(customers=("customer_unique_id", "nunique"), spend=("order_id", "nunique"),
                                       review=("review", "mean"), late=("late", "mean")).reset_index()
stg = stg.sort_values("customers", ascending=False).head(12)
# recency buckets
cust["recency_bucket"] = pd.cut(cust.recency, [-1, 30, 90, 180, 365, 9999], labels=["0-30", "31-90", "91-180", "181-365", "365+"])
rec = cust.groupby("recency_bucket", observed=False).size().reset_index(name="customers")

metrics13 = {
    "customers": int(len(cust)), "repeat_rate": repeat_rate, "repeat90": float(repeat90),
    "avg_spend": float(cust.spend.mean()), "avg_freq": float(cust.freq.mean()),
    "avg_review": float(cust.review.mean()), "late_rate": float(cust.late.mean()),
    "segments": seg.to_dict(orient="records"), "cohort": coh.to_dict(orient="records"),
    "review_repeat": rv.to_dict(orient="records"), "states": stg.to_dict(orient="records"),
    "recency": rec.to_dict(orient="records"),
    "p75_spend": float(p75),
}

# ---------- R07 产品需求 ----------
itc = itf.merge(products[["product_id", "product_category_name"]], on="product_id", how="left").merge(cat, on="product_category_name", how="left")
catg = itc.groupby("product_category_name_english").agg(
    gmv=("gmv", "sum"), orders=("order_id", "nunique"), items=("order_item_id", "count"),
    price=("price", "mean"), review=("review", "mean"), late=("late", "mean"),
    days=("delivery_days", "mean")).reset_index().dropna(subset=["product_category_name_english"])
catg["share"] = catg.gmv / catg.gmv.sum()
catg["score"] = (catg.share * 100) * catg.review.fillna(4) / 5 * (1 - catg.late.fillna(0))
catg = catg.sort_values("gmv", ascending=False)
prods = itc.groupby("product_id").agg(gmv=("gmv", "sum"), orders=("order_id", "nunique"), price=("price", "mean"),
                                      review=("review", "mean"), late=("late", "mean")).reset_index()
prods = prods.merge(products[["product_id", "product_category_name"]], on="product_id", how="left").merge(cat, on="product_category_name", how="left")
prods = prods.dropna(subset=["product_category_name_english"]).sort_values("gmv", ascending=False).head(12)
month = itf.groupby("month").agg(gmv=("gmv", "sum"), orders=("order_id", "nunique"), items=("order_item_id", "count")).reset_index()
month = month[month.month.between("2017-01", "2018-08")]
# category pain: high late + low review
pain = catg.assign(pain=(catg.late * 100) + (5 - catg.review.fillna(4)) * 10).sort_values("pain", ascending=False).head(10)
# top categories monthly for demand? total only
metrics07 = {
    "categories": catg.head(15).to_dict(orient="records"), "products": prods.to_dict(orient="records"),
    "month": month.to_dict(orient="records"), "pain": pain.to_dict(orient="records"),
    "total_gmv": float(catg.gmv.sum()), "total_orders": int(itf.order_id.nunique()), "total_items": int(len(itf)),
    "avg_review": float(catg.review.mean()), "avg_late": float(catg.late.mean()),
}

(OUT / "metrics_r13.json").write_text(json.dumps(metrics13, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
(OUT / "metrics_r07.json").write_text(json.dumps(metrics07, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print("r13", metrics13["customers"], metrics13["repeat_rate"], metrics13["segments"])
print("r07", len(catg), metrics07["total_gmv"], metrics07["total_orders"])

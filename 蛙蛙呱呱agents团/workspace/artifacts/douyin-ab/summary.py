# -*- coding: utf-8 -*-
"""补充汇总：买家数、客单价、GMV 分组合计（对齐已跑出的 skill 结果）。"""
import csv
import json
import os

CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orders.csv")

rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
agg = {}
for r in rows:
    g = r["group"]
    a = agg.setdefault(g, {"n": 0, "buyers": 0, "gmv": 0.0})
    a["n"] += 1
    if r["converted"] == "1":
        a["buyers"] += 1
        a["gmv"] += float(r["amount"])

out = {}
for g, a in agg.items():
    out[g] = {
        "n": a["n"],
        "buyers": a["buyers"],
        "conversion": round(a["buyers"] / a["n"], 4),
        "gmv": round(a["gmv"], 2),
        "aov_buyer": round(a["gmv"] / a["buyers"], 2) if a["buyers"] else 0.0,
        "revenue_per_user": round(a["gmv"] / a["n"], 4),
    }
print(json.dumps(out, ensure_ascii=False, indent=2))

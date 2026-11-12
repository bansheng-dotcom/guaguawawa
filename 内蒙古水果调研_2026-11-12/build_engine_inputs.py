# -*- coding: utf-8 -*-
"""把指标库转成各角色引擎的输入（engine/*.csv|json），供 run_gates.py 真实调用。"""
from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ENG = ROOT / "engine"
ENG.mkdir(exist_ok=True)

M = json.loads((DATA / "底稿指标.json").read_text(encoding="utf-8"))
B = json.loads((DATA / "经营指标.json").read_text(encoding="utf-8"))
L2, L4, L6 = M["L2_全国周度"], M["L4_呼市零售"], M["L6_苹果分市场"]
U = B["unit"]


def write_csv(name: str, header: list[str], rows: list[list]) -> None:
    with (ENG / name).open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def nat_range(nw: str) -> tuple[str, str]:
    s, e = nw.split("-")
    return (f"{s[:4]}-{s[4:6]}-{s[6:8]}", f"{e[:4]}-{e[4:6]}-{e[6:8]}")


def ret_range(rw: str) -> tuple[str, str]:
    s, e = rw.split("~")
    return s, f"{s[:4]}-{e}"


# ---------------------------------------------------------------- ① 日度
write_csv("r06_日度.csv", ["date", "水果6种均价"],
          [[p["date"], p["value"]] for p in M["L1_全国日度"]["points"]])

# ---------------------------------------------------------------- ② 周度对齐（全国富士苹果 vs 呼市苹果零售）
nat = L2["table"]["富士苹果"]
ret = {w: v["price"] for w, v in L4["items"].get("苹果", {}).items()}
pairs = []
for rw, rp in sorted(ret.items(), key=lambda kv: kv[0][:10]):
    rs, re_ = ret_range(rw)
    d0, d1 = date.fromisoformat(rs), date.fromisoformat(re_)
    best, best_ov = None, -1
    for nw in nat:
        ns, ne = nat_range(nw)
        n0, n1 = date.fromisoformat(ns), date.fromisoformat(ne)
        ov = (min(d1, n1) - max(d0, n0)).days
        if ov > best_ov:
            best, best_ov = (nw, ns, ne), ov
    if best and best_ov >= 0:
        pairs.append([best[2], round(nat[best[0]]["this"], 2), rp, rw])
write_csv("r06_周度_苹果.csv", ["week_end", "全国富士苹果", "呼市苹果零售", "呼市周区间"], pairs)

# 篮子对篮子（9 周齐全，用于回归/相关）
basket = []
for rw, rp in sorted({w: v for w, v in L4["avg"].items()}.items(), key=lambda kv: kv[0][:10]):
    rs, re_ = ret_range(rw)
    d0, d1 = date.fromisoformat(rs), date.fromisoformat(re_)
    # 全国 6 种均价按周（周内日均）
    vals = [p["value"] for p in M["L1_全国日度"]["points"] if rs <= p["date"] <= re_]
    if vals:
        basket.append([re_, round(sum(vals) / len(vals), 3), rp, rw])
write_csv("r06_周度_篮子.csv", ["week_end", "全国6种均价", "呼市8种零售均价", "呼市周区间"], basket)

# ---------------------------------------------------------------- ③ 品类前后期（10 月 / 11 月均）
rows = []
for item in L2["items"]:
    d = L2["table"].get(item, {})
    for label, pref in (("10月", "202610"), ("11月", "202611")):
        vals = [v["this"] for w, v in d.items() if w[9:15] == pref]
        if vals:
            rows.append([item, label, round(sum(vals) / len(vals), 2)])
write_csv("r06_品类前后期.csv", ["品类", "期间", "价格"], rows)

# ---------------------------------------------------------------- ④ TCO：三种货源
tco = {
    "annual_rate_pct": 4.35,
    "quotes": [
        {"supplier": "赤峰产地直采（一车直发）", "currency": "CNY", "unit_price": 4.60, "qty": 10000,
         "defects_pct": 8.0, "main_freight": 2100, "lead_days": 2, "payment_terms_days": 7},
        {"supplier": "呼市东瓦窑批发（混级现结）", "currency": "CNY", "unit_price": 8.64, "qty": 10000,
         "defects_pct": 3.0, "main_freight": 120, "lead_days": 0, "payment_terms_days": 0},
        {"supplier": "北京新发地调运（跨省）", "currency": "CNY", "unit_price": 7.60, "qty": 10000,
         "defects_pct": 5.0, "main_freight": 4800, "lead_days": 2, "payment_terms_days": 15},
    ],
}
(ENG / "r15_tco_apple.json").write_text(json.dumps(tco, ensure_ascii=False, indent=1), encoding="utf-8")

for i, (sup, price, qty) in enumerate([
        ("赤峰宁城合作社（产地直采）", 4.60, 10000),
        ("呼和浩特东瓦窑批发市场", 8.64, 10000),
        ("北京新发地经销商（调运）", 7.60, 10000)], start=1):
    (ENG / f"r15_quote_{i}.json").write_text(json.dumps({
        "id": f"SQ-APPLE-00{i}", "supplier": sup, "status": "Submitted", "valid_till": "2026-11-30",
        "items": [{"item_code": "APPLE-FUJI", "qty": qty, "rate": price}],
        "total": round(price * qty, 2)}, ensure_ascii=False, indent=1), encoding="utf-8")

(ENG / "r15_supplier.json").write_text(json.dumps({
    "suppliers": [
        {"supplier_name": "宁城县果树经济林合作社联合社", "supplier_type": "Company",
         "payment_terms_days": 7, "status": "Active"},
        {"supplier_name": "赤峰西城市场果品经销商", "supplier_type": "Company",
         "payment_terms_days": 0, "status": "Active"},
        {"supplier_name": "北京新发地调运商（跨省）", "supplier_type": "Company",
         "payment_terms_days": 15, "status": "Active"},
    ]}, ensure_ascii=False, indent=1), encoding="utf-8")

(ENG / "r15_rfq.json").write_text(json.dumps({
    "id": "RFQ-APPLE-2026-11", "status": "Submitted", "required_by": "2026-11-20", "currency": "CNY",
    "suppliers": [{"supplier": "宁城县合作社"}, {"supplier": "赤峰西城经销商"}, {"supplier": "北京新发地调运商"}],
    "items": [{"item_code": "APPLE-FUJI", "qty": 10000}]}, ensure_ascii=False, indent=1), encoding="utf-8")

# ---------------------------------------------------------------- ⑤ CFO 健康检查（3,000 吨/年情景）
t = 3000 * 1000
revenue = round(t * U["wholesale"], 2)
cogs = round(t * U["total_cost"], 2)
gross = round(revenue - cogs, 2)
opex = 2_200_000.0
(ENG / "r03_healthcheck.json").write_text(json.dumps({
    "balance_sheet": {"assets": 12_000_000.0, "liabilities": 5_000_000.0, "equity": 7_000_000.0},
    "cash_flow": {"cash_begin": 3_000_000.0, "operating": round(gross - opex, 2), "investing": -B["roi"]["invest"],
                  "financing": 0.0, "cash_end": round(3_000_000.0 + gross - opex - B["roi"]["invest"], 2)},
    "income_statement": {"revenue": revenue, "cogs": cogs, "gross_profit": gross}}, ensure_ascii=False, indent=1), encoding="utf-8")

# ---------------------------------------------------------------- ⑥ 链路 SOP
(ENG / "r02_sop.json").write_text(json.dumps({
    "process_name": "赤峰产地苹果 → 呼市货架 的 48 小时链路",
    "purpose": "把赤峰产地苹果以 ≤5% 损耗、≤48 小时时效送到呼市门店/档口",
    "inputs": ["产地采购单", "质检单（糖度/硬度/规格）", "冷链车温控记录"],
    "steps": [
        {"name": "产地采收与分级", "owner": "r15", "action": "按 80# 一二级分选，剔除病果", "is_critical": True,
         "control_point": "糖度≥13、硬度≥6kg/cm²、次果率≤8%"},
        {"name": "预冷", "owner": "r15", "action": "差压预冷 8—12 小时至 0—4℃", "is_critical": True,
         "control_point": "果心温度 ≤4℃ 方可装车"},
        {"name": "冷链干线", "owner": "r15", "action": "赤峰→呼市 750km，全程 0—4℃", "is_critical": True,
         "control_point": "温控记录每 30 分钟一点，超温即扣款"},
        {"name": "销地入库与分拣", "owner": "r15", "action": "销地仓收货、复检、按门店分拣", "is_critical": False},
        {"name": "城配与上架", "owner": "r14", "action": "当日达门店，先进先出", "is_critical": True,
         "control_point": "到店温度 ≤6℃、破损率 ≤1%"},
        {"name": "周度复盘", "owner": "r06", "action": "损耗/时效/毛利三线对拍", "is_critical": False},
    ],
    "outputs": ["到店苹果", "损耗台账", "温控记录"],
    "approvers": ["r01", "r04"]}, ensure_ascii=False, indent=1), encoding="utf-8")

print("engine inputs ok:", sorted(p.name for p in ENG.glob("*")))
print("周度对齐对数:", len(pairs))
print("品类前后期行数:", len(rows))

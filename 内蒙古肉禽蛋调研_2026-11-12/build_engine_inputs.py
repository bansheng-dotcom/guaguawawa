# -*- coding: utf-8 -*-
"""为 R06 / R15 引擎准备真实输入文件（数据来自 data/ 下已核验底稿）"""
import csv, json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
ENG = os.path.join(ROOT, "engine")
os.makedirs(ENG, exist_ok=True)

# ---------- R06 输入：周度序列 ----------
egg_weekly = [
    ("2026-09-25", 11.10), ("2026-10-02", 10.76), ("2026-10-09", 10.42),
    ("2026-10-16", 10.05), ("2026-10-23", 9.77), ("2026-10-30", 9.84),
    ("2026-11-06", 9.93),
]
chicken_weekly = [
    ("2026-09-25", 17.90), ("2026-10-02", 17.82), ("2026-10-09", 17.70),
    ("2026-10-16", 17.68), ("2026-10-23", 17.70), ("2026-10-30", 17.73),
    ("2026-11-06", 17.79),
]
for name, rows in (("r06_周度_鸡蛋批发.csv", egg_weekly), ("r06_周度_白条鸡批发.csv", chicken_weekly)):
    with open(os.path.join(ENG, name), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["日期", "价格"])
        for d, v in rows: w.writerow([d, v])

# ---------- R06 输入：篮子前后期（用于 rootcause decompose） ----------
basket = [
    ("牛肉", "10月", 37.06), ("牛肉", "11月", 37.28),
    ("羊肉", "10月", 39.34), ("羊肉", "11月", 39.56),
    ("白条鸡", "10月", 11.92), ("白条鸡", "11月", 11.97),
    ("鸡蛋", "10月", 5.49), ("鸡蛋", "11月", 5.18),
    ("带鱼", "10月", 17.16), ("带鱼", "11月", 17.20),
    ("草鱼", "10月", 11.32), ("草鱼", "11月", 11.31),
    ("鲤鱼", "10月", 8.91), ("鲤鱼", "11月", 8.86),
]
with open(os.path.join(ENG, "r06_篮子_前后期.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["品类", "期间", "价格"])
    for r in basket: w.writerow(list(r))

# ---------- R06 输入：区域价格（用于 correlate / regression） ----------
region = [
    ("牛肉", 39.36, 33.02), ("羊肉", 40.14, 34.32), ("鸡肉", 11.86, 9.88),
    ("鸡蛋", 5.11, 4.94), ("带鱼", 19.99, 16.20), ("草鱼", 11.94, 10.35),
    ("鲤鱼", 9.74, 8.47),
]
with open(os.path.join(ENG, "r06_区域价格_呼市vs乌兰察布.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["品类", "呼和浩特", "乌兰察布"])
    for r in region: w.writerow(list(r))

# ---------- R15 输入：供应商主数据 ----------
supplier = {"suppliers": [
    {"supplier_name": "呼和浩特东瓦窑批发市场", "supplier_type": "Company", "payment_terms_days": 0, "status": "Active"},
    {"supplier_name": "乌兰察布集宁产地集配", "supplier_type": "Company", "payment_terms_days": 7, "status": "Active"},
    {"supplier_name": "赤峰敖汉定点屠宰厂", "supplier_type": "Company", "payment_terms_days": 15, "status": "Active"},
]}
json.dump(supplier, open(os.path.join(ENG, "r15_supplier.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ---------- R15 输入：RFQ（3 家比价） ----------
rfq = {"id": "RFQ-NMG-BEEF-001", "status": "Submitted", "required_by": "2026-11-30",
       "suppliers": [{"supplier": "呼和浩特东瓦窑批发市场"},
                     {"supplier": "乌兰察布集宁产地集配"},
                     {"supplier": "赤峰敖汉定点屠宰厂"}],
       "items": [{"item_code": "BEEF-BRISKET", "qty": 1000}]}
json.dump(rfq, open(os.path.join(ENG, "r15_rfq_beef.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ---------- R15 输入：三份报价 ----------
quotes = {
    "r15_quote_1_dongwayao.json": {"id": "SQ-BEEF-001", "supplier": "呼和浩特东瓦窑批发市场", "status": "Submitted",
        "valid_till": "2026-11-30", "items": [{"item_code": "BEEF-BRISKET", "qty": 1000, "rate": 36.00}], "total": 36000.0},
    "r15_quote_2_wulanchabu.json": {"id": "SQ-BEEF-002", "supplier": "乌兰察布集宁产地集配", "status": "Submitted",
        "valid_till": "2026-11-30", "items": [{"item_code": "BEEF-BRISKET", "qty": 1000, "rate": 33.02}], "total": 33020.0},
    "r15_quote_3_aohan.json": {"id": "SQ-BEEF-003", "supplier": "赤峰敖汉定点屠宰厂", "status": "Submitted",
        "valid_till": "2026-11-30", "items": [{"item_code": "BEEF-BRISKET", "qty": 1000, "rate": 27.56}], "total": 27560.0},
}
for fn, d in quotes.items():
    json.dump(d, open(os.path.join(ENG, fn), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ---------- R15 输入：TCO 对比（牛肉三种货源，1000 斤） ----------
tco_beef = {
    "annual_rate_pct": 4.35,
    "quotes": [
        {"supplier": "东瓦窑批发（现结）", "currency": "CNY", "unit_price": 36.00, "qty": 1000,
         "defects_pct": 1.5, "main_freight": 900, "lead_days": 0, "payment_terms_days": 0},
        {"supplier": "乌兰察布跨市（现结）", "currency": "CNY", "unit_price": 33.02, "qty": 1000,
         "defects_pct": 1.5, "main_freight": 900, "lead_days": 2, "payment_terms_days": 0},
        {"supplier": "赤峰合作屠宰（活牛折算白条）", "currency": "CNY", "unit_price": 27.56, "qty": 1000,
         "defects_pct": 1.5, "main_freight": 900, "lead_days": 3, "payment_terms_days": 15, "moq": 1500},
    ],
}
json.dump(tco_beef, open(os.path.join(ENG, "r15_tco_beef.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ---------- R15 输入：TCO 对比（鸡蛋两种货源，1000 斤） ----------
tco_egg = {
    "annual_rate_pct": 4.35,
    "quotes": [
        {"supplier": "全国批发口径（现结）", "currency": "CNY", "unit_price": 4.965, "qty": 1000,
         "defects_pct": 1.0, "main_freight": 250, "lead_days": 0, "payment_terms_days": 0},
        {"supplier": "敖汉产地直采（现结）", "currency": "CNY", "unit_price": 4.33, "qty": 1000,
         "defects_pct": 1.0, "main_freight": 300, "destination_charges": 100, "lead_days": 1, "payment_terms_days": 0},
    ],
}
json.dump(tco_egg, open(os.path.join(ENG, "r15_tco_egg.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print("inputs ready:", sorted(os.listdir(ENG)))

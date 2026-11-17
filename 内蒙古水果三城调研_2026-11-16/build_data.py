# -*- coding: utf-8 -*-
"""内蒙呼市/包头/赤峰三城水果价格、产地供价与链路调研：原始表 + 派生指标。

数据口径（逐条可回溯，见 data/sources.json）：
- 三城批发：农业农村部信息中心日行情（证券之星转载）。呼市东瓦窑 11-16、
  赤峰西城 11-16、包头友谊 11-11；呼市东瓦窑 11-09、赤峰西城 11-09 用于周环比。
- 呼市/赤峰零售：两市商务局生活必需品周报（11/2—11/8）；赤峰另有 10/26—11/1。
- 全区零售：内蒙古价格监测综合信息服务平台，红富士一级 11-05 零售价。
- 全国：农业农村部第 46 周 6 种水果批发均价；商务预报苹果/香蕉/梨周度序列。
- 产地：惠农网/一亩田 2026-11-14~15 产地代办价（宁城苹果、洛川富士、
  赵县梨、河口香蕉、卢龙巨峰、广西沙糖橘与沃柑、云南西瓜、丹东草莓）；
  赤峰市农牧局宁城苹果（酵素苹果 20 元/公斤）；通辽林草局塞外红一类果。
- 集散地：东瓦窑（12 万吨/年、17 亿元）、美通果品区（旺季日均 1000 吨）、
  赤峰雨润（41.3 万㎡、26.5 亿元、一期 9.8 万㎡/6 大厅/300 商铺）、
  郑州万邦（1500 万吨/1000 亿元/冷库 70 万吨）。
- 进口：智利车厘子 2026/27 产季出口 66.7 万吨、同比 +16%；1J/2J/3J
  早季批发 26/44/52 元/斤；丹东红颜礼盒 120 元/600g。
- 成本参数：干线 0.65 元/公斤·千公里、包装/装卸/进场/资金、损耗率均为
  声明假设（见 assumptions.json）。

本脚本只做三件事：落原始表、算派生量、写证据台账。不写报告。
"""
from __future__ import annotations

import csv
import json
import os
import statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

# --------------------------------------------------------------------------- #
# 1. 三城批发水果快照（元/公斤，农业农村部信息中心）
# --------------------------------------------------------------------------- #
CITY = {
    "呼和浩特": {
        "market": "东瓦窑", "date": "2026-11-16", "source": "S01",
        "items": {"富士苹果": 14.00, "鸭梨": 7.60, "巨峰葡萄": 15.00,
                  "香蕉": 6.00, "菠萝": 15.00, "西瓜": 6.00},
    },
    "包头": {
        "market": "友谊", "date": "2026-11-11", "source": "S02",
        "items": {"富士苹果": 8.00, "鸭梨": 6.00, "香蕉": 3.00},
    },
    "赤峰": {
        "market": "西城", "date": "2026-11-16", "source": "S03",
        "items": {"富士苹果": 6.00, "鸭梨": 4.80, "巨峰葡萄": 6.80,
                  "香蕉": 5.80, "菠萝": 6.80, "西瓜": 1.90},
    },
}

HOHHOT_1109 = {"富士苹果": 14.00, "鸭梨": 7.60, "巨峰葡萄": 15.00,
               "香蕉": 6.00, "菠萝": 15.00, "西瓜": 6.00}
CHIFENG_1109 = {"富士苹果": 5.90, "鸭梨": 4.70, "巨峰葡萄": 6.90,
                "香蕉": 5.70, "菠萝": 6.70, "西瓜": 1.80}

# --------------------------------------------------------------------------- #
# 2. 零售周度（元/公斤，两市商务局）
# --------------------------------------------------------------------------- #
RETAIL = [
    {"region": "呼和浩特", "period": "2026-11-02~11-08", "n": 8, "avg": 10.49,
     "wow": 0.6, "apple": 13.88, "pear": 7.48, "grape": 16.01,
     "banana": 7.81, "watermelon": 6.52, "citrus": 7.15, "mango": 15.06,
     "source": "S04"},
    {"region": "赤峰", "period": "2026-10-26~11-01", "n": 6, "avg": 9.71,
     "wow": 0.1, "apple": 13.99, "pear": 6.62, "grape": 15.67,
     "banana": 7.20, "watermelon": 5.63, "citrus": 9.14, "mango": None,
     "source": "S05"},
    {"region": "赤峰", "period": "2026-11-02~11-08", "n": 6, "avg": 9.71,
     "wow": 0.0, "apple": 13.63, "pear": 6.55, "grape": 16.05,
     "banana": 7.27, "watermelon": 5.73, "citrus": 9.01, "mango": None,
     "source": "S06"},
]

# --------------------------------------------------------------------------- #
# 3. 产地价（元/公斤；元/斤 × 2）
# --------------------------------------------------------------------------- #
ORIGIN = [
    {"origin": "赤峰宁城", "item": "富士苹果", "price": 6.00, "grade": "1 斤起售 3.00 元/斤", "date": "2026-11-15", "source": "S07"},
    {"origin": "赤峰宁城", "item": "富士苹果", "price": 5.00, "grade": "100 斤起售 2.50 元/斤", "date": "2026-11-15", "source": "S07"},
    {"origin": "赤峰宁城", "item": "富士苹果", "price": 4.00, "grade": "2000 斤起售 2.00 元/斤", "date": "2026-11-15", "source": "S07"},
    {"origin": "赤峰宁城", "item": "酵素苹果", "price": 20.00, "grade": "市场售价 10 元/斤", "date": "2026-10-22", "source": "S08"},
    {"origin": "通辽", "item": "塞外红苹果", "price": 20.00, "grade": "一类果 10 元/斤进新发地", "date": "2025-12-16", "source": "S09"},
    {"origin": "陕西洛川", "item": "富士苹果", "price": 7.00, "grade": "3.5 元/斤", "date": "2026-11-14", "source": "S10"},
    {"origin": "陕西洛川", "item": "富士苹果", "price": 6.00, "grade": "3.0 元/斤", "date": "2026-11-14", "source": "S10"},
    {"origin": "河北赵县", "item": "鸭梨", "price": 0.80, "grade": "0.40 元/斤", "date": "2026-11-15", "source": "S11"},
    {"origin": "河北赵县", "item": "雪花梨", "price": 1.60, "grade": "0.80 元/斤", "date": "2026-11-15", "source": "S12"},
    {"origin": "河北赵县", "item": "雪花梨", "price": 0.50, "grade": "0.25 元/斤", "date": "2026-11-15", "source": "S12"},
    {"origin": "云南河口", "item": "香蕉", "price": 2.52, "grade": "1.26 元/斤 通货", "date": "2026-11-14", "source": "S13"},
    {"origin": "云南河口", "item": "香蕉", "price": 1.68, "grade": "0.84 元/斤 通货", "date": "2026-11-14", "source": "S13"},
    {"origin": "河北卢龙", "item": "巨峰葡萄", "price": 1.60, "grade": "冷库套袋 0.80 元/斤", "date": "2026-11-15", "source": "S14"},
    {"origin": "河北昌黎", "item": "巨峰葡萄", "price": 3.40, "grade": "1.70 元/斤", "date": "2026-11-14", "source": "S15"},
    {"origin": "广西兴安", "item": "沙糖橘", "price": 6.40, "grade": "3.20 元/斤", "date": "2026-11-15", "source": "S16"},
    {"origin": "广西恭城", "item": "沙糖橘", "price": 5.20, "grade": "2.60 元/斤", "date": "2026-11-15", "source": "S16"},
    {"origin": "广西恭城", "item": "沃柑", "price": 2.60, "grade": "1.30 元/斤 无核", "date": "2026-11-15", "source": "S17"},
    {"origin": "广西荔浦", "item": "沃柑", "price": 7.02, "grade": "3.51 元/斤", "date": "2026-11-15", "source": "S17"},
    {"origin": "云南建水", "item": "西瓜", "price": 0.68, "grade": "0.34 元/斤", "date": "2026-11-14", "source": "S18"},
    {"origin": "云南瑞丽", "item": "西瓜", "price": 2.40, "grade": "缅甸黑美人 1.20 元/斤", "date": "2026-11-15", "source": "S18"},
    {"origin": "辽宁东港", "item": "草莓", "price": 31.70, "grade": "红颜 15.85 元/斤", "date": "2026-11-14", "source": "S19"},
    {"origin": "辽宁东港", "item": "草莓", "price": 37.74, "grade": "红颜 18.87 元/斤", "date": "2026-11-15", "source": "S19"},
]

# --------------------------------------------------------------------------- #
# 4. 全国与季节序列（元/公斤）
# --------------------------------------------------------------------------- #
NATIONAL_W46 = {
    "week": "2026-W46", "fruit6_avg": 6.64, "wow": 0.0, "yoy": -6.7,
    "grape_mom": 2.0, "watermelon_mom": 1.5, "banana_mom": 0.6,
    "pear_mom": -1.9, "pineapple_mom": -1.3, "apple_mom": -0.9,
    "source": "S20",
}

SERIES = [
    ("2025-11-21", 9.40, 5.37, 6.71),
    ("2025-12-05", 9.37, 5.47, 6.74),
    ("2025-12-19", 9.30, 5.73, 6.72),
    ("2026-01-16", 9.52, 5.85, 6.50),
    ("2026-02-20", 9.56, 6.45, 6.81),
    ("2026-03-20", 9.42, 6.47, 6.70),
    ("2026-11-06", 8.95, 5.25, 5.92),
]

# --------------------------------------------------------------------------- #
# 5. 集散节点与距离（公里，公路约数）
# --------------------------------------------------------------------------- #
NODES = [
    {"node": "赤峰宁城", "role": "苹果产地（25 万亩经济林）", "to_hohhot": 850, "to_baotou": 1000, "to_chifeng": 80, "source": "S21"},
    {"node": "赤峰雨润", "role": "蒙东/辽西一级集散", "to_hohhot": 850, "to_baotou": 1000, "to_chifeng": 15, "source": "S22"},
    {"node": "呼和浩特东瓦窑", "role": "区域二级分拨", "to_hohhot": 0, "to_baotou": 170, "to_chifeng": 850, "source": "S23"},
    {"node": "包头友谊", "role": "消费型批发市场", "to_hohhot": 170, "to_baotou": 0, "to_chifeng": 1000, "source": "S02"},
    {"node": "北京新发地", "role": "华北枢纽", "to_hohhot": 480, "to_baotou": 600, "to_chifeng": 420, "source": "A1"},
    {"node": "郑州万邦", "role": "全国果品集散", "to_hohhot": 950, "to_baotou": 1100, "to_chifeng": 1050, "source": "S24"},
    {"node": "河北赵县", "role": "梨产地", "to_hohhot": 600, "to_baotou": 700, "to_chifeng": 750, "source": "A1"},
    {"node": "云南河口", "role": "香蕉产地", "to_hohhot": 2600, "to_baotou": 2700, "to_chifeng": 2900, "source": "A1"},
]

# --------------------------------------------------------------------------- #
# 6. 成本模型（元/公斤；声明假设）
# --------------------------------------------------------------------------- #
COST = [
    {"chain": "A 宁城→赤峰西城 苹果", "item": "产地价", "value": 4.00, "basis": "宁城 2000 斤起 2.00 元/斤", "source": "S07"},
    {"chain": "A 宁城→赤峰西城 苹果", "item": "包装", "value": 0.30, "basis": "声明假设", "source": "A2"},
    {"chain": "A 宁城→赤峰西城 苹果", "item": "装卸短驳", "value": 0.05, "basis": "声明假设", "source": "A2"},
    {"chain": "A 宁城→赤峰西城 苹果", "item": "干线运输", "value": 0.05, "basis": "80km×0.65 元/公斤·千公里", "source": "A3"},
    {"chain": "A 宁城→赤峰西城 苹果", "item": "损耗摊销", "value": 0.22, "basis": "5% 损耗", "source": "A4"},
    {"chain": "A 宁城→赤峰西城 苹果", "item": "进场档口", "value": 0.10, "basis": "声明假设", "source": "A2"},
    {"chain": "A 宁城→赤峰西城 苹果", "item": "资金占用", "value": 0.02, "basis": "声明假设", "source": "A2"},
    {"chain": "B 宁城→呼市 苹果直发", "item": "产地价", "value": 4.00, "basis": "宁城 2000 斤起 2.00 元/斤", "source": "S07"},
    {"chain": "B 宁城→呼市 苹果直发", "item": "包装", "value": 0.35, "basis": "声明假设", "source": "A2"},
    {"chain": "B 宁城→呼市 苹果直发", "item": "装卸短驳", "value": 0.08, "basis": "声明假设", "source": "A2"},
    {"chain": "B 宁城→呼市 苹果直发", "item": "干线运输", "value": 0.55, "basis": "850km×0.65 元/公斤·千公里", "source": "A3"},
    {"chain": "B 宁城→呼市 苹果直发", "item": "损耗摊销", "value": 0.39, "basis": "8% 损耗", "source": "A4"},
    {"chain": "B 宁城→呼市 苹果直发", "item": "进场档口", "value": 0.12, "basis": "声明假设", "source": "A2"},
    {"chain": "B 宁城→呼市 苹果直发", "item": "资金占用", "value": 0.04, "basis": "声明假设", "source": "A2"},
    {"chain": "C 宁城→雨润→呼市 苹果", "item": "产地价", "value": 4.00, "basis": "宁城 2000 斤起 2.00 元/斤", "source": "S07"},
    {"chain": "C 宁城→雨润→呼市 苹果", "item": "包装", "value": 0.35, "basis": "声明假设", "source": "A2"},
    {"chain": "C 宁城→雨润→呼市 苹果", "item": "装卸短驳", "value": 0.10, "basis": "声明假设", "source": "A2"},
    {"chain": "C 宁城→雨润→呼市 苹果", "item": "中转档口", "value": 0.25, "basis": "声明假设", "source": "A2"},
    {"chain": "C 宁城→雨润→呼市 苹果", "item": "干线运输", "value": 0.55, "basis": "850km×0.65 元/公斤·千公里", "source": "A3"},
    {"chain": "C 宁城→雨润→呼市 苹果", "item": "损耗摊销", "value": 0.57, "basis": "11% 损耗（二次装卸）", "source": "A4"},
    {"chain": "C 宁城→雨润→呼市 苹果", "item": "进场档口", "value": 0.12, "basis": "声明假设", "source": "A2"},
    {"chain": "C 宁城→雨润→呼市 苹果", "item": "资金占用", "value": 0.05, "basis": "声明假设", "source": "A2"},
    {"chain": "D 赵县→呼市 鸭梨", "item": "产地价", "value": 0.80, "basis": "赵县 0.40 元/斤", "source": "S11"},
    {"chain": "D 赵县→呼市 鸭梨", "item": "包装", "value": 0.25, "basis": "声明假设", "source": "A2"},
    {"chain": "D 赵县→呼市 鸭梨", "item": "装卸短驳", "value": 0.08, "basis": "声明假设", "source": "A2"},
    {"chain": "D 赵县→呼市 鸭梨", "item": "干线运输", "value": 0.39, "basis": "600km×0.65 元/公斤·千公里", "source": "A3"},
    {"chain": "D 赵县→呼市 鸭梨", "item": "损耗摊销", "value": 0.09, "basis": "6% 损耗", "source": "A4"},
    {"chain": "D 赵县→呼市 鸭梨", "item": "进场档口", "value": 0.12, "basis": "声明假设", "source": "A2"},
    {"chain": "D 赵县→呼市 鸭梨", "item": "资金占用", "value": 0.03, "basis": "声明假设", "source": "A2"},
    {"chain": "E 河口→呼市 香蕉", "item": "产地价", "value": 2.52, "basis": "河口 1.26 元/斤 通货", "source": "S13"},
    {"chain": "E 河口→呼市 香蕉", "item": "包装", "value": 0.30, "basis": "声明假设", "source": "A2"},
    {"chain": "E 河口→呼市 香蕉", "item": "装卸短驳", "value": 0.10, "basis": "声明假设", "source": "A2"},
    {"chain": "E 河口→呼市 香蕉", "item": "干线运输", "value": 1.69, "basis": "2600km×0.65 元/公斤·千公里", "source": "A3"},
    {"chain": "E 河口→呼市 香蕉", "item": "损耗摊销", "value": 0.28, "basis": "6% 损耗", "source": "A4"},
    {"chain": "E 河口→呼市 香蕉", "item": "进场档口", "value": 0.12, "basis": "声明假设", "source": "A2"},
    {"chain": "E 河口→呼市 香蕉", "item": "资金占用", "value": 0.05, "basis": "声明假设", "source": "A2"},
]

# --------------------------------------------------------------------------- #
# 7. 情景（2027-01-16 相对 2026-11-16 的涨幅，%）
# --------------------------------------------------------------------------- #
SCEN = [
    {"scenario": "悲观（暖冬+消费弱）", "overall": -3.0, "apple": 0.0, "banana": 5.0,
     "pear": -4.0, "citrus": -15.0, "cherry": -35.0, "note": "柑橘集中上市、车厘子海运放量"},
    {"scenario": "基准（节前备货+正常降温）", "overall": 2.0, "apple": 1.3, "banana": 8.9,
     "pear": -3.1, "citrus": -10.0, "cherry": -30.0, "note": "沿用 2025-11→2026-01 同口径季节变化"},
    {"scenario": "乐观（寒潮封路+春节前置）", "overall": 9.0, "apple": 5.0, "banana": 15.0,
     "pear": 2.0, "citrus": 2.0, "cherry": -20.0, "note": "雨雪阻断南果北运，节前集中备货"},
]

# --------------------------------------------------------------------------- #
# 8. 品类运营（零售口径三城均价 + 声明损耗/周转/波动）
# --------------------------------------------------------------------------- #
CATOPS = [
    {"category": "苹果", "role": "利润+形象", "loss": 5.0, "turnover": 15.0, "volatility": 6.0,
     "note": "耐储、可分级、可礼盒"},
    {"category": "梨", "role": "稳价+搭配", "loss": 6.0, "turnover": 12.0, "volatility": 8.0,
     "note": "耐储但品种价差大"},
    {"category": "葡萄", "role": "利润", "loss": 12.0, "turnover": 5.0, "volatility": 12.0,
     "note": "冷库货单价高、损耗高"},
    {"category": "香蕉", "role": "流量+复购", "loss": 10.0, "turnover": 4.0, "volatility": 8.0,
     "note": "周转最快、现金流品"},
    {"category": "柑橘", "role": "流量", "loss": 8.0, "turnover": 7.0, "volatility": 18.0,
     "note": "旺季放量、价格下行"},
    {"category": "西瓜", "role": "季节引流", "loss": 15.0, "turnover": 2.0, "volatility": 35.0,
     "note": "反季价高量少"},
    {"category": "车厘子", "role": "利润+形象", "loss": 8.0, "turnover": 10.0, "volatility": 30.0,
     "note": "12—1 月进口旺季"},
]

CAT_PRICE = {"苹果": 13.76, "梨": 7.02, "葡萄": 16.03, "香蕉": 7.54,
             "西瓜": 6.13, "柑橘": 8.08, "车厘子": 52.00}

SPEC = [
    {"spec": "纸+膜袋", "price": 5.76, "note": "最低规格"},
    {"spec": "纸袋Φ70-84", "price": 7.60, "note": "主流规格"},
    {"spec": "纸袋Φ85以上", "price": 10.91, "note": "礼盒/精品"},
]


def _write_csv(name, header, rows):
    path = os.path.join(DATA, name)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.mean(xs), 2) if xs else 0.0


def _median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else 0.0


def _cv(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return 0.0
    m = statistics.mean(xs)
    return round(statistics.pstdev(xs) / m * 100, 1) if m else 0.0


def main() -> None:
    rows = []
    for city, pack in CITY.items():
        for item, price in pack["items"].items():
            rows.append([pack["date"], city, pack["market"], item, price,
                         "元/公斤", pack["source"]])
    for item, price in HOHHOT_1109.items():
        rows.append(["2026-11-09", "呼和浩特", "东瓦窑", item, price, "元/公斤", "S25"])
    for item, price in CHIFENG_1109.items():
        rows.append(["2026-11-09", "赤峰", "西城", item, price, "元/公斤", "S25#2"])
    _write_csv("market_prices_long.csv",
               ["date", "city", "market", "item", "price", "unit", "source"],
               sorted(rows, key=lambda r: (r[0], r[1], r[3])))

    _write_csv("retail_weekly.csv",
               ["region", "period", "n_items", "avg_price", "wow_pct", "apple",
                "pear", "grape", "banana", "watermelon", "citrus", "mango", "source"],
               [[r["region"], r["period"], r["n"], r["avg"], r["wow"], r["apple"],
                 r["pear"], r["grape"], r["banana"], r["watermelon"], r["citrus"],
                 "" if r["mango"] is None else r["mango"], r["source"]]
                for r in RETAIL])

    _write_csv("origin_prices.csv",
               ["origin", "item", "price", "grade", "date", "source"],
               [[r["origin"], r["item"], r["price"], r["grade"], r["date"], r["source"]]
                for r in ORIGIN])

    _write_csv("national_series.csv", ["date", "apple", "banana", "pear"],
               [[d, a, b, p] for d, a, b, p in SERIES])

    _write_csv("chain_nodes.csv",
               ["node", "role", "to_hohhot_km", "to_baotou_km", "to_chifeng_km", "source"],
               [[r["node"], r["role"], r["to_hohhot"], r["to_baotou"],
                 r["to_chifeng"], r["source"]] for r in NODES])

    _write_csv("cost_model.csv", ["chain", "item", "value", "unit", "basis", "source"],
               [[r["chain"], r["item"], r["value"], "元/公斤", r["basis"], r["source"]]
                for r in COST])

    _write_csv("scenarios.csv",
               ["scenario", "overall_pct", "apple_pct", "banana_pct", "pear_pct",
                "citrus_pct", "cherry_pct", "note"],
               [[r["scenario"], r["overall"], r["apple"], r["banana"], r["pear"],
                 r["citrus"], r["cherry"], r["note"]] for r in SCEN])

    _write_csv("category_ops.csv",
               ["category", "role", "loss_pct", "turnover_days", "volatility_pct",
                "retail_price", "note"],
               [[r["category"], r["role"], r["loss"], r["turnover"], r["volatility"],
                 CAT_PRICE[r["category"]], r["note"]] for r in CATOPS])

    _write_csv("spec_ladder.csv", ["spec", "price", "note"],
               [[r["spec"], r["price"], r["note"]] for r in SPEC])

    D = {}

    def put(key, name, value, unit="", period="", source="derived", formula=""):
        D[key] = {"id": key, "name": name, "value": round(float(value), 4),
                  "unit": unit, "period": period, "source": source,
                  "formula": formula, "inputs": ""}

    for city, pack in CITY.items():
        vals = list(pack["items"].values())
        put(f"D_{city}_mean", f"{city}{pack['market']}水果简单均价", _mean(vals),
            "元/公斤", pack["date"], pack["source"])
        put(f"D_{city}_n", f"{city}{pack['market']}水果品类数", len(vals),
            "个", pack["date"], pack["source"])

    common6 = sorted(set(CITY["呼和浩特"]["items"]) & set(CITY["赤峰"]["items"]))
    common3 = sorted(set(CITY["呼和浩特"]["items"]) & set(CITY["包头"]["items"])
                     & set(CITY["赤峰"]["items"]))
    put("D_common6_n", "呼市与赤峰共有水果品类数", len(common6), "个",
        "2026-11-16", "S01/S03")
    put("D_common3_n", "三城共有水果品类数", len(common3), "个",
        "2026-11-11~16", "S01/S02/S03")
    for city in ("呼和浩特", "赤峰"):
        put(f"D_common6_{city}_mean", f"呼赤共有{len(common6)}品在{city}的均价",
            _mean([CITY[city]["items"][i] for i in common6]), "元/公斤",
            CITY[city]["date"], CITY[city]["source"])
    for city in ("呼和浩特", "包头", "赤峰"):
        put(f"D_common3_{city}_mean", f"三城共有{len(common3)}品在{city}的均价",
            _mean([CITY[city]["items"][i] for i in common3]), "元/公斤",
            CITY[city]["date"], CITY[city]["source"])
    put("D_common6_cf_vs_hh", "呼赤6品篮子赤峰/呼市倍数",
        _mean([CITY["赤峰"]["items"][i] for i in common6]) /
        _mean([CITY["呼和浩特"]["items"][i] for i in common6]),
        "倍", "2026-11-16", "S01/S03")
    put("D_common3_bt_vs_hh", "三城3品篮子包头/呼市倍数",
        _mean([CITY["包头"]["items"][i] for i in common3]) /
        _mean([CITY["呼和浩特"]["items"][i] for i in common3]),
        "倍", "2026-11-11~16", "S01/S02")
    put("D_common3_cf_vs_hh", "三城3品篮子赤峰/呼市倍数",
        _mean([CITY["赤峰"]["items"][i] for i in common3]) /
        _mean([CITY["呼和浩特"]["items"][i] for i in common3]),
        "倍", "2026-11-11~16", "S01/S03")

    ratio_rows = []
    for item in common3:
        h = CITY["呼和浩特"]["items"][item]
        b = CITY["包头"]["items"][item]
        c = CITY["赤峰"]["items"][item]
        ratio_rows.append({"item": item, "h": h, "b": b, "c": c,
                           "ratio": round(max(h, b, c) / min(h, b, c), 3),
                           "spread": round(max(h, b, c) - min(h, b, c), 2),
                           "cv": _cv([h, b, c])})
    for item in common6:
        h = CITY["呼和浩特"]["items"][item]
        c = CITY["赤峰"]["items"][item]
        put(f"D_hhcf_{item}", f"{item}呼市/赤峰倍数", h / c, "倍",
            "2026-11-16", "S01/S03", f"{h}/{c}")
        put(f"D_hhcf_{item}_gap", f"{item}呼市-赤峰价差", h - c, "元/公斤",
            "2026-11-16", "S01/S03", f"{h}-{c}")
    for r in ratio_rows:
        put(f"D_ratio3_{r['item']}", f"{r['item']}三城最高/最低倍数", r["ratio"],
            "倍", "2026-11-11~16", "S01/S02/S03")
    put("D_ratio3_max", "三城同品最大价差倍数",
        max(r["ratio"] for r in ratio_rows), "倍", "2026-11-11~16", "S01/S02/S03")
    put("D_cv3_mean", "三城同品平均变异系数",
        _mean([r["cv"] for r in ratio_rows]), "%", "2026-11-11~16", "S01/S02/S03")

    for city, base in (("呼和浩特", HOHHOT_1109), ("赤峰", CHIFENG_1109)):
        cur = CITY[city]["items"]
        put(f"D_wow_{city}_6", f"{city}6品篮子周环比",
            (_mean([cur[i] for i in common6]) / _mean([base[i] for i in common6]) - 1) * 100,
            "%", "2026-11-09→11-16", "S25/S01" if city == "呼和浩特" else "S25/S03")
    put("D_wow_cf_apple", "赤峰富士苹果周环比",
        (6.00 / 5.90 - 1) * 100, "%", "2026-11-09→11-16", "S25/S03", "6.00/5.90-1")
    put("D_wow_cf_banana", "赤峰香蕉周环比", (5.80 / 5.70 - 1) * 100, "%",
        "2026-11-09→11-16", "S25/S03")
    put("D_wow_cf_watermelon", "赤峰西瓜周环比", (1.90 / 1.80 - 1) * 100, "%",
        "2026-11-09→11-16", "S25/S03")

    put("D_retail_hohhot", "呼和浩特8种水果零售均价", 10.49, "元/公斤",
        "2026-11-02~08", "S04")
    put("D_retail_chifeng", "赤峰6种水果零售均价", 9.71, "元/公斤",
        "2026-11-02~08", "S06")
    put("D_retail_gap", "呼市-赤峰水果零售价差", 10.49 - 9.71, "元/公斤",
        "2026-11-02~08", "S04/S06", "10.49-9.71")
    put("D_retail_gap_pct", "呼市相对赤峰水果零售溢价",
        (10.49 / 9.71 - 1) * 100, "%", "2026-11-02~08", "S04/S06")
    for k, label, hh, cf in (
        ("apple", "苹果", 13.88, 13.63),
        ("pear", "梨", 7.48, 6.55),
        ("grape", "葡萄", 16.01, 16.05),
        ("watermelon", "西瓜", 6.52, 5.73),
        ("citrus", "柑橘", 7.15, 9.01),
        ("banana", "香蕉", 7.81, 7.27),
    ):
        put(f"D_retail_{k}_hh", f"呼市{k}零售价", hh, "元/公斤", "2026-11", "S04")
        put(f"D_retail_{k}_cf", f"赤峰{k}零售价", cf, "元/公斤", "2026-11", "S06")
        put(f"D_retail_{k}_gap", f"呼市-赤峰{k}零售价差", hh - cf, "元/公斤",
            "2026-11", "S04/S06")
    put("D_ratio_hh_apple_retail_wholesale", "呼市苹果零售/东瓦窑批发倍数",
        13.88 / 14.00, "倍", "2026-11", "S01/S04", "13.88/14.00")
    put("D_ratio_cf_apple_retail_wholesale", "赤峰苹果零售/西城批发倍数",
        13.63 / 6.00, "倍", "2026-11", "S03/S06", "13.63/6.00")
    put("D_ratio_hh_watermelon", "呼市西瓜零售/批发倍数", 6.52 / 6.00, "倍",
        "2026-11", "S01/S04")
    put("D_ratio_cf_watermelon", "赤峰西瓜零售/批发倍数", 5.73 / 1.90, "倍",
        "2026-11", "S03/S06")
    put("D_ratio_hh_grape", "呼市葡萄零售/批发倍数", 16.01 / 15.00, "倍",
        "2026-11", "S01/S04")
    put("D_ratio_cf_grape", "赤峰葡萄零售/批发倍数", 16.05 / 6.80, "倍",
        "2026-11", "S03/S06")
    put("D_ratio_hh_pear", "呼市梨零售/批发倍数", 7.48 / 7.60, "倍",
        "2026-11", "S01/S04")
    put("D_ratio_cf_pear", "赤峰梨零售/批发倍数", 6.55 / 4.80, "倍",
        "2026-11", "S03/S06")
    put("D_retail_apple_nm", "内蒙古红富士一级零售价", 13.06, "元/公斤",
        "2026-11-05", "S26")
    put("D_ratio_nm_apple", "内蒙古苹果零售/全国苹果批发倍数", 13.06 / 8.95, "倍",
        "2026-11-05/11-06", "S26/S27")

    put("D_national_fruit6", "全国6种水果批发周均价", 6.64, "元/公斤",
        "2026-W46", "S20")
    put("D_national_fruit6_yoy", "全国6种水果批发同比", -6.7, "%",
        "2026-W46", "S20")
    put("D_national_fruit6_wow", "全国6种水果批发环比", 0.0, "%",
        "2026-W46", "S20")
    for k, name, v in (("grape", "巨峰葡萄", 2.0), ("watermelon", "西瓜", 1.5),
                       ("banana", "香蕉", 0.6), ("pear", "鸭梨", -1.9),
                       ("pineapple", "菠萝", -1.3), ("apple", "富士苹果", -0.9)):
        put(f"D_national_w46_{k}", f"全国{k}第46周环比", v, "%", "2026-W46", "S20")
    put("D_national_apple", "全国苹果批发价", 8.95, "元/公斤", "2026-11-06", "S27")
    put("D_national_banana", "全国香蕉批发价", 5.25, "元/公斤", "2026-11-06", "S27")
    put("D_national_pear", "全国梨批发价", 5.92, "元/公斤", "2026-11-06", "S27")
    put("D_apple_market_median", "全国56市场富士苹果中位价", 8.00, "元/公斤",
        "2026-11-11", "S28")
    put("D_apple_market_min", "全国56市场富士苹果最低价", 4.00, "元/公斤",
        "2026-11-11", "S28")
    put("D_apple_market_max", "全国56市场富士苹果最高价", 14.00, "元/公斤",
        "2026-11-11", "S28")
    put("D_apple_market_n", "富士苹果报价市场数", 56, "个", "2026-11-11", "S28")
    put("D_apple_market_spread", "全国富士苹果最高/最低倍数", 14.00 / 4.00, "倍",
        "2026-11-11", "S28")
    put("D_hh_vs_median", "呼市富士苹果相对全国中位溢价",
        (14.00 / 8.00 - 1) * 100, "%", "2026-11-11", "S01/S28")
    put("D_cf_vs_median", "赤峰富士苹果相对全国中位折价",
        (6.00 / 8.00 - 1) * 100, "%", "2026-11-11", "S03/S28")

    pairs = [
        ("D_o2w_apple_cf", "宁城苹果→赤峰西城", 4.00, 6.00, "S07/S03"),
        ("D_o2w_apple_hh", "宁城苹果→呼市同规格锚", 4.00, 8.95, "S07/S27"),
        ("D_o2w_apple_hh_premium", "宁城苹果→呼市东瓦窑标价", 4.00, 14.00, "S07/S01"),
        ("D_o2w_pear_hh", "赵县鸭梨→呼市东瓦窑", 0.80, 7.60, "S11/S01"),
        ("D_o2w_banana_hh", "河口香蕉→呼市东瓦窑", 2.52, 6.00, "S13/S01"),
        ("D_o2w_grape_cf", "卢龙冷库巨峰→赤峰西城", 1.60, 6.80, "S14/S03"),
        ("D_o2w_grape_hh", "卢龙冷库巨峰→呼市东瓦窑", 1.60, 15.00, "S14/S01"),
        ("D_o2w_watermelon_cf", "云南建水西瓜→赤峰西城", 0.68, 1.90, "S18/S03"),
        ("D_o2w_citrus_hh", "广西恭城沙糖橘→呼市柑橘零售", 5.20, 7.15, "S16/S04"),
    ]
    for key, label, o, w, src in pairs:
        put(key + "_o", f"{label}产地价", o, "元/公斤", "2026-11-14~16", src)
        put(key + "_w", f"{label}销地价", w, "元/公斤", "2026-11-14~16", src)
        put(key + "_gap", f"{label}价差", w - o, "元/公斤", "2026-11-14~16", src,
            f"{w}-{o}")
        put(key + "_x", f"{label}倍数", w / o, "倍", "2026-11-14~16", src,
            f"{w}/{o}")

    chains = defaultdict(list)
    for r in COST:
        chains[r["chain"]].append(r)
    landed = {}
    for chain, items in chains.items():
        total = round(sum(x["value"] for x in items), 2)
        landed[chain] = total
        tag = chain.split()[0]
        put(f"D_cost_{tag}", f"{chain}到岸成本", total, "元/公斤", "2026-11-16",
            "A2/A3/A4", "+".join(x["item"] for x in items))
        for r in items:
            keymap = {"产地价": "origin", "包装": "pack", "装卸短驳": "handle",
                      "中转档口": "hub", "干线运输": "transport",
                      "损耗摊销": "loss", "进场档口": "stall", "资金占用": "capital"}
            put(f"D_cost{tag}_{keymap.get(r['item'], 'other')}",
                f"{chain}{r['item']}", r["value"], "元/公斤", "2026-11-16", r["source"],
                r["basis"])
    put("D_landed_B", "宁城→呼市苹果到岸成本", landed["B 宁城→呼市 苹果直发"],
        "元/公斤", "2026-11-16", "A2/A3/A4")
    put("D_landed_C", "宁城经雨润→呼市苹果到岸成本", landed["C 宁城→雨润→呼市 苹果"],
        "元/公斤", "2026-11-16", "A2/A3/A4")
    put("D_hub_extra", "二次中转相对直发的到岸增量",
        landed["C 宁城→雨润→呼市 苹果"] - landed["B 宁城→呼市 苹果直发"],
        "元/公斤", "2026-11-16", "A2/A3/A4", "C-B")

    margins = {
        "A": (6.00, "A 宁城→赤峰西城 苹果", "S03/S07"),
        "B": (8.95, "B 宁城→呼市 苹果直发", "S27/S07"),
        "C": (8.95, "C 宁城→雨润→呼市 苹果", "S27/S07"),
        "D": (7.60, "D 赵县→呼市 鸭梨", "S01/S11"),
        "E": (6.00, "E 河口→呼市 香蕉", "S01/S13"),
    }
    for tag, (price, chain, src) in margins.items():
        m = round(price - landed[chain], 2)
        put(f"D_margin_{tag}", f"{chain}批发毛利", m, "元/公斤", "2026-11-16", src,
            f"{price}-{landed[chain]}")
        put(f"D_marginpct_{tag}", f"{chain}批发毛利率", m / price * 100, "%",
            "2026-11-16", src, f"({price}-{landed[chain]})/{price}")
    put("D_banana_transport_share", "河口→呼市香蕉运费占到岸成本",
        1.69 / landed["E 河口→呼市 香蕉"] * 100, "%", "2026-11-16", "A3", "1.69/E")

    base_m = 8.95 - landed["B 宁城→呼市 苹果直发"]
    put("D_sens_transport20", "运费+20%后的毛利", base_m - 0.55 * 0.20, "元/公斤",
        "2026-11-16", "A3")
    put("D_sens_loss4", "损耗8%降到4%后的毛利",
        8.95 - (landed["B 宁城→呼市 苹果直发"] - 0.39 + 4.98 * 0.04),
        "元/公斤", "2026-11-16", "A4")
    put("D_sens_price10", "批发价-10%后的毛利", base_m - 8.95 * 0.10, "元/公斤",
        "2026-11-16", "S27")
    put("D_sens_grade30", "分级溢价+30%后的毛利", base_m + 8.95 * 0.30, "元/公斤",
        "2026-11-16", "A5")
    put("D_sens_origin10", "产地价+10%后的毛利", base_m - 4.00 * 0.10, "元/公斤",
        "2026-11-16", "S07")
    put("D_sens_direct", "中转改直发后的毛利增量", landed["C 宁城→雨润→呼市 苹果"]
        - landed["B 宁城→呼市 苹果直发"], "元/公斤", "2026-11-16", "A2/A3/A4")

    for r in SCEN:
        tag = r["scenario"][:2]
        put(f"D_scen_{tag}_overall", f"{r['scenario']}6种水果篮子涨幅", r["overall"],
            "%", "2027-01-16", "A6")
        put(f"D_scen_{tag}_price", f"{r['scenario']}6种水果篮子价格",
            6.64 * (1 + r["overall"] / 100), "元/公斤", "2027-01-16", "S20/A6")
        for k in ("apple", "banana", "pear", "citrus", "cherry"):
            put(f"D_scen_{tag}_{k}", f"{r['scenario']}{k}涨幅", r[k], "%",
                "2027-01-16", "A6")

    put("D_season_apple", "苹果 11-21→次年 1-16 变化",
        (9.52 / 9.40 - 1) * 100, "%", "2025-11-21→2026-01-16", "S27")
    put("D_season_banana", "香蕉 11-21→次年 1-16 变化",
        (5.85 / 5.37 - 1) * 100, "%", "2025-11-21→2026-01-16", "S27")
    put("D_season_pear", "梨 11-21→次年 1-16 变化",
        (6.50 / 6.71 - 1) * 100, "%", "2025-11-21→2026-01-16", "S27")
    put("D_season_apple_price", "苹果次年 1-16 批发价", 9.52, "元/公斤",
        "2026-01-16", "S27")
    put("D_season_banana_price", "香蕉次年 1-16 批发价", 5.85, "元/公斤",
        "2026-01-16", "S27")
    put("D_season_pear_price", "梨次年 1-16 批发价", 6.50, "元/公斤",
        "2026-01-16", "S27")
    put("D_yoy_apple", "全国苹果同比", (8.95 / 9.40 - 1) * 100, "%",
        "2026-11-06 vs 2025-11-21", "S27")
    put("D_yoy_banana", "全国香蕉同比", (5.25 / 5.37 - 1) * 100, "%",
        "2026-11-06 vs 2025-11-21", "S27")
    put("D_yoy_pear", "全国梨同比", (5.92 / 6.71 - 1) * 100, "%",
        "2026-11-06 vs 2025-11-21", "S27")

    for r in CATOPS:
        cat = r["category"]
        price = CAT_PRICE[cat]
        gross = round(price * (1 - r["loss"] / 100), 2)
        turns = 30 / r["turnover"]
        monthly = gross * turns
        put(f"D_ops_{cat}_price", f"{cat}三城零售均价", price, "元/公斤",
            "2026-11", "S04/S06")
        put(f"D_ops_{cat}_gross", f"{cat}扣损后单位毛利", gross, "元/公斤",
            "2026-11", "A4")
        put(f"D_ops_{cat}_turns", f"{cat}月周转次数", turns, "次/月", "2026-11", "A7")
        put(f"D_ops_{cat}_monthly", f"{cat}单公斤月毛利额", monthly, "元/公斤·月",
            "2026-11", "A7")
        put(f"D_ops_{cat}_score", f"{cat}运营评分", min(100, monthly / r["volatility"] * 10),
            "分", "2026-11", "A4/A7")
    put("D_ops_citrus_turns", "柑橘月周转次数", 30 / 7, "次/月", "2026-11", "A7")
    put("D_ops_cherry_turns", "车厘子月周转次数", 30 / 10, "次/月", "2026-11", "A7")

    put("D_spec_membrane", "纸+膜袋富士苹果价", 5.76, "元/公斤", "2026-11-12", "S29")
    put("D_spec_70_84", "纸袋Φ70-84富士苹果价", 7.60, "元/公斤", "2026-11-12", "S29")
    put("D_spec_85", "纸袋Φ85以上富士苹果价", 10.91, "元/公斤", "2026-11-12", "S29")
    put("D_spec_70_84_x", "纸袋Φ70-84相对膜袋溢价",
        (7.60 / 5.76 - 1) * 100, "%", "2026-11-12", "S29")
    put("D_spec_85_x", "纸袋Φ85以上相对膜袋溢价",
        (10.91 / 5.76 - 1) * 100, "%", "2026-11-12", "S29")
    put("D_spec_85_vs_70", "纸袋Φ85以上相对Φ70-84溢价",
        (10.91 / 7.60 - 1) * 100, "%", "2026-11-12", "S29")
    mix = 0.6 * 6.00 + 0.3 * 7.60 + 0.1 * 10.91
    put("D_grade_mix", "统货6.0按60/30/10分级的综合售价", mix, "元/公斤",
        "2026-11-16", "S03/S29", "0.6*6+0.3*7.6+0.1*10.91")
    put("D_grade_gain", "分级相对统货的售价增益", (mix / 6.00 - 1) * 100, "%",
        "2026-11-16", "S03/S29")
    put("D_grade_gain_per_kg", "分级相对统货的单位增益", mix - 6.00, "元/公斤",
        "2026-11-16", "S03/S29")
    put("D_premium_apple", "呼市富士苹果相对全国中位溢价",
        (14.00 / 8.00 - 1) * 100, "%", "2026-11-11", "S01/S28")
    put("D_ningcheng_enzyme_x", "宁城酵素苹果相对普通苹果倍数",
        20.00 / 4.00, "倍", "2026-10-22", "S08/S07")
    put("D_ningcheng_enzyme_gap", "宁城酵素苹果相对普通苹果价差",
        20.00 - 4.00, "元/公斤", "2026-10-22", "S08/S07")
    put("D_strawberry_box", "丹东红颜礼盒零售价", 200.0, "元/公斤",
        "2026-11-14", "S30", "120 元/600g")
    put("D_strawberry_box_x", "丹东草莓礼盒相对产地通货倍数",
        200.0 / 31.70, "倍", "2026-11-14", "S30/S19")
    put("D_cherry_1j", "智利车厘子1J批发价", 52.0, "元/公斤", "2026-11-12", "S31")
    put("D_cherry_2j", "智利车厘子2J批发价", 88.0, "元/公斤", "2026-11-12", "S31")
    put("D_cherry_3j", "智利车厘子3J批发价", 104.0, "元/公斤", "2026-11-12", "S31")
    put("D_cherry_3j_vs_1j", "车厘子3J相对1J倍数", 104.0 / 52.0, "倍",
        "2026-11-12", "S31")
    put("D_cherry_export", "智利车厘子本季出口量", 66.7, "万吨", "2026/27 产季", "S31")
    put("D_cherry_export_yoy", "智利车厘子出口同比", 16.0, "%", "2026/27 产季", "S31")

    put("D_hub_dwy_volume", "东瓦窑年交易量", 12, "万吨/年", "2025", "S23")
    put("D_hub_dwy_value", "东瓦窑年交易额", 17, "亿元/年", "2025", "S23")
    put("D_hub_dwy_merchants", "东瓦窑经营商户数", 423, "家", "2025", "S23")
    put("D_hub_meitong_day", "美通果品区旺季日均交易量", 1000, "吨/日", "2026", "S32")
    put("D_hub_yurun_area", "赤峰雨润规划建筑面积", 41.3, "万平方米", "2026", "S22")
    put("D_hub_yurun_invest", "赤峰雨润总投资", 26.5, "亿元", "2026", "S22")
    put("D_hub_yurun_phase1", "赤峰雨润一期面积", 9.8, "万平方米", "2026", "S22")
    put("D_hub_yurun_halls", "赤峰雨润一期交易大厅", 6, "个", "2026", "S22")
    put("D_hub_yurun_shops", "赤峰雨润一期商铺", 300, "间", "2026", "S22")
    put("D_hub_wanbang_volume", "郑州万邦年交易量", 1500, "万吨/年", "2025", "S24")
    put("D_hub_wanbang_value", "郑州万邦年交易额", 1000, "亿元/年", "2025", "S24")
    put("D_hub_wanbang_cold", "郑州万邦冷库库容", 70, "万吨", "2025", "S24")
    put("D_hub_wanbang_outshare", "郑州万邦外销占比", 40, "%", "2025", "S24")
    put("D_ningcheng_area", "宁城经济林面积", 25, "万亩", "2025", "S21")
    put("D_ningcheng_output", "宁城年产果品", 16.8, "万吨", "2025", "S21")
    put("D_ningcheng_value", "宁城林果产值", 8.2, "亿元", "2025", "S21")
    put("D_ningcheng_unit", "宁城果品折算单价", 8.2 * 10000 * 10000 / (16.8 * 10000 * 1000),
        "元/公斤", "2025", "S21", "8.2 亿元/16.8 万吨")

    for key, name, val in (("D_dist_ningcheng_cf", "宁城→赤峰公路距离", 80),
                           ("D_dist_cf_hh", "赤峰→呼市公路距离", 850),
                           ("D_dist_bt_hh", "包头→呼市公路距离", 170),
                           ("D_dist_zx_hh", "赵县→呼市公路距离", 600),
                           ("D_dist_hk_hh", "河口→呼市公路距离", 2600),
                           ("D_dist_xfd_hh", "北京新发地→呼市公路距离", 480),
                           ("D_dist_wb_hh", "郑州万邦→呼市公路距离", 950)):
        put(key, name, val, "公里", "声明假设", "A1")

    put("D_opt_A_margin", "选项A 一车28吨毛利", 3.42 * 28000, "元/车",
        "2026-11-16", "A8", "3.42*28000")
    put("D_opt_B_margin", "选项B 一车28吨毛利（加分级）",
        (3.42 + mix - 6.00) * 28000, "元/车", "2026-11-16", "A8",
        "(3.42+1.45)*28000")
    put("D_opt_B_unit", "选项B 单位毛利", 3.42 + mix - 6.00, "元/公斤",
        "2026-11-16", "A8")
    put("D_opt_C_margin", "选项C 礼盒单位毛利", 8.80, "元/公斤",
        "2026-11-16", "A9")
    put("D_opt_A_invest", "选项A 周转资金", 50, "万元", "2026-11-16", "A10")
    put("D_opt_B_invest", "选项B 冷库与分拣投入", 180, "万元", "2026-11-16", "A10")
    put("D_opt_C_invest", "选项C 品牌与包装投入", 260, "万元", "2026-11-16", "A10")
    put("D_opt_stop", "跨城加仓停止线", 0.30, "元/公斤", "2026-11-16", "A11")

    put("D_retail_citrus_mom", "呼市柑橘零售环比", -6.8, "%", "2026-10-26~11-01", "S04")
    put("D_grade_gain_truck", "28 吨分级相对统货的增益", (mix - 6.00) * 28000, "元/车",
        "2026-11-16", "S03/S29", "0.971*28000")
    put("D_loss_reduction", "损耗 8%降到 4% 的单位成本节省",
        0.39 - 4.98 * 0.04, "元/公斤", "2026-11-16", "A4")
    put("D_total_gain", "三项动作合计可回收",
        landed["C 宁城→雨润→呼市 苹果"] - landed["B 宁城→呼市 苹果直发"]
        + (0.39 - 4.98 * 0.04) + (mix - 6.00),
        "元/公斤", "2026-11-16", "A2/A3/A4")
    put("D_season_apple_start", "苹果 11-21 批发价", 9.40, "元/公斤",
        "2025-11-21", "S27")
    put("D_season_banana_start", "香蕉 11-21 批发价", 5.37, "元/公斤",
        "2025-11-21", "S27")
    put("D_season_pear_start", "梨 11-21 批发价", 6.71, "元/公斤",
        "2025-11-21", "S27")
    put("D_banana_baotou_vs_national", "包头香蕉相对全国香蕉", 3.00 / 5.25 * 100,
        "%", "2026-11-11/11-06", "S02/S27")

    put("D_role_n", "参与角色数", 7, "个", "2026-11-16", "R01")
    put("D_req_n", "需求域数", 6, "个", "2026-11-16", "R01")

    values = list(D.values())
    split = 120
    with open(os.path.join(DATA, "derived_metrics.json"), "w", encoding="utf-8") as f:
        json.dump({"metrics": values[:split]}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(DATA, "derived_extra.json"), "w", encoding="utf-8") as f:
        json.dump({"metrics": values[split:]}, f, ensure_ascii=False, indent=1)

    SOURCES = [
        {"id": "S01", "title": "2026年11月16日内蒙古呼和浩特市东瓦窑农副产品批发市场价格行情", "org": "农业农村部信息中心", "date": "2026-11-16", "type": "government", "url": "https://futures.stockstar.com/IG2026111600013402.shtml"},
        {"id": "S02", "title": "2026年11月11日内蒙包头市友谊蔬菜批发市场价格行情", "org": "农业农村部信息中心", "date": "2026-11-11", "type": "government", "url": "https://futures.stockstar.com/IG2026111100024831.shtml"},
        {"id": "S03", "title": "2026年11月16日内蒙赤峰西城市场价格行情", "org": "农业农村部信息中心", "date": "2026-11-16", "type": "government", "url": "https://futures.stockstar.com/IG2026111600013404.shtml"},
        {"id": "S04", "title": "呼和浩特市2026年11月2日至11月8日生活必需品市场运行分析（水果零售）", "org": "呼和浩特市商务局", "date": "2026-11-10", "type": "government", "url": "http://swj.huhhot.gov.cn/tjxx/202611/t20261110_2049154.html"},
        {"id": "S05", "title": "赤峰市10月26日—11月1日生活必需品市场动态分析（水果零售）", "org": "赤峰市商务局", "date": "2026-11-03", "type": "government", "url": "https://cif.mofcom.gov.cn/site/html/neimenggu/html/15362952/2026/11/3/1793696966731.html"},
        {"id": "S06", "title": "赤峰市11月2日—11月8日生活必需品市场动态分析（水果零售）", "org": "赤峰市商务局", "date": "2026-11-11", "type": "government", "url": "https://cif.mofcom.gov.cn/cif/html/market_scanner/2026/11/1794367457799.html"},
        {"id": "S07", "title": "赤峰宁城苹果产地代办价（1/100/2000 斤起售 3.00/2.50/2.00 元/斤）", "org": "惠农网", "date": "2026-11-15", "type": "marketplace", "url": "https://m.cnhnb.com/p/pingguo-0-98-0-0-1/"},
        {"id": "S08", "title": "内蒙古宁城13万亩苹果绘就乡村振兴新图景（酵素苹果 20 元/公斤）", "org": "赤峰市农牧局", "date": "2026-10-22", "type": "government", "url": "http://nmj.chifeng.gov.cn/zwxx/sndt/nmsz/202610/t20261022_2837524.html"},
        {"id": "S09", "title": "通辽市塞外红苹果一类果 10 元/斤进入北京新发地", "org": "通辽市林草局", "date": "2025-12-16", "type": "government", "url": "https://www.tongliao.gov.cn/zjtl/fztl/tltf/nmy/202512/t20251216_1021786.html"},
        {"id": "S10", "title": "陕西洛川冷库纸袋富士 70# 以上半商品 3.0—3.5 元/斤", "org": "生鲜果品日度策略报告", "date": "2026-11-14", "type": "industry_report", "url": "https://notice.10jqka.com.cn/api/original/ec1fbea01275842.pdf"},
        {"id": "S11", "title": "河北赵县鸭梨产地价 0.40 元/斤", "org": "惠农网", "date": "2026-11-15", "type": "marketplace", "url": "https://m.cnhnb.com/p/liz-0-3-0-111_41316-4/"},
        {"id": "S12", "title": "河北赵县雪花梨产地价 0.25—0.80 元/斤", "org": "惠农网", "date": "2026-11-15", "type": "marketplace", "url": "https://m.cnhnb.com/p/liz-0-3-1146-21_21597-1/"},
        {"id": "S13", "title": "云南河口香蕉产地价 0.84—1.26 元/斤", "org": "惠农网/一亩田", "date": "2026-11-14", "type": "marketplace", "url": "https://m.cnhnb.com/p/xiangj-0-25-0-0-10/"},
        {"id": "S14", "title": "河北卢龙冷库套袋巨峰葡萄 0.80 元/斤", "org": "惠农网", "date": "2026-11-15", "type": "marketplace", "url": "https://m.cnhnb.com/p/putao-0-0-1594-0-250/"},
        {"id": "S15", "title": "河北昌黎巨峰葡萄 1.70 元/斤", "org": "惠农网", "date": "2026-11-14", "type": "marketplace", "url": "https://www.cnhnb.com/hangqing/cdlist-2001324-1594-0-0-0-1/"},
        {"id": "S16", "title": "广西沙糖橘产地价 2.60—3.20 元/斤", "org": "惠农网", "date": "2026-11-15", "type": "marketplace", "url": "https://m.cnhnb.com/p/ganju-0-0-4622-78_31057,21_1035-6/"},
        {"id": "S17", "title": "广西沃柑产地价 1.30—3.51 元/斤", "org": "惠农网", "date": "2026-11-15", "type": "marketplace", "url": "https://www.cnhnb.com/hangqing/cdlist-2001686-2943-20-0-0-2/"},
        {"id": "S18", "title": "云南西瓜产地价 0.34—1.20 元/斤（含缅甸黑美人）", "org": "惠农网", "date": "2026-11-14", "type": "marketplace", "url": "https://www.cnhnb.com/hangqing/q-2003191-0-0-25/"},
        {"id": "S19", "title": "辽宁丹东红颜草莓产地价 15.85—18.87 元/斤", "org": "惠农网/一亩田", "date": "2026-11-15", "type": "marketplace", "url": "https://m.ymt.com/hangqing/juhe-7252"},
        {"id": "S20", "title": "2026年第46周国内外农产品市场动态（6种水果 6.64 元/公斤，同比 -6.7%）", "org": "农业农村部市场与信息化司", "date": "2026-11-16", "type": "government", "url": "http://www.agri.cn/sj/jcyj/202611/t20261116_8884013.htm"},
        {"id": "S21", "title": "内蒙古宁城13万亩苹果：经济林 25 万亩、年产 16.8 万吨、产值 8.2 亿元", "org": "赤峰市农牧局", "date": "2026-10-22", "type": "government", "url": "http://nmj.chifeng.gov.cn/zwxx/sndt/nmsz/202610/t20261022_2837524.html"},
        {"id": "S22", "title": "赤峰雨润：辐射蒙东和辽西的农产品流通集散中心（41.3 万㎡、26.5 亿元）", "org": "雨润集团/内蒙古新闻网", "date": "2026", "type": "media", "url": "http://www.yurun.com/news/news-detail.html?id=263&classfy=1"},
        {"id": "S23", "title": "东瓦窑市场：423 家商户、2025 年交易量 12 万吨、交易额 17 亿元", "org": "全国城市农贸中心联合会", "date": "2026", "type": "industry_report", "url": "https://www.cawa.org.cn/content/details_13790_17221.html"},
        {"id": "S24", "title": "郑州万邦：年交易量 1500 万吨、交易额 1000 亿元、辐射内蒙古", "org": "新华网河南频道", "date": "2026-09-29", "type": "media", "url": "http://ha.xinhuanet.com/20260929/6d6b126b5a034e8c8ffacc0116734ba1/c.html"},
        {"id": "S25", "title": "2026年11月9日内蒙古呼和浩特市东瓦窑/内蒙赤峰西城市场价格行情", "org": "农业农村部信息中心", "date": "2026-11-09", "type": "government", "url": "https://4g.stockstar.com/detail/IG2026110900006757"},
        {"id": "S26", "title": "内蒙古价格监测：苹果（红富士一级）零售 6.53 元/500 克", "org": "内蒙古价格监测综合信息服务平台", "date": "2026-11-05", "type": "government", "url": "http://www.nmgjgjc.com.cn/jgjcwz/"},
        {"id": "S27", "title": "商务预报：全国苹果/香蕉/梨批发价格周度走势（2025-11 至 2026-11）", "org": "商务部商务预报", "date": "2026-11-06", "type": "government", "url": "https://cif.mofcom.gov.cn/cif/html/mobile/dataDetail.html?id=224089"},
        {"id": "S28", "title": "2026年11月11日全国主要批发市场富士苹果价格行情（56 个市场）", "org": "农业农村部信息中心", "date": "2026-11-11", "type": "government", "url": "http://futures.stockstar.com/IG2026111100024473.shtml"},
        {"id": "S29", "title": "北京新发地富士苹果分规格报价（纸+膜袋 5.76 / Φ70-84 7.60 / Φ85+ 10.91）", "org": "北京新发地", "date": "2026-11-12", "type": "database", "url": "http://xinfadi.com.cn:8099/minipricedetail.html"},
        {"id": "S30", "title": "丹东草莓上市：礼盒 120 元/600 克，较上市初期 150—160 元回落", "org": "浙江在线", "date": "2026-11-16", "type": "media", "url": "http://zjnews.zjol.com.cn/zjnews/202611/t20261116_32029456.shtml"},
        {"id": "S31", "title": "智利车厘子本季出口 66.7 万吨、同比 +16%；1J/2J/3J 批发 26/44/52 元/斤", "org": "新浪财经/光明网", "date": "2026-11-12", "type": "media", "url": "https://finance.sina.com.cn/jjxw/2026-11-12/doc-iniymsif1223760.shtml"},
        {"id": "S32", "title": "美通果品区：旺季日均交易约 1000 吨，辐射乌兰察布、鄂尔多斯", "org": "食全食美集团", "date": "2026", "type": "media", "url": "http://www.sqsm.com/article/list/25/navid/3.html"},
    ]
    with open(os.path.join(DATA, "sources.json"), "w", encoding="utf-8") as f:
        json.dump({"topic": "内蒙古呼市/包头/赤峰三城水果价格、产地供价与链路优化调研",
                   "sources": SOURCES}, f, ensure_ascii=False, indent=1)

    ASSUMPTIONS = {
        "items": [
            {"id": "A1", "metric": "公路距离", "value": 850, "unit": "公里", "note": "宁城→赤峰约 80km、赤峰→呼市约 850km、包头→呼市 170km、赵县→呼市 600km、河口→呼市 2600km、新发地→呼市 480km、万邦→呼市 950km；均为公路约数"},
            {"id": "A2", "metric": "包装+装卸+进场+资金", "value": 0.35, "unit": "元/公斤", "note": "包装 0.25—0.35、装卸 0.05—0.10、进场 0.10—0.12、资金 0.02—0.05；行业常见区间，声明假设"},
            {"id": "A3", "metric": "干线运输单价", "value": 0.65, "unit": "元/公斤·千公里", "note": "按冷链/普货整车折算，0.65 元/公斤·千公里；真实运价随车型、装载率、季节议价变化"},
            {"id": "A4", "metric": "损耗率", "value": 8.0, "unit": "%", "note": "苹果 5%—8%、梨 6%、香蕉 6%—8%、葡萄 12%、柑橘 8%—10%、西瓜 15%；中转二次装卸取 11%"},
            {"id": "A5", "metric": "分级溢价", "value": 30.0, "unit": "%", "note": "新发地纸+膜袋 5.76 → Φ70-84 7.60（+31.9%）→ Φ85+ 10.91（+89.4%）；取 30% 为保守口径"},
            {"id": "A6", "metric": "季节涨幅", "value": 2.0, "unit": "%", "note": "基准情景 11/16→1/16 6 种水果篮子 +2%；按 2025-11-21→2026-01-16 苹果 +1.3%、香蕉 +8.9%、梨 -3.1% 加权，不是价格承诺"},
            {"id": "A7", "metric": "品类运营评分", "value": 10.0, "unit": "分", "note": "评分 = 扣损后单位毛利 × 月周转次数 ÷ 波动率 × 10，封顶 100；用于排序，不是绝对收益"},
            {"id": "A8", "metric": "单车装载", "value": 28, "unit": "吨/车", "note": "9.6 米/13 米冷链车常见装载 20—28 吨，取 28 吨"},
            {"id": "A9", "metric": "礼盒单位毛利", "value": 8.8, "unit": "元/公斤", "note": "礼盒售价 20 元/公斤 − 产地精品 5.0 − 包装 2.0 − 冷链 1.2 − 损耗 1.0 − 渠道 2.0；声明假设"},
            {"id": "A10", "metric": "投入", "value": 180, "unit": "万元", "note": "A 周转 50 万；B 冷库+分拣 180 万；C 品牌+包装+冷库 260 万；为量级假设"},
            {"id": "A11", "metric": "跨城加仓停止线", "value": 0.30, "unit": "元/公斤", "note": "扣完运费/损耗/人工后，跨城毛利低于 0.30 元/公斤不再加仓"},
        ]
    }
    with open(os.path.join(DATA, "assumptions.json"), "w", encoding="utf-8") as f:
        json.dump(ASSUMPTIONS, f, ensure_ascii=False, indent=1)

    obs = []
    oid = 0
    for city, pack in CITY.items():
        for item, price in pack["items"].items():
            oid += 1
            obs.append({"id": f"O{oid:03d}", "indicator": f"{city}{pack['market']}{item}批发价",
                        "value": price, "unit": "元/公斤", "period": pack["date"],
                        "region": city,
                        "url": next(s["url"] for s in SOURCES if s["id"] == pack["source"]),
                        "quote": f"{item} {price} 元/公斤", "grade": "批发均价"})
    for r in ORIGIN:
        oid += 1
        obs.append({"id": f"O{oid:03d}", "indicator": f"{r['origin']}{r['item']}产地价",
                    "value": r["price"], "unit": "元/公斤", "period": r["date"],
                    "region": r["origin"],
                    "url": next(s["url"] for s in SOURCES if s["id"] == r["source"]),
                    "quote": f"{r['item']} {r['price']} 元/公斤（{r['grade']}）",
                    "grade": r["grade"]})
    with open(os.path.join(DATA, "obs_fruit.json"), "w", encoding="utf-8") as f:
        json.dump({"topic": "三城水果价格与产地供价", "observations": obs}, f,
                  ensure_ascii=False, indent=1)

    print(json.dumps({
        "files": sorted(os.listdir(DATA)),
        "derived_count": len(D),
        "common6": len(common6), "common3": len(common3),
        "city_means": {c: D[f"D_{c}_mean"]["value"] for c in CITY},
        "baskets6": {c: D[f"D_common6_{c}_mean"]["value"] for c in ("呼和浩特", "赤峰")},
        "landed": landed,
        "margins": {k: D[f"D_margin_{k}"]["value"] for k in "ABCDE"},
        "grade_mix": round(mix, 2),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

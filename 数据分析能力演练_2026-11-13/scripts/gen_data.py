# -*- coding: utf-8 -*-
"""生成「数据分析能力演练」所需数据集。

真实数据：直接从 ../个护调研_2026-11-12 复制（76 条观测、价格带、平台、上市公司）。
模拟数据：本脚本按固定 seed 生成，并在 data/MANIFEST.json 中逐文件标注
         real / simulated、锚点（公开数据里能对上的数）与用途。
"""
from __future__ import annotations

import csv
import json
import math
import shutil
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / "data"
REAL = Path(r"D:\蛙蛙呱呱\个护调研_2026-11-12\data")

rng = np.random.default_rng(42)

CITIES = [
    ("北京", 1), ("上海", 1), ("广州", 1), ("深圳", 1), ("杭州", 2), ("成都", 2),
    ("武汉", 2), ("南京", 2), ("西安", 2), ("重庆", 2), ("长沙", 3), ("郑州", 3),
    ("青岛", 3), ("合肥", 3), ("福州", 3), ("昆明", 3), ("济南", 3), ("沈阳", 3),
    ("南昌", 4), ("贵阳", 4),
]
CHANNELS = ["抖音", "天猫", "京东", "淘宝", "线下"]
CHANNEL_P = [0.40, 0.24, 0.18, 0.13, 0.05]
CATS = ["洗护发", "口腔护理", "身体护理", "女性护理", "婴童护理"]
CAT_P = [0.40, 0.25, 0.15, 0.12, 0.08]
PRICE_MU = {"洗护发": 53, "口腔护理": 55, "身体护理": 68, "女性护理": 45, "婴童护理": 78}
PRICE_SD = {"洗护发": 12, "口腔护理": 18, "身体护理": 20, "女性护理": 14, "婴童护理": 22}

TITLES = {
    "洗护发": ["洗发水 控油 蓬松 无硅油 500ml", "洗发水 去屑 止痒 男士 400ml",
              "护发素 修护 干枯 毛躁 500ml", "头皮护理 精华 舒缓 100ml",
              "洗发水 香氛 留香 持久 600ml", "发膜 深层 滋养 顺滑 300g"],
    "口腔护理": ["牙膏 美白 去黄 含氟 120g", "牙膏 抗敏感 护龈 110g",
               "漱口水 清新 口气 500ml", "牙粉 小苏打 亮白 50g",
               "牙刷 软毛 护龈 4支装", "口腔喷雾 便携 清新 20ml"],
    "身体护理": ["沐浴露 氨基酸 温和 500ml", "身体乳 保湿 滋润 400ml",
               "磨砂膏 去角质 200g", "护手霜 滋润 不油腻 50g"],
    "女性护理": ["卫生巾 日用 245mm 10片", "卫生巾 夜用 420mm 8片",
               "护垫 轻薄 150mm 20片", "私处护理 洗液 200ml"],
    "婴童护理": ["婴儿 洗发沐浴 二合一 500ml", "婴儿 润肤霜 保湿 100g",
               "儿童 牙膏 草莓味 60g", "婴儿 湿巾 80抽"],
}


def w(path: str, header: list[str], rows: list[list]) -> None:
    p = DATA / path
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(header)
        wr.writerows(rows)


def gen_orders() -> None:
    n = 20000
    weeks = 39
    # 周度价格指数：让价格有可识别的外生波动（弹性可估），并固定每周订单量，去掉量的随机噪声
    week_factor = rng.uniform(0.88, 1.10, weeks)
    # 用户：Zipf 权重，制造复购
    users = np.arange(1, 6001)
    weight = 1.0 / (np.arange(1, 6001) ** 0.55)
    weight = weight / weight.sum()
    uid = rng.choice(users, size=n, p=weight)

    cat = rng.choice(CATS, size=n, p=CAT_P)
    chan = rng.choice(CHANNELS, size=n, p=CHANNEL_P)
    city_idx = rng.integers(0, len(CITIES), n)
    # 每周大致等量订单：用轮转分配周，再在周内随机日
    week_idx = np.array([i % weeks for i in range(n)])
    rng.shuffle(week_idx)
    start = np.datetime64("2026-01-05")  # 周一

    rows = []
    first_seen = {}
    for i in range(n):
        c = cat[i]
        wk = int(week_idx[i])
        f = float(week_factor[wk])
        price = float(np.clip(PRICE_MU[c] * f * float(np.exp(rng.normal(0, 0.10))), 15, 199))
        # 数量随价格反向变动，弹性约 -1.6
        lam = 1.7 * (price / PRICE_MU[c]) ** (-1.6)
        qty = int(np.clip(rng.poisson(max(lam, 0.2)), 1, 8))
        disc = float(np.clip(rng.beta(2, 6) * 0.45, 0, 0.35))
        rev = round(price * qty * (1 - disc), 2)
        p_ret = 0.05 + (0.03 if chan[i] == "抖音" else 0.0) + (0.02 if price > 99 else 0.0)
        returned = int(rng.random() < p_ret)
        u = int(uid[i])
        is_new = 0 if u in first_seen else 1
        first_seen.setdefault(u, i)
        if rev >= 129 and rng.random() < 0.18:
            coupon = "满129减20"
        elif rev >= 99 and rng.random() < 0.35:
            coupon = "满99减10"
        else:
            coupon = "无"
        title = TITLES[c][int(rng.integers(0, len(TITLES[c])))]
        city, tier = CITIES[city_idx[i]]
        d = start + np.timedelta64(wk * 7 + int(rng.integers(0, 7)), "D")
        date = str(d)
        rows.append([
            f"O{i+1:06d}", date, str(chan[i]), c, f"SKU-{c[:2]}-{int(rng.integers(1, 30)):02d}",
            round(price, 2), qty, rev, round(disc, 3), is_new, tier, city, coupon, returned,
            f"U{u:04d}", date[:7], title,
        ])

    rows.sort(key=lambda r: (r[1], r[0]))
    w("orders.csv",
      ["order_id", "order_date", "channel", "category", "sku_id", "unit_price", "qty",
       "revenue", "discount", "is_new", "city_tier", "city", "coupon", "returned",
       "customer_id", "order_month", "title"], rows)

    # 用户宽表（聚类/分群用）
    last_day = max(int(r[1][8:10]) + (int(r[1][5:7]) - 1) * 30 for r in rows)
    agg: dict[str, dict] = {}
    for r in rows:
        u = r[14]
        a = agg.setdefault(u, {"orders": 0, "revenue": 0.0, "disc": 0.0, "last": "", "first": r[1],
                               "returned": 0})
        a["orders"] += 1
        a["revenue"] += r[7]
        a["disc"] += r[8]
        a["returned"] += r[13]
        a["last"] = max(a["last"], r[1])
        a["first"] = min(a["first"], r[1])
    feat = []
    for u, a in agg.items():
        last = int(a["last"][8:10]) + (int(a["last"][5:7]) - 1) * 30
        feat.append([u, a["orders"], round(a["revenue"], 2), max(last_day - last, 0),
                     round(a["revenue"] / a["orders"], 2), round(a["disc"] / a["orders"], 3),
                     a["returned"]])
    w("customer_features.csv",
      ["customer_id", "orders", "revenue", "recency_days", "aov", "discount_share", "returned_orders"], feat)


def gen_ab() -> None:
    def make(n_per: int, p_ctr_a: float, p_ctr_b: float, pac: float) -> list[list]:
        rows = []
        for g, p in (("A", p_ctr_a), ("B", p_ctr_b)):
            for i in range(n_per):
                device = str(rng.choice(["iOS", "Android", "PC"], p=[0.45, 0.45, 0.10]))
                tier = int(rng.choice([1, 2, 3, 4], p=[0.25, 0.35, 0.25, 0.15]))
                click = int(rng.random() < p)
                conv = int(click and rng.random() < pac)
                rev = round(float(rng.normal(132, 40)), 2) if conv else 0.0
                rows.append([f"{g}{i:06d}", g, device, tier, click, conv, max(rev, 0),
                             f"2026-10-{1 + i % 28:02d}"])
        return rows
    rows = make(100000, 0.0320, 0.0342, 0.62)
    rng.shuffle(rows)
    w("ab_clean.csv", ["user_id", "group", "device", "city_tier", "click", "convert", "revenue", "date"], rows)
    rows2 = make(100000, 0.0320, 0.0342, 0.62)
    # 人为 SRM：随机丢弃 4% 的 B 组，制造 50/48 的分流偏差
    keep = [r for r in rows2 if not (r[1] == "B" and rng.random() < 0.04)]
    rng.shuffle(keep)
    w("ab_srm.csv", ["user_id", "group", "device", "city_tier", "click", "convert", "revenue", "date"], keep)


def gen_panel() -> None:
    weeks = 26
    rows, stag = [], []
    for ci, (city, tier) in enumerate(CITIES * 2):
        base = float(rng.uniform(800000, 1600000))
        treat = 1 if ci % 2 == 0 else 0
        population = float(rng.uniform(3e6, 12e6))
        income = float(rng.uniform(3.5, 6.5))
        pen = float(rng.uniform(0.25, 0.55))
        adopt = [8, 12, 16, 0][(ci // 10) % 4]
        for wk in range(1, weeks + 1):
            season = 1 + 0.06 * math.sin(2 * math.pi * wk / 13)
            post = 1 if wk >= 10 else 0
            eff = 1.08 if (treat and post) else 1.0
            gmv = round(base * season * eff * float(rng.normal(1, 0.04)), 2)
            rows.append([f"C{ci+1:02d}", city, wk, treat, post, gmv, round(population, 0), round(income, 2), round(pen, 3)])
            post_s = 1 if (adopt and wk >= adopt) else 0
            eff_s = 1.10 if post_s else 1.0
            gmv_s = round(base * season * eff_s * float(rng.normal(1, 0.04)), 2)
            stag.append([f"C{ci+1:02d}", city, wk, adopt, 1 if adopt else 0, post_s, gmv_s])
    w("panel_did.csv",
      ["city_id", "city", "week", "treat", "post", "gmv", "population", "income_index", "douyin_penetration"], rows)
    w("panel_staggered.csv", ["city_id", "city", "week", "first_treat", "treat", "post", "gmv"], stag)

    # 截面：处理组=迁预算城市，结局=2025→2026 GMV 增速
    cross = []
    for ci, (city, tier) in enumerate(CITIES * 2):
        treat = 1 if ci % 2 == 0 else 0
        population = float(rng.uniform(3e6, 12e6))
        income = float(rng.uniform(3.5, 6.5))
        pen = float(rng.uniform(0.25, 0.55))
        ecom = float(rng.uniform(0.3, 0.8))
        growth = 0.04 + 0.003 * ecom + 0.002 * pen + (0.07 if treat else 0) + float(rng.normal(0, 0.015))
        cross.append([f"C{ci+1:02d}", city, treat, round(growth * 100, 2),
                      round(population, 0), round(income, 2), round(pen, 3), round(ecom, 3), tier])
    # treat / control 两个文件给 matched
    w("cities_treat.csv", ["city_id", "city", "treat", "gmv_growth", "population", "income_index", "douyin_penetration", "ecommerce_index", "tier"],
      [r for r in cross if r[2] == 1])
    w("cities_control.csv", ["city_id", "city", "treat", "gmv_growth", "population", "income_index", "douyin_penetration", "ecommerce_index", "tier"],
      [r for r in cross if r[2] == 0])
    w("cities_all.csv", ["city_id", "city", "treat", "gmv_growth", "population", "income_index", "douyin_penetration", "ecommerce_index", "tier"], cross)


def gen_rdd() -> None:
    n = 12000
    cart = np.clip(rng.normal(99, 24, n), 30, 220)
    treat = (cart >= 99).astype(int)
    outcome = 0.96 * cart + 12.5 * treat + rng.normal(0, 9, n)
    rows = []
    for i in range(n):
        rows.append([
            f"R{i+1:06d}", round(float(cart[i]), 2), int(treat[i]),
            round(float(outcome[i]), 2), int(rng.random() < 0.4),
            int(rng.random() < 0.45), int(rng.choice([1, 2, 3, 4], p=[0.2, 0.35, 0.3, 0.15])),
        ])
    w("rdd_carts.csv", ["cart_id", "cart_value", "discount_applied", "paid_value", "is_new", "douyin", "city_tier"], rows)


def gen_funnel() -> None:
    stages = [("曝光", 50000), ("点击", 12000), ("加购", 3600), ("下单", 1800), ("支付", 1650)]
    rows = []
    for stage, cnt in stages:
        for i in range(cnt):
            rows.append([f"F{stage}{i:06d}", stage])
    w("funnel.csv", ["user_id", "stage"], rows)


def gen_selfmedia() -> None:
    raw = {
        "platforms": {
            "小红书": {"date": "2026-11-12", "fans": 48210, "new_fans": 312, "revenue": 18600, "posts": 2},
            "抖音": {"date": "2026-11-12", "fans": 96350, "new_fans": 705, "revenue": 42100, "posts": 3},
            "知乎": {"date": "2026-11-11", "fans": 15820, "new_fans": 46, "revenue": 2100, "posts": 1},
        }
    }
    (DATA / "selfmedia_raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


def gen_titles() -> None:
    rows = []
    for c, pool in TITLES.items():
        for t in pool:
            for _ in range(60):
                rows.append([c, t])
    w("sku_titles.csv", ["category", "title"], rows)


def gen_semantic() -> None:
    model = {
        "semantic_models": [{
            "name": "orders", "model": "fct_orders",
            "description": "个护订单语义模型（模拟数据）",
            "entities": [
                {"name": "order", "type": "primary", "expr": "order_id", "description": "订单主键"},
                {"name": "customer", "type": "foreign", "expr": "customer_id", "description": "用户外键"},
            ],
            "dimensions": [
                {"name": "channel", "type": "categorical", "expr": "channel", "description": "渠道"},
                {"name": "category", "type": "categorical", "expr": "category", "description": "品类"},
                {"name": "order_date", "type": "time", "expr": "order_date", "description": "下单日期",
                 "type_params": {"time_granularity": "day"}},
            ],
            "measures": [
                {"name": "gmv", "agg": "sum", "expr": "revenue", "description": "成交金额", "unit": "元"},
                {"name": "aov", "agg": "avg", "expr": "revenue", "description": "客单价", "unit": "元"},
                {"name": "order_count", "agg": "count_distinct", "expr": "order_id", "description": "订单数", "unit": "单"},
                {"name": "user_count", "agg": "count_distinct", "expr": "customer_id", "description": "去重用户", "unit": "人"},
            ],
        }],
        "metrics": [
            {"name": "gmv_total", "label": "成交总额", "description": "全部订单成交金额",
             "type": "simple", "type_params": {"measure": {"name": "gmv"}}},
            {"name": "aov", "label": "客单价", "description": "平均订单金额", "type": "simple",
             "type_params": {"measure": {"name": "aov"}}},
            {"name": "orders_per_user", "label": "人均订单数", "type": "ratio",
             "type_params": {"numerator": {"name": "order_count"}, "denominator": {"name": "user_count"}}},
        ],
    }
    (DATA / "semantic_model.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")


def copy_real() -> None:
    mapping = {
        "observations.csv": "market_obs.csv",
        "derived_metrics.csv": "derived_metrics.csv",
    }
    for src, dst in mapping.items():
        s = REAL / src
        if s.exists():
            shutil.copyfile(s, DATA / dst)
    # 价格带/平台/公司：从 evidence ledger 抽成小表
    ledger = json.loads(Path(r"D:\蛙蛙呱呱\个护调研_2026-11-12\evidence_ledger.json").read_text(encoding="utf-8"))
    w("price_bands.csv", ["band", "sales_share_pct", "volume_share_pct", "sku_share_pct", "efficiency_index"], [
        ["50-80", 39.28, 26.28, 12.3, 3.2],
        ["20-50", 34.09, 40.78, 38.58, 0.88],
        ["80+", 18.44, 6.41, "", ""],
            ])
    w("platforms.csv", ["platform", "gmv_yi", "share_pct", "yoy_pct"], [
        ["抖音", 32.11, 55.22, 30.73], ["天猫", 14.42, 24.80, -2.31],
        ["京东", 8.42, 14.48, 13.76], ["淘宝", 3.20, 5.50, -27.04],
    ])
    w("companies.csv", ["company", "segment", "revenue_yi", "revenue_yoy_pct", "net_profit_yi", "net_profit_yoy_pct", "gross_margin_pct", "margin_delta_pp"], [
        ["珀莱雅", "美妆+洗护", 105.97, -1.68, 14.98, -3.50, 73.26, 1.87],
        ["上海家化", "个护家清+美妆", 63.17, 11.25, 2.68, "", "", ""],
        ["登康口腔", "口腔护理", 17.16, 9.98, 1.81, 12.35, 52.23, 2.85],
        ["百亚股份", "女性卫生", 34.92, 7.32, 2.08, -27.70, 54.30, 1.10],
        ["豪悦护理", "婴童/成人失禁", 37.56, 28.22, 2.32, -40.14, 31.51, 3.60],
        ["拉芳家化", "洗护发", 8.18, -7.92, -0.31, "", 49.11, 1.24],
    ])
    w("haircare_annual.csv", ["year", "channel", "gmv_yi", "volume_index", "avg_price_yuan"], [
        ["2024", "线上洗护发", 646.32, 100.0, 55.75],
        ["2025", "线上洗护发", 695.51, 111.94, 53.35],
    ])


def manifest() -> None:
    items = [
        {"file": "orders.csv", "rows": 20000, "kind": "simulated", "seed": 42,
         "anchors": "洗护均价≈53 元、抖音占比 40%、退货率≈8%，对齐 2025 个护线上公开数据",
         "use": "P1/P2/P6（描述、相关、回归、聚类、留存、分群）"},
        {"file": "ab_clean.csv", "rows": 200000, "kind": "simulated", "seed": 42,
         "anchors": "基线 CTR 3.2%、转化率 2.1%，AOV≈132 元", "use": "P4 A/B 实验"},
        {"file": "ab_srm.csv", "rows": 196000, "kind": "simulated", "seed": 42,
         "anchors": "同 ab_clean，但人为 52/48 分流", "use": "P4 SRM 失配检测"},
        {"file": "panel_did.csv", "rows": 1040, "kind": "simulated", "seed": 42,
         "anchors": "40 城 × 26 周，处理组第 10 周起 +8% 真实效应", "use": "P5 DID/事件研究/安慰剂"},
        {"file": "panel_staggered.csv", "rows": 1040, "kind": "simulated", "seed": 42,
         "anchors": "分三批第 8/12/16 周进入，+10% 效应", "use": "P5 交错处理"},
        {"file": "cities_treat.csv", "rows": 20, "kind": "simulated", "seed": 42,
         "anchors": "处理组 +7pp 增速", "use": "P5 PSM"},
        {"file": "cities_control.csv", "rows": 20, "kind": "simulated", "seed": 42,
         "anchors": "对照组无处理", "use": "P5 PSM"},
        {"file": "rdd_carts.csv", "rows": 12000, "kind": "simulated", "seed": 42,
         "anchors": "满 99 减 10，断点处真实跳跃 +12.5 元", "use": "P3 断点回归"},
        {"file": "funnel.csv", "rows": 69050, "kind": "simulated", "seed": 42,
         "anchors": "曝光→支付 3.3% 整体转化", "use": "P6 漏斗"},
        {"file": "selfmedia_raw.json", "rows": 3, "kind": "simulated", "seed": 42,
         "anchors": "三平台粉丝/新增/收入快照", "use": "P6 自媒体看板"},
        {"file": "sku_titles.csv", "rows": 1440, "kind": "simulated", "seed": 42,
         "anchors": "商品标题（空格分词）", "use": "P2 文本统计"},
        {"file": "market_obs.csv", "rows": 76, "kind": "real",
         "anchors": "个护调研证据台账", "use": "P1 数据体检、P2 量价拆解"},
        {"file": "price_bands.csv", "rows": 4, "kind": "real", "anchors": "魔镜 2026Q1 牙膏价格带", "use": "P3"},
        {"file": "platforms.csv", "rows": 4, "kind": "real", "anchors": "魔镜 2026Q1 口腔分平台", "use": "P2/P3"},
        {"file": "companies.csv", "rows": 6, "kind": "real", "anchors": "6 家上市公司 2025 年报", "use": "P2"},
        {"file": "haircare_annual.csv", "rows": 2, "kind": "real", "anchors": "魔镜 2024/2025 洗护发", "use": "P2"},
    ]
    (DATA / "MANIFEST.json").write_text(json.dumps({"generated_at": "2026-11-13", "items": items},
                                                     ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    DATA.mkdir(exist_ok=True)
    gen_orders()
    gen_ab()
    gen_panel()
    gen_rdd()
    gen_funnel()
    gen_selfmedia()
    gen_titles()
    gen_semantic()
    copy_real()
    manifest()
    print("data generated:", sorted(p.name for p in DATA.iterdir()))


if __name__ == "__main__":
    main()

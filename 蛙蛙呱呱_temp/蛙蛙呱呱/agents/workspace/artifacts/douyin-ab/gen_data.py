# -*- coding: utf-8 -*-
"""抖音商品店铺 A/B 测试 · 模拟数据生成器（确定性，seed 固定可复算）。

场景：商品详情页改版 A/B 实验
  - control   对照组：当前详情页（旧版）
  - treatment 处理组：新版详情页（高清主图 + 卖点前置 + 缩短加载 + 更强 CTA）

指标口径（对齐 ab-experiment 语义层）：
  - converted  是否下单转化（0/1，主指标）
  - amount     每用户营收额（元，次指标；未下单=0）
  - group      control / treatment 二分
  - date       进入实验日期（ISO）
"""
import csv
import math
import os
import random
from datetime import date, timedelta

SEED = 20261106
N_CONTROL = 8180      # 对照组人数（轻微失衡，用于展示 SRM 检测）
N_TREAT = 8220        # 处理组人数
P_CONTROL = 0.050     # 对照组转化率 5.0%
P_TREAT = 0.060       # 处理组转化率 6.0%（相对提升 20%）
AOV_MU = 4.50         # lognormal mu（约 e^4.5 ≈ 90 元）
AOV_SIGMA = 0.38      # lognormal sigma（右偏，覆盖 9.9~999 元）

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orders.csv")

rng = random.Random(SEED)
rows = []
uid = 0
for grp, n, p in (("control", N_CONTROL, P_CONTROL),
                  ("treatment", N_TREAT, P_TREAT)):
    for _ in range(n):
        uid += 1
        day = (date(2026, 10, 26) + timedelta(days=rng.randrange(14))).isoformat()  # 14 天实验周期
        converted = 1 if rng.random() < p else 0
        if converted:
            amount = round(min(999.0, max(9.9, math.exp(rng.normalvariate(AOV_MU, AOV_SIGMA)))), 2)
        else:
            amount = 0.0
        rows.append({
            "user_id": f"U{uid:05d}",
            "group": grp,
            "converted": converted,
            "amount": f"{amount:.2f}",
            "date": day,
        })

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["user_id", "group", "converted", "amount", "date"])
    w.writeheader()
    w.writerows(rows)

print(f"wrote {len(rows)} rows -> {OUT}")
print(f"control={N_CONTROL} treatment={N_TREAT}")

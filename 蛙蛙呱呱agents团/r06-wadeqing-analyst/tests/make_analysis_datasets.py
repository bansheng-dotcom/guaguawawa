# -*- coding: utf-8 -*-
"""生成 T8a 的三份带“预埋真因”的分析数据集（确定性 LCG，可复算）。

为什么不用 examples/*.json 自证：那份只能验结构，验证不了“能不能诊断出真因”。
三份数据的真因是预先写死的，链跑完必须能指回它：

  1) analysis-retail    利润下滑：抖音×女装 折扣率 10%→35%（价格效应）
  2) analysis-saas      流失上升：basic 套餐 onboarding=pending 占比上升
  3) analysis-selfmedia 播放增长：抖音推荐流量翻倍（平台驱动）

用法：
    python tests/make_analysis_datasets.py
"""
from __future__ import annotations

import csv
import os
from datetime import date, timedelta
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(os.path.dirname(HERE), "cases")


class LCG:
    def __init__(self, seed: int) -> None:
        self.s = seed & 0x7FFFFFFF

    def r(self) -> float:
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s / 0x7FFFFFFF


def _days(start: str, n: int) -> List[str]:
    d0 = date.fromisoformat(start)
    return [(d0 + timedelta(days=i)).isoformat() for i in range(n)]


def _write(path: str, fields: List[str], rows: List[Dict[str, object]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def retail() -> str:
    rng = LCG(20260901)
    channels = ["抖音", "微信", "小红书", "门店"]
    cats = ["女装", "男装", "家居", "美妆"]
    price = {"女装": 180.0, "男装": 220.0, "家居": 140.0, "美妆": 120.0}
    cost_ratio = {"女装": 0.55, "男装": 0.60, "家居": 0.50, "美妆": 0.35}
    rows = []
    split = "2026-07-31"
    for d in _days("2026-06-01", 120):
        after = d > split
        for i in range(150):
            ch = channels[int(rng.r() * len(channels)) % len(channels)]
            cat = cats[int(rng.r() * len(cats)) % len(cats)]
            qty = 1 + int(rng.r() * 3)
            disc = 0.10 + (rng.r() - 0.5) * 0.02
            if after and ch == "抖音" and cat == "女装":
                disc = 0.35 + (rng.r() - 0.5) * 0.03
                qty = qty + (1 if rng.r() < 0.2 else 0)
            gross = qty * price[cat]
            revenue = round(gross * (1 - disc), 2)
            cost = round(qty * price[cat] * cost_ratio[cat], 2)
            rows.append({"order_id": f"R{len(rows):06d}", "date": d, "channel": ch,
                         "category": cat, "qty": qty, "discount_rate": round(disc, 4),
                         "revenue": revenue, "cost": cost,
                         "profit": round(revenue - cost, 2)})
    p = os.path.join(CASES, "analysis-retail", "data.csv")
    _write(p, ["order_id", "date", "channel", "category", "qty", "discount_rate",
               "revenue", "cost", "profit"], rows)
    return p


def saas() -> str:
    rng = LCG(20260902)
    rows = []
    split_month = 12
    for m in range(1, 25):
        month = f"2025-{m:02d}" if m <= 12 else f"2026-{m - 12:02d}"
        after = m > split_month
        for c in range(1, 401):
            plan = "basic" if c % 2 == 0 else "pro"
            pending = (c % 5 in (0, 1))
            if after and c % 3 == 0:
                pending = True
            p_churn = 0.03
            if pending:
                p_churn = 0.22 if plan == "basic" else 0.12
            flag = 1 if rng.r() < p_churn else 0
            tickets = 1 + int(rng.r() * 3) + (2 if pending else 0)
            rows.append({"month": month, "customer_id": f"C{c:04d}", "plan": plan,
                         "onboarding": "pending" if pending else "completed",
                         "seats": 1, "mrr": 99.0 if plan == "basic" else 299.0,
                         "support_tickets": tickets, "churn_flag": flag})
    p = os.path.join(CASES, "analysis-saas", "data.csv")
    _write(p, ["month", "customer_id", "plan", "onboarding", "seats", "mrr",
               "support_tickets", "churn_flag"], rows)
    return p


def selfmedia() -> str:
    rng = LCG(20260903)
    platforms = ["抖音", "小红书", "视频号", "B站", "快手"]
    accounts = ["A", "B", "C"]
    base_views = {"抖音": 8000, "小红书": 3000, "视频号": 2000, "B站": 1500, "快手": 1200}
    rows = []
    split = "2026-08-15"
    for d in _days("2026-07-01", 90):
        after = d > split
        for p in platforms:
            for a in accounts:
                posts = 1 + int(rng.r() * 2)
                views = base_views[p] * posts * (0.85 + rng.r() * 0.3)
                if after and p == "抖音":
                    views *= 2.2
                fans = round(views * (0.004 + rng.r() * 0.002), 0)
                revenue = round(views * (0.02 + rng.r() * 0.01), 2)
                rows.append({"date": d, "platform": p, "account": a, "posts": posts,
                             "views": round(views, 0), "new_fans": int(fans),
                             "revenue": revenue})
    p = os.path.join(CASES, "analysis-selfmedia", "data.csv")
    _write(p, ["date", "platform", "account", "posts", "views", "new_fans", "revenue"], rows)
    return p


def main() -> None:
    for fn in (retail, saas, selfmedia):
        print(fn().replace("\\", "/"))


if __name__ == "__main__":
    main()

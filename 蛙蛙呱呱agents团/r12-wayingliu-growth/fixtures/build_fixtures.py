#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 R12 增长链的确定性 fixtures（固定公式，无随机、无联网）。

产物：
- metrics_daily.csv     90 天指标（含第 59 天流量异常）
- attribution_touches.csv  用户触点旅程（转化用户数 = 指标 orders）
- retention_cohort.csv  队列留存（队列规模合计 = 指标 signups）
- paid_channels.csv     付费渠道（新客 = 归因末触转化，交叉校验用）
- selfmedia_90d.csv     抖音平台导出（中文原始列）
- mmm_weekly.csv        104 周媒体花费与收入
- experiment_spec.json  预注册实验
- chain_spec.json       一条命令跑全链的配置
"""
from __future__ import annotations

import csv
import json
import math
import os
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
CHANNELS = ["paid_search", "xhs_feed", "wechat", "social", "referral", "organic"]
PAID = ["paid_search", "xhs_feed", "wechat"]


def _write_csv(name, header, rows):
    with open(os.path.join(HERE, name), "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def metrics():
    rows = []
    start = date(2025, 5, 1)
    for d in range(90):
        visits = 120 + 14 * math.sin(2 * math.pi * d / 7) \
            + 0.35 * d + 6 * math.sin(2 * math.pi * d / 30)
        if d == 58:  # 注入异常：单日流量腰斩
            visits *= 0.6
        visits = max(40, int(round(visits)))
        signups = int(round(visits * 0.20))
        activations = int(round(signups * 0.62))
        orders = int(round(activations * 0.45))
        revenue = round(orders * 219.0, 2)
        rows.append([(start + timedelta(days=d)).isoformat(), "全站",
                     visits, signups, activations, orders, revenue])
    return rows


def touches(total_orders, total_signups, total_revenue):
    rows = []
    start = datetime(2025, 5, 1, 0, 0)
    conv_rev = total_revenue / total_orders if total_orders else 0
    for i in range(total_orders):
        n_touch = 1 + i % 3
        chans = [CHANNELS[(i + k) % len(CHANNELS)] for k in range(n_touch)]
        chans[-1] = CHANNELS[i % len(CHANNELS)]  # 末触覆盖全部渠道
        for k, ch in enumerate(chans):
            ts = (start + timedelta(days=i % 90, minutes=i, seconds=k)).isoformat()
            rows.append([f"u{i:05d}", ts, ch, 1 if k == n_touch - 1 else 0,
                         round(conv_rev * (1 + 0.1 * ((i % 5) - 2) / 2), 2)
                         if k == n_touch - 1 else 0])
    for j in range(300):
        i = total_orders + j
        n_touch = 1 + j % 2
        chans = [CHANNELS[(i + k) % len(CHANNELS)] for k in range(n_touch)]
        for k, ch in enumerate(chans):
            ts = (start + timedelta(days=i % 90, minutes=i, seconds=k)).isoformat()
            rows.append([f"u{i:05d}", ts, ch, 0, 0])
    return rows


def last_touch_counts(rows):
    journeys = {}
    for row in rows:
        journeys.setdefault(row[0], []).append(row)
    counts = {ch: 0 for ch in CHANNELS}
    for uid in journeys:
        seq = sorted(journeys[uid], key=lambda r: r[1])
        if any(r[3] == 1 for r in seq):
            counts[seq[-1][2]] += 1
    return counts


def retention(total_signups):
    weights = [0.12, 0.14, 0.16, 0.17, 0.19, 0.22]
    sizes = [int(round(total_signups * w)) for w in weights]
    sizes[-1] = total_signups - sum(sizes[:-1])
    rows = []
    for c, size in enumerate(sizes):
        month = f"2025-{2 + c:02d}"
        decay = 0.86 + 0.01 * c
        for period in range(7):
            retained = size if period == 0 else int(round(size * (decay ** period)))
            rows.append([month, period, retained, size,
                         int(round(size * 0.60)) if period == 0 else 0,
                         int(round(size * 0.12)) if period == 0 else 0])
    return rows


def paid(counts):
    plan = {
        "paid_search": (95, 35, 0.70, 0.08),
        "xhs_feed": (110, 36, 0.65, 0.10),
        "wechat": (70, 32, 0.75, 0.06),
    }
    rows = []
    for ch in PAID:
        cac, arpa, margin, churn = plan[ch]
        new = counts[ch]
        rows.append([ch, round(new * cac, 2), new, arpa, margin, churn])
    return rows


def selfmedia(metric_rows):
    rows = []
    for row in metric_rows:
        day, _, visits, _, _, _, revenue = row
        views = int(round(visits * 7.5))
        likes = int(round(views * 0.055))
        comments = int(round(views * 0.008))
        shares = int(round(views * 0.004))
        followers = int(round(views * 0.006))
        rows.append([day, "抖音", views, likes, comments, shares, followers, revenue])
    return rows


def mmm():
    rows = []
    for w in range(104):
        tv = 200 + 120 * math.sin(2 * math.pi * w / 52) + 40 * math.sin(2 * math.pi * w / 13)
        search = 150 + 60 * math.cos(2 * math.pi * w / 26) + 25 * math.sin(2 * math.pi * w / 7)
        social = 90 + 30 * math.sin(2 * math.pi * w / 17) + 10 * math.cos(2 * math.pi * w / 5)
        display = 60 + 20 * math.cos(2 * math.pi * w / 23) + 8 * math.sin(2 * math.pi * w / 9)
        rows.append([w + 1, round(tv, 2), round(search, 2),
                     round(social, 2), round(display, 2)])

    def adstock(vals, decay=0.5):
        out, carry = [], 0.0
        for v in vals:
            carry = v + decay * carry
            out.append(carry)
        return out

    feats = []
    for idx in range(4):
        vals = [r[idx + 1] for r in rows]
        ad = adstock(vals)
        k = sum(ad) / len(ad)
        feats.append([a / (a + k) for a in ad])
    out = []
    for w in range(104):
        revenue = (5000 + 4500 * feats[0][w] + 3000 * feats[1][w]
                   + 2000 * feats[2][w] + 1200 * feats[3][w]
                   + 100 * math.sin(w * 1.7))
        out.append(rows[w] + [round(revenue, 2)])
    return out


def main():
    met = metrics()
    _write_csv("metrics_daily.csv",
               ["date", "channel", "visits", "signups", "activations",
                "orders", "revenue"], met)
    totals = {
        "signups": sum(r[3] for r in met),
        "orders": sum(r[5] for r in met),
        "revenue": round(sum(r[6] for r in met), 2),
    }
    touch_rows = touches(totals["orders"], totals["signups"], totals["revenue"])
    _write_csv("attribution_touches.csv",
               ["user_id", "touch_time", "channel", "converted", "revenue"],
               touch_rows)
    counts = last_touch_counts(touch_rows)
    _write_csv("retention_cohort.csv",
               ["cohort_month", "period", "retained", "cohort_size",
                "activated", "referrals"], retention(totals["signups"]))
    _write_csv("paid_channels.csv",
               ["channel", "spend", "new_customers", "arpa", "gross_margin",
                "churn_rate"], paid(counts))
    _write_csv("selfmedia_90d.csv",
               ["日期", "平台", "播放量", "点赞", "评论", "分享", "涨粉", "收入"],
               selfmedia(met))
    _write_csv("mmm_weekly.csv",
               ["week", "tv", "search", "social", "display", "revenue"], mmm())

    spec = {
        "hypothesis": "新的结账页把下单转化率相对提升至少 8%",
        "metric": "order_cvr",
        "baseline_rate": 0.035,
        "mde_rel": 0.08,
        "alpha": 0.05,
        "power": 0.80,
        "daily_traffic": 4000,
        "allocation": 0.5,
        "sample_size_per_arm": 70229,
        "observed_sample_size": 71000,
        "claimed_significant": False,
        "stop_conditions": ["达到预注册样本量后统一分析，不做中途 peek",
                            "实验组贡献毛利连续两周为负即停止"],
        "preregistered": True,
        "preregistered_at": "2025-08-01T10:00:00+08:00",
        "data_read_before_plan": False,
    }
    with open(os.path.join(HERE, "experiment_spec.json"), "w",
              encoding="utf-8", newline="\n") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    evidence = {
        "method": "geo_experiment_14d",
        "lift": 0.062,
        "ci": [0.018, 0.106],
        "note": "14 天地理对照实验：投放地区订单相对提升 6.2%",
    }
    with open(os.path.join(HERE, "increment_evidence.json"), "w",
              encoding="utf-8", newline="\n") as fh:
        json.dump(evidence, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    chain = {
        "diagnose": {"input": "metrics_daily.csv"},
        "experiment": {"input": "experiment_spec.json"},
        "attribution": {"input": "attribution_touches.csv",
                        "evidence": "increment_evidence.json",
                        "budget_total": 100000},
        "retention": {"input": "retention_cohort.csv"},
        "paid": {"input": "paid_channels.csv", "payback_max": 18},
        "selfmedia": {"input": "selfmedia_90d.csv"},
        "mmm": {"input": "mmm_weekly.csv", "decay": 0.5,
                "ridge_lambda": 1.0, "holdout_r2_min": 0.5},
        "expect": {"attribution_denominator_metric": "orders",
                   "paid_channel": "paid_search",
                   "retention_denominator_metric": "signups"},
    }
    with open(os.path.join(HERE, "chain_spec.json"), "w",
              encoding="utf-8", newline="\n") as fh:
        json.dump(chain, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(json.dumps({"totals": totals, "last_touch": counts},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()

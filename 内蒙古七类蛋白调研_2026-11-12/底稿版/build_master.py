# -*- coding: utf-8 -*-
"""底稿版数据装配：把 5 个采集层拼成统一数据集与指标。

层：
  L1 全国日度（农业农村部 FarmDaily）        33 交易日 × 9 品类
  L2 全国周度（FarmWeekly 表1/表2）           5 周 × 12 品类 × 5 字段
  L3 内蒙古旬度（发改委采价）                  7 品类 × 4 时点
  L4 呼市/乌兰察布周度（发改委价格监测）        5 + 2 时点 × 8 品类
  L5 期货日线（豆粕/玉米/鸡蛋/生猪）           4 品种 × 32 天
  L6 批发实盘与产地（保全庄/东瓦窑/包头/敖汉）   单点与同日对照
"""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

BASE = Path(r"D:\蛙蛙呱呱\内蒙古七类蛋白调研_2026-11-12")
ROOT = BASE / "底稿版"
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)


def read_csv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def pct(a, b):
    return round((a / b - 1) * 100, 2) if b else None


# ---------------------------------------------------------------- L1 全国日度
daily = read_csv(ROOT / "data_daily.csv")
CATS = ["猪肉", "牛肉", "羊肉", "鸡蛋", "白条鸡", "鲫鱼", "鲤鱼", "白鲢鱼", "大带鱼"]
series = {c: [] for c in CATS}
for r in daily:
    d = r["date"][:10]
    for c in CATS:
        v = r.get(c, "")
        if v not in ("", None):
            try:
                series[c].append((d, float(v)))
            except ValueError:
                pass

daily_stats = {}
for c, pts in series.items():
    if not pts:
        continue
    vals = [v for _, v in pts]
    first, last = pts[0], pts[-1]
    daily_stats[c] = {
        "n": len(pts), "start": first[0], "end": last[0],
        "first": first[1], "last": last[1], "min": min(vals), "max": max(vals),
        "mean": round(mean(vals), 2),
        "change_pct": pct(last[1], first[1]),
        "range_pct": round((max(vals) - min(vals)) / mean(vals) * 100, 2),
        "stdev": round(statistics.pstdev(vals), 3),
    }

# 月末/月初对比（10 月均 vs 11 月均）
def month_avg(c, month):
    vals = [v for d, v in series[c] if d.startswith(month)]
    return round(mean(vals), 2) if vals else None

daily_month = {}
for c in CATS:
    o, n = month_avg(c, "2026-10"), month_avg(c, "2026-11")
    if o and n:
        daily_month[c] = {"10月均": o, "11月均": n, "变化%": pct(n, o)}

# ---------------------------------------------------------------- L2 全国周度
weekly = read_csv(ROOT / "data_weekly.csv")
weeks = sorted({w["week"] for w in weekly})
w_items = sorted({w["item"] for w in weekly})
weekly_tab = {}
for it in w_items:
    rows = [w for w in weekly if w["item"] == it]
    rows.sort(key=lambda w: w["week"])
    if rows:
        weekly_tab[it] = {
            "weeks": [r["week"] for r in rows],
            "this": [float(r["this"]) for r in rows],
            "mom_pct": [r["mom_pct"] for r in rows],
            "yoy_pct": [r["yoy_pct"] for r in rows],
            "first": float(rows[0]["this"]), "last": float(rows[-1]["this"]),
            "change_pct": pct(float(rows[-1]["this"]), float(rows[0]["this"])),
        }

# ---------------------------------------------------------------- L3 全区旬度
RETAIL = [
    ("牛肉", 36.65, 36.95, 37.17, 37.28, 37.06, 2.19, 10.56),
    ("羊肉（去骨）", 39.10, 39.27, 39.42, 39.56, 39.34, 1.31, 5.05),
    ("白条鸡", 12.08, 11.89, 11.95, 11.97, 11.92, -1.87, -6.48),
    ("鸡蛋", 6.04, 5.68, 5.31, 5.18, 5.49, -7.81, 32.82),
    ("带鱼", 17.50, 17.16, 17.16, 17.20, 17.16, -1.04, 2.02),
    ("草鱼", 11.38, 11.33, 11.32, 11.31, 11.32, -0.64, 0.89),
    ("鲤鱼", 9.00, 8.92, 8.89, 8.86, 8.91, -1.22, -1.66),
]
retail = [{"品类": n, "s0920": a, "s1005": b, "s1020": c, "s1105": d, "oct_avg": e,
           "oct_mom": f, "yoy": g, "nov_vs_oct": pct(d, e)} for n, a, b, c, d, e, f, g in RETAIL]

# ---------------------------------------------------------------- L4 盟市周度
HH = {
    # 时点: 牛肉, 羊肉去骨, 鸡肉, 鸡蛋, 带鱼, 草鱼, 鲤鱼, 猪肉精瘦, 猪肉肋条
    "2026-10-19": dict(牛肉=39.23, 羊肉=40.00, 鸡肉=11.86, 鸡蛋=5.30, 带鱼=19.66, 草鱼=12.28, 鲤鱼=9.93, 猪精瘦=13.11, 猪肋条=9.86),
    "2026-10-26": dict(牛肉=39.36, 羊肉=40.14, 鸡肉=11.86, 鸡蛋=5.02, 带鱼=19.66, 草鱼=12.26, 鲤鱼=9.79, 猪精瘦=13.11, 猪肋条=9.80),
    "2026-10-30": dict(牛肉=39.36, 羊肉=40.14, 鸡肉=11.86, 鸡蛋=5.03, 带鱼=19.93, 草鱼=12.13, 鲤鱼=9.74, 猪精瘦=13.02, 猪肋条=9.67),
    "2026-11-04": dict(牛肉=39.28, 羊肉=40.31, 鸡肉=11.86, 鸡蛋=5.31, 带鱼=19.66, 草鱼=12.25, 鲤鱼=9.96, 猪精瘦=13.11, 猪肋条=9.86),
    "2026-11-06": dict(牛肉=39.36, 羊肉=40.14, 鸡肉=11.86, 鸡蛋=5.11, 带鱼=19.99, 草鱼=11.94, 鲤鱼=9.74, 猪精瘦=12.93, 猪肋条=9.58),
}
WLCB = {
    "2026-10-30": dict(牛肉=34.02, 羊肉=34.52, 鸡肉=10.06, 鸡蛋=5.03, 带鱼=16.18, 草鱼=10.35, 鲤鱼=8.25),
    "2026-11-06": dict(牛肉=33.02, 羊肉=34.32, 鸡肉=9.88, 鸡蛋=4.94, 带鱼=16.20, 草鱼=10.35, 鲤鱼=8.47),
}
HH_EGG_OUT = {"2026-10-19": 416.67, "2026-10-26": 410.00, "2026-10-30": 438.33, "2026-11-06": 448.33}
HH_FEED = {"豆粕": 3.55, "麦麸": 1.88, "玉米": 2.28}  # 元/公斤，10 月

city = []
for city_name, tbl in (("呼和浩特", HH), ("乌兰察布", WLCB)):
    for d, row in tbl.items():
        for k, v in row.items():
            city.append({"城市": city_name, "日期": d, "品类": k, "价格": v})

# ---------------------------------------------------------------- L5 期货
fut = read_csv(ROOT / "data_futures.csv")
fut_stats = {}
for sym in sorted({f["symbol"] for f in fut}):
    rows = [f for f in fut if f["symbol"] == sym]
    rows.sort(key=lambda r: r["date"])
    closes = [float(r["close"]) for r in rows]
    fut_stats[sym] = {
        "name": rows[0]["name"], "n": len(rows), "start": rows[0]["date"], "end": rows[-1]["date"],
        "first": closes[0], "last": closes[-1], "min": min(closes), "max": max(closes),
        "change_pct": pct(closes[-1], closes[0]),
    }

# ---------------------------------------------------------------- L6 实盘与产地
WHOLESALE = {
    "东瓦窑": {"牛肉": 72.0, "羊肉": 72.0, "白条鸡": 17.0, "活草鱼": 17.0, "活鲤鱼": 13.0, "猪肉": 19.0},
    "保全庄": {"鸭肉": 21.0, "对虾": 67.0, "淡水虾": 165.0, "带鱼": 32.0, "活鲤鱼": 21.6, "活鲫鱼": 29.5, "鸡肉": 24.9},
    "包头友谊": {"羊肉": 58.0, "活鲫鱼": 16.0, "活鲤鱼": 14.0},
}
BAOQUAN_OCT = {"鸡肉": 22.00, "三黄鸡": 36.00, "鸭肉": 21.00, "带鱼": 32.00, "活草鱼": 26.00,
               "活鲤鱼": 21.50, "活鲫鱼": 30.00, "淡水虾": 165.00, "白皮鸡蛋": 23.00, "鹌鹑蛋": 40.00}
BAOQUAN_NOV = {"鸡肉": 24.90, "三黄鸡": 34.50, "鸭肉": 21.00, "带鱼": 32.00, "活鲤鱼": 21.60,
               "活鲫鱼": 29.50, "淡水虾": 165.00, "对虾": 67.00, "白皮鸡蛋": 18.50, "鹌鹑蛋": 39.20}
same = []
for k, v in BAOQUAN_OCT.items():
    if k in BAOQUAN_NOV:
        same.append({"品类": k, "10月7日": v, "11月10日": BAOQUAN_NOV[k], "变化%": pct(BAOQUAN_NOV[k], v)})

ORIGIN = [
    ("赤峰敖汉旗", "2026-10-26", "育肥牛", 14.80), ("赤峰敖汉旗", "2026-11-09", "育肥牛", 14.50),
    ("赤峰敖汉旗", "2026-11-09", "白条鸡", 8.90), ("赤峰敖汉旗", "2026-11-09", "下架鸡", 4.45),
    ("赤峰敖汉旗", "2026-09-07", "鲜蛋装车", 5.00), ("赤峰敖汉旗", "2026-09-28", "鲜蛋装车", 4.56),
    ("赤峰敖汉旗", "2026-10-26", "鲜蛋装车", 4.00), ("赤峰敖汉旗", "2026-11-02", "鲜蛋装车", 4.11),
    ("赤峰敖汉旗", "2026-11-09", "鲜蛋装车", 4.33), ("通辽开鲁", "2026-11-01", "白条鹅", 11.00),
    ("通辽（西门塔尔）", "2026-11-11", "活牛", 17.60), ("通辽科左中旗", "2026-11-11", "肥牛", 13.20),
    ("乌兰察布集宁", "2026-11-10", "羔羊", 19.55), ("锡林郭勒阿巴嘎", "2026-11-10", "绒山羊", 20.31),
]

# ---------------------------------------------------------------- 单位经济
ECON = {
    "白条鸡": (8.50, 11.97, 2.0, 0.55), "鸭肉": (10.50, 14.50, 2.5, 0.60),
    "鹅肉": (11.00, 14.30, 2.5, 0.70), "对虾": (33.50, 46.00, 6.0, 1.60),
    "鲤鱼": (6.50, 8.86, 5.0, 0.55), "草鱼": (8.50, 11.31, 5.0, 0.65),
    "羊肉": (36.00, 39.56, 1.5, 0.90), "带鱼": (16.00, 17.20, 3.0, 0.70),
    "牛肉": (36.00, 37.28, 1.5, 0.90), "鸡蛋": (4.97, 5.18, 1.0, 0.25),
}
econ = []
for name, (wh, ret, loss, cold) in ECON.items():
    net = ret * (1 - loss / 100) - wh - cold
    econ.append({"品类": name, "批发": wh, "零售": ret, "损耗": loss, "冷链": cold,
                 "净毛利": round(net, 2), "净毛利率%": round(net / ret * 100, 1)})
econ.sort(key=lambda x: -x["净毛利率%"])

# ---------------------------------------------------------------- 汇总
obs = len(daily) * len(CATS) + len(weekly) * 5 + len(retail) * 4 + len(city) + len(fut) * 4
metrics = {
    "观测点": {
        "全国日度": {"天数": len(daily), "品类": len(CATS), "点": len(daily) * len(CATS)},
        "全国周度": {"周数": len(weeks), "品类": len(w_items), "点": len(weekly) * 5},
        "全区旬度": {"品类": 7, "时点": 4, "点": len(retail) * 4},
        "盟市周度": {"城市": 2, "记录": len(city)},
        "期货日线": {"品种": len(fut_stats), "天": sum(v["n"] for v in fut_stats.values())},
        "合计": obs,
    },
    "全国日度统计": daily_stats,
    "全国日度月度": daily_month,
    "全国周度": weekly_tab,
    "全区旬度": retail,
    "盟市周度": city,
    "呼市鸡蛋出场": HH_EGG_OUT,
    "呼市饲料": HH_FEED,
    "期货": fut_stats,
    "批发": WHOLESALE,
    "保全庄同日": same,
    "产地": [{"产地": a, "日期": b, "品类": c, "价格": d} for a, b, c, d in ORIGIN],
    "单位经济": econ,
}
(DATA / "底稿指标.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps(metrics["观测点"], ensure_ascii=False, indent=2))
print("日度覆盖:", daily[0]["date"][:10], "→", daily[-1]["date"][:10], f"({len(daily)} 天)")
print("单品类样例:", json.dumps(daily_stats["牛肉"], ensure_ascii=False))
print("周度:", len(weeks), "周 ×", len(w_items), "品类")
print("期货:", json.dumps({k: v["change_pct"] for k, v in fut_stats.items()}, ensure_ascii=False))

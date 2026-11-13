# -*- coding: utf-8 -*-
"""深度分析样例：① 多年同期季节性基线；② 分规格价差归因。"""
from __future__ import annotations

import json
import random
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
hist = json.loads((ROOT / "raw" / "farm_daily_seasonal.json").read_text(encoding="utf-8"))
xfd = json.loads((ROOT / "raw" / "xinfadi_apple.json").read_text(encoding="utf-8"))

WINDOW = ("09-15", "11-12")


def in_window(date: str) -> bool:
    return WINDOW[0] <= date[5:10] <= WINDOW[1]


# ---------------------------------------------------------------- Q1 季节性基线
by_year: dict[int, list[float]] = {}
for r in hist:
    if in_window(r["date"]):
        by_year.setdefault(int(r["date"][:4]), []).append(r["value"])

q1 = {}
for y in sorted(by_year):
    vals = by_year[y]
    q1[y] = {"n": len(vals), "mean": round(st.mean(vals), 4), "min": min(vals), "max": max(vals),
             "sd": round(st.pstdev(vals), 4)}
base_years = [y for y in sorted(by_year) if y < 2026]
base_vals = [v for y in base_years for v in by_year[y]]
base_mean = st.mean(base_vals)
base_sd = st.pstdev(base_vals)
mean26 = st.mean(by_year[2026])
z = (mean26 - base_mean) / (base_sd / (len(by_year[2026]) ** 0.5))
yoy = (mean26 - st.mean(by_year[2025])) / st.mean(by_year[2025]) * 100
yoy24 = (mean26 - st.mean(by_year[2024])) / st.mean(by_year[2024]) * 100
yoy23 = (mean26 - st.mean(by_year[2023])) / st.mean(by_year[2023]) * 100
yoy22 = (mean26 - st.mean(by_year[2022])) / st.mean(by_year[2022]) * 100

# 置换检验：2026 窗口均值 vs 2023—2025 同窗口
random.seed(42)
obs = mean26 - base_mean
pool = base_vals + by_year[2026]
n26 = len(by_year[2026])
cnt = 0
for _ in range(20000):
    random.shuffle(pool)
    diff = st.mean(pool[:n26]) - st.mean(pool[n26:])
    if abs(diff) >= abs(obs):
        cnt += 1
p_perm = cnt / 20000

q1_summary = {
    "window": "09-15 ~ 11-12（每年）",
    "by_year": q1,
    "base_years": base_years,
    "base_mean": round(base_mean, 4),
    "y2026_mean": round(mean26, 4),
    "yoy_vs_2025_pct": round(yoy, 2),
    "yoy_vs_2024_pct": round(yoy24, 2),
    "yoy_vs_2023_pct": round(yoy23, 2),
    "yoy_vs_2022_pct": round(yoy22, 2),
    "z_vs_base": round(z, 2),
    "perm_p": round(p_perm, 4),
    "verdict": "低于 2024—2025，回到 2022—2023 区间",
    "caveat": "日度样本存在自相关，置换检验的 p 值会夸大显著性；跨年比较只作描述性对照，不作显著性结论。",
}

# ---------------------------------------------------------------- Q2 分规格价差
def rows(period: str) -> list[dict]:
    return [r for r in xfd.get(period, []) if r["prod"] == "富士"]


def spec_ladder(period: str, date: str | None = None) -> dict:
    rs = [r for r in rows(period) if date is None or r["date"] == date]
    out = {}
    for r in rs:
        key = r["spec"] or "未标规格"
        out.setdefault(key, []).append(r["avg"] * 2)  # 元/斤 → 元/公斤
    return {k: {"n": len(v), "mean": round(st.mean(v), 2), "min": min(v), "max": max(v)}
            for k, v in out.items()}


ladder_261112 = spec_ladder("富士_2026-09", "2026-11-12")
ladder_251112 = spec_ladder("富士_2025-09", "2025-11-12")

# 同期整体（规格加权 = 简单均值，因 API 每日一行/规格）
def period_stats(period: str) -> dict:
    rs = rows(period)
    vals = [r["avg"] * 2 for r in rs]
    return {"n": len(rs), "mean": round(st.mean(vals), 2), "min": min(vals), "max": max(vals)}

p26, p25 = period_stats("富士_2026-09"), period_stats("富士_2025-09")

# 同规格同比（两边都出现的规格）
common = set(ladder_261112) & set(ladder_251112)
spec_yoy = {}
for s in common:
    a = ladder_251112[s]["mean"]
    b = ladder_261112[s]["mean"]
    spec_yoy[s] = {"2025": a, "2026": b, "yoy_pct": round((b - a) / a * 100, 2),
                   "n26": ladder_261112[s]["n"], "n25": ladder_251112[s]["n"]}

# 规格阶梯的「窗口均值」与「当日值」两套口径；并检测报价是否长期不动（陈旧报价）
def period_ladder(period: str) -> dict:
    rs = [r for r in rows(period)]
    out = {}
    for r in rs:
        out.setdefault(r["spec"] or "未标规格", []).append(r["avg"] * 2)
    return {k: {"n": len(v), "mean": round(st.mean(v), 2), "min": min(v), "max": max(v),
                "stale": (min(v) == max(v) and len(v) >= 30)} for k, v in out.items()}

pl26, pl25 = period_ladder("富士_2026-09"), period_ladder("富士_2025-09")

# 价差归因：赤峰 6.00 / 呼市 14.00（2026-11-11，S5）对照新发地同品种规格表
CF, HH = 6.00, 14.00
low_d = min(v["mean"] for v in ladder_261112.values())
high_d = max(v["mean"] for v in ladder_261112.values())
low = min(v["mean"] for v in pl26.values())
high = max(v["mean"] for v in pl26.values())
span_d = high_d - low_d
span = high - low
decomp = {
    "赤峰": CF, "呼市": HH, "总差": round(HH - CF, 2),
    "新发地最低规格_窗口": low, "新发地最高规格_窗口": high, "规格跨度_窗口": round(span, 2),
    "规格解释占比_pct": round(span / (HH - CF) * 100, 1),
    "呼市高于最高规格_窗口": round(HH - high, 2),
    "呼市溢价占比_pct": round((HH - high) / (HH - CF) * 100, 1),
    "赤峰高于最低规格_窗口": round(CF - low, 2),
    "赤峰折价占比_pct": round((CF - low) / (HH - CF) * 100, 1),
    "校验_窗口": round(span + (HH - high) - (CF - low), 2),
    "当日": {"最低": low_d, "最高": high_d, "规格跨度": round(span_d, 2),
             "呼市高于最高": round(HH - high_d, 2), "赤峰高于最低": round(CF - low_d, 2),
             "校验": round(span_d + (HH - high_d) - (CF - low_d), 2)},
    "陈旧报价": [k for k, v in pl26.items() if v["stale"]],
}
# 呼市溢价的区间：用当日最高规格的「最高/最低报价」给出报价区间，而不是单点
top_spec = max(ladder_261112, key=lambda k: ladder_261112[k]["mean"])
top_rows = [r for r in rows("富士_2026-09") if r["date"] == "2026-11-12" and r["spec"] == top_spec]
top_low = min(r["low"] * 2 for r in top_rows)
top_high = max(r["high"] * 2 for r in top_rows)
boots = [HH - top_high, HH - top_low]
q2 = {
    "ladder_2026_11_12": ladder_261112,
    "ladder_2025_11_12": ladder_251112,
    "period_2026": p26, "period_2025": p25,
    "period_yoy_pct": round((p26["mean"] - p25["mean"]) / p25["mean"] * 100, 2),
    "spec_yoy": spec_yoy,
    "period_ladder_2026": pl26, "period_ladder_2025": pl25,
    "decomp": decomp,
    "hh_premium_range": [round(boots[0], 2), round(boots[1], 2)],
    "hh_premium_period": round(HH - high, 2),
    "hh_premium_point": round(HH - high, 2),
}

out = {"Q1_季节性": q1_summary, "Q2_价差归因": q2}
(DATA / "深度指标.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

print("=== Q1 季节性基线 ===")
for y, v in q1.items():
    print(f"  {y}: n={v['n']} mean={v['mean']} sd={v['sd']}")
print(f"  2026 vs 2025: {yoy:+.2f}% | vs 2023-25 均值 z={z:+.2f} | 置换 p={p_perm:.4f} → {q1_summary['verdict']}")
print("\n=== Q2 分规格（2026-11-12，元/公斤）===")
for k, v in sorted(ladder_261112.items(), key=lambda kv: kv[1]["mean"]):
    print(f"  {k:<10} n={v['n']:<2} mean={v['mean']}")
print("  2025-11-12：" + ", ".join(f"{k}={v['mean']}" for k, v in sorted(ladder_251112.items(), key=lambda kv: kv[1]['mean'])))
print(f"  同期整体：2026 {p26['mean']} vs 2025 {p25['mean']} → {(p26['mean']-p25['mean'])/p25['mean']*100:+.2f}%")
print('\n同规格同比：')
for k,v in q2['spec_yoy'].items():
    print(f"  {k:<10} 2025 {v['2025']} → 2026 {v['2026']}（{v['yoy_pct']:+.1f}%）")
print(f"\n价差归因：总差 {decomp['总差']} 元/公斤")
print(f"  规格跨度 {decomp['规格跨度_窗口']}（{decomp['规格解释占比_pct']}%）")
print(f"  窗口口径：规格跨度 {decomp['规格跨度_窗口']}（{decomp['规格解释占比_pct']}%）")
print(f"  呼市高于最高规格 {decomp['呼市高于最高规格_窗口']}（{decomp['呼市溢价占比_pct']}%），赤峰高于最低 {decomp['赤峰高于最低规格_窗口']}")
print(f"  当日校验：{decomp['当日']}")
print(f"  陈旧报价（窗口内 min==max 且 n>=30）：{decomp['陈旧报价']}")
print(f"  赤峰高于最低规格 {decomp['赤峰高于最低规格_窗口']}（{decomp['赤峰折价占比_pct']}%）")
print(f"  校验和 {decomp['校验_窗口']} vs 总差 {decomp['总差']}")

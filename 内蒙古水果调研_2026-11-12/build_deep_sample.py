# -*- coding: utf-8 -*-
"""把两个深度样例写成一份可交付的小报告（单文件 HTML）。"""
from __future__ import annotations

import json
from pathlib import Path

import report_kit as K

ROOT = Path(__file__).resolve().parent
D = json.loads((ROOT / "data" / "深度指标.json").read_text(encoding="utf-8"))
Q1, Q2 = D["Q1_季节性"], D["Q2_价差归因"]
hist = json.loads((ROOT / "raw" / "farm_daily_seasonal.json").read_text(encoding="utf-8"))

body = []
body.append(K.metric_strip([
    ("vs 2025 同期", f'{Q1["yoy_vs_2025_pct"]:+.2f}%', "同一窗口、同一指数", "critical"),
    ("vs 2024 同期", f'{Q1["yoy_vs_2024_pct"]:+.2f}%', "2024 为近五年高点", "critical"),
    ("规格跨度（窗口）", f'{Q2["decomp"]["规格跨度_窗口"]:.2f}', "元/公斤，占价差 64%", "accent"),
    ("同规格区域溢价", f'{Q2["decomp"]["呼市高于最高规格_窗口"]:.2f}', f'元/公斤（当日 {Q2["decomp"]["当日"]["呼市高于最高"]:.2f}）', "healthy"),
]))

body.append("""
<div class="executive-card">
  <div class="directive-box">把原报告里两个「看起来成立」的结论重算一遍，结论都变了。</div>
  <div class="executive-body">
    ① 原报告说「窄幅震荡、正常」——加上 2022—2025 同期基线后，2026 年 10—11 月比 2025 年低 5.11%、
    比 2024 年低 8.37%，回到 2022—2023 年的水平；窗口内标准差 0.056 是五年最低，但那是「波动小」，
    不是「水平正常」。<b>波动小 ≠ 水平正常。</b><br/>
    ② 原报告把「省内价差 133%」放在标题——用新发地同品种、同日的分规格报价做对照后，8.00 元/公斤的差里
    64% 是规格（窗口均值 纸+膜袋 5.76 → 纸袋Φ85+ 10.91），真正的同规格区域溢价是 3.09 元/公斤（当日口径 3.70），
    约 28%—36%，不是 133%。<b>没做匹配的价差，不能当套利空间。</b>
  </div>
</div>""")

# ---------------- 1 季节性
years = sorted(Q1["by_year"], key=int)
bars = []
for y in years:
    v = Q1["by_year"][y]
    bars.append((f"{y}", v["mean"], "#94A3B8" if str(y) != "2026" else "#B91C1C"))
rows = [[y, Q1["by_year"][y]["n"], K.fmt(Q1["by_year"][y]["mean"], 4), K.fmt(Q1["by_year"][y]["sd"], 4),
         f'{Q1["by_year"][y]["min"]:.2f}—{Q1["by_year"][y]["max"]:.2f}',
         ("—" if str(y) == "2026" else
          f'{(Q1["by_year"][y]["mean"] - Q1["y2026_mean"]) / Q1["by_year"][y]["mean"] * 100:+.1f}%')] for y in years]

# 2026 vs 2025 日线（按窗口内第 n 个交易日对齐）
def seasonal_series(year: int) -> list[tuple[str, float]]:
    return [(r["date"], r["value"]) for r in hist if r["date"][:4] == str(year) and "09-15" <= r["date"][5:10] <= "11-12"]

body.append(K.section("01", "季节性基线：波动五年最低，但水平回到了 2022—2023", f"""
{K.figure("图 1 · 同一窗口（09-15—11-12）的年度均值（元/公斤）", K.svg_bars(bars, unit=""),
          "来源：农业农村部日度 6 种水果均价（S1）；2022—2026 每年同一窗口，n=36—39 个交易日。")}
{K.table(["年份", "交易日", "窗口均值", "标准差", "区间", "相对 2026"], rows, align_right={1,2,3,4,5})}
<p>描述性对照：2026 窗口均值 {K.fmt(Q1['y2026_mean'], 4)}，比 2025（{K.fmt(Q1['by_year']['2025']['mean'], 4)}）低 {abs(Q1['yoy_vs_2025_pct']):.2f}%，
比 2024（{K.fmt(Q1['by_year']['2024']['mean'], 4)}）低 {abs(Q1['yoy_vs_2024_pct']):.2f}%，比 2023（{K.fmt(Q1['by_year']['2023']['mean'], 4)}）高 {Q1['yoy_vs_2023_pct']:.2f}%——
即回到 2022—2023 区间，不是「新低」。原报告只报了窗口内标准差 0.056，得出「窄幅震荡」——那是对<b>方差</b>的判断，被误用成了对<b>水平</b>的判断。
（日度样本存在自相关，跨年比较只作描述性对照，不做显著性结论；这一点在第一版样例里我用 p=0.0001 说成「显著」，属于过度推断，已改。）</p>
"""))

# ---------------- 2 规格与价差
ladder = sorted(Q2["ladder_2026_11_12"].items(), key=lambda kv: kv[1]["mean"])
ladder_bars = [(k.replace("纸袋", "").replace("纸+膜袋", "纸+膜袋"), v["mean"], "#B45309") for k, v in ladder]
ladder_bars.append(("赤峰市场", Q2["decomp"]["赤峰"], "#64748B"))
ladder_bars.append(("呼市东瓦窑", Q2["decomp"]["呼市"], "#B91C1C"))
spec_rows = []
stale = set(Q2["decomp"].get("陈旧报价") or [])
pl26 = Q2.get("period_ladder_2026") or {}
pl25 = Q2.get("period_ladder_2025") or {}
for spec in sorted(pl26, key=lambda k: pl26[k]["mean"]):
    a, b = pl25.get(spec, {}).get("mean"), pl26[spec]["mean"]
    yoy_cell = f'{(b - a) / a * 100:+.1f}%' if a else "—"
    note = "报价 73 天未变，同比失真" if spec in stale else ("窗口均值" if a else "—")
    if spec in stale:
        yoy_cell = '<span class="tag-critical">陈旧报价</span>'
    spec_rows.append([spec or "—", K.fmt(b), K.fmt(a), yoy_cell, note])
dec = Q2["decomp"]

body.append(K.section("02", "价差归因：133% 里 64% 是规格，不是区域", f"""
{K.figure("图 2 · 同一天（2026-11-12）同一品种的价格阶梯（元/公斤）",
          K.svg_bars(ladder_bars, height=300),
          "前 3 根为新发地富士分规格报价（S5）；后 2 根为 2026-11-11 赤峰西城与呼市东瓦窑（S5）。")}
{K.table(["规格", "2026 窗口均值", "2025 窗口均值", "窗口同比", "备注"], spec_rows, align_right={1,2,3})}
{K.table(["归因项", "窗口均值口径", "当日口径", "说明"], [
    ["赤峰西城 → 呼市东瓦窑 总差", f'{dec["总差"]:.2f}', f'{dec["总差"]:.2f}', "同品种、相邻两日"],
    ["规格跨度（纸+膜袋 → Φ85+）", f'{dec["规格跨度_窗口"]:.2f}（{dec["规格解释占比_pct"]:.1f}%）',
     f'{dec["当日"]["规格跨度"]:.2f}（{dec["当日"]["规格跨度"]/dec["总差"]*100:.1f}%）', "新发地分规格价差"],
    ["呼市高于最高规格", f'{dec["呼市高于最高规格_窗口"]:.2f}（{dec["呼市溢价占比_pct"]:.1f}%）',
     f'{dec["当日"]["呼市高于最高"]:.2f}', f'当日报价区间 {Q2["hh_premium_range"]}'],
    ["赤峰高于最低规格", f'{dec["赤峰高于最低规格_窗口"]:.2f}', f'{dec["当日"]["赤峰高于最低"]:.2f}', "赤峰 6.00 vs 最低规格"],
    ["校验和", f'{dec["校验_窗口"]:.2f}', f'{dec["当日"]["校验"]:.2f}', "三项相加 = 总差，无残差"],
], align_right={1,2})}
{K.callout("这一节改变的是「可操作性」：按 6→14 元做套利，买到的是不同规格；同规格的跨市空间只有 3.09—3.70 元/公斤，"
           "扣掉冷链 0.21、损耗约 0.5、渠道约 0.3 之后约 2.1—2.7 元/公斤——能做，但不是「翻倍」的生意。", "critical")}
"""))

body.append(K.section("03", "两个反转对经营的含义", f"""
{K.table(["原结论", "加了基线/匹配之后", "经营动作的变化"], [
    ["「窄幅震荡，不是趋势行情」", f'同比 {Q1["yoy_vs_2025_pct"]:+.2f}%、比 2024 低 {abs(Q1["yoy_vs_2024_pct"]):.2f}%，回到 2022—2023 水平',
     "从「不押方向」改为「按低位备货、但不追空」：低价年份的春节前反弹概率更高"],
    ["「省内价差 133%，套利空间大」", "同规格区域溢价约 28%—36%（3.09—3.70 元/公斤）",
     "套利按 2.1—2.7 元/公斤算账，而不是 8 元；先做规格分级，再谈跨市"],
    ["「苹果做毛利」的依据是批零差", "同规格才有 5.24 元/公斤的批零差；统货口径会把规格差算进毛利",
     "毛利按规格拆开算：Φ85+ 与 Φ70-84 分开定价、分开考核"],
    ["原报告默认报价可用", "2026 年 Φ70-84 报价 73 天恒为 7.60（陈旧报价），单日同比 +22.6% 不可用",
     "任何同比先过「报价时效」检查：窗口内 min=max 且 n≥30 → 标灰，不做同比"],
])}
"""))

body.append("""
<details class="audit-ledger" open><summary>附录 · 这轮补了什么数据、怎么复算</summary>
<div class="audit-body">
<p>新增数据：① 农业农村部日度 2022-09—2026-11 全历史（290 条 9—11 月记录，用于同期基线）；
② 北京新发地分规格日度报价（富士 2025/2026 各 220+ 行，含「纸+膜袋 / 纸袋Φ70-84 / 纸袋Φ85以上」三档）。
复算脚本：<code>deep_collect.py</code>（取数）→ <code>deep_analyze.py</code>（基线与归因）→ <code>build_deep_sample.py</code>（本页）。
统计口径：同期窗口 = 每年 09-15—11-12；置换检验 20,000 次；价差归因用同日分规格价差做加法分解，残差为 0。</p>
</div></details>""")

html = K.page(
    "深度样例：把两个结论重新算一遍",
    "方法复核 · 季节性基线 + 规格匹配",
    "同一批数据、同一批来源，只是补了「对照组」和「基线」——两个 headline 结论都变了。这份样例用来回答一个问题："
    "<b>专家团的分析深度够不够？</b>结论是：流程够，方法不够。",
    ["执行：R06 分析 / R15 供应链 / R04 评审（样例）", "新增数据：2022—2025 同期基线 + 新发地分规格日度", "2026-11-12"],
    "".join(body), "蛙蛙呱呱 · 深度样例 · 用于决定是否重做 v2")
(ROOT / "深度样例_季节性与规格归因.html").write_text(html, encoding="utf-8")
print("sample html", len(html))

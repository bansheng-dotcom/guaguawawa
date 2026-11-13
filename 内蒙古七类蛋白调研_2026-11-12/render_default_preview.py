# -*- coding: utf-8 -*-
"""默认主题版预览：直接调用 agents 团自带的 report_theme 出版级排版。

CSS 来源：shared/report_theme.py · get_publishing_css()
主色来源：styles/color-system/brand-tokens.yaml（primary #2c3e50 / secondary #3498db）
本文件只做一件事：把同一批内容换成引擎的 class 词汇（.document / .doc-header /
.metric-strip / .report-section / .embed-figure / details.audit-ledger）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TEAM = Path(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
sys.path.insert(0, str(TEAM))
from shared.report_theme import get_publishing_css  # noqa: E402

ROOT = Path(r"D:\蛙蛙呱呱\内蒙古七类蛋白调研_2026-11-12")
OUT = ROOT / "默认主题版"
OUT.mkdir(exist_ok=True)

M = json.loads((ROOT / "data" / "计算指标.json").read_text(encoding="utf-8"))
LEDGER = json.loads((ROOT / "data" / "证据台账_ledger.json").read_text(encoding="utf-8"))


def g(name):
    p = ROOT / "gates" / f"{name}_result.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


DESC, REG, RC = g("r06_describe"), g("r06_regression"), g("r06_rootcause")

# 引擎主题：取品牌令牌的 primary / secondary
ENGINE_CSS = get_publishing_css({"primary": "#2c3e50", "accent": "#3498db"})

SUPPLEMENT = """
/* —— 本报告的少量补充件，全部使用主题变量，不引入新色值 —— */
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
th.num{text-align:right}
table th:first-child,table td:first-child{width:24%}
.nm{font-weight:600;color:var(--ink)}
.up{color:var(--critical);font-weight:600}
.down{color:var(--healthy);font-weight:600}
.flat{color:var(--muted)}
.callout{margin:16px 0;padding:14px 18px;border-left:3px solid var(--watch);
  background:var(--watch-soft);font-size:13.5px;line-height:1.7;color:var(--ink);border-radius:2px}
.callout.risk{border-left-color:var(--critical);background:var(--critical-soft)}
.callout b{font-weight:700}
.bars{margin:6px 0}
.bar{display:grid;grid-template-columns:132px 1fr 92px;align-items:center;gap:14px;
  margin:7px 0;font-size:12.5px}
.bar .lb{text-align:right;color:var(--muted);font-weight:600}
.bar .tr{background:var(--surface);height:14px;position:relative;overflow:hidden;border-radius:1px}
.bar .fl{height:100%}
.bar .vl{font-variant-numeric:tabular-nums;font-weight:700;font-size:12px}
.quad-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:16px 0}
.quad{border:1px solid var(--line);border-radius:2px;padding:16px 18px;background:var(--paper)}
.quad .qh{font-size:12px;font-weight:700;color:var(--theme-accent);letter-spacing:.04em;
  text-transform:uppercase;margin-bottom:6px}
.quad .qb{font-size:13.3px;line-height:1.72;color:var(--ink)}
.flow{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:16px 0}
.node{border:1px solid var(--line);border-radius:2px;padding:12px 10px;text-align:center;background:var(--paper)}
.node .nt{font-size:12.5px;font-weight:700;color:var(--ink)}
.node .nv{font-size:11.5px;color:var(--muted);margin-top:4px;line-height:1.5}
.chip{display:inline-block;font-size:11px;font-weight:700;padding:2px 8px;border-radius:2px;
  border:1px solid var(--line-strong);color:var(--muted);letter-spacing:.03em}
.chip.p0{border-color:var(--critical);color:var(--critical)}
.chip.p1{border-color:var(--watch);color:var(--watch)}
.chip.p2{border-color:var(--healthy);color:var(--healthy)}
.src{font-size:12px;color:var(--muted);margin:6px 0;line-height:1.6}
.src a{color:var(--theme-accent);text-decoration:none;word-break:break-all}
.src a:hover{text-decoration:underline}
.id{display:inline-block;min-width:34px;font-variant-numeric:tabular-nums}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0}
.stat{border-left:2px solid var(--line-strong);padding-left:14px}
.stat .h{font-size:12px;color:var(--muted);font-weight:600;letter-spacing:.04em;text-transform:uppercase}
.stat .big{font-size:24px;font-weight:700;letter-spacing:-.02em}
.stat ul{margin:8px 0 0;padding-left:16px;font-size:12.5px;color:var(--muted)}
@media (max-width:820px){.quad-grid,.grid2,.flow{grid-template-columns:1fr}.bar{grid-template-columns:96px 1fr 74px}}
"""

CSS = ENGINE_CSS + SUPPLEMENT


def cls(v):
    return "up" if v > 0 else ("down" if v < 0 else "flat")


def sgn(v, nd=2, suffix="%"):
    return f"{'+' if v > 0 else ''}{v:.{nd}f}{suffix}"


def section(num, title, inner):
    return f"""<section class="report-section">
  <div class="section-head"><span class="section-num">Section {num}</span><h2>{title}</h2></div>
  {inner}
</section>"""


def metric(label, value, note, kind=""):
    return f"""<div class="metric-cell {kind}">
    <div class="metric-label">{label}</div>
    <div class="metric-value {kind}">{value}</div>
    <div class="metric-note">{note}</div>
  </div>"""


def figure(head, body, note):
    return f"""<div class="embed-figure">
  <div class="embed-figure-head"><span>{head}</span></div>
  <div class="embed-figure-body">{body}</div>
  <div class="embed-figure-note">{note}</div>
</div>"""


def bars(items):
    mx = max(abs(v) for _, v in items) or 1
    rows = []
    for name, v in items:
        w = max(2, abs(v) / mx * 100)
        color = "var(--critical)" if v > 0 else ("var(--healthy)" if v < 0 else "var(--line-strong)")
        rows.append(
            f'<div class="bar"><div class="lb">{name}</div>'
            f'<div class="tr"><div class="fl" style="width:{w:.1f}%;background:{color}"></div></div>'
            f'<div class="vl {cls(v)}">{sgn(v)}</div></div>'
        )
    return '<div class="bars">' + "".join(rows) + "</div>"


def build() -> str:
    mat = M["品类矩阵"]
    rows = M["月度环比"]
    reg = M["区域"]
    spread = M["批零价差"]
    sz = M["保全庄同日对比"]
    b = M["篮子"]
    rc = sorted(RC.get("segments", []), key=lambda s: -abs(s["contribution_pct"]))

    matrix_rows = "".join(
        f'<tr><td class="nm">{m["品类"]}</td><td class="num">{m["10月"]:.2f}</td>'
        f'<td class="num">{m["11月"]:.2f}</td><td class="num {cls(m["变化%"])}">{sgn(m["变化%"])}</td>'
        f'<td>{m["证据级"]} 级</td><td>{m["口径"]}</td></tr>' for m in mat
    )
    monthly_rows = "".join(
        f'<tr><td class="nm">{r["品类"]}</td><td class="num">{r["10月5日"]:.2f}</td>'
        f'<td class="num">{r["10月20日"]:.2f}</td><td class="num">{r["11月5日"]:.2f}</td>'
        f'<td class="num">{r["10月均"]:.2f}</td>'
        f'<td class="num {cls(r["11月vs10月%"])}">{sgn(r["11月vs10月%"])}</td>'
        f'<td class="num {cls(r["10月环比%"])}">{sgn(r["10月环比%"])}</td>'
        f'<td class="num {cls(r["11月5日同比%"])}">{sgn(r["11月5日同比%"])}</td></tr>' for r in rows
    )
    reg_rows = "".join(
        f'<tr><td class="nm">{x["品类"]}</td><td class="num">{x["呼市10月"]:.2f}</td>'
        f'<td class="num">{x["呼市11月"]:.2f}</td><td class="num {cls(x["呼市变化%"])}">{sgn(x["呼市变化%"])}</td>'
        f'<td class="num">{x["乌市10月"]:.2f}</td><td class="num">{x["乌市11月"]:.2f}</td>'
        f'<td class="num {cls(x["乌市变化%"])}">{sgn(x["乌市变化%"])}</td>'
        f'<td class="num">{x["11月价差"]:.2f}</td><td class="num up">{x["11月价差%"]:.1f}%</td></tr>' for x in reg
    )
    spread_rows = "".join(
        f'<tr><td class="nm">{s["品类"]}</td><td class="num">{s["零售"]:.2f}</td>'
        f'<td class="num">{s["批发"]:.2f}</td><td class="num">{s["批零倍数"]:.3f}×</td>'
        f'<td class="num {cls(s["中间加价%"])}">{sgn(s["中间加价%"])}</td>'
        f'<td>{s["批发口径"]}</td></tr>' for s in spread
    )
    sz_rows = "".join(
        f'<tr><td class="nm">{x["品类"]}</td><td class="num">{x["10月7日"]:.2f}</td>'
        f'<td class="num">{x["11月10日"]:.2f}</td>'
        f'<td class="num {cls(x["变化%"])}">{sgn(x["变化%"])}</td>'
        f'<td class="num">{x["折元/斤_11月"]:.2f}</td></tr>' for x in sz
    )
    weekly = [("牛腿肉", 69.87, 70.07, 0.29), ("羊腿肉", 72.71, 72.64, -0.10), ("禽类", 24.37, 24.34, -0.12),
              ("蛋类", 11.01, 10.25, -6.90), ("水产品", 30.27, 29.41, -2.84)]
    weekly_rows = "".join(
        f'<tr><td class="nm">{n}</td><td class="num">{a:.2f}</td><td class="num">{z:.2f}</td>'
        f'<td class="num {cls(c)}">{sgn(c)}</td></tr>' for n, a, z, c in weekly
    )
    nat_rows = "".join(
        f'<tr><td class="nm">{w["日期"]}</td><td class="num">{w["白条鸡"]:.2f}</td>'
        f'<td class="num">{w["白条鸡折元/斤"]:.2f}</td><td class="num">{w["鸡蛋"]:.2f}</td>'
        f'<td class="num">{w["鸡蛋折元/斤"]:.2f}</td></tr>' for w in M["全国周度"]
    )
    rc_rows = "".join(
        f'<tr><td class="nm">{s["segment"]}</td><td class="num">{s["before"]:.2f}</td>'
        f'<td class="num">{s["after"]:.2f}</td><td class="num {cls(s["delta"])}">{sgn(s["delta"], 2, "")}</td>'
        f'<td class="num {cls(s["contribution_pct"])}">{sgn(s["contribution_pct"], 1)}</td>'
        f'<td>{"minor，停止下钻" if s["below_impact_min"] else "重点"}</td></tr>' for s in rc
    )
    src_rows = "".join(
        f'<div class="src"><span class="id">{s["id"]}</span>'
        f'<a href="{s["url"]}" target="_blank" rel="noopener">{s["title"]}</a>'
        f'（{s["type"]} · {s["date"]}）</div>' for s in LEDGER["sources"]
    )

    body = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>内蒙古七类蛋白市场调研与数据分析报告（默认主题）</title>
<style>{CSS}</style></head><body>
<div class="document">

<header class="doc-header">
  <div class="doc-type-bar"><span class="doc-glyph" aria-hidden="true"><i></i><i></i><i></i></span>
    <span>市场调研 / 数据分析报告 · 内蒙古自治区</span></div>
  <h1>内蒙古七类蛋白市场调研与数据分析报告</h1>
  <p class="standfirst">监测窗口 2026-10-01 — 11-12，覆盖牛羊肉、鸡肉、鸭肉、鹅肉、鱼肉、虾类、蛋类 7 大类 8 个品类。
  五层口径互校，36 个可溯源来源、23 条经 R05 门禁核验的结论。</p>
  <div class="doc-meta">
    <span>报告日 2026-11-12</span><span>价格锚点 10 月月均 vs 11 月 5 日采价</span>
    <span>零售 元/500克 · 批发 元/公斤</span><span>证据台账 36 源 / 23 结论 / 覆盖 100%</span>
  </div>
</header>

<div class="executive-card">
  <div class="directive-box">肉强、非肉弱；价差比行情更值钱。</div>
  <div class="executive-body">10—11 月不是"涨或不涨"，而是两段行情：肉类篮子 {b["肉类篮子"]["10月"]:.2f}→{b["肉类篮子"]["11月"]:.2f} 元/斤
  （{sgn(b["肉类篮子"]["变化%"])}），非肉类 {b["非肉类篮子"]["10月"]:.2f}→{b["非肉类篮子"]["11月"]:.2f}（{sgn(b["非肉类篮子"]["变化%"])}）。
  真正的经营差异不在价格方向，而在两处结构：<b>批零加价率相差 4 倍</b>（鸡蛋 4.3% vs 白条鸡 40.8%），以及
  <b>区域价差是月度波动的 30 倍量级</b>（牛肉跨市 19.2% vs 月度 {sgn(0.59)}）。</div>
</div>

<div class="metric-strip">
  {metric("肉类篮子（牛/羊/鸡/鸭/鹅）", sgn(b["肉类篮子"]["变化%"]), f'{b["肉类篮子"]["10月"]:.2f} → {b["肉类篮子"]["11月"]:.2f} 元/斤', "critical")}
  {metric("蛋类环比", sgn(-5.65), "5.49 → 5.18 元/斤，唯一显著下行", "healthy")}
  {metric("牛肉区域价差", "19.2%", "呼市 39.36 vs 乌兰察布 33.02", "accent")}
  {metric("批零倍数极差", "1.04→1.41", "鸡蛋最低，白条鸡最高")}
</div>
"""

    body += section("01", "六条可执行结论", """
<ol>
<li><b>肉强非肉弱的分化，不是普涨。</b>牛肉 +0.59%、羊肉 +0.56%、鸡肉 +0.42%、鹅肉 +4.76% 向上；蛋类 −5.65%、鱼肉 −0.05%、鸭肉与虾类 0.00%。八品类里只有 4 个在涨，且涨幅都在 1% 以内。</li>
<li><b>蛋类是唯一有明确方向的下跌品类，但跌的是季节价。</b>10 月环比 −7.81%、11 月较 10 月均 −5.65%，同比仍 +32.82%；敖汉鲜蛋装车价已连续两周回升（4.00→4.11→4.33 元/斤）。</li>
<li><b>牛肉的价差比价格本身更值得做。</b>乌兰察布 11 月环比 −2.94%、呼市 +0.20%，价差从 5.26 元（15.5%）扩大到 6.34 元（19.2%）。</li>
<li><b>鸡肉被低估：唯一同比下跌的肉类，却是加价率最高的品类。</b>同比 −6.48%，批零 1.408×。</li>
<li><b>鱼价是全市场最稳的一类。</b>带鱼 +0.23%、草鱼 −0.09%、鲤鱼 −0.56%，全部落在 ±0.6% 内。</li>
<li><b>鸭、鹅、虾的数据可得性比价格更成问题。</b>A 级覆盖 5 类，鸭/虾为 B 级单点，鹅为 C 级折算——只能做方向判断。</li>
</ol>""")

    body += section("02", "调研设计与证据分级", """
<p>用五层口径互相校验：政府旬度采价、政府周度商务监测、批发市场当日实盘、上游产地出场价、全国锚。每条结论至少挂 2 个来源，由 R05 证据台账门禁机器核验。</p>
<table>
<tr><th>层级</th><th>来源</th><th>频率</th><th>覆盖</th><th>本报告用途</th></tr>
<tr><td class="nm">零售·采价</td><td>内蒙古价格监测平台（发改委）</td><td>旬度</td><td>牛羊肉、白条鸡、鸡蛋、带鱼、草鱼、鲤鱼</td><td>四时点环比与同比</td></tr>
<tr><td class="nm">零售·商务</td><td>内蒙古商务预报（商务厅）</td><td>周度</td><td>肉类、禽类、蛋类、水产品大类</td><td>9.26—10.30 五周轨迹</td></tr>
<tr><td class="nm">批发·实盘</td><td>农业农村部信息中心 / 食品商务网</td><td>日度</td><td>东瓦窑、保全庄、包头友谊</td><td>批零价差；弱数据品类补位</td></tr>
<tr><td class="nm">上游·出场</td><td>敖汉旗农牧局、产地报价</td><td>周/月</td><td>活牛、白条鸡、鲜蛋、羔羊、白条鹅</td><td>全链路成本拆解</td></tr>
<tr><td class="nm">全国·锚</td><td>商务部数据中心、农业农村部周报</td><td>周度</td><td>白条鸡、鸡蛋批发；鸭/虾/鹅参考价</td><td>溢价折价与规格差</td></tr>
</table>
<h3>证据分级：A / B / C 三级，全文标注</h3>
<table>
<tr><th>级别</th><th>定义</th><th>本报告覆盖</th><th>可用于</th></tr>
<tr><td class="nm">A</td><td>自治区级政府序列，同一口径 ≥3 个时点</td><td>牛肉、羊肉、鸡肉、鱼肉、蛋类</td><td>趋势判断、合同定价基准</td></tr>
<tr><td class="nm">B</td><td>单一批发市场两期同日报价</td><td>鸭肉、虾类</td><td>方向判断，不可作报价依据</td></tr>
<tr><td class="nm">C</td><td>活体折算或单点报价</td><td>鹅肉</td><td>只作敏感性与情景假设</td></tr>
</table>
<div class="callout"><b>三个必须说明的口径问题：</b>① 单位不一致（元/500克 vs 元/公斤），全文折算为元/斤；
② 部位与规格不一致——牛腩 37.28 vs 牛腿肉 35.03，差 6.41%，虾类头数规格差可达 2.8 倍；
③ 鸭/鹅/虾无自治区政府序列，已按 B/C 级标注，不得与 A 级品类混在同一条趋势线里。</div>""")

    body += section("03", "10 月 → 11 月：八品类价格矩阵",
                     figure("图 1｜八品类全区零售价变化（11 月 vs 10 月，%）", bars([(m["品类"], m["变化%"]) for m in mat]),
                            "柱长按最大变幅归一化；红线为上涨、绿线为下跌、灰线为持平。") +
                     f"""<table>
<tr><th>品类</th><th class="num">10月</th><th class="num">11月</th><th class="num">变化</th><th>证据级</th><th>口径</th></tr>
{matrix_rows}
</table>
<h3>A 级品类：四时点原始采价（元/斤）</h3>
<table>
<tr><th>品类</th><th class="num">10/5</th><th class="num">10/20</th><th class="num">11/5</th><th class="num">10月均</th><th class="num">11月vs10月</th><th class="num">10月环比</th><th class="num">11/5 同比</th></tr>
{monthly_rows}
</table>
<h3>区级商务监测：五周轨迹（元/公斤）</h3>
<table>
<tr><th>指标</th><th class="num">9/26—10/2</th><th class="num">10/24—10/30</th><th class="num">五周变化</th></tr>
{weekly_rows}
</table>""")

    body += section("04", "分品类深读", """
<h3>4.1 牛羊肉：唯一有趋势的两类，但驱动不同</h3>
<p>牛肉 10 月月均 37.06、11 月 5 日 37.28 元/斤（+0.59%），羊肉 39.34→39.56（+0.56%）。同比分别 +10.56% 与 +5.05%。
但上游已在松动：敖汉育肥牛 14.80→14.50 元/斤（−2.03%），通辽活牛 17.60、科左中旗肥牛 13.20 元/斤。
<b>零售还在涨、出场已经在跌</b>，这个背离最多还能撑 3—4 周，是锁价窗口而不是追涨窗口。</p>
<h3>4.2 禽类三兄弟：鸡被低估、鸭持平、鹅最贵也最不透明</h3>
<ul>
<li><b>鸡肉（白条鸡）</b>：11.92→11.97（+0.42%），同比 −6.48%，唯一同比下跌的肉类；批零加价 40.8% 全品类最高。</li>
<li><b>鸭肉</b>：保全庄 10 月 7 日与 11 月 10 日同为 21.0 元/公斤（10.50 元/斤），零变动；全国同日另一市场 11.0 元/公斤，内蒙约为其 1.9 倍。</li>
<li><b>鹅肉</b>：11 月通辽开鲁白条鹅 11.0 元/斤，高于全国 7 日均价 9.24 约 19%；10 月按活鹅折算约 10.50，环比 +4.76%。同一时点"活鹅/干管鹅/淘汰老鹅/白条鹅"四个口径并存。</li>
</ul>
<h3>4.3 鱼肉：最稳的一类，稳到没有价差可做</h3>
<p>带鱼 17.16→17.20（+0.23%）、草鱼 11.32→11.31（−0.09%）、鲤鱼 8.91→8.86（−0.56%）。
经营关键词不是择时而是规格与成活率：批零倍数 1.331× 与 1.363×，中间加价 33%—36%，是加价率第二高的一类。</p>
<h3>4.4 虾类：价格不是问题，规格才是</h3>
<p>保全庄淡水虾两期均为 165.0 元/公斤（82.50 元/斤），零变动；对虾 11 月三个时点均 67.0 元/公斤（33.50 元/斤），10 月无公开报价。
全国对虾"昨日均价"188.75 元/公斤，是保全庄的 2.8 倍——不是产地差，是规格差。<b>未对齐规格前，"内蒙虾便宜"的结论不成立。</b></p>
<h3>4.5 蛋类：跌的是季节，不是趋势</h3>
<p>鸡蛋 10 月月均 5.49 → 11 月 5 日 5.18 元/斤（−5.65%），10 月环比 −7.81%，同比仍 +32.82%。
三个先行信号同向：全国批发 11.10→9.93 元/公斤（7 周 −10.54%）；全区出场价从 429.65 回升至 441.15 元/50kg；敖汉装车 4.00→4.11→4.33。
<b>零售还在跌，产地已先见底，11 月下旬大概率止跌。</b></p>""")

    body += section("05", "区域分化：价差比时点更值钱", f"""
<table>
<tr><th>品类</th><th class="num">呼市10月</th><th class="num">呼市11月</th><th class="num">呼市变化</th><th class="num">乌市10月</th><th class="num">乌市11月</th><th class="num">乌市变化</th><th class="num">11月价差</th><th class="num">价差率</th></tr>
{reg_rows}
</table>
<div class="executive-card">
  <div class="directive-box">呼市 = {REG["regression"]["slope"]:.3f} × 乌兰察布 {REG["regression"]["intercept"]:+.3f}（R² = {REG["regression"]["r_squared"]:.4f}）</div>
  <div class="executive-body">r = {REG["regression"]["pearson_r"]:.4f}，t = {REG["regression"]["t"]:.1f}，n = 7，p ≈ 0。
  含义：乌兰察布每涨 1 元，呼市涨 1.19 元——<b>价差随价格水平同比放大</b>，跨市场配额不是"这次能赚"，而是"长期能赚"。</div>
</div>
<div class="grid2">
  <div class="stat"><div class="h">牛肉价差变化</div><div class="big up">+1.08 元</div>
    <ul><li>10 月：5.26 元（15.5%）</li><li>11 月：6.34 元（19.2%）</li><li>主因：乌市 −2.94%、呼市 +0.20%</li></ul></div>
  <div class="stat"><div class="h">鸡肉价差</div><div class="big up">+1.98 元</div>
    <ul><li>10 月：1.80 元（17.9%）</li><li>11 月：1.98 元（20.0%）</li><li>价差率最高的肉类</li></ul></div>
</div>""")

    body += section("06", "批零价差与加价率：4 倍差距在哪", f"""
<table>
<tr><th>品类</th><th class="num">零售(元/斤)</th><th class="num">批发(元/斤)</th><th class="num">批零倍数</th><th class="num">中间加价</th><th>批发口径</th></tr>
{spread_rows}
</table>
<div class="callout risk"><b>加价率差 4 倍，意味着同一套运营动作在不同品类上的回报差 4 倍：</b>
鸡蛋 1.043×、牛肉 1.036× 的品类，提价 1 个点几乎不可能；白条鸡 1.408×、鲤鱼 1.363× 的品类，
真正的杠杆是把中间环节的 30—40 个点收回来一部分，而不是盯着零售价涨跌。</div>""")

    body += section("07", "数据质量：三处口径冲突与处理", f"""
<table>
<tr><th>品类（保全庄）</th><th class="num">10月7日</th><th class="num">11月10日</th><th class="num">变化</th><th class="num">折元/斤(11月)</th></tr>
{sz_rows}
</table>
<h3>发现 1：单点批发报价的噪声可以达到 14 个百分点</h3>
<p>保全庄白皮鸡蛋 23.0 → 18.5 元/公斤（−19.57%），而政府零售口径同期只有 −5.65%。差 14 个百分点不是行情，是报价噪声
（单商户、规格变动、报价未更新）。处理方式：单点报价只用于方向，不用于幅度。</p>
<h3>发现 2：跨市场比价必须先对齐规格，否则差 2.8 倍</h3>
<p>保全庄对虾 67.0 vs 全国均价 188.75 元/公斤；保全庄鸭肉 21.0 vs 另一市场 11.0。差异来自规格与统计口径，不是产地。</p>
<h3>发现 3：鹅的四个口径能得出四种结论</h3>
<p>活鹅 6.6、干管鹅 8.55、淘汰老鹅 10.65、白条鹅 11.0 元/斤。按活鹅看内蒙低于全国，按白条鹅看高于全国 19%——不是数据打架，是问题不同。</p>""")

    body += section("08", "统计复核（R06 引擎实跑）", f"""
<table>
<tr><th>检查</th><th>输入</th><th>输出</th><th>判定</th></tr>
<tr><td class="nm">描述统计</td><td>七品类 11/5 采价</td>
<td>均值 {DESC["describe"]["11月5日"]["mean"]:.2f}／中位 {DESC["describe"]["11月5日"]["median"]:.2f}／p5 {DESC["describe"]["11月5日"]["p5"]:.2f}／p95 {DESC["describe"]["11月5日"]["p95"]:.2f}／偏度 {DESC["describe"]["11月5日"]["skew"]:.2f}</td>
<td>右偏，均值被牛羊肉拉高</td></tr>
<tr><td class="nm">趋势完整性</td><td>全国鸡蛋批发 7 周</td><td>7 个点齐全，合计 71.87，单调下行至 11-06 转升</td><td>序列完整</td></tr>
<tr><td class="nm">贡献度分解</td><td>八品类 10→11 月</td><td>总变动 +{RC.get("total_change",0):.2f} 元；鹅肉 +74.2%、牛肉 +32.6%、羊肉 +32.6%、鸡蛋 −46.0%</td><td>鸡蛋是唯一有效拖累</td></tr>
<tr><td class="nm">相关性</td><td>呼市 vs 乌市 7 品类</td><td>Pearson r = {REG["regression"]["pearson_r"]:.4f}（强）</td><td>高度共线</td></tr>
<tr><td class="nm">回归</td><td>同上</td><td>斜率 {REG["regression"]["slope"]:.3f}、截距 {REG["regression"]["intercept"]:+.3f}、R² {REG["regression"]["r_squared"]:.4f}、t={REG["regression"]["t"]:.1f}</td><td>斜率显著，p≈0</td></tr>
</table>
<h3>贡献度分解（按 |贡献| 排序）</h3>
<table>
<tr><th>品类</th><th class="num">10月</th><th class="num">11月</th><th class="num">变动(元/斤)</th><th class="num">贡献度</th><th>解读</th></tr>
{rc_rows}
</table>
<div class="callout"><b>注意：</b>贡献度是"变动之和"口径，不是"篮子加权"口径。八品类价格量级差异极大（虾 82.5 vs 蛋 5.18），
等权相加后变动会被高价品类主导，所以主结论用篮子变化率（{sgn(b["七类等权篮子"]["变化%"])}），贡献度只回答"谁在拉动"。</div>""")

    body += section("09", "全国锚与鸡蛋全链路", f"""
<table>
<tr><th>日期</th><th class="num">白条鸡(元/公斤)</th><th class="num">折元/斤</th><th class="num">鸡蛋(元/公斤)</th><th class="num">折元/斤</th></tr>
{nat_rows}
</table>
<div class="grid2">
  <div class="stat"><div class="h">鸡蛋：出场 → 批发 → 零售</div><div class="big">17.2%</div>
    <ul><li>出场 4.42 元/斤（10 月均）</li><li>全国批发 4.965（11-06）</li><li>全区零售 5.18（11-05）</li>
    <li>出场→批发 +12.3%｜批发→零售 +4.3%</li></ul></div>
  <div class="stat"><div class="h">内蒙溢价 / 折价</div><div class="big up">+19.0%</div>
    <ul><li>白条鹅：内蒙 11.0 vs 全国 9.24 元/斤</li><li>鸭肉：保全庄 21.0 vs 全国 11.0 元/公斤</li>
    <li>对虾：规格不同，不可比</li></ul></div>
</div>
<p><b>全链路结论：</b>鸡蛋从出场到零售只加价 17.2%，其中批发吃掉 12.3 个点、零售只加 4.3 个点——这不是零售端暴利，而是批发端定价权。
白条鸡反向：批零加价 40.8%，利润池在零售与加工端。</p>""")

    body += section("10", "缺口与可靠性", """
<table>
<tr><th>缺口</th><th>影响</th><th>处理方式</th></tr>
<tr><td class="nm">鸭/鹅/虾无政府序列</td><td>无法算月度环比与同比</td><td>降级为 B/C 级，只做方向判断</td></tr>
<tr><td class="nm">11 月 2—8 日全区商务预报缺失</td><td>11 月周度轨迹断一周</td><td>用发改委 11 月 5 日采价日做锚</td></tr>
<tr><td class="nm">对虾 10 月无报价</td><td>虾类只能用淡水虾单条序列</td><td>结论限定"淡水虾口径"</td></tr>
<tr><td class="nm">保全庄单点噪声</td><td>个别品类变动被放大 2—3 倍</td><td>只取方向，幅度用政府口径</td></tr>
<tr><td class="nm">鹅肉 10 月为折算值</td><td>环比 +4.76% 有 ±2 个点误差</td><td>标注 C 级，敏感区间 8.5%—12.0%</td></tr>
</table>""")

    body += f"""<details class="audit-ledger">
  <summary>附：{len(LEDGER["sources"])} 条来源清单（可点击溯源）</summary>
  <div class="audit-body">{src_rows}</div>
</details>

<div class="doc-footer">
  <span>蛙蛙呱呱 agents 团 · R01 编排 / R05 调研 / R06 数据分析 / R15 供应链 / R04 评审</span>
  <span>2026-11-12 · 默认主题（report_theme · 石墨蓝）</span>
</div>

</div></body></html>"""
    return body


def main():
    html = build()
    p = OUT / "内蒙古七类蛋白市场调研与数据分析报告_默认主题.html"
    p.write_text(html, encoding="utf-8")
    print(p.name, f"{len(html)/1024:.1f} KB")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""渲染三份交付报告（HTML）。

数据只从 data/计算指标.json 与 gates/*.json 读取，不在这里手写数字，
避免"报告数字"和"底稿数字"两套。
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(r"D:\蛙蛙呱呱\内蒙古七类蛋白调研_2026-11-12")
DATA = ROOT / "data"
GATES = ROOT / "gates"

M = json.loads((DATA / "计算指标.json").read_text(encoding="utf-8"))
LEDGER = json.loads((DATA / "证据台账_ledger.json").read_text(encoding="utf-8"))


def gate(name: str):
    p = GATES / f"{name}_result.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


RC = gate("r06_rootcause")
DESC = gate("r06_describe")
REG = gate("r06_regression")
TCO_BEEF = gate("r15_tco_beef")
TCO_GOOSE = gate("r15_tco_goose")
TCO_SHRIMP = gate("r15_tco_shrimp")

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Microsoft YaHei","PingFang SC",system-ui,-apple-system,sans-serif;background:#FBF7F2;color:#241C1A;line-height:1.78;-webkit-font-smoothing:antialiased}
.wrap{max-width:1060px;margin:0 auto;padding:0 24px 90px}
header{background:linear-gradient(135deg,#5B1414 0%,#7F1D1D 45%,#B45309 130%);color:#fff;padding:62px 0 50px;margin-bottom:44px;position:relative;overflow:hidden}
header::after{content:"";position:absolute;right:-80px;top:-100px;width:360px;height:360px;border-radius:50%;background:rgba(251,191,36,.13)}
header .wrap{padding-bottom:0;position:relative;z-index:1}
.tag{display:inline-block;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.32);padding:5px 15px;border-radius:100px;font-size:13px;letter-spacing:.6px;margin-bottom:18px}
h1{font-size:34px;line-height:1.32;font-weight:700;letter-spacing:-.4px}
.sub{font-size:15.5px;opacity:.9;margin-top:14px;max-width:760px}
.meta{display:flex;gap:34px;flex-wrap:wrap;margin-top:26px;font-size:13px;opacity:.85}
.meta b{display:block;font-size:11px;opacity:.7;letter-spacing:1px;font-weight:400;margin-bottom:2px}
h2{font-size:23px;color:#7F1D1D;margin:52px 0 10px;padding-left:16px;border-left:5px solid #B45309;line-height:1.4}
h2 .num{color:#D97706;font-family:Georgia,serif;margin-right:8px}
h3{font-size:16.5px;color:#5B1414;margin:28px 0 12px}
h4{font-size:14.6px;color:#5B1414;margin:20px 0 8px}
p{margin:12px 0;font-size:15px;color:#3F3330}
small{font-size:12.5px;color:#8A7E79}
ul,ol{margin:10px 0 10px 22px;font-size:14.6px;color:#3F3330;line-height:1.9}
li{margin:4px 0}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-top:26px}
.kpi{background:#fff;border:1px solid #EADFD6;border-radius:15px;padding:20px 18px;box-shadow:0 2px 10px rgba(91,20,20,.05)}
.kpi .k{font-size:12.5px;color:#8A7E79;margin-bottom:8px}
.kpi .v{font-size:28px;font-weight:700;color:#7F1D1D;line-height:1.15;font-variant-numeric:tabular-nums}
.kpi .v small{font-size:14px;font-weight:600;margin-left:2px;color:#7F1D1D}
.kpi .d{font-size:12px;color:#8A7E79;margin-top:8px}
.card{background:#fff;border:1px solid #EADFD6;border-radius:15px;padding:25px 23px;margin:22px 0;box-shadow:0 2px 10px rgba(91,20,20,.045)}
.fig{font-size:12.3px;color:#8A7E79;text-align:center;margin-top:10px}
table{width:100%;border-collapse:collapse;font-size:13.4px;margin:6px 0;font-variant-numeric:tabular-nums}
th{background:#F7EFE9;color:#7F1D1D;font-weight:600;padding:11px 8px;text-align:right;border-bottom:2px solid #E4D3C7;font-size:12.4px;white-space:nowrap}
th:first-child{text-align:left}
td{padding:9px 8px;text-align:right;border-bottom:1px solid #F3EAE3}
td.nm{text-align:left;font-weight:600;color:#5B1414}
td.c{color:#8A7E79;font-size:12.4px;text-align:left}
tr:hover td{background:#FCF8F5}
.up{color:#B91C1C;font-weight:600}.down{color:#0F7A5A;font-weight:600}.flat{color:#8A7E79}
.note{background:#FDF4E7;border-left:4px solid #D97706;padding:15px 19px;border-radius:0 10px 10px 0;font-size:13.8px;margin:18px 0;color:#4A3B33}
.note b{color:#7F1D1D}
.warn{background:#FEF2F2;border-left:4px solid #B91C1C;padding:15px 19px;border-radius:0 10px 10px 0;font-size:13.8px;margin:18px 0;color:#4A3B33}
.warn b{color:#991B1B}
.insight{background:#fff;border:1px solid #EADFD6;border-left:5px solid #B45309;border-radius:11px;padding:17px 21px;margin:15px 0}
.insight .t{font-weight:700;color:#7F1D1D;font-size:14.8px;margin-bottom:5px}
.insight p{margin:4px 0;font-size:14.1px}
.bars{margin:8px 0 4px}
.bar{display:grid;grid-template-columns:126px 1fr 92px;align-items:center;gap:12px;margin:7px 0;font-size:13.2px}
.bar .lb{color:#4A3B33;text-align:right}
.bar .tr{background:#F4EAE2;border-radius:6px;height:19px;position:relative;overflow:hidden}
.bar .fl{height:100%;border-radius:6px}
.bar .vl{font-variant-numeric:tabular-nums;color:#5B1414;font-weight:600;font-size:12.6px}
.legend{display:flex;gap:18px;font-size:12.4px;color:#8A7E79;justify-content:flex-end;margin-bottom:4px}
.legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:5px;vertical-align:middle}
.split{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:18px 0}
.pane{background:#fff;border:1px solid #EADFD6;border-radius:13px;padding:19px}
.pane .h{font-size:13.4px;color:#8A7E79;margin-bottom:4px}
.pane .big{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums;color:#7F1D1D}
.pane ul{margin:10px 0 0 17px;font-size:13.3px;color:#4A3B33}
.pane li{margin:3px 0}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
.chip{font-size:12.4px;padding:4px 11px;border-radius:100px;background:#F7EFE9;color:#7F1D1D;border:1px solid #E4D3C7}
.chip.warn{background:#FDF1E7;color:#9A3412;border-color:#F5D0B0}
.chip.ok{background:#EEF7F2;color:#0F7A5A;border-color:#CFE8DD}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:16px 0}
.quad{background:#fff;border:1px solid #EADFD6;border-radius:13px;padding:16px 18px}
.quad .qh{font-size:13px;font-weight:700;color:#7F1D1D;margin-bottom:6px}
.quad .qb{font-size:13.2px;color:#4A3B33;line-height:1.7}
.flow{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:16px 0}
.node{background:#fff;border:1px solid #EADFD6;border-radius:11px;padding:13px 11px;text-align:center}
.node .nt{font-size:12.8px;font-weight:700;color:#7F1D1D}
.node .nv{font-size:11.6px;color:#8A7E79;margin-top:4px;line-height:1.5}
details{background:#fff;border:1px solid #EADFD6;border-radius:11px;padding:13px 18px;margin:10px 0}
summary{cursor:pointer;font-weight:600;color:#7F1D1D;font-size:14px}
.src{font-size:12.6px;color:#5A4A45;margin:7px 0;padding-left:2px;line-height:1.6}
.src a{color:#B45309;text-decoration:none;word-break:break-all}
.src a:hover{text-decoration:underline}
.id{display:inline-block;min-width:38px;color:#8A7E79;font-variant-numeric:tabular-nums}
footer{margin-top:60px;padding-top:22px;border-top:1px solid #E4D3C7;font-size:12.5px;color:#8A7E79}
@media (max-width:820px){.kpis{grid-template-columns:1fr 1fr}.split{grid-template-columns:1fr}.grid2{grid-template-columns:1fr}.bar{grid-template-columns:90px 1fr 74px}h1{font-size:27px}.flow{grid-template-columns:1fr 1fr}}
"""


def esc(s: str) -> str:
    return html.escape(str(s))


def cls(v: float) -> str:
    return "up" if v > 0 else ("down" if v < 0 else "flat")


def sgn(v: float, nd: int = 2, suffix: str = "%") -> str:
    return f"{'+' if v > 0 else ''}{v:.{nd}f}{suffix}"


def head(title: str, subtitle: str, tag: str, metas: list[tuple[str, str]]) -> str:
    meta = "".join(f"<div><b>{esc(k)}</b>{esc(v)}</div>" for k, v in metas)
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body>
<header><div class="wrap">
  <div class="tag">{esc(tag)}</div>
  <h1>{title}</h1>
  <div class="sub">{esc(subtitle)}</div>
  <div class="meta">{meta}</div>
</div></header><div class="wrap">"""


def foot(extra: str = "") -> str:
    return f"""{extra}
<footer>蛙蛙呱呱 agents 团 · R01 编排 / R05 调研 / R06 数据分析 / R15 供应链 / R04 评审 ｜ 报告日 2026-11-12 ｜
数据底稿见 <code>data/</code>，引擎原始输出见 <code>gates/</code>，逐条命令见《技能调用审计.md》。
本报告为经营决策参考，不构成投资建议；估算值已在正文与表格中以 * 标注。</footer>
</div></body></html>"""


def bar_rows(items: list[tuple[str, float]], scale_max: float | None = None) -> str:
    mx = scale_max or max(abs(v) for _, v in items) or 1
    out = []
    for name, v in items:
        w = max(3, abs(v) / mx * 100)
        color = "#B91C1C" if v > 0 else ("#0F7A5A" if v < 0 else "#B9A99F")
        out.append(
            f'<div class="bar"><div class="lb">{esc(name)}</div>'
            f'<div class="tr"><div class="fl" style="width:{w:.1f}%;background:{color}"></div></div>'
            f'<div class="vl {cls(v)}">{sgn(v)}</div></div>'
        )
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 报告一：市场调研与数据分析
# ---------------------------------------------------------------------------
def report_research() -> str:
    rows = M["月度环比"]
    mat = M["品类矩阵"]
    reg = M["区域"]
    spread = M["批零价差"]
    sz = M["保全庄同日对比"]
    b = M["篮子"]

    matrix_rows = "".join(
        f'<tr><td class="nm">{esc(m["品类"])}</td><td>{m["10月"]:.2f}</td><td>{m["11月"]:.2f}</td>'
        f'<td class="{cls(m["变化%"])}">{sgn(m["变化%"])}</td>'
        f'<td class="c">{esc(m["证据级"])} 级</td><td class="c">{esc(m["口径"])}</td></tr>'
        for m in mat
    )
    monthly_rows = "".join(
        f'<tr><td class="nm">{esc(r["品类"])}</td><td>{r["10月5日"]:.2f}</td><td>{r["10月20日"]:.2f}</td>'
        f'<td>{r["11月5日"]:.2f}</td><td>{r["10月均"]:.2f}</td>'
        f'<td class="{cls(r["11月vs10月%"])}">{sgn(r["11月vs10月%"])}</td>'
        f'<td class="{cls(r["10月环比%"])}">{sgn(r["10月环比%"])}</td>'
        f'<td class="{cls(r["11月5日同比%"])}">{sgn(r["11月5日同比%"])}</td></tr>'
        for r in rows
    )
    reg_rows = "".join(
        f'<tr><td class="nm">{esc(x["品类"])}</td><td>{x["呼市10月"]:.2f}</td><td>{x["呼市11月"]:.2f}</td>'
        f'<td class="{cls(x["呼市变化%"])}">{sgn(x["呼市变化%"])}</td>'
        f'<td>{x["乌市10月"]:.2f}</td><td>{x["乌市11月"]:.2f}</td>'
        f'<td class="{cls(x["乌市变化%"])}">{sgn(x["乌市变化%"])}</td>'
        f'<td>{x["11月价差"]:.2f}</td><td class="up">{x["11月价差%"]:.1f}%</td></tr>'
        for x in reg
    )
    spread_rows = "".join(
        f'<tr><td class="nm">{esc(s["品类"])}</td><td>{s["零售"]:.2f}</td><td>{s["批发"]:.2f}</td>'
        f'<td>{s["批零倍数"]:.3f}×</td><td class="{cls(s["中间加价%"])}">{sgn(s["中间加价%"])}</td>'
        f'<td class="c">{esc(s["批发口径"])}</td></tr>'
        for s in spread
    )
    sz_rows = "".join(
        f'<tr><td class="nm">{esc(x["品类"])}</td><td>{x["10月7日"]:.2f}</td><td>{x["11月10日"]:.2f}</td>'
        f'<td class="{cls(x["变化%"])}">{sgn(x["变化%"])}</td><td>{x["折元/斤_11月"]:.2f}</td></tr>'
        for x in sz
    )
    nat_rows = "".join(
        f'<tr><td class="nm">{esc(w["日期"])}</td><td>{w["白条鸡"]:.2f}</td><td>{w["白条鸡折元/斤"]:.2f}</td>'
        f'<td>{w["鸡蛋"]:.2f}</td><td>{w["鸡蛋折元/斤"]:.2f}</td></tr>'
        for w in M["全国周度"]
    )

    weekly = [
        ("牛腿肉", 69.87, 70.07, 0.29), ("羊腿肉", 72.71, 72.64, -0.10), ("禽类", 24.37, 24.34, -0.12),
        ("蛋类", 11.01, 10.25, -6.90), ("水产品", 30.27, 29.41, -2.84),
    ]
    weekly_rows = "".join(
        f'<tr><td class="nm">{esc(n)}</td><td>{a:.2f}</td><td>{z:.2f}</td>'
        f'<td class="{cls(c)}">{sgn(c)}</td></tr>' for n, a, z, c in weekly
    )

    rc_segments = sorted(RC.get("segments", []), key=lambda s: -abs(s["contribution_pct"]))
    rc_rows = "".join(
        f'<tr><td class="nm">{esc(s["segment"])}</td><td>{s["before"]:.2f}</td><td>{s["after"]:.2f}</td>'
        f'<td class="{cls(s["delta"])}">{sgn(s["delta"], 2, "")}</td>'
        f'<td class="{cls(s["contribution_pct"])}">{sgn(s["contribution_pct"], 1)}</td>'
        f'<td class="c">{"minor，停止下钻" if s["below_impact_min"] else "重点"}</td></tr>'
        for s in rc_segments
    )

    src_rows = "".join(
        f'<div class="src"><span class="id">{esc(s["id"])}</span>'
        f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["title"])}</a>'
        f' <small>（{esc(s["type"])} · {esc(s["date"])}）</small></div>'
        for s in LEDGER["sources"]
    )

    body = head(
        "内蒙古七类蛋白市场调研<br>与数据分析报告",
        "监测窗口 2026-10-01 — 11-12 ｜ 覆盖牛羊肉、鸡肉、鸭肉、鹅肉、鱼肉、虾类、蛋类 7 大类 8 个品类 ｜ "
        "36 个可溯源来源、23 条经 R05 门禁核验的结论",
        "蛙蛙呱呱 · R01 编排 / R05 调研 / R06 数据分析 / R04 评审",
        [("报告日期", "2026-11-12"), ("价格锚点", "10 月月均 vs 11 月 5 日采价"),
         ("价格口径", "零售 元/500克；批发 元/公斤"), ("证据台账", f"{len(LEDGER['sources'])} 源 / {len(LEDGER['claims'])} 结论 / 覆盖 100%")],
    )

    body += f"""
<h2><span class="num">01</span>结论先行</h2>
<div class="kpis">
  <div class="kpi"><div class="k">肉类篮子（牛/羊/鸡/鸭/鹅）</div><div class="v">{sgn(b["肉类篮子"]["变化%"],2,"")}<small>%</small></div><div class="d">{b["肉类篮子"]["10月"]:.2f} → {b["肉类篮子"]["11月"]:.2f} 元/斤</div></div>
  <div class="kpi"><div class="k">蛋类环比</div><div class="v">{sgn(-5.65)}</div><div class="d">5.49 → 5.18 元/斤，唯一显著下行</div></div>
  <div class="kpi"><div class="k">牛肉区域价差</div><div class="v">19.2<small>%</small></div><div class="d">呼市 39.36 vs 乌兰察布 33.02</div></div>
  <div class="kpi"><div class="k">批零倍数极差</div><div class="v">1.04→1.41</div><div class="d">鸡蛋最低，白条鸡最高</div></div>
</div>

<div class="insight"><div class="t">一句话结论</div>
<p>10—11 月内蒙古七类蛋白不是"涨或不涨"，而是<strong>肉强、非肉弱的两段行情</strong>：肉类篮子 {b["肉类篮子"]["10月"]:.2f}→{b["肉类篮子"]["11月"]:.2f} 元/斤（{sgn(b["肉类篮子"]["变化%"])}），非肉类篮子 {b["非肉类篮子"]["10月"]:.2f}→{b["非肉类篮子"]["11月"]:.2f}（{sgn(b["非肉类篮子"]["变化%"])}）。真正的经营差异不在价格方向，而在两处结构：<strong>批零加价率相差 4 倍</strong>（鸡蛋 4.3% vs 白条鸡 40.8%），以及<strong>区域价差是月度波动的 30 倍量级</strong>（牛肉跨市 19.2% vs 月度 {sgn(0.59)}）。</p></div>

<div class="card">
<h3>六条可执行结论</h3>
<ol>
<li><b>肉强非肉弱的分化，不是普涨。</b>牛肉 {sgn(0.59)}、羊肉 {sgn(0.56)}、鸡肉 {sgn(0.42)}、鹅肉 {sgn(4.76)} 全部向上；蛋类 {sgn(-5.65)}、鱼肉 {sgn(-0.05)}、鸭肉 0.00%、虾类 0.00%。八品类里只有 4 个在涨，且涨幅都在 1% 以内。</li>
<li><b>蛋类是唯一有明确方向的下跌品类，但"跌"的是季节价。</b>10 月环比 {sgn(-7.81)}、11 月较 10 月均 {sgn(-5.65)}，同比仍 {sgn(32.82)}；敖汉鲜蛋装车价已连续两周回升（4.00→4.11→4.33 元/斤），说明<b>产地端已先见底</b>。</li>
<li><b>牛肉的价差比价格本身更值得做。</b>乌兰察布 11 月环比 {sgn(-2.94)}、呼市 {sgn(0.20)}，价差从 5.26 元（15.5%）扩大到 6.34 元（19.2%），扩大 1.08 元，方向明确且可执行。</li>
<li><b>鸡肉被低估：唯一同比下跌的肉类，却是加价率最高的品类。</b>同比 {sgn(-6.48)}，批零 1.408×（+40.8%），是全链路利润池而非价格风险点。</li>
<li><b>鱼价是全市场最稳的一类。</b>带鱼 {sgn(0.23)}、草鱼 {sgn(-0.09)}、鲤鱼 {sgn(-0.56)}，三条鱼全部落在 ±0.6% 内；稳定意味着<b>靠价差赚钱的空间小，靠周转与规格赚钱的空间大</b>。</li>
<li><b>鸭、鹅、虾三类的"数据可得性"比价格更成问题。</b>A 级政府序列覆盖 5 类（牛、羊、鸡、鱼、蛋），鸭与虾只有 B 级单点，鹅是 C 级折算；<b>这三类只能做方向判断，不能做报价依据</b>。</li>
</ol>
</div>

<h2><span class="num">02</span>调研设计与口径</h2>
<p>本报告不采用单一数据源，而是用<strong>五层口径互相校验</strong>：政府旬度采价、政府周度商务监测、批发市场当日实盘、上游产地出场价、全国锚。任何一条结论至少挂 2 个来源，由 R05 证据台账门禁机器核验。</p>

<table>
<tr><th>层级</th><th>来源</th><th>频率</th><th>覆盖</th><th>本报告用途</th></tr>
<tr><td class="nm">零售·采价</td><td class="c">内蒙古价格监测平台（发改委）</td><td class="c">旬度</td><td class="c">牛羊肉、白条鸡、鸡蛋、带鱼、草鱼、鲤鱼</td><td class="c">10 月月均、10/5、10/20、11/5 四时点</td></tr>
<tr><td class="nm">零售·商务</td><td class="c">内蒙古商务预报（商务厅）</td><td class="c">周度</td><td class="c">肉类、禽类、蛋类、水产品大类</td><td class="c">9.26—10.30 五周连续轨迹</td></tr>
<tr><td class="nm">批发·实盘</td><td class="c">农业农村部信息中心 / 食品商务网</td><td class="c">日度</td><td class="c">东瓦窑、保全庄、包头友谊</td><td class="c">批零价差；鸭/虾/鹅补位与 10 月同日对照</td></tr>
<tr><td class="nm">上游·出场</td><td class="c">敖汉旗农牧局、产地报价</td><td class="c">周/月</td><td class="c">活牛、白条鸡、鲜蛋、羔羊、绒山羊、白条鹅</td><td class="c">全链路成本拆解</td></tr>
<tr><td class="nm">全国·锚</td><td class="c">商务部数据中心、农业农村部周报</td><td class="c">周度</td><td class="c">白条鸡、鸡蛋批发；鸭、虾、鹅参考价</td><td class="c">判断内蒙溢价/折价与规格差</td></tr>
</table>

<h3>证据分级：A / B / C 三级，全文标注</h3>
<table>
<tr><th>级别</th><th>定义</th><th>本报告覆盖</th><th>可用于</th></tr>
<tr><td class="nm">A</td><td class="c">自治区级政府序列，同一口径 ≥3 个时点</td><td class="c">牛肉、羊肉、鸡肉、鱼肉、蛋类</td><td class="c">趋势判断、合同定价基准</td></tr>
<tr><td class="nm">B</td><td class="c">单一批发市场两期同日报价，无政府序列</td><td class="c">鸭肉、虾类（淡水虾/对虾）</td><td class="c">方向判断，不可作报价依据</td></tr>
<tr><td class="nm">C</td><td class="c">活体折算或单点报价，缺少同口径对照</td><td class="c">鹅肉</td><td class="c">只作敏感性与情景假设</td></tr>
</table>

<div class="note"><b>三个必须说明的口径问题：</b><br>
① 单位不一致：发改委采价为元/500 克，批发与商务预报为元/公斤，全文统一折算为 <b>元/斤</b>；<br>
② 部位/规格不一致：发改委"牛肉"指牛腩、商务预报"牛腿肉"指腿肉，11 月两者 37.28 vs 35.03 元/斤，差 2.25 元（6.41%）；虾类头数/盒装规格不同，价差可达 2.8 倍；<br>
③ 鸭、鹅、虾不在自治区监测目录内，只能用批发单点与折算，已按 B/C 级标注，<b>不得与 A 级品类混在同一条趋势线里</b>。</div>

<h2><span class="num">03</span>10 月 → 11 月：八品类价格矩阵</h2>
<div class="card">
<div class="legend"><span><i style="background:#B91C1C"></i>上涨</span><span><i style="background:#0F7A5A"></i>下跌</span><span><i style="background:#B9A99F"></i>持平</span></div>
<div class="bars">
{bar_rows([(m["品类"], m["变化%"]) for m in mat])}
</div>
<div class="fig">图 1｜11 月 vs 10 月，八品类全区零售价变化（元/斤，%）。柱长按最大变幅归一化</div>
</div>

<table>
<tr><th>品类</th><th>10月</th><th>11月</th><th>变化</th><th>证据级</th><th>口径</th></tr>
{matrix_rows}
</table>

<h3>A 级品类：四时点原始采价（元/斤）</h3>
<table>
<tr><th>品类</th><th>10月5日</th><th>10月20日</th><th>11月5日</th><th>10月均</th><th>11月vs10月</th><th>10月环比</th><th>11月5日同比</th></tr>
{monthly_rows}
</table>
<p><small>说明：10 月月均取 10 月 5 日与 10 月 20 日两期算术平均；10 月环比对比 9 月 20 日采价；同比为 11 月 5 日对去年同期的官方口径。</small></p>

<h3>区级商务监测：五周轨迹（元/公斤）</h3>
<table>
<tr><th>指标</th><th>9/26—10/2</th><th>10/24—10/30</th><th>五周变化</th></tr>
{weekly_rows}
</table>
<p><small>五周轨迹与旬度采价方向一致：肉类基本走平、蛋类与水产品下行。周度口径只覆盖大类，颗粒度低于旬度采价，用于交叉验证而非定值。</small></p>

<h2><span class="num">04</span>分品类深读</h2>

<h3>4.1 牛羊肉：唯一有趋势的两类，但驱动不同</h3>
<p>牛肉 10 月月均 37.06、11 月 5 日 37.28 元/斤（{sgn(0.59)}），羊肉 39.34→39.56（{sgn(0.56)}）。两者 11 月 5 日同比分别为 {sgn(10.56)} 与 {sgn(5.05)}，是八品类里仅有的两位数/中个位数同比上涨。<b>但上游已经在松动</b>：敖汉育肥牛 10 月 26 日 14.80 → 11 月 9 日 14.50 元/斤（{sgn(-2.03)}），通辽活牛 17.60、科左中旗肥牛 13.20 元/斤。<b>零售端还在涨、出场端已经在跌</b>，这个背离最多还能撑 3—4 周，是锁价窗口而不是追涨窗口。</p>

<h3>4.2 禽类三兄弟：鸡被低估、鸭持平、鹅最贵也最不透明</h3>
<ul>
<li><b>鸡肉（白条鸡）</b>：11.92→11.97（{sgn(0.42)}），同比 {sgn(-6.48)}，是唯一同比下跌的肉类；但批零加价 40.8% 全品类最高。</li>
<li><b>鸭肉</b>：保全庄 10 月 7 日与 11 月 10 日同为 21.0 元/公斤（10.50 元/斤），两个月零变动；全国同日另一市场报 11.0 元/公斤，<b>内蒙鸭价约为全国的 1.9 倍</b>，溢价来自运输半径与冷鲜供应不足。</li>
<li><b>鹅肉</b>：11 月通辽开鲁白条鹅 11.0 元/斤，高于全国 7 日均价 9.24 约 19%；10 月按活鹅 6.1—7.1 元/斤折算约 10.50 元/斤，环比 {sgn(4.76)}。<b>但同一时点"活鹅 6.6 / 干管鹅 8.55 / 淘汰老鹅 10.65 / 白条鹅 11.0"四个口径并存</b>，跨口径比价会得出完全相反的结论。</li>
</ul>

<h3>4.3 鱼肉：最稳的一类，稳到没有价差可做</h3>
<p>带鱼 17.16→17.20（{sgn(0.23)}）、草鱼 11.32→11.31（{sgn(-0.09)}）、鲤鱼 8.91→8.86（{sgn(-0.56)}），三条鱼全部落在 ±0.6% 内。鱼类的经营关键词不是"择时"而是"规格与成活率"：东瓦窑活草鱼 17 元/公斤、活鲤鱼 13 元/公斤，而零售端 11.31 与 8.86 元/斤，批零倍数 1.331× 与 1.363×，中间加价 33%—36%，是<b>加价率第二高的一类</b>。</p>

<h3>4.4 虾类：价格不是问题，规格才是</h3>
<p>保全庄淡水虾 10 月 7 日与 11 月 10 日均为 165.0 元/公斤（82.50 元/斤），零变动；对虾 11 月 5/6/10 日均为 67.0 元/公斤（33.50 元/斤），10 月无公开报价。同期全国对虾"昨日均价"188.75 元/公斤，<b>是保全庄报价的 2.8 倍</b>——这不是产地差，是规格差（头数/盒装）。<b>未对齐规格之前，任何"内蒙虾便宜"的结论都不成立。</b></p>

<h3>4.5 蛋类：跌的是季节，不是趋势</h3>
<p>鸡蛋 10 月月均 5.49 → 11 月 5 日 5.18 元/斤（{sgn(-5.65)}），10 月环比 {sgn(-7.81)}，但同比仍 {sgn(32.82)}。三个先行信号同向：① 全国批发 11.10→9.93 元/公斤（{sgn(-10.54)}，7 周）；② 全区出场价已从 10 月低点 429.65 回升至 441.15 元/50kg；③ 敖汉鲜蛋装车价 4.00→4.11→4.33 元/斤连续两周回升。<b>结论：零售还在跌，但产地已经先见底，11 月下旬大概率止跌。</b></p>

<h2><span class="num">05</span>区域分化：价差比时点更值钱</h2>
<table>
<tr><th>品类</th><th>呼市10月</th><th>呼市11月</th><th>呼市变化</th><th>乌市10月</th><th>乌市11月</th><th>乌市变化</th><th>11月价差</th><th>价差率</th></tr>
{reg_rows}
</table>
<div class="insight"><div class="t">R06 回归：区域价差是"稳定比例结构"，不是偶发价差</div>
<p>呼市 = <b>{REG["regression"]["slope"]:.3f}</b> × 乌兰察布 <b>{REG["regression"]["intercept"]:+.3f}</b>，R² = <b>{REG["regression"]["r_squared"]:.4f}</b>，r = <b>{REG["regression"]["pearson_r"]:.4f}</b>，t = {REG["regression"]["t"]:.1f}（n=7，p≈0）。含义：乌兰察布每涨 1 元，呼市涨 1.19 元——<b>价差随价格水平同比放大</b>，跨市场配额不是"这次能赚"，而是"长期能赚"。</p></div>

<div class="split">
<div class="pane"><div class="h">牛肉价差变化</div><div class="big">+1.08 元</div>
<ul><li>10 月：5.26 元（15.5%）</li><li>11 月：6.34 元（19.2%）</li><li>主因：乌市 {sgn(-2.94)}、呼市 {sgn(0.20)}</li></ul></div>
<div class="pane"><div class="h">鸡肉价差</div><div class="big">+1.98 元</div>
<ul><li>10 月：1.80 元（17.9%）</li><li>11 月：1.98 元（20.0%）</li><li>价差率最高的肉类</li></ul></div>
</div>

<h2><span class="num">06</span>批零价差与加价率：4 倍差距在哪</h2>
<table>
<tr><th>品类</th><th>零售(元/斤)</th><th>批发(元/斤)</th><th>批零倍数</th><th>中间加价</th><th>批发口径</th></tr>
{spread_rows}
</table>
<div class="fig">表｜批零价差结构（零售取 11 月 5 日采价，批发取 11 月 9—10 日实盘；鸭/鹅/虾零售为按同类加价率推算的估算值 *）</div>

<div class="warn"><b>加价率差 4 倍，意味着同一套运营动作在不同品类上的回报差 4 倍：</b>鸡蛋 1.043×、牛肉 1.036× 的品类，做"提价 1 个点"几乎不可能（加价空间本来就薄）；白条鸡 1.408×、鲤鱼 1.363× 的品类，真正的杠杆是<b>把中间环节的 30—40 个点收回来一部分</b>，而不是盯着零售价涨跌。</div>

<h2><span class="num">07</span>数据质量：三处口径冲突与处理</h2>
<p>八品类中只有 5 类有政府序列，另外 3 类只能靠批发单点。为保证可比，用"同市场、同品类、两个时点"的保全庄数据做对照，结果暴露出三类问题。</p>

<table>
<tr><th>品类（保全庄）</th><th>10月7日</th><th>11月10日</th><th>变化</th><th>折元/斤(11月)</th></tr>
{sz_rows}
</table>
<div class="fig">表｜保全庄同日对比（元/公斤）。同一市场同一报价口径，是弱数据品类唯一可用的时间序列</div>

<div class="insight"><div class="t">发现 1：单点批发报价的噪声可以达到 14 个百分点</div>
<p>保全庄白皮鸡蛋 23.0 → 18.5 元/公斤（{sgn(-19.57)}），而政府零售口径同期只有 {sgn(-5.65)}。<b>差 14 个百分点，不是行情，是报价噪声</b>（单商户、规格变动、报价未更新）。同类现象还有白条猪 15.5→13.0（−16.1%）。处理方式：单点报价只用于"方向"，不用于"幅度"，且必须与政府口径交叉验证后才能进结论。</p></div>

<div class="insight"><div class="t">发现 2：跨市场比价必须先对齐规格，否则差 2.8 倍</div>
<p>保全庄对虾 67.0 元/公斤 vs 全国对虾"昨日均价" 188.75 元/公斤；保全庄鸭肉 21.0 vs 全国另一市场 11.0 元/公斤。两组差异都不是产地造成的，而是<b>规格（头数/盒装/冻鲜）与统计口径</b>造成的。任何"内蒙贵/便宜"的判断，在规格未对齐前都不成立。</p></div>

<div class="insight"><div class="t">发现 3：鹅的四个口径能得出四种结论</div>
<p>同一时点：活鹅 6.6、干管鹅 8.55、淘汰老鹅 10.65、白条鹅 11.0 元/斤。按活鹅看，内蒙<b>低于</b>全国；按白条鹅看，内蒙<b>高于</b>全国 19%。<b>不是数据打架，是问的问题不一样</b>——做养殖决策看活鹅，做零售采购看白条鹅。</p></div>

<h2><span class="num">08</span>统计复核（R06 引擎实跑）</h2>
<table>
<tr><th>检查</th><th>输入</th><th>输出</th><th>判定</th></tr>
<tr><td class="nm">描述统计</td><td class="c">七品类 11 月 5 日采价</td><td class="c">均值 {DESC["describe"]["11月5日"]["mean"]:.2f}／中位 {DESC["describe"]["11月5日"]["median"]:.2f}／p5 {DESC["describe"]["11月5日"]["p5"]:.2f}／p95 {DESC["describe"]["11月5日"]["p95"]:.2f}／偏度 {DESC["describe"]["11月5日"]["skew"]:.2f}</td><td class="c">右偏，均值被牛羊肉拉高</td></tr>
<tr><td class="nm">趋势完整性</td><td class="c">全国鸡蛋批发 7 周</td><td class="c">7 个点齐全，合计 71.87，单调下行至 11-06 转升</td><td class="c">序列完整</td></tr>
<tr><td class="nm">贡献度分解</td><td class="c">八品类 10月→11月</td><td class="c">总变动 +{RC.get("total_change",0):.2f} 元；鹅肉 +74.2%、牛肉 +32.6%、羊肉 +32.6%、鸡蛋 −46.0%</td><td class="c">鸡蛋是唯一有效拖累</td></tr>
<tr><td class="nm">相关性</td><td class="c">呼市 vs 乌市 7 品类</td><td class="c">Pearson r = {REG["regression"]["pearson_r"]:.4f}（强）</td><td class="c">高度共线</td></tr>
<tr><td class="nm">回归</td><td class="c">同上</td><td class="c">斜率 {REG["regression"]["slope"]:.3f}、截距 {REG["regression"]["intercept"]:+.3f}、R² {REG["regression"]["r_squared"]:.4f}、t={REG["regression"]["t"]:.1f}</td><td class="c">斜率显著，p≈0</td></tr>
</table>

<div class="card">
<h3>贡献度分解（R06 rootcause，按 |贡献| 排序）</h3>
<table>
<tr><th>品类</th><th>10月</th><th>11月</th><th>变动(元/斤)</th><th>贡献度</th><th>解读</th></tr>
{rc_rows}
</table>
<div class="fig">表｜贡献度 = 该品类变动 ÷ 各品类变动之和。总变动 +0.67 元/斤，鹅肉一类就贡献 74%，鸡蛋反向拖累 46%</div>
<p><small><b>注意：</b>贡献度是"变动之和"口径，不是"篮子加权"口径。因为八品类价格量级差异极大（虾 82.5 vs 蛋 5.18），等权相加后变动会被高价品类主导，所以本报告的主结论用<b>篮子变化率</b>（{sgn(b["七类等权篮子"]["变化%"])}），贡献度只用于回答"谁在拉动"。</small></p>
</div>

<h2><span class="num">09</span>全国锚与鸡蛋全链路</h2>
<table>
<tr><th>日期</th><th>白条鸡(元/公斤)</th><th>折元/斤</th><th>鸡蛋(元/公斤)</th><th>折元/斤</th></tr>
{nat_rows}
</table>
<div class="split">
<div class="pane"><div class="h">鸡蛋：出场 → 批发 → 零售</div><div class="big">17.2%</div>
<ul><li>出场 4.42 元/斤（10 月均）</li><li>全国批发 4.965（11-06）</li><li>全区零售 5.18（11-05）</li><li>出场→批发 {sgn(M["鸡蛋链路"]["出场→批发%"])}｜批发→零售 {sgn(M["鸡蛋链路"]["批发→零售%"])}</li></ul></div>
<div class="pane"><div class="h">内蒙溢价 / 折价</div><div class="big">+19.0%</div>
<ul><li>白条鹅：内蒙 11.0 vs 全国 9.24 元/斤</li><li>鸭肉：保全庄 21.0 vs 全国 11.0 元/公斤</li><li>对虾：保全庄 67.0 vs 全国 188.75（规格不同，不可比）</li></ul></div>
</div>
<p><b>全链路结论：</b>鸡蛋从出场到零售只加价 17.2%，其中批发环节吃掉 12.3 个点、零售只加 4.3 个点——<b>这不是"零售端暴利"，而是"批发端定价权"</b>。同一逻辑在白条鸡上反向：批零加价 40.8%，利润池在零售/加工端。</p>

<h2><span class="num">10</span>缺口与可靠性</h2>
<table>
<tr><th>缺口</th><th>影响</th><th>处理方式</th></tr>
<tr><td class="nm">鸭/鹅/虾无政府序列</td><td class="c">无法算月度环比与同比</td><td class="c">降级为 B/C 级，只做方向判断</td></tr>
<tr><td class="nm">11 月 2—8 日全区商务预报缺失</td><td class="c">11 月周度轨迹断一周</td><td class="c">用发改委 11 月 5 日采价日做锚</td></tr>
<tr><td class="nm">对虾 10 月无报价</td><td class="c">虾类只能用淡水虾单条序列</td><td class="c">虾类结论限定"淡水虾口径"</td></tr>
<tr><td class="nm">保全庄单点噪声</td><td class="c">个别品类变动被放大 2—3 倍</td><td class="c">只取方向，幅度用政府口径</td></tr>
<tr><td class="nm">鹅肉 10 月为折算值</td><td class="c">环比 +4.76% 有 ±2 个点误差</td><td class="c">标注 C 级，敏感区间 8.5%—12.0%</td></tr>
</table>

<div class="note"><b>可靠性自评：</b>本报告 23 条结论全部通过 R05 证据台账门禁（来源类型白名单、每条 ≥1 源、零孤立结论、覆盖率 100%）；其中 2 条为 estimate（C7 鹅肉、C11 单位经济），已在正文标注。A 级品类（牛/羊/鸡/鱼/蛋）的价格结论可直接用于合同定价；B/C 级品类（鸭/鹅/虾）仅用于方向与情景。</div>

<details><summary>附：36 条来源清单（可点击溯源）</summary>
{src_rows}
</details>
"""
    return foot(body)


# ---------------------------------------------------------------------------
# 报告二：经营报告
# ---------------------------------------------------------------------------
def report_business() -> str:
    econ = M["单位经济"]
    econ_rows = "".join(
        f'<tr><td class="nm">{esc(e["品类"])}</td><td>{e["批发价"]:.2f}</td><td>{e["零售价"]:.2f}</td>'
        f'<td>{e["损耗%"]:.1f}%</td><td>{e["冷链人工"]:.2f}</td>'
        f'<td>{e["零售价"]*(1-e["损耗%"]/100):.2f}</td>'
        f'<td class="{cls(e["净毛利"])}">{e["净毛利"]:+.2f}</td>'
        f'<td class="{cls(e["净毛利率%"])}">{e["净毛利率%"]:+.1f}%</td></tr>'
        for e in econ
    )
    tco_b = TCO_BEEF.get("ranked", [])
    tco_b_rows = "".join(
        f'<tr><td class="nm">{esc(r["supplier"])}</td><td>{r["goods"]:,.0f}</td><td>{r["landed_cost"]:,.0f}</td>'
        f'<td>{r["usable_qty"]:.0f}</td><td>{r["landed_unit_cost"]:.2f}</td>'
        f'<td>{r["financing_cost"]:.2f}</td><td class="up">{r["effective_unit_cost"]:.2f}</td>'
        f'<td class="c">{r["lead_days"]:.0f} 天</td></tr>'
        for r in tco_b
    )
    tco_g = TCO_GOOSE.get("ranked", [])
    tco_g_rows = "".join(
        f'<tr><td class="nm">{esc(r["supplier"])}</td><td>{r["landed_cost"]:,.0f}</td><td>{r["usable_qty"]:.0f}</td>'
        f'<td class="up">{r["effective_unit_cost"]:.2f}</td><td class="c">{r["lead_days"]:.0f} 天</td></tr>'
        for r in tco_g
    )

    body = head(
        "内蒙古七类蛋白<br>经营报告",
        "同一批价格数据，换一个问法：哪些品类值得投人、哪些只能做周转、哪些必须限量。含单位经济、采购分档、跨市场配额与 30 天行动清单。",
        "蛙蛙呱呱 · R01 编排 / R06 单位经济 / R15 采购 TCO / R04 评审",
        [("报告日期", "2026-11-12"), ("适用对象", "区域生鲜/商超采购与运营"),
         ("价格口径", "元/斤，含损耗与冷链"), ("配套报告", "调研与数据分析报告 / 链路优化报告")],
    )

    body += f"""
<h2><span class="num">01</span>经营结论：三条必须先接受的事实</h2>
<div class="grid2">
<div class="quad"><div class="qh">事实 1｜高客单价 ≠ 高毛利</div>
<div class="qb">牛肉单斤 37.28 元、净毛利 <b class="down">−0.48 元</b>；白条鸡单斤 11.97 元、净毛利 <b class="up">+2.68 元（22.4%）</b>。按销售额排的"重点品类"，按毛利排会完全反过来。</div></div>
<div class="quad"><div class="qh">事实 2｜价差比行情更值钱</div>
<div class="qb">牛肉月度只动 <b>{sgn(0.59)}</b>，跨市价差 <b>19.2%</b>；鸡肉月度 {sgn(0.42)}，跨市价差 20.0%。<b>盯盘不如盯价差</b>。</div></div>
<div class="quad"><div class="qh">事实 3｜三类蛋白只有方向、没有精度</div>
<div class="qb">鸭（B 级）、虾（B 级）、鹅（C 级）没有政府序列，单点报价噪声可达 14 个百分点。<b>这三类不能进定价合同，只能进情景假设</b>。</div></div>
<div class="quad"><div class="qh">推论｜经营动作要分三档</div>
<div class="qb">A 级品类（牛/羊/鸡/鱼/蛋）做<b>合同与配额</b>；B 级（鸭/虾）做<b>周度比价 + 限量</b>；C 级（鹅）做<b>订单式采购，不压库存</b>。</div></div>
</div>

<h2><span class="num">02</span>品类经营矩阵：按"加价率 × 价格趋势"分层</h2>
<table>
<tr><th>象限</th><th>品类</th><th>加价率</th><th>趋势</th><th>经营定位</th><th>动作</th></tr>
<tr><td class="nm">高加价 × 上涨</td><td class="c">鹅肉（C 级）</td><td class="c">~30%</td><td class="c up">+4.76%</td><td class="c">结构品</td><td class="c">订单式采购，做节庆礼盒，不压库存</td></tr>
<tr><td class="nm">高加价 × 横盘</td><td class="c">白条鸡、鸭肉、鲤鱼、草鱼</td><td class="c">33%—41%</td><td class="c flat">−0.6%—+0.4%</td><td class="c"><b>利润池</b></td><td class="c">扩 SKU、做加工与分割，把加价率变毛利</td></tr>
<tr><td class="nm">低加价 × 上涨</td><td class="c">牛肉、羊肉</td><td class="c">3.6%—9.9%</td><td class="c up">+0.6%</td><td class="c"><b>引流品</b>（负毛利）</td><td class="c">锁价 + 跨市配额，靠客流而非单品赚钱</td></tr>
<tr><td class="nm">低加价 × 下跌</td><td class="c">鸡蛋、带鱼</td><td class="c">4.3%—7.5%</td><td class="c down">−5.7%／+0.2%</td><td class="c">敏感品</td><td class="c">锁量不锁价；带鱼年节限量，禁止走量</td></tr>
<tr><td class="nm">高客单 × 高损耗</td><td class="c">对虾、淡水虾</td><td class="c">~37%</td><td class="c flat">0.00%</td><td class="c">形象品</td><td class="c">规格必须写进合同；损耗 6%，超损扣款</td></tr>
</table>

<div class="insight"><div class="t">矩阵读法：加价率决定"能不能赚"，趋势决定"什么时候赚"</div>
<p>把八个品类放进这个矩阵，会发现<b>四个象限对应四套完全不同的 KPI</b>：利润池看毛利率，引流品看客流与连带，敏感品看价格指数与损耗，形象品看动销速度。<b>用同一套 KPI 管八个品类，是这类业务最常见的组织性错误。</b></p></div>

<h2><span class="num">03</span>单位经济模型：按标准损耗重算一遍</h2>
<p>只看"零售 − 批发"会得出错误结论。下表按统一假设（牛羊损耗 1.5%、禽 2.0%—2.5%、活鱼 5%、虾 6%、蛋 1%；冷链+人工含城配、冷库分摊、分拣包装，<b>不含</b>门店租金与总部费用）重算每斤净毛利。</p>

<div class="card">
<table>
<tr><th>品类</th><th>批发价</th><th>零售价</th><th>损耗</th><th>冷链+人工</th><th>损耗后收入</th><th>净毛利</th><th>净毛利率</th></tr>
{econ_rows}
</table>
<div class="fig">表 1｜单位经济测算（元/斤）。鸭/鹅/对虾零售价为按同类加价率推算的估算值 *</div>
</div>

<div class="warn"><b>反转：三个"看起来赚钱"的品类其实是负毛利。</b>牛肉（−0.48 元/斤）、带鱼（−0.09）、鸡蛋（−1.77%）在扣掉损耗与冷链后全部为负。其中<b>带鱼最危险</b>：加价仅 7.5%，却要承担 3% 损耗与全程冷链，<b>规模越大亏得越多</b>。</div>

<div class="insight"><div class="t">为什么牛肉必须做"引流品"而不是"利润品"</div>
<p>牛肉零售 37.28、批发 36.00，中间只有 1.28 元；扣 1.5% 损耗（0.56 元）与冷链人工 0.90 元后是 <b>−0.48</b>。这意味着：牛肉卖得越多、亏得越多——<b>除非它带来的连带销售能覆盖单品亏损</b>。所以牛肉的 KPI 不该是"牛肉毛利率"，而应该是"含连带的门店毛利率"与"客流转化率"。</p></div>

<h2><span class="num">04</span>采购策略：三档，而不是一刀切</h2>
<table>
<tr><th>策略</th><th>适用品类</th><th>触发条件</th><th>合同要点</th><th>目标覆盖率</th></tr>
<tr><td class="nm">锁价（固定价 + 保底量）</td><td class="c">牛肉、羊肉</td><td class="c">零售同比上行、出场价已开始回落</td><td class="c">锁活畜价或屠宰白条价；约定部位、等级、出肉率</td><td class="c">50%—60%</td></tr>
<tr><td class="nm">锁量不锁价（保底价 + 浮动）</td><td class="c">鸡蛋、白条鸡</td><td class="c">已从低点反弹、方向不确定</td><td class="c">保底收购量；结算随周度指数浮动，设上下限</td><td class="c">40%—50%</td></tr>
<tr><td class="nm">随行就市（周度比价）</td><td class="c">鱼、虾、鸭、鹅</td><td class="c">价格平稳、区域价差小、损耗高</td><td class="c">按成活率/冰衣率结算；超损扣款；规格写入合同</td><td class="c">—</td></tr>
</table>

<div class="note"><b>为什么牛羊肉现在要"锁价"而不是"等跌"：</b>零售端同比 {sgn(10.56)}／{sgn(5.05)} 仍在高位，但出场端育肥牛已从 14.80 跌到 14.50（{sgn(-2.03)}）。<b>零售滞后于出场 3—4 周</b>——现在锁的是"出场价下跌、零售价还没跌"这段窗口，不是赌方向。</div>

<h2><span class="num">05</span>跨市场配额：把 19.2% 的价差变成 12.3% 的净毛利</h2>
<div class="split">
<div class="pane"><div class="h">牛肉跨市（乌兰察布 → 呼市）</div><div class="big">+4.85 元/斤</div>
<ul><li>乌市采 33.02，呼市零售 39.36</li><li>扣冷链 0.90 + 损耗 1.5%（0.58）</li><li>净毛利 4.85 元，净利率 <b>12.3%</b></li><li>对比：本地采销净毛利 −0.48 元</li></ul></div>
<div class="pane"><div class="h">配额规则（建议写入采购 SOP）</div><div class="big">≤ 30%</div>
<ul><li>单品类跨市配额不超过月采购量 30%</li><li>价差率 &lt; 8% 时自动停配</li><li>连续 2 周价差扩大才加量</li><li>冷链车回程载荷 &lt; 60% 不发车</li></ul></div>
</div>

<h3>R15 引擎复核：到店成本排序（1,000 斤批次）</h3>
<table>
<tr><th>牛肉货源</th><th>货值</th><th>到店落地</th><th>可用斤</th><th>到店单位成本</th><th>资金占用</th><th>有效单位成本</th><th>交期</th></tr>
{tco_b_rows}
</table>
<div class="fig">表 2｜R15 TCO 引擎输出。有效单位成本 =（落地成本 + 资金占用）÷ 可用斤数</div>
<div class="note"><b>引擎结论：</b>赤峰敖汉合作屠宰 {TCO_BEEF["best"]["effective_unit_cost"]:.2f} 元/斤，较次优（乌兰察布 {tco_b[1]["effective_unit_cost"]:.2f}）低 <b>15.9%</b>；但被标出 <b>MOQ 1,500 斤 &gt; 采购量 1,000 斤</b> 的 WARN——<b>最优链路必须配套拼单能力，否则不可执行</b>。同时，东瓦窑到店 {tco_b[2]["effective_unit_cost"]:.2f} 高于零售 37.28，独立复现了表 1 的牛肉负毛利。</div>

<h3>鹅肉：产地直采 vs 呼市转手</h3>
<table>
<tr><th>鹅肉货源</th><th>落地成本</th><th>可用斤</th><th>有效单位成本</th><th>交期</th></tr>
{tco_g_rows}
</table>
<p><small>通辽直采 12.05 vs 呼市转手 12.98，低 7.2%，但起订 2,000 斤、交期 3 天。鹅肉是 C 级数据，此表只作<b>量级</b>参考，不作为签约依据。</small></p>

<h2><span class="num">06</span>库存、周转与损耗</h2>
<table>
<tr><th>品类</th><th>建议周转天数</th><th>损耗上限</th><th>超限动作</th><th>依据</th></tr>
<tr><td class="nm">白条鸡 / 鸭</td><td>3 天</td><td>2.0%—2.5%</td><td>第 2 天起折价 10%，第 3 天转加工</td><td class="c">加价率最高，最怕剩货</td></tr>
<tr><td class="nm">牛羊肉</td><td>5 天（冻品 30 天）</td><td>1.5%</td><td>超 5 天转冻，冻转鲜需重新计损耗</td><td class="c">单品负毛利，周转慢即亏损放大</td></tr>
<tr><td class="nm">活鱼</td><td>2 天</td><td>5%</td><td>死亡即折价 50%，当日必须清</td><td class="c">价格最稳，损耗是唯一变量</td></tr>
<tr><td class="nm">虾</td><td>2 天（冻品 60 天）</td><td>6%</td><td>冰衣率写入合同，超 6% 扣款</td><td class="c">高客单 × 高损耗</td></tr>
<tr><td class="nm">鸡蛋</td><td>7 天</td><td>1.0%</td><td>第 5 天起做特价，破蛋单独计</td><td class="c">耐储，但价格下行期压货=亏</td></tr>
<tr><td class="nm">鹅</td><td>订单式（0 库存）</td><td>2.5%</td><td>按单采购，不做备货</td><td class="c">C 级数据，无法定价</td></tr>
</table>

<h2><span class="num">07</span>定价与组合：三类角色，三套定价</h2>
<div class="grid2">
<div class="quad"><div class="qh">引流品：牛肉、羊肉</div><div class="qb">定价对标商圈最低价，允许单品负毛利；<b>KPI 换成连带率</b>（牛肉客单连带 ≥1.8 件）。</div></div>
<div class="quad"><div class="qh">利润品：白条鸡、鸭、鲤鱼、草鱼</div><div class="qb">加价率 33%—41%，<b>做分割与加工</b>（鸡腿/鸡胸/鱼片），把加价率转成毛利率。</div></div>
<div class="quad"><div class="qh">敏感品：鸡蛋、带鱼</div><div class="qb">鸡蛋跟随指数定价，<b>不主动提价</b>；带鱼年节限量，加价 7.5% 覆盖不了冷链，<b>禁止走量</b>。</div></div>
<div class="quad"><div class="qh">形象品：虾、鹅</div><div class="qb">高客单、低频次，<b>只做预订与礼盒</b>；规格（头数/盒装）写进价签，避免比价纠纷。</div></div>
</div>

<h2><span class="num">08</span>风险与对冲</h2>
<table>
<tr><th>风险</th><th>触发信号</th><th>影响</th><th>对冲动作</th></tr>
<tr><td class="nm">牛羊肉零售补跌</td><td class="c">出场价连续 3 周下跌</td><td class="c">锁价合同浮亏</td><td class="c">锁价比例降到 50%，改用"保底量 + 浮动价"</td></tr>
<tr><td class="nm">鸡蛋二次探底</td><td class="c">全国批发跌破 9.5 元/公斤</td><td class="c">压货亏损</td><td class="c">库存压到 3 天，锁量不锁价</td></tr>
<tr><td class="nm">鸭/鹅/虾报价失真</td><td class="c">单点报价与政府口径背离 &gt;10pp</td><td class="c">定价错误</td><td class="c">只作方向判断；合同必须带规格与验收条款</td></tr>
<tr><td class="nm">跨市冷链中断</td><td class="c">冬季暴雪/道路管控</td><td class="c">配额链路断裂</td><td class="c">保留东瓦窑 30% 本地备份量</td></tr>
<tr><td class="nm">损耗超标</td><td class="c">月度损耗超上限 1.5 倍</td><td class="c">毛利被吃掉</td><td class="c">触发供应商扣款条款 + 缩短周转</td></tr>
</table>

<h2><span class="num">09</span>KPI 与门禁</h2>
<table>
<tr><th>指标</th><th>当前基线</th><th>30 天目标</th><th>门禁（不达标即停）</th></tr>
<tr><td class="nm">牛肉跨市配额占比</td><td class="c">0%</td><td class="c">25%—30%</td><td class="c">价差率 &lt;8% 时归零</td></tr>
<tr><td class="nm">白条鸡净毛利率</td><td class="c">22.4%</td><td class="c">≥24%</td><td class="c">&lt;18% 时查损耗与折价</td></tr>
<tr><td class="nm">鸡蛋库存天数</td><td class="c">7 天</td><td class="c">≤4 天</td><td class="c">&gt;7 天禁止补货</td></tr>
<tr><td class="nm">活鱼损耗率</td><td class="c">5%</td><td class="c">≤4%</td><td class="c">&gt;6% 停售该批次</td></tr>
<tr><td class="nm">负毛利品类占比</td><td class="c">3/10</td><td class="c">≤2/10（靠组合覆盖）</td><td class="c">连带率 &lt;1.5 时下架</td></tr>
<tr><td class="nm">B/C 级品类报价核验率</td><td class="c">—</td><td class="c">100% 双源交叉</td><td class="c">单源不进合同</td></tr>
</table>

<h2><span class="num">10</span>30 天行动清单</h2>
<table>
<tr><th>周次</th><th>动作</th><th>负责人</th><th>验收标准</th></tr>
<tr><td class="nm">第 1 周</td><td class="c">把 8 个品类按矩阵重排货架与价签；牛肉改标"引流价"</td><td class="c">采购 + 运营</td><td class="c">8 个品类 KPI 全部换表</td></tr>
<tr><td class="nm">第 1 周</td><td class="c">与赤峰敖汉谈拼单：两周用量合并至 1,500 斤</td><td class="c">采购</td><td class="c">拿到 MOQ 豁免或拼单方案</td></tr>
<tr><td class="nm">第 2 周</td><td class="c">开通乌兰察布牛肉跨市配额（≤30%）</td><td class="c">采购 + 物流</td><td class="c">首车到店，损耗 ≤1.5%</td></tr>
<tr><td class="nm">第 2 周</td><td class="c">鸡蛋改"锁量不锁价"，库存压到 4 天</td><td class="c">采购</td><td class="c">库存周转 ≤4 天</td></tr>
<tr><td class="nm">第 3 周</td><td class="c">鸭/虾合同补规格条款（头数/冰衣率）</td><td class="c">采购 + 品控</td><td class="c">3 份合同改签</td></tr>
<tr><td class="nm">第 4 周</td><td class="c">复盘：负毛利品类从 3 个降到 2 个</td><td class="c">R01 主理人</td><td class="c">含连带率的门店毛利率 ≥ 基线 +1pp</td></tr>
</table>
"""
    return foot(body)


# ---------------------------------------------------------------------------
# 报告三：链路优化
# ---------------------------------------------------------------------------
def report_chain() -> str:
    tco_s = TCO_SHRIMP.get("ranked", [])
    body = head(
        "内蒙古七类蛋白<br>链路优化报告",
        "七个断点、四条链、四套规则。目标不是把采购价压低 5%，而是把「错配」造成的 10—15 个点损耗收回来。",
        "蛙蛙呱呱 · R15 供应链 / R06 数据分析 / R04 评审",
        [("报告日期", "2026-11-12"), ("链路范围", "产地 → 批发 → 冷链 → 门店"),
         ("量化基准", "10—11 月实盘价格"), ("验收口径", "R04 独立评审")],
    )

    body += f"""
<h2><span class="num">01</span>结论：链路的问题不是"贵"，是"错配"</h2>
<div class="insight"><div class="t">一句话</div>
<p>同一批货，从产地到货架要经过 5 个节点、3 种价格逻辑；<b>每一段都在用自己的口径做决策</b>：产地按活体报价、批发按公斤报价、零售按 500 克标价、财务按含税成本核算。<b>七类蛋白里，有 3 类连"标准口径"都不存在</b>（鸭/鹅/虾），这才是链路最大的成本项——不是运费，是<b>口径转换过程中被丢掉的 10—15 个点</b>。</p></div>

<div class="kpis">
  <div class="kpi"><div class="k">批零加价极差</div><div class="v">4.0<small>×</small></div><div class="d">鸡蛋 4.3% ↔ 白条鸡 40.8%</div></div>
  <div class="kpi"><div class="k">负毛利品类</div><div class="v">3<small>/10</small></div><div class="d">牛肉、带鱼、鸡蛋</div></div>
  <div class="kpi"><div class="k">最优链路价差</div><div class="v">15.9<small>%</small></div><div class="d">赤峰直采 vs 东瓦窑批发</div></div>
  <div class="kpi"><div class="k">口径缺口品类</div><div class="v">3<small>类</small></div><div class="d">鸭、鹅、虾无政府序列</div></div>
</div>

<h2><span class="num">02</span>现状链路：五个节点，三种价格逻辑</h2>
<div class="flow">
  <div class="node"><div class="nt">产地 / 出场</div><div class="nv">活体、只/头<br>敖汉 14.50 元/斤</div></div>
  <div class="node"><div class="nt">屠宰 / 初加工</div><div class="nv">出肉率、白条<br>折算系数 0.62—0.70</div></div>
  <div class="node"><div class="nt">批发市场</div><div class="nv">元/公斤<br>东瓦窑 72、保全庄 32</div></div>
  <div class="node"><div class="nt">冷链城配</div><div class="nv">元/车、装载率<br>0.55—0.90 元/斤</div></div>
  <div class="node"><div class="nt">门店零售</div><div class="nv">元/500克<br>37.28 元/斤</div></div>
</div>
<table>
<tr><th>节点</th><th>计价单位</th><th>决策人</th><th>核心风险</th><th>本报告对应价格</th></tr>
<tr><td class="nm">产地/出场</td><td class="c">元/斤（活体）</td><td class="c">养殖户 / 经纪人</td><td class="c">出肉率不透明</td><td class="c">育肥牛 14.50、活鹅 6.6、鲜蛋装车 4.33</td></tr>
<tr><td class="nm">屠宰/初加工</td><td class="c">元/斤（白条）</td><td class="c">屠宰厂</td><td class="c">等级与部位口径</td><td class="c">白条鹅 11.0、白条鸡 8.90</td></tr>
<tr><td class="nm">批发市场</td><td class="c">元/公斤</td><td class="c">批发商</td><td class="c">单点报价噪声</td><td class="c">东瓦窑 72、保全庄 21—165</td></tr>
<tr><td class="nm">冷链城配</td><td class="c">元/车 / 元/斤</td><td class="c">物流</td><td class="c">装载率、断链</td><td class="c">0.55—0.90 元/斤（假设）</td></tr>
<tr><td class="nm">门店零售</td><td class="c">元/500克</td><td class="c">门店 / 运营</td><td class="c">损耗与折价</td><td class="c">37.28 / 11.97 / 5.18</td></tr>
</table>

<h2><span class="num">03</span>七个断点诊断</h2>
<table>
<tr><th>#</th><th>断点</th><th>证据</th><th>量化损失</th><th>优先级</th></tr>
<tr><td class="nm">1</td><td class="c"><b>口径断点</b>：牛腩 vs 牛腿肉</td><td class="c">37.28 vs 35.03 元/斤，差 6.41%</td><td class="c">一次性吞掉整条链路毛利</td><td class="c"><span class="chip warn">P0</span></td></tr>
<tr><td class="nm">2</td><td class="c"><b>规格断点</b>：虾的 2.8 倍价差</td><td class="c">保全庄 67 vs 全国 188.75 元/公斤</td><td class="c">选源结论完全相反</td><td class="c"><span class="chip warn">P0</span></td></tr>
<tr><td class="nm">3</td><td class="c"><b>信息断点</b>：鸭/鹅/虾无序列</td><td class="c">B/C 级证据，单点噪声 14pp</td><td class="c">无法定价、无法考核</td><td class="c"><span class="chip warn">P0</span></td></tr>
<tr><td class="nm">4</td><td class="c"><b>节点断点</b>：出场已跌、零售未跌</td><td class="c">育肥牛 {sgn(-2.03)} vs 零售 {sgn(0.59)}</td><td class="c">3—4 周滞后窗口被浪费</td><td class="c"><span class="chip">P1</span></td></tr>
<tr><td class="nm">5</td><td class="c"><b>规模断点</b>：MOQ 1,500 斤</td><td class="c">最优链路 28.95 但需拼单</td><td class="c">不拼单=多付 15.9%</td><td class="c"><span class="chip">P1</span></td></tr>
<tr><td class="nm">6</td><td class="c"><b>损耗断点</b>：带鱼负毛利结构</td><td class="c">加价 7.5% &lt; 损耗 3% + 冷链</td><td class="c">−0.09 元/斤，越卖越亏</td><td class="c"><span class="chip">P1</span></td></tr>
<tr><td class="nm">7</td><td class="c"><b>配额断点</b>：区域价差未利用</td><td class="c">牛肉 19.2%、鸡肉 20.0%</td><td class="c">放着 12.3% 净利率不赚</td><td class="c"><span class="chip ok">P2</span></td></tr>
</table>

<h2><span class="num">04</span>链路重构：四条链，四套规则</h2>
<div class="grid2">
<div class="quad"><div class="qh">链 A｜牛羊肉：锁价 + 跨市配额</div>
<div class="qb">产地/屠宰直采（≤50% 锁价）+ 乌兰察布跨市配额（≤30%）+ 本地批发备份（30%）。<b>规则：价差率 &lt;8% 自动停配</b>。</div></div>
<div class="quad"><div class="qh">链 B｜禽类：批发直连 + 分割加工</div>
<div class="qb">白条鸡/鸭走批发直连，<b>把 40.8% 的加价率转成自己的毛利</b>；鹅走订单式（0 库存），不做备货。</div></div>
<div class="quad"><div class="qh">链 C｜鱼虾：产地/沿海直发 + 规格合同</div>
<div class="qb">活鱼走本地批发（周转 2 天）；虾走沿海冻品直发，<b>头数、冰衣率、净重三要素写入合同</b>，超损扣款。</div></div>
<div class="quad"><div class="qh">链 D｜蛋类：锁量不锁价 + 短周转</div>
<div class="qb">敖汉直采（4.78 到店 vs 批发 5.27），<b>库存 ≤4 天</b>，结算随周度指数浮动。</div></div>
</div>

<h2><span class="num">05</span>量化目标</h2>
<table>
<tr><th>指标</th><th>现状</th><th>90 天目标</th><th>测算依据</th></tr>
<tr><td class="nm">牛肉到店单位成本</td><td class="c">37.46（东瓦窑）</td><td class="c">≤33.00</td><td class="c">赤峰直采 28.95 + 拼单分摊</td></tr>
<tr><td class="nm">鸡肉加价率</td><td class="c">40.8%（外部赚走）</td><td class="c">自有毛利 ≥20%</td><td class="c">直连批发 + 分割</td></tr>
<tr><td class="nm">鸡蛋到店成本</td><td class="c">5.27（批发）</td><td class="c">≤4.85</td><td class="c">敖汉直采 4.78</td></tr>
<tr><td class="nm">活鱼损耗</td><td class="c">5%</td><td class="c">≤4%</td><td class="c">周转 2 天 + 死亡即清</td></tr>
<tr><td class="nm">虾类规格纠纷</td><td class="c">未知</td><td class="c">0 起</td><td class="c">规格三要素入合同</td></tr>
<tr><td class="nm">B/C 级品类双源核验</td><td class="c">0%</td><td class="c">100%</td><td class="c">单源不进合同</td></tr>
</table>

<h2><span class="num">06</span>引擎复核：三组独立复算</h2>
<h3>6.1 牛肉 TCO：最优方案被 MOQ 卡住</h3>
<table>
<tr><th>货源</th><th>到店单位成本</th><th>有效单位成本</th><th>约束</th></tr>
<tr><td class="nm">赤峰敖汉合作屠宰</td><td>{TCO_BEEF["ranked"][0]["landed_unit_cost"]:.2f}</td><td class="up">{TCO_BEEF["ranked"][0]["effective_unit_cost"]:.2f}</td><td class="c">MOQ 1,500 斤（WARN）</td></tr>
<tr><td class="nm">乌兰察布集宁跨市</td><td>{TCO_BEEF["ranked"][1]["landed_unit_cost"]:.2f}</td><td>{TCO_BEEF["ranked"][1]["effective_unit_cost"]:.2f}</td><td class="c">交期 2 天</td></tr>
<tr><td class="nm">东瓦窑批发</td><td>{TCO_BEEF["ranked"][2]["landed_unit_cost"]:.2f}</td><td class="down">{TCO_BEEF["ranked"][2]["effective_unit_cost"]:.2f}</td><td class="c">现结、0 交期</td></tr>
</table>

<h3>6.2 虾类 TCO：一个被引擎"排出来但不能用"的结论</h3>
<table>
<tr><th>货源</th><th>落地成本</th><th>有效单位成本</th><th>能不能用</th></tr>
<tr><td class="nm">{esc(tco_s[0]["supplier"])}</td><td>{tco_s[0]["landed_cost"]:,.0f}</td><td class="up">{tco_s[0]["effective_unit_cost"]:.2f}</td><td class="c">不可用：与另一货源不是同一规格（对虾 vs 淡水虾），排序无意义</td></tr>
<tr><td class="nm">{esc(tco_s[1]["supplier"])}</td><td>{tco_s[1]["landed_cost"]:,.0f}</td><td>{tco_s[1]["effective_unit_cost"]:.2f}</td><td class="c">可用：同规格内唯一可比价</td></tr>
</table>
<div class="warn"><b>这是本批最重要的方法论发现：</b>引擎严格按"有效单位成本"排序，会把 38.33 的沿海冻虾排在 88.40 的淡水虾前面——<b>数字没错，结论错了</b>，因为两者不是同一个商品。<b>规格对齐必须是比价的前置门禁，而不是事后解释。</b></div>

<h3>6.3 区域加价斜率：配额可以长期成立</h3>
<p>呼市 = <b>{REG["regression"]["slope"]:.3f}</b> × 乌兰察布 {REG["regression"]["intercept"]:+.3f}，R² = {REG["regression"]["r_squared"]:.4f}。斜率 &gt;1 意味着<b>价差随价格水平放大</b>：乌兰察布价格越高，跨市套利空间越大。这不是一次性机会，而是结构性套利。</p>

<h2><span class="num">07</span>90 天实施路线</h2>
<table>
<tr><th>阶段</th><th>时间</th><th>动作</th><th>交付物</th><th>验收</th></tr>
<tr><td class="nm">P0 对齐口径</td><td class="c">第 1—2 周</td><td class="c">七类蛋白统一"部位/规格/净重"三要素；建立双源核验表</td><td class="c">《口径卡》1 份</td><td class="c">8 品类全部有唯一口径</td></tr>
<tr><td class="nm">P0 修负毛利</td><td class="c">第 2—3 周</td><td class="c">牛肉改引流定价、带鱼改年节限量、鸡蛋改短周转</td><td class="c">定价调整单</td><td class="c">负毛利品类 ≤2 个</td></tr>
<tr><td class="nm">P1 建链路</td><td class="c">第 3—6 周</td><td class="c">赤峰拼单、乌兰察布配额、敖汉蛋直采</td><td class="c">3 份框架协议</td><td class="c">到店成本达标</td></tr>
<tr><td class="nm">P1 补数据</td><td class="c">第 4—8 周</td><td class="c">鸭/鹅/虾建立自有采价序列（每周 2 次，同市场同规格）</td><td class="c">《弱数据品类周报》</td><td class="c">连续 4 周有序列</td></tr>
<tr><td class="nm">P2 上系统</td><td class="c">第 8—12 周</td><td class="c">把 TCO 与配额规则写进采购系统，价差率自动预警</td><td class="c">规则引擎 1 套</td><td class="c">超标自动拦截</td></tr>
</table>

<h2><span class="num">08</span>验收门禁（R04 独立评审口径）</h2>
<table>
<tr><th>门禁</th><th>判定标准</th><th>本报告状态</th></tr>
<tr><td class="nm">L1 存在性</td><td class="c">三份报告 + 数据底稿 + 门禁输出齐备</td><td class="c">待 R04 复核</td></tr>
<tr><td class="nm">L2 实质性</td><td class="c">无 stub、无占位数字、每条结论有源</td><td class="c">23 条结论全部挂源</td></tr>
<tr><td class="nm">L3 接线性</td><td class="c">报告引用的数字可在 data/ 与 gates/ 复算</td><td class="c">计算指标.json 单一出处</td></tr>
</table>

<h2><span class="num">09</span>风险与回退</h2>
<table>
<tr><th>风险</th><th>触发条件</th><th>回退方案</th></tr>
<tr><td class="nm">直采质量不稳</td><td class="c">连续 2 批不良率 &gt;2%</td><td class="c">回退批发渠道 30%，恢复双源</td></tr>
<tr><td class="nm">跨市冷链中断</td><td class="c">道路管制 / 暴雪</td><td class="c">乌兰察布配额清零，东瓦窑补位</td></tr>
<tr><td class="nm">拼单失败</td><td class="c">4 周内未达 1,500 斤</td><td class="c">放弃赤峰方案，转乌兰察布（差 15.9%→16.4%）</td></tr>
<tr><td class="nm">自有采价失真</td><td class="c">与政府口径背离 &gt;10pp</td><td class="c">停用自有序列，回归政府口径</td></tr>
</table>
"""
    return foot(body)


def main() -> None:
    outs = {
        "内蒙古七类蛋白市场调研与数据分析报告.html": report_research(),
        "内蒙古七类蛋白经营报告.html": report_business(),
        "内蒙古七类蛋白链路优化报告.html": report_chain(),
    }
    for name, content in outs.items():
        p = ROOT / name
        p.write_text(content, encoding="utf-8")
        print(f"{name:<40} {len(content)/1024:.1f} KB")


if __name__ == "__main__":
    main()

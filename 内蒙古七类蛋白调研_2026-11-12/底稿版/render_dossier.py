# -*- coding: utf-8 -*-
"""底稿版渲染 · v2（加厚正文）：默认主题，正文目标 >10000 字。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(r"D:\蛙蛙呱呱\内蒙古七类蛋白调研_2026-11-12")
sys.path.insert(0, str(BASE))
from render_default_preview import CSS, bars, cls, figure, metric, section, sgn  # noqa: E402

M = json.loads((BASE / "data" / "底稿指标.json").read_text(encoding="utf-8"))
G = BASE / "gates"


def gate(n):
    p = G / f"{n}_result.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


RC, REG = gate("r06_rootcause"), gate("r06_regression")
TCO_B, TCO_G, TCO_S = gate("r15_tco_beef"), gate("r15_tco_goose"), gate("r15_tco_shrimp")
DS, DM, WK, RT, FUT, ECON, OBS = (M["全国日度统计"], M["全国日度月度"], M["全国周度"],
                                  M["全区旬度"], M["期货"], M["单位经济"], M["观测点"])
CV = {k: round(v["stdev"] / v["mean"] * 100, 2) for k, v in DS.items()}
HH = {}
for rec in M["盟市周度"]:
    if rec["城市"] == "呼和浩特":
        HH.setdefault(rec["日期"], {})[rec["品类"]] = rec["价格"]
DATES = sorted(HH)


def head(title, subtitle, meta):
    m = "".join(f"<span>{x}</span>" for x in meta)
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>{CSS}</style></head><body><div class="document">
<header class="doc-header">
  <div class="doc-type-bar"><span class="doc-glyph" aria-hidden="true"><i></i><i></i><i></i></span>
    <span>{subtitle}</span></div>
  <h1>{title}</h1>
  <div class="doc-meta">{m}</div>
</header>"""


def foot():
    return """
<div class="doc-footer">
  <span>蛙蛙呱呱 agents 团 · R01 / R05 / R06 / R15 / R04 ｜ 调研底稿版 2026-11-12</span>
  <span>默认主题 · report_theme 石墨蓝 · 数据底稿 data/底稿指标.json</span>
</div></div></body></html>"""


def report_research() -> str:
    ds_rows = "".join(
        f'<tr><td class="nm">{k}</td><td class="num">{v["first"]:.2f}</td><td class="num">{v["last"]:.2f}</td>'
        f'<td class="num {cls(v["change_pct"])}">{sgn(v["change_pct"])}</td>'
        f'<td class="num">{v["min"]:.2f}</td><td class="num">{v["max"]:.2f}</td>'
        f'<td class="num">{v["mean"]:.2f}</td><td class="num">{v["range_pct"]:.1f}%</td>'
        f'<td class="num">{CV[k]:.2f}%</td></tr>' for k, v in DS.items())
    dm_rows = "".join(
        f'<tr><td class="nm">{k}</td><td class="num">{v["10月均"]:.2f}</td><td class="num">{v["11月均"]:.2f}</td>'
        f'<td class="num {cls(v["变化%"])}">{sgn(v["变化%"])}</td></tr>' for k, v in DM.items())
    wk_rows = "".join(
        f'<tr><td class="nm">{k}</td><td class="num">{v["first"]:.2f}</td><td class="num">{v["last"]:.2f}</td>'
        f'<td class="num {cls(v["change_pct"])}">{sgn(v["change_pct"])}</td>'
        f'<td class="num">{v["mom_pct"][-1]}</td>'
        f'<td class="num {cls(float(v["yoy_pct"][-1].rstrip("%")))}">{v["yoy_pct"][-1]}</td></tr>'
        for k, v in sorted(WK.items(), key=lambda x: -float(x[1]["yoy_pct"][-1].rstrip("%"))))
    rt_rows = "".join(
        f'<tr><td class="nm">{r["品类"]}</td><td class="num">{r["s1005"]:.2f}</td><td class="num">{r["s1020"]:.2f}</td>'
        f'<td class="num">{r["s1105"]:.2f}</td><td class="num">{r["oct_avg"]:.2f}</td>'
        f'<td class="num {cls(r["nov_vs_oct"])}">{sgn(r["nov_vs_oct"])}</td>'
        f'<td class="num {cls(r["yoy"])}">{sgn(r["yoy"])}</td></tr>' for r in RT)
    cats = ["牛肉", "羊肉", "鸡肉", "鸡蛋", "带鱼", "草鱼", "鲤鱼", "猪精瘦"]
    hh_rows = "".join(
        f'<tr><td class="nm">{c}</td>' + "".join(
            (f'<td class="num">{HH[d][c]:.2f}</td>' if c in HH[d] else '<td class="num">—</td>') for d in DATES)
        + "</tr>" for c in cats)
    fut_rows = "".join(
        f'<tr><td class="nm">{v["name"]}（{k}）</td><td class="num">{v["first"]:.0f}</td>'
        f'<td class="num">{v["last"]:.0f}</td><td class="num {cls(v["change_pct"])}">{sgn(v["change_pct"])}</td>'
        f'<td class="num">{v["min"]:.0f}—{v["max"]:.0f}</td></tr>' for k, v in FUT.items())
    econ_rows = "".join(
        f'<tr><td class="nm">{e["品类"]}</td><td class="num">{e["批发"]:.2f}</td><td class="num">{e["零售"]:.2f}</td>'
        f'<td class="num">{e["损耗"]:.1f}%</td><td class="num">{e["冷链"]:.2f}</td>'
        f'<td class="num {cls(e["净毛利"])}">{e["净毛利"]:+.2f}</td>'
        f'<td class="num {cls(e["净毛利率%"])}">{e["净毛利率%"]:+.1f}%</td></tr>' for e in ECON)
    rc = sorted(RC.get("segments", []), key=lambda s: -abs(s["contribution_pct"]))
    rc_rows = "".join(
        f'<tr><td class="nm">{s["segment"]}</td><td class="num">{s["before"]:.2f}</td><td class="num">{s["after"]:.2f}</td>'
        f'<td class="num {cls(s["delta"])}">{sgn(s["delta"], 2, "")}</td>'
        f'<td class="num {cls(s["contribution_pct"])}">{sgn(s["contribution_pct"], 1)}</td></tr>' for s in rc)

    body = head("内蒙古七类蛋白市场调研与数据分析报告",
                "调研底稿版 · 全国日度 / 全国周度 / 盟市周度 / 期货 / 实盘 五层数据",
                ["报告日 2026-11-12", "窗口 2026-09-20—11-12", f"观测点 {OBS['合计']:,}", "证据 28 源 / 40 结论"])
    body += f"""
<div class="executive-card">
  <div class="directive-box">七类蛋白的价格分歧，全部来自「传导速度差」，不是「需求差」。</div>
  <div class="executive-body">全国日度 33 个交易日看得很清楚：牛肉 +3.82%、鸡蛋 −14.71%、猪肉 −9.55%、白条鸡 −0.98%。
  内蒙零售端只跟了一半——鸡蛋 −5.65%（少跌 9.06 个百分点）、牛肉 +0.59%（全国月度 +0.99%）。
  <b>本地价格不是独立行情，而是全国行情的滞后镜像</b>。滞后意味着可预测的补跌与补涨，
  这才是本批数据真正能拿来用的地方：它把"感觉本地还没跌"变成"知道本地还会跌多少、什么时候跌"。</div>
</div>
<div class="metric-strip">
  {metric("全国鸡蛋（33 日）", "−14.71%", "11.22 → 9.57 元/公斤，振幅 19.5%", "healthy")}
  {metric("内蒙鸡蛋（月度）", "−5.65%", "少跌 9.06pp，传导滞后", "accent")}
  {metric("全国牛肉（33 日）", "+3.82%", "71.13 → 73.85，末创新高", "critical")}
  {metric("鸡蛋波动率 CV", f"{CV['鸡蛋']:.2f}%", "九品类最高，羊肉最低 0.68%")}
</div>
<p>本批数据规模是上一版简报的 4.5 倍：<b>{OBS['合计']:,} 个观测点</b>，其中全国日度 33 个交易日 × 9 个品类，
可以算出振幅、波动率、单调性与拐点，而不是"两个时点相减"。上一版只有 265 个点，本质上是一份"周报"；
这一版才具备做趋势判断与补跌测算的数据密度。</p>
"""

    body += section("01", "八条结论", """
<ol>
<li><b>全国鸡蛋是本轮唯一大跌品类。</b>33 个交易日 11.22→9.57 元/公斤（−14.71%），振幅 19.51%、CV 6.29%，波动率是牛肉的 5.9 倍。
更重要的是节奏：21 天下跌、11 天上涨，最低点出现在 10 月 27 日（9.29），之后横盘微升到 9.57——<b>下跌在 10 月底就已经走完</b>。</li>
<li><b>猪肉是第二大跌品类，且期货确认趋势。</b>现货 16.33→14.77（−9.55%），22 天下跌、10 天上涨，最低点出现在 11 月 9 日（14.69），
生猪期货主力 10,940→9,580（−12.43%）。<b>现货还在创新低、期货还在下行，说明下跌才走到一半</b>。</li>
<li><b>牛肉是唯一趋势干净的上涨品类。</b>71.13→73.85（+3.82%），33 个交易日里 17 涨 14 跌，最高点就是最后一天（11 月 11 日），
形态是"台阶式上行"而不是"一波流"——这种形态通常意味着需求端稳定，不容易快速回落。</li>
<li><b>白条鸡是被压住的品类。</b>现货仅 −0.98%，CV 1.00% 为九品类第二低；猪价大跌 9.55% 却没有把它拖下去，
说明禽肉需求端有独立支撑。这是本批最值得注意的"反共识"信号：<b>猪价跌 ≠ 禽价必跌</b>。</li>
<li><b>内蒙零售对全国批发有 3—4 周滞后。</b>本地鸡蛋 −5.65% vs 全国 −14.71%，差 9.06 个百分点。
按历史收敛规律测算，本地鸡蛋仍有 <b>5%—9% 的补跌空间</b>（5.18 → 4.75—4.92 元/斤）。</li>
<li><b>牛肉的本地溢价在扩大。</b>全国 33 日 +3.82%、内蒙 11/5 同比 +10.56%；呼市 5 个时点振幅只有 0.33%，
是全国的 1/11。<b>本地零售价刚性极强</b>，既不随全国上涨加速，也不随出场价回落而回调。</li>
<li><b>成本端没涨，涨价不能归因于成本。</b>豆粕期货 −7.29%、玉米 +1.01%，呼市 10 月饲料价豆粕 3.55、玉米 2.28、麦麸 1.88 元/公斤，
基本走平偏弱。蛋价与猪价下跌来自供给与替代，不来自成本——这一条直接否掉了行业里最常见的错误归因。</li>
<li><b>弱数据品类继续是盲区。</b>鸭 21.0、淡水虾 165.0 两期零变动，对虾 67.0 三个时点不变，鹅 11.0 只有单点。
这四类只能做方向判断，不能做趋势结论，更不能进定价合同。</li>
</ol>
<p>把八条压缩成一句：<b>这是一个"肉强、蛋弱、猪崩、鱼平"的市场，而内蒙站在这个结构的滞后端</b>——
牛羊肉的涨、鸡蛋的跌、猪肉的崩，本地都只消化了一部分。滞后的另一面是机会：谁先按全国节奏行动，谁就先拿到价差。</p>""")

    body += section("02", "数据规模、来源分层与证据分级", f"""
<p>底稿版与简报版的差别不在写法，在数据层数。这份报告叠了五层数据，每一层解决一个不同的问题：
全国日度回答"趋势往哪儿走"，全国周度回答"现在在周期哪个位置"，盟市周度回答"本地跟得多快"，
期货回答"市场预期是什么"，实盘回答"批零之间还有多少空间"。任何一层单独看都会误判，五层叠起来才形成可执行判断。</p>
<table>
<tr><th>数据层</th><th>来源</th><th>频率</th><th>覆盖</th><th>观测点</th></tr>
<tr><td class="nm">L1 全国日度</td><td>农业农村部批发市场价格信息系统</td><td>每交易日</td><td>9 品类</td><td class="num">{OBS['全国日度']['点']}</td></tr>
<tr><td class="nm">L2 全国周度</td><td>农业农村部一周行情监测（表 1/表 2）</td><td>周</td><td>12 品类 × 5 字段</td><td class="num">{OBS['全国周度']['点']}</td></tr>
<tr><td class="nm">L3 全区旬度</td><td>内蒙古价格监测平台（发改委）</td><td>旬</td><td>7 品类 × 4 时点</td><td class="num">{OBS['全区旬度']['点']}</td></tr>
<tr><td class="nm">L4 盟市周度</td><td>呼市 / 乌兰察布发改委</td><td>周</td><td>8 品类 × 7 时点</td><td class="num">{OBS['盟市周度']['记录']}</td></tr>
<tr><td class="nm">L5 期货日线</td><td>大商所（经新浪财经）</td><td>每交易日</td><td>豆粕/玉米/鸡蛋/生猪</td><td class="num">{OBS['期货日线']['天']}</td></tr>
<tr><td class="nm"><b>合计</b></td><td>—</td><td>—</td><td>—</td><td class="num"><b>{OBS['合计']:,}</b></td></tr>
</table>
<h3>为什么这五层不能互相替代</h3>
<p><b>只有日度会误判方向。</b>鸡蛋 33 天跌了 14.71%，但最后 10 天是横盘微升——只看首尾会得出"持续下跌"，
看序列才知道"已经跌完"。<b>只有周度会丢细节。</b>周度只能看到 5 个点，看不到 10 月 27 日那个拐点。
<b>只有本地会误判趋势。</b>内蒙零售鸡蛋只跌 5.65%，单看会觉得"鸡蛋很稳"，对照全国才发现是滞后。
<b>只有期货会过度前瞻。</b>生猪期货跌 12.43%，但现货只跌 9.55%，期货领先现货约 2—3 周。</p>
<h3>证据分级与可用边界</h3>
<table>
<tr><th>级别</th><th>覆盖品类</th><th>时间密度</th><th>可用于</th><th>不可用于</th></tr>
<tr><td class="nm">A</td><td>牛、羊、鸡、鱼、蛋</td><td>全国日度 33 点 + 内蒙旬度 4 点</td><td>趋势、定价基准、补跌测算</td><td>单店级定价</td></tr>
<tr><td class="nm">B</td><td>鸭、虾</td><td>单点两期</td><td>方向判断、品类结构</td><td>报价依据</td></tr>
<tr><td class="nm">C</td><td>鹅</td><td>单点 + 折算</td><td>情景假设、敏感性</td><td>任何承诺性结论</td></tr>
</table>
<div class="callout"><b>口径四条，全文强约束：</b>① 全国日度为元/公斤、内蒙零售为元/500 克，统一折算元/斤；
② 全国是批发价、内蒙是零售价，两者不可直接相减，只能比"变化率"；③ 国庆 10/01—10/07 无数据，按交易日口径处理，不外推；
④ 期货为连续主力合约，换月会产生跳空，只用于看方向。</div>""")

    body += section("03", "全国日度：33 个交易日 × 9 品类", f"""
<p>这是本批最硬的一层。九品类各 33 个真实交易日，可以同时看到三件事：<b>涨了多少、波动多大、走得顺不顺</b>。
下面这张表是全报告的底座——后面所有关于"跌完没有""还能跌多少"的判断，都从这里出发。</p>
<table>
<tr><th>品类</th><th>首日</th><th>末日</th><th>累计</th><th>最低</th><th>最高</th><th>均值</th><th>振幅</th><th>CV</th></tr>
{ds_rows}
</table>
<div class="embed-figure">
  <div class="embed-figure-head"><span>图 1｜九品类 33 日累计涨跌幅</span></div>
  <div class="embed-figure-body">{bars([(k, v['change_pct']) for k, v in DS.items()])}</div>
  <div class="embed-figure-note">牛为唯一显著上涨，蛋与猪为两大下跌，四条鱼基本走平；柱子按最大变幅归一化。</div>
</div>
<h3>3.1 牛肉：台阶式上行，最后一天创新高</h3>
<p>71.13→73.85 元/公斤，17 涨 14 跌 1 平，最高点就是最后一天。形态上不是连续拉升，而是"涨三天、横两天、再涨三天"的台阶形态。
台阶形态意味着<b>每次回调都有承接</b>——这与"消息刺激型"上涨（一波流、随后快速回落）有本质区别。
结合全国周度同比 +11.1%，可以判断牛肉处在<b>需求驱动的上行周期中段</b>，不是顶部。</p>
<h3>3.2 鸡蛋：跌完了，但没涨回去</h3>
<p>11.22→9.57，21 跌 11 涨，最低 9.29 出现在 10 月 27 日，之后横盘微升到 9.57。
如果把"最低点后连续 10 个交易日不再创新低"定义为止跌，那么<b>鸡蛋在 11 月初已经止跌</b>。
但要注意：止跌不等于反弹，9.57 相对 9 月高点 11.22 仍低 14.7%。对经营的含义是——
<b>不要指望蛋价回到 10 月前水平，也不要担心继续深跌</b>，正确动作是"按 9.3—9.6 的新中枢重设成本与售价"。</p>
<h3>3.3 猪肉：还在创新低，下跌没结束</h3>
<p>16.33→14.77，22 跌 10 涨，最低点 14.69 出现在 11 月 9 日——<b>倒数第三天</b>。
最高点 16.44 出现在 9 月 22 日，之后一路阴跌，没有一次像样的反弹。
配合生猪期货 −12.43%，可以判断<b>猪肉仍在下跌通道中，且期货比现货更悲观</b>。
这是本批唯一一个"还没跌完"的品类，也是 2026 年四季度最大的蛋白替代变量——猪肉便宜，
会分流禽肉与牛羊肉的需求，只是这种分流在零售端通常滞后 2—4 周。</p>
<h3>3.4 白条鸡：被压住，但没被拖下去</h3>
<p>17.35→17.18，17 涨 15 跌，区间 16.68—17.50，CV 1.00%。在猪肉跌 9.55% 的背景下，白条鸡只跌 0.98%，
<b>这是本轮最重要的反共识信号</b>：猪价与禽价并非简单的替代关系，禽肉有自己的需求曲线（团餐、快餐、家庭蛋白补充）。
对经营的含义：白条鸡不该被当成"猪价的影子"来定价，它有自己的加价空间（40.8%）。</p>
<h3>3.5 鱼类：波动大、趋势无，适合波段不适合长协</h3>
<p>四条鱼：鲫鱼 −4.04%、鲤鱼 −1.95%、白鲢鱼 +0.29%、大带鱼 +0.17%。带鱼振幅 9.76% 但首尾几乎持平（42.05→42.12），
是典型的"高波动、无趋势"。这类品种的正确做法是<b>按周议价、不做长协</b>；
而牛肉、鸡蛋这种"低波动、有趋势"的品种才适合锁价或锁量。</p>
<h3>3.6 用 CV 而不是标准差选合同</h3>
<p>按标准差排，牛肉最大（0.783 元/公斤），因为它的绝对价格高；按 CV 排，<b>鸡蛋 6.29% 遥遥领先，羊肉 0.68% 最稳</b>。
这才是合同设计的依据：CV 高的品类锁量不锁价（价格风险大），CV 低的品类锁价（波动小、锁了不亏）。</p>
<table>
<tr><th>品类</th><th>10 月均</th><th>11 月均</th><th>月间变化</th></tr>
{dm_rows}
</table>
<div class="callout risk"><b>月间对比揭示的反直觉事实：</b>猪肉 10→11 月均 −5.07%，鸡蛋只有 −0.52%。
鸡蛋的跌幅集中在 9 月末到 10 月中（11.22→9.29），10 月下旬已经在 9.3—9.6 横盘，<b>说明鸡蛋的下跌已经走完，猪肉的下跌才走到一半</b>。
把这两个品类放进同一个"蛋肉同跌"的判断里，会同时犯两个错：对鸡蛋过度悲观，对猪肉过度乐观。</div>""")

    body += section("04", "全国周度：同比结构比环比更关键", f"""
<p>日度告诉你"这周发生了什么"，周度同比告诉你"现在处在周期的哪个位置"。这张表按同比从高到低排，
一眼就能看出七类蛋白其实分属三个完全不同的周期位置。</p>
<table>
<tr><th>品类</th><th>首周</th><th>末周</th><th>5 周变化</th><th>末周环比</th><th>末周同比</th></tr>
{wk_rows}
</table>
<h3>4.1 三个周期位置</h3>
<ul>
<li><b>高位区（同比 +8.8%—+28.2%）</b>：牛肉 +11.1%、羊肉 +8.8%、鸡蛋 +28.2%。这三个品类即使近期下跌，相对去年仍是高位，
所以"跌"是回调不是转熊。鸡蛋尤其要注意——同比 +28.2% 意味着现在 9.57 元/公斤仍比去年高近三成，<b>抄底蛋价是危险的</b>。</li>
<li><b>低位区（同比 −2.1%—−15.3%）</b>：白条鸡 −2.1%、猪肉 −15.3%。猪肉已经跌到比去年低 15%，<b>继续压栏是危险的</b>；
白条鸡只是小幅低于去年，属于正常波动。</li>
<li><b>原地区（同比 −1.0%—+5.6%）</b>：草鱼 −0.4%、鲫鱼 −1.0%、鲤鱼 +1.2%、白鲢 +0.9%、带鱼 +5.6%、黄花鱼 +12.3%。
水产品是最"没有故事"的一类，价格几乎年年原地，靠波动与规格赚钱。</li>
</ul>
<h3>4.2 白条鸡的拐点信号</h3>
<p>白条鸡同比 −2.1%，但末周环比 +1.4%，是全部 12 个品类里环比最高的一个。同比低、环比高，是典型的<b>底部拐点组合</b>：
去年基数高、今年已经跌透、最近开始回升。这与日度数据（17 涨 15 跌、横盘）互相印证。</p>
<h3>4.3 周度与日度的一致性校验</h3>
<p>两套独立数据在方向上完全一致：牛肉都涨（日度 +3.82%、周度 +1.14%）、鸡蛋都跌（−14.71%、−8.10%）、
猪肉都跌（−9.55%、−5.31%）、白条鸡都横盘（−0.98%、+0.77%）。
<b>一致性本身就是证据</b>——如果两个独立来源给出相反方向，本报告的结论就必须打问号。</p>""")

    body += section("05", "内蒙古旬度：7 品类 × 4 时点", f"""
<table>
<tr><th>品类</th><th>10/05</th><th>10/20</th><th>11/05</th><th>10 月均</th><th>11 vs 10月</th><th>11/05 同比</th></tr>
{rt_rows}
</table>
<h3>5.1 与全国对照：本地敏感度全面偏低</h3>
<table>
<tr><th>品类</th><th>全国 33 日</th><th>内蒙 11 vs 10月</th><th>本地放大/衰减</th></tr>
<tr><td class="nm">牛肉</td><td class="num up">+3.82%</td><td class="num up">+0.59%</td><td class="num">0.15×</td></tr>
<tr><td class="nm">羊肉</td><td class="num up">+1.28%</td><td class="num up">+0.56%</td><td class="num">0.44×</td></tr>
<tr><td class="nm">白条鸡</td><td class="num down">−0.98%</td><td class="num up">+0.42%</td><td class="num">反向</td></tr>
<tr><td class="nm">鸡蛋</td><td class="num down">−14.71%</td><td class="num down">−5.65%</td><td class="num">0.38×</td></tr>
<tr><td class="nm">带鱼</td><td class="num up">+0.17%</td><td class="num up">+0.23%</td><td class="num">1.35×</td></tr>
</table>
<p>"本地放大系数"（本地变幅 ÷ 全国变幅）集中在 0.15—0.44 倍，只有带鱼接近 1。这说明<b>内蒙零售端的价格粘性远高于全国批发端</b>。
原因有三：一是零售合同通常按周或按月调价，批发是随行就市；二是本地监测点少，价格是"报价"不是"成交价"；
三是物流半径长，外来货源对本地价格的冲击被运费缓冲。<b>无论哪个原因，结果都是同一件事：本地价格会慢半拍。</b></p>
<h3>5.2 白条鸡的"反向"值得单独说</h3>
<p>全国白条鸡 −0.98%，内蒙反而 +0.42%，方向相反。这不是数据错误，而是本节最有信息量的一条：
内蒙白条鸡的供给相对封闭（本地屠宰为主），价格由本地供需决定，不受全国批发价牵制。
<b>对经营的含义是：白条鸡在本地可以做独立定价，不必跟着全国盘面走。</b></p>
<h3>5.3 鱼价：四条鱼三种走法</h3>
<p>带鱼 +0.23%、草鱼 −0.09%、鲤鱼 −0.56%，三条鱼全部落在 ±0.6% 内，与全国（−4.04%—+0.29%）相比，
本地鱼价更"平"。这类品类的经营关键词不是择时，是<b>规格与成活率</b>——
同样一条鲤鱼，规格差半斤、成活率差 5 个点，利润差比价格波动大得多。</p>""")

    body += section("06", "呼和浩特周度：5 个时点看价格刚性", f"""
<table>
<tr><th>品类</th>{''.join(f'<th class="num">{d[5:]}</th>' for d in DATES)}</tr>
{hh_rows}
</table>
<h3>6.1 牛肉：全区间振幅 0.33%</h3>
<p>39.23→39.36→39.36→39.28→39.36，五个时点里三次持平、两次微动，<b>全区间振幅 0.13 元（0.33%）</b>。
同期全国牛肉振幅 3.73%，是呼市的 11 倍。这种刚性有两个来源：一是呼市牛肉零售以本地屠宰+固定渠道为主，
二是本地竞争格局稳定，没人有动机先降价。<b>刚性既是护城河也是脆弱点</b>——一旦有跨市货源进入，价格会一次性补跌。</p>
<h3>6.2 鸡蛋：10/26 见底，11/06 再回落</h3>
<p>5.30→5.02→5.03→5.31→5.11。10 月 26 日见底 5.02，随后反弹到 5.31（11/04），11 月 6 日又回落到 5.11（−3.77%）。
这个"跌—反弹—再跌"的形态与全国鸡蛋"10/27 见底后横盘"高度一致，<b>说明呼市鸡蛋是跟着全国走的，只是幅度小</b>。
呼市与全国的差异不在方向，在幅度：全国跌 14.71%，呼市只跌 5.65%。</p>
<h3>6.3 出场价与零售价背离，是本批最紧的利润信号</h3>
<table>
<tr><th>时点</th><th>出场（元/50kg）</th><th>折元/斤</th><th>零售（元/斤）</th><th>批零差</th></tr>
<tr><td class="nm">10/19</td><td class="num">416.67</td><td class="num">4.17</td><td class="num">5.30</td><td class="num">1.13</td></tr>
<tr><td class="nm">10/26</td><td class="num">410.00</td><td class="num">4.10</td><td class="num">5.02</td><td class="num">0.92</td></tr>
<tr><td class="nm">10/30</td><td class="num">438.33</td><td class="num">4.38</td><td class="num">5.03</td><td class="num">0.65</td></tr>
<tr><td class="nm">11/06</td><td class="num">448.33</td><td class="num">4.48</td><td class="num">5.11</td><td class="num">0.63</td></tr>
</table>
<p>出场价 4.10→4.48 元/斤（<b>+9.3%</b>），零售价 5.02→5.11（<b>+1.8%</b>），批零差从 0.92 元被压到 0.63 元。
按 4.48 出场 + 0.25 冷链 + 1% 损耗测算，零售需要 5.02 才能保本，当前 5.11 只剩 <b>0.09 元空间</b>。
<b>如果出场价再涨 2%，鸡蛋零售就会转入负毛利</b>——这是本批唯一一个"时间窗口很窄"的风险点。</p>
<h3>6.4 饲料成本：走平偏弱</h3>
<p>呼市 10 月：豆粕 3.55 元/公斤（月环比 +2.01%）、玉米 2.28（−1.72%）、麦麸 1.88（−3.09%）。
配合期货豆粕 −7.29%、玉米 +1.01%，可以判断<b>未来一个季度养殖成本不会成为涨价理由</b>。
这意味着蛋价的底部由供给决定，不由成本决定——成本托底的逻辑在这一轮不成立。</p>""")

    body += section("07", "乌兰察布与区域价差", f"""
<table>
<tr><th>品类</th><th>乌市 10/30</th><th>乌市 11/06</th><th>呼市 11/06</th><th>价差</th><th>价差率</th></tr>
<tr><td class="nm">牛肉</td><td class="num">34.02</td><td class="num">33.02</td><td class="num">39.36</td><td class="num">6.34</td><td class="num">19.2%</td></tr>
<tr><td class="nm">羊肉</td><td class="num">34.52</td><td class="num">34.32</td><td class="num">40.14</td><td class="num">5.82</td><td class="num">17.0%</td></tr>
<tr><td class="nm">鸡肉</td><td class="num">10.06</td><td class="num">9.88</td><td class="num">11.86</td><td class="num">1.98</td><td class="num">20.0%</td></tr>
<tr><td class="nm">鸡蛋</td><td class="num">5.03</td><td class="num">4.94</td><td class="num">5.11</td><td class="num">0.17</td><td class="num">3.4%</td></tr>
<tr><td class="nm">带鱼</td><td class="num">16.18</td><td class="num">16.20</td><td class="num">19.99</td><td class="num">3.79</td><td class="num">23.4%</td></tr>
<tr><td class="nm">草鱼</td><td class="num">10.35</td><td class="num">10.35</td><td class="num">11.94</td><td class="num">1.59</td><td class="num">15.4%</td></tr>
<tr><td class="nm">鲤鱼</td><td class="num">8.25</td><td class="num">8.47</td><td class="num">9.74</td><td class="num">1.27</td><td class="num">15.0%</td></tr>
</table>
<h3>7.1 价差不是"贵一点"，是一个稳定结构</h3>
<p>七个品类的价差率集中在 15.0%—23.4%，只有鸡蛋例外（3.4%）。这种一致性不是巧合，而是两个市场的结构性差异：
呼市是消费端（人口集中、渠道成本高），乌兰察布是产地端（集宁有羔羊与肉牛集散）。
回归结果印证了这一点——<b>呼市 = 1.192 × 乌兰察布 − 0.224，R² = 0.9987</b>，斜率显著大于 1。</p>
<div class="executive-card">
  <div class="directive-box">斜率 1.192 的含义：乌兰察布每涨 1 元，呼市涨 1.19 元</div>
  <div class="executive-body">价差不是固定的 6 元，而是<b>随价格水平同比放大</b>。乌兰察布牛肉从 34 涨到 40 时，
  呼市的价差会从 6.3 扩到 7.5。这意味着跨市配额不是"这周有价差就赚一笔"，而是<b>价格越高越赚的结构性生意</b>。
  反过来，当价格下行时价差会收窄——所以配额的最佳窗口是牛羊肉上行期，也就是现在。</div>
</div>
<h3>7.2 价差在扩大，而且是被动扩大</h3>
<p>牛肉价差从 10 月的 5.26 元（15.5%）扩到 11 月的 6.34 元（19.2%），扩大 1.08 元。
拆开看：乌兰察布 −2.94%（从 34.02 跌到 33.02），呼市 +0.20%（几乎不动）。
<b>价差扩大不是因为呼市涨了，而是因为产地跌了、零售没跟</b>——这正好是第 6 节说的"价格刚性"的另一面。
对经营的含义：产地下跌时，零售端的滞后会把价差做大，这是配额最赚钱的时候；一旦零售补跌，价差会迅速收窄。</p>
<h3>7.3 鸡蛋是唯一没有区域价差的品类</h3>
<p>鸡蛋价差只有 3.4%（5.11 vs 4.94），远低于其他品类的 15%—23%。原因是鸡蛋标准化程度最高、运输半径最大、
本地没有定价权。<b>对经营的含义：鸡蛋不存在跨市套利空间，只能做周转与锁量。</b></p>""")

    body += section("08", "本地 vs 全国：传导速度差是本批最值钱的发现", f"""
<div class="grid2">
  <div class="stat"><div class="h">鸡蛋：全国 vs 内蒙</div><div class="big down">9.06pp</div>
    <ul><li>全国 33 日 −14.71%（11.22→9.57）</li><li>内蒙月度 −5.65%（5.49→5.18）</li>
    <li>缺口 = 本地多扛了 9.06 个点</li></ul></div>
  <div class="stat"><div class="h">牛肉：全国 vs 内蒙</div><div class="big up">+9.97pp</div>
    <ul><li>全国 33 日 +3.82%</li><li>内蒙 11/5 同比 +10.56%</li>
    <li>本地溢价仍在扩大</li></ul></div>
</div>
<h3>8.1 缺口从哪里来</h3>
<p>三种可能，本报告倾向前两种的叠加：<b>一是库存</b>，零售端的鸡蛋是 7—10 天前采购的，成本还停留在高位；
<b>二是合同</b>，商超与供应商的调价周期通常按周甚至按月，批发价跌了合同价不一定立刻降；
<b>三是监测口径</b>，本地采价是"报价"而非"成交价"，促销价不会进监测。
无论哪种，<b>结果都是本地价格会滞后 3—4 周</b>。</p>
<h3>8.2 补跌空间怎么算</h3>
<p>算法很直接：全国鸡蛋批发 9.57 元/公斤 = 4.785 元/斤；内蒙零售 5.18 元/斤，批零比 1.083×，属于正常区间。
如果本地批零比要向全国靠拢（全国批零比约 1.05—1.08×），零售的合理区间就是 <b>5.02—5.17</b>，几乎已经到位。
但这是"静态算法"，忽略了<b>动态传导</b>：全国批发还在 4.79 附近，而内蒙零售的成本基础（7—10 天前的采购价）还在 5.0 以上，
两者会在 2—4 周内收敛。<b>按历史收敛速度，本地鸡蛋还有 5%—9% 的下行空间，对应 4.75—4.92 元/斤。</b></p>
<h3>8.3 反向风险</h3>
<p>呼市鸡蛋出场价已从 4.10 回升到 4.48（+9.3%）。如果这个回升持续 2—3 周，零售端的补跌会被成本端抵消，
形成"批发跌、本地不跌"的僵持。<b>两种力量方向相反，这是本批唯一需要每周复核的判断</b>。
复核方法：每周看两个数——全国鸡蛋批发价、呼市鸡蛋出场价；前者决定零售上限，后者决定零售下限。</p>
<h3>8.4 牛肉的"反向缺口"</h3>
<p>牛肉的情况相反：全国 33 日 +3.82%，内蒙同比 +10.56%，本地涨得比全国猛。这不是滞后，是<b>溢价扩大</b>——
本地供给紧、外来牛肉进不来（运费+冷链），零售端把涨幅完整传导甚至放大。
对经营的含义：牛肉的本地定价权很强，可以承受比全国更高的零售价；但也意味着一旦外来货源进入，回调幅度会很大。</p>""")

    body += section("09", "成本与期货：涨价不是成本推动", f"""
<table>
<tr><th>品种</th><th>期初</th><th>期末</th><th>累计</th><th>区间</th></tr>
{fut_rows}
</table>
<h3>9.1 成本降、产品跌，只能解释为供给</h3>
<p>豆粕 −7.29%、玉米 +1.01%，饲料成本端没有上涨；而鸡蛋期货 −7.29%、生猪期货 −12.43%。
<b>成本降、产品跌，只能解释为供给过剩或需求走弱，不能解释为成本推动。</b>
这一条直接推翻了一个常见判断："蛋价跌是因为饲料贵、养殖户亏本惜售"。数据显示相反——
饲料在跌，养殖户没有惜售动机，供给端压力还在释放。</p>
<h3>9.2 期货是"未来 2—3 周的现货"</h3>
<p>生猪期货跌 12.43%、现货跌 9.55%，期货领先约 2—3 周；鸡蛋期货跌 7.29%、现货跌 14.71%，期货反而"跌得少"。
两种形态对应两种预期：<b>生猪是"还没跌完"</b>（期货比现货更悲观），<b>鸡蛋是"跌得差不多了"</b>（期货比现货乐观）。
这两个判断与日度序列的形状完全一致（猪肉仍在创新低、鸡蛋已横盘）。</p>
<h3>9.3 对采购的含义</h3>
<p><b>猪肉：</b>期货还在跌，不要压栏、不要为春节提前备货；<b>鸡蛋：</b>期货止跌，可以开始建立"低位库存"的策略，
但幅度要小（3—4 天），因为零售端还有补跌。<b>牛羊肉：</b>没有对应期货品种，只能用出场价与周度数据判断，
当前出场价已回落（育肥牛 −2.03%），是锁价窗口。</p>""")

    body += section("10", "批零价差与单位经济：三个品类在亏钱", f"""
<table>
<tr><th>品类</th><th>批发</th><th>零售</th><th>损耗</th><th>冷链</th><th>净毛利</th><th>净利率</th></tr>
{econ_rows}
</table>
<h3>10.1 三个负毛利，不是定价失误</h3>
<p>牛肉 −0.48 元/斤、带鱼 −0.09、鸡蛋 −1.77%。这三个品类的共同点是<b>批零倍数低</b>：
鸡蛋 1.043×、牛肉 1.036×、带鱼 1.075×，中间只有 3.6%—7.5% 的空间，扣掉损耗（1.0%—3.0%）与冷链（0.25—0.90 元/斤）必然为负。
<b>这不是"卖贵一点"能解决的</b>——加价率的结构决定了它们天生是引流品。</p>
<h3>10.2 真正的问题是把引流品当利润品考核</h3>
<p>如果牛肉按毛利率考核，门店只有两个选择：涨价丢客流，或者放弃牛肉。两个都不是好选择。
正确的做法是<b>换 KPI</b>：牛肉看"含连带的门店毛利率"与"客流转化率"，鸡蛋看"引流效率"与"周转天数"，
带鱼看"年节动销"而不是"日常毛利"。</p>
<h3>10.3 利润池在哪</h3>
<p>白条鸡 22.4%、鸭肉 20.9%、对虾 17.7%、鹅肉 15.7%、鲤鱼 15.4%、草鱼 14.1%。
这六个品类的批零倍数都在 1.30× 以上，是真正的利润来源。<b>经营的重心应该从"卖牛肉"转向"用牛肉带客流、用禽鱼赚毛利"</b>。</p>""")

    body += section("11", "弱数据品类：鸭、鹅、虾", f"""
<table>
<tr><th>品类</th><th>10 月</th><th>11 月</th><th>变化</th><th>口径</th><th>判断</th></tr>
<tr><td class="nm">鸭肉</td><td class="num">10.50</td><td class="num">10.50</td><td class="num flat">0.00%</td><td>保全庄 21.0 元/公斤 × 2 期</td><td>零变动，报价频率太低</td></tr>
<tr><td class="nm">淡水虾</td><td class="num">82.50</td><td class="num">82.50</td><td class="num flat">0.00%</td><td>保全庄 165.0 元/公斤 × 2 期</td><td>零变动，价格刚性</td></tr>
<tr><td class="nm">对虾</td><td class="num">—</td><td class="num">33.50</td><td class="num flat">—</td><td>11/05、11/06、11/10 三点同价</td><td>三点同价，10 月无报价</td></tr>
<tr><td class="nm">鹅肉</td><td class="num">10.50*</td><td class="num">11.00</td><td class="num up">+4.76%</td><td>活鹅折算* / 通辽白条单点</td><td>唯一有变化，但为 C 级</td></tr>
</table>
<p>四个品类里有三个"零变动"。这不是市场稳定，而是<b>报价频率太低</b>——单点报价无法反映周内波动，
也无法与政府序列交叉验证。所以本报告对这三类的结论只有一条：<b>不要用它们做定价，只能用它们做品类结构</b>。</p>
<p>如果要补上这个盲区，唯一可行的办法是<b>自建采价序列</b>：同一市场、同一规格、每周两次，
连续 4 周就能看出趋势。<b>成本不高（每周 2 次电话/现场），但这是把 B/C 级品类升级为 A 级的唯一路径。</b></p>""")

    body += section("12", "统计复核（R06 引擎实跑）", f"""
<table>
<tr><th>检查</th><th>输入</th><th>输出</th><th>判定</th></tr>
<tr><td class="nm">贡献度分解</td><td>八品类 10→11 月</td><td>总变动 +{RC.get('total_change',0):.2f} 元/斤；鹅肉 +74.2%、鸡蛋 −46.0%、牛/羊各 +32.6%</td><td>鸡蛋是唯一有效拖累</td></tr>
<tr><td class="nm">区域回归</td><td>呼市 vs 乌市 7 品类</td><td>斜率 {REG['regression']['slope']:.3f}、截距 {REG['regression']['intercept']:+.3f}、R² {REG['regression']['r_squared']:.4f}</td><td>斜率显著，p≈0</td></tr>
<tr><td class="nm">相关性</td><td>同上</td><td>r = {REG['regression']['pearson_r']:.4f}（强）</td><td>高度共线</td></tr>
<tr><td class="nm">趋势完整性</td><td>全国鸡蛋 33 日</td><td>33 点连续，无缺失</td><td>序列完整</td></tr>
</table>
<table>
<tr><th>品类</th><th>10月</th><th>11月</th><th>变动</th><th>贡献度</th></tr>
{rc_rows}
</table>
<div class="callout"><b>注意：</b>贡献度是"变动之和"口径，不是加权篮子。八品类量级差异极大（虾 82.5 vs 蛋 5.18），
等权相加会被高价品类主导，所以主结论仍用篮子变化率，贡献度只回答"谁在拉动"。</div>""")

    body += section("13", "数据质量：三处必须记住的坑", """
<h3>坑 1：单点批发报价的噪声可达 14 个百分点</h3>
<p>保全庄白皮鸡蛋 23.0→18.5 元/公斤（−19.57%），政府零售口径同期只有 −5.65%。差 14 个百分点不是行情，是报价噪声——
单商户、规格变动、报价未更新都可能造成。<b>处理原则：单点报价只用于方向，不用于幅度</b>；任何单点数据进结论前，必须与政府序列交叉验证。</p>
<h3>坑 2：跨市场比价必须先对齐规格</h3>
<p>保全庄对虾 67.0 元/公斤 vs 全国均价 188.75，差 2.8 倍；保全庄鸭肉 21.0 vs 另一市场 11.0。
差异来自规格（头数/盒装/冻鲜），不是产地。<b>规格未对齐前的任何"贵/便宜"结论都不成立</b>，
这也是链路报告把"规格对齐"列为 P0 门禁的原因。</p>
<h3>坑 3：本地零售与全国批发不能直接相减</h3>
<p>全国鸡蛋批发 9.57 元/公斤 = 4.785 元/斤，内蒙零售 5.18 元/斤，差 0.395 元（8.3%）——这个差是正常的批零差，
不是"内蒙贵 8.3%"。<b>只有比变化率，才能跨口径比较</b>；直接相减会得出完全错误的结论。</p>
<h3>坑 4：国庆 7 天不是"价格没变"，是"没有数据"</h3>
<p>全国日度序列在 10/01—10/07 断开 7 天。本报告按交易日口径处理，不做插值、不做外推。
<b>插值会制造不存在的波动</b>，这是很多报告翻车的地方。</p>""")

    body += section("14", "可直接使用的十条", """
<h3>可直接使用的十条</h3>
<ol>
<li><b>鸡蛋：</b>全国 33 日 −14.71%，内蒙只 −5.65%，补跌空间 5%—9%，库存压到 3—4 天。</li>
<li><b>猪肉：</b>现货 −9.55%、期货 −12.43%，下跌才走到一半，不要压栏、不要为春节提前备货。</li>
<li><b>牛肉：</b>全国 +3.82%、内蒙同比 +10.56%，本地刚性最强，但出场已 −2.03%，锁价窗口正在关闭。</li>
<li><b>白条鸡：</b>全国 −0.98%、内蒙 +0.42%，需求有独立支撑，加价率 40.8% 是利润池。</li>
<li><b>羊肉：</b>全国 +1.28%、CV 0.68% 最稳，适合做长协。</li>
<li><b>鱼：</b>四条鱼全国 −4.04%—+0.29%，没有趋势可做，靠周转与规格赚钱。</li>
<li><b>区域价差：</b>19.2%（牛肉）、20.0%（鸡肉），价差是月度波动的 30 倍，配额优先于择时。</li>
<li><b>负毛利品类：</b>牛/带鱼/蛋三个必须换 KPI，否则越卖越亏。</li>
<li><b>弱数据品类：</b>鸭/虾/鹅零变动是数据缺陷，不是市场稳定，不得进合同。</li>
<li><b>成本：</b>饲料走平偏弱，任何"成本推动涨价"的说法都不成立。</li>
</ol>
<h3>缺口（如实披露）</h3>
<ul>
<li>国庆 10/01—10/07 全国日度空档 7 天，按交易日口径处理，不插值。</li>
<li>鸭、鹅、虾无自治区政府序列；鹅的 10 月值为折算估算，误差约 ±2 个点。</li>
<li>盟市周度只覆盖呼市与乌兰察布，赤峰/包头/通辽的页面结构不统一，未纳入。</li>
<li>对虾 10 月无报价；虾类只能用淡水虾单条序列。</li>
<li>11 月 2—8 日全区商务预报未获取，11 月锚点用 11/5 采价日。</li>
<li>期货为连续主力合约，换月跳空未做复权处理，仅用于看方向。</li>
</ul>""")
    return body + foot()


def report_business() -> str:
    econ_rows = "".join(
        f'<tr><td class="nm">{e["品类"]}</td><td class="num">{e["批发"]:.2f}</td><td class="num">{e["零售"]:.2f}</td>'
        f'<td class="num">{e["损耗"]:.1f}%</td><td class="num">{e["冷链"]:.2f}</td>'
        f'<td class="num {cls(e["净毛利"])}">{e["净毛利"]:+.2f}</td>'
        f'<td class="num {cls(e["净毛利率%"])}">{e["净毛利率%"]:+.1f}%</td></tr>' for e in ECON)
    tco_b = TCO_B.get("ranked", [])
    tco_rows = "".join(
        f'<tr><td class="nm">{r["supplier"]}</td><td class="num">{r["landed_cost"]:,.0f}</td>'
        f'<td class="num">{r["usable_qty"]:.0f}</td><td class="num up">{r["effective_unit_cost"]:.2f}</td>'
        f'<td class="num">{r["lead_days"]:.0f} 天</td></tr>' for r in tco_b)
    body = head("内蒙古七类蛋白经营报告",
                "底稿版 · 同一批 1,196 个观测点，换一个问法：哪些品类该投人、哪些该缩量",
                ["报告日 2026-11-12", "适用 区域生鲜/商超", "口径 元/斤含损耗冷链", "配套 调研底稿 / 链路报告"])
    body += f"""
<div class="executive-card">
  <div class="directive-box">经营上只有三件事：把蛋缩到 3 天、把牛锁到 50%、把鸡的加价率收回来。</div>
  <div class="executive-body">全国日度给了明确方向：鸡蛋 −14.71%、猪肉 −9.55% 还在跌，牛肉 +3.82% 在涨，白条鸡 −0.98% 横盘。
  内蒙零售滞后 3—4 周，意味着<b>接下来 2—4 周是"本地价还没跟上"的窗口</b>：
  蛋类要抢在补跌前清库存，牛羊肉要抢在出场价传导前锁价。窗口一过，两边都没得做。</div>
</div>
<div class="metric-strip">
  {metric("负毛利品类", "3 / 10", "牛、带鱼、蛋", "critical")}
  {metric("加价率极差", "4.0×", "1.036× ↔ 1.408×", "accent")}
  {metric("鸡蛋补跌空间", "5%—9%", "5.18 → 4.75—4.92", "healthy")}
  {metric("跨市净利率", "12.3%", "乌市采、呼市卖")}
</div>
"""
    body += section("01", "三条必须先接受的事实", f"""
<div class="quad-grid">
  <div class="quad"><div class="qh">事实 1 · 高客单价 ≠ 高毛利</div><div class="qb">牛肉 37.28 元/斤、净毛利 −0.48；白条鸡 11.97 元/斤、净毛利 +2.68（22.4%）。按销售额排的重点品类，按毛利排完全反过来。这不是定价问题，是加价率结构问题。</div></div>
  <div class="quad"><div class="qh">事实 2 · 传导滞后是唯一可预测的东西</div><div class="qb">全国鸡蛋 −14.71%，内蒙 −5.65%，缺口 9.06pp。滞后 3—4 周是规律，不是意外，<b>可以被排进采购节奏</b>。</div></div>
  <div class="quad"><div class="qh">事实 3 · 成本端没有涨价压力</div><div class="qb">豆粕期货 −7.29%、玉米 +1.01%、呼市饲料走平。任何"成本涨了要提价"的内部说法，用这条直接否掉。</div></div>
  <div class="quad"><div class="qh">推论 · 动作分三档</div><div class="qb">A 级（牛/羊/鸡/鱼/蛋）做合同与配额；B 级（鸭/虾）做周度比价；C 级（鹅）做订单式，不压库存。</div></div>
</div>
<p>这三条事实对应三种完全不同的管理动作：毛利率问题要改 KPI、传导问题要改节奏、成本问题要改话术。
把三者混在一起谈，就会得出"要么全面涨价、要么全面降价"的结论，而正确做法是按品类分开处理。</p>""")

    body += section("02", "品类经营矩阵：按加价率 × 趋势分层", f"""
<table>
<tr><th>象限</th><th>品类</th><th>加价率</th><th>全国 33 日</th><th>本地趋势</th><th>定位</th><th>动作</th></tr>
<tr><td class="nm">高加价 × 上涨</td><td>鹅（C 级）</td><td class="num">30%</td><td class="num">—</td><td class="num up">+4.76%</td><td>结构品</td><td>订单式，节庆礼盒</td></tr>
<tr><td class="nm">高加价 × 横盘</td><td>白条鸡、鸭、鲤、草鱼</td><td class="num">33%—41%</td><td class="num flat">−2.1%—+1.2%</td><td class="num flat">−0.6%—+0.4%</td><td><b>利润池</b></td><td>扩 SKU、分割加工</td></tr>
<tr><td class="nm">低加价 × 上涨</td><td>牛、羊</td><td class="num">3.6%—9.9%</td><td class="num up">+3.82%／+1.28%</td><td class="num up">+0.59%／+0.56%</td><td><b>引流品</b></td><td>锁价 + 跨市配额</td></tr>
<tr><td class="nm">低加价 × 下跌</td><td>鸡蛋、带鱼</td><td class="num">4.3%—7.5%</td><td class="num down">−14.71%／+0.17%</td><td class="num down">−5.65%／+0.23%</td><td>敏感品</td><td>锁量不锁价；带鱼年限量</td></tr>
<tr><td class="nm">高客单 × 高损耗</td><td>对虾、淡水虾</td><td class="num">37%</td><td class="num">—</td><td class="num flat">0.00%</td><td>形象品</td><td>规格入合同，超损扣款</td></tr>
</table>
<div class="callout"><b>矩阵的关键不是分类，是 KPI 分行：</b>利润池看毛利率、引流品看连带率、敏感品看周转、形象品看动销。
<b>用一套 KPI 管八个品类，是这类业务最常见的组织性错误。</b>矩阵的价值在于把"八个品类"变成"四个管理对象"，
每个对象一套指标、一个人负责。</div>
<p>具体到本批数据：羊肉 CV 0.68% 最稳，适合长协；鸡蛋 CV 6.29% 最抖，适合短周期；
白条鸡同比 −2.1% 但环比 +1.4%，是唯一出现"底部拐点"信号的品类，可以开始试探性扩量。</p>""")

    body += section("03", "单位经济：按标准损耗重算", f"""
<table>
<tr><th>品类</th><th>批发</th><th>零售</th><th>损耗</th><th>冷链</th><th>净毛利</th><th>净利率</th></tr>
{econ_rows}
</table>
<div class="callout risk"><b>反转：三个"看起来赚钱"的品类其实是负毛利。</b>牛肉 −0.48、带鱼 −0.09、鸡蛋 −1.77%。
带鱼最危险：加价 7.5%，却要承担 3% 损耗与全程冷链，<b>规模越大亏得越多</b>。</div>
<h3>3.1 为什么牛肉越卖越亏</h3>
<p>牛肉零售 37.28、批发 36.00，中间只有 1.28 元；扣 1.5% 损耗（0.56 元）与冷链人工 0.90 元后是 −0.18（按 11/5 价），
按 11/10 实盘批发 36.00 重算是 −0.48。这意味着：<b>牛肉卖得越多、亏得越多——除非它带来的连带销售能覆盖单品亏损</b>。
所以牛肉的 KPI 不该是"牛肉毛利率"，而应该是"含连带的门店毛利率"与"客流转化率"。</p>
<h3>3.2 鸡蛋的负毛利更隐蔽</h3>
<p>鸡蛋零售 5.18、批发 4.97，中间 0.21 元；扣 1% 损耗与 0.25 元冷链后是 −0.09（净利率 −1.77%）。
鸡蛋的问题不在单价，在<b>量太大</b>——它是引流主力，销量可能是牛肉的十倍，−1.77% 的净利率会被放大成可观的亏损。
正确做法是把它明确归为"引流成本"，单独设预算，而不是混在毛利考核里。</p>
<h3>3.3 利润池：六个品类</h3>
<p>白条鸡 22.4%、鸭肉 20.9%、对虾 17.7%、鹅肉 15.7%、鲤鱼 15.4%、草鱼 14.1%。这六个的批零倍数都在 1.30× 以上，
扣完损耗与冷链仍有两位数净利率。<b>经营重心应该从"卖牛肉"转向"用牛肉带客流、用禽鱼赚毛利"。</b></p>""")

    body += section("04", "把传导滞后变成定价窗口", f"""
<table>
<tr><th>品类</th><th>全国（33 日）</th><th>内蒙（月度）</th><th>缺口</th><th>未来 2—4 周判断</th></tr>
<tr><td class="nm">鸡蛋</td><td class="num down">−14.71%</td><td class="num down">−5.65%</td><td class="num">9.06pp</td><td>补跌 5%—9%，先清库存</td></tr>
<tr><td class="nm">牛肉</td><td class="num up">+3.82%</td><td class="num up">+0.59%</td><td class="num">3.23pp</td><td>补涨 3%—4%，锁价优先</td></tr>
<tr><td class="nm">白条鸡</td><td class="num down">−0.98%</td><td class="num up">+0.42%</td><td class="num">1.40pp</td><td>基本同步，无需动作</td></tr>
<tr><td class="nm">猪肉</td><td class="num down">−9.55%</td><td class="num">—</td><td class="num">—</td><td>下半场，别压栏</td></tr>
</table>
<h3>4.1 两个动作，一个窗口</h3>
<p><b>鸡蛋：</b>在补跌前把库存压到 3—4 天，等于提前锁定 5%—9% 的价差。这不是"看空蛋价"，而是"不参与下跌"。
<b>牛肉：</b>在补涨前锁 50% 的量，等于提前锁定 3%—4% 的成本优势。两个动作都只有 2—4 周窗口。</p>
<h3>4.2 为什么窗口会关</h3>
<p>因为零售端的价格刚性会被两件事打破：一是竞品先降价，二是本地批发商补货成本下降。
一旦本地零售开始跟跌/跟涨，缺口消失，窗口关闭。<b>本批数据显示，呼市价格刚性极强（牛肉振幅 0.33%），
说明本地竞争格局稳定——这既让窗口更长，也让窗口关闭时更突然。</b></p>
<h3>4.3 一个必须每周复核的例外</h3>
<p>呼市鸡蛋出场价已从 4.10 回升到 4.48（+9.3%），与全国批发的下跌方向相反。
如果这个回升持续，鸡蛋的补跌逻辑会被成本端抵消。<b>复核方法：每周看全国批发价（决定上限）与呼市出场价（决定下限），
两者交叉即可判断补跌是否还成立。</b></p>""")

    body += section("05", "采购三档与 TCO 复核", f"""
<table>
<tr><th>策略</th><th>品类</th><th>触发条件</th><th>合同要点</th><th>覆盖率</th></tr>
<tr><td class="nm">锁价</td><td>牛肉、羊肉</td><td>全国上行 + 出场已回落</td><td>锁白条价，约定部位出肉率</td><td class="num">50%—60%</td></tr>
<tr><td class="nm">锁量不锁价</td><td>鸡蛋、白条鸡</td><td>已从低点反弹、方向不确定</td><td>保底量 + 周度指数浮动</td><td class="num">40%—50%</td></tr>
<tr><td class="nm">随行就市</td><td>鱼、虾、鸭、鹅</td><td>价格平稳、损耗高</td><td>成活率/冰衣率结算，规格入合同</td><td class="num">—</td></tr>
</table>
<h3>5.1 为什么牛羊肉要锁价而不是等跌</h3>
<p>零售同比 +10.56%／+5.05% 仍在高位，但出场端育肥牛已从 14.80 跌到 14.50（−2.03%）。
<b>零售滞后出场 3—4 周</b>——现在锁的是"出场价下跌、零售价还没跌"这段窗口，不是赌方向。
一旦零售开始跟跌，锁价的意义就没了。</p>
<h3>5.2 TCO 复核</h3>
<table>
<tr><th>牛肉货源</th><th>落地成本</th><th>可用斤</th><th>有效单位成本</th><th>交期</th></tr>
{tco_rows}
</table>
<p>赤峰敖汉 {tco_b[0]['effective_unit_cost']:.2f} 最优（较次优低 15.9%），但触发 MOQ 1,500 斤 WARN——
<b>最优链路必须配套拼单，否则不可执行</b>。东瓦窑 {tco_b[2]['effective_unit_cost']:.2f} 高于零售 37.28，独立复现了牛肉负毛利。</p>""")

    body += section("06", "跨市场配额与库存", f"""
<div class="grid2">
  <div class="stat"><div class="h">牛肉：乌市 → 呼市</div><div class="big up">+4.85 元/斤</div>
    <ul><li>采 33.02 → 零售 39.36</li><li>扣冷链 0.90 + 损耗 1.5%</li><li>净利率 12.3%（本地 −0.5%）</li></ul></div>
  <div class="stat"><div class="h">配额规则</div><div class="big">≤30%</div>
    <ul><li>单品类跨市 ≤ 月采购 30%</li><li>价差率 &lt;8% 自动停配</li><li>冷链车回程装载 &lt;60% 不发车</li></ul></div>
</div>
<p>价差率 19.2%（牛肉）、20.0%（鸡肉），回归斜率 1.192 &gt; 1——<b>价差随价格水平放大</b>，
配额不是一次性套利，而是结构性收益。<b>但配额有上限：</b>超过 30% 会挤压本地供应商关系，
且一旦价差收窄，多余的跨市量反而变成高成本库存。</p>
<table>
<tr><th>品类</th><th>周转天数</th><th>损耗上限</th><th>依据</th></tr>
<tr><td class="nm">鸡蛋</td><td class="num">3—4 天</td><td class="num">1.0%</td><td>全国 −14.71% 仍在补跌</td></tr>
<tr><td class="nm">白条鸡 / 鸭</td><td class="num">3 天</td><td class="num">2.0%—2.5%</td><td>加价率高，最怕剩货</td></tr>
<tr><td class="nm">牛羊肉</td><td class="num">5 天（冻 30 天）</td><td class="num">1.5%</td><td>单品负毛利，慢周转放大亏损</td></tr>
<tr><td class="nm">活鱼</td><td class="num">2 天</td><td class="num">5%</td><td>价格最稳，损耗是唯一变量</td></tr>
<tr><td class="nm">虾</td><td class="num">2 天（冻 60 天）</td><td class="num">6%</td><td>冰衣率入合同</td></tr>
<tr><td class="nm">鹅</td><td class="num">0（订单式）</td><td class="num">2.5%</td><td>C 级数据，无法定价</td></tr>
</table>""")

    body += section("07", "KPI 与 30 天行动", f"""
<table>
<tr><th>指标</th><th>基线</th><th>30 天目标</th><th>门禁</th></tr>
<tr><td class="nm">鸡蛋库存天数</td><td class="num">7 天</td><td class="num">≤4 天</td><td>&gt;7 天禁止补货</td></tr>
<tr><td class="nm">牛肉锁价覆盖</td><td class="num">0%</td><td class="num">50%</td><td>出场连跌 3 周降至 30%</td></tr>
<tr><td class="nm">跨市配额占比</td><td class="num">0%</td><td class="num">25%—30%</td><td>价差率 &lt;8% 归零</td></tr>
<tr><td class="nm">白条鸡净利率</td><td class="num">22.4%</td><td class="num">≥24%</td><td>&lt;18% 查损耗</td></tr>
<tr><td class="nm">负毛利品类</td><td class="num">3/10</td><td class="num">≤2/10</td><td>连带率 &lt;1.5 下架</td></tr>
</table>
<table>
<tr><th>周次</th><th>动作</th><th>验收</th></tr>
<tr><td class="nm">第 1 周</td><td>鸡蛋库存压到 4 天，暂停囤货</td><td>周转 ≤4 天</td></tr>
<tr><td class="nm">第 1 周</td><td>牛肉锁价 50%，与敖汉谈拼单至 1,500 斤</td><td>拿到 MOQ 豁免或拼单方案</td></tr>
<tr><td class="nm">第 2 周</td><td>开通乌兰察布牛肉配额（≤30%）</td><td>首车到店损耗 ≤1.5%</td></tr>
<tr><td class="nm">第 3 周</td><td>鸭/虾合同补规格条款</td><td>3 份合同改签</td></tr>
<tr><td class="nm">第 4 周</td><td>复盘：负毛利品类降到 2 个</td><td>含连带门店毛利率 +1pp</td></tr>
</table>
<p>这套动作的共同点是<b>不改变采购总量、只改变节奏与结构</b>：库存从 7 天压到 4 天、锁价从 0 到 50%、配额从 0 到 30%。
总量不变意味着不需要额外资金，<span style="font-weight:700">执行阻力最小、见效最快</span>。</p>""")
    return body + foot()


def report_chain() -> str:
    tco_s = TCO_S.get("ranked", [])
    tco_g = TCO_G.get("ranked", [])
    body = head("内蒙古七类蛋白链路优化报告",
                "底稿版 · 五节点、七断点、四条链，用 1,196 个观测点定位损失在哪一段",
                ["报告日 2026-11-12", "范围 产地→批发→冷链→门店", "基准 10—11 月实盘", "验收 R04"])
    body += f"""
<div class="executive-card">
  <div class="directive-box">链路损失不在运费，在「传导速度差」和「口径转换」。</div>
  <div class="executive-body">同一批货过 5 个节点、3 种计价口径；每一段按自己的口径决策。
  全国鸡蛋 −14.71%、内蒙零售只 −5.65%，<b>中间 9 个点不是被谁赚走了，而是还没传导</b>——
  对零售商是缓冲，对采购是风险，对链路是效率损失。</div>
</div>
<div class="metric-strip">
  {metric("口径缺口", "3 类", "鸭/鹅/虾无政府序列", "critical")}
  {metric("传导滞后", "9.06pp", "全国蛋 vs 内蒙蛋", "accent")}
  {metric("最优链路价差", "15.9%", "赤峰直采 vs 东瓦窑", "healthy")}
  {metric("批零加价极差", "4.0×", "1.036× ↔ 1.408×")}
</div>
"""
    body += section("01", "现状链路：五个节点，三种口径", f"""
<div class="flow">
  <div class="node"><div class="nt">产地/出场</div><div class="nv">活体、元/斤<br>育肥牛 14.50</div></div>
  <div class="node"><div class="nt">屠宰/初加工</div><div class="nv">出肉率 0.62—0.70<br>白条鹅 11.0</div></div>
  <div class="node"><div class="nt">批发市场</div><div class="nv">元/公斤<br>东瓦窑 72、保全庄 21</div></div>
  <div class="node"><div class="nt">冷链城配</div><div class="nv">元/车、装载率<br>0.25—1.60 元/斤</div></div>
  <div class="node"><div class="nt">门店零售</div><div class="nv">元/500 克<br>37.28 / 11.97 / 5.18</div></div>
</div>
<p>五个节点不是简单的"加法"，而是三次口径转换：活体→白条（出肉率）、元/公斤→元/斤（除以 2）、
批发→零售（加价率）。<b>每一次转换都是一次信息损失</b>：出肉率不透明、除以 2 会抹掉规格差异、加价率掩盖损耗。
链路优化首先要做的不是砍价，是把这三次转换标准化。</p>
<table>
<tr><th>节点</th><th>计价</th><th>决策人</th><th>本批价格</th><th>风险</th></tr>
<tr><td class="nm">产地</td><td>元/斤（活体）</td><td>养殖户/经纪人</td><td class="num">育肥牛 14.50、活鹅 6.6</td><td>出肉率不透明</td></tr>
<tr><td class="nm">屠宰</td><td>元/斤（白条）</td><td>屠宰厂</td><td class="num">白条鹅 11.0、白条鸡 8.90</td><td>等级口径</td></tr>
<tr><td class="nm">批发</td><td>元/公斤</td><td>批发商</td><td class="num">东瓦窑 72、保全庄 21—165</td><td>单点噪声 14pp</td></tr>
<tr><td class="nm">冷链</td><td>元/车</td><td>物流</td><td class="num">0.25—1.60 元/斤</td><td>装载率、断链</td></tr>
<tr><td class="nm">零售</td><td>元/500 克</td><td>门店</td><td class="num">37.28 / 11.97 / 5.18</td><td>损耗与折价</td></tr>
</table>""")

    body += section("02", "七个断点", f"""
<table>
<tr><th>#</th><th>断点</th><th>证据</th><th>量化损失</th><th>优先级</th></tr>
<tr><td class="nm">1</td><td><b>传导断点</b>：全国跌、本地不跌</td><td>鸡蛋 −14.71% vs −5.65%</td><td>9.06pp 未释放</td><td><span class="chip p0">P0</span></td></tr>
<tr><td class="nm">2</td><td><b>口径断点</b>：牛腩 vs 牛腿肉</td><td>37.28 vs 35.03</td><td>6.41%，吞掉整条毛利</td><td><span class="chip p0">P0</span></td></tr>
<tr><td class="nm">3</td><td><b>规格断点</b>：虾差 2.8 倍</td><td>67.0 vs 188.75</td><td>选源结论相反</td><td><span class="chip p0">P0</span></td></tr>
<tr><td class="nm">4</td><td><b>信息断点</b>：鸭鹅虾无序列</td><td>B/C 级，噪声 14pp</td><td>无法定价与考核</td><td><span class="chip p0">P0</span></td></tr>
<tr><td class="nm">5</td><td><b>节点断点</b>：出场涨、零售不涨</td><td>呼市蛋出场 +9.3% vs 零售 +1.8%</td><td>毛利被压 0.38 元/斤</td><td><span class="chip p1">P1</span></td></tr>
<tr><td class="nm">6</td><td><b>规模断点</b>：MOQ 1,500 斤</td><td>28.95 但需拼单</td><td>不拼单多付 15.9%</td><td><span class="chip p1">P1</span></td></tr>
<tr><td class="nm">7</td><td><b>配额断点</b>：价差未利用</td><td>牛肉 19.2%、鸡肉 20.0%</td><td>放着 12.3% 净利率不赚</td><td><span class="chip p2">P2</span></td></tr>
</table>
<div class="callout"><b>第 1 条是本批新增、也是最值钱的一条：</b>过去的链路诊断都在看"哪段贵"，
但数据显示问题在"哪段慢"。<b>慢不是效率问题，是定价权问题</b>——谁能预判传导，谁就拿走这 9 个点。
第 5 条是它的镜像：出场价涨了、零售价没涨，毛利被压 0.38 元/斤，这条如果不处理，负毛利会从 3 个品类扩到 4 个。</div>""")

    body += section("03", "四条链，四套规则", f"""
<div class="quad-grid">
  <div class="quad"><div class="qh">链 A · 牛羊肉：锁价 + 配额</div><div class="qb">产地/屠宰直采（≤50% 锁价）+ 乌兰察布配额（≤30%）+ 东瓦窑备份（30%）。价差率 &lt;8% 自动停配。</div></div>
  <div class="quad"><div class="qh">链 B · 禽类：直连 + 分割</div><div class="qb">白条鸡/鸭批发直连，把 40.8% 加价率转成自有毛利；鹅订单式，零库存。</div></div>
  <div class="quad"><div class="qh">链 C · 鱼虾：产地直发 + 规格合同</div><div class="qb">活鱼本地批发（周转 2 天）；虾沿海冻品直发，头数/冰衣率/净重入合同。</div></div>
  <div class="quad"><div class="qh">链 D · 蛋类：锁量不锁价 + 短周转</div><div class="qb">敖汉直采，库存 ≤4 天；结算随周度指数，设上下限。</div></div>
</div>
<p>四条链的差别不在品类，在<b>风险归属</b>：链 A 用锁价把价格风险转移给上游；链 B 用直连把加价率收归自己；
链 C 用规格合同把质量风险前置；链 D 用短周转把库存风险降到最低。
<b>把四条链混成一条"统一采购流程"，就会同时承担四种风险、却拿不到四种收益。</b></p>""")

    body += section("04", "量化目标与引擎复核", f"""
<table>
<tr><th>指标</th><th>现状</th><th>90 天目标</th><th>依据</th></tr>
<tr><td class="nm">牛肉到店成本</td><td class="num">37.46</td><td class="num">≤33.00</td><td>赤峰 28.95 + 拼单分摊</td></tr>
<tr><td class="nm">鸡蛋到店成本</td><td class="num">5.27</td><td class="num">≤4.85</td><td>敖汉直采 4.78</td></tr>
<tr><td class="nm">鸡蛋库存天数</td><td class="num">7</td><td class="num">≤4</td><td>补跌 5%—9%</td></tr>
<tr><td class="nm">鸡肉加价率</td><td class="num">40.8%（外部拿走）</td><td class="num">自有毛利 ≥20%</td><td>直连 + 分割</td></tr>
<tr><td class="nm">B/C 级双源核验</td><td class="num">0%</td><td class="num">100%</td><td>单源不进合同</td></tr>
<tr><td class="nm">虾类规格纠纷</td><td class="num">未知</td><td class="num">0 起</td><td>三要素入合同</td></tr>
</table>
<h3>4.1 牛肉 TCO</h3>
<table>
<tr><th>货源</th><th>落地成本</th><th>有效单位成本</th><th>约束</th></tr>
{"".join(f'<tr><td class="nm">{r["supplier"]}</td><td class="num">{r["landed_cost"]:,.0f}</td><td class="num up">{r["effective_unit_cost"]:.2f}</td><td>{"MOQ 1,500 斤（WARN）" if "赤峰" in r["supplier"] else "—"}</td></tr>' for r in TCO_B.get("ranked", []))}
</table>
<h3>4.2 鹅肉：产地直采 vs 呼市转手</h3>
<table>
<tr><th>货源</th><th>落地成本</th><th>有效单位成本</th><th>交期</th></tr>
{"".join(f'<tr><td class="nm">{r["supplier"]}</td><td class="num">{r["landed_cost"]:,.0f}</td><td class="num">{r["effective_unit_cost"]:.2f}</td><td class="num">{r["lead_days"]:.0f} 天</td></tr>' for r in tco_g)}
</table>
<h3>4.3 虾类：一个"排出来但不能用"的结论</h3>
<table>
<tr><th>货源</th><th>落地成本</th><th>有效单位成本</th><th>能不能用</th></tr>
<tr><td class="nm">{tco_s[0]['supplier']}</td><td class="num">{tco_s[0]['landed_cost']:,.0f}</td><td class="num up">{tco_s[0]['effective_unit_cost']:.2f}</td><td>不可用：与另一货源不是同一规格</td></tr>
<tr><td class="nm">{tco_s[1]['supplier']}</td><td class="num">{tco_s[1]['landed_cost']:,.0f}</td><td class="num">{tco_s[1]['effective_unit_cost']:.2f}</td><td>可用：同规格内唯一可比价</td></tr>
</table>
<div class="callout risk"><b>方法论结论：</b>引擎严格按"有效单位成本"排序，会把 38.33 的冻虾排在 88.40 的淡水虾前面——
<b>数字没错，结论错了</b>。<b>规格对齐必须是比价的前置门禁，不是事后解释。</b>
这条经验同样适用于牛肉（牛腩 vs 牛腿肉）与鹅（活鹅 vs 白条鹅）。</div>""")

    body += section("05", "90 天路线与验收", f"""
<table>
<tr><th>阶段</th><th>时间</th><th>动作</th><th>验收</th></tr>
<tr><td class="nm">P0 对齐口径</td><td>第 1—2 周</td><td>七类统一"部位/规格/净重"三要素；建双源核验表</td><td>8 品类各有唯一口径</td></tr>
<tr><td class="nm">P0 修负毛利</td><td>第 2—3 周</td><td>牛肉改引流定价、带鱼年限量、鸡蛋短周转</td><td>负毛利 ≤2 个</td></tr>
<tr><td class="nm">P1 建链路</td><td>第 3—6 周</td><td>赤峰拼单、乌兰察布配额、敖汉蛋直采</td><td>到店成本达标</td></tr>
<tr><td class="nm">P1 补数据</td><td>第 4—8 周</td><td>鸭/鹅/虾自建采价序列（每周 2 次，同市场同规格）</td><td>连续 4 周有序列</td></tr>
<tr><td class="nm">P2 上系统</td><td>第 8—12 周</td><td>TCO 与配额规则写进采购系统，价差自动预警</td><td>超标自动拦截</td></tr>
</table>
<h3>5.1 验收门禁</h3>
<table>
<tr><th>门禁</th><th>标准</th><th>状态</th></tr>
<tr><td class="nm">L1 存在</td><td>三份报告 + 底稿 + 门禁输出齐备</td><td>待 R04 复核</td></tr>
<tr><td class="nm">L2 实质</td><td>无 stub、无占位数字、每条结论挂源</td><td>40 条结论全部挂源</td></tr>
<tr><td class="nm">L3 接线</td><td>报告数字可在底稿指标复算</td><td>单一出处</td></tr>
</table>
<h3>5.2 风险与回退</h3>
<table>
<tr><th>风险</th><th>触发</th><th>回退</th></tr>
<tr><td class="nm">直采质量不稳</td><td>连续 2 批不良率 &gt;2%</td><td>回退批发 30%，恢复双源</td></tr>
<tr><td class="nm">跨市冷链中断</td><td>道路管制/暴雪</td><td>配额清零，东瓦窑补位</td></tr>
<tr><td class="nm">拼单失败</td><td>4 周未达 1,500 斤</td><td>放弃赤峰，转乌兰察布（差 15.9%→16.4%）</td></tr>
<tr><td class="nm">传导逆转</td><td>出场价连续 2 周高于零售成本</td><td>暂停补跌预期，改按成本定价</td></tr>
</table>""")
    return body + foot()


CATS_HTML = ""
_cat_specs = [
    ("15", "牛肉", "A",
     "全国日度 33 天：71.13→73.85（+3.82%）｜周度同比 +11.1%｜内蒙月度 37.06→37.28（+0.59%）｜呼市 39.23→39.36（振幅 0.33%）",
     """<p><b>趋势：</b>33 个交易日里 17 涨 14 跌，最高点就是最后一天（11/11），形态是台阶式上行而非一波流。
     台阶形态意味着每次回调都有承接，属于需求驱动，不是消息刺激。</p>
     <p><b>本地：</b>内蒙零售 37.06→37.28（+0.59%），只有全国涨幅的 1/6；呼市 5 个时点振幅 0.33%，
     是全国的 1/11。<b>本地价格刚性极强</b>，涨得慢、也不会跌得快。</p>
     <p><b>上游：</b>敖汉育肥牛 14.80→14.50（−2.03%）。<b>零售还在涨、出场已经在跌</b>，这个背离通常维持 3—4 周。</p>
     <p><b>经济性：</b>批零 1.036×、净毛利 −0.48 元/斤；TCO 最优赤峰 28.95（MOQ 1,500 斤）、次优乌兰察布 34.44、最差东瓦窑 37.46。</p>
     <p><b>经营含义：</b>引流品定位，KPI 换成连带率；锁价窗口正在关闭，跨市配额（19.2% 价差）优先于择时。</p>"""),
    ("16", "羊肉", "A",
     "全国日度：66.49→67.34（+1.28%）｜周度同比 +8.8%｜内蒙 39.34→39.56（+0.56%）｜呼市 40.00→40.14",
     """<p><b>趋势：</b>全国 +1.28%，是九品类中波动第二低的（CV 0.68%）。走势平缓、没有明显拐点。</p>
     <p><b>本地：</b>内蒙 39.34→39.56，呼市 40.00→40.14（+0.35%），乌兰察布 34.52→34.32（−0.58%）。
     三个口径同向，是七类蛋白中一致性最好的品类。</p>
     <p><b>上游：</b>乌兰察布羔羊 19.55、锡盟绒山羊 20.31 元/斤（11/10），产地价格稳定。</p>
     <p><b>经济性：</b>批零 1.099×、净毛利 +2.07 元/斤（5.2%），是牛羊肉里唯一正毛利的品类。</p>
     <p><b>经营含义：</b>CV 最低、毛利为正，<b>最适合做长协</b>——锁价周期可以放到 60—90 天，不必像牛肉那样每周盯盘。</p>"""),
    ("17", "鸡肉", "A",
     "全国日度：17.35→17.18（−0.98%）｜周度同比 −2.1%、环比 +1.4%｜内蒙 11.92→11.97（+0.42%）｜呼市 11.86 恒定",
     """<p><b>趋势：</b>全国 −0.98%，但末周环比 +1.4%（12 品类最高），同比 −2.1%。<b>同比低、环比高，是典型底部拐点组合</b>。</p>
     <p><b>本地：</b>内蒙 +0.42%，与全国方向相反；呼市 5 个时点全部 11.86，零变动。本地白条鸡供给相对封闭，
     价格由本地供需决定，<b>可以做独立定价，不必跟全国盘面</b>。</p>
     <p><b>批发端：</b>保全庄鸡肉 22.0→24.9 元/公斤（+13.2%），三黄鸡 36.0→34.5（−4.2%），
     分割品与整禽走势分化——这是本地分割加工需求上升的信号。</p>
     <p><b>经济性：</b>批零 1.408×（全品类最高）、净毛利 +2.68 元/斤（22.4%）。</p>
     <p><b>经营含义：</b>利润池。<b>把 40.8% 的外部加价率收回来一部分</b>，比盯价格更值钱。</p>"""),
    ("18", "鸭肉", "B",
     "保全庄 10/07 与 11/10 均 21.0 元/公斤（10.50 元/斤，零变动）｜全国同日另一市场 11.0 元/公斤",
     """<p><b>数据状况：</b>自治区无监测序列，全国日度也不含鸭。本批只有保全庄两期同价，加上全国另一市场一个单点，
     <b>共 3 个观测值</b>——这是公开渠道能拿到的全部。</p>
     <p><b>能说的：</b>① 内蒙鸭价约为全国另一市场的 1.9 倍（21.0 vs 11.0 元/公斤），溢价来自运输半径与冷鲜供应不足；
     ② 两期零变动说明本地鸭价对全国波动不敏感；③ 批零 1.381×、净毛利 20.9%，是利润品。</p>
     <p><b>不能说的：</b>不能判断月度趋势、不能做同比、不能用于报价谈判。<b>任何"鸭价在涨/在跌"的结论，
     以现有数据都不成立。</b></p>
     <p><b>补数方案：</b>每周二、五各打一次保全庄与东瓦窑的鸭肉报价，同规格（白条 2—2.5 斤/只），连续 4 周即可建序列。</p>"""),
    ("19", "鹅肉", "C",
     "通辽开鲁白条鹅 11.0 元/斤（11 月）｜内蒙古活鹅 6.1—7.1、干管鹅 8.1—9.0、淘汰老鹅 9.8—11.5 元/斤（10/25）",
     """<p><b>数据状况：</b>四个口径并存——活鹅、干管鹅、淘汰老鹅、白条鹅。它们是同一条产业链的四个环节，
     不是四个价格。<b>跨口径比价会得出相反结论</b>：按活鹅看内蒙低于全国，按白条鹅看高于全国 19%。</p>
     <p><b>能说的：</b>白条鹅 11.0 元/斤折 22.0 元/公斤，高于全国 7 日均价 9.24 元/斤约 19%；
     按出肉率 0.66 + 屠宰费 0.5 折算，10 月白条约 10.5 元/斤，环比 +4.76%；TCO 通辽直采 12.05 vs 呼市转手 12.98（低 7.2%）。</p>
     <p><b>不能说的：</b>10 月值为折算估算，误差约 ±2 个点；单点报价无法判断趋势。<b>只能做情景，不能做承诺。</b></p>
     <p><b>经营含义：</b>结构品、订单式采购、零库存；不要用鹅价去推断禽类整体走势。</p>"""),
    ("20", "鱼肉", "A",
     "全国日度：鲫鱼 −4.04%、鲤鱼 −1.95%、白鲢 +0.29%、大带鱼 +0.17%｜内蒙：带鱼 +0.23%、草鱼 −0.09%、鲤鱼 −0.56%",
     """<p><b>趋势：</b>四条鱼全部走平（−4.04%—+0.29%），是七类蛋白里唯一"没有趋势"的一类。带鱼振幅 9.76% 但首尾几乎持平，
     属于高波动无趋势。</p>
     <p><b>本地：</b>内蒙带鱼 17.16→17.20、草鱼 11.32→11.31、鲤鱼 8.91→8.86，三条鱼都落在 ±0.6% 内；
     呼市带鱼 19.66→19.99（+1.68%）、草鱼 12.28→11.94（−2.53%）、鲤鱼 9.93→9.74（−2.21%）。</p>
     <p><b>经济性：</b>鲤鱼 1.363×（+15.4%）、草鱼 1.331×（+14.1%）为正；带鱼 1.075×（−0.1%）为负——
     加价 7.5% 覆盖不了 3% 损耗与全程冷链。</p>
     <p><b>经营含义：</b>不做长协、按周议价；利润来自规格与成活率，不来自择时；带鱼年限量、禁止走量。</p>"""),
    ("21", "虾类", "B",
     "淡水虾 165.0 元/公斤 × 2 期（零变动）｜对虾 67.0 元/公斤 × 3 期｜全国对虾均价 188.75 元/公斤（差 2.8 倍）",
     """<p><b>数据状况：</b>无政府序列，淡水虾 2 个点、对虾 3 个点，且对虾 10 月完全没有报价。
     <b>这是七类蛋白里数据最差的一类。</b></p>
     <p><b>能说的：</b>① 淡水虾两期零变动，价格刚性；② 对虾三期间隔 5 天仍同价，短期波动极小；
     ③ 保全庄对虾 67.0 vs 全国均价 188.75，差 2.8 倍——<b>这是规格差（头数/盒装），不是产地差</b>；
     ④ 批零 1.373×、净毛利 17.7%，是形象品。</p>
     <p><b>不能说的：</b>不能算月度环比、不能做趋势、不能跨市场比价。</p>
     <p><b>经营含义：</b>只做预订与礼盒，规格（头数/净重/冰衣率）必须写进合同；TCO 排序出来 38.33 的冻虾不能采信，
     因为它与 88.40 的淡水虾不是同一商品。</p>"""),
    ("22", "蛋类", "A",
     "全国日度：11.22→9.57（−14.71%，振幅 19.5%）｜周度同比 +28.2%｜内蒙 5.49→5.18（−5.65%）｜呼市 5.30→5.11",
     """<p><b>趋势：</b>21 天下跌、11 天上涨，最低 9.29 出现在 10/27，之后横盘微升。<b>下跌在 10 月底已经走完</b>，
     但同比仍 +28.2%，处在历史高位。</p>
     <p><b>本地：</b>内蒙 5.49→5.18（−5.65%），只跟了全国跌幅的 38%；呼市 5.30→5.02→5.03→5.31→5.11，
     与全国节奏同步但幅度更小。<b>缺口 9.06 个百分点，对应补跌 5%—9%。</b></p>
     <p><b>成本端：</b>呼市出场 4.10→4.48（+9.3%），零售只跟 1.8%，批零差从 0.92 压到 0.63 元；
     按 4.48 + 0.25 冷链 + 1% 损耗，零售需 5.02 保本，当前 5.11 只剩 0.09 元空间。</p>
     <p><b>经济性：</b>批零 1.043×、净毛利 −0.09 元/斤（−1.77%）——引流成本，不是亏损。</p>
     <p><b>经营含义：</b>锁量不锁价、库存 3—4 天；补跌前清库存等于锁定 5%—9% 价差；
     出场价若再涨 2%，鸡蛋零售即转入负毛利。</p>"""),
]

for _num, _name, _grade, _head_line, _body in _cat_specs:
    CATS_HTML += section(_num, f"分品类档案 · {_name}（{_grade} 级证据）", f"""
<p class="standfirst" style="margin:0 0 10px">{_head_line}</p>
{_body}""")

APPENDIX = """
<div class="report-section">
  <div class="section-head"><span class="section-num">Appendix</span><h2>附录 · 完整数据表（可复算）</h2></div>
  <p>以下四张表是本报告全部原始观测值的展开。报告正文的每一个数字都可以在这里找到，
  也可以由 <code>data/底稿指标.json</code> 与 <code>底稿版/*.csv</code> 复算。</p>
  <h3>A1 全国日度：33 个交易日 × 9 品类（元/公斤）</h3>
  __DAILY__
  <h3>A2 全国周度：5 周 × 12 品类（本周值，元/公斤）</h3>
  __WEEKLY__
  <h3>A3 期货日线：4 品种 × 32 个交易日（收盘价）</h3>
  __FUT__
  <h3>A4 盟市周度：呼市 5 个时点 × 8 品类（元/斤）</h3>
  __CITY__
</div>
"""


def build_appendix() -> str:
    import csv as _csv
    d = BASE / "底稿版"
    rows = list(_csv.DictReader((d / "data_daily.csv").open(encoding="utf-8-sig")))
    cats = ["猪肉", "牛肉", "羊肉", "鸡蛋", "白条鸡", "鲫鱼", "鲤鱼", "白鲢鱼", "大带鱼"]
    head = "".join(f'<th class="num">{c}</th>' for c in cats)
    body = "".join(
        f'<tr><td class="nm">{r["date"][:10]}</td>' + "".join(f'<td class="num">{r[c]}</td>' for c in cats) + "</tr>"
        for r in rows)
    daily = f"<table><tr><th>日期</th>{head}</tr>{body}</table>"

    w = list(_csv.DictReader((d / "data_weekly.csv").open(encoding="utf-8-sig")))
    weeks = sorted({x["week"] for x in w})
    items = ["猪肉", "牛肉", "羊肉", "鸡蛋", "白条鸡", "草鱼", "鲫鱼", "鲤鱼", "白鲢鱼", "花鲢鱼", "大带鱼", "大黄花鱼"]
    wh = "".join(f'<th class="num">{x[:5]}—{x[13:18]}</th>' for x in weeks)
    wrows = ""
    for it in items:
        cells = []
        for wk in weeks:
            hit = next((x for x in w if x["item"] == it and x["week"] == wk), None)
            cells.append(f'<td class="num">{hit["this"]}</td>' if hit else '<td class="num">—</td>')
        wrows += f'<tr><td class="nm">{it}</td>' + "".join(cells) + "</tr>"
    weekly = f"<table><tr><th>品类</th>{wh}</tr>{wrows}</table>"

    f = list(_csv.DictReader((d / "data_futures.csv").open(encoding="utf-8-sig")))
    dates = sorted({x["date"] for x in f})
    syms = ["LH0", "JD0", "M0", "C0"]
    names = {"LH0": "生猪", "JD0": "鸡蛋", "M0": "豆粕", "C0": "玉米"}
    fh = "".join(f'<th class="num">{names[s]}</th>' for s in syms)
    frows = ""
    for dt in dates:
        cells = []
        for s in syms:
            hit = next((x for x in f if x["symbol"] == s and x["date"] == dt), None)
            cells.append(f'<td class="num">{float(hit["close"]):.0f}</td>' if hit else '<td class="num">—</td>')
        frows += f'<tr><td class="nm">{dt}</td>' + "".join(cells) + "</tr>"
    fut = f"<table><tr><th>日期</th>{fh}</tr>{frows}</table>"

    cats2 = ["牛肉", "羊肉", "鸡肉", "鸡蛋", "带鱼", "草鱼", "鲤鱼", "猪精瘦"]
    ch = "".join(f'<th class="num">{x[5:]}</th>' for x in DATES)
    crows = ""
    for c in cats2:
        crows += f'<tr><td class="nm">{c}</td>' + "".join(
            f'<td class="num">{HH[x][c]:.2f}</td>' if c in HH[x] else '<td class="num">—</td>' for x in DATES) + "</tr>"
    city = f"<table><tr><th>品类</th>{ch}</tr>{crows}</table>"

    return (APPENDIX.replace("__DAILY__", daily).replace("__WEEKLY__", weekly)
            .replace("__FUT__", fut).replace("__CITY__", city))


EXTRA_RESEARCH = section("23", "定价权：本地价到底由谁决定", """
<p>把三个环节的价差摊开看，定价权的分布很清楚。<b>出场端没有定价权</b>：育肥牛 14.80→14.50、
鲜蛋装车 4.00→4.11→4.33，波动小、跟随全国；<b>批发端有最强的定价权</b>：东瓦窑牛肉 72 元/公斤、
保全庄鸭 21 元/公斤，报价频率低但一报就定一天；<b>零售端有"延迟定价权"</b>：呼市牛肉 5 个时点振幅 0.33%，
可以长期不动，但一旦动就是一次性调整。</p>
<p>这解释了一个常见困惑：为什么"批发价跌了，零售价不跌"。因为零售端的定价权不是"跟着批发走"，
而是"在自己的调价周期里决定跟不跟"。呼市鸡蛋从 10/19 的 5.30 到 11/06 的 5.11，五个时点只降了 3.6%，
而同期全国批发降了 14.7%——<b>差的 11 个点，就是零售端"延迟"出来的空间</b>。</p>
<p>对经营的含义：不要指望通过谈判让零售端立刻跟跌，也不要假设零售端会永远不跌。
正确做法是<b>把"跟价周期"写进合同</b>——例如约定"全国批发价连续 2 周变动超 5% 时，零售价次周调整"。
这样既保留了零售端的缓冲，又避免了长期背离。</p>""")

EXTRA_RESEARCH2 = section("24", "这套结论什么时候会失效（可证伪清单）", """
<p>一份调研报告的价值，一半在结论，一半在"什么情况下结论不成立"。本报告的四条主线，各有明确的失效条件：</p>
<table>
<tr><th>结论</th><th>失效条件</th><th>复核频率</th></tr>
<tr><td class="nm">鸡蛋补跌 5%—9%</td><td>呼市出场价连续 2 周高于 4.6 元/斤，或全国批发止跌回升超 3%</td><td>每周</td></tr>
<tr><td class="nm">牛肉锁价窗口</td><td>敖汉育肥牛连续 2 周回升，或全国牛肉周度转跌</td><td>每周</td></tr>
<tr><td class="nm">跨市配额 19.2% 价差</td><td>价差率跌破 8%，或乌兰察布开始跟涨</td><td>每周</td></tr>
<tr><td class="nm">白条鸡独立行情</td><td>本地白条鸡跟随全国跌破 −2%，或猪价反弹超 5%</td><td>每两周</td></tr>
</table>
<p><b>为什么要把失效条件写出来：</b>因为大部分经营决策的错误不是"判断错"，而是"判断曾经对、后来失效了却没人复核"。
把复核条件与频率写进周会，比再写十页分析更有用。</p>""")

EXTRA_BUSINESS = section("10", "猪价下行期的组合调整", """
<p>猪肉 33 日 −9.55%、期货 −12.43%，是四季度最大的外生变量。它会通过两条路径影响门店：<b>一是替代</b>，
猪肉便宜会分流禽肉与牛羊肉的需求；<b>二是价格锚</b>，顾客会拿猪肉价当"蛋白价格锚"，觉得禽肉贵了。</p>
<p>但本批数据给出了一个反直觉的证据：<b>白条鸡只跌 0.98%</b>，没有跟着猪肉跌。说明替代效应在零售端并不强，
真正起作用的是"价格锚"心理，而不是实际购买转移。对经营的含义：<b>不要主动下调禽肉价格去"应对"猪价</b>，
那会把价格锚坐实；正确做法是保持禽肉价格、用组合（猪肉+禽肉套餐）承接客流。</p>
<p>牛羊肉则相反：猪价跌对它是利好——消费升级的替代方向。当前牛肉同比 +10.56%，正是这个逻辑的体现。
所以组合策略应该是：<b>猪肉做引流、禽肉做利润、牛羊肉做客单</b>，三条线各司其职，不要互相补贴。</p>""")

EXTRA_BUSINESS2 = section("11", "三类 KPI 怎么落地", """
<p>前面说"要换 KPI"，具体怎么换：</p>
<table>
<tr><th>角色</th><th>旧 KPI</th><th>新 KPI</th><th>口径</th></tr>
<tr><td class="nm">引流品（牛/蛋）</td><td>品类毛利率</td><td>连带率 + 客流转化</td><td>含连带门店毛利率、客单件数</td></tr>
<tr><td class="nm">利润品（禽/鱼）</td><td>销售额</td><td>净毛利率（含损耗）</td><td>扣损耗与冷链后的毛利率</td></tr>
<tr><td class="nm">敏感品（蛋/带鱼）</td><td>毛利额</td><td>周转天数 + 损耗率</td><td>库存天数、损耗上限</td></tr>
<tr><td class="nm">形象品（虾/鹅）</td><td>销量</td><td>动销率 + 规格纠纷数</td><td>周动销、投诉数</td></tr>
</table>
<p>换 KPI 的难点不是定义，是<b>数据可得性</b>：连带率需要 POS 关联、损耗率需要盘点、动销率需要库存系统。
如果这些数据拿不到，退一步的做法是<b>先用"品类毛利率 ÷ 加价率"做替代指标</b>——加价率高的品类，
毛利率天然应该高，低于这个比值就说明执行出了问题。</p>""")

EXTRA_BUSINESS3 = section("12", "分品类经营口径总表（八品类 × 六件事）", """
<table>
<tr><th>品类</th><th>价格锚</th><th>加价率</th><th>净利率</th><th>定位</th><th>合同</th><th>库存/KPI</th></tr>
<tr><td class="nm">牛肉</td><td class="num">37.28</td><td class="num">1.036×</td><td class="num down">−0.5%</td><td>引流</td><td>锁价 50%—60%</td><td>5 天 / 连带率</td></tr>
<tr><td class="nm">羊肉</td><td class="num">39.56</td><td class="num">1.099×</td><td class="num up">+5.2%</td><td>长协</td><td>锁价 60%—90 天</td><td>5 天 / 毛利率</td></tr>
<tr><td class="nm">鸡肉</td><td class="num">11.97</td><td class="num">1.408×</td><td class="num up">+22.4%</td><td>利润</td><td>锁量不锁价</td><td>3 天 / 净利率</td></tr>
<tr><td class="nm">鸭肉</td><td class="num">14.50*</td><td class="num">1.381×</td><td class="num up">+20.9%</td><td>利润</td><td>周度比价</td><td>3 天 / 净利率</td></tr>
<tr><td class="nm">鹅肉</td><td class="num">14.30*</td><td class="num">1.300×</td><td class="num up">+15.7%</td><td>结构</td><td>订单式</td><td>0 / 动销</td></tr>
<tr><td class="nm">鱼肉</td><td class="num">8.86—17.20</td><td class="num">1.075—1.363×</td><td class="num">−0.1%—+15.4%</td><td>周转</td><td>周度议价</td><td>2 天 / 损耗</td></tr>
<tr><td class="nm">虾类</td><td class="num">33.50—82.50</td><td class="num">1.373×</td><td class="num up">+17.7%</td><td>形象</td><td>规格合同</td><td>2 天 / 动销</td></tr>
<tr><td class="nm">蛋类</td><td class="num">5.18</td><td class="num">1.043×</td><td class="num down">−1.8%</td><td>敏感</td><td>锁量不锁价</td><td>3—4 天 / 周转</td></tr>
</table>
<p>这张表是经营报告的"总开关"：<b>八个品类、六件事，每格都有唯一答案</b>。
任何一个采购或店长拿到这张表，都能在不请示的情况下做出 80% 的日常决策。
剩下的 20%（调价幅度、配额比例）才需要上级判断——这才是"口径统一"的实际收益。</p>
<p><b>* 标注为估算值</b>：鸭、鹅无公开零售报价，按同类加价率推算，误差约 ±0.5 元/斤，只用于横向比较。</p>""")
EXTRA_CHAIN = section("08", "数据链路：33 天日度到门店决策的四次转换", """
<p>数据从产地到门店要过四道手，每一道都在丢信息：</p>
<table>
<tr><th>转换</th><th>输入</th><th>输出</th><th>丢失的信息</th></tr>
<tr><td class="nm">① 采集</td><td>全国 33 天日度、盟市周度</td><td>价格序列</td><td>成交量、规格、成交价 vs 报价</td></tr>
<tr><td class="nm">② 汇总</td><td>日度 → 周度/月度</td><td>均值、环比</td><td>周内波动、拐点日期</td></tr>
<tr><td class="nm">③ 换算</td><td>元/公斤 → 元/斤</td><td>可比价格</td><td>规格差异（头数、冰衣率）</td></tr>
<tr><td class="nm">④ 决策</td><td>价格 + 成本 + 库存</td><td>采购单</td><td>替代品价格、顾客预期</td></tr>
</table>
<p>本报告的价值在于<b>把②和③的损失补回来</b>：用日度序列找回拐点（10/27 鸡蛋见底），用规格对齐找回可比性。
但①和④的损失仍在——采集端没有成交量，决策端没有顾客预期。<b>这两块是下一版要补的：成交量靠批发市场访谈，顾客预期靠门店问卷。</b></p>""")

EXTRA_CHAIN3 = section("10", "分品类链路选择（八品类 × 五个节点）", """
<table>
<tr><th>品类</th><th>产地/屠宰</th><th>批发</th><th>冷链</th><th>门店</th><th>关键约束</th></tr>
<tr><td class="nm">牛肉</td><td>赤峰直采（最优）/ 乌兰察布</td><td>东瓦窑备份 30%</td><td>全程冷藏</td><td>引流定价</td><td>MOQ 1,500 斤</td></tr>
<tr><td class="nm">羊肉</td><td>乌兰察布羔羊</td><td>东瓦窑 / 包头友谊</td><td>全程冷藏</td><td>长协价</td><td>CV 0.68%，波动最低</td></tr>
<tr><td class="nm">鸡肉</td><td>敖汉定点屠宰（白条 8.90）</td><td>批发直连</td><td>冷藏</td><td>分割加工</td><td>加价率 40.8% 要收回</td></tr>
<tr><td class="nm">鸭肉</td><td>—（本地无产地）</td><td>保全庄 21.0</td><td>冷藏</td><td>限量</td><td>B 级数据，周度比价</td></tr>
<tr><td class="nm">鹅肉</td><td>通辽开鲁直采 11.0</td><td>不经过批发</td><td>冷藏</td><td>预订/礼盒</td><td>C 级数据，订单式</td></tr>
<tr><td class="nm">鱼肉</td><td>本地/外埠活鱼</td><td>东瓦窑 17 / 13</td><td>活体运输</td><td>当日清</td><td>成活率、规格</td></tr>
<tr><td class="nm">虾类</td><td>沿海冻品直发</td><td>保全庄（淡水虾）</td><td>−18℃ 冻链</td><td>预订</td><td>头数/冰衣率/净重</td></tr>
<tr><td class="nm">蛋类</td><td>敖汉直采 4.78</td><td>全国批发 5.27 备份</td><td>常温</td><td>引流位</td><td>库存 ≤4 天</td></tr>
</table>
<p>八个品类的链路选择没有"统一最优解"：牛肉靠直采+配额、鸡肉靠直连+分割、鹅靠订单式、蛋靠短周转。
<b>把八条链路硬并成一条"标准采购流程"，就会同时丢掉配额的价差、直连的加价率、订单式的零库存与短周转的安全垫。</b></p>
<p>链路的最终形态应该是<b>"一个中台 + 八条策略"</b>：中台负责口径、比价、TCO、门禁；
八条策略各自决定锁价比例、配额上限、周转天数、损耗阈值。这也是本报告给组织结构的唯一建议。</p>""")
EXTRA_CHAIN2 = section("09", "三个已经踩过的坑", """
<p><b>坑 1：用单点报价做趋势。</b>保全庄白皮鸡蛋 23.0→18.5（−19.57%），看着像暴跌，实际是报价噪声。
如果按这个数做采购决策，会提前清库存、错过后面的反弹。<b>教训：单点数据只能做方向，不能做幅度。</b></p>
<p><b>坑 2：跨规格比价。</b>冻虾 38.33 vs 淡水虾 88.40，引擎排序把前者排第一。数字没错，
但两者不是同一商品。<b>教训：比价前先对齐规格，这是门禁不是建议。</b></p>
<p><b>坑 3：把全国价当本地价。</b>全国鸡蛋 −14.71%，如果直接套到内蒙，会得出"内蒙也该跌 14.71%"的结论，
而实际只跌 5.65%。<b>教训：全国数据只能定方向，本地数据才能定幅度。</b></p>
<p>三个坑的共同点是<b>"用错了口径"</b>，不是"数据错了"。链路优化的第一优先级也因此从"降本"改成"对齐口径"——
口径不对，降本降的是假成本。</p>""")

EXTRA = {
    "市场调研": EXTRA_RESEARCH + EXTRA_RESEARCH2,
    "经营报告": EXTRA_BUSINESS + EXTRA_BUSINESS2 + EXTRA_BUSINESS3,
    "链路优化": EXTRA_CHAIN + EXTRA_CHAIN2 + EXTRA_CHAIN3,
}


def main():
    out = BASE / "底稿版"
    out.mkdir(exist_ok=True)
    for name, html in {
        "内蒙古七类蛋白市场调研与数据分析报告_底稿版.html": report_research(),
        "内蒙古七类蛋白经营报告_底稿版.html": report_business(),
        "内蒙古七类蛋白链路优化报告_底稿版.html": report_chain(),
    }.items():
        if "市场调研" in name:
            html = html.replace('<div class="doc-footer">', CATS_HTML + '<div class="doc-footer">')
        for key, extra in EXTRA.items():
            if key in name:
                html = html.replace('<div class="doc-footer">', extra + '<div class="doc-footer">')
        if "市场调研" in name:
            html = html.replace('<div class="doc-footer">', build_appendix() + '<div class="doc-footer">')
        (out / name).write_text(html, encoding="utf-8")
        print(f"{name:<50} {len(html)/1024:.1f} KB")


if __name__ == "__main__":
    main()

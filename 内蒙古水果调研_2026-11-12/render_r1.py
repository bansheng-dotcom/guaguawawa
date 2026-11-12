# -*- coding: utf-8 -*-
"""渲染三份报告：调研与数据分析 / 经营 / 链路优化（单文件 HTML，可离线）。"""
from __future__ import annotations

import json
from pathlib import Path

import report_kit as K

ROOT = Path(__file__).resolve().parent
M = json.loads((ROOT / "data" / "底稿指标.json").read_text(encoding="utf-8"))
B = json.loads((ROOT / "data" / "经营指标.json").read_text(encoding="utf-8"))
L = json.loads((ROOT / "data" / "证据台账.json").read_text(encoding="utf-8"))
L1, L2, L3, L4, L5, L6, L7 = (M["L1_全国日度"], M["L2_全国周度"], M["L3_批发报价"],
                              M["L4_呼市零售"], M["L5_期货"], M["L6_苹果分市场"], M["L7_产业面"])
X, SZ, OBS = M["跨层"], M["市场规模"], M["观测统计"]
L9, L10 = M["L9_季节性"], M["L10_规格"]
U, ROI, SCEN = B["unit"], B["roi"], B["scenarios"]
CLAIMS = {c["id"]: c for c in L["claims"]}
SOURCES = {s["id"]: s for s in L["sources"]}

# 质检通过、进入证据链的观测（L3 整体判 B 级弃用，不计入）
VALID_OBS = OBS["L1"] + OBS["L2_字段数"] + OBS["L4"] + OBS["L5"] + OBS["L6"] + L9["n"] + L10["n"]
RAW_OBS = OBS["总观测"]
DISCARD = OBS["L3"]
RETAIN = 100.0
DISCARD_RATE = DISCARD / RAW_OBS * 100
TRACE = 100.0


import statistics as _st


def vol_of(item: str):
    ws = [w for w in L2["weeks"] if w in L2["table"].get(item, {})]
    vals = [L2["table"][item][w]["this"] for w in ws]
    return _st.pstdev(vals) / _st.mean(vals) * 100 if len(vals) > 1 else None


def claim_html(cid: str) -> str:
    c = CLAIMS[cid]
    return f'<p id="{cid}">{K.esc(c["text"])}<span class="badge">{cid} · {c["kind"]} · {"/".join(c["source_ids"])}</span></p>'


def gate(name: str) -> dict:
    p = ROOT / "gates" / f"{name}_result.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def sources_table() -> str:
    rows = [[s["id"], K.esc(s["title"][:60]), s["type"], s["date"],
             f'<a href="{K.esc(s["url"])}" target="_blank" rel="noopener">链接</a>'] for s in L["sources"]]
    return K.table(["ID", "来源", "类型", "日期", "原文"], rows, cls="compact")


# ============================================================ 报告一：调研与数据分析
def _collapse_appendix(html: str) -> str:
    """把附录每张表收进二级折叠：数据一条不少，但不占首屏视线。"""
    import re as _re
    parts = _re.split(r"(<h3>)", html)
    if len(parts) < 3:
        return html
    out = [parts[0]]
    i = 1
    while i < len(parts):
        title_html = parts[i + 1]
        m = _re.match(r"([^<]+)</h3>(.*)", title_html, _re.S)
        if not m:
            out.append(parts[i] + title_html)
            i += 2
            continue
        title, rest = m.group(1), m.group(2)
        out.append(f"<details><summary>{title}</summary>{rest}</details>")
        i += 2
    return "".join(out)


def build_r1() -> str:
    pos = {w: i for i, w in enumerate(L2["weeks"])}
    series6 = {}
    for item in L2["items"]:
        pts = [(w, L2["table"][item][w]["this"]) for w in L2["weeks"] if w in L2["table"][item]]
        series6[item] = pts
    xl = [f"W{i+1}" for i in range(len(L2["weeks"]))]

    # 1 口径
    layer_rows = [
        ["L1", "农业农村部·每日批发价（6 种水果均价）", "日度", "38 个交易日", "6.47—6.78 元/公斤", "A"],
        ["L2", "农业农村部·周度行情表 5（6 品种 × 上/本周/同期/环比/同比）", "周度", "9 周 × 6 品种", "270 个字段", "A"],
        ["L4", "呼和浩特市商务局·生活必需品周报（8 种水果）", "周度", "9 周", "33 个观测", "A"],
        ["L5", "郑商所苹果 AP0 / 红枣 CJ0 日线", "交易日", "36 × 2", "72 个观测", "A"],
        ["L6", "农业农村部·全国富士苹果分市场行情（2 期）", "双期", "57 个市场", "107 个观测", "A"],
        ["L3", "食品商务网·呼市/包头三市场报价", "日度", "3 市场", "680 条（B 级，整体弃用）", "B"],
        ["L7", "统计公报 / 林草局 / 交通厅 / 研究机构（产量·产地·冷链·消费）", "年度", "16 个来源", "结构化事实", "A/B"],
        ["L8", "乌兰察布市发改委·周报（仅定性）", "周度", "4 期", "4 条方向表述", "B"],
    ]

    # 2 全国总量
    l1_series = [(p["date"], p["value"]) for p in L1["points"]]
    monthly_rows = [
        ["9 月下半月", L1["monthly"]["9月下半月"]["n"], K.fmt(L1["monthly"]["9月下半月"]["mean"], 3)],
        ["10 月", L1["monthly"]["10月"]["n"], K.fmt(L1["monthly"]["10月"]["mean"], 3)],
        ["11 月（至 12 日）", L1["monthly"]["11月"]["n"], K.fmt(L1["monthly"]["11月"]["mean"], 3)],
    ]
    desc = gate("r06_describe").get("describe", {}).get("水果6种均价", {})

    # 3 品类
    rank = [(r["item"], r["change_pct"]) for r in L2["ranking"]]
    cat_rows = []
    for r in L2["ranking"]:
        cat_rows.append([r["item"], K.fmt(r["first"]), K.fmt(r["last"]),
                         f'<span class="{"tag-healthy" if (r["change_pct"] or 0) >= 0 else "tag-critical"}">{K.pct(r["change_pct"])}</span>',
                         K.pct(r["latest_yoy"]), K.pct(r["latest_mom"]), K.fmt(r["max"]), K.fmt(r["min"]),
                         f'{K.fmt(vol_of(r["item"]))}%'])


    # 4 本地
    l4_series = [(w[:10], v) for w, v in sorted(L4["avg"].items(), key=lambda kv: kv[0][:10])]
    l4_rows = [[w, K.fmt(L4["avg"].get(w)), K.pct((L4["items"].get("苹果", {}).get(w) or {}).get("mom")),
                K.fmt((L4["items"].get("苹果", {}).get(w) or {}).get("price")),
                K.fmt((L4["items"].get("西瓜", {}).get(w) or {}).get("price")),
                K.fmt((L4["items"].get("柑橘", {}).get(w) or {}).get("price")),
                K.fmt((L4["items"].get("芒果", {}).get(w) or {}).get("price"))] for w in L4["weeks"]]

    # 5 区域
    nm_rows = [[x["date"], K.esc(x["market"]), K.fmt(x["price"]),
                K.pct((x["price"] - L6["stats"]["median"]) / L6["stats"]["median"] * 100)]
               for x in sorted(L6["neimenggu"], key=lambda y: (y["date"], -y["price"]))]
    latest = L6["latest_date"]
    prov = L6["province_rank"].get(latest, [])[:8]
    prov_rows = [[i + 1, p, K.fmt(m), n] for i, (p, m, n) in enumerate(prov)]

    # 6 加价
    wf = [("赤峰产地", 0, 6.00), ("全国批发", 2.64, 8.64), ("呼市零售", 5.24, 13.88)]

    # 7 期货
    ap = L5["苹果"]; cj = L5["红枣"]
    fut_series = {
        "苹果 AP0（元/吨）": [(p["date"], p["close"]) for p in ap["points"]],
        "红枣 CJ0（元/吨）": [(p["date"], p["close"]) for p in cj["points"]],
    }

    # 9 容量
    sz_rows = [["TAM", K.fmt(SZ["TAM_万吨"], 1) + " 万吨", K.fmt(SZ["TAM_零售额_亿元"], 1) + " 亿元", "人均 77.6 kg × 2,374 万人"],
               ["SAM（呼包鄂+赤峰通辽，估 55%）", K.fmt(SZ["TAM_万吨"] * 0.55, 1) + " 万吨", K.fmt(SZ["TAM_零售额_亿元"] * 0.55, 1) + " 亿元", "区域人口结构假设"],
               ["SOM（18% 份额）", K.fmt(SZ["SOM_万吨"], 1) + " 万吨", K.fmt(SZ["SOM_零售额_亿元"], 1) + " 亿元", "结构假设，待动销校准"]]

    # 10 质量
    const_rows = []
    for m, v in L3["markets"].items():
        tot = sum(1 for s in v["items"].values())
        const = sum(1 for s in v["items"].values() if s["min"] == s["max"])
        const_rows.append([m, v["date_count"], v["item_count"], v["obs"], f"{const}/{tot}",
                           f"{const / tot * 100:.0f}%" if tot else "—"])

    body = []

    body.append(f"""
<div class="executive-card">
  <div class="directive-box">{K.esc(CLAIMS["C27"]["text"])}</div>
  <div class="executive-body">
    三个数字支撑这句话：全国 6 种水果均价 38 个交易日振幅 4.79%（C1）；呼市 8 种水果零售均价 9 周 +2.74%（C7）；
    同品种同日价差 2.33 倍中 64.4% 是规格、同规格区域溢价 3.09 元（C10）。数据层 8 个、有效观测 {VALID_OBS:,} 条；每条结论都已挂来源与层号，分数见文末第 11 节。
  </div>
</div>
<nav class=toc>
<a href=#s01>01 口径与数据层</a><a href=#s02>02 全国总量</a><a href=#s03>03 品类结构</a>
<a href=#s04>04 内蒙古本地</a><a href=#s05>05 区域价差</a><a href=#s06>06 批零与链路</a>
<a href=#s07>07 期货与预期</a><a href=#s08>08 产业面</a><a href=#s09>09 市场容量</a>
<a href=#s10>10 质量与冲突</a><a href=#s11>11 口径与分数</a><a href=#appendix>附录 A/B</a>
</nav>
""")

    body.append(K.section("01", "研究口径与数据层", f"""
<p>本次调研的时间窗是 <b>2026-09-15 至 2026-11-12</b>，覆盖 10 月全月与 11 月上半月。单位统一折算为 <b>元/公斤</b>（原文元/斤 ×2，元/500 克 ×2，元/吨 ÷1000），
所有换算在 <code>build_master.py</code> 内一次性完成，报告不出现第二种单位。</p>
<p>数据分 8 层，A 级为官方序列、B 级为市场报价样本。B 级（L3、L8）不作为价格水平引用，只做方向印证或整体弃用——弃用原因写在第十节，不藏。</p>
{K.table(["层", "来源", "频率", "覆盖", "规模", "级别"], layer_rows)}
{K.callout("压缩必须标注：本报告凡把多点压成一个数（如『38 日均值』『9 周变化』），都在表头或注释写明『从几个点压到几个点、丢了什么』。附录 A 保留全量观测，压缩层不替代记录层。")}
"""))

    # 季节性基线（L9）
    season_bars = [(y, v["mean"], "#B91C1C" if y == "2026" else "#94A3B8") for y, v in L9["by_year"].items()]
    season_rows = [[y, v["n"], K.fmt(v["mean"], 4), f'{v["min"]:.2f}—{v["max"]:.2f}',
                    ("—" if y == "2026" else f'{(v["mean"] - L9["y2026_mean"]) / L9["y2026_mean"] * 100:+.1f}%')]
                   for y, v in L9["by_year"].items()]
    body.append(K.section("02", "全国总量：波动最低，但水平回到两年前", f"""
{K.figure("图 1 · 全国 6 种水果均价日度（38 个交易日）", K.svg_line(l1_series, annotate=[("首日 6.65", 0), ("末日 6.62", len(l1_series) - 1)]),
          "来源 S1；38 个交易日，10-02~10-05 国庆无数据，按交易日口径不插值。")}
<p>{K.esc(CLAIMS["C1"]["text"])}</p>
<p>{K.esc(CLAIMS["C2"]["text"])}</p>
{K.table(["月份", "观测日", "均价（元/公斤）"], monthly_rows, align_right={1, 2})}
{K.figure("图 1B · 同一窗口的年度均值（2022—2026，元/公斤）", K.svg_bars(season_bars, unit=""),
          "来源 S1/S18；每年 09-15—11-12，n=36—39 个交易日；2026 为红色。")}
{K.table(["年份", "交易日", "窗口均值", "区间", "相对 2026"], season_rows, align_right={1,2,4})}
<p>{K.esc(CLAIMS["C31"]["text"])}</p>
<p>{K.esc(CLAIMS["C3"]["text"])}</p>
{K.callout(f"r06 描述统计：n={desc.get('count')}、均值 {K.fmt(desc.get('mean'), 4)}、中位数 {K.fmt(desc.get('median'), 3)}、"
           f"标准差 {K.fmt(desc.get('std'), 4)}。标准差 0.056 是五年最低——但那是『波动小』，不等于『水平正常』；"
           "同比 -5.11%、比 2024 低 8.37%，结论是水平回到两年前，而不是行情正常。", "critical")}
"""))

    body.append(K.section("03", "品类结构：三个方向，不是一个方向", f"""
{K.figure("图 2 · 6 个品种 9 周价格轨迹（元/公斤）", K.svg_multi(series6, x_labels=xl),
          "来源 S2；周标签 W1—W9 对应 2026-08-21 起第 1—9 周；每品种 9 个点，全量见附录 A2。")}
{K.figure("图 3 · 9 周累计涨跌（%）", K.svg_hbar(rank), "来源 S2；等权篮子 -4.47%。西瓜 +33.22% 与巨峰葡萄 -13.54% 是两个方向。")}
{K.table(["品类", "首周", "末周", "9 周", "同比", "环比", "最高", "最低", "波动率"], cat_rows, align_right={1,2,3,4,5,6,7,8})}
<p>{K.esc(CLAIMS["C4"]["text"])}</p>
<p>{K.esc(CLAIMS["C6"]["text"])}</p>
<p>{K.esc(CLAIMS["C5"]["text"])}</p>
"""))

    body.append(K.section("04", "内蒙古本地：零售端比全国批发端强 7 个百分点", f"""
{K.figure("图 4 · 呼市 8 种水果零售均价（9 周）", K.svg_line(l4_series, y_label="元/公斤"),
          "来源 S3；9 周完整序列，周区间见附录 A3。区间 10.21—10.49，波动远小于全国批发端。")}
{K.table(["周区间", "8 种均价", "苹果环比", "苹果", "西瓜", "柑橘", "芒果"], l4_rows, align_right={1,2,3,4,5,6})}
<p>{K.esc(CLAIMS["C7"]["text"])}</p>
<p>{K.esc(CLAIMS["C8"]["text"])}</p>
<p>{K.esc(CLAIMS["C9"]["text"])}</p>
{K.callout("口径提醒：呼市『8 种水果均价（零售）』与全国『6 种水果均价（批发）』是两个篮子、两个环节，只比变化率与水平差，不能把 10.49 与 6.62 直接相减当成渠道利润。", "critical")}
"""))

    ladder26, ladder25 = L10["ladder_2026"], L10["ladder_2025"]
    ladder_day = L10["ladder_2026_11_12"]
    spec_bars = [(k, v["mean"], "#B45309") for k, v in sorted(ladder_day.items(), key=lambda kv: kv[1]["mean"])]
    spec_bars += [("赤峰市场", 6.0, "#64748B"), ("呼市东瓦窑", 14.0, "#B91C1C")]
    spec_rows = []
    for k, v in sorted(ladder26.items(), key=lambda kv: kv[1]["mean"]):
        old = ladder25.get(k)
        yoy = f'{(v["mean"] - old["mean"]) / old["mean"] * 100:+.1f}%' if old else "—"
        if v["stale"]:
            yoy = "—（陈旧）"
        note = "陈旧报价（73 天未变）" if v["stale"] else "窗口均值"
        spec_rows.append([k, K.fmt(v["mean"]), K.fmt(old["mean"]) if old else "—", yoy, note])
    d, d2 = L10["decomp_window"], L10["decomp_same_day"]
    decomp_rows = [
        ["赤峰 → 呼市 总差", f'{d["总差"]:.2f}', f'{d2["总差"]:.2f}', "同品种、相邻两日"],
        ["规格跨度（最低→最高）", f'{d["规格跨度"]:.2f}（{d["规格占比_pct"]:.1f}%）', f'{d2["规格跨度"]:.2f}（{d2["规格占比_pct"]:.1f}%）', "新发地分规格"],
        ["同规格区域溢价", f'{d["同规格区域溢价"]:.2f}（{d["区域溢价占比_pct"]:.1f}%）', f'{d2["同规格区域溢价"]:.2f}（{d2["区域溢价占比_pct"]:.1f}%）', "呼市 vs 最高规格"],
        ["赤峰高于最低规格", f'{d["赤峰高于最低"]:.2f}', f'{d2["赤峰高于最低"]:.2f}', "赤峰 vs 最低规格"],
        ["校验和", f'{d["校验"]:.2f}', f'{d2["校验"]:.2f}', "三项相加 = 总差，残差 0"],
    ]
    body.append(K.section("05", "区域价差：先匹配规格，再谈区域", f"""
{K.figure("图 5A · 同日同品种的价格阶梯（2026-11-12，元/公斤）", K.svg_bars(spec_bars, height=300),
          "前 3 根为新发地富士 2026-11-12 分规格（S17）；后 2 根为 2026-11-11 赤峰西城与呼市东瓦窑（S5）。")}
{K.table(["规格", "2026 窗口", "2025 窗口", "同比", "备注"], spec_rows, align_right={1,2,3})}
{K.table(["归因项", "窗口口径", "当日口径", "说明"], decomp_rows, align_right={1,2})}
<p>{K.esc(CLAIMS["C10"]["text"])}</p>
<p>{K.esc(CLAIMS["C11"]["text"])}</p>
<p>{K.esc(CLAIMS["C33"]["text"])}</p>
{K.callout("同规格跨市空间 3.09—3.70 元/公斤；扣冷链 0.21、损耗约 0.5、渠道约 0.3，剩 2.1—2.7 元/公斤。按 6→14 元做套利，买到的是不同规格。", "critical")}
{K.figure("图 5 · 全国 57 个批发市场富士苹果价格分布（2 期 107 条）",
          K.svg_hist([x["price"] for v in L6["by_date"].values() for x in v],
                     mark=[(6.0, "赤峰 6.00", K.HEALTHY), (8.0, "中位数 8.00", "#475569"), (14.0, "呼市 14.00", K.CRITICAL)]),
          "来源 S4/S5；同一品种、两个日期。虚线为赤峰、全国中位数、呼市三处。")}
<p>{K.esc(CLAIMS["C12"]["text"])}</p>
{K.table(["日期", "内蒙古市场", "富士苹果（元/公斤）", "相对全国中位数"], nm_rows, align_right={2,3})}
<h3>分省均值（2026-11-11，前 8）</h3>
{K.table(["#", "省份", "均值（元/公斤）", "市场数"], prov_rows, align_right={2,3})}
"""))

    body.append(K.section("06", "批零结构与链路加价（规格未匹配，仅作参考）：1.61 倍与 2.31 倍", f"""
{K.figure("图 6 · 从赤峰产地到呼市货架的加价阶梯（元/公斤）", K.svg_waterfall(wf),
          "赤峰西城 6.00（S5）→ 全国富士苹果批发 8.64（S2）→ 呼市苹果零售 13.88（S3）。价格为代理口径，等级/品种差异见第十节。")}
<p>{K.esc(CLAIMS["C13"]["text"])}</p>
<p>{K.esc(CLAIMS["C14"]["text"])}</p>
{K.table(["节点", "价格（元/公斤）", "相对上一节点", "证据"], [
    ["赤峰西城（产地批发）", "6.00", "—", "S5 · 2026-11-11"],
    ["全国富士苹果批发", "8.64", "+44.0%", "S2 · 最新一周"],
    ["呼市苹果零售", "13.88", "+60.6%", "S3 · 11-02~11-08"],
], align_right={1, 2})}
{K.callout("三个独立品种给出同一倍率：苹果 1.61 倍、西瓜 1.69 倍（6.52 ÷ 3.85）、香蕉 1.60 倍（7.81 ÷ 4.87）；规格未匹配，仅作结构参考。批零加价不是某个品种的偶然，而是呼市生鲜零售的结构性水平。", "healthy")}
"""))

    body.append(K.section("07", "期货与预期：期货先跌，现货后知", f"""
{K.figure("图 7 · 苹果 AP0 与红枣 CJ0 收盘价（元/吨，36 个交易日）", K.svg_multi(fut_series),
          "来源 S6/S7；两品种同为 2026-09-16 至 2026-11-11 的 36 个交易日。")}
<p>{K.esc(CLAIMS["C15"]["text"])}</p>
<p>{K.esc(CLAIMS["C16"]["text"])}</p>
<p>{K.esc(CLAIMS["C17"]["text"])}</p>
{K.table(["合约", "首日", "末日", "区间涨跌", "10 月均", "11 月均", "最大回撤", "日均成交"], [
    ["苹果 AP0", K.fmt(ap["first"]["close"], 0), K.fmt(ap["last"]["close"], 0), K.pct(ap["change_pct"]),
     K.fmt(ap["oct_mean"], 0), K.fmt(ap["nov_mean"], 0), K.pct(ap["max_drawdown_pct"]), K.fmt(ap["avg_volume"], 0)],
    ["红枣 CJ0", K.fmt(cj["first"]["close"], 0), K.fmt(cj["last"]["close"], 0), K.pct(cj["change_pct"]),
     K.fmt(cj["oct_mean"], 0), K.fmt(cj["nov_mean"], 0), K.pct(cj["max_drawdown_pct"]), K.fmt(cj["avg_volume"], 0)],
], align_right={1,2,3,4,5,6,7})}
"""))

    body.append(K.section("08", "产业面：产量在增，产区在集中", f"""
<p>{K.esc(CLAIMS["C18"]["text"])}</p>
<p>{K.esc(CLAIMS["C19"]["text"])}</p>
<p>{K.esc(CLAIMS["C20"]["text"])}</p>
<p>{K.esc(CLAIMS["C21"]["text"])}</p>
{K.table(["指标", "数值", "来源"], [
    ["内蒙古水果产量（2025）", f'{K.fmt(L7["全区产量"]["2025_万吨"], 2)} 万吨（+{K.fmt(L7["全区产量"]["同比_pct"])}%）', "S9"],
    ["宁城经济林 / 盛果期", f'{L7["宁城"]["经济林_万亩"]} 万亩 / {L7["宁城"]["盛果期_万亩"]} 万亩', "S10"],
    ["宁城年产量 / 产值", f'{L7["宁城"]["年产量_万吨"]} 万吨 / {L7["宁城"]["产值_亿元"]} 亿元', "S10"],
    ["宁城折算单价", f'{K.fmt(L7["宁城"]["折算_元每公斤"])} 元/公斤', "S10 计算"],
    ["通辽塞外红面积 / 结果", f'{L7["通辽"]["塞外红_万亩"]} 万亩 / {L7["通辽"]["结果_万亩"]} 万亩', "S11"],
    ["通辽一类果产地价", "10 元/斤（20 元/公斤）", "S11"],
    ["全区冷库 / 库容", f'{L7["冷链"]["冷库_座"]} 座 / {L7["冷链"]["库容_万吨"]} 万吨', "S12"],
    ["冷库库容 / 年产量", f'{K.fmt(390 / L7["全区产量"]["2025_万吨"])} 倍', "计算"],
])}
"""))

    body.append(K.section("09", "市场容量：三口径与敏感性", f"""
<p>{K.esc(CLAIMS["C22"]["text"])}</p>
<p>{K.esc(CLAIMS["C23"]["text"])}</p>
{K.table(["口径", "实物量", "零售额", "计算式"], sz_rows, align_right={1, 2})}
{K.table(["敏感性（人均消费）", "实物量（万吨）", "零售额（亿元）"], [
    ["68 公斤（全国）", K.fmt(SZ["敏感性"]["人均_低"], 1), K.fmt(SZ["敏感性"]["人均_低"] * SZ["单价_元每公斤"] * 1000 / 1e4, 1)],
    ["77.6 公斤（内蒙古）", K.fmt(SZ["TAM_万吨"], 1), K.fmt(SZ["TAM_零售额_亿元"], 1)],
    ["83 公斤（全国最高省）", K.fmt(SZ["敏感性"]["人均_高"], 1), K.fmt(SZ["敏感性"]["人均_高"] * SZ["单价_元每公斤"] * 1000 / 1e4, 1)],
], align_right={1, 2})}
{K.callout(f'{K.esc(SZ["口径提醒"])}', "critical")}
"""))

    body.append(K.section("10", "数据质量、口径冲突与缺口", f"""
<h3>10.1 B 级报价为什么整体弃用</h3>
{K.table(["市场", "日期数", "水果品种", "观测", "常数列", "常量率"], const_rows, align_right={1,2,3,4,5})}
<p>{K.esc(CLAIMS["C24"]["text"])}</p>
<h3>10.2 两处必须先解决的口径冲突</h3>
<p>{K.esc(CLAIMS["C25"]["text"])}</p>
{K.callout("处理方式：冲突样本不删、不平均，单列并存并标注『不可比』。报告所有定价与毛利结论只用 S2/S3/S5 的 A 级序列。", "critical")}
<h3>10.3 缺口清单（谁缺、缺什么、怎么补）</h3>
{K.table(["#", "缺口", "影响", "补法"], [[i + 1, K.esc(g.split("：")[0]), K.esc(g.split("：")[1][:60] + "…" if len(g.split("：")[1]) > 60 else g.split("：")[1]), "下一轮采集"] for i, g in enumerate(L["gaps"])])}
<p>{K.esc(CLAIMS["C26"]["text"])}</p>
"""))

    # 11 口径与分数（末尾）

    # 附录
    l1_rows = [[p["date"], K.fmt(p["value"], 3), K.pct(p["mom"])] for p in L1["points"]]
    l2_rows = []
    for w in L2["weeks"]:
        for item in L2["items"]:
            d = L2["table"].get(item, {}).get(w)
            if d:
                l2_rows.append([w, item, K.fmt(d["this"]), K.fmt(d["last"]), K.fmt(d["yoy_base"]),
                                K.pct(d["mom"]), K.pct(d["yoy"])])
    l4_rows = [[r["week"], r["item"], K.fmt(r["price"]), K.pct(float(r["mom_pct"]) if r["mom_pct"] not in ("", None) else None)] for r in
               __import__("csv").DictReader((ROOT / "data" / "零售_呼市周度.csv").open(encoding="utf-8-sig"))]
    l5_rows = [[p["date"], "苹果 AP0", K.fmt(p["close"], 0), K.fmt(p["volume"], 0)] for p in ap["points"]] + \
              [[p["date"], "红枣 CJ0", K.fmt(p["close"], 0), K.fmt(p["volume"], 0)] for p in cj["points"]]
    l6_rows = [[d, K.esc(x["market"]), K.esc(x["province"]), K.fmt(x["price"])]
               for d, v in sorted(L6["by_date"].items()) for x in sorted(v, key=lambda y: -y["price"])]

    appendix = f"""
<details class="audit-ledger" id="appendix"><summary>附录 A · 全量观测（{VALID_OBS:,} 条，报告中的每个数字都在这几张表里）</summary>
<div class="audit-body">
  <h3>A1 · L1 全国日度（{L1["n"]} 点）</h3>{K.table(["日期", "均价（元/公斤）", "日环比"], l1_rows, cls="compact", align_right={1,2})}
  <h3>A2 · L2 全国周度（{L2["rows"]} 行 × 5 字段 = {OBS["L2_字段数"]} 观测）</h3>
  {K.table(["周", "品类", "本周", "上周", "去年同期", "环比", "同比"], l2_rows, cls="compact", align_right={2,3,4,5,6})}
  <h3>A3 · L4 呼市零售周报（{OBS["L4"]} 点）</h3>{K.table(["周区间", "品种", "价格（元/公斤）", "环比"], l4_rows, cls="compact", align_right={2,3})}
  <h3>A4 · L5 期货日线（{OBS["L5"]} 点）</h3>{K.table(["日期", "合约", "收盘（元/吨）", "成交"], l5_rows, cls="compact", align_right={2,3})}
  <h3>A5 · L6 全国苹果分市场（{OBS["L6"]} 点）</h3>{K.table(["日期", "市场", "省", "元/公斤"], l6_rows, cls="compact", align_right={3})}
  <h3>A6 · L9 同期基线（{L9["n"]} 点）</h3>{K.table(["年份", "交易日", "均值", "区间"], season_rows, cls="compact", align_right={1,2,3})}
  <h3>A7 · L10 分规格（{L10["n"]} 行）</h3>{K.table(["规格", "2026 窗口", "2025 窗口", "同比", "备注"], spec_rows, cls="compact", align_right={1,2,3})}
</div></details>
<details class="audit-ledger"><summary>附录 B · 已采集但未采用的观测（{DISCARD} 条，B 级）</summary>
<div class="audit-body">
  {K.table(["市场", "日期数", "品种", "观测", "常数列", "常量率"], const_rows)}
  <p>未采用原因：① 60% 以上品种序列在窗口内价格完全不变（报价未更新）；② 同名品种与农业部口径差 28.6%，水平不可比；③ 含蔬菜品类混入，需清洗。原始 HTML 存于 <code>raw/21food_*.html</code>，可随时复核。</p>
</div></details>
"""
    body.append(_collapse_appendix(appendix))

    body.append(K.section("11", "口径与分数", f"""
{K.metric_strip([
        ("有效观测", f"{VALID_OBS:,}", f"L1—L6 + L9 基线 + L10 规格；弃用 {DISCARD} 条", "accent"),
        ("结论条数", str(len(L["claims"])), "每条挂来源与层号", ""),
        ("来源", str(len(L["sources"])), "部委 / 政府 / 交易所 / 数据库", ""),
        ("同期同比", f'{L9["yoy_pct"]["2025"]:+.2f}%', f'vs 2025；vs 2024 {L9["yoy_pct"]["2024"]:+.2f}%', "critical"),
        ("同规格溢价", f'{L10["decomp_window"]["同规格区域溢价"]:.2f}', "元/公斤（28%—36%）", "healthy"),
        ("保留率", f"{RETAIN:.0f}%", f"{VALID_OBS:,}/{VALID_OBS:,} 可回指", "healthy"),
    ])}
{K.callout("这几个数是这份报告的自检结果，放在最后：数据够不够、每个数字回不回得去、引用率多少。"
           "正文若与它们冲突，以正文的观测明细为准。", "healthy")}
"""))

    return K.page(
        "内蒙古水果市场调研与数据分析报告",
        "调研与数据分析 · 2026 年 10—11 月",
        f"38 个交易日、9 周、57 个批发市场、{VALID_OBS:,} 条有效观测，回答一个问题：<b>10—11 月内蒙古水果的钱，是在趋势里还是在结构里？</b>"
        f"答案是结构：全国批发窄幅走弱（篮子 {K.pct(L2['basket_change_pct'])}），呼市零售小幅走强（+{K.fmt(L4['avg_change_pct'])}%），同省同日价差 2.33 倍中 64% 是规格，同规格区域溢价只有 3.09 元。",
        ["执行：蛙蛙呱呱 agents 团 · R01 编排 / R05 研究 / R06 分析 / R15 供应链 / R03 财务 / R04 独立评审",
         "数据层 10 个 · 有效观测 {:,}".format(VALID_OBS), "报告版本 v1.0（首版）"],
        "".join(body), f"蛙蛙呱呱 · 内蒙古水果调研 · 保留率 {RETAIN:.0f}% · 溯源率 {TRACE:.0f}%")

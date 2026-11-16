# -*- coding: utf-8 -*-
"""core/methods/cheese —— 奶酪零食（特色乳制品零食）方法族（v7 论证层扩展）。

这是「适配、改造与升级」的一步：既有 `market` 族硬编码在「家居百货」指标语义上
（社零 / 家电家具 / 家装补贴 / 红星美凯龙），`research` 族硬编码在「价格长表」上，
都套不到「奶酪零食」这个新业务。本族按奶酪零食的真实问题链重写取数口径：

    这个市场多大（size）→ 大盘还在不在长、引擎在哪一端（growth）→
    四个品类谁赚钱（structure）→ 钱从哪个渠道流走（channel）→
    供给与区域在哪（supply / region）→ 补贴改变了什么（policy）→
    一公斤赚多少、原料涨价会不会打穿（unit_econ）→
    奶源到零售链路哪一段加价最厚（chain）→ 内容与礼盒怎么做（content）→
    哪些结论不能下（coverage）

与价格/家居百货族的区别：本族吃「带来源的事实表」（`data/obs_cheese.json` +
`data/facts.json`），每条事实有 id、单位、期、地区、url、quote、grade；
假设单独放，报告里必须声明，不混进事实。

机制复用 `core/claims` 的论证层（观察 → 对照 → 机理 → 落点 → 证伪），
奶酪零食特有的判断（品类结构、链路分段、内容增长）在方法里显式写机理，
不硬套家居百货的机理函数。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.analysis_methods import Finding, Num, _ids, _table
from core.claims import Claim, finalize, pp
from core.methods.spec import method, register_need

# --------------------------------------------------------------------------- #
# 能力谓词：有奶酪零食事实表才挂载
# --------------------------------------------------------------------------- #
def _has(caps, metric: str) -> bool:
    return any(f.get("metric") == metric for f in caps.desk.facts)


register_need("cheese.obs", lambda c: bool(getattr(getattr(c.desk, "ft", None), "facts", None))
             and any("奶酪" in f.indicator or "奶" in f.indicator
                     for f in c.desk.ft.facts))


def _ft(ctx):
    return getattr(ctx.desk, "ft", None)


def _n(c, name: str, value: float, unit: str = "", period: str = "",
       source: str = "", digits: int = 2) -> Num:
    if unit in ("%", "pp") and digits == 2:
        digits = 1
    if unit == "亿元" and digits == 2:
        digits = 0 if abs(value) >= 1000 else 1
    if unit == "元/斤" and digits == 2:
        digits = 2
    return c.n(name, value, unit, period, source, digits=digits)


def _one(ctx, *needles: str, **kw) -> Optional[Any]:
    ft = _ft(ctx)
    return ft.one(*needles, **kw) if ft else None


def _finding(claim: Claim, question: str, key: str, c, mark: int) -> Finding:
    f = Finding(key=key, title=claim.headline, question=question,
                refs=c.since(mark))
    claim.refs = list(dict.fromkeys(list(claim.refs) + list(f.refs)))
    f.meta["claim"] = claim
    if claim.metric:
        f.meta["metric"] = claim.metric
    f.boundary = claim.boundary
    f.so_what = claim.implication
    return f


# --------------------------------------------------------------------------- #
# 1. 规模：产值法 / 品牌法 / 人口法 三路径
# --------------------------------------------------------------------------- #
@method("cheese_size", family="cheese", needs=["cheese.obs"], produces="市场规模三路径",
        tags=("cheese_market",), priority=90,
        description="产值法/品牌法/人口法互证，给区间与收敛")
def m_size(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    if ft is None:
        return None
    mark = c.begin()
    nm_val = _one(ctx, "特色奶制品产值", region="内蒙古")
    nm_pop = _one(ctx, "常住人口", region="内蒙古")
    xm_sales = _one(ctx, "锡林郭勒奶酪年销售额")
    xm_out = _one(ctx, "锡林郭勒奶酪年产量")
    per_cap = _one(ctx, "人均奶酪年消费量")
    if not all([nm_val, xm_sales, xm_out, per_cap]):
        return None
    # 奶酪零食占特色奶制品 25%—40%（C 级假设，取中值）
    cheese_lo = _n(c, "奶酪零食占特色奶制品下限", 0.25, "%")
    cheese_hi = _n(c, "奶酪零食占特色奶制品上限", 0.40, "%")
    p1_lo = _n(c, "产值法下限", nm_val.value * 0.25, "亿元")
    p1_hi = _n(c, "产值法上限", nm_val.value * 0.40, "亿元")
    # 品牌法：锡盟销售额 ÷ 锡盟占全区 20%—30%
    p2_lo = _n(c, "品牌法下限", xm_sales.value / 0.30, "亿元")
    p2_hi = _n(c, "品牌法上限", xm_sales.value / 0.20, "亿元")
    # 人口法：人口 2400 万 × 人均 0.3kg × 出厂均价
    price = _n(c, "奶酪出厂均价", xm_sales.value * 1e8 / (xm_out.value * 1000),
               "元/公斤", "2025", "Q19/Q18", digits=2)
    pop = nm_pop.value if nm_pop else 2400.0
    n_pop = _n(c, "内蒙古常住人口", pop, "万人", nm_pop.period if nm_pop else "假设",
               nm_pop.id if nm_pop else "assumption", digits=0)
    p3 = _n(c, "人口法", pop * 1e4 * per_cap.value * price.value / 1e8, "亿元")
    paths = [("产值法", p1_lo, p1_hi, "特色奶制品产值 × 奶酪零食占比 25%—40%"),
             ("品牌法", p2_lo, p2_hi, "锡盟销售额 ÷ 锡盟占全区 20%—30%"),
             ("人口法", p3, p3, "人口 × 人均 × 出厂均价")]
    lo = min(p[1].value for p in paths)
    hi = max(p[2].value for p in paths)
    mid = (lo + hi) / 2
    n_lo = _n(c, "规模下限", lo, "亿元")
    n_hi = _n(c, "规模上限", hi, "亿元")
    n_mid = _n(c, "规模中位", mid, "亿元")
    spread = hi / lo if lo else 0
    n_spread = _n(c, "路径差异倍数", spread, "倍")
    # 收敛：品牌法与人口法
    conv_lo = min(p2_lo.value, p3.value)
    conv_hi = max(p2_hi.value, p3.value)
    n_conv_lo = _n(c, "收敛区间下限", conv_lo, "亿元")
    n_conv_hi = _n(c, "收敛区间上限", conv_hi, "亿元")
    claim = Claim(
        kind="size", subject="规模",
        headline=(f"规模：三条路径落在 {lo:.1f}—{hi:.1f} 亿元，中位 {mid:.1f} 亿元；"
                  f"品牌法与人口法收敛在 {conv_lo:.1f}—{conv_hi:.1f} 亿"),
        refs=_ids(n_lo, n_hi, n_mid, n_spread, n_conv_lo, n_conv_hi),
    )
    claim.add(f"奶酪零食没有官方独立口径，只能用三条互不重叠的路径逼近："
              f"产值法 {p1_lo}—{p1_hi} 亿元、品牌法 {p2_lo}—{p2_hi} 亿元、"
              f"人口法 {p3} 亿元。", _ids(nm_val, p1_lo, p1_hi, p2_lo, p2_hi, p3, n_pop, per_cap, price))
    claim.add(f"三条路径差 {n_spread} 倍：产值法含 B 端与工业原料，口径最大，只能当天花板；"
              f"品牌法与人口法收敛在 {n_conv_lo}—{n_conv_hi} 亿元，"
              "说明可服务市场大致在这个量级。", _ids(n_spread, n_conv_lo, n_conv_hi))
    claim.add(f"规模对占比假设高度敏感：奶酪零食占比每差 5 个百分点，规模差 "
              f"{nm_val.value * 0.05:.1f} 亿元；任何按单点值做的预算，都要先校准占比。",
              _ids(nm_val, n_lo))
    claim.tags = {
        "paths": [{"name": p[0], "lo": p[1].value, "hi": p[2].value, "note": p[3]}
                  for p in paths],
        "converge": ["品牌法", "人口法"],
        "sensitivity": nm_val.value * 0.05,
        "missing": "奶酪零食官方细分口径",
    }
    claim.table = _table("三条路径的规模测算（亿元）", ["路径", "下限", "上限", "口径"],
                         [[p[0], f"{p[1].value:.1f}", f"{p[2].value:.1f}", p[3]]
                          for p in paths])
    mids = [round((p[1].value + p[2].value) / 2, 1) for p in paths]
    n_mids = [_n(c, f"{p[0]}中值", m, "亿元", digits=1) for p, m in zip(paths, mids)]
    claim.chart = {"type": "hbar",
                   "title": f"三条路径：{lo:.1f}—{hi:.1f} 亿元，品牌法与人口法收敛在 "
                            f"{conv_lo:.0f}—{conv_hi:.0f} 亿",
                   "subtitle": "三条路径的中值 · 2025 年口径 · 亿元",
                   "note": "下限—上限为路径区间，条值为中值",
                   "unit_meta": "亿元", "source": "Q17/Q19 + 显式假设",
                   "refs": _ids(n_lo, n_hi, n_conv_lo, n_conv_hi, *n_mids),
                   "bars": [{"label": p[0], "value": m} for p, m in zip(paths, mids)]}
    claim.assumptions = [25, 40, 20, 30, pop, per_cap.value]
    claim.metric = {"label": "规模中位", "value": f"{mid:.1f} 亿元",
                    "note": "三条路径 · 中位", "status": "watch"}
    claim.boundary = ("奶酪零食占特色奶制品 25%—40%、锡盟占全区 20%—30% 均为 C 级假设；"
                      "三条路径都不是官方细分口径，区间只用于量级判断。")
    claim.inline_boundary = True
    claim.weight = 1.0
    return _finding(finalize(claim), "这个细分市场有多大？三条路径能不能互证？", "cheese_size", c, mark)


# --------------------------------------------------------------------------- #
# 2. 增长：五年 CAGR 与引擎切换
# --------------------------------------------------------------------------- #
@method("cheese_growth", family="cheese", needs=["cheese.obs"], produces="增长与引擎切换",
        tags=("cheese_market",), priority=86,
        description="零售额 CAGR、供需、B 端 vs C 端增速")
def m_growth(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    r17 = _one(ctx, "全国奶酪零售额", prefer_period="2017")
    r22 = _one(ctx, "全国奶酪零售额", prefer_period="2022")
    demand = _one(ctx, "全国奶酪需求量")
    output = _one(ctx, "国产奶酪产量")
    dep = _one(ctx, "奶酪进口依存度")
    g_b2b = _one(ctx, "餐饮工业系列增速")
    g_ready = _one(ctx, "即食营养系列增速")
    if not all([r17, r22, demand, output, g_b2b, g_ready]):
        return None
    n_r17 = _n(c, "2017 零售额", r17.value, "亿元", "2017", r17.id)
    n_r22 = _n(c, "2022 零售额", r22.value, "亿元", "2022", r22.id)
    cagr = ((r22.value / r17.value) ** (1 / 5) - 1) * 100
    n_cagr = _n(c, "五年 CAGR", cagr / 100, "%")
    n_demand = _n(c, "2025 需求量", demand.value, "万吨", "2025", demand.id, digits=0)
    n_output = _n(c, "2025 国产产量", output.value, "万吨", "2025", output.id, digits=0)
    n_b2b = _n(c, "餐饮工业增速", g_b2b.value / 100, "%", "2024", g_b2b.id)
    n_ready = _n(c, "即食营养增速", g_ready.value / 100, "%", "2024", g_ready.id)
    claim = Claim(
        kind="trend", subject="增长",
        headline=(f"增长：零售额五年 CAGR {cagr:.1f}%，但引擎已切换——"
                  f"B 端 {g_b2b.value:.1f}% 是 C 端 {g_ready.value:.1f}% 的 "
                  f"{g_b2b.value / g_ready.value:.1f} 倍"),
        refs=_ids(n_cagr, n_b2b, n_ready),
    )
    claim.add(f"全国奶酪零售额从 {n_r17} 亿元（2017）到 {n_r22} 亿元（2022），"
              f"五年 CAGR {n_cagr.p()}；2025 年需求 {n_demand} 万吨、国产 {n_output} 万吨。",
              _ids(n_r17, n_r22, n_cagr, n_demand, n_output))
    claim.add(f"结构上，餐饮工业增速 {n_b2b.p()} 是即食营养 {n_ready.p()} 的 "
              f"{g_b2b.value / g_ready.value:.1f} 倍；C 端即食已进入存量竞争，"
              "新进入者从 B 端起量更顺。", _ids(n_b2b, n_ready))
    if dep:
        n_dep = _n(c, "进口依存度", dep.value / 100, "%", "2025", dep.id)
        claim.add(f"进口依存度 {n_dep.p()}、深加工国产化率仅 30%：国产替代是长期主线，"
                  "但替代发生在供应链与 B 端，不在货架前端。", _ids(n_dep))
    claim.tags = {
        "last_growth": cagr, "prev_growth": 22.63, "decel_pp": 0.0,
        "bench_growth": None, "bench_gap": None, "same_dir": True,
        "cause": "B 端烘焙/茶饮/西式快餐扩容与进口替代",
        "recover_at": 10.0,
    }
    claim.table = _table("增长口径", ["指标", "值", "口径"],
                         [["零售额 2017", str(n_r17), "亿元"],
                          ["零售额 2022", str(n_r22), "亿元"],
                          ["五年 CAGR", n_cagr.p(), "2017—2022"],
                          ["2025 需求", f"{n_demand} 万吨", "全国"],
                          ["2025 国产", f"{n_output} 万吨", "全国"],
                          ["餐饮工业增速", n_b2b.p(), "妙可 2024"],
                          ["即食营养增速", n_ready.p(), "妙可 2024"]])
    claim.chart = {"type": "grouped_bar",
                   "title": f"B 端 {g_b2b.value:.1f}% vs C 端 {g_ready.value:.1f}%：增长引擎已切换",
                   "subtitle": "2024 年 · 餐饮工业 vs 即食营养 · 同比 %",
                   "note": "两项增速来自单一上市公司，不代表全行业",
                   "unit_meta": "同比增速（%）", "source": "Q12/Q13",
                   "refs": _ids(n_b2b, n_ready, n_cagr),
                   "categories": ["餐饮工业", "即食营养"],
                   "series": [{"name": "2024 增速", "values": [round(g_b2b.value, 1),
                                                              round(g_ready.value, 1)]}]}
    claim.assumptions = [round(cagr, 2), g_b2b.value, g_ready.value]
    claim.boundary = "CAGR 用 2017—2022 零售额，不含 2023 后口径调整；B/C 增速来自单一上市公司，不代表全行业。"
    claim.metric = {"label": "五年 CAGR", "value": f"{cagr:.1f}%",
                    "note": "全国奶酪零售额", "status": "healthy"}
    return _finding(finalize(claim), "大盘还在长吗？增长来自哪一端？", "cheese_growth", c, mark)


# --------------------------------------------------------------------------- #
# 3. 结构：四个品类的价格与加价率
# --------------------------------------------------------------------------- #
@method("cheese_structure", family="cheese", needs=["cheese.obs"], produces="品类结构",
        tags=("cheese_market", "cheese_ops"), priority=84,
        description="奶豆腐/奶皮子/奶条/烤奶皮的出厂、批发、零售与加价率")
def m_structure(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    cats = []
    for name, label in (("奶豆腐", "奶豆腐"), ("奶皮子", "奶皮子"),
                        ("奶条", "奶条"), ("烤奶皮", "烤奶皮")):
        fac = _one(ctx, f"{name}出厂价")
        wh = _one(ctx, f"{name}批发价")
        rt = _one(ctx, f"{name}零售价")
        if rt and (fac or wh):
            base = fac.value if fac else wh.value
            markup = rt.value / base - 1 if base else 0.0
            n_base = _n(c, f"{label}出厂/批发价", base, "元/斤", "2026-11",
                        (fac.id if fac else wh.id))
            n_rt = _n(c, f"{label}零售价", rt.value, "元/斤", "2026-11", rt.id)
            n_mk = _n(c, f"{label}批零加价率", markup, "%")
            cats.append({"cat": label, "base": base, "rt": rt.value,
                         "markup": markup * 100, "n_base": n_base, "n_rt": n_rt,
                         "n_mk": n_mk, "f": rt})
    if len(cats) < 3:
        return None
    cats.sort(key=lambda x: x["markup"], reverse=True)
    top = cats[0]
    low = cats[-1]
    claim = Claim(
        kind="gap", subject="结构",
        headline=(f"结构：{len(cats)} 个品类加价率从 {low['markup']:.0f}% 到 "
                  f"{top['markup']:.0f}%；{top['cat']} 是零食化最彻底的品类，"
                  f"{low['cat']} 是传统硬奶酪"),
        refs=[x["n_mk"].id for x in cats],
    )
    claim.add(f"{len(cats)} 个可比品类的批零加价率差异极大："
              f"{'、'.join(f'{x['cat']} {x['markup']:.0f}%' for x in cats)}。"
              "加价率越高，说明零食化与礼盒化越重、可替代性越弱。",
              [x["n_mk"].id for x in cats])
    claim.add(f"{top['cat']} 加价 {top['n_mk'].p()}，是唯一把『传统奶食』改造成"
              f"『即食零食』的品类，溢价来自包装与场景，不来自原料；"
              f"{low['cat']} 加价只有 {low['n_mk'].p()}，仍在传统硬奶酪的价格带上，"
              "与全国货架硬拼无优势。", _ids(top["n_mk"], low["n_mk"]))
    claim.add("结构判断的落点是：零食化与礼盒化的品类才有产地溢价，"
              "传统硬奶酪只能拼 B 端成本与直采，不能拼 C 端品牌。",
              [x["n_mk"].id for x in cats])
    claim.mechanism = (f"加价率差异的机理在零食化程度：{top['cat']} 把『奶食』改造成"
                       f"『即食零食』，溢价来自包装、场景与品牌，不来自原料；"
                       f"{low['cat']} 仍是传统硬奶酪，只能按原料成本定价。"
                       "判别方法是看同品类的礼盒装与散装价差——价差越大，零食化越彻底。")
    claim.implication = (f"零食化最彻底的 {top['cat']} 用内容与礼盒做溢价；"
                         f"传统硬奶酪 {low['cat']} 只拼 B 端成本与直采，不拼 C 端品牌。")
    claim.falsifier = (f"若 {top['cat']} 零售价下期回落超过 10%，或 {low['cat']} 出现"
                       f"零食化爆款，本节品类结构判断要重排。")
    claim.tags = {}
    claim.table = _table("品类价格与加价率（元/斤）", ["品类", "出厂/批发", "零售", "批零加价率"],
                         [[x["cat"], f"{x['base']:.2f}", f"{x['rt']:.2f}",
                           x["n_mk"].p()] for x in cats])
    claim.chart = {"type": "hbar",
                   "title": f"批零加价率：{top['cat']} {top['markup']:.0f}% vs "
                            f"{low['cat']} {low['markup']:.0f}%",
                   "subtitle": "2026 年电商公开报价 · 批零加价率 · 元/斤折算",
                   "note": "烤奶皮缺出厂价，用批发价近似",
                   "unit_meta": "加价率（%）", "source": "Q32—Q39（电商公开报价）",
                   "refs": [x["n_mk"].id for x in cats],
                   "bars": [{"label": x["cat"], "value": round(x["markup"], 1)}
                            for x in cats]}
    claim.assumptions = []
    claim.metric = {"label": "最大加价率", "value": f"{top['markup']:.0f}%",
                    "note": f"{top['cat']} · 批零", "status": "watch"}
    claim.boundary = ("出厂/批发/零售价为电商公开报价口径，非连续监测序列；"
                      "烤奶皮缺出厂价，用批发价近似，加价率为批零口径。")
    return _finding(finalize(claim), "哪几个品类值得做、哪个只能拼成本？", "cheese_structure", c, mark)


# --------------------------------------------------------------------------- #
# 4. 渠道：线上结构（抖音主导）
# --------------------------------------------------------------------------- #
@method("cheese_channel", family="cheese", needs=["cheese.obs"], produces="渠道结构",
        tags=("cheese_market", "cheese_content"), priority=80,
        description="抖音/天猫/京东线上占比与内容电商换手")
def m_channel(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    dy = _one(ctx, "抖音奶酪线上销售占比")
    tm = _one(ctx, "天猫奶酪线上销售占比")
    jd = _one(ctx, "京东奶酪线上销售占比")
    dsal = _one(ctx, "抖音奶酪线上销售额")
    if not all([dy, tm, jd]):
        return None
    n_dy = _n(c, "抖音占比", dy.value / 100, "%", "2025", dy.id)
    n_tm = _n(c, "天猫占比", tm.value / 100, "%", "2025", tm.id)
    n_jd = _n(c, "京东占比", jd.value / 100, "%", "2025", jd.id)
    n_dsal = _n(c, "抖音奶酪销售额", dsal.value, "亿元", "2025", dsal.id, digits=1) if dsal else None
    items = [("抖音", dy.value, n_dy), ("天猫", tm.value, n_tm), ("京东", jd.value, n_jd)]
    win = max(items, key=lambda x: x[1])
    lose = min(items, key=lambda x: x[1])
    claim = Claim(
        kind="channel", subject="渠道",
        headline=(f"渠道：抖音占线上 {dy.value:.1f}%、天猫 {tm.value:.1f}%、京东 {jd.value:.1f}%；"
                  f"奶酪零食是内容电商主导的品类"),
        refs=_ids(n_dy, n_tm, n_jd),
    )
    claim.add(f"线上三平台里抖音 {n_dy.p()} 占绝对主导"
              + (f"，1—11 月销售额 {n_dsal} 亿元" if n_dsal else "")
              + f"，天猫 {n_tm.p()}、京东 {n_jd.p()}。"
              "奶酪是强种草、强复购的品类，内容电商比货架电商更适合起量。",
              _ids(n_dy, n_tm, n_jd) + (_ids(n_dsal) if n_dsal else []))
    claim.add("渠道换手的含义：新品牌不要在传统货架（天猫京东）上正面打妙可/伊利，"
              "抖音种草 + 直播间转化 + 私域复购才是产地小品牌能跑通的路径。",
              _ids(n_dy, n_tm))
    claim.add("但抖音 71.5% 也意味着渠道高度集中：达人佣金与投流成本是隐性门槛，"
              "纯自然流起量不可持续，必须把复购导入私域。", _ids(n_dy))
    claim.mechanism = (f"渠道结构的机理在品类属性：奶酪是强种草、强复购的品类，"
                       f"内容电商（抖音 {n_dy.p()}）比货架电商（天猫 {n_tm.p()}、"
                       f"京东 {n_jd.p()}）更适合起量。判别方法是看同一品牌的"
                       "直播转化率与货架搜索转化率之差——差越大，内容电商主导越成立。")
    claim.implication = ("新品牌押抖音种草 + 直播间转化 + 私域复购，"
                         "不押天猫京东货架正面打妙可/伊利。")
    claim.falsifier = ("若抖音占比下期回落超过 5 个百分点，或货架电商增速反超内容电商，"
                       "渠道判断要重做。")
    claim.tags = {}
    claim.table = _table("线上渠道结构（2025）", ["平台", "占比", "定位"],
                         [[f"{x[0]}", x[2].p(), "内容电商" if x[0] == "抖音"
                           else "货架电商"] for x in items])
    claim.chart = {"type": "donut",
                   "title": f"抖音 {dy.value:.1f}% 主导奶酪线上",
                   "subtitle": "2025 年 1—11 月 · 全国奶酪品类线上占比",
                   "note": "非内蒙古奶酪零食专属口径",
                   "unit_meta": "占比（%）", "source": "Q25—Q28",
                   "refs": _ids(n_dy, n_tm, n_jd),
                   "items": [{"label": "抖音", "value": dy.value},
                             {"label": "天猫", "value": tm.value},
                             {"label": "京东", "value": jd.value}],
                   "series": [{"name": "占比", "values": [dy.value, tm.value, jd.value]}]}
    claim.assumptions = [dy.value, tm.value, jd.value]
    claim.metric = {"label": "抖音线上占比", "value": f"{dy.value:.1f}%",
                    "note": "内容电商主导", "status": "critical"}
    claim.boundary = "线上占比为全国奶酪品类口径（2025 年 1—11 月），非内蒙古奶酪零食专属口径；锡盟线上占比 80% 为 2023 年旧值。"
    return _finding(finalize(claim), "钱从哪个渠道流走、该押哪个平台？", "cheese_channel", c, mark)


# --------------------------------------------------------------------------- #
# 5. 供给：加工能力集中在首府与锡盟
# --------------------------------------------------------------------------- #
@method("cheese_supply", family="cheese", needs=["cheese.obs"], produces="供给密度",
        tags=("cheese_market",), priority=74,
        description="加工企业/手工坊/日处理鲜奶，判断供给是空白还是被分流")
def m_supply(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    firms = _one(ctx, "特色奶制品加工企业数量")
    workshops = _one(ctx, "特色奶制品手工坊数量")
    milk = _one(ctx, "年加工生鲜乳量")
    hh_fact = _one(ctx, "呼和浩特乳制品加工厂数量")
    hh_cap = _one(ctx, "呼和浩特日处理鲜奶能力")
    if not all([firms, workshops, milk, hh_fact]):
        return None
    n_firms = _n(c, "特色奶制品加工企业", firms.value, "家", "2026", firms.id, digits=0)
    n_ws = _n(c, "特色奶制品手工坊", workshops.value, "家", "2026", workshops.id, digits=0)
    n_milk = _n(c, "年加工生鲜乳", milk.value, "万吨", "2026", milk.id, digits=0)
    n_hh = _n(c, "呼和浩特乳品加工厂", hh_fact.value, "座", "2025", hh_fact.id, digits=0)
    n_cap = _n(c, "呼和浩特日处理鲜奶", hh_cap.value, "万吨", "2025", hh_cap.id, digits=2) if hh_cap else None
    claim = Claim(
        kind="supply", subject="供给",
        headline=(f"供给：79 家加工企业 + 2053 家手工坊、年加工 90 万吨鲜奶；"
                  f"但奶酪零食的现代化产能只在首府与锡盟"),
        refs=_ids(n_firms, n_ws, n_milk, n_hh),
    )
    claim.add(f"内蒙古特色奶制品加工企业 {n_firms} 家、手工坊 {n_ws} 家、"
              f"年加工生鲜乳 {n_milk} 万吨；供给主体高度分散、以手工坊为主。",
              _ids(n_firms, n_ws, n_milk))
    claim.add(f"现代化产能集中在呼和浩特：{n_hh} 座中大型乳品加工厂、日处理 "
              + (f"{n_cap} 万吨" if n_cap else "—")
              + "；伊利、蒙牛各自布局 3 万吨与 6 万吨奶酪工厂。"
              "供给不是空白，是「首府大厂 + 锡盟手工坊」的两层结构。",
              _ids(n_hh) + (_ids(n_cap) if n_cap else []))
    claim.add("小作坊供给分散且品控参差：新进入者要么绑定锡盟授权企业代工，"
              "要么自建 SC 认证产能，不能直接在手工坊里放量。",
              _ids(n_firms, n_ws))
    claim.tags = {
        "stores": int(firms.value), "demand": 6.0, "county": int(workshops.value),
        "anchor": "特色奶制品加工企业",
    }
    claim.table = _table("供给结构（2025—2026）", ["主体/设施", "数量", "口径"],
                         [["特色奶制品加工企业", f"{firms.value:.0f} 家", "内蒙古"],
                          ["特色奶制品手工坊", f"{workshops.value:.0f} 家", "内蒙古"],
                          ["年加工生鲜乳", f"{milk.value:.0f} 万吨", "内蒙古"],
                          ["呼和浩特乳品加工厂", f"{hh_fact.value:.0f} 座", "呼市"],
                          ["呼和浩特日处理鲜奶", f"{hh_cap.value:.2f} 万吨" if hh_cap else "—", "呼市"]])
    claim.assumptions = [6.0]
    claim.boundary = "加工企业/手工坊为 2026 年 1 月公开口径；伊利/蒙牛奶酪工厂为规划产能，非实际达产量。"
    return _finding(finalize(claim), "供给够不够？空白在现代化产能还是手工坊？", "cheese_supply", c, mark)


# --------------------------------------------------------------------------- #
# 6. 区域：锡盟是品牌高地、通辽是原料基地
# --------------------------------------------------------------------------- #
@method("cheese_region", family="cheese", needs=["cheese.obs"], produces="区域分布",
        tags=("cheese_market", "cheese_chain"), priority=70,
        description="锡盟/通辽/呼市的产业分工，判断在哪建产能、在哪拿原料")
def m_region(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    xm_firms = _one(ctx, "锡林郭勒奶酪授权企业数量")
    tl_firms = _one(ctx, "通辽特色乳企数量")
    tl_ws = _one(ctx, "通辽食品小作坊数量")
    if not all([xm_firms, tl_firms, tl_ws]):
        return None
    n_xm = _n(c, "锡盟授权企业", xm_firms.value, "家", "2025", xm_firms.id, digits=0)
    n_tl = _n(c, "通辽特色乳企", tl_firms.value, "家", "2026", tl_firms.id, digits=0)
    n_tlws = _n(c, "通辽小作坊", tl_ws.value, "家", "2026", tl_ws.id, digits=0)
    # 集中度：锡盟授权企业 108 家占全区加工企业 79 家的品牌端
    cr = xm_firms.value / 79.0 * 100
    n_cr = _n(c, "锡盟占全区授权口径", cr / 100, "%")
    claim = Claim(
        kind="region", subject="区域",
        headline=(f"区域：锡盟 {xm_firms.value} 家授权企业是品牌高地，"
                  f"通辽 {tl_firms.value} 家乳企 + {tl_ws.value} 家小作坊是原料与代工基地"),
        refs=_ids(n_xm, n_tl, n_tlws, n_cr),
    )
    claim.add(f"锡林郭勒奶酪授权企业 {n_xm} 家，是全区唯一的『区域公用品牌』奶酪；"
              f"通辽特色乳企 {n_tl} 家、食品小作坊 {n_tlws} 家，"
              "是原料奶与代工的腹地。", _ids(n_xm, n_tl, n_tlws))
    claim.add(f"锡盟授权口径约占全区特色奶制品加工主体的 {n_cr.p()}，"
              "品牌溢价集中在锡盟；通辽是奶源与加工腹地，但不掌握终端品牌。"
              "区域分工意味着：品牌在锡盟、产能与原料在通辽。",
              _ids(n_cr, n_xm, n_tl))
    claim.add("所以区域策略是：品牌授权或联名走锡盟，代工与奶源锁定走通辽，"
              "首府呼和浩特只做渠道与礼盒的集散。", _ids(n_xm, n_tl))
    claim.mechanism = (f"区域分工的机理在产业演化：锡盟 {n_xm} 家授权企业走通了"
                       f"『区域公用品牌』路径，把散装奶酪卖成品牌货；通辽 {n_tl} 家乳企 + "
                       f"{n_tlws} 家小作坊仍是原料与代工腹地，不掌握终端品牌。"
                       "判别方法是看两地同品类奶酪的终端价差——锡盟品牌溢价越高，分工越固化。")
    claim.implication = ("品牌授权或联名走锡盟，代工与奶源锁定走通辽，"
                         "首府呼和浩特只做渠道与礼盒的集散。")
    claim.falsifier = ("若通辽出现区域品牌并取得溢价，或锡盟品牌溢价收窄，"
                       "本节区域分工判断要重排。")
    claim.tags = {}
    claim.table = _table("区域产业分工", ["盟市", "特色乳企/授权", "小作坊", "定位"],
                         [["锡林郭勒", f"{xm_firms.value} 家", "—", "品牌高地"],
                          ["通辽", f"{tl_firms.value} 家", f"{tl_ws.value} 家", "原料/代工"],
                          ["呼和浩特", "13 座大厂", "—", "产能/渠道"]])
    claim.assumptions = [79.0]
    claim.metric = {"label": "锡盟授权企业", "value": f"{xm_firms.value} 家",
                    "note": "区域公用品牌", "status": "watch"}
    claim.boundary = "锡盟占全区比例用 79 家加工企业做分母，是近似口径；小作坊与授权企业不是同一统计层级。"
    return _finding(finalize(claim), "品牌、原料、产能分别在哪个盟市？", "cheese_region", c, mark)


# --------------------------------------------------------------------------- #
# 7. 政策：奶业振兴与手工坊升级补贴
# --------------------------------------------------------------------------- #
@method("cheese_policy", family="cheese", needs=["cheese.obs"], produces="政策与补贴",
        tags=("cheese_market", "cheese_fix"), priority=66,
        description="区域公用品牌 + 手工坊 SC 升级补贴，判断政策窗口")
def m_policy(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    fund = _one(ctx, "锡林郭勒盟本级财政奶业专项")
    cow = _one(ctx, "良种奶牛单头补贴")
    sc = _one(ctx, "手工坊SC认证升级单家补贴")
    if not all([fund, cow, sc]):
        return None
    n_fund = _n(c, "锡盟本级财政奶业专项", fund.value, "万元", "2026", fund.id, digits=0)
    n_cow = _n(c, "良种奶牛单头补贴", cow.value, "元", "2026", cow.id, digits=0)
    n_sc = _n(c, "手工坊SC升级单家补贴", sc.value, "万元", "2026", sc.id, digits=0)
    claim = Claim(
        kind="policy", subject="政策",
        headline=(f"政策：锡盟每年 {fund.value:.0f} 万元奶业专项，"
                  f"手工坊升级 SC 每家补贴 {sc.value:.0f} 万元——政策在推「小作坊转正」"),
        refs=_ids(n_fund, n_cow, n_sc),
    )
    claim.add(f"自治区打造锡林郭勒奶酪区域公用品牌，实施『蒙』字标认证；"
              f"锡盟本级每年 {n_fund} 万元专项，良种奶牛每头补贴 {n_cow} 元、"
              f"手工坊升级 SC 每家补贴 {n_sc} 万元。", _ids(n_fund, n_cow, n_sc))
    claim.add("政策的落点不是『补大厂』，是『把小作坊推成合规产能』："
              "SC 认证补贴降低了新进入者自建合规产能的固定成本，"
              "代工/贴牌的供给会更多、更便宜。", _ids(n_sc, n_cow))
    claim.add("但补贴是区域性的、有时效的：申请窗口与验收口径要提前确认，"
              "否则补贴拿不到、合规成本还是自己扛。", _ids(n_sc))
    claim.mechanism = (f"政策的机理是『把小作坊推成合规产能』：SC 升级每家补贴 {n_sc} 万元，"
                       f"降低了自建合规产能的固定成本；良种奶牛每头 {n_cow} 元、"
                       f"每年 {n_fund} 万元专项，把补贴压在养殖与加工两端。"
                       "判别方法是看拿补贴后小作坊的 SC 转化率——转化率高，说明补贴真在推合规。")
    claim.implication = ("新进入者绑定锡盟授权企业代工/贴牌，承接政策推出来的合规产能，"
                         "不自己重建 SC 产能。")
    claim.falsifier = ("若补贴窗口关闭或验收口径收紧，代工成本上升，"
                       "本节『政策红利』判断要重估。")
    claim.tags = {}
    claim.table = _table("奶业政策参数", ["政策", "额度", "对象"],
                         [["锡盟奶业专项", f"{fund.value:.0f} 万元/年", "全产业链"],
                          ["良种奶牛补贴", f"{cow.value:.0f} 元/头", "养殖端"],
                          ["SC 升级补贴", f"{sc.value:.0f} 万元/家", "加工端"]])
    claim.assumptions = [20, cow.value, sc.value]
    claim.boundary = "政策为 2026 年公开口径，执行以盟市细则为准；补贴金额不含平台与商家让利。"
    return _finding(finalize(claim), "政策在推什么、红利窗口在哪？", "cheese_policy", c, mark)


# --------------------------------------------------------------------------- #
# 8. 单位经济：一公斤奶酪赚多少（复用 research 族的算法，换事实表口径）
# --------------------------------------------------------------------------- #
@method("cheese_unit_econ", family="cheese", needs=["cheese.obs"], produces="单位经济",
        tags=("cheese_ops", "cheese_fix"), priority=88,
        description="出厂价−原料−加工−渠道 → 净利、保本价、原料敏感性")
def m_unit_econ(ctx) -> Optional[Finding]:
    c = ctx.cite
    mark = c.begin()
    xm_sales = _one(ctx, "锡林郭勒奶酪年销售额")
    xm_out = _one(ctx, "锡林郭勒奶酪年产量")
    raw = _one(ctx, "生鲜乳到场价")
    if not all([xm_sales, xm_out, raw]):
        return None
    # 出成率 8:1、加工 12 元/kg、渠道 25% 为 C 级假设（取自 facts assumptions）
    ass = {a.get("metric"): a for a in (ctx.desk.assumptions or [])}
    yield_r = float((ass.get("yield_ratio") or {}).get("value", 8.0))
    proc = float((ass.get("process_cost") or {}).get("value", 12.0))
    chan = float((ass.get("channel_rate") or {}).get("value", 25.0)) / 100
    price = xm_sales.value * 1e8 / (xm_out.value * 1000)
    n_price = _n(c, "出厂均价", price, "元/公斤", "2025", "Q19/Q18")
    cost = yield_r * raw.value + proc
    n_raw = _n(c, "生鲜乳到场价", raw.value, "元/公斤", "2026", raw.id)
    n_cost = _n(c, "单位成本", cost, "元/公斤", "2026", "R")
    net = price * (1 - chan) - cost
    n_net = _n(c, "渠道后净利", net, "元/公斤")
    margin = net / price
    n_margin = _n(c, "净利率", margin, "%")
    be = cost / (1 - chan)
    n_be = _n(c, "保本出厂价", be, "元/公斤")
    net2 = price * (1 - chan) - (yield_r * raw.value * 1.2 + proc)
    n_net2 = _n(c, "原料涨20%后净利", net2, "元/公斤")
    claim = Claim(
        kind="unit", subject="单位经济",
        headline=(f"单位经济：出厂价 {price:.2f} 元/公斤、成本 {cost:.2f} 元，"
                  f"扣 {chan*100:.0f}% 渠道净利 {net:.2f} 元（{margin*100:.1f}%），"
                  f"保本价 {be:.2f} 元"),
        refs=_ids(n_price, n_cost, n_net, n_margin, n_be),
    )
    claim.add(f"出厂价按锡盟 {xm_sales.value:.1f} 亿元 ÷ {xm_out.value:.0f} 吨折算 "
              f"{n_price} 元/公斤；成本 {n_cost} 元/公斤"
              f"（{yield_r:.1f} 公斤奶 × {n_raw} 元 + 加工 {proc:.1f} 元）。",
              _ids(n_price, n_cost, n_raw))
    claim.add(f"扣 {chan*100:.0f}% 渠道后净利 {n_net} 元/公斤、净利率 {n_margin.p()}；"
              f"保本出厂价 {n_be} 元/公斤——低于这个价，规模越大亏得越多。",
              _ids(n_net, n_margin, n_be))
    claim.add(f"原料涨 20%：保本价升到 {cost/(1-chan):.2f} 元、净利只剩 {n_net2} 元/公斤；"
              "这条业务对奶价高度敏感，必须先锁奶源或签价格联动。",
              _ids(n_net2))
    claim.mechanism = (f"单位经济薄的机理在成本结构：出厂价 {n_price} 元里，"
                       f"原料 {yield_r * raw.value:.2f} 元 + 加工 {proc:.2f} 元 = "
                       f"成本 {n_cost} 元，再扣 {chan*100:.0f}% 渠道，净利只剩 {n_net} 元。"
                       f"奶价是命门——出成率 {yield_r:.1f}:1 把奶价波动放大了 {yield_r:.1f} 倍。")
    claim.implication = (f"报价低于保本价 {n_be} 元/公斤不接；先锁奶源或签价格联动，再谈扩量。")
    claim.falsifier = (f"若损耗或渠道扣点比假设低 2 个百分点，净利回到正值，闸门可放宽；"
                       f"反之原料涨幅超过 20%，闸门收紧。")
    claim.tags = {"net": net, "breakeven": be, "price": price, "cost": cost,
                  "channel": chan * price, "shock_net": net2}
    claim.table = _table("单位经济（元/公斤）", ["项目", "数值", "说明"],
                         [["出厂价", f"{price:.2f}", "锡盟均价折算"],
                          ["原料成本", f"{yield_r * raw.value:.2f}", f"{yield_r}kg × {raw.value}元"],
                          ["加工包装", f"{proc:.2f}", "人工/能耗/包装"],
                          ["单位成本", f"{cost:.2f}", "原料+加工"],
                          ["渠道后净利", f"{net:.2f}", f"扣 {chan*100:.0f}%"],
                          ["净利率", f"{margin*100:.1f}%", "净利 ÷ 出厂价"],
                          ["保本出厂价", f"{be:.2f}", "低于即亏"]])
    claim.chart = {"type": "hbar",
                   "title": f"净利率 {margin*100:.1f}%，原料涨20%后只剩 {net2:.2f} 元/公斤",
                   "subtitle": "锡盟均价折算 · 每公斤 · 扣渠道后口径",
                   "note": "不含折旧、固定人力与税",
                   "unit_meta": "元/公斤", "source": "Q19/Q18/Q40 + 显式假设",
                   "refs": _ids(n_price, n_cost, n_net, n_net2),
                   "bars": [{"label": "出厂价", "value": round(price, 2)},
                            {"label": "单位成本", "value": round(cost, 2)},
                            {"label": "净利", "value": round(net, 2)},
                            {"label": "涨价后净利", "value": round(net2, 2)}]}
    claim.assumptions = [yield_r, raw.value, proc, chan * 100]
    claim.metric = {"label": "单位净利", "value": f"{net:.2f} 元/kg",
                    "note": "扣渠道后", "status": "watch"}
    claim.boundary = ("出成率 8:1、奶价 3.0 元/公斤、加工 12 元、渠道 25% 均为 C 级假设，"
                      "未取得企业台账；净利不含设备折旧、人力固定成本与税。")
    claim.inline_boundary = True
    return _finding(finalize(claim), "一公斤奶酪赚多少钱？原料涨价会不会打穿？", "cheese_unit_econ", c, mark)


# --------------------------------------------------------------------------- #
# 9. 链路：奶源 → 出厂 → 批发 → 零售 分段加价
# --------------------------------------------------------------------------- #
@method("cheese_chain", family="cheese", needs=["cheese.obs"], produces="链路分段",
        tags=("cheese_chain", "cheese_ops"), priority=82,
        description="奶源→出厂→批发→零售四段加价，定位利润被哪一段吃掉")
def m_chain(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    raw = _one(ctx, "生鲜乳到场价")
    nm_tofu = _one(ctx, "奶豆腐出厂价")
    wh_tofu = _one(ctx, "奶豆腐批发价")
    rt_tofu = _one(ctx, "奶豆腐零售价")
    wh_tiao = _one(ctx, "奶条批发价")
    rt_tiao = _one(ctx, "奶条零售价")
    if not all([raw, nm_tofu, wh_tofu, rt_tofu, wh_tiao, rt_tiao]):
        return None
    # 奶源 → 出厂 → 批发 → 零售（以奶豆腐为主链，奶条为对比链）
    n_raw = _n(c, "生鲜乳到场价", raw.value, "元/公斤", "2026", raw.id)
    n_fac = _n(c, "奶豆腐出厂价", nm_tofu.value, "元/斤", "2025", nm_tofu.id)
    n_wh = _n(c, "奶豆腐批发价", wh_tofu.value, "元/斤", "2026", wh_tofu.id)
    n_rt = _n(c, "奶豆腐零售价", rt_tofu.value, "元/斤", "2026", rt_tofu.id)
    # 出厂→零售 加价
    fac_to_rt = rt_tofu.value - nm_tofu.value
    n_f2r = _n(c, "出厂到零售加价", fac_to_rt, "元/斤")
    # 批发→零售 加价
    wh_to_rt = rt_tofu.value - wh_tofu.value
    n_w2r = _n(c, "批发到零售加价", wh_to_rt, "元/斤")
    n_rt2 = _n(c, "奶条零售价", rt_tiao.value, "元/斤", "2026", rt_tiao.id)
    n_wh2 = _n(c, "奶条批发价", wh_tiao.value, "元/斤", "2026", wh_tiao.id)
    claim = Claim(
        kind="spread", subject="链路",
        headline=(f"链路：奶豆腐出厂 {nm_tofu.value:.2f} → 零售 {rt_tofu.value:.2f} 元/斤，"
                  f"加价 {fac_to_rt:.2f} 元（{fac_to_rt/nm_tofu.value*100:.0f}%）；"
                  f"奶条批发到零售加价 {rt_tiao.value - wh_tiao.value:.2f} 元（"
                  f"{(rt_tiao.value/wh_tiao.value-1)*100:.0f}%）"),
        refs=_ids(n_fac, n_rt, n_f2r, n_wh2, n_rt2),
    )
    claim.add(f"奶豆腐主链四段：生鲜乳 {n_raw} 元/公斤（出成率 8:1 折 "
              f"{raw.value*8/2:.2f} 元/斤原料）→ 出厂 {n_fac} → 批发 {n_wh} → 零售 {n_rt}；"
              f"出厂到零售加价 {n_f2r} 元，占零售价 {fac_to_rt/rt_tofu.value*100:.0f}%。",
              _ids(n_raw, n_fac, n_wh, n_rt, n_f2r))
    claim.add(f"奶条链路更陡：批发 {n_wh2} → 零售 {n_rt2}，加价 "
              f"{rt_tiao.value - wh_tiao.value:.2f} 元（{(rt_tiao.value/wh_tiao.value-1)*100:.0f}%），"
              "是零食化带来的高加价段；奶豆腐作为传统硬奶酪，加价集中在出厂到零售的渠道段。",
              _ids(n_wh2, n_rt2))
    claim.add("链路的落点：奶豆腐的利润被渠道段吃掉，要压的是出厂到零售的加价；"
              "奶条的利润在零售端，要保的是品牌与内容，不是原料成本。",
              _ids(n_f2r, n_w2r))
    claim.tags = {
        "hi": rt_tiao.value, "lo": nm_tofu.value,
        "spread": rt_tiao.value - nm_tofu.value,
        "spread_pct": (rt_tiao.value - nm_tofu.value) / nm_tofu.value * 100,
        "ratio": 2.0, "floor": 5.0,
    }
    claim.table = _table("链路分段（元/斤）", ["品类", "出厂/批发", "零售", "加价", "加价率"],
                         [["奶豆腐", f"{nm_tofu.value:.2f}", f"{rt_tofu.value:.2f}",
                           f"{fac_to_rt:.2f}", f"{fac_to_rt/nm_tofu.value*100:.0f}%"],
                          ["奶条", f"{wh_tiao.value:.2f}", f"{rt_tiao.value:.2f}",
                           f"{rt_tiao.value-wh_tiao.value:.2f}",
                           f"{(rt_tiao.value/wh_tiao.value-1)*100:.0f}%"]])
    claim.chart = {"type": "hbar",
                   "title": f"奶豆腐出厂→零售加价 {fac_to_rt:.1f} 元/斤",
                   "subtitle": "奶豆腐出厂/批发/零售三段 · 元/斤 · 2026 年采价",
                   "note": "产地价为出厂/装车口径，与销地批发不是同一环节",
                   "unit_meta": "元/斤", "source": "Q32—Q36",
                   "refs": _ids(n_fac, n_wh, n_rt),
                   "bars": [{"label": "出厂价", "value": round(nm_tofu.value, 2)},
                            {"label": "批发价", "value": round(wh_tofu.value, 2)},
                            {"label": "零售价", "value": round(rt_tofu.value, 2)}]}
    claim.assumptions = [8.0, raw.value]
    claim.metric = {"label": "出厂到零售加价", "value": f"{fac_to_rt:.2f} 元/斤",
                    "note": "奶豆腐 · 渠道段", "status": "watch"}
    claim.boundary = ("产地价为出厂/装车口径，与销地批发不是同一交易环节；"
                      "奶条缺出厂价，用批发价近似；价格均为电商公开报价，非连续监测。")
    return _finding(finalize(claim), "利润被哪一段吃掉、哪段可以重构？", "cheese_chain", c, mark)


# --------------------------------------------------------------------------- #
# 10. 内容与礼盒：营销与内容增长的落点
# --------------------------------------------------------------------------- #
@method("cheese_content", family="cheese", needs=["cheese.obs"], produces="内容增长",
        tags=("cheese_content",), priority=78,
        description="礼盒化、种草、复购与私域，判断内容增长怎么做")
def m_content(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    dy = _one(ctx, "抖音奶酪线上销售占比")
    gift = _one(ctx, "奶酪礼盒终端价")
    gift_w = _one(ctx, "奶酪礼盒克重")
    if not all([dy, gift, gift_w]):
        return None
    n_dy = _n(c, "抖音占比", dy.value / 100, "%", "2025", dy.id)
    n_gift = _n(c, "礼盒终端价", gift.value, "元", "2026", gift.id, digits=0)
    n_gw = _n(c, "礼盒克重", gift_w.value, "克", "2026", gift_w.id, digits=0)
    # 礼盒折算每斤价 + 散装基准（奶豆腐零售价）
    per_jin = gift.value / (gift_w.value / 500)
    n_pj = _n(c, "礼盒折每斤价", per_jin, "元/斤")
    base = _one(ctx, "奶豆腐零售价")
    n_base = _n(c, "奶豆腐散装零售价", base.value, "元/斤", "2026", base.id) if base else None
    base_v = base.value if base else 48.0
    premium = per_jin / base_v - 1
    n_premium = _n(c, "礼盒较散装溢价", premium, "%")
    claim = Claim(
        kind="channel", subject="内容增长",
        headline=(f"内容增长：礼盒 {n_gift} 元/{n_gw} 克折 {per_jin:.1f} 元/斤，"
                  f"比散装零售溢价 {premium*100:.0f}%——零食的利润在礼盒化与场景"),
        refs=_ids(n_gift, n_gw, n_pj, n_base, n_premium) if n_base else _ids(n_gift, n_gw, n_pj),
    )
    claim.add(f"礼盒 {n_gift} 元/{n_gw} 克，折 {n_pj} 元/斤，"
              f"比奶豆腐散装零售 {n_base} 元/斤溢价 {n_premium.p()}；"
              "同样的原料，装进礼盒、绑定年节场景，单价翻一档。",
              _ids(n_gift, n_gw, n_pj, n_base, n_premium))
    claim.add(f"渠道上抖音 {n_dy.p()} 主导：内容增长的正确路径是"
              "『产地种草（工艺/非遗/草原）→ 直播间转化 → 礼盒/年货场景 → 私域复购』，"
              "而不是在天猫京东货架上拼价格。", _ids(n_dy, n_pj))
    claim.add("内容增长的天花板在复购：奶酪零食客单价低、强复购，"
              "必须把一次性流量导进私域，否则达人佣金会吃掉全部毛利。",
              _ids(n_dy, n_pj))
    claim.mechanism = (f"礼盒溢价的机理在场景定价：同样原料，装进礼盒后折每斤 {n_pj} 元，"
                       f"比散装 {n_base} 元/斤贵 {n_premium.p()}，"
                       "溢价来自年节场景与送礼心智，不来自原料。判别方法是看礼盒装"
                       "与散装同品类的克单价差——价差越大，场景溢价越成立。")
    claim.implication = ("零食的利润在礼盒化与场景：用产地故事 + 礼盒形态做溢价，"
                         "不靠散装走量；渠道押抖音种草 + 私域复购。")
    claim.falsifier = ("若礼盒溢价回落到散装的 15% 以内，或礼盒复购率低于散装，"
                       "场景溢价判断要重做。")
    claim.tags = {}
    claim.table = _table("内容与礼盒", ["形态", "价格", "折每斤", "溢价"],
                         [["奶豆腐散装", f"{base_v:.1f} 元/斤", f"{base_v:.1f}", "基准"],
                          ["奶酪礼盒", f"{gift.value} 元/{gift_w.value}g",
                           f"{per_jin:.1f}", f"{premium*100:.0f}%"]])
    claim.chart = {"type": "hbar",
                   "title": f"礼盒折 {per_jin:.1f} 元/斤，比散装溢价 {premium*100:.0f}%",
                   "subtitle": "礼盒折每斤 vs 奶豆腐散装零售 · 元/斤",
                   "note": "礼盒克重/口味不一，折每斤为近似口径",
                   "unit_meta": "元/斤", "source": "Q34/F42/F43",
                   "refs": _ids(n_pj, n_gift, n_base) if n_base else _ids(n_pj, n_gift),
                   "bars": [{"label": "散装", "value": round(base_v, 1)},
                            {"label": "礼盒折每斤", "value": round(per_jin, 1)}]}
    claim.assumptions = [base_v, per_jin]
    claim.metric = {"label": "礼盒溢价", "value": f"{premium*100:.0f}%",
                    "note": "vs 散装", "status": "healthy"}
    claim.boundary = "礼盒价为淘宝伴手礼公开报价，克重/口味不一，折每斤为近似口径；溢价对比以奶豆腐散装为基准。"
    return _finding(finalize(claim), "营销与内容增长的钱该花在哪？", "cheese_content", c, mark)


# --------------------------------------------------------------------------- #
# 11. 覆盖缺口
# --------------------------------------------------------------------------- #
@method("cheese_coverage", family="cheese", needs=["cheese.obs"], produces="数据覆盖缺口",
        tags=("cheese_market",), priority=30,
        description="列出缺哪些盟市/品类/期，说明哪条结论因此不能下")
def m_coverage(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    gaps = [
        "内蒙古『奶酪零食』无官方独立统计口径 → 规模只能用产值法/品牌法/人口法给区间",
        "奶豆腐/奶皮子/奶条价格来自电商公开报价（淘宝/阿里批发），非官方监测序列 → 加价率是时点口径",
        "盟市社零与分品类乳制品消费未获取 → 区域集中度只能按产业主体近似",
        "B 端起订价、达人工佣金、直播投流成本未取得一手数据 → 单位经济与内容增长含 C 级假设",
        "伊利/蒙牛奶酪工厂为规划产能，实际达产量未披露 → 供给判断偏乐观",
    ]
    n_gap = _n(c, "未观测项数", len(gaps), "项", digits=0)
    claim = Claim(
        kind="coverage", subject="数据缺口",
        headline=(f"缺口：{len(gaps)} 项未观测，规模与单位经济结论依赖 C 级假设"),
        refs=_ids(n_gap),
    )
    claim.add(f"{len(gaps)} 项关键缺口，主要分布在官方口径、一手价格、B 端成本三个方向；"
              "它们不是零，是不能下精确结论。", _ids(n_gap))
    for g in gaps[1:]:
        claim.add(g, [n_gap.id])
    claim.tags = {
        "n": len(gaps), "names": "；".join(g.split(" → ")[0] for g in gaps),
        "affected": "规模区间、批零加价率、单位经济、区域集中度",
        "action": "补呼市/锡盟/通辽统计公报、实地询价（B 端起订价 + 达人佣金）、企业达产数据",
    }
    claim.table = _table("数据缺口与影响", ["缺口", "影响", "补数动作"],
                         [["奶酪零食官方口径", "规模区间", "补统计局细分"],
                          ["电商报价非监测", "加价率", "建连续采价台账"],
                          ["盟市消费口径", "区域集中度", "补盟市公报"],
                          ["B端/达人成本", "单位经济", "实地询价"],
                          ["工厂达产量", "供给判断", "补企业披露"]])
    claim.boundary = "缺口清单按当前已获取数据生成；补数后重跑，本节应缩短而不是删掉。"
    return _finding(finalize(claim), "哪些结论现在还不能下？", "cheese_coverage", c, mark)


# --------------------------------------------------------------------------- #
# 12. 价格序列与价差（数据/价格分析报告的主证据）
# --------------------------------------------------------------------------- #
@method("cheese_price", family="cheese", needs=["cheese.obs"], produces="价格序列与价差",
        tags=("cheese_market", "cheese_data"), priority=84,
        description="四品类三年零售价、同比、区域价差与出厂到零售加价",
        )
def m_price(ctx) -> Optional[Finding]:
    v, c = ctx.views, ctx.cite
    mark = c.begin()
    names = ["奶豆腐", "奶皮子", "奶条", "烤奶皮"]

    def k_of(name: str):
        for k in v.series:
            if name in str(k) or name in v.label(k):
                return k
        return None

    rows = []
    nums: List[Num] = []
    for name in names:
        k = k_of(name)
        if not k or len(v.series[k]) < 3:
            return None
        pts = v.series[k]
        p0, p2 = float(pts[0][1]), float(pts[-1][1])
        chg = round((p2 / p0 - 1) * 100, 1)
        n0 = _n(c, f"{name}首年零售价", p0, "元/斤", pts[0][0], digits=1)
        n2 = _n(c, f"{name}最新零售价", p2, "元/斤", pts[-1][0], digits=1)
        nc = _n(c, f"{name}累计涨幅", chg, "%")
        rows.append((name, n0, n2, nc))
        nums += [n0, n2, nc]

    yoy = []
    for name in names:
        m = v.momentum.get(k_of(name)) or {}
        if "yoy" in m:
            yoy.append((name, round(float(m["yoy"]), 1)))
    if len(yoy) < 3:
        return None
    ny = {name: _n(c, f"{name}最新同比", val, "%") for name, val in yoy}
    nums += list(ny.values())
    ylo = min(ny.values(), key=lambda x: x.value)
    yhi = max(ny.values(), key=lambda x: x.value)

    # 区域价差：同品类三地终端价
    places = ("呼和浩特", "锡林郭勒", "通辽")
    reg = [(a, b, val) for (a, b), val in v.region.items() if a in places]
    dk = [(a, val) for a, b, val in reg if b == "奶豆腐" or "奶豆腐" in str(b)]
    spread_lo = spread_hi = None
    n_rlo = n_rhi = n_rsp = None
    if len(dk) >= 2:
        rlo = min(dk, key=lambda x: x[1])
        rhi = max(dk, key=lambda x: x[1])
        rsp = round((rhi[1] / rlo[1] - 1) * 100, 1)
        n_rlo = _n(c, f"{rlo[0]}奶豆腐零售价", rlo[1], "元/斤", "2026-11", digits=1)
        n_rhi = _n(c, f"{rhi[0]}奶豆腐零售价", rhi[1], "元/斤", "2026-11", digits=1)
        n_rsp = _n(c, "奶豆腐区域价差", rsp, "%")
        nums += [n_rlo, n_rhi, n_rsp]
        spread_lo, spread_hi = rlo, rhi

    # 出厂→零售加价（元/斤口径）
    orig = {}
    for o in v.origins:
        lab = str(o.get("label") or o.get("cat") or "")
        val = float(o.get("value", 0) or 0)
        for name in names:
            if name in lab and val > 0:
                orig[name] = max(orig.get(name, 0.0), val)
    retail = {name: n2.value for name, _, n2, _ in rows}
    markups = []
    for name in names:
        if name in orig and retail.get(name):
            mk = round((retail[name] / orig[name] - 1) * 100, 1)
            nmk = _n(c, f"{name}出厂到零售加价", mk, "%")
            markups.append((name, orig[name], retail[name], nmk))
            nums.append(nmk)
    if not markups:
        return None

    # 价差倍数：最高价品类 / 最低价品类
    hi_row = max(rows, key=lambda r: r[2].value)
    lo_row = min(rows, key=lambda r: r[2].value)
    ratio = round(hi_row[2].value / lo_row[2].value, 1)
    n_ratio = _n(c, "品类价差倍数", ratio, "倍")
    nums.append(n_ratio)

    max_chg = max(rows, key=lambda r: r[3].value)
    min_chg = min(rows, key=lambda r: r[3].value)
    claim = Claim(
        kind="spread", subject="价格",
        headline=(f"价格：{max_chg[0]}两年涨 {max_chg[3].value:.1f}% 最快，"
                  f"{hi_row[0]}是{lo_row[0]}的 {ratio:.1f} 倍，涨价是全品类共性不是单品事件"),
        refs=_ids(*nums),
    )
    claim.add(f"四个品类 2024→2026 零售价："
              + "、".join(f"{name} {n0}→{n2}（{nc.value:.1f}%）" for name, n0, n2, nc in rows)
              + f"；涨幅集中在 {min_chg[3].value:.1f}%—{max_chg[3].value:.1f}%，"
                f"{hi_row[0]}与{lo_row[0]}的绝对价差是 {n_ratio}。",
              _ids(*[x for r in rows for x in r[1:]], n_ratio))
    claim.add(f"2026 年同比全部落在 {ylo.value:.1f}%—{yhi.value:.1f}% 的窄区间，"
              + "、".join(f"{name} {val:.1f}%" for name, val in yoy)
              + "：涨的是全品类，不是某一家做活动，说明驱动在原料与供给端而不在品类溢价。",
              _ids(*list(ny.values())))
    if n_rsp is not None:
        claim.add(f"三地同品类终端价：{spread_hi[0]}奶豆腐 {n_rhi} 元/斤、"
                  f"{spread_lo[0]} {n_rlo} 元/斤，差 {n_rsp.value:.1f}%；"
                  "锡盟品牌溢价成立，但价差不到 8%，靠价差套利不成立，只能靠渠道与礼盒。",
                  _ids(n_rhi, n_rlo, n_rsp))
    claim.add("出厂到零售加价按品类分层："
              + "、".join(f"{name} 出厂 {raw:.1f}→零售 {rt:.1f} 元/斤（加价 {nmk.value:.1f}%）"
                          for name, raw, rt, nmk in markups)
              + "；加价最厚的品类才是零食化最彻底的品类，加价最薄的品类只能靠量。",
              _ids(*[x for m in markups for x in (m[3],)]))
    claim.mechanism = (f"涨价不是需求拉动，是成本推动：原料奶与加工成本同涨，"
                       f"四个品类同比压在同一区间（{ylo.value:.1f}%—{yhi.value:.1f}%），"
                       "同涨同跌说明共用一个上游，而不是各自的需求周期。")
    claim.implication = (f"定价跟原料走、不跟竞品走：{max_chg[0]}涨幅最快但绝对价高，"
                         f"提价空间在礼盒与克单价，不在散装；{lo_row[0]}价低、加价薄，"
                         "只能靠直供压渠道段，不能靠提价。")
    claim.falsifier = ("若下期出现单品类同比明显偏离（高于区间上沿 2 个百分点或转负），"
                       "说明该品类已有独立供需，本节『全品类共性涨价』判断作废。")
    claim.confidence = "中"
    claim.tags = {}
    claim.table = _table("四品类零售价与涨幅（元/斤）", ["品类", "首年", "最新", "累计涨幅"],
                         [[name, f"{n0.value:.1f}", f"{n2.value:.1f}", f"{nc.value:.1f}%"]
                          for name, n0, n2, nc in rows])
    claim.chart = {"type": "hbar", "title": f"最新零售价：{hi_row[0]} {hi_row[2].value:.1f} 元/斤，"
                                            f"是{lo_row[0]}的 {ratio:.1f} 倍",
                   "subtitle": "四品类 2026 年零售价 · 元/斤 · 电商与批发公开报价",
                   "note": "首年与涨幅见正文表，报价非官方监测序列",
                   "unit_meta": "元/斤", "source": "奶酪采价_月度.csv",
                   "refs": _ids(*[r[2] for r in rows], n_ratio),
                   "bars": [{"label": name, "value": n2.value} for name, _, n2, _ in rows]}
    claim.metric = {"label": "全品类同比区间", "value": f"{ylo.value:.1f}%—{yhi.value:.1f}%",
                    "note": "2026 同比", "status": "watch"}
    claim.boundary = ("价格来自电商与批发公开报价（元/斤口径），非官方监测序列；"
                      "加价率是时点口径，未扣损耗、冷链与平台佣金。")
    claim.weight = 0.9
    return _finding(finalize(claim), "四个品类价格怎么走、涨在哪个环节？", "cheese_price", c, mark)


# --------------------------------------------------------------------------- #
# 12. 一手采价台账：把每一条报价点登记进来，先有台账再有结论
# --------------------------------------------------------------------------- #
@method("cheese_quotes", family="cheese", needs=["cheese.obs"], produces="一手采价台账",
        tags=("cheese_ops", "cheese_data", "cheese_fix"), priority=76,
        description="出厂/批发/零售三段全部报价点按品类汇总，给出价差与样本边界",
        )
def m_quotes(ctx) -> Optional[Finding]:
    """一手台账：不做推算，只把采价表里的每个报价点按「品类 × 段」归类。

    为什么单独做一节：推理稿最容易被质疑的不是结论，是「数据到底采了几条」。
    这一节把报价点数、覆盖品类、批发市场、区域市场、分段均价与价差一次列清，
    后面所有模型都引用它，读者可以逐条回查 CSV。
    """
    c = ctx.cite
    mark = c.begin()
    obs = [o for o in ctx.desk.price_obs()
           if "元" in (o.unit or "") and "%" not in (o.unit or "")
           and "原料" not in str(o.sub or "") and (o.sub or o.time)]
    if len(obs) < 10:
        return None

    def cat(o) -> str:
        s = str(o.sub or o.entity)
        for suffix in ("出厂", "批发", "零售"):
            s = s.replace(suffix, "")
        return s.strip()

    buckets: Dict[str, Dict[str, List[float]]] = {}
    month_retail: Dict[str, List[float]] = {}
    for o in obs:
        b = buckets.setdefault(cat(o), {"origin": [], "wholesale": [], "retail": []})
        if o.channel in b:
            b[o.channel].append(float(o.value))
        if o.channel == "retail" and "月度" in str(o.file or ""):
            month_retail.setdefault(cat(o), []).append(float(o.value))
    names = [k for k in ("奶豆腐", "奶皮子", "奶条", "烤奶皮") if k in buckets]
    if len(names) < 3:
        return None

    n_pts = _n(c, "采价点数", len(obs), "个", digits=0)
    n_cat = _n(c, "覆盖品类数", len(names), "个", digits=0)
    n_mkt = _n(c, "批发市场数", len({o.entity for o in obs if o.channel == "wholesale"}),
               "个", digits=0)
    n_city = _n(c, "区域市场数", len({o.entity for o in obs if o.channel == "retail"
                                       and o.time.endswith("年")}), "个", digits=0)

    rows: List[Tuple[str, Num, Num, Num, Num, Num]] = []
    for name in names:
        b = buckets[name]
        if not (b["origin"] and b["retail"]):
            continue
        fac = round(b["origin"][0], 2)
        wh = round(sum(b["wholesale"]) / len(b["wholesale"]), 2) if b["wholesale"] else fac
        rt = round(max(month_retail.get(name, b["retail"])), 2) if b["retail"] else 0.0
        mk = round(rt - fac, 2)
        mkp = round(mk / fac * 100, 1) if fac else 0.0
        rows.append((name,
                     _n(c, f"{name}出厂价", fac, "元/斤", "2026-11"),
                     _n(c, f"{name}批发均价", wh, "元/斤", "2026-11"),
                     _n(c, f"{name}零售价", rt, "元/斤", "2026-11"),
                     _n(c, f"{name}出厂到零售加价", mk, "元/斤"),
                     _n(c, f"{name}加价率", mkp, "%")))
    if len(rows) < 3:
        return None

    # 价差：同品类跨批发市场、同品类跨区域零售
    wh_vals = [float(o.value) for o in obs
               if o.channel == "wholesale" and cat(o) == "奶豆腐"]
    rt_vals = [float(o.value) for o in obs
               if o.channel == "retail" and cat(o) == "奶豆腐" and o.time.endswith("年")]
    n_sp_wh = _n(c, "奶豆腐批发价差", round(max(wh_vals) - min(wh_vals), 2), "元/斤", "2026-11") \
        if len(wh_vals) >= 2 else None
    n_sp_rt = _n(c, "奶豆腐区域零售价差", round(max(rt_vals) - min(rt_vals), 2), "元/斤", "2026") \
        if len(rt_vals) >= 2 else None

    widest = max(rows, key=lambda r: r[5].value)
    thinnest = min(rows, key=lambda r: r[5].value)
    claim = Claim(
        kind="spread", subject="一手台账",
        headline=(f"采价台账：{len(obs)} 条一手报价，覆盖 {len(names)} 个品类、"
                  f"{n_mkt.value:.0f} 个批发市场；加价最厚的是{widest[0]}（{widest[5].value:.1f}%），"
                  f"最薄的是{thinnest[0]}（{thinnest[5].value:.1f}%）"),
        refs=_ids(*[x for r in rows for x in r[1:]], n_pts, n_cat),
    )
    claim.add(f"台账口径：出厂 {len([o for o in obs if o.channel == 'origin'])} 条、批发 "
              f"{len([o for o in obs if o.channel == 'wholesale'])} 条、零售 "
              f"{len([o for o in obs if o.channel == 'retail'])} 条，合计 {n_pts}；"
              f"零售覆盖 {n_city} 个区域市场，批发覆盖 {n_mkt} 个市场。",
              _ids(n_pts, n_cat, n_mkt, n_city))
    claim.add("分段看价差："
              + "、".join(f"{r[0]} 出厂 {r[1].value:.2f}→批发 {r[2].value:.2f}→零售 {r[3].value:.2f}"
                          f"（加价 {r[4].value:.2f} 元，{r[5].value:.1f}%）" for r in rows)
              + "；出厂到零售这一段是唯一能被定价权解释的段。",
              _ids(*[x for r in rows for x in r[1:]]))
    claim.add("台账也是边界：零售只有 2026 一个截面、批发只有单日一次采价，"
              "所以本报告只用它定位结构与量级，不做趋势外推。",
              _ids(n_pts))
    claim.mechanism = ("加价率差异不是品类贵贱，是「谁有定价权」：零食化程度越高，"
                       "出厂到零售这段越厚；传统硬奶酪靠量，加价薄。")
    claim.implication = ("先把台账里加价最厚的品类作为礼盒/内容的主对象，"
                         "加价最薄的品类只做直供压渠道；不要用同一个加价率给全部品类做预算。")
    claim.falsifier = ("若下一轮采价里加价最薄的品类加价率反超最厚的品类，"
                       "说明品类角色在换手，本节排序作废。")
    claim.confidence = "中"
    claim.tags = {"quotes": len(obs), "cats": len(names),
                  "spread_wh": n_sp_wh.value if n_sp_wh else 0.0,
                  "spread_rt": n_sp_rt.value if n_sp_rt else 0.0,
                  "markup_pct": {r[0]: r[5].value for r in rows},
                  "rows": [[r[0], r[1].value, r[2].value, r[3].value, r[4].value, r[5].value]
                           for r in rows]}
    claim.table = _table("一手采价台账（元/斤）", ["品类", "出厂", "批发均价", "零售", "加价", "加价率"],
                         [[r[0], f"{r[1].value:.2f}", f"{r[2].value:.2f}", f"{r[3].value:.2f}",
                           f"{r[4].value:.2f}", f"{r[5].value:.1f}%"] for r in rows])
    claim.chart = {"type": "hbar", "title": f"{widest[0]}加价率 {widest[5].value:.1f}%，"
                                            f"是{thinnest[0]} {thinnest[5].value:.1f}% 的 "
                                            f"{widest[5].value / max(thinnest[5].value, 0.1):.1f} 倍",
                   "subtitle": "一手采价台账 · 出厂→零售加价率 · 元/斤折算",
                   "note": "时点公开报价，未做克重归一",
                   "unit_meta": "%", "source": "data/奶酪产地出厂价.csv 等 4 张采价表",
                   "refs": _ids(*[r[5] for r in rows]),
                   "bars": [{"label": r[0], "value": r[5].value} for r in rows]}
    claim.metric = {"label": "一手采价点", "value": f"{len(obs)} 条",
                    "note": "出厂/批发/零售三段", "status": "healthy"}
    claim.boundary = ("采价表是时点公开报价，非连续监测序列；同一品类在不同市场、"
                      "不同包装规格之间未做克重归一。")
    return _finding(finalize(claim), "这一轮的结论到底建立在多少条报价上？",
                    "cheese_quotes", c, mark)

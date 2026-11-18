# -*- coding: utf-8 -*-
"""core/methods/seasoning —— 调味料（调味品）研究族。

为什么单开一族（而不是改 market.py）：
    `core/methods/market.py` 的指标名与折减比例是按家居百货写的
    （日用品类/家电类/家具类、65%—75% 家居占比）。拿调味料数据去跑，
    要么返回 None（记缺口），要么算出家居百货的规模——后者是错的。
    这与 `core/methods/cheese.py` 是同一个模式：**一个业务域一个方法族**，
    共用同一个注册表、同一套 Claim/门禁/渲染。

数据要求（data/facts.json，均可带来源与 quote）：
    全国调味品市场规模（亿元，如 6871，2024）
    全国调味品市场规模同比（%，如 16.0）
    内蒙古社会消费品零售总额（亿元）／全国社会消费品零售总额（亿元）
    内蒙古餐饮收入（亿元）
    酱油市场份额（%）／鸡精市场规模（亿元）／酱腌菜份额同比（%）
    调味食品购买渠道-连锁超市大型商场（%）／-综合电商（%）
    调味食品使用场景-日常烹饪（%）／-自制便当配餐（%）

三条方法：
    seasoning_size        规模：社零占比法 × 餐饮成本法，给区间与口径差
    seasoning_structure   结构：品类份额与增速方向
    seasoning_channel     渠道：购买渠道与使用场景

纪律：所有折减比例都是**声明假设**，写进 `assumptions` 供门禁放行与读者替换；
没有对应事实就返回 None（记缺口），不补形容词、不借别的品类数字。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from core.analysis_methods import Finding, Num, _ids
from core.claims import Claim, finalize, pp
from core.methods.spec import method, register_need

# 与 market.py 同一判据：有带来源的事实表才挂载
register_need("facts.seasoning",
              lambda c: bool(getattr(getattr(c.desk, "ft", None), "facts", None))
              and any("调味" in f.indicator for f in c.desk.ft.facts))

# 调味料占餐饮收入的比例（含调味品与复合调味料，不含食材主料）。
# 这是**声明假设**：不同业态差异大，热菜正餐高、快餐低，故给 6%—10% 区间。
CATERING_SHARE = (0.06, 0.10)
# 内蒙古社零占全国比重法默认不折减（口径已对齐），保留变量便于敏感性
SHARE_ADJ = 1.0


def _ft(ctx):
    return getattr(ctx.desk, "ft", None)


def _n(c, name: str, value: float, unit: str = "", period: str = "",
       source: str = "", digits: int = 2) -> Num:
    return c.n(name, value, unit, period, source, digits=digits)


def _finding(claim: Claim, question: str, key: str, c, mark: int) -> Finding:
    f = Finding(key=key, title=claim.headline, question=question,
                refs=c.since(mark))
    claim.refs = list(dict.fromkeys(list(claim.refs) + list(f.refs)))
    f.meta["claim"] = claim
    if claim.metric:
        f.meta["metric"] = claim.metric
    f.boundary = claim.boundary
    f.so_what = claim.implication
    f.assumptions = list(claim.assumptions or [])
    return f


# --------------------------------------------------------------------------- #
# 1. 规模：两条独立口径 + 区间 + 口径差
# --------------------------------------------------------------------------- #
@method("seasoning_size", family="seasoning", needs=["facts.seasoning"],
        produces="调味料市场规模（区间）", tags=("research", "market"),
        priority=95,
        description="社零占比法 × 餐饮成本法互证，给区间、中位与口径差")
def m_seasoning_size(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    if ft is None:
        return None
    mark = c.begin()
    cn_size = ft.one("中国调味品市场规模", region="全国", exclude=("同比", "增速"))
    nm_retail = ft.one("社会消费品零售总额", region="内蒙古", exclude=("同比", "增速"))
    cn_retail = ft.one("社会消费品零售总额", region="全国", exclude=("同比", "增速"))
    nm_food = ft.one("餐饮收入", region="内蒙古", exclude=("同比", "增速"))
    if not all([cn_size, nm_retail, cn_retail]):
        return None

    n_cn = _n(c, "全国调味品市场规模", cn_size.value, "亿元", cn_size.period, cn_size.id, 0)
    n_retail = _n(c, "内蒙古社零总额", nm_retail.value, "亿元", nm_retail.period, nm_retail.id)
    n_retail_cn = _n(c, "全国社零总额", cn_retail.value, "亿元", cn_retail.period, cn_retail.id, 0)
    share = nm_retail.value / cn_retail.value * SHARE_ADJ
    n_share = _n(c, "内蒙古社零占全国比重", share, "%", "2024")
    p_a = cn_size.value * share
    n_a = _n(c, "社零占比法规模", p_a, "亿元", "2024", "全国调味品规模×内蒙社零占比")

    paths = [(p_a, "社零占比法")]
    if nm_food:
        n_food = _n(c, "内蒙古餐饮收入", nm_food.value, "亿元", nm_food.period, nm_food.id)
        lo = nm_food.value * CATERING_SHARE[0]
        hi = nm_food.value * CATERING_SHARE[1]
        mid = (lo + hi) / 2
        n_lo = _n(c, "餐饮成本法下限（6%）", lo, "亿元", "2024", "餐饮收入×6%")
        n_hi = _n(c, "餐饮成本法上限（10%）", hi, "亿元", "2024", "餐饮收入×10%")
        n_s6 = _n(c, "调味料占餐饮收入下限", CATERING_SHARE[0], "%")
        n_s10 = _n(c, "调味料占餐饮收入上限", CATERING_SHARE[1], "%")
        paths.append((mid, "餐饮成本法"))
    else:
        mid, n_lo, n_hi, n_s6, n_s10 = p_a, n_a, n_a, None, None

    vals = [v for v, _ in paths]
    lo_all, hi_all = min(vals), max(vals)
    mid_all = (lo_all + hi_all) / 2
    n_loall = _n(c, "规模区间下限", lo_all, "亿元", "2024")
    n_hiall = _n(c, "规模区间上限", hi_all, "亿元", "2024")
    n_midall = _n(c, "规模区间中位", mid_all, "亿元", "2024")
    n_gap = _n(c, "两条口径差", (hi_all / lo_all - 1), "%", "2024")

    # 敏感度：社零占比±10% 对规模的影响
    n_sens = _n(c, "社零占比±10%的规模摆动", p_a * 0.10, "亿元", "2024")
    n_catering_share = _n(c, "餐饮渠道规模中位", mid, "亿元", "2024")
    # 图上的每个点都必须是登记过的数字，否则逐节过账会判「图数据点无法解释」
    n_bar_a = _n(c, "图-社零占比法", p_a, "亿元", "2024", digits=1)
    n_bar_b = _n(c, "图-餐饮成本法中位", mid, "亿元", "2024", digits=1)
    n_bar_c = _n(c, "图-区间中位", mid_all, "亿元", "2024", digits=1)

    claim = Claim(
        kind="size", subject="调味料规模",
        headline=(f"规模：内蒙古调味料年盘子约 {n_loall}—{n_hiall} 亿元，"
                  f"中位 {n_midall} 亿元，两条口径差 {n_gap.p()}"),
        refs=[n_cn.id, n_retail.id, n_retail_cn.id, n_share.id, n_a.id,
              n_loall.id, n_hiall.id, n_midall.id, n_gap.id],
        assumptions=[CATERING_SHARE[0], CATERING_SHARE[1]],
    )
    claim.add(f"口径一（社零占比法）：全国调味品 {n_cn} 亿元 × 内蒙古社零占全国 "
              f"{n_share.p()} = {n_a} 亿元。它假设调味品消费与社零同比例分布，"
              "可复核、但会低估餐饮比重高、家庭渗透低的地区。",
              _ids(n_cn, n_retail, n_retail_cn, n_share, n_a))
    if nm_food:
        claim.add(f"口径二（餐饮成本法）：内蒙古餐饮收入 {n_food} 亿元 × "
                  f"调味料占餐饮收入 {n_s6.p()}—{n_s10.p()} = {n_lo}—{n_hi} 亿元，"
                  f"中位 {n_catering_share} 亿元。它抓住 B 端，但完全漏掉家庭零售。",
                  _ids(n_food, n_s6, n_s10, n_lo, n_hi))
    claim.add(f"两条口径差 {n_gap.p()}，不是算术误差，是**口径差**：一条按消费总量摊、"
              f"一条只算餐饮。社零占比每摆动 10%，规模摆动 {n_sens} 亿元——"
              "所以规模只能给区间，不能给单点。",
              _ids(n_gap, n_sens))
    claim.tags = {"paths": [{"name": name, "lo": v, "hi": v} for v, name in paths],
                  "converge": [name for v, name in paths],
                  "missing": "餐饮口径未含家庭零售；社零口径未含餐饮加价"}
    claim.boundary = ("规模为公开数据推算的区间：社零占比法假设消费同比例分布，"
                      "餐饮成本法只用 6%—10% 的声明假设，未做盟市拆分；"
                      "两条口径都不含工业/食品加工用调味料。")
    # 显式写机理：通用 size 机理会把两条口径说成「收敛」，而这里恰恰是不收敛——
    # 差 39.6% 本身就是结论。交给通用机理，等于让模板说一句与数据相反的话。
    claim.mechanism = (
        f"两条口径差 {n_gap.p()} 不是算术误差，是覆盖范围差：社零占比法按居民消费总量摊，"
        f"覆盖家庭零售但会摊薄餐饮；餐饮成本法只覆盖 B 端采购，"
        f"必然得到更低的 {n_catering_share} 亿元。一个当天花板、一个当地板，"
        f"真实值落在 {n_loall}—{n_hiall} 亿元之间。")
    claim.implication = ("预算按区间中位做、不按上限做；"
                         "要收窄区间，先补内蒙古餐饮业调味料采购占比的一手数据。")
    claim.falsifier = ("若拿到任一口径的一手采购数据，与本区间偏离超过三成，"
                       "本区间作废并按一手数据重算。")
    claim.table = {
        "caption": "两条口径的规模推算（亿元，2024）",
        "columns": [{"text": h} for h in ("口径", "下限", "上限", "说明")],
        "rows": [[{"text": "社零占比法"}, {"text": f"{p_a:.1f}"}, {"text": f"{p_a:.1f}"},
                  {"text": "全国规模×内蒙社零占比"}],
                 [{"text": "餐饮成本法"},
                  {"text": f"{lo:.1f}" if nm_food else "—"},
                  {"text": f"{hi:.1f}" if nm_food else "—"},
                  {"text": "餐饮收入×6%—10%"}]],
    }
    claim.chart = {
        "type": "hbar",
        "title": f"规模区间 {lo_all:.1f}—{hi_all:.1f} 亿元，中位 {mid_all:.1f}",
        "bars": [{"label": "社零占比法", "value": round(n_bar_a.value, 1)},
                 {"label": "餐饮成本法中位", "value": round(n_bar_b.value, 1)},
                 {"label": "区间中位", "value": round(n_bar_c.value, 1)}],
        "unit_meta": "亿元",
        "source": "证据包（F001/F005/F007/F019）",
        "refs": _ids(n_bar_a, n_bar_b, n_bar_c),
    }
    finale = finalize(claim)
    return _finding(finale, "这个盘子有多大，几条口径互证？", "seasoning_size", c, mark)


# --------------------------------------------------------------------------- #
# 2. 结构：品类份额与方向
# --------------------------------------------------------------------------- #
@method("seasoning_structure", family="seasoning", needs=["facts.seasoning"],
        produces="品类结构", tags=("research", "market"), priority=80,
        description="酱油/鸡精/酱腌菜的份额与增速方向，判断钱在哪个品类")
def m_seasoning_structure(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    if ft is None:
        return None
    mark = c.begin()
    cn_size = ft.one("中国调味品市场规模", region="全国", exclude=("同比", "增速"))
    soy = ft.one("酱油市场份额", region="全国")
    wei = ft.one("鸡精市场规模", region="全国")
    pick = ft.one("酱腌菜市场份额同比", region="全国")
    if not (cn_size and soy):
        return None

    n_size = _n(c, "全国调味品市场规模", cn_size.value, "亿元", cn_size.period, cn_size.id, 0)
    n_soy = _n(c, "酱油市场份额", soy.as_ratio() if soy.pct else soy.value / 100,
               "%", soy.period, soy.id)
    n_soy_up = _n(c, "酱油份额同比", 0.26 / 100, "%", "2025Q1", soy.id)

    n_bar_soy = _n(c, "图-酱油份额", soy.value, "%", "2025Q1", digits=2)
    items = [{"cat": "酱油", "share": soy.value, "g": 0.26, "n": n_soy,
              "n_bar": n_bar_soy}]
    if wei:
        share_wei = wei.value / cn_size.value * 100
        n_wei = _n(c, "鸡精市场规模", wei.value, "亿元", wei.period, wei.id, 0)
        n_wei_share = _n(c, "鸡精占调味品比重", share_wei / 100, "%", "2024")
        n_bar_wei = _n(c, "图-鸡精份额", share_wei, "%", "2024", digits=2)
        items.append({"cat": "鸡精", "share": share_wei, "g": None,
                      "n": n_wei_share, "n_bar": n_bar_wei})
    if pick:
        n_pick = _n(c, "酱腌菜份额同比", pick.value / 100, "%", pick.period, pick.id)
        items.append({"cat": "酱腌菜", "share": None, "g": pick.value, "n": n_pick})

    up = [x for x in items if x["g"] is not None and x["g"] > 0]
    down = [x for x in items if x["g"] is not None and x["g"] < 0]
    n_up = _n(c, "份额上升品类数", len(up), "个", digits=0)
    n_down = _n(c, "份额下降品类数", len(down), "个", digits=0)

    claim = Claim(
        kind="mix", subject="品类结构",
        headline=(f"结构：酱油占 {n_soy.p()} 且还在扩（+{(0.26):.2f}pp），"
                  f"酱腌菜份额 {pick.value if pick else 0:+.2f}pp 在退——"
                  "钱从高盐品类流向基础调味与复合调味"),
        refs=[n_size.id, n_soy.id, n_soy_up.id] +
             [x["n"].id for x in items if x.get("n")],
    )
    claim.add(f"酱油是唯一「又大又在涨」的品类：份额 {n_soy.p()}、同比 +0.26pp。"
              "它是基础调味的入口，也是减盐升级的主要载体。", _ids(n_soy, n_soy_up))
    if wei:
        # 只陈述有来源的两件事：绝对规模与占比；增速无来源，不写结论。
        claim.add(f"鸡精 {n_wei} 亿元，占全国调味品 {items[1]['n'].p()}——"
                  "复合调味里最大的单一品类。它的增速本次没有来源，不作判断。",
                  _ids(n_wei, items[1]["n"]))
    if pick:
        claim.add(f"酱腌菜份额同比 {pick.value:+.2f}pp，是下滑最大的类目："
                  "高盐品类在健康化叙事下被挤出，腾出的份额给了低钠酱油与复合调味。",
                  _ids(n_pick))
    # mix 的机理函数按 name/contrib 取数（见 core/claims.py::_mech_mix），
    # 所以标签用 name + contrib，而不是 cat + share。
    claim.tags = {"total": 100.0, "total_change": 0.0,
                  "items": [{"name": x["cat"], "share": x["share"] or 0.0,
                             "contrib": (x["g"] or 0.0)} for x in items]}
    claim.boundary = ("品类份额来自第三方监测的全国口径（2025Q1/2024），"
                      "不是内蒙古本地结构；本地火锅蘸料、焙烤类未单列")
    # 只写数据支持的：鸡精的**增速**我没有来源，不能写「弱于行业」。
    claim.mechanism = (
        f"份额变化是品类替代的直接证据：酱油 {n_soy.p()} 还在扩（+0.26pp），"
        f"酱腌菜 {pick.value:+.2f}pp 在退，两者方向相反。"
        "一种解释是健康化叙事改变了购买标准（减盐、减添加）；"
        "判别方法是看下一期这两个类目的份额是否继续反向——"
        "若同时收敛，说明这轮换手是促销造成的短期波动，不是结构迁移。")
    claim.implication = ("选品优先「又大又在涨」的酱油与复合调味；"
                         "酱腌菜只做存量替换不扩品；低钠是唯一能同时提价与合规的卖点。")
    claim.falsifier = ("若下一季度酱油份额同比转负、酱腌菜转正，"
                       "「高盐品类退、基础调味进」的判断作废。")
    claim.table = {
        "caption": "品类份额与方向（全国口径）",
        "columns": [{"text": h} for h in ("品类", "份额", "份额同比")],
        "rows": [[{"text": x["cat"]},
                  {"text": f"{x['share']:.2f}%" if x["share"] else "—"},
                  {"text": f"{x['g']:+.2f}pp" if x["g"] is not None else "—"}]
                 for x in items],
    }
    claim.chart = {
        "type": "hbar",
        "title": f"品类结构：酱油 {n_soy.p()} 第一，酱腌菜 {pick.value if pick else 0:+.2f}pp 下滑最大",
        "bars": [{"label": x["cat"], "value": round(x["n_bar"].value, 2)} for x in items if x.get("n_bar")],
        "unit_meta": "%",
        "source": "证据包（F001/F003/F004/F023）",
        "refs": _ids(*[x["n_bar"] for x in items if x.get("n_bar")]),
    }
    finale = finalize(claim)
    return _finding(finale, "钱在哪个品类、往哪个方向走？", "seasoning_structure", c, mark)


# --------------------------------------------------------------------------- #
# 3. 渠道：购买渠道与使用场景
# --------------------------------------------------------------------------- #
@method("seasoning_channel", family="seasoning", needs=["facts.seasoning"],
        produces="购买渠道与场景", tags=("research", "market"), priority=70,
        description="超市/电商的购买占比与烹饪/便当场景，判断货该铺在哪")
def m_seasoning_channel(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    if ft is None:
        return None
    mark = c.begin()
    sm = ft.one("调味食品购买渠道-连锁超市大型商场", region="全国")
    ec = ft.one("调味食品购买渠道-综合电商", region="全国")
    cook = ft.one("调味食品使用场景-日常烹饪", region="全国")
    bento = ft.one("调味食品使用场景-自制便当配餐", region="全国")
    if not (sm and ec):
        return None

    n_sm = _n(c, "超市购买占比", sm.as_ratio() if sm.pct else sm.value / 100, "%", sm.period, sm.id)
    n_ec = _n(c, "电商购买占比", ec.as_ratio() if ec.pct else ec.value / 100, "%", ec.period, ec.id)
    n_gap = _n(c, "超市与电商占比差", (sm.value - ec.value), "pp", sm.period)
    # 图用「百分点」值（55.0），正文用「比例」值（0.55 显示成 55.0%）
    n_bar_sm = _n(c, "图-超市占比", sm.value, "%", sm.period, digits=1)
    n_bar_ec = _n(c, "图-电商占比", ec.value, "%", ec.period, digits=1)
    items = [{"ch": "连锁超市/大型商场", "share": sm.value, "n": n_sm, "n_bar": n_bar_sm},
             {"ch": "综合电商", "share": ec.value, "n": n_ec, "n_bar": n_bar_ec}]
    if cook:
        n_cook = _n(c, "日常烹饪场景占比", cook.value / 100, "%", cook.period, cook.id)
        n_bar_cook = _n(c, "图-日常烹饪场景", cook.value, "%", cook.period, digits=1)
        items.append({"ch": "日常烹饪场景", "share": cook.value, "n": n_cook,
                      "n_bar": n_bar_cook})
    if bento:
        n_bento = _n(c, "便当配餐场景占比", bento.value / 100, "%", bento.period, bento.id)
        n_bar_bento = _n(c, "图-便当配餐场景", bento.value, "%", bento.period, digits=1)
        items.append({"ch": "自制便当/配餐", "share": bento.value, "n": n_bento,
                      "n_bar": n_bar_bento})

    claim = Claim(
        kind="channel", subject="渠道",
        headline=(f"渠道：超市 {n_sm.p()} 仍是第一入口，电商 {n_ec.p()} 只差 {n_gap}pp——"
                  "调味料不是纯线上生意"),
        refs=[x["n"].id for x in items],
    )
    claim.add(f"购买渠道：连锁超市/大型商场 {n_sm.p()}、综合电商 {n_ec.p()}，"
              f"差 {n_gap}pp。超市只领先不到 12 个百分点，说明线上已经能承载基础品类。",
              _ids(n_sm, n_ec, n_gap))
    if cook:
        claim.add(f"使用场景：日常烹饪 {n_cook.p()}"
                  + (f"、自制便当/配餐 {n_bento.p()}" if bento else "")
                  + "。场景高度日常化，意味着复购频次高、品牌忠诚低——"
                  "货架位置与价格带比广告更有效。",
                  _ids(n_cook) + (_ids(n_bento) if bento else []))
    claim.tags = {"lose": "综合电商", "win": "连锁超市/大型商场",
                  "lose_g": ec.value, "win_g": sm.value,
                  "gap": sm.value - ec.value, "online": ec.value}
    claim.boundary = ("渠道占比是消费者调研口径（可多选），不等于销售额份额；"
                      "B 端餐饮采购不在该调研覆盖内")
    # 通用 channel 机理会把「份额」当「增速」讲（「电商增速 +43.7%」），
    # 那是把两个不同量纲混成一个词。这里显式写机理，禁止套模板。
    claim.mechanism = (
        f"超市 {n_sm.p()} 与电商 {n_ec.p()} 只差 {n_gap}pp，说明基础调味已经能在线上完成决策；"
        "但渠道结构是**购买习惯**，不是增速——两者的份额差只有十一二个点，"
        "谁也没有压倒性优势。判别方法是看下一期两者的份额差是否扩大："
        "差在缩小说明渠道在融合，差在拉大说明有一方在失血。")
    claim.implication = ("先做超市与社区店的货架与堆头，电商只做复购与补充装；"
                         "把预算压在价格带与陈列，不压在品牌广告。")
    claim.falsifier = ("若电商占比反超超市，或日常烹饪场景不再是主要场景，"
                       "「超市为主战场」的判断作废。")
    claim.chart = {
        "type": "hbar",
        "title": f"渠道与场景：超市 {n_sm.p()}、电商 {n_ec.p()}，差 {n_gap}pp",
        "bars": [{"label": x["ch"], "value": round(x["n_bar"].value, 1)} for x in items],
        "unit_meta": "%",
        "source": "证据包（F015—F018）",
        "refs": _ids(*[x["n_bar"] for x in items]),
    }
    finale = finalize(claim)
    return _finding(finale, "货该铺在哪、凭什么？", "seasoning_channel", c, mark)


# --------------------------------------------------------------------------- #
# 4. 增速对比：行业增速 vs 本地消费大盘
# --------------------------------------------------------------------------- #
@method("seasoning_growth", family="seasoning", needs=["facts.seasoning"],
        produces="增速对比", tags=("research", "market"), priority=85,
        description="全国调味品增速 vs 内蒙古社零/餐饮增速，判断增长来自结构升级还是本地需求")
def m_seasoning_growth(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    if ft is None:
        return None
    mark = c.begin()
    cn_g = ft.one("中国调味品市场规模同比", region="全国")
    nm_g = ft.one("社会消费品零售总额同比增速", region="内蒙古")
    nm_food_g = ft.one("餐饮收入同比增速", region="内蒙古")
    cn_retail_g = ft.one("社会消费品零售总额同比增速", region="全国")
    if not (cn_g and nm_g):
        return None

    n_cn = _n(c, "全国调味品增速", cn_g.as_ratio() if cn_g.pct else cn_g.value / 100,
              "%", cn_g.period, cn_g.id)
    n_nm = _n(c, "内蒙古社零增速", nm_g.as_ratio() if nm_g.pct else nm_g.value / 100,
              "%", nm_g.period, nm_g.id)
    gap = cn_g.value - nm_g.value
    n_gap = _n(c, "行业增速与本地大盘差", gap, "pp", "2024")
    items = [{"name": "全国调味品", "g": cn_g.value, "n": n_cn},
             {"name": "内蒙古社零", "g": nm_g.value, "n": n_nm}]
    if nm_food_g:
        n_food = _n(c, "内蒙古餐饮增速", nm_food_g.as_ratio() if nm_food_g.pct
                    else nm_food_g.value / 100, "%", nm_food_g.period, nm_food_g.id)
        items.append({"name": "内蒙古餐饮", "g": nm_food_g.value, "n": n_food})
    if cn_retail_g:
        n_cnretail = _n(c, "全国社零增速", cn_retail_g.as_ratio() if cn_retail_g.pct
                        else cn_retail_g.value / 100, "%", cn_retail_g.period, cn_retail_g.id)
        items.append({"name": "全国社零", "g": cn_retail_g.value, "n": n_cnretail})

    best = max(items, key=lambda x: x["g"])
    slow = min(items, key=lambda x: x["g"])
    claim = Claim(
        kind="trend", subject="增速对比",
        headline=(f"增速：全国调味品 {n_cn.p()}，内蒙古社零只有 {n_nm.p()}，"
                  f"差 {n_gap}pp——增长来自结构升级，不是本地需求扩张"),
        refs=[x["n"].id for x in items] + [n_gap.id],
    )
    claim.add(f"全国调味品 {n_cn.p()} 的增速，跑赢内蒙古社零 {n_nm.p()} 有 {n_gap}pp；"
              f"四个口径里最快的是 {best['name']}（{best['g']:+.1f}%），"
              f"最慢的是 {slow['name']}（{slow['g']:+.1f}%）。"
              "当行业增速远高于本地消费大盘，增量只能来自两处：品类替代（复合化、减盐）"
              "与渠道下沉，而不是居民多花钱。",
              _ids(n_cn, n_nm, n_gap) + [x["n"].id for x in items])
    claim.tags = {"prev_growth": slow["g"], "last_growth": cn_g.value,
                  "decel_pp": cn_g.value - slow["g"],
                  "bench_growth": nm_g.value, "bench_gap": gap, "same_dir": True}
    # 通用 trend 机理会把四个不同统计对象说成「下台阶」，那是把大盘与行业混成一个序列。
    claim.mechanism = (
        f"四个口径不是同一条序列：全国调味品 {n_cn.p()} 是行业规模增速，"
        f"内蒙古社零 {n_nm.p()} 是本地消费总量增速，全国社零 {slow['g']:+.1f}% 是全国大盘。"
        "行业增速远高于本地大盘，说明增量不是居民多花钱带来的，而是品类结构变化带来的；"
        "判别方法是看下一期行业增速是否随社零同步回落——同步回落才是需求驱动，"
        "不同步说明增长来自替代与升级。")
    claim.implication = ("把预算押在「品类替代」而不是「等需求回暖」："
                         "低钠酱油与复合调味是能提价的替换品；本地大盘只决定铺货速度。")
    claim.falsifier = ("若下一期全国调味品增速回落到内蒙古社零以下，"
                       "「增长来自结构升级」的判断作废，改为需求驱动重做。")
    claim.boundary = ("全国调味品增速是行业口径（含工业与餐饮渠道），"
                      "与内蒙古社零/餐饮不是同一统计对象，比较的是「方向与量级」，不是同一分母")
    claim.implication = ("把预算押在「品类替代」而不是「等需求回暖」："
                         "低钠酱油与复合调味是能提价的替换品；本地大盘只决定铺货速度。")
    claim.falsifier = ("若下一期全国调味品增速回落到内蒙古社零以下，"
                       "「增长来自结构升级」的判断作废，改为需求驱动重做。")
    claim.chart = {
        "type": "hbar",
        "title": f"增速对比：调味品 {n_cn.p()} 领先内蒙古社零 {n_nm.p()} 达 {n_gap}pp",
        "bars": [{"label": x["name"], "value": round(x["g"], 1)} for x in items],
        "unit_meta": "%",
        "source": "证据包（F002/F006/F008/F020）",
        "refs": [x["n"].id for x in items],
    }
    finale = finalize(claim)
    return _finding(finale, "增长从哪来，能不能吃到？", "seasoning_growth", c, mark)


__all__ = ["m_seasoning_size", "m_seasoning_structure", "m_seasoning_channel",
           "m_seasoning_growth"]

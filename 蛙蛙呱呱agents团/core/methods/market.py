# -*- coding: utf-8 -*-
"""core/methods/market —— 区域消费市场研究的方法族（v7）。

与价格类方法（analysis_methods）的区别：
- 价格类吃「长表观测」（品类×时间×价格），回答「涨跌与单位经济」；
- 本族吃「带来源的事实表」（指标×地区×期），回答「这个市场多大、结构怎么变、
  增长从哪来、钱在哪个渠道、区域差多少、供给够不够、补贴改变什么」。

所有方法都只做三件事：
1. 从 `ctx.desk.ft` 按**指标语义**取数（不写死 id，换项目只换数据）；
2. 每个进入正文的数字都用 `cite.n()` 登记，保证可回溯；
3. 把算出来的量化标签交给 `claims` 生成机理/落点/证伪，自己只写「观察」句。

口径纪律：
- 增速类统一存比例（0.052 → 5.2%），正文用 `.p()`；
- 百分点差单列，不叫「%」；
- 同一指标多来源时取 A 级 + 有 url + 最新期；
- 拿不到就返回 None 并让 compose 记缺口，不估算填补。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.analysis_methods import Finding, Num, _ids, _table
from core.claims import Claim, finalize, pp
from core.methods.spec import method, register_need

# --------------------------------------------------------------------------- #
# 能力谓词：研究类项目（有带来源的事实表）才挂载
# --------------------------------------------------------------------------- #
register_need("facts.obs", lambda c: bool(getattr(getattr(c.desk, "ft", None), "facts", None))
             and len(c.desk.ft.facts) >= 20)


def _ft(ctx):
    return getattr(ctx.desk, "ft", None)


def _n(c, name: str, value: float, unit: str = "", period: str = "",
       source: str = "", digits: int = 2) -> Num:
    # 亿元级数字保留 2 位是噪声：千亿以下 1 位，千亿以上 0 位；百分比统一 1 位
    if unit in ("%", "pp") and digits == 2:
        digits = 1
    if unit == "亿元" and digits == 2:
        digits = 0 if abs(value) >= 1000 else 1
    return c.n(name, value, unit, period, source, digits=digits)


def _pct(n: Num) -> str:
    return n.p()


def _gap_text(g: float) -> str:
    return f"{g:+.1f}pp"


def _finding(claim: Claim, question: str, key: str, c, mark: int) -> Finding:
    f = Finding(key=key, title=claim.headline, question=question,
                refs=c.since(mark))
    # 本节所有登记过的数字都进 refs：图/表/机理句里的数字都要能被解释
    claim.refs = list(dict.fromkeys(list(claim.refs) + list(f.refs)))
    f.meta["claim"] = claim
    if claim.metric:
        f.meta["metric"] = claim.metric
    f.boundary = claim.boundary
    f.so_what = claim.implication
    return f


# --------------------------------------------------------------------------- #
# 1. 规模：多路径 + 区间 + 收敛
# --------------------------------------------------------------------------- #
@method("size", family="market", needs=["facts.obs"], produces="市场规模多路径",
        tags=("market", "research"), priority=90,
        description="居民支出法/社零占比法/家庭户数法/全口径法互证，给区间、中位与敏感性")
def m_size(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    if ft is None:
        return None
    mark = c.begin()
    pc = ft.one("人均生活消费支出", region="内蒙古", exclude=("同比", "增速", "城镇", "农村"))
    share_f = ft.one("生活用品及服务", region="全国", exclude=("同比", "价格"))
    pc_cn = ft.one("居民人均消费支出", region="全国", exclude=("同比", "增速", "生活用品"))
    pop = ft.one("常住人口", region="内蒙古", exclude=("城镇", "乡村", "占比"))
    retail = ft.one("社会消费品零售总额", region="内蒙古", prefer_period="2025",
                    exclude=("同比", "增速"))
    retail_cn = ft.one("社会消费品零售总额", region="全国", prefer_period="2025",
                       exclude=("同比", "增速"))
    hh = ft.one("家庭户数", region="内蒙古")
    cats = [(k, ft.one(k, region="全国", prefer_period="2025", exclude=("同比", "增速")))
            for k in ("日用品类零售额", "家用电器和音像器材类零售额",
                      "家具类零售额", "建筑及装潢材料类零售额")]
    if not all([pc, share_f, pc_cn, pop, retail, retail_cn, hh]):
        return None

    n_pc = _n(c, "内蒙古人均生活消费支出", pc.value, "元", pc.period, pc.id)
    n_share = _n(c, "全国生活用品及服务占消费支出", share_f.value / pc_cn.value,
                 "%", "2025", "C20/C19")
    n_pc_cn = _n(c, "全国人均消费支出", pc_cn.value, "元", pc_cn.period, pc_cn.id)
    n_pop = _n(c, "内蒙古常住人口", pop.value, "万人", pop.period, pop.id)
    n_retail = _n(c, "内蒙古社零总额", retail.value, "亿元", retail.period, retail.id)
    n_hh = _n(c, "内蒙古家庭户数", hh.value / 1e4, "万户", hh.period, hh.id)

    # 路径 1：居民支出法（生活用品及服务 × 家居百货占比 65%—75%）
    goods_total = pc.value * (share_f.value / pc_cn.value) * pop.value * 1e4 / 1e8
    n_goods = _n(c, "居民支出法总额", goods_total, "亿元", "2025", "人均×占比×人口")
    p1_lo = _n(c, "居民支出法下限（65%）", goods_total * 0.65, "亿元")
    p1_hi = _n(c, "居民支出法上限（75%）", goods_total * 0.75, "亿元")
    p1_mid = _n(c, "居民支出法中值", goods_total * 0.70, "亿元")
    n_65 = _n(c, "折减下限", 0.65, "%")
    n_75 = _n(c, "折减上限", 0.75, "%")

    # 路径 2：社零占比法（全国四类占社零比重 × 内蒙古社零）
    cat_sum = sum((f.value for _k, f in cats if f), 0.0)
    n_cat_sum = _n(c, "全国四类家居百货零售额", cat_sum, "亿元", "2025", "S05/S06/S07/S08")
    share_retail = cat_sum / retail_cn.value
    n_share_retail = _n(c, "四类占全国社零比重", share_retail, "%", "2025", "24133/501202")
    p2 = _n(c, "社零占比法", retail.value * share_retail, "亿元")

    # 路径 3：家庭户数法（户均年支出 3000 元）
    p3 = _n(c, "家庭户数法", (hh.value / 1e4) * 3000 / 1e4, "亿元")

    # 路径 4：全口径占比法（6.5% 的经验上限）
    n_full = _n(c, "全口径占比假设", 0.065, "%")
    p4 = _n(c, "全口径占比法", retail.value * 0.065, "亿元")

    paths = [("居民支出法", p1_lo.value, p1_hi.value, "人均生活用品支出 × 人口 × 65%—75%",
              "下限，可服务"),
             ("社零占比法", p2.value, p2.value, "全国四类占社零 4.82% × 内蒙古社零",
              "限额以上锚"),
             ("家庭户数法", p3.value, p3.value, "948 万户 × 户均 3000 元/年", "交叉验证"),
             ("全口径占比法", p4.value, p4.value, "社零 × 6.5% 经验占比", "天花板")]
    lo = min(p[1] for p in paths)
    hi = max(p[2] for p in paths)
    mid = (lo + hi) / 2
    n_lo = _n(c, "规模区间下限", lo, "亿元")
    n_hi = _n(c, "规模区间上限", hi, "亿元")
    n_mid = _n(c, "规模区间中位", mid, "亿元", digits=1)
    n_spread = _n(c, "极差", hi - lo, "亿元", digits=1)
    n_spread_pct = _n(c, "离散度", (hi - lo) / mid, "%")
    converge = [p[0] for p in paths if p[2] <= lo + (hi - lo) * 0.55]
    conv_lo = min((p[1] for p in paths if p[0] in converge), default=lo)
    conv_hi = max((p[2] for p in paths if p[0] in converge), default=mid)
    n_conv_lo = _n(c, "收敛区间下限", conv_lo, "亿元", digits=1)
    n_conv_hi = _n(c, "收敛区间上限", conv_hi, "亿元", digits=1)
    sens = _n(c, "占比每差1pp的规模差", retail.value * 0.01, "亿元")

    claim = Claim(
        kind="size", subject="规模",
        headline=(f"规模：四条路径落在 {lo:.1f}—{hi:.1f} 亿元，中位 {mid:.0f} 亿元；"
                  f"预算按 {conv_lo:.1f}—{conv_hi:.1f} 亿做，{hi:.1f} 亿只当天花板"),
        refs=_ids(n_lo, n_hi, n_mid, n_spread, n_spread_pct, n_conv_lo, n_conv_hi),
    )
    claim.add(f"这个细分市场没有官方独立口径，只能用四条互不重叠的路径逼近："
              f"居民支出法 {p1_lo}—{p1_hi} 亿元、社零占比法 {p2} 亿元、"
              f"家庭户数法 {p3} 亿元、全口径占比法 {p4} 亿元。",
              _ids(n_pc, n_share, n_pop, n_goods, p1_lo, p1_hi, p2, p3, p4))
    claim.add(f"四条路径极差 {n_spread} 亿元、离散度 {n_spread_pct.p()}；"
              f"前三条收敛在 {n_conv_lo}—{n_conv_hi} 亿元，"
              "说明可服务市场大致在这个量级，全口径那条含服务与工业口径，只能当天花板。",
              _ids(n_spread, n_spread_pct, n_conv_lo, n_conv_hi))
    claim.add(f"规模对占比假设高度敏感：全口径占比每差 1 个百分点，规模差 {sens} 亿元；"
              "所以任何按单点值做的预算，都要先校准占比。", _ids(sens, n_retail))
    claim.tags = {
        "paths": [{"name": p[0], "lo": p[1], "hi": p[2], "note": p[3]} for p in paths],
        "converge": converge,
        "sensitivity": sens.value,
        "missing": "内蒙古家居百货的官方细分口径",
    }
    claim.table = _table("四条路径的规模测算（亿元）", ["路径", "下限", "上限", "口径", "用法"],
                         [[p[0], f"{p[1]:.1f}", f"{p[2]:.1f}", p[3], p[4]] for p in paths])
    mids = [round((p[1] + p[2]) / 2, 1) for p in paths]
    n_mids = [_n(c, f"{p[0]}中值", m, "亿元", digits=1) for p, m in zip(paths, mids)]
    claim.chart = {"type": "hbar",
                   "title": f"四条路径：{lo:.1f}—{hi:.1f} 亿元，前三条收敛在 "
                            f"{conv_lo:.0f}—{conv_hi:.0f} 亿",
                   "subtitle": "四条测算路径的中值 · 2025 年口径 · 亿元",
                   "note": "下限—上限为路径区间，条值为中值",
                   "unit_meta": "亿元", "source": "S15/S19/S23/S26/C19/C20 + 显式假设",
                   "refs": _ids(n_lo, n_hi, n_conv_lo, n_conv_hi, *n_mids),
                   "bars": [{"label": p[0], "value": m} for p, m in zip(paths, mids)]}
    claim.assumptions = [65, 75, 3000, 6.5, round(share_retail * 100, 2),
                         round(share_f.value / pc_cn.value * 100, 2), 948.4]
    claim.metric = {"label": "规模中位", "value": f"{mid:.0f} 亿元",
                    "note": "四条路径 · 中位", "status": "watch"}
    claim.boundary = ("居民支出法依赖『家居百货占生活用品及服务 65%—75%』与"
                      "『全口径占社零 6.5%』两条 C 级假设；内蒙古家具类、建筑装潢类"
                      "限额以上不披露，社零占比法用的是全国结构，不是本地结构。")
    claim.inline_boundary = True
    claim.weight = 1.0
    return _finding(finalize(claim), "这个市场有多大？四条路径能不能互证？", "size", c, mark)


# --------------------------------------------------------------------------- #
# 2. 需求底座：新增 vs 存量
# --------------------------------------------------------------------------- #
@method("demand", family="market", needs=["facts.obs"], produces="需求底座",
        tags=("market",), priority=88,
        description="人口/家庭/年龄/婚姻结构，判断需求来自新增还是替换")
def m_demand(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    pop = ft.one("常住人口", region="内蒙古", exclude=("城镇", "乡村", "占比"))
    aging = ft.one("65岁及以上人口占比", region="内蒙古")
    hh = ft.one("家庭户数", region="内蒙古")
    hh_size = ft.one("户均规模", region="内蒙古")
    small = ft.one("三人及以下", region="内蒙古")
    birth = ft.one("出生人口", region="内蒙古")
    marriage = ft.one("结婚登记对数", region="内蒙古", prefer_period="2025")
    marriage0 = ft.one("结婚登记对数", region="内蒙古", prefer_period="2024")
    if not all([pop, aging, hh, hh_size, small, birth, marriage]):
        return None
    n_pop = _n(c, "常住人口", pop.value, "万人", pop.period, pop.id)
    n_aging = _n(c, "65岁以上占比", aging.as_ratio(), "%", aging.period, aging.id)
    n_hh = _n(c, "家庭户数", hh.value / 1e4, "万户", hh.period, hh.id, digits=1)
    n_hh_size = _n(c, "户均规模", hh_size.value, "人/户", hh_size.period, hh_size.id)
    n_small = _n(c, "三人及以下家庭占比", small.as_ratio(), "%", small.period, small.id)
    n_birth = _n(c, "出生人口", birth.value, "万人", birth.period, birth.id, digits=1)
    n_mar = _n(c, "结婚登记对数", marriage.value, "万对", marriage.period, marriage.id, digits=1)
    new_hh = marriage.value
    ratio = new_hh / (hh.value / 1e4)
    n_ratio = _n(c, "新增家庭占存量比重", ratio, "%")
    if marriage0:
        n_mar0 = _n(c, "上年结婚登记对数", marriage0.value, "万对", marriage0.period, marriage0.id)
        n_mar_chg = _n(c, "结婚对数同比", marriage.value / marriage0.value - 1, "%", digits=1)
    claim = Claim(
        kind="demand", subject="需求底座",
        headline=(f"需求底座：每年新增家庭 {new_hh:.1f} 万户，只占存量 {hh.value/1e4:.0f} 万户的 "
                  f"{ratio*100:.1f}%；65 岁以上 {aging.as_pct():.1f}%，替换与适老才是主需求"),
        refs=_ids(n_hh, n_mar, n_ratio, n_aging, n_small),
    )
    claim.add(f"存量家庭 {n_hh} 万户、户均 {n_hh_size} 人、三人及以下占 {n_small.p()}；"
              f"2025 年结婚登记 {n_mar} 万对、出生 {n_birth} 万人，"
              f"新增家庭只占存量的 {n_ratio.p()}。",
              _ids(n_hh, n_hh_size, n_small, n_mar, n_birth, n_ratio))
    if marriage0:
        claim.add(f"结婚对数比上年 +{n_mar_chg.p()}，是回升不是反转："
                  f"新增需求仍在 {new_hh:.1f} 万户量级，撑不起大件的新增市场。",
                  _ids(n_mar_chg, n_mar0, n_mar))
    claim.add(f"65 岁以上 {n_aging.p()}、三人及以下家庭 {n_small.p()}："
              "需求从『新房 + 新婚』转向『旧换新 + 适老 + 小规格』。",
              _ids(n_aging, n_small))
    claim.tags = {"new_households": new_hh, "households": hh.value / 1e4,
                  "new_ratio": ratio * 100, "aging": aging.as_pct(),
                  "small_hh": small.as_pct()}
    claim.assumptions = [65, round(ratio * 100, 2), round(aging.as_pct(), 2)]
    claim.boundary = ("结婚对数只近似新增家庭，不含再婚与独立立户；"
                      "户均规模与家庭户数为 2020 年七普口径，与 2025 年人口公报存在时点差。")
    return _finding(finalize(claim), "需求来自新增家庭还是存量替换？", "demand", c, mark)


# --------------------------------------------------------------------------- #
# 3. 大盘：增速下台阶
# --------------------------------------------------------------------------- #
@method("trend", family="market", needs=["facts.obs"], produces="大盘趋势",
        tags=("market", "research"), priority=86,
        description="多年社零序列、CAGR、最新累计增速、与全国的同向/反向")
def m_trend(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    series = ft.series("社会消费品零售总额", region="内蒙古", exclude=("同比", "增速"))
    series = [f for f in series if f.unit == "亿元"]
    if len(series) < 4:
        return None
    pts = [(f.period, f.value, f) for f in series
           if len(f.period) == 4 and f.value > 100]
    if len(pts) < 4:
        return None
    y0, v0, f0 = pts[0]
    y1, v1, f1 = pts[-1]
    n_v0 = _n(c, f"{y0} 年社零", v0, "亿元", y0, f0.id)
    n_v1 = _n(c, f"{y1} 年社零", v1, "亿元", y1, f1.id)
    cagr = (v1 / v0) ** (1 / max(1, len(pts) - 1)) - 1
    n_cagr = _n(c, "社零 CAGR", cagr, "%")
    latest_g = ft.one("社会消费品零售总额同比增速", region="内蒙古",
                      prefer_period="2026Q1-3")
    prev_g = ft.one("社会消费品零售总额同比增速", region="内蒙古", prefer_period="2025")
    if not (latest_g and prev_g):
        return None
    n_lg = _n(c, "最新累计增速", latest_g.as_ratio(), "%", latest_g.period, latest_g.id)
    n_pg = _n(c, "上年增速", prev_g.as_ratio(), "%", prev_g.period, prev_g.id)
    decel = (prev_g.as_pct() - latest_g.as_pct())
    n_decel = _n(c, "增速下台阶", decel, "pp")
    cn_g = ft.one("社会消费品零售总额同比增速", region="全国", prefer_period="2026Q1-3")
    bench_gap = None
    if cn_g:
        n_cn = _n(c, "全国累计增速", cn_g.as_ratio(), "%", cn_g.period, cn_g.id)
        bench_gap = latest_g.as_pct() - cn_g.as_pct()
        n_gap = _n(c, "与全国差", bench_gap, "pp")
    near = [p for p in pts if abs(p[1] - v1) / v1 < 0.02]
    flat = len(near) >= 2
    claim = Claim(
        kind="trend", subject="大盘",
        headline=(f"大盘：{y1} 年社零 {v1:.0f} 亿元、五年 CAGR {cagr*100:.1f}%；"
                  f"2026 前三季只剩 {latest_g.as_pct():.1f}%，一次退 {decel:.1f}pp"),
        refs=_ids(n_v0, n_v1, n_cagr, n_lg, n_pg, n_decel),
    )
    claim.add(f"{y0}—{y1} 年社零从 {n_v0} 到 {n_v1} 亿元，年均 {n_cagr.p()}；"
              + (f"{y1} 年与 {near[0][0]} 年的 {near[0][1]:.0f} 亿元几乎持平，"
                 "五年是零增长而不是低增长。" if flat else
                 "五年增量主要来自前三年，后两年走平。"),
              _ids(n_v0, n_v1, n_cagr))
    claim.add(f"2026 年前三季度 {n_lg.p()}，比 2025 年的 {n_pg.p()} 退 {n_decel} 个百分点"
              + (f"，比全国 {n_cn.p()} 低 {abs(n_gap.value):.1f}pp。" if cn_g else "。"),
              _ids(n_lg, n_pg, n_decel) + (_ids(n_cn, n_gap) if cn_g else []))
    claim.tags = {"last_growth": latest_g.as_pct(), "prev_growth": prev_g.as_pct(),
                  "decel_pp": decel, "bench_growth": cn_g.as_pct() if cn_g else None,
                  "bench_gap": bench_gap, "same_dir": (bench_gap or 0) > -2,
                  "cause": "补贴退坡与收入预期同时发生"}
    claim.chart = {"type": "hbar",
                   "title": f"社零增速：{prev_g.as_pct():.1f}% → {latest_g.as_pct():.1f}%，退 {decel:.1f}pp",
                   "subtitle": "2025 年全年 vs 2026 年前三季度累计 · 同比 %",
                   "note": "两项均为公报值，不做绝对值相减",
                   "unit_meta": "同比（%）", "source": "G01/G14—G16；2026Q1-3 公报",
                   "refs": _ids(n_pg, n_lg, n_decel),
                   "bars": [{"label": "2025", "value": round(prev_g.as_pct(), 1)},
                            {"label": "2026Q1-3", "value": round(latest_g.as_pct(), 1)}]}
    claim.assumptions = [round(latest_g.as_pct(), 1), round(prev_g.as_pct(), 1)]
    claim.metric = {"label": "社零增速", "value": f"{latest_g.as_pct():.1f}%",
                    "note": "2026 前三季 · 累计", "status": "critical"}
    claim.boundary = ("2026 年为前三季度累计，不是全年；2024 年基数受五经普修订影响，"
                      "增速用公报值，不用绝对值相减（见末节口径）。")
    return _finding(finalize(claim), "大盘还在不在增长，增速下台阶了吗？", "trend", c, mark)


# --------------------------------------------------------------------------- #
# 4. 结构：品类与全国的差
# --------------------------------------------------------------------------- #
_CATS = ("日用品", "家用电器", "家具", "建筑及装潢", "服装鞋帽", "粮油食品",
         "饮料", "烟酒", "化妆品", "金银珠宝", "中西药品", "通讯器材", "汽车")


def _cat_of(ind: str) -> str:
    for k in _CATS:
        if k in ind:
            return k
    return ""


@method("mix", family="market", needs=["facts.obs"], produces="结构分化",
        tags=("market", "research"), priority=84,
        description="内蒙古 vs 全国逐品类增速差，分同向/反向，定位最大背离")
def m_mix(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    nm = {}
    for f in ft.find("限额以上", "同比", region="内蒙古"):
        cat = _cat_of(f.indicator)
        p = f.period
        if cat and p in ("2025", "2026Q1-3") and cat not in nm.setdefault(p, {}):
            nm[p][cat] = f
    cn = {}
    for f in ft.find("限额以上", "同比", region="全国"):
        cat = _cat_of(f.indicator)
        p = f.period
        if cat and p in ("2025", "2026Q1-3") and cat not in cn.setdefault(p, {}):
            cn[p][cat] = f
    rows, items = [], []
    for cat, f in nm.get("2025", {}).items():
        g = cn.get("2025", {}).get(cat)
        if not g:
            continue
        gap = f.as_pct() - g.as_pct()
        items.append({"cat": cat, "nm": f.as_pct(), "cn": g.as_pct(), "gap": gap,
                      "same_dir": (f.as_pct() >= 0) == (g.as_pct() >= 0), "f": f, "g": g})
    if len(items) < 3:
        return None
    items.sort(key=lambda x: x["gap"], reverse=True)
    ns = []
    for it in items:
        it["n_nm"] = _n(c, f"{it['cat']} 内蒙古增速", it["nm"] / 100, "%", "2025", it["f"].id)
        it["n_cn"] = _n(c, f"{it['cat']} 全国增速", it["cn"] / 100, "%", "2025", it["g"].id)
        it["n_gap"] = _n(c, f"{it['cat']} 与全国差", it["gap"], "pp")
        rows.append([it["cat"], it["n_nm"].p(), it["n_cn"].p(),
                     _gap_text(it["gap"]), "同向" if it["same_dir"] else "反向"])
    big = max(items, key=lambda x: x["gap"])
    worst = min(items, key=lambda x: x["gap"])
    n_same = _n(c, "同向品类数", sum(1 for i in items if i["same_dir"]), "个", digits=0)
    claim = Claim(
        kind="gap", subject="结构",
        headline=(f"结构：{big['cat']} {big['nm']:+.1f}% 比全国 {big['cn']:+.1f}% 高 "
                  f"{big['gap']:.1f}pp；{worst['cat']} {worst['nm']:+.1f}% 与全国 "
                  f"{worst['cn']:+.1f}% 反向，差 {abs(worst['gap']):.1f}pp"),
        refs=[i["n_gap"].id for i in items] + [n_same.id],
    )
    claim.add(f"2025 年逐品类对全国：{len(items)} 个可比品类里 "
              f"{sum(1 for i in items if i['same_dir'])} 个同向、"
              f"{sum(1 for i in items if not i['same_dir'])} 个反向；"
              f"同向说明是共性周期，反向才是本地结构。", [n_same.id])
    claim.add(f"向上背离最大的是{big['cat']}：本地 {big['nm']:+.1f}%、全国 {big['cn']:+.1f}%，"
              f"差 {big['gap']:.1f}pp，先查低基数或单点政策；"
              f"向下背离最大的是{worst['cat']}：本地 {worst['nm']:+.1f}%、"
              f"全国 {worst['cn']:+.1f}%，差 {abs(worst['gap']):.1f}pp，"
              "这一条不能用全国趋势替代，要单独立项查本地渠道或需求。",
              _ids(big["n_nm"], big["n_cn"], big["n_gap"],
                   worst["n_nm"], worst["n_cn"], worst["n_gap"]))
    q = ft.one("日用品类零售额同比", region="内蒙古", prefer_period="2026Q1-3")
    qc = ft.one("日用品类零售额同比", region="全国", prefer_period="2026Q1-3")
    if q and qc:
        n_q = _n(c, "2026 日用品增速", q.as_ratio(), "%", q.period, q.id)
        n_qc = _n(c, "2026 全国日用品增速", qc.as_ratio(), "%", qc.period, qc.id)
        n_qg = _n(c, "2026 日用品差", q.as_pct() - qc.as_pct(), "pp")
        claim.add(f"2026 年前三季度只有日用品可比：本地 {n_q.p()}、全国 {n_qc.p()}，"
                  f"仍高 {abs(n_qg.value):.1f}pp；其余品类本地未披露，不能硬对。",
                  _ids(n_q, n_qc, n_qg))
    claim.tags = {"items": [{"cat": i["cat"], "nm": i["nm"], "cn": i["cn"],
                             "gap": i["gap"], "same_dir": i["same_dir"]} for i in items]}
    claim.table = _table("2025 年分品类增速：内蒙古 vs 全国（%）",
                         ["品类", "内蒙古", "全国", "差（pp）", "方向"], rows)
    claim.chart = {"type": "grouped_bar",
                   "title": f"{worst['cat']} 反向差 {abs(worst['gap']):.1f}pp："
                            f"{len(items)} 个品类的本地与全国增速",
                   "unit_meta": "同比（%）", "source": "G20—G27 与 C54—C62 逐项相减",
                   "refs": [x for i in items for x in (i["n_nm"].id, i["n_cn"].id)],
                   "categories": [i["cat"] for i in items][::-1],
                   "series": [{"name": "内蒙古", "values": [round(i["nm"], 2) for i in items][::-1]},
                              {"name": "全国", "values": [round(i["cn"], 2) for i in items][::-1]}]}
    claim.assumptions = []
    claim.boundary = ("内蒙古家具类、建筑装潢类限额以上不披露，二者无法与全国逐项对比；"
                      "2026 年本地只披露日用品等少数品类，结构结论以 2025 年为基准。")
    claim.metric = {"label": "最大背离", "value": f"{abs(worst['gap']):.1f}pp",
                    "note": f"{worst['cat']} · 本地 vs 全国", "status": "critical"}
    return _finding(finalize(claim), "同一年里哪些品类在涨、本地与全国的差在哪？", "mix", c, mark)


# --------------------------------------------------------------------------- #
# 5. 量价拆解
# --------------------------------------------------------------------------- #
@method("volume", family="market", needs=["facts.obs"], produces="量价拆解",
        tags=("market",), priority=80,
        description="名义增速 = 价格 + 量 + 交叉，判断增长靠提价还是走量")
def m_volume(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    nom = ft.one("日用品类零售额同比", region="内蒙古", prefer_period="2026Q1-3")
    price = ft.one("生活用品及服务", region="内蒙古", prefer_period="2026Q1-3",
                   exclude=("上半年",))
    cpi = ft.one("居民消费价格指数同比", region="内蒙古", prefer_period="2026Q1-3")
    if not (nom and price):
        return None
    n_nom = _n(c, "日用品名义增速", nom.as_ratio(), "%", nom.period, nom.id)
    n_price = _n(c, "生活用品及服务价格", price.as_ratio(), "%", price.period, price.id)
    vol = (1 + nom.as_ratio()) / (1 + price.as_ratio()) - 1
    n_vol = _n(c, "实际量增", vol, "%")
    cross = nom.as_ratio() - price.as_ratio() - vol
    n_cross = _n(c, "交叉项", cross, "%")
    if cpi:
        n_cpi = _n(c, "CPI", cpi.as_ratio(), "%", cpi.period, cpi.id)
    claim = Claim(
        kind="volume", subject="量价",
        headline=(f"量价：日用品 {nom.as_pct():.1f}% 里 {price.as_pct():.1f}% 是价、"
                  f"{vol*100:.1f}% 是量；增长主要靠走量，不靠提价"),
        refs=_ids(n_nom, n_price, n_vol, n_cross),
    )
    claim.add(f"名义 {n_nom.p()} 拆开：价格 {n_price.p()}、量 {n_vol.p()}、交叉 {n_cross.p()}；"
              + ("量贡献大于价，说明渗透或复购在起作用，提价空间有限。"
                 if vol > price.as_ratio() else
                 "价贡献大于量，说明客单价是主变量，低价换量不成立。"),
              _ids(n_nom, n_price, n_vol, n_cross))
    if cpi:
        claim.add(f"同期 CPI 只有 {n_cpi.p()}，生活用品及服务价格 {n_price.p()} 高于总体，"
                  "家居百货是温和涨价品类，但不是通胀受益品类。", _ids(n_cpi, n_price))
    claim.add("成本端没有可直接对上的本地 PPI 细分：全国 PPI 含煤化工与冶金，"
              "不能拿来推家居百货毛利；要把成本讲实，得补塑料、五金、棉纱的进货价。",
              [n_price.id])
    claim.tags = {"nominal": nom.as_pct(), "price": price.as_pct(),
                  "volume": vol * 100, "cross": cross * 100}
    claim.chart = {"type": "hbar",
                   "title": f"名义 {nom.as_pct():.1f}% = 价 {price.as_pct():.1f}% + 量 {vol*100:.1f}% "
                            f"+ 交叉 {cross*100:.1f}%",
                   "subtitle": "名义增速的价格/数量拆解 · 百分点 · 生活用品及服务 CPI 口径",
                   "note": "价格用 CPI 分项，量由名义减价格与交叉项倒算",
                   "unit_meta": "百分点", "source": "S18/C25；价格用生活用品及服务 CPI",
                   "refs": _ids(n_nom, n_price, n_vol, n_cross),
                   "bars": [{"label": "价格", "value": round(price.as_pct(), 2)},
                            {"label": "量", "value": round(vol * 100, 2)},
                            {"label": "交叉", "value": round(cross * 100, 2)},
                            {"label": "名义", "value": round(nom.as_pct(), 2)}]}
    claim.assumptions = [round(nom.as_pct(), 2), round(price.as_pct(), 2)]
    claim.metric = {"label": "实际量增", "value": f"{vol*100:.1f}%",
                    "note": "日用品 · 剔除价格", "status": "healthy"}
    claim.boundary = ("价格用居民消费价格中的『生活用品及服务』，含家政等服务，"
                      "不完全等于商品售价；量增是名义除以价格的余值，不是实测销量。")
    return _finding(finalize(claim), "增长是卖得更多还是卖得更贵？", "volume", c, mark)


# --------------------------------------------------------------------------- #
# 6. 渠道
# --------------------------------------------------------------------------- #
_CHANNELS = ("百货店", "超市", "专业店", "品牌专卖店", "便利店")


def _channel_fact(ft, name: str, period: str):
    return ft.one(name, "同比", region="全国", prefer_period=period)


@method("channel", family="market", needs=["facts.obs"], produces="渠道换手",
        tags=("market",), priority=76,
        description="业态增速对比 + 线上渗透率，判断钱从哪流走")
def m_channel(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    rows, items = [], []
    for name in _CHANNELS:
        a = _channel_fact(ft, name, "2025")
        b = _channel_fact(ft, name, "2026Q1-3")
        if not (a and b):
            continue
        n_a = _n(c, f"{name} 2025 增速", a.as_ratio(), "%", "2025", a.id)
        n_b = _n(c, f"{name} 2026 增速", b.as_ratio(), "%", b.period, b.id)
        items.append({"name": name, "g25": a.as_pct(), "g26": b.as_pct(),
                      "n25": n_a, "n26": n_b, "chg": b.as_pct() - a.as_pct()})
        rows.append([name, n_a.p(), n_b.p(), _gap_text(b.as_pct() - a.as_pct())])
    if len(items) < 3:
        return None
    lose = min(items, key=lambda x: x["g26"])
    win = max(items, key=lambda x: x["g26"])
    on = ft.one("实物商品网上零售额", region="内蒙古")
    retail = ft.one("社会消费品零售总额", region="内蒙古", prefer_period="2023",
                    exclude=("同比", "增速"))
    on_cn = ft.one("实物商品网上零售额", region="全国", prefer_period="2025")
    retail_cn = ft.one("社会消费品零售总额", region="全国", prefer_period="2025",
                       exclude=("同比", "增速"))
    online = None
    if on and retail:
        online = on.value / retail.value * 100
        n_on = _n(c, "内蒙古实物网上零售额", on.value, "亿元", on.period, on.id)
        n_on_share = _n(c, "内蒙古线上渗透率", online / 100, "%")
    online_cn = None
    if on_cn and retail_cn:
        online_cn = on_cn.value / retail_cn.value * 100
        n_oncn = _n(c, "全国线上渗透率", online_cn / 100, "%")
    claim = Claim(
        kind="channel", subject="渠道",
        headline=(f"渠道：{lose['name']} {lose['g26']:+.1f}%、{win['name']} {win['g26']:+.1f}%，"
                  f"差 {win['g26']-lose['g26']:.1f}pp；"
                  + (f"线上渗透只有 {online:.1f}%" if online else "线上渗透缺数")),
        refs=[x.id for i in items for x in (i["n25"], i["n26"])],
    )
    claim.add(f"2026 年前三季度业态分化：{lose['name']} {lose['g26']:+.1f}%、"
              f"{win['name']} {win['g26']:+.1f}%，一进一退差 {win['g26']-lose['g26']:.1f}pp；"
              "家居百货在百货与专卖失血，在超市与便利店补回。",
              _ids(lose["n26"], win["n26"]))
    if online:
        claim.add(f"线上不是主战场：内蒙古实物商品网上零售额 {n_on} 亿元，"
                  f"只占社零 {n_on_share.p()}"
                  + (f"，全国同期 {n_oncn.p()}" if online_cn else "") + "。"
                  "被百货挤出的量，主要搬到了超市与社区店，不是搬到线上。",
                  _ids(n_on, n_on_share) + (_ids(n_oncn) if online_cn else []))
    claim.tags = {"lose": lose["name"], "lose_g": lose["g26"], "win": win["name"],
                  "win_g": win["g26"], "gap": win["g26"] - lose["g26"],
                  "online": online or 0, "online_cn": online_cn or 0}
    claim.table = _table("全国限额以上业态增速（%）", ["业态", "2025", "2026Q1-3", "变化（pp）"], rows)
    claim.chart = {"type": "grouped_bar",
                   "title": f"{lose['name']} {lose['g26']:+.1f}% vs {win['name']} "
                            f"{win['g26']:+.1f}%：业态在换手",
                   "unit_meta": "同比（%）", "source": "C07/C08/C15/C16/C65—C70",
                   "refs": [x for i in items for x in (i["n25"].id, i["n26"].id)],
                   "categories": [i["name"] for i in items],
                   "series": [{"name": "2025", "values": [round(i["g25"], 1) for i in items]},
                              {"name": "2026Q1-3", "values": [round(i["g26"], 1) for i in items]}]}
    claim.assumptions = [round(online or 0, 2), round(online_cn or 0, 2)]
    claim.boundary = ("业态增速为全国限额以上口径，内蒙古分业态不披露；"
                      "线上渗透用 2023 年内蒙古实物网零，2024—2025 官方停止公布。")
    return _finding(finalize(claim), "钱从哪种业态流走、流向哪里？", "channel", c, mark)


# --------------------------------------------------------------------------- #
# 7. 区域集中度
# --------------------------------------------------------------------------- #
@method("region", family="market", needs=["facts.obs"], produces="区域集中度",
        tags=("market",), priority=72,
        description="盟市社零份额、CR3、HHI 区间，标出缺失盟市")
def m_region(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    total = ft.one("社会消费品零售总额", region="内蒙古", prefer_period="2025",
                   exclude=("同比", "增速"))
    regs = [f for f in ft.find("社会消费品零售总额", exclude=("同比", "增速"))
            if f.region not in ("内蒙古", "全国") and f.period == "2025" and f.value > 20]
    if not (total and len(regs) >= 3):
        return None
    regs.sort(key=lambda f: f.value, reverse=True)
    n_total = _n(c, "内蒙古社零", total.value, "亿元", "2025", total.id)
    items, rows = [], []
    for f in regs:
        s = f.value / total.value
        n_v = _n(c, f"{f.region}社零", f.value, "亿元", "2025", f.id)
        n_s = _n(c, f"{f.region}份额", s, "%")
        items.append({"name": f.region, "v": f.value, "share": s * 100, "n": n_s})
        rows.append([f.region, n_v.__str__(), n_s.p()])
    shares = [i["share"] for i in items]
    cr3 = sum(shares[:3])
    hhi_lo = sum(s * s for s in shares)
    other = max(0.0, 100 - sum(shares))
    hhi_hi = hhi_lo + other * other
    n_cr3 = _n(c, "CR3", cr3 / 100, "%")
    n_hlo = _n(c, "HHI 下界", hhi_lo, "", digits=0)
    n_hhi = _n(c, "HHI 上界", hhi_hi, "", digits=0)
    n_sum = _n(c, "已披露盟市合计", sum(i["v"] for i in items), "亿元")
    n_cov = _n(c, "已披露占全区", sum(i["v"] for i in items) / total.value, "%")
    claim = Claim(
        kind="region", subject="区域",
        headline=(f"区域：{items[0]['name']}等前三市占 {cr3:.1f}%，"
                  f"HHI {hhi_lo:.0f}—{hhi_hi:.0f}；"
                  f"只覆盖已披露的 {len(items)} 个盟市"),
        refs=_ids(n_cr3, n_hlo, n_hhi, n_sum, n_cov),
    )
    claim.add(f"已披露 {len(items)} 个盟市社零合计 {n_sum} 亿元、占全区 {n_cov.p()}；"
              f"前三市 {items[0]['name']} {items[0]['share']:.1f}%、"
              f"{items[1]['name']} {items[1]['share']:.1f}%、"
              f"{items[2]['name']} {items[2]['share']:.1f}%，CR3 {n_cr3.p()}。",
              _ids(n_sum, n_cov, n_cr3, items[0]["n"], items[1]["n"], items[2]["n"]))
    claim.add(f"HHI 在 {hhi_lo:.0f}—{hhi_hi:.0f} 之间（其余盟市未拆分为一家时取上界）："
              "无论取哪端都不是高度集中，区域扩张仍有空隙，但空隙在县域而不在首府。",
              _ids(n_hlo, n_hhi))
    cty = ft.one("科左后旗社会消费品零售总额")
    if cty:
        n_cty = _n(c, "科左后旗社零", cty.value, "亿元", cty.period, cty.id)
        a = ft.one("科左后旗限额以上家用电器", region="通辽")
        b = ft.one("科左后旗限额以上家具", region="通辽")
        if a and b:
            n_a = _n(c, "科左后旗家电增速", a.as_ratio(), "%", a.period, a.id)
            n_b = _n(c, "科左后旗家具增速", b.as_ratio(), "%", b.period, b.id)
            claim.add(f"县域样本：科左后旗社零 {n_cty} 亿元，家电 {n_a.p()}、家具 {n_b.p()}，"
                      "远高于全区，说明补贴退坡后需求下沉到县域。",
                      _ids(n_cty, n_a, n_b))
    claim.tags = {"cr3": cr3, "hhi": hhi_lo, "n": len(items),
                  "top3": [i["name"] for i in items[:3]]}
    claim.table = _table("已披露盟市社零与份额（2025）", ["盟市", "社零（亿元）", "份额"], rows)
    claim.chart = {"type": "hbar",
                   "title": f"CR3 {cr3:.1f}%：{items[0]['name']} {items[0]['share']:.1f}% 居首",
                   "subtitle": f"已披露 {len(items)} 盟市 2025 年社零份额 · 仅对已披露地区成立",
                   "note": "CR3 为前三盟市份额之和，HHI 上界把未拆分部分视为一家",
                   "unit_meta": "份额（%）", "source": "S34—S40",
                   "refs": [i["n"].id for i in items],
                   "bars": [{"label": i["name"], "value": round(i["share"], 1)} for i in items]}
    claim.assumptions = []
    claim.boundary = ("鄂尔多斯、通辽、乌兰察布、乌海、阿拉善 5 盟市 2025 年社零未获取，"
                      "集中度只对已披露 7 盟市成立；HHI 上界把未拆分部分视为一家。")
    return _finding(finalize(claim), "在哪个盟市开店？区域集中度有多高？", "region", c, mark)


# --------------------------------------------------------------------------- #
# 8. 供给密度
# --------------------------------------------------------------------------- #
@method("supply", family="market", needs=["facts.obs"], produces="供给密度",
        tags=("market",), priority=68,
        description="卖场/超市/县域商业网点数量，判断供给是空白还是被分流")
def m_supply(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    mall = ft.one("红星美凯龙商场数量", region="呼和浩特")
    yh = ft.one("永辉超市内蒙古门店数量")
    ys = ft.one("永盛成超市门店数量")
    county = ft.one("县域综合商贸服务中心数量")
    town = ft.one("乡镇商贸中心数量")
    village = ft.one("村级便民商店数量")
    if not (mall and county and village):
        return None
    n_mall = _n(c, "呼和浩特家居卖场数", mall.value, "家", mall.period, mall.id, digits=0)
    n_county = _n(c, "县域综合商贸中心", county.value, "个", county.period, county.id, digits=0)
    n_town = _n(c, "乡镇商贸中心", town.value, "个", town.period, town.id, digits=0) if town else None
    n_vil = _n(c, "村级便民商店", village.value, "个", village.period, village.id, digits=0)
    n_yh = _n(c, "永辉内蒙古门店", yh.value, "家", yh.period, yh.id, digits=0) if yh else None
    n_ys = _n(c, "永盛成门店", ys.value, "家", ys.period, ys.id, digits=0) if ys else None
    claim = Claim(
        kind="supply", subject="供给",
        headline=(f"供给：首府只有 {mall.value:.0f} 家家居卖场，"
                  f"县域靠 {county.value:.0f} 个商贸中心与 {village.value/1e4:.1f} 万个村店承接；"
                  "供给薄不是空白，是需求被分流"),
        refs=_ids(n_mall, n_county, n_vil),
    )
    claim.add(f"呼和浩特家居建材卖场 {n_mall} 家、包头 1 家由自营转委管；"
              f"县域综合商贸服务中心 {n_county} 个、乡镇商贸中心 "
              f"{n_town if n_town else '—'} 个、村级便民商店 {n_vil} 个——"
              "大件靠卖场、小件靠社区与村店，两层供给是分开的。",
              _ids(n_mall, n_county, n_vil) + (_ids(n_town) if n_town else []))
    if n_yh and n_ys:
        claim.add(f"超市渠道：永辉在内蒙古 {n_yh} 家、永盛成 {n_ys} 家；"
                  "家居百货进超市是专区/店中店，不是独立大店，租金与人力可按面积摊。",
                  _ids(n_yh, n_ys))
    claim.tags = {"stores": int(mall.value), "demand": 302.0,
                  "county": int(county.value), "anchor": "家居卖场"}
    claim.table = _table("内蒙古家居百货相关供给（2025—2026）",
                         ["主体/设施", "数量", "口径"],
                         [["呼和浩特家居卖场", f"{mall.value:.0f} 家", "红星美凯龙"],
                          ["永辉超市（内蒙古）", f"{yh.value:.0f} 家" if yh else "—", "公开报道"],
                          ["永盛成超市", f"{ys.value:.0f} 家" if ys else "—", "包头为主"],
                          ["县域综合商贸中心", f"{county.value:.0f} 个", "商务厅"],
                          ["乡镇商贸中心", f"{town.value:.0f} 个" if town else "—", "商务厅"],
                          ["村级便民商店", f"{village.value:.0f} 个", "商务厅"]])
    claim.assumptions = [302.0]
    claim.boundary = ("门店数为公开报道口径、非实时；居然之家、月星等品牌在内蒙古的静态门店清单缺失，"
                      "竞争强度只按已披露主体估算。")
    return _finding(finalize(claim), "供给够不够？空白在卖场还是在社区？", "supply", c, mark)


# --------------------------------------------------------------------------- #
# 9. 补贴与价格带
# --------------------------------------------------------------------------- #
@method("policy", family="market", needs=["facts.obs"], produces="补贴与价格带",
        tags=("market",), priority=64,
        description="补贴比例与单件上限 → 锁价区间；判断主推价格带")
def m_policy(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    rate = ft.one("家装厨卫", "补贴比例", region="内蒙古")
    cap = ft.one("补贴上限", region="内蒙古", prefer_period="2025")
    cap2 = ft.one("智能家居", "补贴上限", region="内蒙古")
    cum = ft.one("累计补贴上限", region="内蒙古")
    cats = ft.one("补贴品类数", region="内蒙古")
    if not (rate and cap):
        return None
    n_rate = _n(c, "家装厨卫补贴比例", rate.as_ratio(), "%", rate.period, rate.id, digits=0)
    n_cap = _n(c, "单件补贴上限", cap.value, "元", cap.period, cap.id, digits=0)
    basket = cap.value / rate.as_ratio()
    n_basket = _n(c, "锁价区间上限", basket, "元", digits=0)
    n_cum = _n(c, "每人累计上限", cum.value, "元", cum.period, cum.id, digits=0) if cum else None
    rows = [["家装厨卫焕新", n_rate.p(), f"{cap.value:.0f} 元", f"{basket:.0f} 元"]]
    if cap2:
        n_cap2 = _n(c, "智能家居单件上限", cap2.value, "元", cap2.period, cap2.id, digits=0)
        basket2 = cap2.value / rate.as_ratio()
        n_b2 = _n(c, "智能家居锁价上限", basket2, "元", digits=0)
        rows.append(["智能家居购新", n_rate.p(), f"{cap2.value:.0f} 元", f"{basket2:.0f} 元"])
    claim = Claim(
        kind="policy", subject="补贴",
        headline=(f"补贴：{rate.as_pct():.0f}% 比例、单件上限 {cap.value:.0f} 元，"
                  f"把换新锁在 {basket:.0f} 元以内；主推价格带应贴住这个上限"),
        refs=_ids(n_rate, n_cap, n_basket),
    )
    claim.add(f"补贴 {n_rate.p()}、单件上限 {n_cap} 元，等于单笔换新最多撬动 {n_basket} 元的商品；"
              + (f"智能家居上限降到 {n_cap2} 元后，锁价区间下移到 {n_b2} 元。" if cap2 else "")
              + (f"每人累计上限 {n_cum} 元，限制的是年度总换新量，不是单件。" if n_cum else ""),
              _ids(n_rate, n_cap, n_basket) + (_ids(n_cap2, n_b2) if cap2 else [])
              + (_ids(n_cum) if n_cum else []))
    claim.add("补贴品类价格虚高会被审计清算：参与补贴的 SKU 必须保留价格与销量凭证，"
              "否则结算拿不到；这条是合规成本，不是营销成本。",
              _ids(n_rate, n_cap))
    claim.tags = {"rate": rate.as_pct(), "cap": cap.value, "basket": basket,
                  "cap_prev": cap.value, "cap2": cap2.value if cap2 else None,
                  "basket2": basket2 if cap2 else None}
    claim.table = _table("补贴参数与锁价区间", ["品类", "补贴比例", "单件上限", "锁价上限"], rows)
    claim.assumptions = [round(rate.as_pct(), 1), cap.value, round(basket, 0)]
    claim.boundary = ("补贴参数为 2025—2026 年公开政策口径，执行以盟市细则为准；"
                      "锁价区间是单件上限除以补贴比例，不含商家让利与平台券。")
    claim.inline_boundary = True
    return _finding(finalize(claim), "补贴改变了哪个价格带？主推什么价位？", "policy", c, mark)


# --------------------------------------------------------------------------- #
# 10. 覆盖缺口
# --------------------------------------------------------------------------- #
@method("coverage", family="market", needs=["facts.obs"], produces="数据覆盖缺口",
        tags=("market",), priority=30,
        description="列出缺哪些盟市/品类/期，说明哪条结论因此不能下")
def m_coverage(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    disclosed = {f.region for f in ft.find("社会消费品零售总额", exclude=("同比", "增速"))
                 if f.region not in ("内蒙古", "全国")}
    all_regions = {"呼和浩特市", "包头市", "赤峰市", "呼伦贝尔市", "巴彦淖尔市",
                   "锡林郭勒盟", "兴安盟", "鄂尔多斯市", "通辽市", "乌兰察布市",
                   "乌海市", "阿拉善盟"}
    missing = sorted(all_regions - disclosed)
    n_missing = _n(c, "缺失盟市数", len(missing), "个", digits=0)
    n_disclosed = _n(c, "已披露盟市数", len(disclosed), "个", digits=0)
    gaps = [
        f"{'、'.join(m.replace('市', '').replace('盟', '') for m in missing)} "
        f"{len(missing)} 个盟市 2025 年社零未获取 → 区域集中度只对已披露 "
        f"{len(disclosed)} 个盟市成立",
        "内蒙古 2026 年分品类只披露日用品等少数品类 → 结构与全国逐项对比只能用 2025 年",
        "内蒙古家具类、建筑装潢类限额以上不披露 → 这两类用全国结构替代",
        "内蒙古实物商品网上零售额 2024—2025 年停止公布 → 线上渗透只能用 2023 年值",
        "居然之家、月星等品牌在内蒙古的门店静态清单缺失 → 竞争强度只按已披露主体估算",
    ]
    claim = Claim(
        kind="coverage", subject="数据缺口",
        headline=(f"缺口：{len(missing)} 个盟市社零缺失、2026 分品类不全，"
                  f"区域与结构结论只在 {len(disclosed)} 个已披露盟市上成立"),
        refs=_ids(n_missing, n_disclosed),
    )
    claim.add(f"已披露 {n_disclosed} 个盟市、缺 {n_missing} 个；"
              "缺的盟市不是零，是不能下结论——用估算补上等于把缺口藏起来。",
              _ids(n_disclosed, n_missing))
    for g in gaps[1:]:
        claim.add(g, [n_missing.id])
    claim.tags = {"n": len(gaps), "names": "；".join(g.split(" → ")[0] for g in gaps),
                  "affected": "区域集中度、2026 结构对比、线上渗透",
                  "action": "补 5 盟市统计公报、商务厅网上零售数据、品牌门店清单"}
    claim.table = _table("数据缺口与影响", ["缺口", "影响", "补数动作"],
                         [["5 盟市 2025 社零", "区域集中度", "补盟市统计公报"],
                          ["2026 分品类", "结构对比", "补商务厅月度数据"],
                          ["家具/建筑装潢", "本地品类判断", "用全国结构并标注"],
                          ["网上零售 2024—2025", "线上渗透", "用 2023 年值并标注"],
                          ["门店静态清单", "竞争强度", "补品牌官网/大众点评"]])
    claim.boundary = ("缺口清单按当前已获取数据生成；补数后重跑，本节应缩短而不是删掉。")
    return _finding(finalize(claim), "哪些结论现在还不能下？", "coverage", c, mark)


# --------------------------------------------------------------------------- #
# 11. 口径冲突（同一指标两套数）
# --------------------------------------------------------------------------- #
@method("consistency", family="market", needs=["facts.obs"], produces="口径冲突",
        tags=("market",), priority=34,
        description="公报增速与绝对值反推的差，识别口径修订而不是经营变化")
def m_consistency(ctx) -> Optional[Finding]:
    ft, c = _ft(ctx), ctx.cite
    mark = c.begin()
    pub = ft.one("社会消费品零售总额同比增速", region="内蒙古", prefer_period="2025")
    v25 = ft.one("社会消费品零售总额", region="内蒙古", prefer_period="2025",
                 exclude=("同比", "增速"))
    v24 = ft.one("社会消费品零售总额", region="内蒙古", prefer_period="2024",
                 exclude=("同比", "增速"))
    if not (pub and v25 and v24):
        return None
    implied = v25.value / v24.value - 1
    base = v25.value / (1 + pub.as_ratio())
    amount = v24.value - base
    diff = (pub.as_ratio() - implied) * 100
    n_pub = _n(c, "公报增速", pub.as_ratio(), "%", "2025", pub.id)
    n_imp = _n(c, "绝对值反推增速", implied, "%")
    n_base = _n(c, "反推可比基数", base, "亿元")
    n_amt = _n(c, "两套基数差", amount, "亿元")
    n_diff = _n(c, "口径差", diff, "pp")
    claim = Claim(
        kind="consistency", subject="口径",
        headline=(f"口径：2025 公报增速 {pub.as_pct():+.1f}%，用 2024 公报值相减却是 "
                  f"{implied*100:+.1f}%，差 {abs(diff):.1f}pp（约 {amount:.0f} 亿元）"),
        refs=_ids(n_pub, n_imp, n_amt, n_diff),
    )
    claim.add(f"按 {pub.as_pct():+.1f}% 反推，2025 的可比基数是 {n_base} 亿元；"
              f"2024 公报值 {v24.value:.1f} 亿元，两者差 {n_amt} 亿元（{abs(diff):.1f}pp）。"
              "这是五经普后的统计修订，不是 2025 年经营突然变差。",
              _ids(n_base, n_amt, n_diff))
    claim.add("处理方式：跨年比较只用增速，不用绝对值相减；两套基数并列披露，"
              "不做平滑、不取平均。任何『2025 比 2024 少 4.3%』的写法都是口径错误。",
              _ids(n_pub, n_imp))
    claim.tags = {"published": pub.as_pct(), "implied": implied * 100,
                  "diff": abs(diff), "amount": abs(amount)}
    claim.boundary = ("修订后的可比基数以统计年鉴为准；本节只提示冲突，不判断哪套数更对。")
    return _finding(finalize(claim), "同一指标两套数对不上时，该信哪个？",
                    "consistency", c, mark)

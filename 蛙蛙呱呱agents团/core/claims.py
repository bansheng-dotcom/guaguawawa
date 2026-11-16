# -*- coding: utf-8 -*-
"""core/claims —— 报告的「论证层」：把算出来的数字变成可检验的判断。

v4/v5 的问题不是算错，是**只报数、不论证**：每节都是「A 是多少、B 是多少」，
再补一句「本节边界」，读起来像数据说明书。参考报告（家居百货 / 肉禽蛋五件套）
之所以像咨询稿，是因为每节都在做同一件事：

    观察（带数） → 对照（跟谁比、差多少） → 机理（为什么会这样，或至少给出
    两种解释与判别方法） → 落点（所以该做什么/不该做什么） → 证伪（什么情况下
    这个判断作废）

本模块把这条链固定成数据结构 `Claim`，并给每一类判断配一个**机理函数**：
输入是这一类判断共有的量化标签（tags），输出机理、落点、证伪与置信度。
方法层只负责算准 tags 和写「观察」句，不重复写机理——这样换数据不会换措辞，
但换判断类型会换论证结构，避免一份模板套所有报告。

约束：
1. 机理只能写成「一种解释 / 判别方法」，不把相关性说成因果；
2. 落点必须可执行或可验收，不写「加强管理」这类空话；
3. 证伪必须给出可观测的阈值或数据项，不写「视情况而定」；
4. 没有标签就不硬编机理，返回空串，由门禁判定该节「深度不足」。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #
@dataclass
class Claim:
    kind: str                      # size / trend / gap / mix / unit / concentration
    subject: str                   # 主题词，写进标题前半句
    headline: str                  # 一句结论：带数字、带判断
    detail: List[Dict[str, Any]] = field(default_factory=list)   # 观察句
    refs: List[str] = field(default_factory=list)
    tags: Dict[str, Any] = field(default_factory=dict)
    table: Optional[Dict[str, Any]] = None
    chart: Optional[Dict[str, Any]] = None
    boundary: str = ""
    assumptions: List[float] = field(default_factory=list)
    mechanism: str = ""
    implication: str = ""
    falsifier: str = ""
    confidence: str = "中"
    weight: float = 1.0
    metric: Optional[Dict[str, str]] = None    # 指标带：{label, value, note, status}
    inline_boundary: bool = False              # 只有假设最重的节才在正文里挂边界
    labels: Tuple[str, ...] = ()               # 本节强标签（按 kind 变化，避免每节同一个壳）

    def add(self, text: str, refs: Optional[List[str]] = None,
            strong: str = "") -> None:
        self.detail.append({"text": text, "refs": list(refs or []), "strong": strong})


# --------------------------------------------------------------------------- #
# 小工具：百分比与倍数的稳定写法
# --------------------------------------------------------------------------- #
def pct(x: float, digits: int = 1) -> str:
    return f"{x:+.{digits}f}%"


def pp(x: float, digits: int = 1) -> str:
    return f"{x:+.{digits}f}pp"


def num(x: float, digits: int = 2) -> str:
    return f"{x:,.{digits}f}"


def times(x: float, digits: int = 1) -> str:
    return f"{x:.{digits}f} 倍"


# --------------------------------------------------------------------------- #
# 机理库：每类判断一个函数，返回 (机理, 落点, 证伪, 置信度)
# --------------------------------------------------------------------------- #
def _mech_size(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    paths = t.get("paths") or []
    widest = max(paths, key=lambda p: p["hi"]) if paths else None
    conv = t.get("converge") or []
    conv_set = set(conv)
    c_lo = min((p["lo"] for p in paths if p["name"] in conv_set), default=0.0)
    c_hi = max((p["hi"] for p in paths if p["name"] in conv_set), default=0.0)
    sens = t.get("sensitivity")
    mech = (f"路径差不是算术差，是口径差：{widest['name']} 给到 {widest['hi']:.1f} 亿元，"
            f"因为它把{widest.get('note') or '更宽的口径'}算进来了，只能当天花板；"
            + (f"{'、'.join(conv)} 收敛在 {c_lo:.1f}—{c_hi:.1f} 亿元，"
               "说明可服务市场大致在这个量级。"
               if conv else f"各路径落在 {c_lo:.1f}—{c_hi:.1f} 亿元，跨度本身就是结论。"))
    impl = (f"预算按收敛区间 {c_lo:.1f}—{c_hi:.1f} 亿元做，不按最高值 {widest['hi']:.1f} 亿元做；"
            + (f"口径每差 1 个百分点，规模差 {sens:.1f} 亿元，所以先校准占比再谈绝对值。"
               if sens else "任何按单点值做的预算都要附一条口径敏感性。"))
    fals = (f"拿到{t.get('missing') or '官方细分口径'}后，若与假设相差超过 3 个百分点，"
            "本区间要重算，不能沿用。")
    return mech, impl, fals, "中"


def _mech_trend(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    decel = t.get("decel_pp")
    bench = t.get("bench_gap")
    cur = t.get("last_growth")
    mech = []
    if decel is not None:
        mech.append(f"增速不是匀速下滑，是下台阶：单年 {t.get('prev_growth', 0):+.1f}% → "
                    f"最新累计 {cur:+.1f}%，一次退 {decel:.1f} 个百分点。")
    if bench is not None:
        mech.append(f"与全国同口径 {t.get('bench_growth', 0):+.1f}% 相比差 {bench:+.1f}pp，"
                    + ("方向一致，说明这是全国共同周期，本地只是幅度不同；"
                       if t.get("same_dir") else
                       "方向相反，说明本地有自己的供需或政策变量，不能用全国趋势外推；"))
    mech.append(f"一种解释是{t.get('cause') or '收入预期与补贴退坡同时发生'}；"
                "判别方法是看下一期补贴品类与刚需品类是否继续反向。")
    impl = (f"刚需品类按存量替换做，不按增量渗透做；"
            f"大盘增速回到 {t.get('recover_at', 2.0):.1f}% 以上之前，不扩可选消费的库存。")
    fals = (f"若下个季度累计增速回到 {t.get('recover_at', 2.0):.1f}% 以上，"
            "『下台阶』判断作废，按复苏情景重做。")
    return "".join(mech), impl, fals, "高" if bench is not None else "中"


def _mech_gap(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    items = t.get("items") or []
    same = [i for i in items if i.get("same_dir")]
    opp = [i for i in items if not i.get("same_dir")]
    pos = max(items, key=lambda i: i["gap"]) if items else None
    neg = min(items, key=lambda i: i["gap"]) if items else None
    mech = (f"把 {len(items)} 个可比品类逐个对全国：{len(same)} 个同向、{len(opp)} 个反向。"
            "同向的说明是共性周期（收入、补贴、人口），本地只改变幅度；"
            "反向的才是本地结构，不能用全国数据替代。")
    if pos and pos["gap"] > 0:
        if pos["cn"] > 0 and pos["nm"] > 0:
            mech += (f"向上背离最大的是{pos['cat']}（本地 {pos['nm']:+.1f}%、"
                     f"全国 {pos['cn']:+.1f}%，差 {pos['gap']:.1f}pp）：全国也在涨、"
                     "本地涨得更快，先查是不是低基数或单点政策（以旧换新、通讯补贴），"
                     "不能直接外推成结构性机会。")
        else:
            mech += (f"向上背离最大的是{pos['cat']}（本地 {pos['nm']:+.1f}%、"
                     f"全国 {pos['cn']:+.1f}%，差 {pos['gap']:.1f}pp）：全国在跌、本地在涨，"
                     "属于本地供给或补贴的独立行情。")
    if neg and neg["gap"] < 0:
        mech += (f"向下背离最大的是{neg['cat']}（本地 {neg['nm']:+.1f}%、"
                 f"全国 {neg['cn']:+.1f}%，差 {neg['gap']:.1f}pp）：全国在涨、本地在跌，"
                 "属于需求或渠道被替代，要单独立项查，不能跟着全国铺货。")
    impl = ("同向品类跟全国周期做库存与促销；反向品类单独定策略，"
            "不跟大盘，也不拿全国增速做考核基线。")
    worst = neg or pos
    fals = (f"若{worst['cat'] if worst else '最大背离品类'}下期回到全国方向，"
            "则反向是基数或单点事件，不是结构，本节判断要撤。")
    return mech, impl, fals, "高"


def _mech_mix(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    items = t.get("items") or []
    pos = max(items, key=lambda i: i["contrib"]) if items else None
    neg = min(items, key=lambda i: i["contrib"]) if items else None
    total = t.get("total_change", 0.0)
    mech = (f"总量只动 {total:+.1f}%，但结构在换手："
            + (f"{pos['name']} 贡献 {pos['contrib']:+.1f}pp、" if pos else "")
            + (f"{neg['name']} 拖累 {neg['contrib']:+.1f}pp。" if neg else "")
            + "涨的和跌的互相抵消，所以『大盘平稳』是错觉，实际是份额从一类商品搬到另一类。")
    impl = ("按品类分角色：贡献正的加陈列与库存，拖累的减 SKU；"
            "不要用一个总量指标考核全部品类。")
    fals = ("若下期正贡献品类转为负、负贡献品类转正，说明是短期促销而非结构换手。")
    return mech, impl, fals, "中"


def _mech_volume(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    nominal = t.get("nominal", 0.0)
    price = t.get("price", 0.0)
    volume = t.get("volume", 0.0)
    driver = "价格" if abs(price) > abs(volume) else "量"
    mech = (f"名义 {nominal:+.1f}% 拆成价格 {price:+.1f}%、量 {volume:+.1f}%"
            f"（交叉项可忽略）：增长主要由{driver}驱动。"
            + ("价格驱动意味着客单价是主变量，低价换量在这个阶段不成立；"
               if driver == "价格" else
               "量驱动意味着渗透或复购是主变量，提价空间有限。"))
    impl = ("考核从『销售额』改成『量 × 客单』两项拆开看；"
            "价格驱动时保毛利，量驱动时保周转。")
    fals = ("若下期价格转负而名义仍正，则量增判断成立；若量转负而名义仍正，"
            "则全部由价格贡献，本节的驱动判断要改。")
    return mech, impl, fals, "中"


def _mech_unit(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    net = t.get("net", 0.0)
    be = t.get("breakeven", 0.0)
    price = t.get("price", 0.0)
    shock = t.get("shock_net")
    buffer = (price - be) / price * 100 if price else 0.0
    mech = (f"净利 {net:+.2f} 元 = 售价 {price:.2f} − 成本 {t.get('cost', 0):.2f}"
            f" − 渠道 {t.get('channel', 0):.2f}；保本价 {be:.2f} 元。"
            + (f"原料涨 20% 后净利只剩 {shock:+.2f} 元，安全垫只有售价的 {buffer:.1f}%。"
               if shock is not None else ""))
    impl = (f"报价低于 {be:.2f} 元不接；先锁原料或签价格联动，再谈扩量——"
            "这条业务放大规模会放大亏损。")
    fals = ("若损耗率或渠道扣点比假设低 2 个百分点，净利回到正值，闸门可以放宽；"
            "反之若原料涨幅超过 20%，闸门要收紧。")
    return mech, impl, fals, "中"


def _mech_concentration(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    cr = t.get("cr3", 0.0)
    hhi = t.get("hhi", 0.0)
    verdict = ("头部集中，正面进入要买流量" if cr >= 50 or hhi >= 1500 else
               "中度集中，缝隙在细分场景" if cr >= 30 or hhi >= 800 else
               "分散市场，靠渠道效率而非品牌壁垒")
    mech = (f"CR3 {cr:.1f}%、HHI {hhi:.0f}：{verdict}。"
            "集中度不是好坏，是进入成本：越集中，越不能按『再做一个同款』进。")
    impl = ("先从头部不做的场景切（区域、B 端、礼盒、定制），"
            "用代工或联名验证订单，不先建产能。")
    fals = ("若头部份额在下期下降超过 3 个百分点，说明在换手，正面进入的窗口可能打开。")
    return mech, impl, fals, "中"


def _mech_region(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    cr3 = t.get("cr3", 0.0)
    hhi = t.get("hhi", 0.0)
    top = t.get("top3") or []
    mech = (f"CR3 {cr3:.1f}% 是区域集中、不是品牌集中："
            f"{'、'.join(top[:3])} 三市占全区社零一半以上，HHI {hhi:.0f}；"
            "这说明需求集中在少数城市，不说明竞争已经打满——"
            "要看的是这些城市里同类供给有几家，而不是份额本身。")
    impl = ("开店排序按『社零份额 × 增速 × 现有供给』三项排，"
            "首府做形象店、县域做嵌入，不按城市名气排。")
    fals = ("若某盟市份额一年内变动超过 3 个百分点，或已披露城市出现第二家大型卖场，"
            "区域排序要重排。")
    return mech, impl, fals, "中"


def _mech_spread(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    ratio = t.get("ratio")
    mech = (f"同一时点最高 {t.get('hi', 0):.2f}、最低 {t.get('lo', 0):.2f}，"
            f"差 {t.get('spread', 0):.2f}（{t.get('spread_pct', 0):.1f}%）"
            + (f"，是月度波动的 {ratio:.1f} 倍" if ratio else "")
            + "。空间差大于时间差，说明『在哪买』比『什么时候买』更值钱。")
    impl = ("先做跨市场调运与换源，再谈锁价；"
            f"价差回落到 {t.get('floor', 3.0):.1f} 元以内时停止调运。")
    fals = ("若扣掉运费与损耗后价差为负，则套利不成立，本节的空间判断作废。")
    return mech, impl, fals, "高"


def _mech_phase(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    mech = (f"月度均值会抹平节奏：{t.get('phase', '')}。"
            "把周度序列拉开后，真正的拐点出现在"
            f"{t.get('turn', '最近两周')}，与月度方向不一致。")
    impl = ("报价有效期按周设，不按月设；"
            f"在{t.get('turn', '拐点')}之后先小批量验证，再决定是否锁量。")
    fals = (f"若{t.get('turn', '拐点')}之后连续两周反向，则拐点判断作废，回到月度口径。")
    return mech, impl, fals, "中"


def _mech_consistency(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    mech = (f"公报增速 {t.get('published', 0):+.1f}% 与绝对值反推 {t.get('implied', 0):+.1f}% "
            f"相差 {t.get('diff', 0):.1f}pp（约 {t.get('amount', 0):.0f} 亿元）："
            "这是统计口径修订，不是经营变化。")
    impl = ("跨年比较只用增速，不用绝对值相减；两套基数并列披露，"
            "不做平滑、不取平均。")
    fals = ("若统计年鉴给出修订后的可比基数，以年鉴为准重算，本节的两套数撤掉。")
    return mech, impl, fals, "高"


def _mech_coverage(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    mech = (f"缺 {t.get('n', 0)} 项：{t.get('names', '')}。"
            "它们不是零，是不能下结论——用估算补上，等于把缺口藏起来。")
    impl = (f"受影响的是：{t.get('affected', '相关品类与区域结论')}；"
            f"补数动作：{t.get('action', '按公开口径补齐后再重跑')}。")
    return mech, impl, "", "高"


def _mech_demand(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    mech = (f"需求底座在换：新增家庭约 {t.get('new_households', 0):.0f} 万户/年，"
            f"存量家庭 {t.get('households', 0):.0f} 万户，新增只占 {t.get('new_ratio', 0):.1f}%；"
            f"65 岁以上占 {t.get('aging', 0):.1f}%、三人及以下家庭占 {t.get('small_hh', 0):.1f}%。"
            "增量逻辑（新房、新婚）已经让位给替换逻辑（旧换新、适老化、小规格）。")
    impl = ("选品与陈列按『替换』做：高频刚需、小规格、易安装、适老化；"
            "不押新房交付与婚庆大件。")
    fals = ("若出生人口或结婚对数连续两年回升超过 10%，新增需求重新成为主变量，"
            "本节判断作废。")
    return mech, impl, fals, "高"


def _mech_channel(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    mech = (f"渠道在换手：{t.get('lose', '百货/专卖')} 增速 {t.get('lose_g', 0):+.1f}%，"
            f"{t.get('win', '超市/便利店')} 增速 {t.get('win_g', 0):+.1f}%，"
            f"差 {t.get('gap', 0):.1f}pp。"
            f"线上渗透 {t.get('online', 0):.1f}%（全国 {t.get('online_cn', 0):.1f}%），"
            "本地线上不是主战场，失血的量主要在业态之间搬，不是搬到线上。")
    impl = ("把陈列与库存从百货/专卖往超市与社区店迁；"
            "线上只做特产的增量，不用它承接家居百货的主力。")
    fals = ("若线上渗透一年内提升超过 3 个百分点，或百货店增速转正，"
            "渠道换手的方向要重判。")
    return mech, impl, fals, "中"


def _mech_supply(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    mech = (f"需求 {t.get('demand', 0):.0f} 亿元，但本地供给很薄："
            f"{t.get('anchor', '家居卖场')} 只有 {t.get('stores', 0)} 家、"
            f"县域综合商贸中心 {t.get('county', 0)} 个。"
            "供给密度低不是空白市场，是需求被超市、社区店与线上分流了。")
    impl = ("先做店中店/专区（超市 + 社区店），不先开大卖场；"
            "县域用现有的商贸中心做嵌入，不自建网络。")
    fals = ("若出现第二家大型家居卖场开业，或超市渠道家居品类增速转负，"
            "供给判断要重做。")
    return mech, impl, fals, "中"


def _mech_policy(t: Dict[str, Any]) -> Tuple[str, str, str, str]:
    rate = t.get("rate", 0.0)
    cap = t.get("cap", 0.0)
    basket = t.get("basket", 0.0)
    cap2, basket2 = t.get("cap2"), t.get("basket2")
    mech = (f"补贴 {rate:.0f}%、单件上限 {cap:.0f} 元，等于单笔换新最多撬动 "
            f"{basket:.0f} 元的商品；超过这个价位，顾客自付比例陡增，成交会被截断。")
    if cap2:
        mech += (f"智能家居单件上限 {cap2:.0f} 元，锁价下移到 {basket2:.0f} 元——"
                 "两个品类锁的不是同一价位，主推价格带要分开定。")
    impl = (f"主推价格带放在 {basket:.0f} 元的 1.0—1.3 倍，让顾客『够得着上限』；"
            "参与补贴的 SKU 保留价格与销量凭证，否则结算拿不到。")
    fals = ("若补贴比例或上限再次调整，价格带结论按新参数重算；"
            "补贴退出后若中高价带销量不降，说明需求不是补贴创造的。")
    return mech, impl, fals, "中"


_MECH: Dict[str, Callable[[Dict[str, Any]], Tuple[str, str, str, str]]] = {
    "size": _mech_size,
    "trend": _mech_trend,
    "gap": _mech_gap,
    "mix": _mech_mix,
    "volume": _mech_volume,
    "unit": _mech_unit,
    "concentration": _mech_concentration,
    "spread": _mech_spread,
    "phase": _mech_phase,
    "consistency": _mech_consistency,
    "coverage": _mech_coverage,
    "demand": _mech_demand,
    "channel": _mech_channel,
    "supply": _mech_supply,
    "policy": _mech_policy,
    "region": _mech_region,
}

# 每类判断至少要有的标签：缺了就不许写机理（门禁据此判「深度不足」）
REQUIRED_TAGS: Dict[str, Tuple[str, ...]] = {
    "size": ("paths",),
    "trend": ("last_growth",),
    "gap": ("items",),
    "mix": ("items",),
    "volume": ("nominal", "price"),
    "unit": ("net", "breakeven"),
    "concentration": ("cr3",),
    "spread": ("spread",),
    "phase": ("phase",),
    "consistency": ("published", "implied"),
    "coverage": ("n",),
    "demand": ("households",),
    "channel": ("lose_g", "win_g"),
    "supply": ("stores",),
    "policy": ("rate", "cap"),
    "region": ("cr3",),
}


def finalize(claim: Claim) -> Claim:
    """补机理/落点/证伪。标签不足时留空，让门禁把「深度不足」暴露出来。"""
    need = REQUIRED_TAGS.get(claim.kind, ())
    have = all(claim.tags.get(k) is not None for k in need)
    if have and claim.kind in _MECH:
        mech, impl, fals, conf = _MECH[claim.kind](claim.tags)
        claim.mechanism = claim.mechanism or mech
        claim.implication = claim.implication or impl
        claim.falsifier = claim.falsifier or fals
        claim.confidence = claim.confidence or conf
    return claim


# --------------------------------------------------------------------------- #
# Claim → 报告章节
# --------------------------------------------------------------------------- #
# 每类判断的强标签：(观察句标签, 机理/落点/证伪标签)。
# 同一份报告里不能每节都长成「判断/机理/落点/证伪」——前两句照实说，
# 后三句换词：口径差 / 背离清单 / 成本栈 / 位次 / 缺口清单 …
SECTION_LABELS: Dict[str, Tuple[Tuple[str, ...], Tuple[str, ...]]] = {
    "size": (("判断　", "口径差　", "用法　"), ("机理　", "落点　", "证伪　")),
    "trend": (("判断　", "对照　"), ("机理　", "落点　", "触发条件　")),
    "gap": (("判断　", "背离清单　"), ("机理　", "落点　", "证伪　")),
    "mix": (("判断　", "结构变化　"), ("机理　", "落点　", "证伪　")),
    "volume": (("判断　", "拆解　"), ("机理　", "落点　", "反证　")),
    "unit": (("判断　", "成本栈　"), ("闸门　", "落点　", "敏感性　")),
    "concentration": (("判断　", "位次　"), ("含义　", "落点　", "换手信号　")),
    "spread": (("判断　", "极差　"), ("机理　", "落点　", "套利边界　")),
    "phase": (("判断　", "拐点　"), ("机理　", "落点　", "反证　")),
    "consistency": (("判断　", "两套数　"), ("处理方式　", "落点　", "以什么为准　")),
    "coverage": (("判断　", "缺口清单　"), ("机理　", "受影响结论　", "")),
    "demand": (("判断　", "结构　"), ("含义　", "落点　", "反转信号　")),
    "channel": (("判断　", "对照　"), ("机理　", "落点　", "换手信号　")),
    "supply": (("判断　", "供给密度　"), ("含义　", "落点　", "供给变化　")),
    "policy": (("判断　", "参数　"), ("含义　", "落点　", "政策变化　")),
    "region": (("判断　", "集中度　"), ("含义　", "落点　", "排序变化　")),
}
_TAIL_DEFAULT = ("机理　", "落点　", "什么会推翻它　")


def to_section(claim: Claim, question: str = "", index: int = 0) -> Dict[str, Any]:
    """把一条判断装配成 renderer 认的 section。

    阅读顺序：观察（detail，方法层已排好） → 机理 → 落点 → 证伪。
    不同 kind 的 detail 条数与句式不同，不强行凑成三段。

    强标签按 kind 变化（口径/背离/成本栈/位次/清单…），避免每节都是
    「判断/机理/落点/什么会推翻它」同一个壳。
    """
    full = list(dict.fromkeys(list(claim.refs) +
                              [r for d in claim.detail for r in (d.get("refs") or [])]))
    labels = claim.labels or SECTION_LABELS.get(claim.kind, ((), ()))
    dlab, tlab = (labels if isinstance(labels, tuple) and len(labels) == 2
                  and isinstance(labels[0], tuple) else ((), ()))
    tlab = tuple(tlab) + _TAIL_DEFAULT[len(tlab):] if tlab else _TAIL_DEFAULT
    reading: List[Dict[str, Any]] = []
    for i, d in enumerate(claim.detail):
        strong = d.get("strong") or ""
        if not strong:
            strong = dlab[i] if i < len(dlab) else ("判断　" if i == 0 else "")
        reading.append({"text": d["text"], "refs": full, "strong": strong})
    if claim.mechanism:
        reading.append({"text": claim.mechanism, "refs": full, "strong": tlab[0]})
    if claim.implication:
        reading.append({"text": claim.implication, "refs": full, "strong": tlab[1]})
    if claim.falsifier:
        reading.append({"text": claim.falsifier, "refs": full, "strong": tlab[2]})
    sec: Dict[str, Any] = {
        "index": index,
        "title": claim.headline,
        "question": question or "",
        "reading": reading,
        "refs": full,
        "assumptions": list(claim.assumptions),
    }
    if claim.table:
        sec["table"] = claim.table
    if claim.chart:
        sec["chart"] = claim.chart
    if claim.inline_boundary and claim.boundary:
        sec["boundary"] = claim.boundary
    if claim.confidence:
        sec["confidence"] = claim.confidence
    return sec


def merge_claims(claims: List[Claim], question: str = "",
                 index: int = 0) -> Optional[Dict[str, Any]]:
    """一个章节需要两条判断时（如「结构 + 量价」），合成一节：标题取主判断。"""
    claims = [c for c in claims if c]
    if not claims:
        return None
    claims.sort(key=lambda c: c.weight, reverse=True)
    main = claims[0]
    sec = to_section(main, question, index)
    for extra in claims[1:]:
        for d in extra.detail:
            sec["reading"].append({"text": d["text"], "refs": list(d.get("refs") or []),
                                   "strong": d.get("strong") or ""})
        if extra.table and not sec.get("table"):
            sec["table"] = extra.table
        if extra.chart and not sec.get("chart"):
            sec["chart"] = extra.chart
        sec["refs"] = list(dict.fromkeys(list(sec["refs"]) + list(extra.refs)))
        if extra.boundary and not sec.get("boundary"):
            sec["boundary"] = extra.boundary
    return sec

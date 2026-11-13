# -*- coding: utf-8 -*-
"""八字推演链（纯函数）：五行力量量化 → 旺衰五档 → 用神五法 → 岁运逐年评分。

借鉴 tianzhi-core（MIT，https://pypi.org/project/tianzhi-core/）的「第三段：判断与推演」
模型，把八字从「四指标散件」升级成一条可对质、可复现、可测试的连续流水线。

── 与现有散件的关系（不删旧，只补强）──
  现有 libs/judge/tiaohou.py 的 analyze_wangshuai（得令/得地/得生/得助 四布尔）仍是
  可用的一维粗筛；本模块给的是 tianzhi-core 式「成分加权 + 归一化 ratio 五档」。
  现有 libs/pan/bazi_liunian.py 的 _score_year（喜忌 ±15 + 合冲刑害）仍可用；本模块给的是
  带 breakdown 逐项交代「每一分从哪来」的可解释评分。
  两者不冲突：本模块是「推演链」的权威实现，旧件作交叉印证（见 libs/judge/bazi_evaluator.py）。

── 契约（同 tianzhi-core）──
  纯函数：不读系统时间、不访问网络/文件（调候表除外，属包内数据表）。
  同一 quad（四柱）永远得到同一输出。流派分歧处收敛为显式参数（priority / zishi），
  不替使用者选边。所有工程系数标注「本包取值，可调」。

── 数据校勘提示 ──
  调候表复用 libs/judge/tiaohou.py 的 TIAO_HOU（《穷通宝鉴》120 格）。tianzhi-core 已
  逐格回原文校勘（甲戌「甲庚」→「丁庚」、甲午补庚、甲未「癸庚丁」→「丁庚」、甲申次序、
  乙未次序），本表尚未同步这五处，用前建议按 tianzhi-classics 校勘。

用法:
  python libs/judge/bazi_chain.py --pillars 辛巳 丁酉 戊子 甲寅
  python libs/judge/bazi_chain.py --pillars 丙子 壬辰 乙酉 癸未 --year 丙午
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

# ======================================================================
# 一、五行与干支基础表（tianzhi-core core/wuxing.py + core/ganzhi.py）
# ======================================================================

ORDER: tuple[str, ...] = ("木", "火", "土", "金", "水")

SHENG: dict[str, str] = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE: dict[str, str] = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
SHENG_ME: dict[str, str] = {v: k for k, v in SHENG.items()}
KE_ME: dict[str, str] = {v: k for k, v in KE.items()}

GAN: str = "甲乙丙丁戊己庚辛壬癸"
ZHI: str = "子丑寅卯辰巳午未申酉戌亥"

GAN_WUXING: dict[str, str] = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
ZHI_WUXING: dict[str, str] = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}
GAN_YANG: frozenset[str] = frozenset("甲丙戊庚壬")

#: 地支藏干，本气、中气、余气（tianzhi-core core/ganzhi.py HIDDEN）
HIDDEN: dict[str, tuple[tuple[str, str], ...]] = {
    "子": (("癸", "本"),),
    "丑": (("己", "本"), ("癸", "中"), ("辛", "余")),
    "寅": (("甲", "本"), ("丙", "中"), ("戊", "余")),
    "卯": (("乙", "本"),),
    "辰": (("戊", "本"), ("乙", "中"), ("癸", "余")),
    "巳": (("丙", "本"), ("庚", "中"), ("戊", "余")),
    "午": (("丁", "本"), ("己", "中")),
    "未": (("己", "本"), ("丁", "中"), ("乙", "余")),
    "申": (("庚", "本"), ("壬", "中"), ("戊", "余")),
    "酉": (("辛", "本"),),
    "戌": (("戊", "本"), ("辛", "中"), ("丁", "余")),
    "亥": (("壬", "本"), ("甲", "中")),
}
#: 子、卯、酉只藏一字，气最纯（量化时给更高权重，出处 china-testing/bazi 之 zhi5）
PURE_ZHI: frozenset[str] = frozenset("子卯酉")

CHANGSHENG: tuple[str, ...] = (
    "长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养",
)
_CS_START: dict[str, str] = {"甲": "亥", "丙": "寅", "戊": "寅", "庚": "巳", "壬": "申"}
_CS_START_YIN: dict[str, str] = {"乙": "午", "丁": "酉", "己": "酉", "辛": "子", "癸": "卯"}
YANGREN: dict[str, str] = {"甲": "卯", "丙": "午", "戊": "午", "庚": "酉", "壬": "子"}

GAN_HE: dict[frozenset[str], str] = {
    frozenset({"甲", "己"}): "土", frozenset({"乙", "庚"}): "金",
    frozenset({"丙", "辛"}): "水", frozenset({"丁", "壬"}): "木",
    frozenset({"戊", "癸"}): "火",
}
GAN_CHONG: frozenset[frozenset[str]] = frozenset({
    frozenset({"甲", "庚"}), frozenset({"乙", "辛"}),
    frozenset({"丙", "壬"}), frozenset({"丁", "癸"}),
})
ZHI_LIUHE: dict[frozenset[str], str] = {
    frozenset({"子", "丑"}): "土", frozenset({"寅", "亥"}): "木",
    frozenset({"卯", "戌"}): "火", frozenset({"辰", "酉"}): "金",
    frozenset({"巳", "申"}): "水", frozenset({"午", "未"}): "土",
}
ZHI_SANHE: dict[tuple[str, str, str], str] = {
    ("申", "子", "辰"): "水", ("亥", "卯", "未"): "木",
    ("寅", "午", "戌"): "火", ("巳", "酉", "丑"): "金",
}
ZHI_SANHUI: dict[tuple[str, str, str], str] = {
    ("寅", "卯", "辰"): "木", ("巳", "午", "未"): "火",
    ("申", "酉", "戌"): "金", ("亥", "子", "丑"): "水",
}
ZHI_CHONG: dict[str, str] = {
    "子": "午", "午": "子", "丑": "未", "未": "丑", "寅": "申", "申": "寅",
    "卯": "酉", "酉": "卯", "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳",
}
ZHI_HAI: dict[str, str] = {
    "子": "未", "未": "子", "丑": "午", "午": "丑", "寅": "巳", "巳": "寅",
    "卯": "辰", "辰": "卯", "申": "亥", "亥": "申", "酉": "戌", "戌": "酉",
}
ZHI_XING_GROUPS: tuple[tuple[str, ...], ...] = (("寅", "巳", "申"), ("丑", "戌", "未"))
ZHI_XING_PAIR: frozenset[frozenset[str]] = frozenset({frozenset({"子", "卯"})})
ZHI_ZIXING: frozenset[str] = frozenset({"辰", "午", "酉", "亥"})

SUPPORT: frozenset[str] = frozenset({"比劫", "印"})
DRAIN: frozenset[str] = frozenset({"食伤", "财", "官杀"})

TEN_GODS: tuple[str, ...] = ("比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印")

# 四柱键序
POSITIONS: tuple[str, ...] = ("year", "month", "day", "hour")

# 四柱输入类型：{year:(干,支), month:(干,支), day:(干,支), hour:(干,支)}
Quad = Mapping[str, tuple[str, str]]


def relation(target: str, me: str) -> str:
    """target 这一行对 me 是什么关系：比劫/印/食伤/财/官杀。"""
    if target == me:
        return "比劫"
    if SHENG[target] == me:
        return "印"
    if SHENG[me] == target:
        return "食伤"
    if KE[me] == target:
        return "财"
    if KE[target] == me:
        return "官杀"
    raise ValueError(f"不是五行：{target!r} 或 {me!r}")


def ten_god(gan: str, day_gan: str) -> str:
    """以日主 day_gan 论，返回 gan 的十神名。"""
    d, x = GAN_WUXING[day_gan], GAN_WUXING[gan]
    same = (gan in GAN_YANG) == (day_gan in GAN_YANG)
    if x == d:
        return "比肩" if same else "劫财"
    if SHENG[d] == x:
        return "食神" if same else "伤官"
    if KE[d] == x:
        return "偏财" if same else "正财"
    if KE[x] == d:
        return "七杀" if same else "正官"
    if SHENG[x] == d:
        return "偏印" if same else "正印"
    raise ValueError(f"不是天干：{gan!r}")


def dishi(gan: str, zhi: str) -> str:
    """天干在某个地支上的十二长生状态。阳干顺行、阴干逆行。"""
    if gan in _CS_START:
        start, step = _CS_START[gan], 1
    elif gan in _CS_START_YIN:
        start, step = _CS_START_YIN[gan], -1
    else:
        raise ValueError(f"不是天干：{gan!r}")
    d = (ZHI.index(zhi) - ZHI.index(start)) * step % 12
    return CHANGSHENG[d]


def validate_quad(quad: Quad) -> None:
    for pos in POSITIONS:
        cell = quad.get(pos)
        if not cell or len(cell) != 2:
            raise ValueError(f"缺少或不完整的柱：{pos!r}")
        gan, zhi = cell
        if gan not in GAN:
            raise ValueError(f"{pos} 柱天干不合法：{gan!r}")
        if zhi not in ZHI:
            raise ValueError(f"{pos} 柱地支不合法：{zhi!r}")


# ======================================================================
# 二、量化（strength：成分加权 → 五行力量 / 旺衰五档 / 十神力量 / 寒暖）
# ======================================================================

GAN_BASE: float = 10.0            # 天干基础分（本包取值，可调）
ZHI_BASE: float = 12.0            # 地支基础分（本包取值，可调）
ROOT_COEF: dict[str, float] = {"本": 1.0, "中": 0.5, "余": 0.3}   # 本中余三档
PURE_ZHI_COEF: float = 1.6        # 纯气支加权（8/5，本包取值）
MONTH_WEIGHT: float = 2.0         # 月令配重（《子平真诠》「专求月令」，倍数本包取值）
SILING_BOOST: float = 1.1         # 人元司令加权（本包取值）
ATTACH_FACTOR: float = 1.2        # 贴身加权（月干、日支，与生克无关）
ATTACH_GAN_POS: frozenset[str] = frozenset({"month"})
ATTACH_ZHI_POS: frozenset[str] = frozenset({"day"})
VIRTUAL_FLOAT_FACTOR: float = 0.5  # 虚透无根折减
DAY_ROOT_BONUS: float = 0.0        # 日主根气额外加分（默认 0，避免重复计根）
#: 旺衰五档分界（归一化 ratio = 同党/(同党+异党)），阈值按 3000 随机盘分位数标定（本包取值）
RATIO_BANDS: tuple[float, float, float, float] = (0.26, 0.35, 0.48, 0.61)
ROOT_DISHI: frozenset[str] = frozenset({"长生", "临官", "帝旺"})
ROOT_COUNT_TH: int = 2

CLIMATE_ZHI: dict[str, float] = {
    "子": -1.0, "丑": -0.8, "寅": 0.3, "卯": 0.1, "辰": -0.4, "巳": 0.9,
    "午": 1.0, "未": 0.7, "申": -0.1, "酉": -0.3, "戌": 0.4, "亥": -0.9,
}
CLIMATE_GAN: dict[str, float] = {
    "甲": 0.2, "乙": 0.1, "丙": 1.0, "丁": 0.8, "戊": 0.3,
    "己": -0.2, "庚": -0.2, "辛": -0.3, "壬": -0.9, "癸": -0.8,
}
CLIMATE_W_MONTH_ZHI: float = 3.0
CLIMATE_W_ZHI: float = 1.5
CLIMATE_W_GAN: float = 1.0


@dataclass(frozen=True)
class Component:
    """全盘拆出的一个力量成分。"""
    pos: str
    kind: str               # 干 / 支
    char: str               # 该柱上的字（天干或地支）
    gan: str                # 折算到的天干（地支取藏干）
    level: str              # 透 / 本 / 中 / 余
    weight: float
    tags: tuple[str, ...]   # 加权理由短标签


def _has_root(gan: str, quad: Quad) -> bool:
    wx = GAN_WUXING[gan]
    return any(
        GAN_WUXING[hg] == wx
        for pos in POSITIONS
        for hg, _ in HIDDEN[quad[pos][1]]
    )


def components(quad: Quad, *, month_siling: str | None = None,
               include_day_gan: bool = True) -> list[Component]:
    """把四柱拆成带权重的成分表。旺衰/五行分布/十神力量都建在这上面。"""
    validate_quad(quad)
    out: list[Component] = []
    for pos in POSITIONS:
        gan, zhi = quad[pos]
        if pos != "day" or include_day_gan:
            w = GAN_BASE
            tags: list[str] = []
            if not _has_root(gan, quad):
                w *= VIRTUAL_FLOAT_FACTOR
                tags.append("虚透")
            if pos in ATTACH_GAN_POS:
                w *= ATTACH_FACTOR
                tags.append("贴身")
            out.append(Component(pos, "干", gan, gan, "透", w, tuple(tags)))
        is_month = pos == "month"
        pure = zhi in PURE_ZHI
        for hg, level in HIDDEN[zhi]:
            w = ZHI_BASE * ROOT_COEF[level]
            tags = []
            if pure:
                w *= PURE_ZHI_COEF
                tags.append("纯气")
            if is_month:
                w *= MONTH_WEIGHT
                tags.append("月令")
                if month_siling and hg == month_siling:
                    w *= SILING_BOOST
                    tags.append("司令")
            if pos in ATTACH_ZHI_POS:
                w *= ATTACH_FACTOR
                tags.append("贴身")
            out.append(Component(pos, "支", zhi, hg, level, w, tuple(tags)))
    return out


def element_power(quad: Quad, *, month_siling: str | None = None) -> dict[str, float]:
    """全盘五行力量分布。五键恒在，缺者为 0.0。"""
    out = {w: 0.0 for w in ORDER}
    for c in components(quad, month_siling=month_siling):
        out[GAN_WUXING[c.gan]] += c.weight
    return {k: round(v, 3) for k, v in out.items()}


@dataclass(frozen=True)
class Strength:
    """日主旺衰。"""
    support: float
    drain: float
    net: float
    ratio: float
    label: str              # 身旺/偏旺/中和/偏弱/身弱
    has_root: bool          # 强根布尔闸，与 ratio 并联，不参与连续分
    root_note: tuple[str, ...]
    items: tuple[dict, ...]


def day_master_strength(quad: Quad, *, month_siling: str | None = None) -> Strength:
    """日主旺衰（五档）。同党=比劫+印，异党=食伤+财+官杀。

    分档作用在归一化 ratio 上，不用未归一净值。强根闸 has_root 与 ratio 并联：
    日主在任一地支得长生/临官/帝旺，或全盘藏干同五行者多于 ROOT_COUNT_TH，即为 True。
    """
    validate_quad(quad)
    day_gan = quad["day"][0]
    day_wx = GAN_WUXING[day_gan]

    items = []
    support = drain = 0.0
    for c in components(quad, month_siling=month_siling, include_day_gan=False):
        rel = relation(GAN_WUXING[c.gan], day_wx)
        side = "support" if rel in SUPPORT else "drain"
        score = c.weight
        if side == "support" and rel == "比劫" and c.kind == "支":
            score += DAY_ROOT_BONUS * ROOT_COEF[c.level]
        src = f"{c.pos}{c.kind}{c.char}" + (f"藏{c.gan}" if c.kind == "支" else "")
        items.append({"pos": c.pos, "src": src, "gan": c.gan, "rel": rel,
                      "side": side, "score": round(score, 3), "tags": c.tags})
        if side == "support":
            support += score
        else:
            drain += score

    total = support + drain
    ratio = support / total if total > 0 else 0.5
    lo2, lo1, hi1, hi2 = RATIO_BANDS
    if ratio >= hi2:
        label = "身旺"
    elif ratio >= hi1:
        label = "偏旺"
    elif ratio <= lo2:
        label = "身弱"
    elif ratio <= lo1:
        label = "偏弱"
    else:
        label = "中和"

    notes: list[str] = []
    rooted = False
    for pos in POSITIONS:
        zhi = quad[pos][1]
        d = dishi(day_gan, zhi)
        if d in ROOT_DISHI:
            rooted = True
            notes.append(f"{pos}支{zhi}·{d}")
    same_cnt = sum(
        1
        for pos in POSITIONS
        for hg, _ in HIDDEN[quad[pos][1]]
        if GAN_WUXING[hg] == day_wx
    )
    if same_cnt > ROOT_COUNT_TH:
        rooted = True
        notes.append(f"比劫墓库根×{same_cnt}")

    return Strength(
        support=round(support, 3), drain=round(drain, 3),
        net=round(support - drain, 3), ratio=round(ratio, 4),
        label=label, has_root=rooted, root_note=tuple(notes), items=tuple(items),
    )


def ten_god_power(quad: Quad, *, month_siling: str | None = None) -> dict[str, float]:
    """十神各自的力量。日干自身不计。十键恒在，缺者 0.0。"""
    validate_quad(quad)
    day_gan = quad["day"][0]
    out = {t: 0.0 for t in TEN_GODS}
    for c in components(quad, month_siling=month_siling, include_day_gan=False):
        out[ten_god(c.gan, day_gan)] += c.weight
    return {k: round(v, 3) for k, v in out.items()}


def climate_index(quad: Quad) -> float:
    """寒暖燥湿标量，负数偏寒湿、正数偏燥暖，落在 [-1,1]。"""
    validate_quad(quad)
    num = den = 0.0
    for pos in POSITIONS:
        gan, zhi = quad[pos]
        wz = CLIMATE_W_MONTH_ZHI if pos == "month" else CLIMATE_W_ZHI
        num += CLIMATE_ZHI[zhi] * wz
        den += wz
        num += CLIMATE_GAN[gan] * CLIMATE_W_GAN
        den += CLIMATE_W_GAN
    return round(num / den, 4) if den else 0.0


# ======================================================================
# 三、调候（《穷通宝鉴》表 + 按盘面剔除）
# ======================================================================

try:
    from .tiaohou import TIAO_HOU as _TIAO_HOU
except Exception:  # 表缺失时降级为空，climate_gods 返回 None
    _TIAO_HOU: dict = {}


def climate_gods(day_gan: str, month_zhi: str) -> list[str] | None:
    """查《穷通宝鉴》调候用神天干（按优先级）。查不到返回 None。"""
    gans = (_TIAO_HOU.get(day_gan) or {}).get(month_zhi)
    return list(gans) if gans else None


def _elements(gans) -> tuple[str, ...]:
    out: list[str] = []
    for g in gans or ():
        w = GAN_WUXING.get(g)
        if w and w not in out:
            out.append(w)
    return tuple(out)


def climate_need(quad: Quad) -> dict | None:
    """查调候表，再按盘面剔除（病药法：古表点名的用神若正是全盘之病则剔除）。

    返回 {gods: [天干], elements: (五行,), kept: (五行,), dropped: (五行,),
          bing: 最旺五行, fallback: bool}，查不到返回 None。
    """
    validate_quad(quad)
    gans = climate_gods(quad["day"][0], quad["month"][1])
    if gans is None:
        return None
    mass = element_power(quad)
    bing = max(mass, key=lambda k: mass[k]) if mass else ""
    elements = _elements(gans)
    kept = tuple(w for w in elements if w != bing)
    dropped = tuple(w for w in elements if w == bing)
    fallback = not kept
    if fallback:
        kept = elements[:1]
    return {"gods": gans, "elements": elements, "kept": kept,
            "dropped": dropped, "bing": bing, "fallback": fallback}


# ======================================================================
# 四、格局（《子平真诠》月令取格）
# ======================================================================

@dataclass(frozen=True)
class Pattern:
    name: str
    ten_god: str
    gan: str
    month_zhi: str
    basis: str              # 本气/透干/建禄/阳刃
    transparent_at: tuple[str, ...]
    evidence: tuple[str, ...]


def month_pattern(quad: Quad, *, month_siling: str | None = None) -> Pattern:
    """月令取格（《子平真诠·论用神》「八字用神，专求月令」）。

    1) 月支为日主临官→建禄格、帝旺（阳干）→阳刃格；2) 月支本气十神为基础格；
    3) 藏干透年/月/时干则透出者定格；4) 比劫定格称「月劫格」。
    """
    validate_quad(quad)
    day_gan = quad["day"][0]
    month_zhi = quad["month"][1]
    hidden = HIDDEN[month_zhi]

    d = dishi(day_gan, month_zhi)
    if d == "临官":
        return Pattern("建禄格", ten_god(day_gan, day_gan), day_gan, month_zhi, "建禄",
                       (), (f"月令{month_zhi}为{day_gan}之临官", "子平真诠·论建禄月劫"))
    if d == "帝旺" and YANGREN.get(day_gan) == month_zhi:
        return Pattern("阳刃格", ten_god(day_gan, day_gan), day_gan, month_zhi, "阳刃",
                       (), (f"月令{month_zhi}为{day_gan}之帝旺·阳刃", "子平真诠·论阳刃"))

    base_gan = hidden[0][0]
    basis = "本气"
    if month_siling and any(hg == month_siling for hg, _ in hidden):
        base_gan = month_siling
        basis = "司令"

    visible = {pos: quad[pos][0] for pos in ("year", "month", "hour")}
    chosen_gan, chosen_at = base_gan, ()
    for hg, _ in hidden:
        at = tuple(p for p, g in visible.items() if g == hg)
        if at:
            chosen_gan, chosen_at = hg, at
            basis = "透干"
            break

    tg = ten_god(chosen_gan, day_gan)
    name = "月劫格" if tg in ("比肩", "劫财") else f"{tg}格"
    if basis == "透干":
        ev = (f"月令{month_zhi}藏{chosen_gan}·{tg}", "透于" + "、".join(chosen_at), "子平真诠·论用神")
    else:
        ev = (f"月令{month_zhi}{basis}{chosen_gan}·{tg}", "未见透出", "子平真诠·论用神")
    return Pattern(name, ten_god=tg, gan=chosen_gan, month_zhi=month_zhi,
                   basis=basis, transparent_at=chosen_at, evidence=ev)


# ======================================================================
# 五、取用（yongshen：用神五法 → 用喜忌仇闲）
# ======================================================================

#: 默认：算准网口径（格局 > 扶抑 > 通关 > 病药 > 调候）
DEFAULT_PRIORITY: tuple[str, ...] = ("格局", "扶抑", "通关", "病药", "调候")
#: HeiGe 口径，供换派
HEIGE_PRIORITY: tuple[str, ...] = ("格局", "调候", "扶抑", "通关", "病药")

FOLLOW_WEAK_RATIO: float = 0.12    # 从弱阈值
FOLLOW_STRONG_RATIO: float = 0.88  # 专旺/从强阈值
TONGGUAN_MIN_SHARE: float = 0.22
TONGGUAN_BALANCE_MAX: float = 1.10
BING_MARGIN: float = 1.10
FUYI_BIJIE_MARGIN: float = 1.15
CLIMATE_TIEBREAK: bool = True


@dataclass(frozen=True)
class YongShen:
    yong: str
    xi: str
    ji: str
    chou: str
    xian: tuple[str, ...]
    method: str
    evidence: tuple[str, ...]

    @property
    def favorable(self) -> tuple[str, ...]:
        return (self.yong, self.xi)

    @property
    def unfavorable(self) -> tuple[str, ...]:
        return (self.ji, self.chou)


class _Ctx:
    def __init__(self, quad, month_siling):
        self.quad = quad
        self.day_gan = quad["day"][0]
        self.day_wx = GAN_WUXING[self.day_gan]
        self.body = day_master_strength(quad, month_siling=month_siling)
        self.mass = element_power(quad, month_siling=month_siling)
        self.gods = ten_god_power(quad, month_siling=month_siling)
        self.need = climate_need(quad)
        self.pattern = month_pattern(quad, month_siling=month_siling)


class _Pick:
    def __init__(self, yong, method, evidence):
        self.yong = yong
        self.method = method
        self.evidence = tuple(evidence)


def _climate_first(ctx, candidates):
    if not CLIMATE_TIEBREAK or ctx.need is None:
        return candidates
    kept = set(ctx.need["kept"])
    return [c for c in candidates if c in kept] + [c for c in candidates if c not in kept]


def _tier_geju(ctx):
    """特殊格局：从格与专旺（《滴天髓》「从得真者只论从」「一气专旺」）。"""
    b = ctx.body
    if b.ratio <= FOLLOW_WEAK_RATIO and not b.has_root:
        foe = {w: p for w, p in ctx.mass.items() if relation(w, ctx.day_wx) in DRAIN}
        if foe:
            yong = max(foe, key=lambda k: foe[k])
            rel = relation(yong, ctx.day_wx)
            return _Pick(yong, f"从格·从{rel}",
                         (f"同党占比{b.ratio:.2f}", "日主无强根", f"从其旺神·{rel}", "滴天髓·从象"))
    if b.ratio >= FOLLOW_STRONG_RATIO and b.has_root:
        return _Pick(ctx.day_wx, "专旺·顺其势",
                     (f"同党占比{b.ratio:.2f}", "日主有强根", "顺势不逆"))
    return None


def _tier_fuyi(ctx):
    """扶抑。身弱以比劫为用、喜印；身旺以财为用（比劫独重改官杀），喜食伤。"""
    b = ctx.body
    if b.label in ("身弱", "偏弱"):
        return _Pick(ctx.day_wx, "扶抑·身弱扶",
                     (f"同党占比{b.ratio:.2f}", "用比劫·喜印"))
    if b.label in ("身旺", "偏旺"):
        cai = KE[ctx.day_wx]
        guansha = KE_ME[ctx.day_wx]
        bijie = ctx.gods["比肩"] + ctx.gods["劫财"]
        yin = ctx.gods["正印"] + ctx.gods["偏印"]
        jie_leads = bijie > yin * FUYI_BIJIE_MARGIN
        cands = [guansha, cai] if jie_leads else [cai, guansha]
        why = "劫重·官煞制之" if jie_leads else "财制印比"
        ordered = _climate_first(ctx, cands)
        tag = ("调候合",) if ctx.need and ordered[0] in ctx.need["kept"] else ()
        src = ("子平真诠·论用神",) if jie_leads else ()
        return _Pick(ordered[0], "扶抑·身旺抑",
                     (f"同党占比{b.ratio:.2f}", why) + tag + src)
    return None


def _tier_tongguan(ctx):
    """通关：两行相战势均力敌，取居中一行泄强生弱（《滴天髓·通关》）。"""
    total = sum(ctx.mass.values())
    if total <= 0:
        return None
    bing = max(ctx.mass, key=lambda k: ctx.mass[k])
    best = None
    for a, b in KE.items():
        pa, pb = ctx.mass[a], ctx.mass[b]
        if min(pa, pb) <= 0:
            continue
        if pa / total < TONGGUAN_MIN_SHARE or pb / total < TONGGUAN_MIN_SHARE:
            continue
        if max(pa, pb) / min(pa, pb) > TONGGUAN_BALANCE_MAX:
            continue
        if bing in (a, b):
            continue
        mid = SHENG[a]
        if SHENG.get(mid) != b:
            continue
        if SHENG[mid] == bing:
            continue
        cand = (pa + pb, a, b, mid)
        if best is None or cand[0] > best[0]:
            best = cand
    if best is None:
        return None
    _, a, b, mid = best
    return _Pick(mid, "通关", (f"{a}{b}相战", f"通关·{mid}", f"非病·{bing}不与", "滴天髓·通关"))


def _bing_of(ctx):
    """全盘之病：最旺且领先次旺 BING_MARGIN 倍的那一行；身弱时不以日主自身为病。"""
    pool = dict(ctx.mass)
    if ctx.body.label in ("身弱", "偏弱"):
        pool.pop(ctx.day_wx, None)
    pool = {k: v for k, v in pool.items() if v > 0}
    if not pool:
        return None
    ranked = sorted(pool.items(), key=lambda kv: (-kv[1], ORDER.index(kv[0])))
    if len(ranked) > 1 and ranked[0][1] < ranked[1][1] * BING_MARGIN:
        return None
    return ranked[0][0]


def _tier_bingyao(ctx):
    """病药：全盘最旺者为病、克之者为药（《神峰通考·病药说》）。"""
    bing = _bing_of(ctx)
    if bing is None:
        return None
    yao = KE_ME[bing]
    return _Pick(yao, "病药", (f"病·{bing}最旺", f"药·{yao}制之", "神峰通考·病药说"))


def _tier_tiaohou(ctx):
    """调候：《穷通宝鉴》查表，已按盘面剔除。"""
    if ctx.need is None or not ctx.need["kept"]:
        return None
    return _Pick(ctx.need["kept"][0], "调候",
                 (f"取{''.join(ctx.need['gods'])}", f"剔除·{''.join(ctx.need['dropped']) or '无'}"))


PRIORITY_TIERS = {
    "格局": _tier_geju, "扶抑": _tier_fuyi, "通关": _tier_tongguan,
    "病药": _tier_bingyao, "调候": _tier_tiaohou,
}


def select(quad: Quad, *, month_siling: str | None = None,
           priority: tuple[str, ...] = DEFAULT_PRIORITY) -> YongShen:
    """取用。按 priority 逐档尝试，第一个给出用神的档即为依据。

    用喜忌仇闲由用神机械推出：喜=生用神者、忌=克用神者、仇=生忌神者、闲=其余，
    五行成环，天然互斥且忌神非空。
    """
    validate_quad(quad)
    day_gan = quad["day"][0]
    ctx = _Ctx(quad, month_siling)

    pick = None
    for tier in priority:
        fn = PRIORITY_TIERS.get(tier)
        if fn is None:
            raise ValueError(f"未知的取用档次：{tier!r}")
        pick = fn(ctx)
        if pick is not None:
            break
    if pick is None:
        pick = _Pick(ctx.day_wx, "兜底·扶身", ("各档均未落地",))

    yong = pick.yong
    xi = SHENG_ME[yong]
    ji = KE_ME[yong]
    chou = SHENG_ME[ji]
    xian = tuple(w for w in ORDER if w not in (yong, xi, ji, chou))

    ev = [f"旺衰·{ctx.body.label}", f"格·{ctx.pattern.name}"]
    if ctx.body.has_root:
        ev.append("日主有强根")
    ev.extend(pick.evidence)
    if ctx.need is not None:
        ev.append(f"调候·{''.join(ctx.need['kept'])}")
        ev.append(f"穷通宝鉴·{day_gan}日{quad['month'][1]}月")

    return YongShen(yong=yong, xi=xi, ji=ji, chou=chou, xian=xian,
                    method=pick.method, evidence=tuple(ev))


# ======================================================================
# 六、岁运引动（interact 精简：合冲刑害 + 岁运并临/冲 + 三合三会）
# ======================================================================

def _zhi_relation_kind(a: str, b: str) -> list[str]:
    """两地支之间的全部关系种类（合/冲/刑/自刑/害）。"""
    out = []
    if a == b:
        if a in ZHI_ZIXING:
            out.append("自刑")
        return out
    p = frozenset({a, b})
    if p in ZHI_LIUHE:
        out.append("合")
    if ZHI_CHONG.get(a) == b:
        out.append("冲")
    if ZHI_HAI.get(a) == b:
        out.append("害")
    if p in ZHI_XING_PAIR or any(a in g and b in g for g in ZHI_XING_GROUPS):
        out.append("刑")
    return out


def _gan_relation_kind(a: str, b: str) -> str | None:
    if a == b:
        return None
    p = frozenset({a, b})
    if p in GAN_HE:
        return "合"
    if p in GAN_CHONG:
        return "冲"
    return None


def _zhi_groups(zhis) -> list[tuple[str, str, str]]:
    """一组地支里成立的三合与三会（三字全在才成局）。返回 (kind, trio, into)。"""
    have = set(zhis)
    out = []
    for trio, into in ZHI_SANHE.items():
        if have.issuperset(trio):
            out.append(("三合", "".join(trio), into))
    for trio, into in ZHI_SANHUI.items():
        if have.issuperset(trio):
            out.append(("三会", "".join(trio), into))
    return out


def _interact(quad: Quad, year_gz: str, dayun_gz: str | None) -> dict:
    """流年 + 大运 对原局的引动。返回 score 所需的结构。"""
    validate_quad(quad)
    if len(year_gz) != 2 or year_gz[0] not in GAN or year_gz[1] not in ZHI:
        raise ValueError(f"流年干支不合法：{year_gz!r}")
    y_gan, y_zhi = year_gz
    day_gan = quad["day"][0]

    # 流年天干对日主十神
    year_ten_god = ten_god(y_gan, day_gan)

    # 流年地支与四柱的冲刑害合
    zhi_rels = []
    for pos in POSITIONS:
        zhi = quad[pos][1]
        for kind in _zhi_relation_kind(y_zhi, zhi):
            zhi_rels.append({"kind": kind, "pillar": pos, "target": zhi})

    # 流年天干与四柱（冲/合）
    gan_rels = []
    for pos in POSITIONS:
        gan = quad[pos][0]
        k = _gan_relation_kind(y_gan, gan)
        if k:
            gan_rels.append({"kind": k, "pillar": pos, "target": gan})

    # 岁运并临 / 相冲
    suiyun_binglin = dayun_gz is not None and year_gz == dayun_gz
    suiyun_chong = False
    if dayun_gz and len(dayun_gz) == 2:
        suiyun_chong = ZHI_CHONG.get(y_zhi) == dayun_gz[1]

    # 流年 + 四柱四支凑成的三合三会
    groups = _zhi_groups([y_zhi] + [quad[pos][1] for pos in POSITIONS])

    return {"day_gan": day_gan, "year_ten_god": year_ten_god,
            "year_zhi_relations": zhi_rels, "year_gan_relations": gan_rels,
            "suiyun_binglin": suiyun_binglin, "suiyun_chong": suiyun_chong,
            "groups": groups}


# ======================================================================
# 七、逐年评分（score：可解释的相对分）
# ======================================================================

BASE: float = 50.0
FLOOR: float = 0.0
CEILING: float = 100.0
WX_HIT: float = 8.0
SLOT_WEIGHT: dict[str, float] = {"year_gan": 1.0, "year_zhi": 1.2,
                                 "dayun_gan": 0.5, "dayun_zhi": 0.6}
GOD_BIAS: dict[str, float] = {
    "正财": 6.0, "偏财": 5.0, "正官": 6.0, "正印": 5.0, "食神": 5.0,
    "偏印": 1.0, "比肩": 0.0, "劫财": -4.0, "伤官": -4.0, "七杀": -5.0,
}
GOD_WEIGHT: float = 0.8
REL_DELTA: dict[str, float] = {"冲": -9.0, "刑": -5.0, "自刑": -4.0, "害": -3.0, "合": 2.0}
PILLAR_WEIGHT: dict[str, float] = {"month": 1.4, "day": 1.3, "year": 0.8, "hour": 0.8}
DAY_GAN_CHONG: float = -5.0
DAY_GAN_HE: float = -1.0
SUIYUN_BINGLIN: float = -6.0
SUIYUN_CHONG: float = -6.0
GROUP_DELTA: float = 5.0


@dataclass(frozen=True)
class YearScore:
    ganzhi: str
    score: float
    breakdown: dict[str, float]
    terms: tuple[dict, ...]
    dayun: str | None
    ten_god: str | None
    stance: str


def _wx_delta(wx, favorable, unfavorable):
    if wx in favorable:
        return WX_HIT, "喜用"
    if wx in unfavorable:
        return -WX_HIT, "忌神"
    return 0.0, "闲神"


def _stance(gan_wx, zhi_wx, favorable, unfavorable):
    hits = [w for w in (gan_wx, zhi_wx) if w in favorable]
    miss = [w for w in (gan_wx, zhi_wx) if w in unfavorable]
    if len(hits) == 2:
        return "顺"
    if len(miss) == 2:
        return "逆"
    if hits and miss:
        return "混"
    if hits:
        return "偏顺"
    if miss:
        return "偏逆"
    return "平"


def score_year(quad: Quad, year_gz: str, *, dayun_gz: str | None = None,
               favorable: Sequence[str] | None = None,
               unfavorable: Sequence[str] | None = None) -> YearScore:
    """给一年打 0~100 相对分，逐项交代「每一分从哪来」（breakdown）。

    favorable/unfavorable 是喜用与忌神五行，由 yongshen 层取来；不给则五行项计 0。
    """
    fav = tuple(favorable or ())
    unf = tuple(unfavorable or ())
    y_gan, y_zhi = year_gz
    d = dayun_gz if (dayun_gz and len(dayun_gz) == 2) else None
    inter = _interact(quad, year_gz, dayun_gz)

    terms: list[tuple[str, str, float]] = [("base", "基准", BASE)]

    gan_wx = GAN_WUXING[y_gan]
    zhi_wx = ZHI_WUXING[y_zhi]
    for slot, char, wx in (("year_gan", y_gan, gan_wx), ("year_zhi", y_zhi, zhi_wx)):
        raw, tag = _wx_delta(wx, fav, unf)
        if raw:
            terms.append((slot, f"{char}({wx}){tag}", raw * SLOT_WEIGHT[slot]))
    if d:
        for slot, char, wx in (("dayun_gan", d[0], GAN_WUXING[d[0]]),
                               ("dayun_zhi", d[1], ZHI_WUXING[d[1]])):
            raw, tag = _wx_delta(wx, fav, unf)
            if raw:
                terms.append((slot, f"{char}({wx}){tag}", raw * SLOT_WEIGHT[slot]))

    tg = inter["year_ten_god"]
    if GOD_BIAS.get(tg):
        terms.append(("ten_god", f"{y_gan}对{inter['day_gan']}为{tg}", GOD_BIAS[tg] * GOD_WEIGHT))

    for rel in inter["year_zhi_relations"]:
        delta = REL_DELTA.get(rel["kind"], 0.0) * PILLAR_WEIGHT.get(rel["pillar"], 1.0)
        if delta:
            terms.append((f"zhi.{rel['kind']}.{rel['pillar']}",
                          f"{rel['target']}{rel['kind']}{rel['pillar']}支{y_zhi}", delta))

    for rel in inter["year_gan_relations"]:
        if rel["pillar"] != "day":
            continue
        if rel["kind"] == "冲":
            terms.append(("gan.冲.day", f"{y_gan}冲日主{inter['day_gan']}", DAY_GAN_CHONG))
        elif rel["kind"] == "合":
            terms.append(("gan.合.day", f"{y_gan}合日主{inter['day_gan']}", DAY_GAN_HE))

    if inter["suiyun_binglin"]:
        terms.append(("suiyun.并临", f"流年与大运同为{year_gz}", SUIYUN_BINGLIN))
    if inter["suiyun_chong"]:
        terms.append(("suiyun.冲", f"{y_zhi}冲大运支{d[1] if d else ''}", SUIYUN_CHONG))

    for kind, trio, into in inter["groups"]:
        raw, tag = _wx_delta(into, fav, unf)
        if raw:
            sign = 1.0 if raw > 0 else -1.0
            terms.append((f"group.{kind}", f"{trio}{kind}{into}局({tag})", GROUP_DELTA * sign))

    total = max(FLOOR, min(CEILING, sum(t[2] for t in terms)))
    breakdown: dict[str, float] = {}
    for src, detail, delta in terms:
        key = src if src == "base" else f"{src}|{detail}"
        while key in breakdown:
            key += "'"
        breakdown[key] = round(delta, 2)

    return YearScore(ganzhi=year_gz, score=round(total, 1), breakdown=breakdown,
                     terms=tuple({"source": s, "detail": dt, "delta": round(dv, 2)}
                                 for s, dt, dv in terms),
                     dayun=dayun_gz, ten_god=tg,
                     stance=_stance(gan_wx, zhi_wx, fav, unf))


def curve(quad: Quad, cycles, *, favorable=None, unfavorable=None) -> list[dict]:
    """整条人生曲线，每个流年一个点（相对分形状，非断语）。"""
    points = []
    for item in cycles:
        if isinstance(item, Mapping):
            gz = str(item.get("ganzhi") or "")
            years = item.get("years") or ()
        else:
            gz, years = str(item[0] or ""), (item[1] or ())
        for year, gz_y in years:
            ys = score_year(quad, gz_y, dayun_gz=gz or None,
                            favorable=favorable, unfavorable=unfavorable)
            points.append({"year": int(year), "ganzhi": gz_y, "dayun": gz,
                           "score": ys.score, "ten_god": ys.ten_god,
                           "stance": ys.stance, "breakdown": dict(ys.breakdown)})
    points.sort(key=lambda p: p["year"])
    return points


# ======================================================================
# 八、CLI
# ======================================================================

def _parse_pillars(args) -> Quad:
    return {"year": (args[0][0], args[0][1]), "month": (args[1][0], args[1][1]),
            "day": (args[2][0], args[2][1]), "hour": (args[3][0], args[3][1])}


def main():
    import sys
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    a = sys.argv[1:]
    if "--pillars" in a:
        i = a.index("--pillars")
        pillars = a[i + 1:i + 5]
        year = a[a.index("--year") + 1] if "--year" in a else None
    else:
        print(__doc__)
        return
    quad = _parse_pillars(pillars)

    s = day_master_strength(quad)
    y = select(quad)
    print("[八字推演链] 四柱 " + " ".join(f"{g}{z}" for g, z in quad.values()))
    print(f"  日主 {quad['day'][0]}({GAN_WUXING[quad['day'][0]]})  旺衰 {s.label}"
          f"(ratio={s.ratio}, 同党{s.support}/异党{s.drain})  强根{'有' if s.has_root else '无'}")
    print(f"  五行力量 " + " ".join(f"{w}{p}" for w, p in element_power(quad).items()))
    print(f"  格局 {y.evidence[1]}  用神 {y.yong}({y.method})  喜{y.xi} 忌{y.ji} 仇{y.chou} 闲{''.join(y.xian)}")
    print(f"  证据 " + " | ".join(y.evidence))
    if year:
        ys = score_year(quad, year, favorable=y.favorable, unfavorable=y.unfavorable)
        print(f"  {year} 年 评分 {ys.score}（{ys.stance}·流年十神{ys.ten_god}）")
        for src, detail, delta in [(t["source"], t["detail"], t["delta"]) for t in ys.terms]:
            print(f"    {delta:+6.2f}  {src}  {detail}")


# ======================================================================
# 九、与 cast.py 的桥接（lunar_python EightChar → quad → 推演链报告）
# ======================================================================

def quad_from_eightchar(b) -> Quad:
    """lunar_python EightChar 对象 → quad 四柱 dict。"""
    return {
        "year": (b.getYearGan(), b.getYearZhi()),
        "month": (b.getMonthGan(), b.getMonthZhi()),
        "day": (b.getDayGan(), b.getDayZhi()),
        "hour": (b.getTimeGan(), b.getTimeZhi()),
    }


def chain_report(quad: Quad, *, month_siling: str | None = None) -> dict:
    """推演链完整报告（结构化 dict）。"""
    s = day_master_strength(quad, month_siling=month_siling)
    y = select(quad, month_siling=month_siling)
    return {
        "四柱": " ".join(f"{g}{z}" for g, z in quad.values()),
        "日主": quad["day"][0], "日主五行": GAN_WUXING[quad["day"][0]],
        "旺衰": s.label, "ratio": s.ratio, "同党": s.support, "异党": s.drain,
        "强根": s.has_root, "根由": list(s.root_note),
        "五行力量": element_power(quad, month_siling=month_siling),
        "十神力量": ten_god_power(quad, month_siling=month_siling),
        "格局": y.evidence[1],
        "用神": y.yong, "取用依据": y.method,
        "喜": y.xi, "忌": y.ji, "仇": y.chou, "闲": "".join(y.xian),
        "证据": list(y.evidence),
        "寒暖": climate_index(quad),
    }


def print_chain_report(quad: Quad, *, month_siling: str | None = None) -> dict:
    """打印推演链报告（cast.py bazi 命令调用），返回报告 dict。"""
    r = chain_report(quad, month_siling=month_siling)
    print("【八字推演链】五行力量量化 → 旺衰五档 → 用神五法（tianzhi-core 式）")
    print(f"  四柱 {r['四柱']}  日主 {r['日主']}({r['日主五行']})")
    gen = ("（" + "、".join(r["根由"]) + "）") if r["根由"] else ""
    print(f"  旺衰 {r['旺衰']}（ratio={r['ratio']}，同党{r['同党']}/异党{r['异党']}）"
          f"  强根{'有' if r['强根'] else '无'}{gen}")
    print(f"  五行力量 " + " ".join(f"{w}{p}" for w, p in r["五行力量"].items()))
    print(f"  格局 {r['格局']}  用神 {r['用神']}（{r['取用依据']}）")
    print(f"  用喜忌仇闲：用{r['用神']} 喜{r['喜']} 忌{r['忌']} 仇{r['仇']} 闲{r['闲']}")
    print(f"  证据 " + " | ".join(r["证据"]))
    return r


if __name__ == "__main__":
    main()

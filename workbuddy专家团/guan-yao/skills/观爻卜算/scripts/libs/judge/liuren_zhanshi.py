# -*- coding: utf-8 -*-
"""大六壬分类占断（11 类类神）—— port tianzhi-core liuren/zhanshi.py（MIT）。

起课回答「盘是什么」，这里回答「这件事在盘上怎么看」。步骤皆出《六壬大全》：
1. 取类神：卷八《事類神》「人事類神兼二三，以入課傳為取用；若是皆入皆不入，不用兼神責將神」。
2. 看类神：入不入课传、旺相休囚、空亡、与日辰生克合。
3. 各类事另有专条者照专条判（青龙求财、天后占婚、玄武盗贼等）。
4. 看三传：初传言事之始、末传决事之终；用生终死、母子顺逆。
5. 看急迟与应期。

每条结论带 code、tone（+1 顺、-1 阻、0 陈述）与出处标签（六壬大全·占事·某）。
本模块不出白话——怎么说给人听是调用方（断卦 LLM）的事。合成总倾向的加法是本包取值，
每条的方向（顺还是阻）照原文。

用法：
  from judge.liuren_zhanshi import zhanshi
  result = zhanshi(r, day_gz, month_gz, year_gz, lmonth, "求财")
"""
from __future__ import annotations

# ======================================================================
# 一、支持表（tianzhi-core 值，逐字移植）
# ======================================================================
GAN: str = "甲乙丙丁戊己庚辛壬癸"
ZHI: str = "子丑寅卯辰巳午未申酉戌亥"

WUXING_GAN: dict[str, str] = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
WUXING_ZHI: dict[str, str] = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}
SHENG: dict[str, str] = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE: dict[str, str] = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

#: 十干寄宫（六壬以寄宫代日干论天地盘）
GAN_JIGONG: dict[str, str] = {
    "甲": "寅", "乙": "辰", "丙": "巳", "丁": "未", "戊": "巳",
    "己": "未", "庚": "申", "辛": "戌", "壬": "亥", "癸": "丑",
}
#: 五行长生 / 墓（水土同宫长生申）
CHANGSHENG: dict[str, str] = {"木": "亥", "火": "寅", "金": "巳", "水": "申", "土": "申"}
MU: dict[str, str] = {"木": "未", "火": "戌", "金": "丑", "水": "辰", "土": "辰"}
#: 天将五行
JIANG_WX: dict[str, str] = {"贵人": "土", "螣蛇": "火", "腾蛇": "火", "朱雀": "火", "六合": "木",
                           "勾陈": "土", "青龙": "木", "天空": "土", "白虎": "金", "太常": "土",
                           "玄武": "水", "太阴": "金", "天后": "水"}
JI_JIANG: set[str] = {"贵人", "六合", "青龙", "太常", "太阴", "天后"}
XIONG_JIANG: set[str] = {"螣蛇", "朱雀", "勾陈", "天空", "白虎", "玄武"}

#: 日德（《六壬大全》，据日干定）
DAY_DE: dict[str, str] = {"甲": "寅", "乙": "申", "丙": "巳", "丁": "亥", "戊": "巳",
                         "己": "寅", "庚": "申", "辛": "巳", "壬": "亥", "癸": "巳"}

LIUHE: dict[str, str] = {"子": "丑", "丑": "子", "寅": "亥", "亥": "寅", "卯": "戌", "戌": "卯",
                        "辰": "酉", "酉": "辰", "巳": "申", "申": "巳", "午": "未", "未": "午"}
SANHE: list[set[str]] = [set("申子辰"), set("寅午戌"), set("巳酉丑"), set("亥卯未")]

#: 天将顺行序（贵人起，顺行），用于「贵前/贵后」定事急迟
TIAN_JIANG: list[str] = ["贵人", "螣蛇", "朱雀", "六合", "勾陈", "青龙", "天空", "白虎",
                         "太常", "玄武", "太阴", "天后"]

# kinliuren 引擎天将简称 → 完整名
_TIANJIANG_ALIAS: dict[str, str] = {
    "貴": "贵人", "蛇": "螣蛇", "雀": "朱雀", "合": "六合", "勾": "勾陈", "龍": "青龙",
    "空": "天空", "虎": "白虎", "常": "太常", "玄": "玄武", "陰": "太阴", "后": "天后",
}

SHI: tuple[str, ...] = ("事业", "求财", "感情", "出行", "寻物",
                        "疾病", "文书", "官司", "阴私", "酒食", "逃亡")

# 每类事的类神：jiang 为将神（按书中次序，前者优先），yao 为兼神（六亲爻），ma 取驿马/天马
# 前 5 类出卷八《事類神》与卷二各将专条；后 6 类出十二天将总纲（六壬大全:2375）。
LEISHEN: dict[str, dict] = {
    "事业": {"jiang": ["青龙", "太常"], "yao": "官", "src": "事类神"},   # 求官龍常及官星
    "求财": {"jiang": ["青龙"], "yao": "财", "src": "事类神"},            # 求財青龍財爻通
    "感情": {"jiang": ["天后"], "yao": None, "src": "事类神"},            # 婚天后
    "出行": {"jiang": ["白虎"], "yao": None, "ma": True, "src": "事类神"},  # 路白虎；天馬驛馬入垣
    "寻物": {"jiang": ["玄武"], "yao": None, "src": "玄武盗贼"},
    # —— 十二天将总纲（六壬大全:2375）——
    "疾病": {"jiang": ["白虎"], "yao": "官", "src": "白虎死丧"},           # 占病切忌白虎贼日
    "文书": {"jiang": ["朱雀"], "yao": "父", "src": "朱雀文书口舌"},        # 朱雀文书口舌
    "官司": {"jiang": ["勾陈"], "yao": "官", "src": "勾陈鬬讼"},            # 勾陈主鬬讼勾连
    "阴私": {"jiang": ["太阴", "天后"], "yao": None, "src": "天后太阴阴私"},  # 天后奸心暗昧、太阴隠晦阴私
    "酒食": {"jiang": ["太常"], "yao": None, "src": "太常酒食"},           # 太常有酒食之筵会
    "逃亡": {"jiang": ["天空"], "yao": None, "src": "天空欺诈逃亡"},        # 天空主欺诈之逃亡
}

S: str = "六壬大全·占事·"


# ======================================================================
# 二、辅助（五行生克 / 六亲 / 旺相休囚死）
# ======================================================================
def _wx(x):
    return WUXING_GAN.get(x) or WUXING_ZHI.get(x) or JIANG_WX.get(x)


def _ke(a, b):
    return KE.get(_wx(a)) == _wx(b)


def _sheng(a, b):
    return SHENG.get(_wx(a)) == _wx(b)


def _he(a, b):
    """两支六合或同在一个三合里。"""
    return LIUHE.get(a) == b or any(a in g and b in g and a != b for g in SANHE)


def _rel(x, gan):
    """x 对日干：生日 / 克日 / 日生 / 日克 / 比和。"""
    if _sheng(x, gan):
        return "生日"
    if _ke(x, gan):
        return "克日"
    if _sheng(gan, x):
        return "日生"
    if _ke(gan, x):
        return "日克"
    return "比和"


def liu_qin(v, gan):
    """v（支/将）对日干之六亲，返回简称：父/官/财/子/兄。"""
    vw, gw = _wx(v), WUXING_GAN[gan]
    if vw == gw:
        return "兄"
    if SHENG[vw] == gw:
        return "父"
    if SHENG[gw] == vw:
        return "子"
    if KE[vw] == gw:
        return "官"
    if KE[gw] == vw:
        return "财"
    return "?"


def wangxiang(target, month_zhi):
    """某一行生在某月令，处于旺相休囚死的哪一档。"""
    ruler = WUXING_ZHI[month_zhi]
    if target == ruler:
        return "旺"
    if SHENG[ruler] == target:
        return "相"
    if SHENG[target] == ruler:
        return "休"
    if KE[target] == ruler:
        return "囚"
    return "死"


# ======================================================================
# 三、_Ke（从 qike 结果里取出判事要用的量）
# ======================================================================
class _Ke:
    def __init__(self, ke):
        self.ke = ke
        self.gan, self.zhi = ke["day_gan"], ke["day_zhi"]
        self.gong = GAN_JIGONG[self.gan]
        self.tdp = ke["tian_di_pan"]                       # 地盘 → 天盘
        self.below = {s: e for e, s in self.tdp.items()}   # 天盘 → 地盘
        self.tj = ke["tian_jiang_map"]                     # 天盘支 → 天将
        self.jiang_at = {j: s for s, j in self.tj.items()}  # 天将 → 所乘天盘支
        cls = ke["four_classes"]
        self.ke_up = {"干上": cls[0]["up"], "干阴": cls[1]["up"],
                      "支上": cls[2]["up"], "支阴": cls[3]["up"]}
        ch = ke["three_chuan"]
        self.chuan = {"初传": ch["chu"]["zhi"], "中传": ch["zhong"]["zhi"], "末传": ch["mo"]["zhi"]}
        self.trio = list(self.chuan.values())
        self.kong = set(ke.get("xun_kong") or [])
        self.month_zhi = ke["ganzhi"]["month"][1]
        self.year_zhi = ke["ganzhi"]["year"][1]
        self.shensha = {s["name"]: s["zhi"] for s in ke.get("shen_sha") or []}

    def where(self, z):
        for k, v in self.chuan.items():
            if v == z:
                return k
        for k, v in self.ke_up.items():
            if v == z:
                return k
        return "局外"

    def void(self, z):
        return z in self.kong or self.below.get(z) in self.kong

    def qi(self, z):
        return wangxiang(WUXING_ZHI[z], self.month_zhi)

    def with_ri_chen(self, z):
        sheng = _sheng(z, self.gan) or _sheng(self.gan, z) or _sheng(z, self.zhi) or _sheng(self.zhi, z)
        he = _he(z, self.gong) or _he(z, self.zhi)
        return sheng, he

    def front_of_gui(self, earth):
        return TIAN_JIANG.index(self.tj[self.tdp[earth]])


def _info(k, name, z, kind):
    return {"name": name, "kind": kind, "zhi": z, "at": k.below.get(z, ""),
            "where": k.where(z), "qi": k.qi(z), "void": k.void(z),
            "jiang": k.tj.get(z, ""), "to_day": _rel(z, k.gan)}


def _pick(k, shi):
    spec = LEISHEN[shi]
    jiangs = [_info(k, j, k.jiang_at[j], "将") for j in spec["jiang"]]
    jiang = next((x for x in jiangs if x["where"] != "局外"), jiangs[0])
    jian = None
    if spec.get("yao"):
        places = list(k.chuan.items()) + list(k.ke_up.items())
        z = next((v for _, v in places if liu_qin(v, k.gan) == spec["yao"]), None)
        if z:
            jian = _info(k, spec["yao"] + "爻", z, "爻")
    elif spec.get("ma"):
        for nm in ("驿马", "天马"):
            z = k.shensha.get(nm)
            if z and k.where(z) != "局外":
                jian = _info(k, "驿马" if nm == "驿马" else "天马", z, "马")
                break
    j_in, y_in = jiang["where"] != "局外", bool(jian and jian["where"] != "局外")
    primary = jian if (y_in and not j_in) else jiang
    return primary, [x for x in [jiang, jian] if x]


def _f(code, tone, src, **args):
    return {"code": code, "tone": tone, "src": S + src, "args": args}


# ======================================================================
# 四、各类事专条
# ======================================================================
def _common(k, p, shi):
    out = []
    good_qi = p["qi"] in ("旺", "相")
    if p["where"] == "局外":
        out.append(_f("类神局外", 0 if good_qi else -1, "事类神", name=p["name"], qi=p["qi"]))
    else:
        out.append(_f("类神入传", 1, "事类神", name=p["name"], where=p["where"]))
        out.append(_f("类神旺衰", 1 if good_qi else -1, "旺衰", name=p["name"], qi=p["qi"]))
    if p["void"]:
        out.append(_f("类神空亡", -2, "空亡", name=p["name"]))
    return out


def _shiye(k, p):
    out = []
    for j in ("青龙", "太常"):
        z = k.jiang_at[j]
        if z == k.year_zhi:
            out.append(_f("岁作龙常", 1, "龙常占官", jiang=j))
    if p["kind"] == "将":
        sheng, he = k.with_ri_chen(p["zhi"])
        good = sheng or he
        out.append(_f("龙常和日" if good else "龙常不和", 1 if good else -1, "龙常占官", name=p["name"]))
    g = k.jiang_at["贵人"]
    r = _rel(g, k.gan)
    if r == "生日":
        out.append(_f("贵人生日", 1, "贵人"))
    elif r == "克日":
        out.append(_f("贵人克日", -1, "贵人"))
    if k.void(g):
        out.append(_f("贵人空亡", -1, "贵人空亡"))
    return out


def _qiucai(k, _p):
    z = k.jiang_at["青龙"]
    sheng, he = k.with_ri_chen(z)
    at = k.below[z]
    conds = {
        "乘旺相气": k.qi(z) in ("旺", "相"),
        "临旺相乡": k.qi(at) in ("旺", "相"),
        "与日辰生合": sheng or he,
        "入日辰三传": k.where(z) != "局外",
    }
    lack = [c for c, ok in conds.items() if not ok]
    if not lack:
        return [_f("青龙求财全", 2, "青龙求财")]
    if not conds["入日辰三传"]:
        return [_f("青龙闲地", -2, "青龙求财", lack=lack)]
    return [_f("青龙求财缺", -1 if len(lack) > 1 else 0, "青龙求财", lack=lack)]


def _ganqing(k, p):
    out = []
    z = k.jiang_at["天后"]
    sheng = _sheng(z, k.gan) or _sheng(k.gan, z)
    he = _he(z, k.gong) or _he(z, k.zhi)
    if sheng or he:
        out.append(_f("后日生合", 2, "天后占婚"))
    else:
        out.append(_f("后日不合", -1, "天后占婚"))
    if _ke(z, k.gan):
        out.append(_f("后克日", 0, "天后占婚"))
    elif _ke(k.gan, z):
        out.append(_f("日克后", 0, "天后占婚"))
    lh = k.jiang_at["六合"]
    if k.where(lh) in k.chuan and k.qi(lh) in ("旺", "相") and (_sheng(lh, k.gan) or _sheng(k.gan, lh)):
        out.append(_f("六合主婚", 1, "六合婚姻"))
    if z in k.trio and lh in k.trio:
        out.append(_f("后合同传", -1, "狡童佚女"))
    return out


def _chuxing(k, p):
    out = []
    ma = [(nm, k.shensha.get(nm)) for nm in ("驿马", "天马")]
    moving = [(nm, z) for nm, z in ma if z and z in k.trio]
    if moving:
        nm, z = moving[0]
        out.append(_f("马入传", 1, "马入垣", ma=nm, zhi=z, void=k.void(z)))
        if k.void(z):
            out.append(_f("马空", -1, "空亡", ma=nm))
    else:
        out.append(_f("马不入传", 0, "马入垣"))
    z = k.jiang_at["白虎"]
    r = _rel(z, k.gan)
    if r == "克日":
        out.append(_f("白虎克日", -1, "白虎道路"))
    elif r == "生日":
        out.append(_f("白虎生日", 1, "白虎道路"))
    w = k.where(z)
    if w in k.chuan:
        out.append(_f("行人", 0, "白虎行人", where=w))
    return out


def _xunwu(k, p):
    s1 = k.jiang_at["玄武"]
    out = [_f("玄武所在", 0, "玄武盗贼", where=k.where(s1), zhi=s1, at=k.below[s1])]
    s2 = k.tdp[s1]
    s3 = k.tdp[s2]
    pairs = [(s1, s2), (s2, s3)]
    sheng = all(_sheng(a, b) or _sheng(b, a) for a, b in pairs)
    ke = any(_ke(a, b) or _ke(b, a) for a, b in pairs)
    ji = all(k.tj[x] in JI_JIANG for x in (s2, s3))
    xiong = any(k.tj[x] in XIONG_JIANG for x in (s2, s3))
    if sheng and ji:
        out.append(_f("玄武三传生吉", -2, "玄武盗贼", trio=[s1, s2, s3]))
    elif ke and xiong:
        out.append(_f("玄武三传克凶", 2, "玄武盗贼", trio=[s1, s2, s3]))
    if _ke(k.gan, s1):
        out.append(_f("日制玄武", 1, "玄武盗贼"))
    gou = k.jiang_at["勾陈"]
    if _ke(gou, s1):
        out.append(_f("勾制玄武", 1, "勾陈捕贼"))
    if gou == k.ke_up["干上"]:
        out.append(_f("勾临日干", 1, "勾陈捕贼"))
    if s1 == DAY_DE.get(k.gan) and k.where(s1) in ("干上", "支上"):
        out.append(_f("玄武附德", 2, "玄武附德"))
    for j, key, code in (("青龙", "青龙占盗", "龙入课"), ("六合", "六合占盗", "合入课"),
                         ("太阴", "太阴占盗", "阴入课")):
        if k.where(k.jiang_at[j]) != "局外":
            out.append(_f(code, -1, key))
    return out


def _jibing(k, p):
    """疾病忌白虎（六壬大全：占病切忌白虎贼日，兼虎带杀贼日皆凶）。"""
    out = []
    z = k.jiang_at["白虎"]
    r = _rel(z, k.gan)
    if r == "克日":
        out.append(_f("白虎贼日", -1, "疾病"))
    elif r == "生日":
        out.append(_f("白虎生日", 0, "疾病"))
    if k.void(z):
        out.append(_f("白虎空亡", 0, "空亡"))
    if z in k.trio:
        out.append(_f("白虎入传", -1, "疾病"))
    return out


def _wenshu(k, p):
    """文书口舌看朱雀（六壬大全：朱雀文书口舌）。"""
    out = []
    z = k.jiang_at["朱雀"]
    if k.where(z) != "局外":
        out.append(_f("朱雀入传", 1 if k.qi(z) in ("旺", "相") else 0, "文书口舌"))
    r = _rel(z, k.gan)
    if r == "克日":
        out.append(_f("朱雀克日", -1, "文书口舌"))
    elif r == "生日":
        out.append(_f("朱雀生日", 1, "文书口舌"))
    return out


def _guansi(k, p):
    """官司争讼看勾陈（六壬大全：勾陈主鬬讼勾连）。"""
    out = []
    z = k.jiang_at["勾陈"]
    r = _rel(z, k.gan)
    if r == "克日":
        out.append(_f("勾陈克日", -1, "鬬讼"))
    elif r == "生日":
        out.append(_f("勾陈生日", 1, "鬬讼"))
    if k.where(z) != "局外":
        out.append(_f("勾陈入传", 0, "鬬讼"))
    return out


def _yinsi(k, p):
    """阴私看太阴、天后（六壬大全：天后奸心暗昧，太阴隠晦阴私）。"""
    out = []
    for j in ("太阴", "天后"):
        z = k.jiang_at[j]
        if k.where(z) != "局外":
            out.append(_f(f"{j}入传", 0, "阴私", jiang=j))
        if _ke(z, k.gan):
            out.append(_f(f"{j}克日", -1, "阴私", jiang=j))
    return out


def _jiushi(k, p):
    """酒食看太常（六壬大全：太常有酒食之筵会）。"""
    out = []
    z = k.jiang_at["太常"]
    if k.where(z) != "局外":
        out.append(_f("太常入传", 1 if k.qi(z) in ("旺", "相") else 0, "酒食"))
    if k.void(z):
        out.append(_f("太常空亡", -1, "空亡"))
    return out


def _taowang(k, p):
    """逃亡看天空（六壬大全：天空主欺诈之逃亡）。"""
    out = []
    z = k.jiang_at["天空"]
    if k.where(z) != "局外":
        out.append(_f("天空入传", 0, "逃亡"))
    if _ke(z, k.gan):
        out.append(_f("天空克日", -1, "逃亡"))
    return out


SPECIFIC = {"事业": _shiye, "求财": _qiucai, "感情": _ganqing, "出行": _chuxing, "寻物": _xunwu,
            "疾病": _jibing, "文书": _wenshu, "官司": _guansi, "阴私": _yinsi, "酒食": _jiushi, "逃亡": _taowang}


# ======================================================================
# 五、三传始终 / 急迟 / 应期
# ======================================================================
def _tone_of(k, z):
    j = k.tj.get(z, "")
    good_qi = k.qi(z) in ("旺", "相")
    if j in JI_JIANG:
        return 1 if good_qi else 0
    if j in XIONG_JIANG:
        return 0 if good_qi else -1
    return 0


def shengsi(gan, chu, mo):
    w = _wx(gan)
    if chu == CHANGSHENG[w] and mo == MU[w]:
        return "用生终死"
    if chu == MU[w] and mo == CHANGSHENG[w]:
        return "用死终生"
    return None


def muzi(chu, mo):
    if _sheng(chu, mo):
        return "母传子"
    if _sheng(mo, chu):
        return "子传母"
    return None


def ying_ri(gan, good):
    yang = GAN.index(gan) % 2
    w = _wx(gan)
    return next((g for g in GAN if GAN.index(g) % 2 == yang and
                 (SHENG[WUXING_GAN[g]] == w if good else KE[WUXING_GAN[g]] == w)), None)


def _course(k):
    out = []
    chu, zhong, mo = k.trio
    a, b = _tone_of(k, chu), _tone_of(k, mo)
    shape = {(1, 1): "始终皆顺", (-1, -1): "始终皆阻", (-1, 1): "先阻后顺", (1, -1): "先顺后阻"}.get((a, b))
    if shape is None:
        shape = "先阻后平" if a < 0 else "先顺后平" if a > 0 else "先平后阻" if b < 0 else "先平后顺" if b > 0 else "平"
    tone = {"始终皆顺": 2, "先阻后顺": 1, "先平后顺": 1, "先顺后平": 0, "平": 0,
            "先阻后平": -1, "先顺后阻": -1, "先平后阻": -1, "始终皆阻": -2}[shape]
    out.append(_f("三传始终", tone, "始终" if shape in ("先阻后顺", "先顺后阻") else "物类",
                  shape=shape, chu=[chu, k.tj.get(chu, "")], mo=[mo, k.tj.get(mo, "")]))
    sx = shengsi(k.gan, chu, mo)
    if sx:
        out.append(_f(sx, -1 if sx == "用生终死" else 1, "生死"))
    mz = muzi(chu, mo)
    if mz:
        out.append(_f(mz, 1 if mz == "母传子" else -1, "母子"))
    if tone < 0:
        de = DAY_DE.get(k.gan)
        if de in k.trio or any(_sheng(x, k.gan) for x in k.trio):
            out.append(_f("三传有救", 1, "三传有救"))
    return out


def _pace(k):
    pts = [k.below[k.trio[0]], k.gong, k.zhi]
    d = [k.front_of_gui(e) for e in pts]
    if all(1 <= x <= 6 for x in d):
        return _f("事急", 0, "急迟")
    if all(7 <= x <= 11 for x in d):
        return _f("事迟", 0, "急迟")
    return None


def _timing(k, good):
    out = []
    chu = k.trio[0]
    if chu == k.year_zhi:
        out.append(_f("应在年内", 0, "应期", zhi=chu))
    if chu == k.month_zhi:
        out.append(_f("应在月内", 0, "应期", zhi=chu))
    if chu == k.zhi:
        out.append(_f("应在旬内", 0, "应期", zhi=chu))
    if chu == k.gong:
        out.append(_f("应在朝夕", 0, "应期", zhi=chu))
    g = ying_ri(k.gan, good)
    if g:
        out.append(_f("应日", 0, "应日", gan=g, good=good))
    return out


# ======================================================================
# 六、课体象辞（卷五至卷八各课「象曰」，原样截取）
# ======================================================================
KETI_SHI: dict[str, dict] = {
    "元首": {"事业": "官職首擢", "求财": "市賈出色名利超羣", "感情": "婚諧鸞鳯", "通": "天地得位品物咸新"},
    "重审": {"通": "諸般謀望先難後成"},
    "知一": {"寻物": "尋人失物近處堪求", "通": "事向朋謀"},
    "涉害": {"事业": "謀為利名多費機闗", "求财": "謀為利名多費機闗", "感情": "婚姻有阻", "通": "風波險惡度渉艱難"},
    "遥克": {"事业": "文書虚謀", "通": "憂喜未實"},
    "昴星": {"出行": "闗梁閉塞越度稽留", "通": "家居守静方免閒憂"},
    "别责": {"求财": "財物不全", "感情": "求婚别娶", "通": "謀為處正"},
    "八专": {"事业": "成功異路顯擢士林", "寻物": "物失内尋", "通": "二人同心其利斷金"},
    "伏吟": {"事业": "科舉高中求名榮歸", "通": "律身謹慎動作無虞"},
    "返吟": {"求财": "得物尤失敗物反成", "寻物": "得物尤失敗物反成", "通": "髙岸為谷深谷為陵"},
    "铸印": {"事业": "官職高擢詔命重宣"},
    "斫轮": {"事业": "禄位加增官職超擢", "求财": "財喜懽躍"},
    "轩盖": {"事业": "朱輪稳上詔用榮宣", "求财": "求財大獲", "出行": "行者必旋"},
    "引从": {"事业": "官職陞遷名利榮耀", "感情": "婚招金玉", "出行": "出行取財"},
    "闭口": {"寻物": "尋人没影失物潛藏", "通": "事跡難明"},
    "三交": {"事业": "謀事不明", "求财": "求財無益", "通": "謀事不明"},
    "淫泆": {"感情": "嫁娶不吉", "寻物": "捕捉難獲"},
    "度厄": {"出行": "行者多災", "通": "類神旺相禍去福來"},
    "无禄": {"通": "求謀不遂動作多疑"},
    "六仪": {"事业": "干貴逢時", "通": "兆多喜慶"},
    "三奇": {"事业": "士有竒遇", "感情": "婚求淑女", "通": "萬事和合千殃觧除"},
    "殃咎": {"事业": "營幹不一", "出行": "出行不樂", "通": "營幹不一"},
    "鬼墓": {"寻物": "捕盗深藏", "出行": "行人可至", "通": "謀為遲滯"},
    "全局": {"事业": "有官官易就", "求财": "求財有財財易得", "感情": "利合婚姻", "通": "吉事必成凶事難棄"},
    "玄胎": {"事业": "官加恩爵", "求财": "財利叠興", "感情": "婚獲娉婷"},
    "连珠": {"通": "凶則重重吉當累累"},
}


def keti_says(keti, shi):
    out = []
    for h in keti:
        t = KETI_SHI.get(h["name"], {})
        s = t.get(shi) or t.get("通")
        if s:
            out.append({"keti": h["name"], "text": s, "specific": shi in t, "src": f"六壬大全·{h['name']}课"})
    return out


# ======================================================================
# 七、read 汇总
# ======================================================================
def read(ke, shi):
    """qike 结果 + 所问之事 → 这一课对此事的论断（结构化，带出处）。"""
    if shi not in SHI:
        raise ValueError(f"所问之事只能是 {SHI} 之一：{shi!r}")
    k = _Ke(ke)
    primary, all_ls = _pick(k, shi)
    facts = ([] if shi == "寻物" else _common(k, primary, shi)) + SPECIFIC[shi](k, primary)
    course = _course(k)
    score = sum(f["tone"] for f in facts + course)
    trend = "顺" if score >= 4 else "可成" if score >= 2 else "未定" if score >= 0 else "多阻" if score >= -2 else "难"
    if primary["void"] and trend in ("顺", "可成"):
        trend = "未定"
    pace = _pace(k)
    timing = _timing(k, score >= 0)
    return {"shi": shi, "leishen": all_ls, "primary": primary, "facts": facts,
            "course": course, "pace": pace, "timing": timing, "score": score, "trend": trend,
            "keti": keti_says(ke.get("keti") or [], shi)}


# ======================================================================
# 八、适配 kinliuren 引擎输出 → tianzhi-core 的 ke dict
# ======================================================================
def _xunkong(day_gz):
    """旬空两字（由日干支旬首定）。"""
    gan, zhi = day_gz[0], day_gz[1]
    xun_shou = (ZHI.index(zhi) - GAN.index(gan)) % 12
    return ZHI[(xun_shou - 2) % 12] + ZHI[(xun_shou - 1) % 12]


def from_kinliuren(r, day_gz, month_gz, year_gz, lmonth=1):
    """kinliuren 引擎的 r → zhanshi 需要的 ke dict。

    r 的字段（见 pan/liuren.py）：格局(课体名列表)、三傳(初/中/末传[支,天将简称,六亲,遁干])、
    四課、天地盤(天盤/地盤/天將 三并行数组)、日馬、節氣、日期。
    """
    day_gan, day_zhi = day_gz[0], day_gz[1]
    tp = r["天地盤"]
    tian, di, jiang = tp["天盤"], tp["地盤"], tp["天將"]
    tdp = {di[i]: tian[i] for i in range(12)}                      # 地盘 → 天盘
    tian_jiang_map = {tian[i]: _TIANJIANG_ALIAS.get(jiang[i], jiang[i]) for i in range(12)}

    # 四课：干上/干阴/支上/支阴（由寄宫与天地盘推出，同 tianzhi-core pan.py）
    jigong = GAN_JIGONG[day_gan]
    four = [{"up": tdp[jigong]}, {"up": tdp[tdp[jigong]]},
            {"up": tdp[day_zhi]}, {"up": tdp[tdp[day_zhi]]}]

    ch = r["三傳"]
    three = {"chu": {"zhi": ch["初傳"][0]}, "zhong": {"zhi": ch["中傳"][0]}, "mo": {"zhi": ch["末傳"][0]}}

    # 神煞：驿马（r["日馬"]）+ 天马（据月支）
    from judge import liuren_shensha
    shensha = [{"name": "驿马", "zhi": r["日馬"]}]
    tianma = liuren_shensha._TIANMA.get(month_gz[1])
    if tianma:
        shensha.append({"name": "天马", "zhi": tianma})

    keti = [{"name": n} for n in (r.get("格局") or [])]

    return {
        "day_gan": day_gan, "day_zhi": day_zhi,
        "tian_di_pan": tdp, "tian_jiang_map": tian_jiang_map,
        "four_classes": four, "three_chuan": three,
        "xun_kong": list(_xunkong(day_gz)),
        "ganzhi": {"month": [month_gz[0], month_gz[1]], "year": [year_gz[0], year_gz[1]]},
        "shen_sha": shensha, "keti": keti,
    }


def zhanshi(r, day_gz, month_gz, year_gz, lmonth=1, shi="求财"):
    """kinliuren r + 问事 → 分类占断结果。"""
    return read(from_kinliuren(r, day_gz, month_gz, year_gz, lmonth), shi)


def zhanshi_from_dt(dt, r, shi):
    """由占时 dt + 已排盘的 r 直接分类占断（重推干支，供 cast.py liuren 调用）。"""
    import datetime as _dt
    dt = dt or _dt.datetime.now()
    from lunar_python import Solar
    solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    lunar = solar.getLunar()
    day_gz = lunar.getDayInGanZhi()
    month_gz = lunar.getMonthInGanZhi()
    year_gz = lunar.getYearInGanZhi()
    return zhanshi(r, day_gz, month_gz, year_gz, lunar.getMonth(), shi)


if __name__ == "__main__":
    import sys
    import datetime as _dt
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    shi = sys.argv[1] if len(sys.argv) > 1 else "求财"
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    from engines.taiyi.kinliuren import Liuren
    from lunar_python import Solar
    solar = Solar.fromYmdHms(2026, 10, 14, 12, 0, 0)
    lunar = solar.getLunar()
    day_gz, hour_gz = lunar.getDayInGanZhi(), lunar.getTimeInGanZhi()
    month_gz, year_gz = lunar.getMonthInGanZhi(), lunar.getYearInGanZhi()
    lr = Liuren(lunar.getPrevJieQi().getName(), lunar.getMonth(), day_gz, hour_gz)
    r = lr.result(1)
    res = zhanshi(r, day_gz, month_gz, year_gz, lunar.getMonth(), shi)
    print(f"[大六壬分类占断] 问事={shi} 总分={res['score']} 趋势={res['trend']}")
    leishen_str = "、".join(f"{x['name']}({x['where']},{x['qi']})" for x in res["leishen"])
    print(f"  类神：{leishen_str}")
    for f in res["facts"]:
        print(f"    [{f['tone']:+d}] {f['code']}（{f['src']}）")
    for c in res["course"]:
        print(f"    [{c['tone']:+d}] {c['code']}（{c['src']}）")
    if res["pace"]:
        print(f"    急迟：{res['pace']['code']}")
    if res["timing"]:
        print(f"    应期：{'、'.join(t['code'] for t in res['timing'])}")

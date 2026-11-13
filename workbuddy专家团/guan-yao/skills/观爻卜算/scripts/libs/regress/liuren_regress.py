# -*- coding: utf-8 -*-
"""大六壬 720/8640 课全量回归 + 结构不变量 + 历史课体对照。

三层体检（不依赖外部引擎，用「独立实现的九宗门选择逻辑」+「古籍案例库课体真值」）：
  1. 穷举体检 sweep()：12 节气(月将) × 60 甲子日 × 12 时辰 = 8640 课，
     统计崩溃(异常)、漏课(八法全「不適用」)、课体分布。
  2. 结构不变量 check_structural()：四课是否合法(独立重算四课逐字比对)、
     三传是否 3 支、初传是否∈四课上神、顺传宗门三传是否递进。
  3. 历史课体对照 cross_check_cases()：解析 案例库/大六壬/*.md 的「课式」行，
     按(日,月将,时)重排，核对引擎课体宗门是否与古籍记录一致。

用法：
  python scripts/libs/liuren_regress.py            # 全部三层
  python scripts/libs/liuren_regress.py sweep      # 只跑穷举体检
  python scripts/libs/liuren_regress.py cases      # 只跑历史对照
"""
import sys
import os
import re
import datetime
import collections

# 本文件在 regress/ 子目录，需把上级 libs/ 加进 sys.path 才能 `from engines.taiyi.kinliuren`，
# 否则 docs 里的 `python scripts/libs/regress/liuren_regress.py` 直跑会 ModuleNotFoundError。
_LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from lunar_python import Solar
from engines.taiyi.kinliuren import Liuren

# —— 基础常量（独立于引擎）——
_GAN = "甲乙丙丁戊己庚辛壬癸"
_ZHI = "子丑寅卯辰巳午未申酉戌亥"
# 干支五行（干五行 + 支五行）
_GAN_WX = {"甲乙": "木", "丙丁": "火", "戊己": "土", "庚辛": "金", "壬癸": "水"}
_ZHI_WX = {"寅卯": "木", "巳午": "火", "申酉": "金", "亥子": "水", "辰戌丑未": "土"}
# 十干寄宫
_JIGONG = {"甲": "寅", "乙": "辰", "丙": "巳", "丁": "未", "戊": "巳",
           "己": "未", "庚": "申", "辛": "戌", "壬": "亥", "癸": "丑"}
# 月将 -> 节气（用引擎 moon_general_dict 的繁体键，见引擎 sky_pan_list 繁简不一致）
_JIANG2JIEQI = {"亥": "雨水", "戌": "春分", "酉": "穀雨", "申": "小滿", "未": "夏至",
                "午": "大暑", "巳": "處暑", "辰": "秋分", "卯": "霜降", "寅": "小雪",
                "丑": "冬至", "子": "大寒"}
# 五鼠遁：日干起时干
_WUSHUDUN = {"甲": "甲", "己": "甲", "乙": "丙", "庚": "丙", "丙": "戊", "辛": "戊",
             "丁": "庚", "壬": "庚", "戊": "壬", "癸": "壬"}
# 五行相克
_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
# 孟仲季
_MENGZHONGJI = {"寅申巳亥": "孟", "子午卯酉": "仲", "辰戌丑未": "季"}
# 顺传宗门（三传按递进）；昴星/别责/伏吟/返吟 为特殊三传。用引擎输出的繁体宗门名。
_SHUNCHUAN = {"賊尅", "比用", "涉害", "遙尅", "八專"}


def gan_wx(g):
    for k, v in _GAN_WX.items():
        if g in k:
            return v
    return None


def zhi_wx(z):
    for k, v in _ZHI_WX.items():
        if z in k:
            return v
    return None


def wx(gz):
    """干支五行（干优先，其次支）"""
    if gz in _GAN:
        return gan_wx(gz)
    return zhi_wx(gz)


def yinyang(gz):
    """干支阴阳：奇位为阳。干甲=1=阳，支子=1=阳。"""
    if gz in _GAN:
        return "阳" if _GAN.index(gz) % 2 == 0 else "阴"
    return "阳" if _ZHI.index(gz) % 2 == 0 else "阴"


def mengzhongji(zhi):
    for k, v in _MENGZHONGJI.items():
        if zhi in k:
            return v
    return None


def hour_gan(day_gan, hour_zhi):
    """五鼠遁：日干起时干。"""
    start = _WUSHUDUN[day_gan]
    gi = _GAN.index(start)
    zi = _ZHI.index(hour_zhi)
    return _GAN[(gi + zi) % 10]


def all_jiazi():
    return [_GAN[i % 10] + _ZHI[i % 12] for i in range(60)]


# —— 独立四课重算 ——
def ref_earth_sky(jiang, shi_zhi):
    """独立天地盘：地盘从时支顺排，天盘从月将顺排；返回 earth->sky 映射。"""
    earth = [_ZHI[(_ZHI.index(shi_zhi) + i) % 12] for i in range(12)]
    sky = [_ZHI[(_ZHI.index(jiang) + i) % 12] for i in range(12)]
    return dict(zip(earth, sky))


def ref_sike(jiang, shi_zhi, day_gan, day_zhi):
    """独立四课：[课4, 课3, 课2, 课1]，每课=上神支+下神(干/支)。"""
    e2s = ref_earth_sky(jiang, shi_zhi)
    yike = e2s[_JIGONG[day_gan]] + day_gan          # 第1课
    erke = e2s[yike[0]] + yike[0]                   # 第2课
    sanke = e2s[day_zhi] + day_zhi                  # 第3课
    sike = e2s[sanke[0]] + sanke[0]                 # 第4课
    return [sike, sanke, erke, yike]


def ke_relation(ke):
    """上克下/下贼上/比和/生 关系。ke='上神下神'。"""
    up, dn = wx(ke[0]), wx(ke[1])
    if _KE.get(dn) == up:            # 下克上 = 下贼上
        return "下贼上"
    if _KE.get(up) == dn:            # 上克下
        return "上克下"
    return "比和"


# —— 独立九宗门初传（覆盖贼克/比用/涉害/遥克；伏吟返吟八专昴星别责另判）——
def ref_zongmen_chuchuan(jiang, shi_zhi, day_gan, day_zhi):
    """独立九宗门选择。返回 (宗门, 课体名, [初传, 中传, 末传]) 或 None=无法独立判定。"""
    e2s = ref_earth_sky(jiang, shi_zhi)
    sike = ref_sike(jiang, shi_zhi, day_gan, day_zhi)   # [4,3,2,1]
    rels = [ke_relation(k) for k in sike]                # 与 sike 同序
    zeke = [i for i, r in enumerate(rels) if r == "下贼上"]   # 下贼上课索引
    shangke = [i for i, r in enumerate(rels) if r == "上克下"]  # 上克下课索引
    dy_yy = yinyang(day_gan)

    # 伏吟 / 返吟（天地盘特判）
    if jiang == shi_zhi:
        # 伏吟：无克，刚日(自任)取干上神、柔日(自信)取支上神
        return ("伏吟", "伏吟", _fuyin_chuan(e2s, day_gan, day_zhi))
    if jiang == _ZHI[(_ZHI.index(shi_zhi) + 6) % 12]:
        # 返吟：有克取克课、无克为井栏射（丑未日）
        return ("返吟", "返吟", _fanyin_chuan(e2s, day_zhi, sike, rels, day_gan))

    # 贼克 / 比用 / 涉害（下贼上优先于上克下）
    if zeke:
        if len(zeke) == 1:
            return ("贼克", "重审", _shun_chuan(e2s, sike[zeke[0]][0]))
        if len(zeke) >= 2:
            bi = [i for i in zeke if yinyang(sike[i][0]) == dy_yy]
            if len(bi) == 1:
                return ("比用", "知一", _shun_chuan(e2s, sike[bi[0]][0]))
            return ("涉害", "涉害", _shehai_v2(e2s, sike, zeke, day_gan, day_zhi, dy_yy))
    elif shangke:
        if len(shangke) == 1:
            return ("贼克", "元首", _shun_chuan(e2s, sike[shangke[0]][0]))
        if len(shangke) >= 2:
            bi = [i for i in shangke if yinyang(sike[i][0]) == dy_yy]
            if len(bi) == 1:
                return ("比用", "知一", _shun_chuan(e2s, sike[bi[0]][0]))
            return ("涉害", "涉害", _shehai_v2(e2s, sike, shangke, day_gan, day_zhi, dy_yy))
    else:
        # 无克 → 八专 / 遥克 / 昴星 / 别责
        # 八专：干支同位（寄宫==日支）且四课无克（须在无克分支内判，勿提前到有克前）
        if _JIGONG[day_gan] == day_zhi:
            return ("八专", "八专", _bazhuan_chuan(e2s, day_gan, day_zhi))
        # 遥克：先蒿矢(上神克日)后弹射(日克上神)，多个取与日干比者（阳日阳阴日阴）
        shangshen = [k[0] for k in sike]
        tan = [i for i, s in enumerate(shangshen) if _KE.get(wx(s)) == wx(day_gan)]   # 上神克干 -> 蒿矢
        she = [i for i, s in enumerate(shangshen) if _KE.get(wx(day_gan)) == wx(s)]    # 干克上神 -> 弹射
        if tan:
            bi = [i for i in tan if yinyang(shangshen[i]) == yinyang(day_gan)]
            return ("遥克", "蒿矢", _shun_chuan(e2s, shangshen[bi[0] if bi else tan[0]]))
        if she:
            bi = [i for i in she if yinyang(shangshen[i]) == yinyang(day_gan)]
            return ("遥克", "弹射", _shun_chuan(e2s, shangshen[bi[0] if bi else she[0]]))
        # 别责：四课不备（上神去重<4）且无克无遥克
        if len({k[0] for k in sike}) < 4:
            return ("别责", "别责", _bieze_chuan(e2s, day_gan, day_zhi))
        return ("昴星", "昴星", _maoxing_chuan(e2s, day_gan, day_zhi))


def _shun_chuan(e2s, first):
    """顺传三传：中传=天盘(初传地盘位)，末传=天盘(中传地盘位)。"""
    return [first, e2s[first], e2s[e2s[first]]]


def _shehai_chuan(e2s, sike, idxs):
    """涉害：取涉害深者（简化：孟仲季先孟后仲后季），返回三传。"""
    cands = [sike[i][0] for i in idxs]
    for grade in ("孟", "仲", "季"):
        hit = [c for c in cands if mengzhongji(c) == grade]
        if hit:
            return _shun_chuan(e2s, hit[0])
    return _shun_chuan(e2s, cands[0])


# —— 涉害数（受克重数）：本气五行 + 寄宫干五行，见《六壬大全》涉害课 ——
_BENQI = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
          "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}
# 十干寄宫：每个地支所寄之干（子午卯酉不寄干）
_JIGAN = {"丑": ["癸"], "寅": ["甲"], "辰": ["乙"], "巳": ["丙", "戊"],
          "未": ["丁", "己"], "申": ["庚"], "戌": ["辛"], "亥": ["壬"]}
_GWX = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
        "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}


def _shehai_depth(shangshen, suo_lin):
    """涉害数：上神从所临地盘顺行归本家，途中克其上神五行的重数（本气+寄宫干）。"""
    wx = zhi_wx(shangshen)
    i = (_ZHI.index(suo_lin) + 1) % 12
    target = _ZHI.index(shangshen)
    depth = 0
    while i != target:
        z = _ZHI[i]
        if _KE.get(_BENQI[z]) == wx:
            depth += 1
        for g in _JIGAN.get(z, []):
            if _KE.get(_GWX[g]) == wx:
                depth += 1
        i = (i + 1) % 12
    return depth


def _shehai_v2(e2s, sike, idxs, day_gan, day_zhi, day_yy):
    """涉害课（见机/察微/缀瑕）：先取涉害数最深者，同深取孟→仲→季，再同（复等）阳日干上/阴日支上。"""
    cands = [sike[i][0] for i in idxs]
    # 每个上神的地盘位置（天盘支坐在地盘支上）
    e2s_inv = {v: k for k, v in e2s.items()}
    depths = [(_shehai_depth(s, e2s_inv.get(s, s)), s) for s in cands]
    maxd = max(d for d, s in depths)
    deep = [s for d, s in depths if d == maxd]
    if len(deep) == 1:
        return _shun_chuan(e2s, deep[0])
    # 同深 → 孟→仲→季
    for grade in ("孟", "仲", "季"):
        hit = [s for s in deep if mengzhongji(s) == grade]
        if hit:
            return _shun_chuan(e2s, hit[0])
    # 复等（缀瑕）：阳日取干上神（第1课上神），阴日取支上神（第3课上神）
    first = sike[3][0] if day_yy == "阳" else sike[1][0]
    return _shun_chuan(e2s, first)


def _fuyin_chuan(e2s, day_gan, day_zhi):
    """伏吟：无克，刚日(自任)取干上神、柔日(自信)取支上神为初传。"""
    if yinyang(day_gan) == "阳":
        first = e2s[_JIGONG[day_gan]]
    else:
        first = e2s[day_zhi]
    return _shun_chuan(e2s, first)


def _fanyin_chuan(e2s, day_zhi, sike, rels, day_gan):
    """返吟：有克取克课初传、中末取冲；无克为井栏射（丑日取巳上神、未日取亥上神）。"""
    chong = lambda z: _ZHI[(_ZHI.index(z) + 6) % 12]
    for i, r in enumerate(rels):
        if r in ("下贼上", "上克下"):
            first = sike[i][0]
            return [first, chong(first), first]
    # 无克 → 井栏射（返吟无克惟丑未日）：丑日取巳上神、未日取亥上神；中传支上神、末传干上神
    if day_zhi == "丑":
        first = e2s["巳"]
    elif day_zhi == "未":
        first = e2s["亥"]
    else:
        first = e2s[day_zhi]
    return [first, e2s[day_zhi], e2s[_JIGONG[day_gan]]]


def _maoxing_chuan(e2s, day_gan, day_zhi):
    """昴星（虎视）：刚日取酉上神、柔日取酉下神为初传。
    刚日：初=酉上神，中=支上神，末=干上神；柔日：初=酉下神，中=干上神，末=支上神。"""
    e2s_inv = {v: k for k, v in e2s.items()}
    if yinyang(day_gan) == "阳":
        return [e2s["酉"], e2s[day_zhi], e2s[_JIGONG[day_gan]]]
    return [e2s_inv["酉"], e2s[_JIGONG[day_gan]], e2s[day_zhi]]


def _bazhuan_chuan(e2s, day_gan, day_zhi):
    """八专：刚日干上神顺数三辰、柔日支上神逆数三辰为初传，中末皆干上神。"""
    ganshang = e2s[_JIGONG[day_gan]]
    if yinyang(day_gan) == "阳":
        first = _ZHI[(_ZHI.index(ganshang) + 2) % 12]
    else:
        first = _ZHI[(_ZHI.index(e2s[day_zhi]) - 2) % 12]
    return [first, ganshang, ganshang]


def _bieze_chuan(e2s, day_gan, day_zhi):
    """别责：刚日取干合之干寄宫上神、柔日取支三合前一辰(支+4)上神为初传，中末皆干上神。"""
    ganshang = e2s[_JIGONG[day_gan]]
    if yinyang(day_gan) == "阳":
        he = {"甲": "己", "己": "甲", "乙": "庚", "庚": "乙", "丙": "辛",
              "辛": "丙", "丁": "壬", "壬": "丁", "戊": "癸", "癸": "戊"}
        first = e2s[_JIGONG[he[day_gan]]]
    else:
        first = e2s[_ZHI[(_ZHI.index(day_zhi) + 4) % 12]]
    return [first, ganshang, ganshang]


# —— 交叉校验：独立九宗门实现 vs kinliuren 引擎 ——
_ZONGMEN_SIM = {"賊尅": "贼克", "比用": "比用", "涉害": "涉害", "遙尅": "遥克",
                "八專": "八专", "別責": "别责", "返吟": "返吟", "伏吟": "伏吟", "昴星": "昴星"}
# 独立实现未校三传的宗门（特殊三传，ref 只判宗门不校三传）
_REF_NO_SAN = {"八专", "昴星"}


def cross_check_ref(dt=None):
    """交叉校验：独立九宗门实现 vs kinliuren 引擎（宗门 + 三传）。

    独立实现与引擎各自独立判课，返回两套宗门/课体/三传及是否一致。
    用途：`cast.py liuren --ref` 排盘时加一道独立复核，不一致即提示该课宗门/三传存疑，
    需按《六壬大全》原文人工复核（对应 SKILL.md「已知引擎边界」）。
    """
    dt = dt or datetime.datetime.now()
    solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    lunar = solar.getLunar()
    day_gz = lunar.getDayInGanZhi()
    hour_gz = lunar.getTimeInGanZhi()
    jieqi = lunar.getPrevJieQi().getName()
    jieqi = {"惊蛰": "驚蟄", "谷雨": "穀雨", "小满": "小滿", "芒种": "芒種", "处暑": "處暑"}.get(jieqi, jieqi)
    lr = Liuren(jieqi, lunar.getMonth(), day_gz, hour_gz)
    jiang = lr.moongeneral()
    day_gan, day_zhi, shi_zhi = day_gz[0], day_gz[1], hour_gz[1]

    # 引擎
    e_err = None
    try:
        r = lr.result(1)
        eju = [j.rstrip("0123456789") for j in (r.get("格局") or [])]
        esan = [r["三傳"][k][0] for k in ("初傳", "中傳", "末傳")]
    except Exception as e:
        eju, esan, e_err = [], [], str(e)

    # 独立实现
    ref = ref_zongmen_chuchuan(jiang, shi_zhi, day_gan, day_zhi)
    r_zong, r_kt, r_san = ref if ref else ("无", "无", None)

    e_zong = _ZONGMEN_SIM.get(eju[0], eju[0]) if eju else "崩溃"
    r_zong_s = _ZONGMEN_SIM.get(r_zong, r_zong)
    zong_ok = (e_zong == r_zong_s)
    # 三传只对顺传宗门比对；独立实现未校的特殊宗门跳过
    san_ok = None
    if esan and r_san and r_zong_s not in _REF_NO_SAN:
        san_ok = (esan == r_san)
    return {
        "引擎宗门": e_zong, "引擎课体": eju[1] if len(eju) > 1 else "", "引擎三传": esan, "引擎异常": e_err,
        "独立宗门": r_zong_s, "独立课体": r_kt, "独立三传": r_san,
        "宗门一致": zong_ok, "三传一致": san_ok,
    }


def format_cross_check(cc):
    """格式化交叉校验结果（供 cast.py --ref 打印）。"""
    lines = []
    if cc["引擎异常"]:
        lines.append(f"  引擎：排盘异常（{cc['引擎异常']}）——此课不可用，须人工复核")
    else:
        lines.append(f"  引擎：{cc['引擎宗门']}·{cc['引擎课体']}  三传 {' -> '.join(cc['引擎三传'])}")
    san = cc["独立三传"]
    san_s = f"  独立：{cc['独立宗门']}·{cc['独立课体']}"
    if san:
        san_s += f"  三传 {' -> '.join(san)}"
    else:
        san_s += "  三传（特殊课，未校）"
    lines.append(san_s)
    if cc["宗门一致"]:
        verdict = "✓ 宗门一致"
    else:
        verdict = "✗ 宗门分歧——此课宗门存疑，按《六壬大全》原文复核（涉害/比用/返吟/八专边界易误判）"
    if cc["三传一致"] is not None:
        verdict += "；三传一致" if cc["三传一致"] else "；✗ 三传分歧——初传取用存疑"
    lines.append(f"  {verdict}")
    return "\n".join(lines)


# —— 层1：穷举体检 ——
def sweep(subset=None):
    """穷举 12 月将 × 60 日 × 12 时。subset=节气名元组时只跑指定节气。返回统计 dict。"""
    jiazi = all_jiazi()
    stats = {
        "total": 0, "crash": [], "empty": [],            # 崩溃 / 八法全不適用
        "结构四课错": [], "结构三传错": [], "结构初传不在上神": [],
        "宗门分布": collections.Counter(), "课体分布": collections.Counter(),
    }
    for jiang, jieqi in _JIANG2JIEQI.items():
        if subset and jieqi not in subset:
            continue
        for day in jiazi:
            dg, dz = day[0], day[1]
            for sz in _ZHI:
                hgz = hour_gan(dg, sz) + sz
                stats["total"] += 1
                try:
                    lr = Liuren(jieqi, "八", day, hgz)
                    r = lr.result(1)
                except Exception as e:
                    stats["crash"].append((jieqi, day, hgz, repr(e)))
                    continue
                ju = r.get("格局", [])
                if not ju:
                    stats["empty"].append((jieqi, day, hgz))
                    continue
                stats["宗门分布"][ju[0]] += 1
                stats["课体分布"][ju[1]] += 1
                # 结构不变量
                err = check_structural(r, jiang, sz, dg, dz)
                if err:
                    stats[f"结构{err}"].append((jieqi, day, hgz, ju))
    return stats


def check_structural(r, jiang, shi_zhi, day_gan, day_zhi):
    """校验一课的结构不变量。返回错误类型或 None。"""
    # 四课独立重算比对
    ref = ref_sike(jiang, shi_zhi, day_gan, day_zhi)     # [4,3,2,1]
    eng = r.get("四課", {})
    order = [("四課", 0), ("三課", 1), ("二課", 2), ("一課", 3)]
    for label, idx in order:
        if eng.get(label) and eng[label][0] != ref[idx]:
            return "四课错"
    # 三传 3 支
    chuan = r.get("三傳", {})
    zhis = [chuan.get(k, [""])[0] for k in ("初傳", "中傳", "末傳")]
    if not all(z in _ZHI for z in zhis):
        return "三传错"
    ju = r.get("格局", [])
    zm = ju[0] if ju else ""
    # 顺传宗门：初传必是四课上神 + 三传递进；特殊宗门（昴星/别责/伏吟/返吟）三传另起
    if zm in _SHUNCHUAN:
        shangshen = [k[0] for k in ref]
        if zhis[0] not in shangshen:
            return "初传不在上神"
        e2s = ref_earth_sky(jiang, shi_zhi)
        if zhis[1] != e2s[zhis[0]] or zhis[2] != e2s[zhis[1]]:
            return "三传错"
    return None


# —— 层3：历史课体对照 ——
# 古籍课体名 -> 宗门（只保留能唯一确定宗门的名字；类课如铸印/乘轩/励德/元胎/龙战/
# 绝嗣/寡宿/闭口/井栏射/转蓬 不映射，它们跨宗门、不决定三传起法）
_ZONGMEN_MAP = {
    "元首": "賊尅", "重审": "賊尅", "重審": "賊尅",
    "知一": "比用",
    "涉害": "涉害", "见机": "涉害", "見機": "涉害", "察微": "涉害",
    "缀瑕": "涉害", "綴瑕": "涉害", "度厄": "涉害",
    "遥克": "遙尅", "遙克": "遙尅", "蒿矢": "遙尅", "弹射": "遙尅", "彈射": "遙尅",
    "昴星": "昴星", "昂星": "昴星", "虎视": "昴星", "冬蛇": "昴星",
    "别责": "別責", "別責": "別責",
    "八专": "八專", "八專": "八專",
    "伏吟": "伏吟", "自任": "伏吟", "自信": "伏吟", "杜传": "伏吟", "杜傳": "伏吟",
    "返吟": "返吟", "反吟": "返吟", "无依": "返吟", "無依": "返吟",
}


def parse_case_line(line):
    """从课式行解析 (日干支, 月将, 时支, 课体名列表)。"""
    day = re.search(r"([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])日", line)
    jiang = re.search(r"([子丑寅卯辰巳午未申酉戌亥])将", line)
    shi = re.search(r"([子丑寅卯辰巳午未申酉戌亥])时", line)
    if not (day and jiang and shi):
        return None
    return day.group(1), jiang.group(1), shi.group(1), line


def cross_check_cases(case_dir):
    """历史课体对照。返回 (命中, 未命中, 无法解析)。"""
    hit, miss, unparse = 0, 0, 0
    miss_detail = []
    files = [f for f in os.listdir(case_dir) if f.endswith(".md")]
    for f in files:
        try:
            with open(os.path.join(case_dir, f), encoding="utf-8") as fh:
                text = fh.read()
        except Exception:
            continue
        # 取「盘面（课式）」段第一行
        m = re.search(r"##\s*盘面[^\n]*\n\s*([^\n]+)", text)
        if not m:
            continue
        line = m.group(1)
        parsed = parse_case_line(line)
        if not parsed:
            unparse += 1
            continue
        day, jiang, shi_zhi, _ = parsed
        if jiang not in _JIANG2JIEQI:
            unparse += 1
            continue
        dg, dz = day[0], day[1]
        hgz = hour_gan(dg, shi_zhi) + shi_zhi
        # 历史课体名 -> 宗门集合
        hist_zong = set()
        for name, zm in _ZONGMEN_MAP.items():
            if name in line:
                hist_zong.add(zm)
        if not hist_zong:
            unparse += 1
            continue
        try:
            lr = Liuren(_JIANG2JIEQI[jiang], "八", day, hgz)
            r = lr.result(1)
            ju = r.get("格局", [])
        except Exception:
            miss += 1
            continue
        eng_zong = ju[0] if ju else ""
        if eng_zong in hist_zong or eng_zong == "":
            if eng_zong in hist_zong:
                hit += 1
            else:
                unparse += 1
        else:
            miss += 1
            miss_detail.append((f, day, jiang, shi_zhi, hist_zong, ju))
    return hit, miss, unparse, miss_detail


def _fmt_stats(stats):
    lines = []
    lines.append(f"总计 {stats['total']} 课")
    lines.append(f"崩溃(异常): {len(stats['crash'])}")
    for c in stats["crash"][:10]:
        lines.append(f"    {c}")
    lines.append(f"漏课(八法全不適用): {len(stats['empty'])}")
    for c in stats["empty"][:10]:
        lines.append(f"    {c}")
    lines.append(f"四课错: {len(stats['结构四课错'])}")
    lines.append(f"三传错(递进): {len(stats['结构三传错'])}")
    lines.append(f"初传不在上神: {len(stats['结构初传不在上神'])}")
    for k in ("结构四课错", "结构三传错", "结构初传不在上神"):
        for c in stats[k][:8]:
            lines.append(f"    {c}")
    lines.append("宗门分布: " + ", ".join(f"{k}={v}" for k, v in stats["宗门分布"].most_common()))
    return "\n".join(lines)


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    argv = sys.argv[1:]
    mode = argv[0] if argv else "all"
    case_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "..", "..", "..", "国学czhengli", "txt", "案例库", "大六壬")
    if mode in ("all", "sweep"):
        print("=" * 60)
        print("[层1+2] 穷举体检 + 结构不变量（8640 课）")
        stats = sweep()
        print(_fmt_stats(stats))
    if mode in ("all", "cases"):
        print("=" * 60)
        print("[层3] 历史课体对照（案例库/大六壬）")
        if os.path.isdir(case_dir):
            hit, miss, unparse, detail = cross_check_cases(case_dir)
            print(f"命中 {hit} / 未命中 {miss} / 无法解析 {unparse}")
            for d in detail[:30]:
                print(f"    未命中 {d}")
        else:
            print(f"案例库目录不存在: {case_dir}")
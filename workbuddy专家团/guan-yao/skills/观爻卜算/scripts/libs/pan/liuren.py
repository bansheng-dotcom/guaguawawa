# -*- coding: utf-8 -*-
"""大六壬排盘（引擎: kentang2017/kinliuren，经 engines/taiyi/kinliuren.py 复用）

在 kinliuren 天地盘/四课/三传基础上，补结构化判定层：
  1. 三传天将吉凶（十二天将，liuren_shensha）
  2. 命中神煞（驿马/桃花/华盖/劫煞/灾煞/岁煞/日德/日禄/羊刃/天乙/月德/天喜/红鸾/旬空）
  3. 毕法赋条目检索建议（liuren_bifa，按格局/神煞关键词）

以上均为「结构化判定层 + 出处指针」，断卦时仍须按条目名/神煞名 Grep 原文佐证（双重保证）。
"""
import datetime
from lunar_python import Solar
from engines.taiyi.kinliuren import Liuren
from judge import liuren_shensha
from judge import liuren_bifa
# 天将简称 -> 完整名（kinliuren 三传/天地盘用简称）
_TIANJIANG_ALIAS = {
    "貴": "贵人", "蛇": "螣蛇", "雀": "朱雀", "合": "六合", "勾": "勾陈",
    "龍": "青龙", "空": "天空", "虎": "白虎", "常": "太常", "玄": "玄武",
    "陰": "太阴", "后": "天后",
}

# lunar_python 返回简体节气名，但 kinliuren 的 moon_general_dict 用繁体
# （驚蟄/穀雨/小滿/芒種/處暑），不一致时 getPrevJieQi().getName() 命中不到 -> 月将取 None -> 崩溃。
# 此处归一化：简体节气 -> 引擎字典用的繁体，防 cast.py liuren 在这 5 个节气期间崩溃。
_JIEQI_NORMALIZE = {
    "惊蛰": "驚蟄", "谷雨": "穀雨", "小满": "小滿", "芒种": "芒種", "处暑": "處暑",
}

_ZHI = "子丑寅卯辰巳午未申酉戌亥"
_GAN = "甲乙丙丁戊己庚辛壬癸"

# 课体格局名 -> 毕法赋检索关键词（同义/异名归一，繁体格局名常见）
_JU_ALIAS = {
    "返吟": "伏吟", "反吟": "伏吟", "伏吟": "伏吟",
    "六合": "合", "三合": "合", "六儀": "三六合", "六仪": "三六合",
    "空亡": "空", "旬空": "空", "空上": "空", "空上逢空": "空",
    "財": "财", "財局": "财", "財逢": "财",
    "白虎": "虎", "虎視": "虎", "虎": "虎",
    "貴人": "贵", "貴": "贵", "夜貴": "贵", "晝貴": "贵",
    "螣蛇": "蛇", "蛇": "蛇",
    "玄武": "盗", "玄": "盗",
    "朱雀": "雀", "雀": "雀",
    "墓": "墓", "入墓": "墓", "墓覆": "墓",
    "丁馬": "丁马", "丁馬動": "丁马", "驛馬": "丁马",
    "絶嗣": "绝嗣", "絕嗣": "绝嗣",
    "連茹": "连茹", "進茹": "连茹", "退茹": "连茹",
    "昴星": "昴星",
    "天網": "天网", "羅網": "天网",
}


def correct_three_pass(r, lr, day_gan, day_zhi, hour_zhi, moongeneral):
    """独立九宗门交叉修正三传：kinliuren 边界课型（比用/昴星/八专/返吟井栏射）易误判初传，
    以规则推导 `regress.liuren_regress.ref_zongmen_chuchuan` 为准修正三传地支，并重算天将/六亲/旬空。

    返回是否修正过。kinliuren 的宗门函数是硬编码分支森林，这里不动它，只在校验层兜底——
    与《六壬大全》课经起例对拍不符时，以规则推导的三传覆盖，并在盘面标注 `_三传修正`。
    """
    from regress import liuren_regress as _lr_reg
    ref = _lr_reg.ref_zongmen_chuchuan(moongeneral, hour_zhi, day_gan, day_zhi)
    if not ref or not ref[2]:
        return False
    kin = [r["三傳"]["初傳"][0], r["三傳"]["中傳"][0], r["三傳"]["末傳"][0]]
    if kin == ref[2]:
        return False
    g2 = lr.guiren_order_list(1)
    for key, zhi in zip(("初傳", "中傳", "末傳"), ref[2]):
        jiang = g2.get(zhi)
        liuqin = lr.liuqing_dict.get(lr.multi_key_dict_get(
            lr.wuxing_relation_2, lr.Ganzhiwuxing(day_gan) + lr.Ganzhiwuxing(zhi)))
        r["三傳"][key] = [zhi, jiang, liuqin[0], lr.shunkong(lr.daygangzhi, zhi)]
    r["_三传修正"] = {"原三传": kin, "修正为": ref[2], "依据": "独立九宗门规则推导(liuren_regress)"}
    return True


def cast(dt=None):
    dt = dt or datetime.datetime.now()
    solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    lunar = solar.getLunar()
    day_gz = lunar.getDayInGanZhi()
    hour_gz = lunar.getTimeInGanZhi()
    day_gan, day_zhi = day_gz[0], day_gz[1]
    year_zhi = lunar.getYearZhi()
    month_zhi = lunar.getMonthZhi()
    jieqi = lunar.getPrevJieQi().getName()
    jieqi = _JIEQI_NORMALIZE.get(jieqi, jieqi)   # 简体->繁体归一化，防月将取 None 崩溃
    lmonth = lunar.getMonth()

    lr = Liuren(jieqi, lmonth, day_gz, hour_gz)
    r = lr.result(1)
    # 归一化引擎的 debug 后缀（"涉害1"->"涉害"、"蒿矢11"->"蒿矢"、"知一1"->"知一"、"間傳1"->"間傳"），
    # 这些是 kinliuren 硬编码分支里的调试尾巴，漏进课体/宗门名里污染输出。
    r["格局"] = [j.rstrip("0123456789") if isinstance(j, str) else j for j in (r.get("格局") or [])]

    # 独立九宗门交叉修正：边界课型初传易误判，以规则推导兜底（详见 correct_three_pass 注释）
    correct_three_pass(r, lr, day_gan, day_zhi, hour_gz[1], lr.moongeneral())

    print(f"[大六壬] {lunar.toString()} {jieqi}  {day_gz}日{hour_gz}时")
    print(f"格局: {'、'.join(r.get('格局', []))}")
    t = r.get('三傳', {})
    print(f"三传: 初传 {t.get('初傳')} -> 中传 {t.get('中傳')} -> 末传 {t.get('末傳')}")
    print(f"四课: {r.get('四課', {})}")
    print(f"日马(驿马): {r.get('日馬', '')}  月将: {lr.moongeneral()}")

    # —— 三传天将吉凶（结构化 + 出处）——
    print("\n【三传天将】")
    for label, key in (("初传", "初傳"), ("中传", "中傳"), ("末传", "末傳")):
        chuan = t.get(key)
        if not chuan:
            continue
        jiang = _TIANJIANG_ALIAS.get(chuan[1], chuan[1])
        tj = liuren_shensha.tianjiang(jiang)
        print(f"  {label} {chuan[0]} 乘{jiang}（{tj['吉凶']}，{tj['主事']}）[出处：{tj['出处']}]")

    # —— 命中神煞 ——
    hits = liuren_shensha.compute_shensha(day_gan, day_zhi, year_zhi, month_zhi, lmonth)
    print("\n【命中神煞】")
    print(liuren_shensha.format_shensha(hits))

    # —— 毕法赋检索建议（按格局/神煞关键词，供 Grep 原文佐证）——
    print("\n【毕法赋关联条目】（结构化索引，断卦按条名 Grep 原文佐证）")
    kws = set()
    for ju in r.get('格局', []):
        kws.add(_JU_ALIAS.get(ju, ju))
    kws |= set(hits.keys())
    kws |= {day_zhi}
    related = []
    for kw in kws:
        for h in liuren_bifa.lookup(kw):
            if h["句"] not in [x["句"] for x in related]:
                related.append(h)
    if related:
        for h in related[:6]:
            print(f"  [{h['吉凶']}] {h['句']} —— {h['主断']}（出处：{h['出处']}）")
    else:
        print("  （无直接关联条目，断卦按课体特征在 liuren_bifa.lookup 检索）")

    r["_神煞"] = hits
    r["_天将"] = {k: liuren_shensha.tianjiang(_TIANJIANG_ALIAS.get(v[1], v[1]))
                  for k, v in t.items() if v}
    return r


def summary(r):
    """一眼摘要卡：日期节气/格局/三传/日马（借鉴八字/紫微升级的「一眼看懂」层）。"""
    sc = r.get("三傳", {})

    def _chuan(x):
        if not x:
            return "—"
        return f"{x[0]}({x[1]}·{x[2]})" if len(x) >= 3 else str(x)

    geju = "、".join(r.get("格局", [])) if r.get("格局") else "—"
    return "\n".join([
        f"【一眼摘要】大六壬 · {r.get('日期', '')} · {r.get('節氣', '')}",
        f"  格局：{geju} · 日马{r.get('日馬', '')}",
        f"  三传：初{_chuan(sc.get('初傳'))} → 中{_chuan(sc.get('中傳'))} → 末{_chuan(sc.get('末傳'))}",
    ])


def pan_json(r):
    """盘面事实层 JSON（机读，schema=liuren-panfact-v1）。"""
    from judge.rules import pan_meta
    return {"schema": "liuren-panfact-v1", **r, **pan_meta("大六壬")}
# -*- coding: utf-8 -*-
"""紫微斗数 · 格局判定规则引擎（结构化判定层 + 典籍出处指针）。

把「断：格局」这类开放提示落成可判定、可回归测试的规则。每个格局命中返回：
  {格局, 吉凶, 落宫, 断语, 原文, 出处, 破格, detail, confidence}
断卦时仍须按格局名 Grep《紫微斗数全书》txt 原文佐证（双重保证），
原文缺失的格局本模块不收录，或标「流派分歧」降级。

数据输入：`zhiwei.cast()` 返回的 dict（十二宫含主星[(星,亮度,四化)]/辅星/命/身）。

宫位索引约定（与 zhiwei.py 一致）：寅宫下标 0，顺时针 +1（寅0 卯1 辰2 巳3 午4
未5 申6 酉7 戌8 亥9 子10 丑11）。地支→宫位：idx = (ZHI.index(zhi) - 2) % 12。
"""
from pan import zhiwei
ZHI = zhiwei.ZHI
SRC = "《紫微斗数全书》"


def _zhi_to_idx(zhi):
    return zhiwei._zhi_palace(zhi)


def sanfang_sizheng(idx):
    """三方四正（4 宫）：本宫 + 对宫 + 三合两宫。宫位索引 寅=0。"""
    return zhiwei.sanfang_sizheng(idx)


def _palace_stars(chart, idx):
    """某宫全部星名集合（主星 + 辅星）。"""
    p = chart["十二宫"][idx]
    names = {n for n, _b, _s in p["主星"]}
    names.update(p["辅星"])
    return names


def _star_idx(chart, name):
    """星曜所在宫位索引列表（主星 + 辅星都查）。"""
    return [i for i in range(12) if name in _palace_stars(chart, i)]


def _ming_palace(chart):
    for i, p in enumerate(chart["十二宫"]):
        if p["命"]:
            return i
    return None


def _palace_name(chart, idx):
    return chart["十二宫"][idx]["宫"]


def _zhi_of(chart, idx):
    return chart["十二宫"][idx]["支"]


# —— 格局定义 ——
# 每个格局一个 check(chart) -> (matched, palace_idx|None, detail, broken)
# 吉凶取「吉/凶/中」；confidence 取「高/中/低」（流派分歧标中/低）。


def _check_junchen_qinghui(chart):
    """君臣庆会：紫微守命，左辅右弼同宫或来拱（或三方见天府天相）。
    原文「君臣慶會 紫微左右同守命是也，更會相武陰妙上」。"""
    m = _ming_palace(chart)
    if m is None or "紫微" not in _palace_stars(chart, m):
        return False, None, "", False
    fang = set(sanfang_sizheng(m))
    jia = {"左辅", "右弼", "天府", "天相"}
    hit = jia & {s for i in fang for s in _palace_stars(chart, i)}
    if hit:
        return True, m, f"紫微守命，{'、'.join(sorted(hit))}同宫或三方拱照", False
    return True, m, "紫微守命，然左右/府相未拱，君臣庆会不完整", True  # 破格


def _check_fuxiang_chaoyuan(chart):
    """府相朝垣：天府/天相守命，或天府与天相同见于命三方四正。
    原文「府相朝垣命必荣」「府相朝垣千锺食禄」。"""
    m = _ming_palace(chart)
    if m is None:
        return False, None, "", False
    ms = _palace_stars(chart, m)
    if "天府" in ms or "天相" in ms:
        return True, m, f"{_palace_name(chart, m)}守命，府相朝垣", False
    fang = set(sanfang_sizheng(m))
    alls = {s for i in fang for s in _palace_stars(chart, i)}
    if {"天府", "天相"} <= alls:
        return True, m, "天府、天相同会于命三方四正，府相朝垣", False
    return False, None, "", False


def _check_jiyuetongliang(chart):
    """机月同梁：天机、太阴、天同、天梁会于命三方四正（四星全则成格，三星为倾向）。
    原文「机月同梁作吏人 命在寅申方论」。"""
    m = _ming_palace(chart)
    if m is None:
        return False, None, "", False
    fang = set(sanfang_sizheng(m))
    need = {"天机", "太阴", "天同", "天梁"}
    got = need & {s for i in fang for s in _palace_stars(chart, i)}
    if len(got) >= 4:
        return True, m, "天机太阴天同天梁会命三方四正，机月同梁成格", False
    if len(got) == 3:
        miss = sorted(need - got)
        return True, m, f"机月同梁缺{'、'.join(miss)}，不完整（倾向）", True
    return False, None, "", False


def _check_yuelang_tianmen(chart):
    """月朗天门：太阴在亥守命（入庙）。原文「月朗天门于亥地登云职掌大权」。"""
    m = _ming_palace(chart)
    if m is None or _zhi_of(chart, m) != "亥":
        return False, None, "", False
    if "太阴" in _palace_stars(chart, m):
        return True, m, "太阴在亥守命，月朗天门", False
    return False, None, "", False


def _check_rizhao_leimen(chart):
    """日照雷门 / 日出扶桑：太阳在卯守命。原文「日照雷门子辰卯地昼生富贵声扬」。"""
    m = _ming_palace(chart)
    if m is None or _zhi_of(chart, m) != "卯":
        return False, None, "", False
    if "太阳" in _palace_stars(chart, m):
        return True, m, "太阳在卯守命，日照雷门（日出扶桑）", False
    return False, None, "", False


def _check_yuesheng_canghai(chart):
    """月生沧海：太阴在子守田宅。原文「月生滄海 月在子宮守田宅是也」。"""
    for i in range(12):
        if _palace_name(chart, i) == "田宅宫" and _zhi_of(chart, i) == "子" \
                and "太阴" in _palace_stars(chart, i):
            return True, i, "太阴在子宫守田宅，月生沧海", False
    return False, None, "", False


def _check_qisha_chaodou(chart):
    """七杀朝斗：七杀在寅申子午守命。原文「七杀寅申子午一生爵禄荣昌 为七杀朝斗格」。"""
    m = _ming_palace(chart)
    if m is None or _zhi_of(chart, m) not in ("寅", "申", "子", "午"):
        return False, None, "", False
    if "七杀" in _palace_stars(chart, m):
        return True, m, f"七杀在{_zhi_of(chart, m)}守命，七杀朝斗", False
    return False, None, "", False


def _check_wuqu_miaoyuan(chart):
    """武曲庙垣：武曲在辰戌丑未守命。原文「武曲庙垣威名赫奕」。"""
    m = _ming_palace(chart)
    if m is None or _zhi_of(chart, m) not in ("辰", "戌", "丑", "未"):
        return False, None, "", False
    if "武曲" in _palace_stars(chart, m):
        return True, m, f"武曲在{_zhi_of(chart, m)}守命，武曲庙垣", False
    return False, None, "", False


def _check_shizhong_yinyu(chart):
    """石中隐玉：巨门在子午守命，更会科权禄。原文「身命居子午宫为石中隐玉格」。"""
    m = _ming_palace(chart)
    if m is None or _zhi_of(chart, m) not in ("子", "午"):
        return False, None, "", False
    if "巨门" not in _palace_stars(chart, m):
        return False, None, "", False
    sihua = {s for _n, _b, s in chart["十二宫"][m]["主星"] if s}
    if sihua:
        return True, m, f"巨门在{_zhi_of(chart, m)}守命且{''.join(sihua)}在身，石中隐玉福厚", False
    return True, m, "巨门在子午守命（石中隐玉），未会科权禄则减力", False


def _check_lumajiaochi(chart):
    """禄马交驰：禄存与天马同宫或对照。原文「禄马交驰亦吉」「武曲禄马交驰发财远郡」。"""
    lu = _star_idx(chart, "禄存")
    ma = _star_idx(chart, "天马")
    if not lu or not ma:
        return False, None, "", False
    if set(lu) & set(ma):
        return True, lu[0], "禄存与天马同宫，禄马交驰", False
    if any((l + 6) % 12 in ma for l in lu):
        return True, lu[0], "禄存与天马对照，禄马交驰", False
    return False, None, "", False


def _check_qingyang_rumiao(chart):
    """擎羊入庙：擎羊在辰戌丑未。原文「擎羊入庙富贵声扬」。"""
    qy = _star_idx(chart, "擎羊")
    for i in qy:
        if _zhi_of(chart, i) in ("辰", "戌", "丑", "未"):
            return True, i, f"擎羊在{_zhi_of(chart, i)}入庙，擎羊入庙富贵声扬", False
    return False, None, "", False


def _check_matou_daijian(chart):
    """马头带剑/箭：擎羊在午（天马同宫更确）。流派有分歧，标中置信。
    原文「马头带剑 谓马有刃是也不是居午格」「马头带箭富且贵」。"""
    qy = _star_idx(chart, "擎羊")
    ma = set(_star_idx(chart, "天马"))
    for i in qy:
        if _zhi_of(chart, i) == "午":
            if i in ma:
                return True, i, "擎羊天马同会午宫，马头带剑（箭）", False
            return True, i, "擎羊在午（马头带剑/箭），未与天马同宫则偏武职奋斗", False
    return False, None, "", False


def _check_zifu_tonggong(chart):
    """紫府同宫：紫微天府同宫（寅申）。原文「天府惟寅申二宫紫府同宫」。"""
    for i in range(12):
        s = _palace_stars(chart, i)
        if {"紫微", "天府"} <= s:
            return True, i, f"紫微天府同宫（{_zhi_of(chart, i)}），紫府同宫", False
    return False, None, "", False


def _check_fubi_gongzhu(chart):
    """辅弼拱主：紫微守命，左辅右弼来拱/夹。原文「辅弼拱主 紫微守命二星来拱是也」。"""
    m = _ming_palace(chart)
    if m is None or "紫微" not in _palace_stars(chart, m):
        return False, None, "", False
    fang = set(sanfang_sizheng(m))
    got = {"左辅", "右弼"} & {s for i in fang for s in _palace_stars(chart, i)}
    if got:
        return True, m, f"紫微守命，{'、'.join(sorted(got))}来拱，辅弼拱主", False
    return False, None, "", False


def _check_juri_tonggong(chart):
    """巨日同宫/拱照：巨门与太阳同宫。原文「巨日拱照亦为奇」。"""
    for i in range(12):
        s = _palace_stars(chart, i)
        if {"巨门", "太阳"} <= s:
            return True, i, f"巨门太阳同宫（{_zhi_of(chart, i)}），巨日同宫", False
    return False, None, "", False


def _check_riyue_bingming(chart):
    """日月并明：太阳太阴同宫，或日月分居卯亥（日卯月亥）对照拱照。
    原文「日月守命不如照合并明」。流派有分歧，标中置信。"""
    tai = _star_idx(chart, "太阳")
    yin = _star_idx(chart, "太阴")
    if not tai or not yin:
        return False, None, "", False
    if set(tai) & set(yin):
        return True, tai[0], "太阳太阴同宫，日月并明（同临）", False
    # 日卯月亥对照（明珠出海/日月并明一体）
    if _zhi_to_idx("卯") in tai and _zhi_to_idx("亥") in yin:
        return True, tai[0], "太阳在卯、太阴在亥，日月拱照并明", False
    if _zhi_to_idx("巳") in tai and _zhi_to_idx("酉") in yin:
        return True, tai[0], "太阳在巳、太阴在酉，日月拱照并明", False
    return False, None, "", False


def _check_shapolang(chart):
    """杀破狼：七杀、破军、贪狼三星会于命三方四正。主大变动，吉凶看格局高低。
    原文「紫微入限本为祥，只恐三方杀破狼」。标「中」。"""
    m = _ming_palace(chart)
    if m is None:
        return False, None, "", False
    fang = set(sanfang_sizheng(m))
    alls = {s for i in fang for s in _palace_stars(chart, i)}
    got = {"七杀", "破军", "贪狼"} & alls
    if len(got) == 3:
        return True, m, "七杀破军贪狼会命三方，杀破狼主变动开创", False
    return False, None, "", False


def _check_juji_tonglin(chart):
    """巨机同临：巨门与天机同宫（卯酉为破格）。原文「巨门天机为破荡」。"""
    for i in range(12):
        s = _palace_stars(chart, i)
        if {"巨门", "天机"} <= s:
            broken = _zhi_of(chart, i) in ("卯", "酉")
            d = f"巨门天机同宫（{_zhi_of(chart, i)}），{'卯酉为破荡下格' if broken else '巨机同临'}"
            return True, i, d, broken
    return False, None, "", False


# 格局注册表：key 稳定、name 中文、吉凶、断语、原文、check。
_PATTERNS = [
    {"key": "junchen_qinghui", "name": "君臣庆会", "吉凶": "吉",
     "断语": "紫微为君、左右为辅，贵气聚命，多得贵人助力、掌权有望",
     "原文": "君臣慶會 紫微左右同守命是也，更會相武陰妙上",
     "check": _check_junchen_qinghui},
    {"key": "fuxiang_chaoyuan", "name": "府相朝垣", "吉凶": "吉",
     "断语": "天府天相为财荫之星，朝拱命垣，主富贵荣显、财禄丰厚",
     "原文": "府相朝垣命必荣；府相朝垣千锺食禄",
     "check": _check_fuxiang_chaoyuan},
    {"key": "jiyuetongliang", "name": "机月同梁", "吉凶": "吉",
     "断语": "机月同梁作吏人，主稳定文职、公门清贵、安分守成",
     "原文": "机月同梁作吏人 命在寅申方论",
     "check": _check_jiyuetongliang},
    {"key": "yuelang_tianmen", "name": "月朗天门", "吉凶": "吉",
     "断语": "太阴入庙于亥，主大富大贵、掌权有谋略",
     "原文": "月朗天门于亥地登云职掌大权；月落亥宮 月在亥守命是也",
     "check": _check_yuelang_tianmen},
    {"key": "rizhao_leimen", "name": "日照雷门", "吉凶": "吉",
     "断语": "太阳在卯入庙守命，主声名显达、富贵扬名（昼生更验）",
     "原文": "日照雷门子辰卯地昼生富贵声扬；日出扶桑 日在卯守命是也",
     "check": _check_rizhao_leimen},
    {"key": "yuesheng_canghai", "name": "月生沧海", "吉凶": "吉",
     "断语": "太阴在子守田宅，主田宅丰厚、家业安稳、晚福绵长",
     "原文": "月生滄海 月在子宮守田宅是也",
     "check": _check_yuesheng_canghai},
    {"key": "qisha_chaodou", "name": "七杀朝斗", "吉凶": "吉",
     "断语": "七杀在寅申子午朝拱紫微，主武职权贵、威权显赫",
     "原文": "七杀寅申子午一生爵禄荣昌 为七杀朝斗格",
     "check": _check_qisha_chaodou},
    {"key": "wuqu_miaoyuan", "name": "武曲庙垣", "吉凶": "吉",
     "断语": "武曲于四墓地入庙，主财帛威权、经商发达",
     "原文": "武曲庙垣威名赫奕",
     "check": _check_wuqu_miaoyuan},
    {"key": "shizhong_yinyu", "name": "石中隐玉", "吉凶": "吉",
     "断语": "巨门子午藏玉于石，先难后成、更会科权禄则终身福厚",
     "原文": "身命居子午宫为石中隐玉格，更会科权禄，终身福厚",
     "check": _check_shizhong_yinyu},
    {"key": "lumajiaochi", "name": "禄马交驰", "吉凶": "吉",
     "断语": "禄存天马交驰，主财禄丰足、奔波得财、发财远郡",
     "原文": "禄马交驰亦吉；武曲禄马交驰发财远郡",
     "check": _check_lumajiaochi},
    {"key": "qingyang_rumiao", "name": "擎羊入庙", "吉凶": "吉",
     "断语": "擎羊辰戌丑未入庙，主先破后成、武职发迹、闹中发财",
     "原文": "擎羊入庙富贵声扬；擎羊入庙最利武职",
     "check": _check_qingyang_rumiao},
    {"key": "matou_daijian", "name": "马头带剑", "吉凶": "吉",
     "断语": "擎羊在午带剑，主于险中得富、武职奋斗成贵",
     "原文": "马头带剑 谓马有刃是也不是居午格；马头带箭富且贵",
     "check": _check_matou_daijian, "confidence": "中"},
    {"key": "zifu_tonggong", "name": "紫府同宫", "吉凶": "吉",
     "断语": "紫微天府同宫，主福禄厚重、稳重有成、一生衣食",
     "原文": "天府惟寅申二宫紫府同宫",
     "check": _check_zifu_tonggong},
    {"key": "fubi_gongzhu", "name": "辅弼拱主", "吉凶": "吉",
     "断语": "左辅右弼拱护紫微，主左右得人、助力强、事业有靠",
     "原文": "辅弼拱主 紫微守命二星来拱是也",
     "check": _check_fubi_gongzhu},
    {"key": "juri_tonggong", "name": "巨日同宫", "吉凶": "吉",
     "断语": "巨门太阳同宫，主食禄驰名、声名在外、口才扬名",
     "原文": "巨日拱照亦为奇",
     "check": _check_juri_tonggong},
    {"key": "riyue_bingming", "name": "日月并明", "吉凶": "吉",
     "断语": "日月并明，主阴阳调和、福寿双全、名利两得",
     "原文": "日月守命不如照合并明",
     "check": _check_riyue_bingming, "confidence": "中"},
    {"key": "shapolang", "name": "杀破狼", "吉凶": "中",
     "断语": "杀破狼会命，主大变动、开创、动荡，成者大起败者大落",
     "原文": "紫微入限本为祥，只恐三方杀破狼",
     "check": _check_shapolang},
    {"key": "juji_tonglin", "name": "巨机同临", "吉凶": "凶",
     "断语": "巨门天机同宫破荡，主是非、多谋少成、易破败",
     "原文": "巨门天机为破荡；巨宿天机为破荡",
     "check": _check_juji_tonglin},
]


def judge_patterns(chart):
    """判定命盘格局，返回命中列表（按吉凶排：凶→中→吉，同档按注册序）。"""
    hits = []
    for p in _PATTERNS:
        matched, idx, detail, broken = p["check"](chart)
        if not matched:
            continue
        hits.append({
            "格局": p["name"],
            "key": p["key"],
            "吉凶": p["吉凶"],
            "落宫": (_palace_name(chart, idx) if idx is not None else ""),
            "断语": p["断语"],
            "原文": p["原文"],
            "出处": SRC,
            "破格": broken,
            "detail": detail,
            "confidence": p.get("confidence", "高"),
        })
    order = {"凶": 0, "中": 1, "吉": 2}
    hits.sort(key=lambda h: order[h["吉凶"]])
    return hits


def format_patterns(hits):
    """格式化格局命中列表为字符串。"""
    if not hits:
        return "（未见具名格局，按三方四正与主星庙旺断）"
    lines = []
    for h in hits:
        brk = "〔破格〕" if h["破格"] else ""
        jx = {"吉": "吉", "凶": "凶", "中": "变动"}[h["吉凶"]]
        why = f"〔{h['detail']}〕" if h["破格"] else ""
        lines.append(f"  • {h['格局']}({jx}){brk} — {h['断语']}〔落{h['落宫']}，{h['confidence']}置信〕{why}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    # 演示：1990-05-15 08:00 男
    r = zhiwei.cast(1990, 5, 15, 8, 1)
    hits = judge_patterns(r)
    print("【格局判定】" + "（出处《紫微斗数全书》，断卦按格局名 Grep 原文佐证）")
    print(format_patterns(hits))
    print("\n原文依据：")
    for h in hits:
        print(f"  {h['格局']}: {h['原文']}")
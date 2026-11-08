# -*- coding: utf-8 -*-
"""六爻纳甲装卦：纳甲配干支、安世应、配六亲、定六神、旬空（自写，可复用）"""

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"

ZHI_WX = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
          "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}

# 八卦纳甲：卦号(1~8) -> (内卦(天干, 地支串), 外卦(天干, 地支串))
NAJIA = {
    1: (("甲", "子寅辰"), ("壬", "午申戌")),  # 乾
    2: (("丁", "巳卯丑"), ("丁", "亥酉未")),  # 兑
    3: (("己", "卯丑亥"), ("己", "酉未巳")),  # 离
    4: (("庚", "子寅辰"), ("庚", "午申戌")),  # 震
    5: (("辛", "丑亥酉"), ("辛", "未巳卯")),  # 巽
    6: (("戊", "寅辰午"), ("戊", "申戌子")),  # 坎
    7: (("丙", "辰午申"), ("丙", "戌子寅")),  # 艮
    8: (("乙", "未巳卯"), ("癸", "丑亥酉")),  # 坤
}

# 八宫：宫首 -> (宫五行, [本/一/二/三/四/五/游魂/归魂 八卦名])
GONG = {
    "乾": ("金", ["乾为天", "天风姤", "天山遁", "天地否", "风地观", "山地剥", "火地晋", "火天大有"]),
    "兑": ("金", ["兑为泽", "泽水困", "泽地萃", "泽山咸", "水山蹇", "地山谦", "雷山小过", "雷泽归妹"]),
    "离": ("火", ["离为火", "火山旅", "火风鼎", "火水未济", "山水蒙", "风水涣", "天水讼", "天火同人"]),
    "震": ("木", ["震为雷", "雷地豫", "雷水解", "雷风恒", "地风升", "水风井", "泽风大过", "泽雷随"]),
    "巽": ("木", ["巽为风", "风天小畜", "风火家人", "风雷益", "天雷无妄", "火雷噬嗑", "山雷颐", "山风蛊"]),
    "坎": ("水", ["坎为水", "水泽节", "水雷屯", "水火既济", "泽火革", "雷火丰", "地火明夷", "地水师"]),
    "艮": ("土", ["艮为山", "山火贲", "山天大畜", "山泽损", "火泽睽", "天泽履", "风泽中孚", "风山渐"]),
    "坤": ("土", ["坤为地", "地雷复", "地泽临", "地天泰", "雷天大壮", "泽天夬", "水天需", "水地比"]),
}

# 世爻位置（对应八宫卦序 本/一/二/三/四/五/游魂/归魂）
SHI_POS = [6, 1, 2, 3, 4, 5, 4, 3]

SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 地支六冲（月破 / 日冲的判定基准）
CHONG = {"子": "午", "午": "子", "丑": "未", "未": "丑", "寅": "申", "申": "寅",
         "卯": "酉", "酉": "卯", "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳"}

LIUSHEN = ["青龙", "朱雀", "勾陈", "腾蛇", "白虎", "玄武"]
# 日干 -> 初爻六神起始索引
LIUSHEN_START = {"甲": 0, "乙": 0, "丙": 1, "丁": 1, "戊": 2, "己": 3, "庚": 4, "辛": 4, "壬": 5, "癸": 5}

_GUA64_REV = None
_GONG_MAP = None


def _gua64_rev():
    global _GUA64_REV
    if _GUA64_REV is None:
        from gua import GUA64
        _GUA64_REV = {name: (u, d) for (u, d), name in GUA64.items()}
    return _GUA64_REV


def _gong_map():
    global _GONG_MAP
    if _GONG_MAP is None:
        m = {}
        for gong, (wx, guas) in GONG.items():
            for i, name in enumerate(guas):
                m[name] = (gong, wx, SHI_POS[i])
        _GONG_MAP = m
    return _GONG_MAP


def najia_lines(name):
    """卦名 -> 六爻干支列表（自下而上 初~上）"""
    u, d = _gua64_rev()[name]
    inner_gan, inner_zhi = NAJIA[d][0]
    outer_gan, outer_zhi = NAJIA[u][1]
    return [inner_gan + inner_zhi[0], inner_gan + inner_zhi[1], inner_gan + inner_zhi[2],
            outer_gan + outer_zhi[0], outer_gan + outer_zhi[1], outer_gan + outer_zhi[2]]


def liuqin(gong_wx, zhi):
    """以宫五行为我，地支定六亲"""
    z_wx = ZHI_WX[zhi]
    if z_wx == gong_wx:
        return "兄弟"
    if SHENG.get(z_wx) == gong_wx:
        return "父母"   # 爻生宫 = 生我
    if SHENG.get(gong_wx) == z_wx:
        return "子孙"   # 宫生爻 = 我生
    if KE.get(z_wx) == gong_wx:
        return "官鬼"   # 爻克宫 = 克我
    if KE.get(gong_wx) == z_wx:
        return "妻财"   # 宫克爻 = 我克
    return "?"


def xunkong(day_gz):
    """日柱干支 -> 旬空地支两字"""
    gan, zhi = day_gz[0], day_gz[1]
    g = GAN.index(gan)
    z = ZHI.index(zhi)
    xun_shou = (z - g) % 12
    return ZHI[(xun_shou - 2) % 12] + ZHI[(xun_shou - 1) % 12]


def _huajin_tui(ben_zhi, bian_zhi):
    """动爻化出变爻地支：顺行一位=进神，逆行一位=退神，否则空。"""
    i, j = ZHI.index(ben_zhi), ZHI.index(bian_zhi)
    d = (j - i) % 12
    if d == 1:
        return "进神"
    if d == 11:
        return "退神"
    return ""


def fushen(ben_name, gong, gong_wx, ben_lines):
    """用神不现时的伏神：取本宫首卦（八纯卦）同位六亲，本卦六亲缺失者即伏神（伏于同位飞神之下）。"""
    ben_qin = [liuqin(gong_wx, x[-1]) for x in ben_lines]
    shou_lines = najia_lines(GONG[gong][1][0])
    present = set(ben_qin)
    out = []
    for i in range(6):
        q = liuqin(gong_wx, shou_lines[i][-1])
        if q not in present:
            out.append({
                "六亲": q,
                "干支": shou_lines[i],
                "伏爻": ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"][i],
                "飞神": f"{ben_qin[i]} {ben_lines[i]}",
            })
    return out


def zhuang(ben_name, bian_name, dong, day_gz, month_gz=""):
    """完整装卦。day_gz 如 '壬子'，month_gz 如 '丁酉'（可空）。"""
    gm = _gong_map()
    gong, gong_wx, shi = gm[ben_name]
    ying = ((shi - 1 + 3) % 6) + 1

    ben_lines = najia_lines(ben_name)
    bian_lines = najia_lines(bian_name)

    start = LIUSHEN_START[day_gz[0]]
    shen = [LIUSHEN[(start + i) % 6] for i in range(6)]

    ben_qin = [liuqin(gong_wx, x[-1]) for x in ben_lines]
    bian_qin = [liuqin(gong_wx, x[-1]) for x in bian_lines]

    dong = set(dong or [])
    kong = xunkong(day_gz)
    kong_set = set(kong)

    month_zhi = month_gz[-1] if month_gz else ""
    day_zhi = day_gz[1] if day_gz else ""

    return {
        "宫": f"{gong}宫({gong_wx})",
        "宫五行": gong_wx,
        "世爻": shi,
        "应爻": ying,
        "日辰": day_zhi,
        "月建": month_zhi,
        "旬空": kong,
        "伏神": fushen(ben_name, gong, gong_wx, ben_lines),
        "六爻": [
            {
                "爻": ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"][i],
                "六神": shen[i],
                "本卦": f"{ben_qin[i]} {ben_lines[i]}",
                "变卦": f"{bian_qin[i]} {bian_lines[i]}" if (i + 1) in dong else "",
                "世应": ("世" if (i + 1) == shi else ("应" if (i + 1) == ying else "")),
                "动": "动" if (i + 1) in dong else "",
                "空": "空" if ben_lines[i][-1] in kong_set else "",
                "破": "破" if (month_zhi and ben_lines[i][-1] == CHONG.get(month_zhi)) else "",
                "冲": "冲" if (day_zhi and ben_lines[i][-1] == CHONG.get(day_zhi)) else "",
                "化": _huajin_tui(ben_lines[i][-1], bian_lines[i][-1]) if (i + 1) in dong else "",
            }
            for i in range(6)
        ],
    }


def print_zhuang(r, yaos=None):
    """打印装卦表。yaos 为爻画列表（1=阳,0=阴，自下而上）；None 则据纳甲地支兜底。"""
    print(f"[装卦] {r['宫']}  月建:{r['月建'] or '—'}  日辰:{r['日辰']}  旬空:{r['旬空']}")
    print(f"       世爻:第{r['世爻']}爻  应爻:第{r['应爻']}爻")
    if r.get("伏神"):
        fs = "；".join(f"{f['六亲']}{f['干支']}伏{f['伏爻']}(飞{f['飞神']})" for f in r["伏神"])
        print(f"       伏神: {fs}")
    print(f"{'六神':<5}{'爻位':<5}{'爻画':<6}{'本卦(六亲 干支)':<16}{'变卦(六亲 干支)':<16}{'标'}")
    for i, x in enumerate(r["六爻"]):
        b = x["本卦"]
        v = x["变卦"] or "—"
        if yaos is not None:
            yang = yaos[i]
        else:
            yang = b.split()[1][-1] in "子寅辰午申戌"
        hua = ("━━━" if yang else "━ ━") + ("○" if x["动"] else " ")
        tag = x["世应"] + x["动"] + x["空"] + x["破"] + x["冲"] + x["化"]
        print(f"{x['六神']:<5}{x['爻']:<5}{hua:<6}{b:<16}{v:<16}{tag}")


# ======================================================================
# 用神分析 + 断卦分析 + 趋吉避凶（[规则推演] 只给方向，不作铁断）
# ======================================================================

# 问事 → 用神六亲（子串匹配；婚姻默认按男测婚取妻财，女测婚取官鬼需另注）
_YONGSHEN_KEYWORDS = [
    ("妻财", ["求财", "财运", "财", "生意", "投资", "货物", "妻"]),
    ("官鬼", ["官", "事业", "工作", "求职", "升职", "官司", "官非", "疾病", "病", "夫"]),
    ("父母", ["文书", "考", "学", "证件", "房产", "车", "合同", "长辈", "父"]),
    ("子孙", ["子女", "求子", "晚辈", "出行", "娱乐", "宠物", "健康"]),
    ("兄弟", ["兄弟", "合作", "合伙", "朋友", "竞争"]),
]
# 六爻原神 / 忌神（生用神 / 克用神）
_YUANSHEN = {"父母": "官鬼", "兄弟": "父母", "子孙": "兄弟", "妻财": "子孙", "官鬼": "妻财"}
_JISHEN = {"父母": "妻财", "兄弟": "官鬼", "子孙": "父母", "妻财": "兄弟", "官鬼": "子孙"}


def yongshen_for(question):
    """问事 → 用神六亲。未知问事默认看世爻（自身）。"""
    q = question or "通用"
    for yong, kws in _YONGSHEN_KEYWORDS:
        if any(k in q for k in kws):
            return yong
    return "世"


def _wx_level(zhi, month_zhi, day_zhi):
    """用神地支在月建/日辰下的旺衰（旺相平衰死）。[规则推演]"""
    wx = ZHI_WX[zhi]
    notes, score = [], 0
    for label, ref in (("月建", month_zhi), ("日辰", day_zhi)):
        if not ref:
            continue
        rwx = ZHI_WX[ref]
        if wx == rwx:
            notes.append(f"{label}同气"); score += 2
        elif SHENG.get(rwx) == wx:
            notes.append(f"{label}生我"); score += 2
        elif SHENG.get(wx) == rwx:
            notes.append(f"我生{label}"); score -= 1
        elif KE.get(rwx) == wx:
            notes.append(f"{label}克我"); score -= 2
        elif KE.get(wx) == rwx:
            notes.append(f"我克{label}"); score -= 1
    level = "旺" if score >= 3 else ("相" if score >= 1 else
             ("平" if score >= -1 else ("衰" if score >= -3 else "死")))
    return {"等级": level, "说明": notes, "分数": score}


def yongshen_analysis(r, question):
    """用神分析 + 断卦分析。返回 dict（[规则推演] 只给方向）。"""
    ys = yongshen_for(question)
    lines = r["六爻"]
    target = [x for x in lines if (x["世应"] == "世" if ys == "世" else x["本卦"].split()[0] == ys)]
    fushen = None
    if not target and ys != "世":
        for f in r.get("伏神", []):
            if f.get("六亲") == ys:
                fushen = f
                break
    if target:
        t = target[0]
        zhi = t["本卦"].split()[1][-1]
        pos = t["爻"]
    elif fushen:
        zhi = fushen["干支"][-1]
        pos = f"伏{fushen['伏爻']}"
    else:
        zhi, pos = None, "不现"
    lv = _wx_level(zhi, r["月建"], r["日辰"]) if zhi else {"等级": "不现", "说明": ["用神不上卦，看伏神或待出空"], "分数": 0}

    shi_x = next(x for x in lines if x["世应"] == "世")
    ying_x = next(x for x in lines if x["世应"] == "应")
    swx, ywx = ZHI_WX[shi_x["本卦"].split()[1][-1]], ZHI_WX[ying_x["本卦"].split()[1][-1]]
    if SHENG.get(ywx) == swx:
        shi_ying = ("应生世", "吉", "外境/对方来助我，顺遂")
    elif SHENG.get(swx) == ywx:
        shi_ying = ("世生应", "泄", "我付出多回报少，宜守")
    elif KE.get(ywx) == swx:
        shi_ying = ("应克世", "凶", "对方克我，压力阻力大")
    elif KE.get(swx) == ywx:
        shi_ying = ("世克应", "小吉", "我制彼，费力可成")
    else:
        shi_ying = ("世应比和", "平", "同心同力，成败在己")

    dim = {}
    dim["用神旺衰"] = {"旺": 20, "相": 12, "平": 0, "衰": -12, "死": -20, "不现": -15}.get(lv["等级"], 0)
    dim["世应关系"] = {"应生世": 15, "世克应": 8, "世应比和": 10, "世生应": -8, "应克世": -15}[shi_ying[0]]
    if ys != "世":
        for x in lines:
            if x["动"]:
                qin = x["本卦"].split()[0]
                if _YUANSHEN.get(ys) == qin:
                    dim.setdefault("原神动生", 15)
                elif _JISHEN.get(ys) == qin:
                    dim.setdefault("忌神动克", -15)
    if zhi:
        if zhi in r["旬空"]:
            dim.setdefault("用神旬空", -10)
        if r["月建"] and zhi == CHONG.get(r["月建"]):
            dim.setdefault("用神月破", -12)
    score = max(10, min(90, 50 + sum(dim.values())))
    jx = "吉" if score >= 65 else ("平" if score >= 45 else "凶")
    return {"用神": ys, "落爻": pos, "旺衰": lv, "世应": shi_ying,
            "评分": score, "分项": dim, "吉凶": jx}


def print_yongshen(r, question):
    """打印 用神分析 + 断卦分析 + 趋吉避凶。"""
    a = yongshen_analysis(r, question)
    print()
    print(f"【用神分析】问事：{question or '通用'}  →  用神：{a['用神']}  落：{a['落爻']}")
    print(f"    用神旺衰：{a['旺衰']['等级']}（{'、'.join(a['旺衰']['说明']) or '—'}）")
    print(f"    世应关系：{a['世应'][0]}（{a['世应'][1]}）— {a['世应'][2]}")
    print(f"【断卦分析】吉凶评分 {a['评分']}/100  →  {a['吉凶']}")
    print(f"    分项：{'；'.join(f'{k} {v:+d}' for k, v in a['分项'].items())}")
    print("【趋吉避凶】")
    if a["吉凶"] == "吉":
        print("  ✓ 用神旺相、世应得宜，可进宜主动，把握时机")
    elif a["吉凶"] == "平":
        print("  → 卦象平稳，宜守不宜攻，等待时机、多方核实")
    else:
        print("  ✗ 用神衰/受克或世应不利，宜缓守、换时机方位，忌硬碰")
    if a["旺衰"]["等级"] in ("衰", "死", "不现"):
        print("  · 用神衰弱：待月建/日辰生扶之日再动，忌冲动")
    if a["世应"][0] == "应克世":
        print("  · 应克世：防对方施压，宜退让换框架")
    if "用神旬空" in a["分项"]:
        print("  · 用神旬空：事虚待出空，暂勿定论")
    if "忌神动克" in a["分项"]:
        print("  · 忌神动克用神：防对应之失，原神可解")
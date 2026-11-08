# -*- coding: utf-8 -*-
"""八字流年/流月深度分析（在原 bazi.liunian/liuyue 基础上补强）。

在原「干支+生肖+纳音+五行生克」之上，补：
- 流年/流月干支与原局四柱、大运的合冲刑害叠合（xingchong.zhi_relation / gan_relation）
- 岁运并临（流年干支 == 大运干支）
- 天克地冲（流年干克日干/大运干 且 流年支冲日支/大运支）
- 犯太岁（值/冲/刑/害/破年支）
- 喜忌判定（旺衰扶抑为主 + 调候用神参考）
- 吉凶评分（喜忌 + 合冲刑害 加权，10~90 分档）

诚实边界：喜忌为 [规则推演/HEURISTIC] 扶抑模型 + 调候参考，只给方向，**不是精确吉凶**；
精确年份 + 具体生平的判断上限见 SKILL.md 第十五节（MingLi-Bench 36.2%）。
时柱按午时排（本命令只取年月日），涉及时柱的结论降级。
"""
import datetime
from lunar_python import Solar
from pan import bazi
import xingchong
from judge import tiaohou
_WX = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土",
       "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
_ZHI_WX = {"寅": "木", "卯": "木", "巳": "火", "午": "火", "申": "金", "酉": "金",
           "亥": "水", "子": "水", "辰": "土", "戌": "土", "丑": "土", "未": "土"}
_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
_WX_ALL = {"木", "火", "土", "金", "水"}

# 五行 → 喜用落地建议（方位/颜色/行业/数字/吉祥物/食物，[规则推演] 传统取象，只给方向）
_WX_ADVICE = {
    "木": {"方位": ["正东", "东南"], "颜色": ["绿色", "青色"],
           "行业": ["教育", "医药", "出版", "木材家具", "园林"],
           "数字": ["3", "8"], "吉祥物": ["绿色植物", "木质饰品"],
           "食物": ["菠菜", "芹菜", "绿色蔬菜"]},
    "火": {"方位": ["正南"], "颜色": ["红色", "紫色", "橙色"],
           "行业": ["照明", "电子科技", "能源", "传媒", "餐饮"],
           "数字": ["2", "7"], "吉祥物": ["红玛瑙", "红水晶"],
           "食物": ["西红柿", "红豆", "辣椒"]},
    "土": {"方位": ["西南", "中央", "东北"], "颜色": ["黄色", "棕色", "米色"],
           "行业": ["建筑", "房地产", "农业", "陶瓷"],
           "数字": ["5", "10"], "吉祥物": ["黄水晶", "陶瓷", "琥珀"],
           "食物": ["南瓜", "红薯", "小米", "山药"]},
    "金": {"方位": ["正西", "西北"], "颜色": ["白色", "金色", "银色"],
           "行业": ["金融", "机械", "五金", "汽车", "珠宝"],
           "数字": ["4", "9"], "吉祥物": ["金属饰品", "白水晶"],
           "食物": ["白萝卜", "百合", "梨"]},
    "水": {"方位": ["正北"], "颜色": ["黑色", "蓝色"],
           "行业": ["水产", "物流", "旅游", "贸易"],
           "数字": ["1", "6"], "吉祥物": ["黑曜石", "水晶"],
           "食物": ["黑豆", "黑芝麻", "海带"]},
}
_ADVICE_ORDER = ["方位", "颜色", "行业", "数字", "吉祥物", "食物"]
_ADVICE_ICON = {"方位": "🧭", "颜色": "🎨", "行业": "💼", "数字": "🔢", "吉祥物": "🎁", "食物": "🍵"}
_SX = "鼠牛虎兔龙蛇马羊猴鸡狗猪"


def _shengwo(wx):
    return [k for k, v in _SHENG.items() if v == wx][0]


def _kewo(wx):
    return [k for k, v in _KE.items() if v == wx][0]


def _deling_wangruo(ri_wx, yue_wx):
    """得令一维：月支生/同 日主 → 旺；否则弱。与 rules.bazi_deling 同口径。"""
    if ri_wx == yue_wx:
        return "旺"          # 比劫
    if _SHENG.get(yue_wx) == ri_wx:
        return "旺"          # 印
    return "弱"              # 官杀 / 食伤 / 财


def xi_ji_wx(qiang_ruo, ri_wx):
    """扶抑喜忌五行集合。返回 (喜集合, 忌集合)。"""
    if qiang_ruo == "强":
        xi = {_SHENG[ri_wx], _kewo(ri_wx), _KE[ri_wx]}   # 我生(食伤) + 克我(官杀) + 我克(财)
    else:
        xi = {_shengwo(ri_wx), ri_wx}                    # 生我(印) + 同我(比劫)
    return xi, _WX_ALL - xi


# ======================================================================
# P1 增强准确度：旺衰量化得分 / 格局成破救应 / 干支合化条件判断
# ======================================================================

_SHI_SHEN_GROUP = {
    "比肩": "比劫", "劫财": "比劫",
    "正印": "印", "偏印": "印",
    "食神": "食伤", "伤官": "食伤",
    "正财": "财", "偏财": "财",
    "正官": "官杀", "七杀": "官杀",
}


def wangshuai_score(ec):
    """日主旺衰量化得分（0-100）。[规则推演] 权重法：
    得令 40 + 得地 30 + 得势 15 + 得生 15；根气按 本气/中气/余气 分权（本气重、余气轻），
    避免布尔法把「中气比劫根」当强根（如戊土在子月仅午中气己土，量化后为中和偏弱）。
    >55 强、45-55 中和、<45 弱。"""
    ri_wx = _WX[ec.getDayGan()]
    parts = {}

    # 得令 40
    yue_ss = ec.getMonthShiShenZhi()[0]
    g = _SHI_SHEN_GROUP.get(yue_ss, "")
    if g == "比劫":
        parts["得令"] = (40, f"月支本气{yue_ss}(比劫)")
    elif g == "印":
        parts["得令"] = (30, f"月支本气{yue_ss}(印)")
    elif g == "食伤":
        parts["得令"] = (15, f"月支本气{yue_ss}(食伤)")
    elif g == "财":
        parts["得令"] = (10, f"月支本气{yue_ss}(财)")
    else:
        parts["得令"] = (0, f"月支本气{yue_ss}(官杀)")

    # 得地 30（四支藏干比劫根，本气/中气/余气分权；月支本气已在得令计）
    _POS_W = {"日": (12, 7, 3), "年": (8, 4, 2), "时": (8, 4, 2), "月": (0, 4, 2)}
    _di, _di_detail = 0, []
    for pos, hg, ss in (("年", ec.getYearHideGan(), ec.getYearShiShenZhi()),
                        ("月", ec.getMonthHideGan(), ec.getMonthShiShenZhi()),
                        ("日", ec.getDayHideGan(), ec.getDayShiShenZhi()),
                        ("时", ec.getTimeHideGan(), ec.getTimeShiShenZhi())):
        for i, s in enumerate(ss):
            if _SHI_SHEN_GROUP.get(s) == "比劫":
                w = _POS_W[pos][i] if i < len(_POS_W[pos]) else _POS_W[pos][-1]
                _di += w
                _di_detail.append(f"{pos}支{hg[i]}({s})+{w}")
    _di = min(_di, 30)
    parts["得地"] = (_di, "四支比劫根" + ("：" + "，".join(_di_detail) if _di_detail else "：无"))

    # 得势 15（天干比劫，日主除外）
    gans_ss = [ec.getYearShiShenGan(), ec.getMonthShiShenGan(), ec.getTimeShiShenGan()]
    _shi = min(sum(5 for s in gans_ss if _SHI_SHEN_GROUP.get(s) == "比劫"), 15)
    parts["得势"] = (_shi, "天干比劫")

    # 得生 15（印：天干 5 / 藏干 3）
    _sheng = sum(5 for s in gans_ss if _SHI_SHEN_GROUP.get(s) == "印")
    for hg, ss in ((ec.getYearHideGan(), ec.getYearShiShenZhi()),
                   (ec.getMonthHideGan(), ec.getMonthShiShenZhi()),
                   (ec.getDayHideGan(), ec.getDayShiShenZhi()),
                   (ec.getTimeHideGan(), ec.getTimeShiShenZhi())):
        _sheng += sum(3 for s in ss if _SHI_SHEN_GROUP.get(s) == "印")
    _sheng = min(_sheng, 15)
    parts["得生"] = (_sheng, "印(天干5/藏干3)")

    total = sum(p[0] for p in parts.values())
    level = "强" if total > 55 else ("中和" if total >= 45 else "弱")
    return {"得分": round(total, 1), "档次": level, "分项": parts, "日主五行": ri_wx}


def wangshuai_ratio(ec):
    """日主旺衰连续 ratio（0-1 同党占比）。复用 `judge/bazi_chain.py::day_master_strength`
    的成分加权（同党=比劫+印，异党=食伤+财+官杀，`ratio = 同党/(同党+异党)`），
    与 `wangshuai_score`（0-100 帮身绝对分）互补——score 暴露「帮身绝对分」，
    ratio 暴露「同党/(同党+异党)」归一化连续值，收口「旺衰量化暴露连续 ratio（现为离散分）」。
    返回 {ratio, 档次, 有根, 同党, 异党, 净值}，五档分界沿用 bazi_chain.RATIO_BANDS。"""
    from judge import bazi_chain as bc
    quad = {
        "year": (ec.getYearGan(), ec.getYearZhi()),
        "month": (ec.getMonthGan(), ec.getMonthZhi()),
        "day": (ec.getDayGan(), ec.getDayZhi()),
        "hour": (ec.getTimeGan(), ec.getTimeZhi()),
    }
    s = bc.day_master_strength(quad)
    return {"ratio": s.ratio, "档次": s.label, "有根": s.has_root,
            "同党": s.support, "异党": s.drain, "净值": s.net}


_SS_EXPAND = {
    "伤官": ["伤官"], "食神": ["食神"], "偏印": ["偏印"], "正官": ["正官"], "七杀": ["七杀"],
    "印": ["正印", "偏印"], "财": ["正财", "偏财"], "比劫": ["比肩", "劫财"],
    "官杀": ["正官", "七杀"], "食伤": ["食神", "伤官"],
}

# 格局 → (破格十神, 救应十神)（据《子平真诠》GE_JU_JIU_YING 表机器化）
_GEJU_PO = {
    "正官格": ("伤官", "印"), "七杀格": ("财", "食伤/印"),
    "正财格": ("比劫", "官杀"), "偏财格": ("比劫", "官杀"),
    "正印格": ("财", "比劫"), "偏印格": ("食伤", "财"),
    "食神格": ("偏印", "财"), "伤官格": ("正官", "财/印"),
    "建禄格": ("比劫", "官杀"), "羊刃格": ("财", "七杀"),
}


def _has_shishen(ec, ss_names):
    """某十神是否出现在天干或藏干。ss_names 为十神名列表。"""
    gans = [ec.getYearShiShenGan(), ec.getMonthShiShenGan(),
            ec.getDayShiShenGan(), ec.getTimeShiShenGan()]
    zhis = []
    for ss in (ec.getYearShiShenZhi(), ec.getMonthShiShenZhi(),
               ec.getDayShiShenZhi(), ec.getTimeShiShenZhi()):
        zhis += ss
    return any(s in gans or s in zhis for s in ss_names)


def _expand_ss(token):
    return _SS_EXPAND.get(token, [token])


def geju_chengjiu(ec, ge_name):
    """格局成破救应（《子平真诠》）。返回 {格局, 判定, 依据}。"""
    # ding_ge 返回「正财/正官/伤官…」或「建禄格/羊刃格」，统一补「格」后缀查表
    key = ge_name if ge_name.endswith("格") else ge_name + "格"
    po_jiu = _GEJU_PO.get(key)
    if not po_jiu:
        return {"格局": ge_name, "判定": "未定义成破", "依据": "非十神格或表外格局"}
    po, jiu = po_jiu
    has_po = any(_has_shishen(ec, _expand_ss(t)) for t in po.split("/"))
    has_jiu = any(_has_shishen(ec, _expand_ss(t)) for t in jiu.split("/"))
    if has_po and has_jiu:
        return {"格局": ge_name, "判定": "破格有救", "依据": f"见破格十神({po})，但有救应({jiu})"}
    if has_po:
        return {"格局": ge_name, "判定": "破格", "依据": f"见破格十神({po})，无救应({jiu})"}
    return {"格局": ge_name, "判定": "成格", "依据": f"无破格十神({po})"}


# 合化化神五行（合化需化神得令/透干/有本气根，否则合而不化）
_GAN_HE_WX = {"甲": "土", "己": "土", "乙": "金", "庚": "金", "丙": "水", "辛": "水",
              "丁": "木", "壬": "木", "戊": "火", "癸": "火"}
_ZHI_HE_WX = {"子": "土", "丑": "土", "寅": "木", "亥": "木", "卯": "火", "戌": "火",
              "辰": "金", "酉": "金", "巳": "水", "申": "水", "午": "土", "未": "土"}
_SAN_HE_WX = {"申子辰": "水", "亥卯未": "木", "寅午戌": "火", "巳酉丑": "金"}


def hehua_judge(hua_wx, ec):
    """判断合化是否成化：化神五行得月令/透干/有本气根 → 成化；否则合而不化。"""
    yue_wx = _ZHI_WX[ec.getMonthZhi()]
    de_ling = (yue_wx == hua_wx) or (_SHENG.get(yue_wx) == hua_wx)
    gans = [ec.getYearGan(), ec.getMonthGan(), ec.getDayGan(), ec.getTimeGan()]
    tou_gan = any(_WX[g] == hua_wx for g in gans)
    you_gen = False
    for hg in (ec.getYearHideGan(), ec.getMonthHideGan(),
               ec.getDayHideGan(), ec.getTimeHideGan()):
        if hg and _WX[hg[0]] == hua_wx:
            you_gen = True
    return "成化" if (de_ling or tou_gan or you_gen) else "合而不化"


def hehua_report(ec):
    """八字内所有天干五合/地支六合/三合的合化判断。返回 [{类型, 组合, 化神, 判定}]。"""
    gans = [ec.getYearGan(), ec.getMonthGan(), ec.getDayGan(), ec.getTimeGan()]
    zhis = [ec.getYearZhi(), ec.getMonthZhi(), ec.getDayZhi(), ec.getTimeZhi()]
    out = []
    # 天干五合（相邻紧贴）
    for i in range(len(gans) - 1):
        a, b = gans[i], gans[i + 1]
        if xingchong.GAN_HE.get(a) == b:
            out.append({"类型": "天干五合", "组合": f"{a}{b}",
                        "化神": _GAN_HE_WX[a], "判定": hehua_judge(_GAN_HE_WX[a], ec)})
    # 地支六合（相邻紧贴）
    for i in range(len(zhis) - 1):
        a, b = zhis[i], zhis[i + 1]
        if xingchong.LIU_HE.get(a) == b:
            out.append({"类型": "地支六合", "组合": f"{a}{b}",
                        "化神": _ZHI_HE_WX[a], "判定": hehua_judge(_ZHI_HE_WX[a], ec)})
    # 地支三合（三支齐全）
    for combo, hua in _SAN_HE_WX.items():
        if all(z in zhis for z in combo):
            out.append({"类型": "地支三合", "组合": combo,
                        "化神": hua, "判定": hehua_judge(hua, ec)})
    return out


def comprehensive_score(ws, cj, tiao):
    """综合评分（0-100，[规则推演] 透明加权，只给方向不作铁断）。
    日主平衡 40 + 格局 35 + 调候 25；分项透明可复核。"""
    parts = {}
    w = ws["得分"]
    if 45 <= w <= 55:
        parts["日主平衡"] = 40
    elif 38 <= w < 45 or 55 < w <= 62:
        parts["日主平衡"] = 28
    elif 25 <= w < 38 or 62 < w <= 72:
        parts["日主平衡"] = 16
    else:
        parts["日主平衡"] = 8
    parts["格局"] = {"成格": 35, "破格有救": 24, "破格": 10,
                     "未定义成破": 20}.get(cj["判定"], 20)
    parts["调候"] = 25 if tiao else 8
    total = sum(parts.values())
    level = "上" if total >= 78 else ("中上" if total >= 62 else
                                      ("中" if total >= 45 else "中下"))
    return {"总分": total, "分项": parts, "等级": level}


def mingli_analysis(y, mo, d, hh=12, mi=0, ss=0, gender=1):
    """命理增强分析：旺衰量化 + 格局成破 + 合化判断。打印并返回 dict。"""
    ec = Solar.fromYmdHms(y, mo, d, hh, mi, ss).getLunar().getEightChar()
    ws = wangshuai_score(ec)
    wsr = wangshuai_ratio(ec)
    ge = tiaohou.ding_ge(y, mo, d, hh, gender)
    cj = geju_chengjiu(ec, ge["格局"])
    hh_report = hehua_report(ec)
    print("[旺衰量化] 日主{}{}({}) 得分 {} 分 → {}  连续ratio {:.2f}（同党{}/异党{}）→ {}  ".format(
        ec.getDayGan(), ec.getDayZhi(), ws["日主五行"], ws["得分"], ws["档次"],
        wsr["ratio"], wsr["同党"], wsr["异党"], wsr["档次"]))
    print("  " + "；".join(f"{k}{v[0]}分({v[1]})" for k, v in ws["分项"].items()))
    print(f"[格局] {ge['格局']}（{ge['依据']}）→ {cj['判定']}：{cj['依据']}")
    if hh_report:
        for h in hh_report:
            print(f"[合化] {h['类型']}{h['组合']}化{h['化神']} → {h['判定']}")
    else:
        print("[合化] 原局无天干五合/地支六合/三合")

    # 喜忌五行 + 综合评分 + 趋吉避凶六大维度（[规则推演] 只给方向，不作铁断）
    xi, ji = xi_ji_wx(ws["档次"], ws["日主五行"])
    tiao = tiaohou.tiao_hou_yongshen(ec.getDayGan(), ec.getMonthZhi())
    score = comprehensive_score(ws, cj, tiao)
    print()
    print(f"【喜忌五行】喜：{'、'.join(sorted(xi))}   忌：{'、'.join(sorted(ji))}" +
          (f"   调候：{'、'.join(tiao)}" if tiao else ""))
    print(f"【综合评分】{score['总分']}/100  {score['等级']}   " +
          f"({'；'.join(f'{k} {v}' for k, v in score['分项'].items())})")
    print("【趋吉避凶】按喜用五行取象（[规则推演] 只给方向）")
    for k in _ADVICE_ORDER:
        vals = []
        for wx in sorted(xi):
            vals += _WX_ADVICE[wx][k]
        print(f"  {_ADVICE_ICON[k]} 吉利{k}：{'、'.join(dict.fromkeys(vals))}")
    by = bingyao(ws, cj, sorted(xi), sorted(ji))
    print()
    print(f"【病药框架】{by}")
    return {"旺衰": ws, "旺衰ratio": wsr, "格局": cj, "合化": hh_report,
            "喜": sorted(xi), "忌": sorted(ji), "综合评分": score, "病药": by}


def bingyao(ws, cj, xi, ji):
    """病药框架（借鉴 yueyuan-bazi）：病在X、药为Y。"""
    dx = ws.get("档次", "")
    gj = cj.get("格局", "") if isinstance(cj, dict) else str(cj)
    if dx in ("弱", "偏弱"):
        if "伤官" in gj:
            bing, yao = "伤官旺泄身、日主身弱", "印星生身制伤（伤官佩印）"
        elif "杀" in gj or "偏官" in gj:
            bing, yao = "七杀重而日主身弱", "印星化杀生身"
        elif "财" in gj:
            bing, yao = "财多身弱（富屋贫人）", "印比帮身任财"
        elif "官" in gj:
            bing, yao = "官重而日主身弱", "印星化官生身"
        elif "食" in gj or "伤" in gj:
            bing, yao = "食伤泄身、日主身弱", "印星制食伤生身"
        else:
            bing, yao = f"日主身弱、忌{'、'.join(ji)}当令", f"印比生扶（喜{'、'.join(xi)}）"
    elif dx in ("强", "偏强"):
        bing, yao = f"日主身强、{'、'.join(ji)}过旺", f"财官食伤泄耗（喜{'、'.join(xi)}）"
    else:
        bing, yao = "中和、无明显之病", "顺格局调候取用"
    return f"病在{bing}，药为{yao}"


def _pillars(b):
    """八字符 → {年:干支, 月:干支, 日:干支, 时:干支}。"""
    return {"年": b.getYear(), "月": b.getMonth(), "日": b.getDay(), "时": b.getTime()}


def _dayun_map(b, gender):
    """{年份: 大运干支}，起运前标 None。dys[0] 为起运前空干支。"""
    dys = b.getYun(gender).getDaYun()
    m = {}
    for dy in dys:
        gz = dy.getGanZhi()
        if not gz:
            continue
        for yr in range(dy.getStartYear(), dy.getEndYear() + 1):
            m[yr] = gz
    return m


def _cross_liunian(liu_gan, liu_zhi, pillars, dayun_gz):
    """流年干支 与 原局四柱 + 大运 的合冲刑害叠合。
    返回 [{柱, 干关系, 支关系列表, 吉凶}]。"""
    rows = []
    for pos, gz in pillars.items():
        pg, pz = gz[0], gz[1]
        gr = xingchong.gan_relation(liu_gan, pg)
        zr = xingchong.zhi_relation(liu_zhi, pz)
        rows.append({"柱": pos, "干支": gz, "干": gr, "支": zr})
    if dayun_gz:
        dg, dz = dayun_gz[0], dayun_gz[1]
        gr = xingchong.gan_relation(liu_gan, dg)
        zr = xingchong.zhi_relation(liu_zhi, dz)
        rows.append({"柱": "大运", "干支": dayun_gz, "干": gr, "支": zr})
    return rows


def _fantaisui(liu_zhi, nian_zhi):
    """犯太岁检测：值/冲/刑/害/破。返回说明字符串或 ''。"""
    if liu_zhi == nian_zhi:
        return "值太岁（本命年）"
    zr = xingchong.zhi_relation(liu_zhi, nian_zhi)
    rels = [r["关系"] for r in zr["关系列表"]]
    out = []
    for r in rels:
        if r == "六冲":
            out.append("冲太岁")
        elif "刑" in r:
            out.append("刑太岁")
        elif r == "六害":
            out.append("害太岁")
        elif r == "相破":
            out.append("破太岁")
    return "、".join(out)


def _tianke_dichong(liu_gan, liu_zhi, pillars, dayun_gz):
    """天克地冲：流年干克X干 且 流年支冲X支。X=日柱或大运。返回说明字符串或 ''。"""
    out = []
    rigan, rizhi = pillars["日"][0], pillars["日"][1]
    if xingchong.gan_relation(liu_gan, rigan)["关系"] == "相克" and \
            any(r["关系"] == "六冲" for r in xingchong.zhi_relation(liu_zhi, rizhi)["关系列表"]):
        out.append("天克地冲日柱")
    if dayun_gz:
        dg, dz = dayun_gz[0], dayun_gz[1]
        if xingchong.gan_relation(liu_gan, dg)["关系"] == "相克" and \
                any(r["关系"] == "六冲" for r in xingchong.zhi_relation(liu_zhi, dz)["关系列表"]):
            out.append("岁运天克地冲")
    return "、".join(out)


def _score_year(liu_gan_wx, liu_zhi_wx, xi, ji, rows, flags):
    """透明评分：喜忌 ±15，合冲刑害逐柱加权，特殊格局扣分，夹到 10~90。"""
    s = 50
    if liu_gan_wx in xi:
        s += 15
    elif liu_gan_wx in ji:
        s -= 15
    if liu_zhi_wx in xi:
        s += 15
    elif liu_zhi_wx in ji:
        s -= 15
    for row in rows:
        jx = row["支"]["吉凶"]
        if jx == "吉":
            s += 10
        elif jx == "半吉":
            s += 5
        elif jx == "凶":
            s -= 15 if row["柱"] in ("日", "大运") else 10
        elif jx == "半凶":
            s -= 8
    if flags.get("tianke_dichong"):
        s -= 20
    if flags.get("fantaisui") and "冲" in flags["fantaisui"]:
        s -= 10
    return max(10, min(90, s))


def _base(y, mo, d, gender):
    """排原局 + 旺衰量化 + 喜忌 + 大运映射。返回 dict。"""
    b = Solar.fromYmdHms(y, mo, d, 12, 0, 0).getLunar().getEightChar()
    ri_gan = b.getDayGan()
    ri_wx = _WX[ri_gan]
    yue_wx = _ZHI_WX[b.getMonthZhi()]
    wscore = wangshuai_score(b)
    qr = wscore["档次"]
    deling = _deling_wangruo(ri_wx, yue_wx)
    # 冲突：得令一维与量化档次明显相反（量化弱而一维旺 / 量化强而一维弱）
    conflict = (deling == "旺" and qr == "弱") or (deling == "弱" and qr == "强")
    xi, ji = xi_ji_wx(qr, ri_wx)
    tiao = tiaohou.tiao_hou_yongshen(ri_gan, b.getMonthZhi())
    return {
        "b": b, "ri_gan": ri_gan, "ri_wx": ri_wx, "qr": qr,
        "deling": deling, "conflict": conflict,
        "xi": xi, "ji": ji, "tiao": tiao,
        "wscore": wscore, "dayun_map": _dayun_map(b, gender),
        "pillars": _pillars(b),
    }


def liunian_deep(y=None, mo=None, d=None, gender=1, start=None, n=10):
    """流年深度分析。返回 {日主, 身强弱, 喜, 忌, 调候, data:[每年明细]}。"""
    now = datetime.datetime.now()
    if y is None:
        y, mo, d = now.year, now.month, now.day
    start = start or now.year
    base = _base(y, mo, d, gender)
    b = base["b"]
    nian_zhi = b.getYearZhi()
    print(f"[八字流年深度] 日主 {base['ri_gan']}{b.getDayZhi()}({base['ri_wx']})  "
          f"身{base['qr']}(得分{base['wscore']['得分']},得令{base['deling']})  喜{''.join(sorted(base['xi']))}  忌{''.join(sorted(base['ji']))}  "
          f"调候用神(穷通宝鉴){'、'.join(base['tiao']) or '无'}  {start}~{start + n - 1} 年")
    if base["conflict"]:
        print("  ⚠ 得令一维与四维综合判旺衰相反，喜忌可能翻转，本盘按四维综合取喜忌，建议双盘对照（信号冲突降级）。")
    print(f"  （扶抑+调候参考，[规则推演] 只示方向；时柱按午时，涉及时柱结论降级）")
    data = []
    for yr in range(start, start + n):
        gz = bazi._ganzhi_year(yr)
        lg, lz = gz[0], gz[1]
        lg_wx, lz_wx = _WX[lg], _ZHI_WX[lz]
        dy = base["dayun_map"].get(yr)
        rows = _cross_liunian(lg, lz, base["pillars"], dy)
        ft = _fantaisui(lz, nian_zhi)
        tkc = _tianke_dichong(lg, lz, base["pillars"], dy)
        sbl = dy is not None and gz == dy
        flags = {"tianke_dichong": tkc, "fantaisui": ft}
        score = _score_year(lg_wx, lz_wx, base["xi"], base["ji"], rows, flags)
        # 五行生克标签（保留原 bazi._liunian_rel 口径）
        rel = bazi._liunian_rel(base["ri_wx"], lg_wx)
        ny = Solar.fromYmdHms(yr, 7, 1, 12, 0, 0).getLunar().getYearNaYin()
        # 组装输出行
        tags = []
        if sbl:
            tags.append("岁运并临")
        if tkc:
            tags.append(tkc)
        if ft:
            tags.append(ft)
        chong = []
        for row in rows:
            for r in row["支"]["关系列表"]:
                if r["关系"] != "平":
                    chong.append(f"{row['柱']}支{r['关系']}")
        xj = "喜" if lg_wx in base["xi"] else ("忌" if lg_wx in base["ji"] else "平")
        line = (f"  {yr} {gz}  {score:>3}分  {rel:<9} {xj}"
                f"  大运:{dy or '起运前'}  {('[' + ' '.join(tags) + ']') if tags else ''}")
        print(line)
        if chong:
            print(f"       合冲刑害: {'，'.join(chong)}")
        data.append({"year": yr, "gz": gz, "score": score, "dayun": dy,
                     "rel": rel, "tags": tags, "chonghe": chong,
                     "fantaisui": ft, "tianke_dichong": tkc, "suiyun_binglin": sbl,
                     "xi_ji": xj})
    return {"日主": base["ri_gan"] + b.getDayZhi(), "身强弱": base["qr"],
            "喜": sorted(base["xi"]), "忌": sorted(base["ji"]),
            "调候": base["tiao"], "start": start, "n": n, "data": data}


def liuyue_deep(y=None, mo=None, d=None, gender=1, year=None):
    """流月深度分析（某流年 12 个月）。返回 {日主, 身强弱, 喜, 忌, data:[每月明细]}。"""
    now = datetime.datetime.now()
    if y is None:
        y, mo, d = now.year, now.month, now.day
    year = year or now.year
    base = _base(y, mo, d, gender)
    b = base["b"]
    nian_zhi = b.getYearZhi()
    liu_year_gz = bazi._ganzhi_year(year)
    dy = base["dayun_map"].get(year)
    print(f"[八字流月深度] 日主 {base['ri_gan']}{b.getDayZhi()}({base['ri_wx']})  "
          f"身{base['qr']}(得分{base['wscore']['得分']},得令{base['deling']})  喜{''.join(sorted(base['xi']))}  忌{''.join(sorted(base['ji']))}  "
          f"{year} 年（{liu_year_gz}）流月  大运:{dy or '起运前'}")
    if base["conflict"]:
        print("  ⚠ 得令一维与四维综合判旺衰相反，喜忌可能翻转，本盘按四维综合取喜忌，建议双盘对照（信号冲突降级）。")
    data = []
    for m in range(1, 13):
        l = Solar.fromYmd(year, m, 15).getLunar()
        gz = l.getMonthInGanZhi()
        mg, mz = gz[0], gz[1]
        mg_wx = _WX[mg]
        rows = _cross_liunian(mg, mz, base["pillars"], dy)
        ft = _fantaisui(mz, nian_zhi)
        tkc = _tianke_dichong(mg, mz, base["pillars"], dy)
        flags = {"tianke_dichong": tkc, "fantaisui": ft}
        score = _score_year(mg_wx, _ZHI_WX[mz], base["xi"], base["ji"], rows, flags)
        rel = bazi._liunian_rel(base["ri_wx"], mg_wx)
        chong = []
        for row in rows:
            for r in row["支"]["关系列表"]:
                if r["关系"] != "平":
                    chong.append(f"{row['柱']}支{r['关系']}")
        tags = [t for t in (tkc, ft) if t]
        xj = "喜" if mg_wx in base["xi"] else ("忌" if mg_wx in base["ji"] else "平")
        print(f"  {m:>2}月 {gz}  {score:>3}分  {rel:<9} {xj}  {('[' + ' '.join(tags) + ']') if tags else ''}")
        if chong:
            print(f"       合冲刑害: {'，'.join(chong)}")
        data.append({"month": m, "gz": gz, "score": score, "rel": rel,
                     "xi_ji": xj, "tags": tags, "chonghe": chong})
    return {"日主": base["ri_gan"] + b.getDayZhi(), "身强弱": base["qr"],
            "喜": sorted(base["xi"]), "忌": sorted(base["ji"]),
            "流年": year, "data": data}


if __name__ == "__main__":
    import sys
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    liunian_deep(2000, 1, 1, 1, 2026, 10)
    print()
    liuyue_deep(2000, 1, 1, 1, 2026)
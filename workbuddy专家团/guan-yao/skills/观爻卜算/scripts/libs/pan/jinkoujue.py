# -*- coding: utf-8 -*-
"""大六壬金口诀排盘 + 断语库（四位：人元 / 贵神 / 将神 / 地分）。

出处：《六壬神课金口诀古本》（原文见 `国学czhengli/txt/[易藏] 六壬神课金口诀古本.txt`）。
本模块为确定性排盘 + 结构化断语层：四位排布、五动爻、三动、干神将方生克、
用爻（阴阳次第）、五行休旺、五行聚管、十二贵神/十二将神吉凶。断卦时仍须按
条目名 Grep 原文佐证（双重保证）。

用法：
  from pan.jinkoujue import cast
  r = cast(dt=None, difen=None)      # difen 为地分（地支或方位），缺省取时支
  print_pan(r)
"""
import datetime

from lunar_python import Solar

SOURCE = "《六壬神课金口诀古本》"

_GAN = "甲乙丙丁戊己庚辛壬癸"
_ZHI = "子丑寅卯辰巳午未申酉戌亥"
_ZHIDX = {z: i for i, z in enumerate(_ZHI)}
_GANDX = {g: i for i, g in enumerate(_GAN)}

# —— 五行 ——
_GAN_WX = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
           "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
_ZHI_WX = {"寅": "木", "卯": "木", "巳": "火", "午": "火", "申": "金", "酉": "金",
           "亥": "水", "子": "水", "辰": "土", "戌": "土", "丑": "土", "未": "土"}
_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}  # 我生
_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}      # 我克

# 阴阳：阳干/阳支
_YANG_GAN = set("甲丙戊庚壬")
_YANG_ZHI = set("子寅辰午申戌")

# —— 十二将神（月将）：地支 -> (将名, 五行, 阴阳, 月序) ——
# 正月登明亥、二月河魁戌……十二月神后子（逆布十二位）
_JIANGSHEN = {
    "亥": ("登明", "水", "阴", 1), "戌": ("河魁", "土", "阳", 2),
    "酉": ("从魁", "金", "阴", 3), "申": ("传送", "金", "阳", 4),
    "未": ("小吉", "土", "阴", 5), "午": ("胜光", "火", "阳", 6),
    "巳": ("太乙", "火", "阴", 7), "辰": ("天罡", "土", "阳", 8),
    "卯": ("太冲", "木", "阴", 9), "寅": ("功曹", "木", "阳", 10),
    "丑": ("大吉", "土", "阴", 11), "子": ("神后", "水", "阳", 12),
}

# —— 十二贵神（顺行序：天乙 -> 天后）：(名, 五行, 阴阳, 吉凶, 主事) ——
_GUISHEN = [
    ("天乙", "土", "阴", "吉", "喜庆多、谒贵成就、贵人接引"),
    ("螣蛇", "火", "阴", "凶", "惊忧疑、阴私、虚惊怪异、失物官灾"),
    ("朱雀", "火", "阳", "凶", "口舌、文书、官讼、火光飞鸟"),
    ("六合", "木", "阴", "吉", "和合、婚姻、交易、赏赐"),
    ("勾陈", "土", "阳", "凶", "田土、争讼、牵滞勾连"),
    ("青龙", "木", "阳", "吉", "财喜、升迁、富足、贵人"),
    ("天空", "土", "阳", "凶", "虚诈、惊恐、落空、奴婢走失"),
    ("白虎", "金", "阳", "凶", "血伤、丧病、道路、威猛"),
    ("太常", "土", "阴", "吉", "酒食、财帛、和合、亨通"),
    ("玄武", "水", "阳", "凶", "盗骗、暗昧、走失、逃亡"),
    ("太阴", "金", "阴", "吉", "阴私、暗助、财帛、妇女"),
    ("天后", "水", "阴", "吉", "恩泽、婚喜、荫庇、财兴"),
]
_GUISHEN_IDX = {name: i for i, (name, *_rest) in enumerate(_GUISHEN)}

# —— 贵人起例（日干 -> (昼贵人支, 夜贵人支)）——
# 甲戊庚牛羊、乙己鼠猴、丙丁猪鸡、壬癸蛇兔、六辛马虎
_GUIREN = {
    "甲": ("丑", "未"), "戊": ("丑", "未"), "庚": ("丑", "未"),
    "乙": ("子", "申"), "己": ("子", "申"),
    "丙": ("亥", "酉"), "丁": ("亥", "酉"),
    "壬": ("巳", "卯"), "癸": ("巳", "卯"),
    "辛": ("午", "寅"),
}
# 顺逆：贵人在亥子丑寅卯辰顺行，在巳午未申酉戌逆行（「从戌至巳逆行，以辰到亥顺就」）
_SHUN_ZHI = set("亥子丑寅卯辰")

# —— 五子元遁遁首（日干 -> 子时起干）——
_DUNSHOU = {"甲": "甲", "己": "甲", "乙": "丙", "庚": "丙", "丙": "戊", "辛": "戊",
            "丁": "庚", "壬": "庚", "戊": "壬", "癸": "壬"}

# —— 月将（以中气为界；lunar_python 节气名为简体）——
_YUEJIANG = {
    "雨水": "亥", "惊蛰": "亥", "春分": "戌", "清明": "戌",
    "谷雨": "酉", "立夏": "酉", "小满": "申", "芒种": "申",
    "夏至": "未", "小暑": "未", "大暑": "午", "立秋": "午",
    "处暑": "巳", "白露": "巳", "秋分": "辰", "寒露": "辰",
    "霜降": "卯", "立冬": "卯", "小雪": "寅", "大雪": "寅",
    "冬至": "丑", "小寒": "丑", "大寒": "子", "立春": "子",
}

# —— 五行休旺（春/夏/四季/秋/冬，据月支）——
_WANGXIU = {
    "春":   {"旺": "木", "相": "火", "死": "土", "囚": "金", "休": "水"},
    "夏":   {"旺": "火", "相": "土", "死": "金", "囚": "水", "休": "木"},
    "四季": {"旺": "土", "相": "金", "死": "水", "囚": "木", "休": "火"},
    "秋":   {"旺": "金", "相": "水", "死": "木", "囚": "火", "休": "土"},
    "冬":   {"旺": "水", "相": "木", "死": "火", "囚": "土", "休": "金"},
}
_SEASON = {"寅": "春", "卯": "春", "巳": "夏", "午": "夏",
           "辰": "四季", "戌": "四季", "丑": "四季", "未": "四季",
           "申": "秋", "酉": "秋", "亥": "冬", "子": "冬"}

# —— 方位 -> 地分（八方位，每方二支取主支）——
_FANGWEI = {"北": "子", "南": "午", "东": "卯", "西": "酉",
            "东北": "丑", "东南": "辰", "西南": "未", "西北": "戌",
            "子": "子", "丑": "丑", "寅": "寅", "卯": "卯", "辰": "辰", "巳": "巳",
            "午": "午", "未": "未", "申": "申", "酉": "酉", "戌": "戌", "亥": "亥"}

# —— 五行聚管（四位五行组合断，签名按 木火土金水 计数）——
_JULU = {
    "金2水2": ("吉", "子孙荣旺、妻有姿质、家道大富（最吉）"),
    "水3金1": ("吉", "主文章、蟾宫折桂、不久得官或大富"),
    "金3火1": ("吉", "家业富贵、贵人接引、子孙兴盛（凶中取吉）"),
    "土3金1": ("吉", "出英俊子孙、聪慧有文、科甲或大富"),
    "水2土1木1": ("吉", "家道荣昌、子孙兴盛、资财进益（先忧后喜）"),
    "水2木1金1": ("吉", "子孙聪慧、田宅兴旺、资财喜美"),
    "木2土2": ("凶", "克刑伤、劳病、官事牢狱争讼不绝（大凶）"),
    "火3水1": ("凶", "家贫破败、子孙作贼、刺配他方（大凶）"),
    "火3金1": ("凶", "灾病疮痍、药不能治、死伤人口（大凶）"),
    "火2水1土1": ("凶", "刑伤、阴人不良、伤母、资财破败"),
    "水3火1": ("凶", "家贫庄田破散、子孙作贼（凶）"),
    "木2火1水1": ("凶", "官灾病患、淫乱、失财（凶）"),
}


def _gan_yin_yang(gan):
    return "阳" if gan in _YANG_GAN else "阴"


def _zhi_yin_yang(zhi):
    return "阳" if zhi in _YANG_ZHI else "阴"


def _get_jieqi_and_yuejiang(dt):
    """取上一个节气名 + 月将地支。"""
    solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    lunar = solar.getLunar()
    jieqi = lunar.getPrevJieQi().getName()
    yuejiang = _YUEJIANG.get(jieqi, "亥")
    return lunar, jieqi, yuejiang


def _difen_to_zhi(difen):
    """地分输入归一为地支；缺省/不识则返回 None。"""
    if not difen:
        return None
    return _FANGWEI.get(str(difen).strip())


def cast(dt=None, difen=None):
    """金口诀起盘。dt 为占时（缺省当前），difen 为地分（地支或方位，缺省取时支）。

    返回 dict（四位 + 五动三动 + 用爻 + 旺相 + 聚管），可 print_pan 或供 htmlpan/测试。
    """
    dt = dt or datetime.datetime.now()
    lunar, jieqi, yuejiang_zhi = _get_jieqi_and_yuejiang(dt)

    day_gz = lunar.getDayInGanZhi()
    hour_gz = lunar.getTimeInGanZhi()
    day_gan, day_zhi = day_gz[0], day_gz[1]
    hour_zhi = hour_gz[1]
    month_zhi = lunar.getMonthZhi()

    # 地分：缺省取时支（自动起盘），可传方位/地支覆盖
    difen_zhi = _difen_to_zhi(difen) or hour_zhi

    # —— 将神：月将加时，顺数到地分 ——
    step = (_ZHIDX[difen_zhi] - _ZHIDX[hour_zhi]) % 12
    jiang_zhi = _ZHI[(_ZHIDX[yuejiang_zhi] + step) % 12]
    jiang_name, jiang_wx, jiang_yy, _m = _JIANGSHEN[jiang_zhi]

    # —— 贵神：天乙贵人依日干起，昼夜定支，顺逆数到地分 ——
    day_or_night = "昼" if hour_zhi in "卯辰巳午未申" else "夜"
    guiren_zhi = _GUIREN[day_gan][0 if day_or_night == "昼" else 1]
    shun = guiren_zhi in _SHUN_ZHI
    if shun:
        gs_step = (_ZHIDX[difen_zhi] - _ZHIDX[guiren_zhi]) % 12
    else:
        gs_step = (_ZHIDX[guiren_zhi] - _ZHIDX[difen_zhi]) % 12
    guishen_name, guishen_wx, guishen_yy, guishen_jx, guishen_shi = _GUISHEN[gs_step]

    # —— 人元：五子元遁，从子顺数到地分 ——
    dun = _DUNSHOU[day_gan]
    renyuan_gan = _GAN[(_GANDX[dun] + _ZHIDX[difen_zhi]) % 10]
    renyuan_wx = _GAN_WX[renyuan_gan]

    difen_wx = _ZHI_WX[difen_zhi]
    difen_yy = _zhi_yin_yang(difen_zhi)
    renyuan_yy = _gan_yin_yang(renyuan_gan)

    four = {
        "人元": {"符号": renyuan_gan, "五行": renyuan_wx, "阴阳": renyuan_yy, "名": renyuan_gan},
        "贵神": {"符号": guishen_name, "五行": guishen_wx, "阴阳": guishen_yy,
                 "名": guishen_name, "吉凶": guishen_jx, "主事": guishen_shi},
        "将神": {"符号": jiang_name, "五行": jiang_wx, "阴阳": jiang_yy,
                 "名": f"{jiang_name}（{jiang_zhi}）"},
        "地分": {"符号": difen_zhi, "五行": difen_wx, "阴阳": difen_yy, "名": difen_zhi},
    }

    # —— 五动爻（干克方/神克干/神克将/将克神/方克干）——
    wudong = []
    if _KE.get(renyuan_wx) == difen_wx:
        wudong.append(("妻动", "干克方", "占主妻妾事；有官求财不利防损折；访人不悦；外来索取；物翻正旁有缺"))
    if _KE.get(guishen_wx) == renyuan_wx:
        wudong.append(("官动", "神克干", "利求官、逢驿马迁官；常人有公府事；问病在喉咽"))
    if _KE.get(guishen_wx) == jiang_wx:
        wudong.append(("贼动", "神克将", "内贼生、勾连诈；损财卑幼病；谋望无成；奸私暗昧"))
    if _KE.get(jiang_wx) == guishen_wx:
        wudong.append(("财动", "将克神", "利求财；占官不谐；人出外；妻妾身灾；病难瘥"))
    if _KE.get(difen_wx) == renyuan_wx:
        wudong.append(("鬼动", "方克干", "忧灾怪；官亨人出外；争讼带他人；口舌喧争；家宅未安泰"))

    # —— 三动（生/比和，不入正动）——
    sandong = []
    if _SHENG.get(difen_wx) == renyuan_wx:
        sandong.append(("父母动", "方生干", "为印绶，小干尊，大吉"))
    if _SHENG.get(renyuan_wx) == difen_wx:
        sandong.append(("子孙动", "干生方", "主子孙之事，小吉"))
    if renyuan_wx == difen_wx:
        sandong.append(("兄弟动", "干方同", "事在比肩朋友，小凶"))

    # —— 干/神/将/方 生克断语（16 条，命中项）——
    shengke = []
    if _KE.get(renyuan_wx) == guishen_wx:
        shengke.append("干克神：外来取索，防人谋害；常人损财，仕人失位，不宜求干")
    if _KE.get(renyuan_wx) == jiang_wx:
        shengke.append("干克将：求财不得，常人破财忧病；将阳主本身、将阴主妻室")
    if _SHENG.get(renyuan_wx) == guishen_wx:
        shengke.append("干生神：外生助我物帛，亲友相访，主富而有生意")
    if _SHENG.get(renyuan_wx) == jiang_wx:
        shengke.append("干生将：内外和顺，人将物来送，或有人干预于我")
    if _SHENG.get(guishen_wx) == difen_wx:
        shengke.append("神生方：宛转和合，贵人有怜小人之意，得贵人之力")
    if _KE.get(guishen_wx) == difen_wx:
        shengke.append("神克方：隔手求财难，事主晚成")
    if _SHENG.get(guishen_wx) == jiang_wx:
        shengke.append("神生将：所谋顺遂，内外和谐，行人将至")
    if _SHENG.get(guishen_wx) == renyuan_wx:
        shengke.append("神生干：仕人论官，常人有官府事；事求必得、寻必见")
    if _SHENG.get(jiang_wx) == renyuan_wx:
        shengke.append("将生干：将财与贵人，内外和畅，富贵之兆，百事有成")
    if _KE.get(jiang_wx) == renyuan_wx:
        shengke.append("将克干：喜事重重，求财必得、求名必遂、科举上榜、宜远行")
    if _SHENG.get(jiang_wx) == difen_wx:
        shengke.append("将生方（天覆）：家人内合，有人助我；财帛有喜、子孙兴荣")
    if _KE.get(jiang_wx) == difen_wx:
        shengke.append("将克方：斗讼官事，小口不安，六畜损失，家宅不宁")
    if _KE.get(difen_wx) == guishen_wx:
        shengke.append("方克神：损外财，隔位克，下犯上、民告官")
    if _KE.get(difen_wx) == jiang_wx:
        shengke.append("方克将：钱财散失，又主伤妻，人欲出外失财")
    if _SHENG.get(difen_wx) == guishen_wx:
        shengke.append("方生神：内外和合，人广财丰，求事不隔手")
    if _SHENG.get(difen_wx) == jiang_wx:
        shengke.append("方生将（地载）：家人和合，喜庆富贵，婚姻喜美，谋望有成")

    # —— 四位生克总断 ——
    all_ke = len(wudong) > 0
    zong = ("四位有克，内有刑克忧患缠：克人元主官事、克贵神伤尊长、克将神伤妻财、克地分伤小口"
            if all_ke else "四位无克（相生/比和），百事吉，从旺断")

    # —— 用爻（阴阳次第）——
    yang_cnt = sum(1 for k in four if four[k]["阴阳"] == "阳")
    yin_cnt = 4 - yang_cnt
    if yin_cnt == 3 and yang_cnt == 1:
        yongyao = "三阴一阳，以阳为用，事在男子"
    elif yang_cnt == 3 and yin_cnt == 1:
        yongyao = "三阳一阴，以阴为用，事在女子"
    elif yang_cnt == 2:
        yongyao = "二阴二阳，以将为用（随将阴阳辨之）"
    elif yang_cnt == 0:
        yongyao = "纯阴反阳，以将为用，方内之物（宜主不宜客）"
    else:
        yongyao = "纯阳反阴，以神为用，方外之物（宜客不宜主）"

    # —— 旺相休囚 ——
    season = _SEASON.get(month_zhi, "春")
    ws = _WANGXIU[season]
    wx_wangxiu = {wx: "旺" if ws["旺"] == wx else ("相" if ws["相"] == wx
                 else ("死" if ws["死"] == wx else ("囚" if ws["囚"] == wx else "休")))
                  for wx in ("木", "火", "土", "金", "水")}

    # —— 五行聚管（组合断）——
    wxs = [renyuan_wx, guishen_wx, jiang_wx, difen_wx]
    sign = "".join(f"{w}{wxs.count(w)}" for w in ("木", "火", "土", "金", "水") if wxs.count(w))
    julu = _JULU.get(sign)

    return {
        "时间": dt, "农历": lunar.toString(), "节气": jieqi,
        "日干支": day_gz, "时干支": hour_gz, "月将": f"{_JIANGSHEN[yuejiang_zhi][0]}（{yuejiang_zhi}）",
        "昼夜": day_or_night, "贵人支": guiren_zhi, "顺逆": "顺" if shun else "逆",
        "四位": four, "五动": wudong, "三动": sandong, "生克断": shengke,
        "总断": zong, "用爻": yongyao, "季节": season, "旺相休囚": wx_wangxiu,
        "聚管": julu,
        "_四个五行": wxs,
    }


def print_pan(r):
    """打印金口诀盘。"""
    four = r["四位"]
    rn, gs, js, df = four["人元"], four["贵神"], four["将神"], four["地分"]
    print(f"[金口诀] {r['农历']} {r['节气']}  {r['日干支']}日{r['时干支']}时")
    print(f"月将：{r['月将']}  {r['昼夜']}贵人（{r['贵人支']}，{r['顺逆']}行）")

    print("\n【四位】")
    print(f"  人元：{rn['符号']}（{rn['五行']}，{rn['阴阳']}）")
    print(f"  贵神：{gs['名']}（{gs['五行']}，{gs['阴阳']}，{gs['吉凶']}）——{gs['主事']} [出处：{SOURCE}·十二贵神所属]")
    print(f"  将神：{js['名']}（{js['五行']}，{js['阴阳']}）")
    print(f"  地分：{df['符号']}（{df['五行']}，{df['阴阳']}）")

    print("\n【五动爻】" + ("" if r["五动"] else "（无）"))
    for name, rel, text in r["五动"]:
        print(f"  · {name}（{rel}）：{text} [出处：{SOURCE}·五动爻诵]")

    if r["三动"]:
        print("\n【三动】")
        for name, rel, text in r["三动"]:
            print(f"  · {name}（{rel}）：{text} [出处：{SOURCE}·三动]")

    if r["生克断"]:
        print("\n【干神将方生克断】")
        for s in r["生克断"]:
            print(f"  · {s} [出处：{SOURCE}·干/神/将/方类]")

    print(f"\n【四位总断】{r['总断']} [出处：{SOURCE}·入式歌解]")
    print(f"【用爻】{r['用爻']} [出处：{SOURCE}·阴阳次第五用]")

    wx = r["旺相休囚"]
    print(f"【旺相休囚】{r['季节']}：木{wx['木']} 火{wx['火']} 土{wx['土']} 金{wx['金']} 水{wx['水']} [出处：{SOURCE}·五行休旺]")

    if r["聚管"]:
        jx, text = r["聚管"]
        print(f"【五行聚管】{jx}：{text} [出处：{SOURCE}·五行聚管]")


if __name__ == "__main__":
    import sys
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    import argparse
    ap = argparse.ArgumentParser(description="金口诀起盘")
    ap.add_argument("difen", nargs="?", default=None, help="地分（地支或方位，缺省取时支）")
    ap.add_argument("--time", "-t", default=None, help="占时 YYYY-MM-DD HH:MM")
    args = ap.parse_args()

    dt = None
    if args.time:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.datetime.strptime(args.time, fmt)
                break
            except ValueError:
                continue
    print_pan(cast(dt, args.difen))


def summary(r):
    """一眼摘要卡：日时干支/四位/用爻（借鉴八字/紫微升级的「一眼看懂」层）。"""
    sw = r.get("四位", {})
    sw_s = "  ".join(f"{k}{v.get('符号', '')}({v.get('五行', '')})" for k, v in sw.items())
    return "\n".join([
        f"【一眼摘要】金口诀 · {r.get('日干支', '')} {r.get('时干支', '')}",
        f"  四位：{sw_s}",
        f"  用爻：{r.get('用爻', '')}",
    ])


def pan_json(r):
    """盘面事实层 JSON（机读，schema=jinkoujue-panfact-v1）。"""
    from judge.rules import pan_meta
    return {"schema": "jinkoujue-panfact-v1", **r, **pan_meta("金口诀")}
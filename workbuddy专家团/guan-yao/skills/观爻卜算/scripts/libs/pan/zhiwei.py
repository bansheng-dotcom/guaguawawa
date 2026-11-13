# -*- coding: utf-8 -*-
"""紫微斗数排盘（自写，算法移植自 iztro 开源库，MIT）

宫位索引约定：寅宫下标为 0，顺时针 +1（寅0 卯1 辰2 巳3 午4 未5 申6 酉7 戌8 亥9 子10 丑11）。
地支索引（子=0）与宫位索引换算：宫位 = (地支-2) % 12。
"""
import datetime
from lifa import taiyangshi

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"

# 五虎遁（年干 -> 寅宫天干）
TIGER_RULE = {"甲": "丙", "乙": "戊", "丙": "庚", "丁": "壬", "戊": "甲",
              "己": "丙", "庚": "戊", "辛": "庚", "壬": "壬", "癸": "甲"}

# 十二宫名（自命宫起，逆时针）
PALACES = ["命宫", "兄弟宫", "夫妻宫", "子女宫", "财帛宫", "疾厄宫",
           "迁移宫", "交友宫", "官禄宫", "田宅宫", "福德宫", "父母宫"]

# 四化表（年干 -> [化禄, 化权, 化科, 化忌]）
SIHUA = {
    "甲": ["廉贞", "破军", "武曲", "太阳"],
    "乙": ["天机", "天梁", "紫微", "太阴"],
    "丙": ["天同", "天机", "文昌", "廉贞"],
    "丁": ["太阴", "天同", "天机", "巨门"],
    "戊": ["贪狼", "太阴", "右弼", "天机"],
    "己": ["武曲", "贪狼", "天梁", "文曲"],
    "庚": ["太阳", "武曲", "太阴", "天同"],
    "辛": ["巨门", "太阳", "文曲", "文昌"],
    "壬": ["天梁", "紫微", "左辅", "武曲"],
    "癸": ["破军", "巨门", "太阴", "贪狼"],
}

# 十四主星亮度（按地支 子0 丑1 ... 亥11）
# 对齐 py-iztro 庙旺表（原书落宫断语验证：紫微午宫入庙/寅申旺地/丑未入庙/辰戌得地 等，iztro 全对）。
BRIGHTNESS = {
    "紫微": ["平", "庙", "旺", "旺", "得", "旺", "庙", "庙", "旺", "旺", "得", "旺"],
    "天机": ["庙", "陷", "得", "旺", "利", "平", "庙", "陷", "得", "旺", "利", "平"],
    "太阳": ["陷", "不", "旺", "庙", "旺", "旺", "旺", "得", "得", "陷", "不", "陷"],
    "武曲": ["旺", "庙", "得", "利", "庙", "平", "旺", "庙", "得", "利", "庙", "平"],
    "天同": ["旺", "不", "利", "平", "平", "庙", "陷", "不", "旺", "平", "平", "庙"],
    "廉贞": ["平", "利", "庙", "平", "利", "陷", "平", "利", "庙", "平", "利", "陷"],
    "天府": ["庙", "庙", "庙", "得", "庙", "得", "旺", "庙", "得", "旺", "庙", "得"],
    "太阴": ["庙", "庙", "旺", "陷", "陷", "陷", "不", "不", "利", "不", "旺", "庙"],
    "贪狼": ["旺", "庙", "平", "利", "庙", "陷", "旺", "庙", "平", "利", "庙", "陷"],
    "巨门": ["旺", "不", "庙", "庙", "陷", "旺", "旺", "不", "庙", "庙", "陷", "旺"],
    "天相": ["庙", "庙", "庙", "陷", "得", "得", "庙", "得", "庙", "陷", "得", "得"],
    "天梁": ["庙", "旺", "庙", "庙", "庙", "陷", "庙", "旺", "陷", "得", "庙", "陷"],
    "七杀": ["旺", "庙", "庙", "旺", "庙", "平", "旺", "庙", "庙", "庙", "庙", "平"],
    "破军": ["庙", "旺", "得", "陷", "旺", "平", "庙", "旺", "得", "陷", "旺", "平"],
}

# 主星系（偏移量：紫微系逆，天府系顺）
ZIWEI_GROUP = [("紫微", 0), ("天机", 1), ("太阳", 3), ("武曲", 4), ("天同", 5), ("廉贞", 8)]
TIANFU_GROUP = [("天府", 0), ("太阴", 1), ("贪狼", 2), ("巨门", 3),
                ("天相", 4), ("天梁", 5), ("七杀", 6), ("破军", 10)]


def _zhi_palace(zhi_name):
    """地支名 -> 宫位索引（寅=0）"""
    return (ZHI.index(zhi_name) - 2) % 12


# 地支三合局（宫位索引）：申子辰水 / 寅午戌火 / 巳酉丑金 / 亥卯未木
_SANHE_GROUPS = [[2, 6, 10], [0, 4, 8], [3, 7, 11], [1, 5, 9]]


def sanfang_sizheng(idx):
    """三方四正（4 宫位索引，寅=0）：本宫 + 对宫 + 三合两宫。"""
    grp = next(g for g in _SANHE_GROUPS if idx in g)
    others = [x for x in grp if x != idx]
    return [idx, (idx + 6) % 12, others[0], others[1]]


def _gan_num(g):
    return GAN.index(g) // 2 + 1


def _zhi_num(z):
    return (ZHI.index(z) % 6) // 2 + 1


def wuxing_ju(gan, zhi):
    """命宫干支 -> (五行, 局数)"""
    n = _gan_num(gan) + _zhi_num(zhi)
    while n > 5:
        n -= 5
    wx = {1: "木", 2: "金", 3: "水", 4: "火", 5: "土"}[n]
    ju = {"木": 3, "金": 4, "水": 2, "火": 6, "土": 5}[wx]
    return wx, ju


def _ziwei_tianfu(ju, day):
    """紫微星、天府星宫位（寅=0）。口诀：六五四三二，酉午亥辰丑。"""
    offset = -1
    while True:
        offset += 1
        divisor = day + offset
        q = divisor // ju
        r = divisor % ju
        if r == 0:
            break
    q %= 12
    zw = q - 1
    zw += offset if offset % 2 == 0 else -offset
    zw %= 12
    tf = (12 - zw) % 12
    return zw, tf


def _lucun(gan):
    """禄存宫位（寅=0）：甲寅乙卯丙戊巳丁己午庚申辛酉壬亥癸子"""
    return {"甲": 0, "乙": 1, "丙": 3, "丁": 4, "戊": 3, "己": 4,
            "庚": 6, "辛": 7, "壬": 9, "癸": 10}[gan]


def _kuiyue(gan):
    """天魁、天钺宫位（寅=0）"""
    t = {
        "甲": ("丑", "未"), "戊": ("丑", "未"), "庚": ("丑", "未"),
        "乙": ("子", "申"), "己": ("子", "申"),
        "辛": ("午", "寅"),
        "丙": ("亥", "酉"), "丁": ("亥", "酉"),
        "壬": ("卯", "巳"), "癸": ("卯", "巳"),
    }
    kui, yue = t[gan]
    return _zhi_palace(kui), _zhi_palace(yue)


def _tianma(zhi):
    """天马宫位（寅=0）：寅午戌→申 申子辰→寅 巳酉丑→亥 亥卯未→巳"""
    t = {"寅": "申", "午": "申", "戌": "申", "申": "寅", "子": "寅", "辰": "寅",
         "巳": "亥", "酉": "亥", "丑": "亥", "亥": "巳", "卯": "巳", "未": "巳"}
    return _zhi_palace(t[zhi])


def _huoling(zhi, shi_idx):
    """火星、铃星宫位（寅=0）。shi_idx 为时支索引（子=0）。"""
    huo = ling = None
    if zhi in ("寅", "午", "戌"):
        huo, ling = _zhi_palace("丑"), _zhi_palace("卯")
    elif zhi in ("申", "子", "辰"):
        huo, ling = _zhi_palace("寅"), _zhi_palace("戌")
    elif zhi in ("巳", "酉", "丑"):
        huo, ling = _zhi_palace("卯"), _zhi_palace("戌")
    else:  # 亥卯未
        huo, ling = _zhi_palace("酉"), _zhi_palace("戌")
    return (huo + shi_idx) % 12, (ling + shi_idx) % 12


def _luanxi(zhi):
    """红鸾、天喜（寅=0）"""
    hongluan = (_zhi_palace("卯") - ZHI.index(zhi)) % 12
    return hongluan, (hongluan + 6) % 12


def cast(sy, sm, sd, hour, gender, lon=None, dst=False, fix_leap=True):
    """排盘。sy/sm/sd 为公历年月日，hour 为 24 小时制，gender 1 男 0 女。lon 东经度，dst 回拨夏令时。
    fix_leap 闰月口径（UND 流派分歧）：True=十五日分界（iztro fixLeap=true 默认），False=闰月作本月（iztro fixLeap=false）。"""
    from lunar_python import Solar
    if lon is not None or dst:
        _dt0, _notes = taiyangshi.correct(datetime.datetime(sy, sm, sd, hour, 0, 0), lon, dst)
        if _notes:
            print(f"[时间校正] {'；'.join(_notes)}")
        sy, sm, sd, hour = _dt0.year, _dt0.month, _dt0.day, _dt0.hour
    solar = Solar.fromYmdHms(sy, sm, sd, hour, 0, 0)
    lunar = solar.getLunar()
    lmonth = lunar.getMonth()
    lday = lunar.getDay()
    # 年干/年支以「立春」为界（对齐 iztro，字段级 parity）；「正月初一」为另一流派口径。
    year_gan = lunar.getYearGanByLiChun()
    year_zhi = lunar.getYearZhiByLiChun()
    # 闰月（lunar_python 对闰月 getMonth() 返回负数，如闰七月=-7）：流派分歧 UND。
    # fix_leap=True（默认，对齐 iztro fixLeap=true）：十五日（含）前作本月，十六日起作下月；
    # fix_leap=False（对齐 iztro fixLeap=false）：闰月一律作本月。
    if lmonth < 0:
        lmonth = -lmonth + (1 if (fix_leap and lday > 15) else 0)

    # 时辰
    shi_idx = (hour + 1) // 2 % 12  # 子=0

    # 命宫、身宫（宫位索引 寅=0）
    month_index = lmonth - 1
    soul = (month_index - shi_idx) % 12
    body = (month_index + shi_idx) % 12

    # 命宫干支
    soul_zhi = ZHI[(soul + 2) % 12]
    soul_gan = GAN[(GAN.index(TIGER_RULE[year_gan]) + soul) % 10]

    # 生年旬空（空亡）：生年干支所在旬空亡的两地支（甲子旬空戌亥等）
    xunshou = (ZHI.index(year_zhi) - GAN.index(year_gan)) % 12
    xunkong = [ZHI[(xunshou - 1) % 12], ZHI[(xunshou - 2) % 12]]

    # 五行局
    wx, ju = wuxing_ju(soul_gan, soul_zhi)

    # 紫微、天府
    zw, tf = _ziwei_tianfu(ju, lday)

    # 十二宫天干（五虎遁顺排）
    palace_gan = [GAN[(GAN.index(TIGER_RULE[year_gan]) + i) % 10] for i in range(12)]

    # 宫位 -> 宫名（命宫起逆时针，地支倒序：命宫→兄弟→夫妻→…→父母）
    # 宫 i（寅=0）对应十二宫 PALACES[(soul - i) % 12]
    def palace_name(i):
        return PALACES[(soul - i) % 12]

    # 安主星
    stars = {i: [] for i in range(12)}  # 宫位 -> [(星名, 亮度, 四化)]
    sihua = {v: k for k, v in zip(["禄", "权", "科", "忌"], SIHUA[year_gan])}

    def add_star(idx, name):
        brightness = BRIGHTNESS.get(name, [""] * 12)[(idx + 2) % 12]
        si = sihua.get(name, "")
        stars[idx].append((name, brightness, si))

    for name, off in ZIWEI_GROUP:
        add_star((zw - off) % 12, name)
    for name, off in TIANFU_GROUP:
        add_star((tf + off) % 12, name)

    # 安辅星
    fu = {i: [] for i in range(12)}
    fu_sihua = {}  # 宫位 -> {辅星名: 四化}（文昌文曲左右亦可为四化星）

    def add_fu(idx, name):
        fu[idx].append(name)
        if name in sihua:
            fu_sihua.setdefault(idx, {})[name] = sihua[name]

    # 禄存、擎羊、陀罗
    lu = _lucun(year_gan)
    add_fu(lu, "禄存"); add_fu((lu + 1) % 12, "擎羊"); add_fu((lu - 1) % 12, "陀罗")
    # 天马
    add_fu(_tianma(year_zhi), "天马")
    # 天魁天钺
    kui, yue = _kuiyue(year_gan)
    add_fu(kui, "天魁"); add_fu(yue, "天钺")
    # 左辅右弼（生月）
    add_fu((_zhi_palace("辰") + lmonth - 1) % 12, "左辅")
    add_fu((_zhi_palace("戌") - (lmonth - 1)) % 12, "右弼")
    # 文昌文曲（时辰）
    add_fu((_zhi_palace("戌") - shi_idx) % 12, "文昌")
    add_fu((_zhi_palace("辰") + shi_idx) % 12, "文曲")
    # 火星铃星
    huo, ling = _huoling(year_zhi, shi_idx)
    add_fu(huo, "火星"); add_fu(ling, "铃星")
    # 地空地劫（时辰）
    add_fu((_zhi_palace("亥") - shi_idx) % 12, "地空")
    add_fu((_zhi_palace("亥") + shi_idx) % 12, "地劫")
    # 红鸾天喜
    hl, tx = _luanxi(year_zhi)
    add_fu(hl, "红鸾"); add_fu(tx, "天喜")
    # 天刑（杂曜）：从酉宫起正月，顺数至生月（安天刑天姚星诀）
    add_fu((_zhi_palace("酉") + lmonth - 1) % 12, "天刑")

    # 大限（阳男阴女顺行，阴男阳女逆行；阴阳以年支定）
    yang_zhi = ZHI.index(year_zhi) % 2 == 0
    is_male = bool(gender)
    shunxing = (is_male and yang_zhi) or (not is_male and not yang_zhi)
    daxian = {}
    for i in range(12):
        idx = (soul + i) % 12 if shunxing else (soul - i) % 12
        start = ju + 10 * i
        daxian[idx] = (start, start + 9)

    # 小限（命宫起，男顺女逆，每岁一宫；12 年一轮，虚岁加 12 同宫）
    xiaoxian_dir = 1 if is_male else -1
    xiaoxian = [(xusui, palace_name((soul + (xusui - 1) * xiaoxian_dir) % 12))
                for xusui in range(1, 13)]

    _warn = taiyangshi.jieqi_warning(solar)
    if _warn:
        print(_warn)

    # 星曜定位：主星 + 辅星（四化星含辅星，如文昌科/文曲忌/右弼科/左辅科）
    def star_palace(name):
        for i in range(12):
            if any(n == name for n, b, s in stars[i]) or name in fu[i]:
                return i
        return None

    # 四化飞星：禄权科忌四化星各飞落哪个宫（地支 + 宫名）
    fly = []
    for si_name, star_name in zip(("禄", "权", "科", "忌"), SIHUA[year_gan]):
        idx = star_palace(star_name)
        if idx is not None:
            fly.append({"四化": si_name, "星": star_name,
                        "宫": palace_name(idx), "支": ZHI[(idx + 2) % 12]})

    # 宫干四化（飞星派/北派）：十二宫各自天干起四化，飞入对应星曜所在宫。
    # 后世流派，《全书》以生年四化为主，故本层只作盘面事实，断法标 [规则推演]。
    gong_gan_sihua = []
    for i in range(12):
        g = palace_gan[i]
        for si_name, star_name in zip(("禄", "权", "科", "忌"), SIHUA[g]):
            j = star_palace(star_name)
            if j is not None:
                gong_gan_sihua.append({"宫": palace_name(i), "宫干": g,
                                       "四化": si_name, "星": star_name,
                                       "飞入": palace_name(j), "支": ZHI[(j + 2) % 12]})

    from judge.rules import pan_meta
    return {
        **pan_meta("紫微"),
        "四柱": f"{year_gan}{year_zhi}  {lunar.getMonthInGanZhi()}  {lunar.getDayInGanZhi()}  {lunar.getTimeInGanZhi()}",
        "年干": year_gan,
        "性别": "男" if gender else "女",
        "农历": lunar.toString(),
        "命宫": f"{soul_gan}{soul_zhi}",
        "空亡": xunkong,
        "身宫": f"{GAN[(GAN.index(TIGER_RULE[year_gan]) + body) % 10]}{ZHI[(body + 2) % 12]}",
        "五行局": f"{wx}{ju}局",
        "局数": ju,
        "紫微": ZHI[(zw + 2) % 12],
        "天府": ZHI[(tf + 2) % 12],
        "四化": f"禄[{SIHUA[year_gan][0]}] 权[{SIHUA[year_gan][1]}] 科[{SIHUA[year_gan][2]}] 忌[{SIHUA[year_gan][3]}]",
        "四化飞星": fly,
        "辅星四化": fu_sihua,
        "宫干四化": gong_gan_sihua,
        "命宫三方四正": [palace_name(i) for i in sanfang_sizheng(soul)],
        "小限": xiaoxian,
        "十二宫": [
            {
                "宫": palace_name(i),
                "干": palace_gan[i],
                "支": ZHI[(i + 2) % 12],
                "主星": stars[i],
                "辅星": fu[i],
                "大限": daxian.get(i),
                "空宫": not stars[i],
                "命": i == soul,
                "身": i == body,
            }
            for i in range(12)
        ],
    }


def print_pan(r):
    """打印命盘"""
    print(f"[紫微斗数] {r['农历']}  四柱: {r['四柱']}")
    print(f"命宫: {r['命宫']}  身宫: {r['身宫']}  五行局: {r['五行局']}  紫微在{r['紫微']}  天府在{r['天府']}")
    print(f"四化: {r['四化']}")
    if r.get("四化飞星"):
        fly = "  ".join(f"{f['四化']}入{f['宫']}({f['星']}{f['支']})" for f in r["四化飞星"])
        print(f"四化飞星: {fly}")
    if r.get("命宫三方四正"):
        print(f"命宫三方四正: {'、'.join(r['命宫三方四正'])}")
    if r.get("小限"):
        xs = "  ".join(f"{y}岁→{g}" for y, g in r["小限"])
        print(f"小限(命宫起,男顺女逆,12年一轮): {xs}")
    if r.get("宫干四化"):
        print("宫干四化(飞星派·后世流派,盘面事实;断法标[规则推演]):")
        by_palace = {}
        for f in r["宫干四化"]:
            by_palace.setdefault(f["宫"], []).append(f"{f['四化']}{f['星']}→{f['飞入']}")
        for p in r["十二宫"]:
            if p["宫"] in by_palace:
                print(f"  {p['宫']}({p['干']}): {'  '.join(by_palace[p['宫']])}")
    print()
    print(f"{'宫':<6}{'干支':<6}{'主星(亮度·四化)':<28}{'辅星':<30}{'大限'}")
    fu_sihua = r.get("辅星四化") or {}
    for i, p in enumerate(r["十二宫"]):
        gz = p["干"] + p["支"]
        main = " ".join(f"{n}({b}{s})" if s else f"{n}({b})" for n, b, s in p["主星"]) or "—"
        fsi = fu_sihua.get(i, {})
        fu = " ".join(f"{n}({fsi[n]})" if n in fsi else n for n in p["辅星"]) or "—"
        tag = "命" if p["命"] else ("身" if p["身"] else "")
        if p.get("空宫"):
            tag += "·空"
        dx = f"{p['大限'][0]}-{p['大限'][1]}" if p["大限"] else "—"
        print(f"{p['宫']:<6}{gz:<6}{main:<28}{fu:<30}{dx}  {tag}")


def summary(r):
    """一眼摘要卡：命宫/身宫/五行局/四化/三方四正（借鉴八字升级的「一眼看懂」层，不牺牲可复核）。"""
    mg = next((p for p in r["十二宫"] if p["命"]), None)
    sg = next((p for p in r["十二宫"] if p["身"]), None)

    def _stars(p):
        if not p or not p["主星"]:
            return "空宫"
        return " ".join(f"{n}({b}{s})" if s else f"{n}({b})" for n, b, s in p["主星"])

    mg_line = f"命宫 {mg['干']}{mg['支']}({_stars(mg)})" if mg else "命宫 —"
    sg_line = f"身宫 {sg['干']}{sg['支']}({_stars(sg)})" if sg else "身宫 —"
    return "\n".join([
        f"【一眼摘要】紫微斗数 · {r.get('四柱', '')}",
        f"  {mg_line} · {sg_line} · 五行局 {r.get('五行局', '')}",
        f"  四化：{r.get('四化', '')}",
        f"  三方四正：{'、'.join(r.get('命宫三方四正', []))}",
    ])


_DUIGONG = {"命宫": "迁移宫", "迁移宫": "命宫", "兄弟宫": "交友宫", "交友宫": "兄弟宫",
            "夫妻宫": "官禄宫", "官禄宫": "夫妻宫", "子女宫": "田宅宫", "田宅宫": "子女宫",
            "财帛宫": "福德宫", "福德宫": "财帛宫", "疾厄宫": "父母宫", "父母宫": "疾厄宫"}


def feixing_panorama(r):
    """飞星四化全景（借鉴 mingli-skills）：循环忌 + 忌冲命/身宫。"""
    ggs = r.get("宫干四化", [])
    ji_map = {}
    for f in ggs:
        if f.get("四化") == "忌":
            ji_map.setdefault(f["宫"], []).append(f["飞入"])
    xunhuan, zihua, checked = [], [], set()
    for a, bs in ji_map.items():
        for b in bs:
            if b == a:
                zihua.append(a)  # 自化忌（化忌飞入本宫）
            elif b in ji_map and a in ji_map[b] and (b, a) not in checked:
                xunhuan.append(f"{a}↔{b}")
                checked.add((a, b))
    chong = []
    ming_gong = next((p["宫"] for p in r.get("十二宫", []) if p.get("命")), "命宫")
    shen_gong = next((p["宫"] for p in r.get("十二宫", []) if p.get("身")), None)
    for a, bs in ji_map.items():
        for b in bs:
            if _DUIGONG.get(b) == ming_gong:
                chong.append(f"{a}忌冲命宫（飞{b}冲{_DUIGONG[b]}）")
            if shen_gong and _DUIGONG.get(b) == shen_gong:
                chong.append(f"{a}忌冲身宫（飞{b}冲{_DUIGONG[b]}）")
    return {"循环忌": xunhuan, "自化忌": zihua, "忌冲": chong, "忌入": ji_map}


def format_feixing(pan):
    """格式化飞星四化全景（循环忌/自化忌/忌冲）。"""
    lines = ["【飞星四化全景】宫干四化·循环忌/自化忌/忌冲（飞星派，断法标[规则推演]）"]
    if pan["循环忌"]:
        lines.append("  ⚠ 循环忌：" + "  ".join(pan["循环忌"]) + "（两宫互忌，情势纠缠）")
    else:
        lines.append("  · 无循环忌（宫干忌无互飞闭环）")
    if pan["自化忌"]:
        lines.append("  ⚠ 自化忌：" + "  ".join(pan["自化忌"]) + "（化忌飞入本宫，自耗自缚）")
    if pan["忌冲"]:
        lines.append("  ⚠ 忌冲：" + "  ".join(pan["忌冲"]))
    else:
        lines.append("  · 无忌冲命/身宫")
    return "\n".join(lines)
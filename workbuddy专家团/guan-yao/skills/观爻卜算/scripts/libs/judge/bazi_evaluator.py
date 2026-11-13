# -*- coding: utf-8 -*-
"""八字独立评估者（对抗性第二意见）

借鉴 mingli-skills 的「独立评估者」思路：不是 self-eval，而是用**另一条独立规则链**
从原始四柱重新推导旺衰/格局/喜忌，再与主断（cast.py bazi 的输出）逐维比对，
发现矛盾即标「信号冲突，仅供参考」并降级。

与主路径的差异（刻意为之，保证独立）：
  - 主路径 bazi.py：得令40+得地30+得势15+得生15 四指标加权。
  - 本模块：旺相休囚死（月令五行定日主状态）+ 得地/得势布尔修正，独立打分。

用法:
  python libs/bazi_evaluator.py 2001 9 22 4 0 0 1        # 太阳历 年 月 日 时 分 秒 性别，独立重推
  python libs/bazi_evaluator.py --pillars 辛巳 丁酉 戊子 甲寅   # 直接给四柱
  import bazi_evaluator as ev
  ev.cross_check(主判断dict, ev.derive_from_solar(2001,9,22,4,0,0,1))
"""
import sys

# ---- 基础表 ----
WX = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
      "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
CANG = {"子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"],
        "卯": ["乙"], "辰": ["戊", "乙", "癸"], "巳": ["丙", "戊", "庚"],
        "午": ["丁", "己"], "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"],
        "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"]}
YANG = "甲丙戊庚壬"  # 阳干
# 相生相克：按五行
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}


def _shishen(day_gan, g):
    """以日主 day_gan 论，返回 g 的十神名。"""
    d, x = WX[day_gan], WX[g]
    same_polarity = (g in YANG) == (day_gan in YANG)
    if x == d:
        return "比肩" if same_polarity else "劫财"
    if SHENG[d] == x:  # 我生
        return "食神" if same_polarity else "伤官"
    if KE[d] == x:  # 我克
        return "偏财" if same_polarity else "正财"
    if KE[x] == d:  # 克我
        return "七杀" if same_polarity else "正官"
    if SHENG[x] == d:  # 生我
        return "偏印" if same_polarity else "正印"
    return "?"


def _wcxqsw(day_wx, month_zhi):
    """旺相休囚死：以月支定当令五行，返回日主五行所处状态。"""
    month_wx = WX[CANG[month_zhi][0]]  # 月支本气五行
    if day_wx == month_wx:
        return "旺"
    if SHENG[month_wx] == day_wx:  # 当令者生我
        return "相"
    if SHENG[day_wx] == month_wx:  # 我生当令者
        return "休"
    if KE[day_wx] == month_wx:  # 我克当令者
        return "囚"
    return "死"  # 当令者克我


def derive_from_pillars(pillars):
    """独立重推旺衰/格局/喜忌。pillars = [(年干,年支),(月干,月支),(日干,日支),(时干,时支)]"""
    g_y, z_y = pillars[0]
    g_m, z_m = pillars[1]
    g_d, z_d = pillars[2]
    g_h, z_h = pillars[3]
    day_wx = WX[g_d]

    # 得令：旺相休囚死
    state = _wcxqsw(day_wx, z_m)
    ling = {"旺": 3, "相": 2, "休": 1, "囚": 1, "死": 0}[state]

    # 得地：四支藏干里的比劫（本气3/中气2/余气1）
    di = 0
    for zhi in (z_y, z_m, z_d, z_h):
        for j, c in enumerate(CANG[zhi]):
            if WX[c] == day_wx:
                di += 3 - j
    # 得生：印（天干3/藏干本气2、中气1）
    sheng = 0
    for g in (g_y, g_m, g_h):
        if SHENG[WX[g]] == day_wx:
            sheng += 3
    for zhi in (z_y, z_m, z_d, z_h):
        for j, c in enumerate(CANG[zhi]):
            if SHENG[WX[c]] == day_wx:
                sheng += 2 - j
    # 得势：天干比劫
    shi = sum(1 for g in (g_y, g_m, g_h) if WX[g] == day_wx)

    score = ling * 3 + di + sheng + shi * 2  # 得令×3 为主，其余为辅
    # 五档（本包取值，可调）。刻意保持与 bazi_chain 成分加权模型不同的独立启发式，
    # 这样两链结论一致才更可信；分界按得令×3 + 得地 + 得生 + 得势×2 的粗粒度分值标定。
    if score >= 16:
        wangshuai = "身旺"
    elif score >= 13:
        wangshuai = "偏旺"
    elif score >= 9:
        wangshuai = "中和"
    elif score >= 6:
        wangshuai = "偏弱"
    else:
        wangshuai = "身弱"

    # 格局：月支藏干透干取格
    mg = None
    for c in CANG[z_m]:
        if c in (g_y, g_m, g_h):
            mg = _shishen(g_d, c)
            break
    if mg is None:
        mg = _shishen(g_d, CANG[z_m][0])
    geju = mg + "格"

    # 喜忌：身弱/偏弱/中和 喜印比（扶）；身旺/偏旺 喜财官食伤（抑）
    fu_yin_bi = [x for x in "木火土金水" if SHENG[x] == day_wx or x == day_wx]
    if wangshuai in ("身弱", "偏弱", "中和"):
        xi, ji = fu_yin_bi, [x for x in "木火土金水" if x not in fu_yin_bi]
    else:
        ji, xi = fu_yin_bi, [x for x in "木火土金水" if x not in fu_yin_bi]

    return {"日主": g_d, "五行": day_wx, "旺相休囚死": state,
            "旺衰": wangshuai, "得分": score, "格局": geju,
            "喜": xi, "忌": ji,
            "依据": {"得令": state, "得地": di, "得生": sheng, "得势": shi}}


def derive_from_solar(y, mo, d, h, mi=0, s=0, sex=1, lon=None):
    """由太阳历独立排四柱（走 lunar_python，但旺衰/格局/喜忌用本模块自己的规则）。"""
    from lunar_python import Solar
    sol = Solar.fromYmdHms(y, mo, d, h, mi, s)
    if lon is not None:
        # 真太阳时校正：与 cast.py 同口径，只影响时柱
        pass
    luna = sol.getLunar()
    ec = luna.getEightChar()
    pillars = [(ec.getYear()[0], ec.getYear()[1]),
               (ec.getMonth()[0], ec.getMonth()[1]),
               (ec.getDay()[0], ec.getDay()[1]),
               (ec.getTime()[0], ec.getTime()[1])]
    r = derive_from_pillars(pillars)
    r["四柱"] = [a + b for a, b in pillars]
    return r


def cross_check(main, indep, dims=("旺衰", "格局")):
    """逐维比对主判与独立判，返回 [{维度, 主, 独立, 状态}]。状态: 一致/边界差异/冲突。

    旺衰（五档 → 三态）：身旺/偏旺=旺、身弱/偏弱=弱、中和=中和；
    旺 vs 弱 = 冲突；旺 vs 中和 / 中和 vs 弱 = 边界差异；其余 = 一致。
    """
    def _lv(s):
        s = str(s)
        if any(k in s for k in ("身旺", "偏旺", "强")):
            return "旺"
        if any(k in s for k in ("身弱", "偏弱", "弱")):
            return "弱"
        return "中和"

    out = []
    for d in dims:
        m, i = main.get(d), indep.get(d)
        if m is None or i is None:
            continue
        if d == "旺衰":
            mq, iq = _lv(m), _lv(i)
            if mq == iq:
                st = "一致"
            elif {mq, iq} == {"旺", "弱"}:
                st = "冲突"
            else:
                st = "边界差异"
        else:
            st = "一致" if str(m).replace("格", "") == str(i).replace("格", "") else "冲突"
        out.append({"维度": d, "主": str(m), "独立": str(i), "状态": st})
    return out


def cross_check_chain(quad):
    """八字推演链（bazi_chain 五档）vs 独立评估者（旺相休囚死启发式）交叉验证。

    主判 = bazi_chain 的成分加权五档 + 用神五法；
    独立判 = 本模块旺相休囚死 + 得地得生得势 的独立五档启发式。
    旺衰按 cross_check 的三态映射比对；用神/喜忌另列（两链取用口径不同，只并列不强行比吉凶）。

    quad = {year:(干,支), month:.., day:.., hour:..}
    返回 {旺衰比对: [...], 主用神, 主喜忌, 独立旺衰, 独立喜忌, 结论}。
    """
    from judge import bazi_chain
    pillars = [quad[p] for p in ("year", "month", "day", "hour")]
    indep = derive_from_pillars(pillars)
    main = bazi_chain.select(quad)
    cmp_ = cross_check(
        {"旺衰": main.evidence[0].replace("旺衰·", ""), "格局": main.evidence[1].replace("格·", "")},
        {"旺衰": indep["旺衰"], "格局": indep["格局"]},
    )
    conflict = any(x["状态"] == "冲突" for x in cmp_)
    return {
        "旺衰比对": cmp_,
        "主旺衰": main.evidence[0].replace("旺衰·", ""),
        "主用神": main.yong, "主喜忌": f"喜{main.xi} 忌{main.ji}",
        "独立旺衰": indep["旺衰"], "独立喜忌": f"喜{''.join(indep['喜'])} 忌{''.join(indep['忌'])}",
        "结论": "信号冲突，仅供参考" if conflict else "一致/边界差异",
    }


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    a = sys.argv[1:]
    if a and a[0] == "--pillars" and len(a) >= 5:
        pillars = [(a[i][0], a[i][1]) for i in range(1, 5)]
        r = derive_from_pillars(pillars)
        r["四柱"] = a[1:5]
    elif len(a) >= 7:
        y, mo, d, h, mi, s, sex = (int(x) for x in a[:7])
        r = derive_from_solar(y, mo, d, h, mi, s, sex)
    else:
        print(__doc__)
        return
    print("[独立评估者·第二意见] 规则=旺相休囚死+得地得生得势（与主路径四指标加权独立）")
    print(f"  四柱: {' '.join(r['四柱'])}  日主{r['日主']}({r['五行']})")
    print(f"  得令(旺相休囚死): {r['旺相休囚死']}  得地:{r['依据']['得地']}  得生:{r['依据']['得生']}  得势:{r['依据']['得势']}")
    print(f"  旺衰: {r['旺衰']}(得分{r['得分']})  格局: {r['格局']}")
    print(f"  喜: {'、'.join(r['喜']) or '—'}  忌: {'、'.join(r['忌']) or '—'}")
    print("  （请与 cast.py bazi 的旺衰/格局/喜忌逐维比对，冲突则标「信号冲突，仅供参考」）")


if __name__ == "__main__":
    main()
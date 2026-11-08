# -*- coding: utf-8 -*-
"""梅花易数：时间起卦 / 数字起卦"""
import datetime
from gua import GUA, YAO, WX, gua_num, hexagram_name, tri_to_num, wx_rel, cuo, zong, fu, name_of

DIZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 八卦取象（外应断卦用，[规则推演] 传统取象，速查见 references/八卦取象速查.md）
_GUA_XIANG = {
    "乾": {"颜色": "金色/白色", "物品": "金属、圆形、贵重", "人物": "父亲/长者/领导", "方位": "西北"},
    "兑": {"颜色": "白色/银色", "物品": "金属、口器、破损", "人物": "少女/口才", "方位": "西"},
    "离": {"颜色": "红色/紫色", "物品": "火、照明、文书", "人物": "中女/文人", "方位": "南"},
    "震": {"颜色": "绿色/青色", "物品": "木、雷、响声", "人物": "长男/动者", "方位": "东"},
    "巽": {"颜色": "绿色/青色", "物品": "木、风、绳索", "人物": "长女/文静", "方位": "东南"},
    "坎": {"颜色": "黑色/蓝色", "物品": "水、液体、流动", "人物": "中男/智谋", "方位": "北"},
    "艮": {"颜色": "黄色/棕色", "物品": "土、山、静止", "人物": "少男/稳重", "方位": "东北"},
    "坤": {"颜色": "黄色/米色", "物品": "土、布、柔顺", "人物": "母亲/众人", "方位": "西南"},
}


def _month_zhi(dt=None):
    """dt → 月支（正月=寅月，农历月近似）。缺省用当前时间。"""
    now = dt or datetime.datetime.now()
    try:
        from lunar_python import Solar
        m = abs(Solar.fromYmd(now.year, now.month, now.day).getLunar().getMonth())
    except Exception:
        m = now.month
        print("[梅花易数] 警告：农历换算失败，退用公历月，卦气旺衰可能不准")
    return DIZHI[(m + 1) % 12]


def _print_enhance(r, month_zhi=""):
    """卦气旺衰 + 断卦分析 + 吉凶评分 + 应期 + 外应（[规则推演] 只给方向）。"""
    from judge.rules import meihua as _mh, meihua_wangshuai as _mhw, meihua_probability as _mhp
    ti_wx, yong_wx = r["体五行"], r["用五行"]
    mh = _mh(ti_wx, yong_wx)
    wangshuai = _mhw(ti_wx, month_zhi) if month_zhi else None
    prob = _mhp(ti_wx, yong_wx)
    print()
    if wangshuai:
        print(f"【卦气旺衰】体卦{ti_wx} 月令{month_zhi} → {wangshuai['judgment']}：{wangshuai['basis']}")
    print(f"【断卦分析】{mh['judgment']}（R-MH-01）— {mh['basis']}")
    print(f"    成事/得物概率：{prob['judgment']}（{prob['basis']}）")
    score = {"吉": 82, "中": 55, "凶": 30}.get(mh["judgment"], 50)
    if wangshuai:
        score += {"旺": 10, "相": 6, "休": -4, "衰": -14}.get(wangshuai["judgment"], 0)
    score = max(10, min(95, score))
    jx = "吉" if score >= 70 else ("中" if score >= 45 else "凶")
    print(f"【吉凶评分】{score}/100  →  {jx}")
    gs = r["上卦数"] + r["下卦数"]
    print(f"【应期】卦数应期约 {gs} 日/周/月；动爻第{r['动爻']}爻（[规则推演] 粗推，仅供参考）")
    xiang = _GUA_XIANG.get(r["体卦"], {})
    if xiang:
        print(f"【外应取象】体卦{r['体卦']}（{r['体五行']}）→ 🧭{xiang.get('方位', '')} "
              f"🎨{xiang.get('颜色', '')} 🎁{xiang.get('物品', '')} 👤{xiang.get('人物', '')}")


def cast_time(dt=None):
    now = dt or datetime.datetime.now()
    try:
        from lunar_python import Solar
        l = Solar.fromYmd(now.year, now.month, now.day).getLunar()
        m, d = abs(l.getMonth()), l.getDay()
    except Exception:
        m, d = now.month, now.day
        print("[梅花易数] 警告：农历换算失败，退用公历月日，结果可能不准")
    shi = (now.hour + 1) // 2 % 12
    n_year = (now.year - 4) % 12 + 1       # 年支数(子1...亥12)
    n_shi = shi + 1
    return _calc(n_year, m, d, n_shi,
                 note=f"公历{now:%Y-%m-%d %H:%M} 农历{now.year}年{m}月{d}日 {DIZHI[shi]}时",
                 month_zhi=DIZHI[(m + 1) % 12])


def cast_num(nums):
    nums = [int(x) for x in nums]
    if len(nums) == 1:
        return _calc(nums[0], 0, 0, 0, note=f"单数起卦: {nums[0]}")
    if len(nums) == 2:
        a, b = nums
        return _build(gua_num(a), gua_num(b), gua_num(a + b) % 6 or 6,
                      note=f"数字起卦: {a},{b}")
    a, b, c = nums
    return _build(gua_num(a), gua_num(b), c % 6 or 6,
                  note=f"数字起卦: {a},{b},{c}")


def _calc(n_year, m, d, n_shi, note="", month_zhi=None):
    shang = gua_num(n_year + m + d)
    xia = gua_num(n_year + m + d + n_shi)
    dong = (n_year + m + d + n_shi) % 6 or 6
    return _build(shang, xia, dong, note=note, month_zhi=month_zhi)


# ---------------------------------------------------------------------------
# 后天起卦（触机）：物数占 / 声音占 / 字占 / 端法（物+方位）
# 据《梅花易数》卷一「物数占例 / 声音占例 / 字占 / 物卦起例(端法)」
# 时数：子=1 ... 亥=12（与年月日时起例同）
# ---------------------------------------------------------------------------
def _shichen(dt=None):
    now = dt or datetime.datetime.now()
    shi = (now.hour + 1) // 2 % 12
    return shi + 1


def _to_gua(x):
    """数字/卦名/方位名/五行名 -> 卦数 1-8（先天数：乾1兑2离3震4巽5坎6艮7坤8）"""
    if isinstance(x, int):
        return gua_num(x)
    s = str(x).strip()
    if s.isdigit():
        return gua_num(int(s))
    m = {"乾": 1, "兑": 2, "离": 3, "震": 4, "巽": 5, "坎": 6, "艮": 7, "坤": 8}
    if s in m:
        return m[s]
    fw = {"南": 3, "北": 6, "东": 4, "西": 2, "东南": 5, "西北": 1, "西南": 8, "东北": 7}
    if s in fw:
        return fw[s]
    wx = {"火": 3, "水": 6, "金": 1, "木": 4, "土": 8}
    if s in wx:
        return wx[s]
    raise ValueError(f"无法识别卦/方位/物象: {x}")


def cast_guanwu(n, dt=None):
    """物数占（后天）：见可数之物，物数为上卦，物数+时数为下卦，总除六取动爻"""
    n = int(n)
    shi = _shichen(dt)
    return _build(gua_num(n), gua_num(n + shi), (n + shi) % 6 or 6,
                  note=f"物数占(后天): 物数{n} 时数{shi}", month_zhi=_month_zhi(dt))


def cast_shengyin(n, dt=None):
    """声音占（后天）：闻声几数，声数为上卦，声数+时数为下卦，总除六取动爻"""
    n = int(n)
    shi = _shichen(dt)
    return _build(gua_num(n), gua_num(n + shi), (n + shi) % 6 or 6,
                  note=f"声音占(后天): 声数{n} 时数{shi}", month_zhi=_month_zhi(dt))


def cast_zishu(n, dt=None):
    """字占（后天）：字数停匀分半，不匀则少一字为上卦、多一字为下卦，合二卦总数取爻"""
    n = int(n)
    shang = gua_num(n // 2) or 8          # 上卦取少的一边
    xia = gua_num(n - n // 2)             # 下卦取多的一边
    return _build(shang, xia, n % 6 or 6,
                  note=f"字占(后天): {n}字 上{n // 2} 下{n - n // 2}", month_zhi=_month_zhi(dt))


def cast_duanfa(wu, fang, dt=None):
    """端法后天起卦：以物为上卦、方位为下卦，合物卦数+方卦数+时数取动爻"""
    wu_n = _to_gua(wu)
    fang_n = _to_gua(fang)
    shi = _shichen(dt)
    return _build(wu_n, fang_n, (wu_n + fang_n + shi) % 6 or 6,
                  note=f"端法后天起卦: 物={GUA[wu_n]}({wu}) 方位={GUA[fang_n]}({fang}) 时数{shi}",
                  month_zhi=_month_zhi(dt))


def _build(shang, xia, dong, note="", month_zhi=None):
    ben = hexagram_name(shang, xia)
    liu = YAO[xia] + YAO[shang]                  # 本卦六爻(自下而上)
    hu_xia = tri_to_num(liu[1:4])                # 下互=二三四
    hu_shang = tri_to_num(liu[2:5])              # 上互=三四五
    hu = hexagram_name(hu_shang, hu_xia)
    liu2 = list(liu); liu2[dong - 1] ^= 1        # 动爻变
    bian_xia = tri_to_num(tuple(liu2[:3]))
    bian_shang = tri_to_num(tuple(liu2[3:]))
    bian = hexagram_name(bian_shang, bian_xia)
    # 错综复三观（补齐射覆取象不全，会合参证见 judge/meihua_cuozongfu.py）
    cuo_n = name_of(cuo(liu))                     # 错卦=六爻全变
    zong_n = name_of(zong(liu))                   # 综卦=上下颠倒
    fu_shang_n = name_of(fu(liu, "上"))           # 复上=上体翻对体（外伏）
    fu_xia_n = name_of(fu(liu, "下"))             # 复下=下体翻对体（内伏）
    yong, ti = (xia, shang) if dong <= 3 else (shang, xia)  # 动为用、静为体
    sheng = wx_rel(WX[yong], WX[ti])
    if month_zhi is None:
        month_zhi = _month_zhi()
    print(f"[梅花易数] {note}")
    print(f"本卦: {ben}（{GUA[shang]}上 {GUA[xia]}下）")
    print(f"动爻: 第{dong}爻")
    print(f"互卦: {hu}")
    print(f"变卦: {bian}")
    print(f"错综复: 错={cuo_n} 综={zong_n} 复上={fu_shang_n} 复下={fu_xia_n}")
    print(f"体用: 体={GUA[ti]}({WX[ti]}) 用={GUA[yong]}({WX[yong]})  -> {sheng}")
    r = {
        "note": note,
        "本卦": ben, "互卦": hu, "变卦": bian, "动爻": dong,
        "错卦": cuo_n, "综卦": zong_n, "复卦上": fu_shang_n, "复卦下": fu_xia_n,
        "上卦": GUA[shang], "下卦": GUA[xia], "上卦数": shang, "下卦数": xia,
        "体卦": GUA[ti], "体五行": WX[ti],
        "用卦": GUA[yong], "用五行": WX[yong],
        "体用关系": sheng, "月令": month_zhi,
    }
    _print_enhance(r, month_zhi)
    return r


def _analysis(r):
    """体用生克 + 卦气旺衰 + 概率 + 评分（供 summary/pan_json 复用）。"""
    from judge.rules import meihua as _mh, meihua_wangshuai as _mhw, meihua_probability as _mhp
    ti_wx, yong_wx = r["体五行"], r["用五行"]
    mh = _mh(ti_wx, yong_wx)
    wangshuai = _mhw(ti_wx, r.get("月令")) if r.get("月令") else None
    prob = _mhp(ti_wx, yong_wx)
    score = {"吉": 82, "中": 55, "凶": 30}.get(mh["judgment"], 50)
    if wangshuai:
        score += {"旺": 10, "相": 6, "休": -4, "衰": -14}.get(wangshuai["judgment"], 0)
    score = max(10, min(95, score))
    jx = "吉" if score >= 70 else ("中" if score >= 45 else "凶")
    return {"体用": mh, "卦气": wangshuai, "概率": prob, "评分": score, "吉凶": jx}


def summary(r):
    """一眼摘要卡：本卦变卦/体用生克/卦气/评分吉凶（借鉴八字/紫微升级的「一眼看懂」层）。"""
    a = _analysis(r)
    qixi = a["卦气"]["judgment"] if a["卦气"] else "—"
    return "\n".join([
        f"【一眼摘要】梅花易数 · {r['本卦']} → {r['变卦']}  动爻第{r['动爻']}",
        f"  互卦 {r['互卦']} · 体={r['体卦']}({r['体五行']}) 用={r['用卦']}({r['用五行']}) · {r['体用关系']}",
        f"  评分：{a['评分']}/100({a['吉凶']}) · 卦气{qixi} · {a['概率']['judgment']}",
    ])


def pan_json(r):
    """盘面事实层 JSON（机读，schema=meihua-panfact-v1）。"""
    from judge.rules import pan_meta
    a = _analysis(r)
    return {"schema": "meihua-panfact-v1", **r, **pan_meta("梅花"),
            "分析": {"体用生克": a["体用"]["judgment"], "卦气旺衰": a["卦气"]["judgment"] if a["卦气"] else None,
                     "概率": a["概率"]["judgment"], "评分": a["评分"], "吉凶": a["吉凶"],
                     "应期": f"卦数{r['上卦数'] + r['下卦数']}日/周/月"}}
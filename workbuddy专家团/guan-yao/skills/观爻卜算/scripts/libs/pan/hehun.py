# -*- coding: utf-8 -*-
"""八字合婚（生肖·日主五行·夫妻宫·纳音 + 四柱全盘比对 + 用神喜忌互补）。

在原「生肖/日主/夫妻宫/纳音」四维基础上补：
- 双方四柱全盘比对（年/月/日/时 逐柱干支合冲刑害，时柱缺省降级）
- 用神喜忌互补（旺衰扶抑 → 喜忌五行 → 看对方日主是补还是冲）
返回结构化 dict（同时打印），便于后续喂 HTML/报告。

诚实边界：合婚得分为 [规则推演] 加权模型，只给方向，非精确吉凶。
"""
from lunar_python import Solar
import xingchong
from pan import bazi_liunian
_GAN = "甲乙丙丁戊己庚辛壬癸"
_ZHI = "子丑寅卯辰巳午未申酉戌亥"
_SHENGXIAO = "鼠牛虎兔龙蛇马羊猴鸡狗猪"

_HE = {frozenset("子丑"), frozenset("寅亥"), frozenset("卯戌"), frozenset("辰酉"), frozenset("巳申"), frozenset("午未")}
_CHONG = {frozenset("子午"), frozenset("丑未"), frozenset("寅申"), frozenset("卯酉"), frozenset("辰戌"), frozenset("巳亥")}
_HAI = {frozenset("子未"), frozenset("丑午"), frozenset("寅巳"), frozenset("卯辰"), frozenset("申亥"), frozenset("酉戌")}
_XING = {frozenset("子卯"), frozenset("寅巳"), frozenset("巳申"), frozenset("申寅"), frozenset("丑戌"), frozenset("戌未"), frozenset("未丑")}
_SANHE = [set("申子辰"), set("寅午戌"), set("巳酉丑"), set("亥卯未")]

_WX = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}


def _shengxiao_rel(z1, z2):
    """生肖关系 -> (关系, 分)"""
    if z1 == z2:
        return "同肖", 0
    for s in _SANHE:
        if {z1, z2} <= s:
            return "三合", 3
    p = frozenset((z1, z2))
    if p in _HE:
        return "六合", 3
    if p in _CHONG:
        return "六冲", -3
    if p in _HAI:
        return "六害", -2
    if p in _XING:
        return "相刑", -2
    return "平", 0


def _wx_rel(w1, w2):
    """五行关系 -> (关系, 分)。w1 为男方日主五行。"""
    if w1 == w2:
        return "比和", 1
    if _SHENG[w1] == w2:
        return f"{w1}生{w2}(我生)", 1
    if _SHENG[w2] == w1:
        return f"{w2}生{w1}(生我)", 2
    if _KE[w1] == w2:
        return f"{w1}克{w2}(我克)", -1
    return f"{w2}克{w1}(克我)", -2


def _nayin_rel(ny1, ny2):
    """纳音五行关系（取末字判粗略五行）。"""
    w1 = ny1[-1] if ny1 else "土"
    w2 = ny2[-1] if ny2 else "土"
    if w1 == w2:
        return "比和", 0
    if w1 in _SHENG and _SHENG[w1] == w2:
        return "相生", 1
    if w2 in _SHENG and _SHENG[w2] == w1:
        return "相生", 1
    return "相克", -1


def cast(y1, m1, d1, y2, m2, d2, h1=None, h2=None):
    """合婚。y1/m1/d1/h1 男方，y2/m2/d2/h2 女方；时柱可选（缺省按午时 + 标注降级）。
    返回结构化 dict，同时打印。"""
    time_known = h1 is not None and h2 is not None
    hh1 = h1 if h1 is not None else 12
    hh2 = h2 if h2 is not None else 12
    b1 = Solar.fromYmdHms(y1, m1, d1, hh1, 0, 0).getLunar().getEightChar()
    b2 = Solar.fromYmdHms(y2, m2, d2, hh2, 0, 0).getLunar().getEightChar()

    p1 = {"年": b1.getYear(), "月": b1.getMonth(), "日": b1.getDay(), "时": b1.getTime()}
    p2 = {"年": b2.getYear(), "月": b2.getMonth(), "日": b2.getDay(), "时": b2.getTime()}
    z1, z2 = b1.getYearZhi(), b2.getYearZhi()
    g1, g2 = b1.getDayGan(), b2.getDayGan()
    dz1, dz2 = b1.getDayZhi(), b2.getDayZhi()
    w1, w2 = _WX[g1], _WX[g2]
    ny1, ny2 = b1.getYearNaYin(), b2.getYearNaYin()

    # —— 四维（保留）——
    sx_rel, sx_score = _shengxiao_rel(z1, z2)
    wx_rel, wx_score = _wx_rel(w1, w2)
    gz_rel, gz_score = _shengxiao_rel(dz1, dz2)
    ny_rel, ny_score = _nayin_rel(ny1, ny2)

    # —— 四柱全盘比对（年/月/日/时；时柱缺省降级）——
    zhucol, zhucol_score = [], 0
    cols = ["年", "月", "日"] + (["时"] if time_known else [])
    for pos in cols:
        mg, mz = p1[pos][0], p1[pos][1]
        fg, fz = p2[pos][0], p2[pos][1]
        gr = xingchong.gan_relation(mg, fg)
        zr = xingchong.zhi_relation(mz, fz)
        s = 0
        if gr["关系"] == "五合":
            s += 2
        elif gr["关系"] == "相克":
            s -= 2
        for r in zr["关系列表"]:
            if r["关系"] == "六合":
                s += 3
            elif r["关系"] == "半三合":
                s += 2
            elif r["关系"] == "六冲":
                s -= 3
            elif r["关系"] in ("六害", "自刑", "无礼之刑"):
                s -= 2
            else:
                s -= 1
        zhucol_score += s
        desc = []
        if gr["关系"] != "平":
            desc.append(f"干{gr['关系']}")
        desc += [f"支{r['关系']}" for r in zr["关系列表"] if r["关系"] != "平"]
        zhucol.append({"柱": pos, "男": p1[pos], "女": p2[pos],
                       "关系": "、".join(desc) or "平和", "分": s})

    # —— 用神喜忌互补（旺衰量化得分 → 喜忌五行）——
    wscore1 = bazi_liunian.wangshuai_score(b1)
    wscore2 = bazi_liunian.wangshuai_score(b2)
    qr1, qr2 = wscore1["档次"], wscore2["档次"]
    xi1, ji1 = bazi_liunian.xi_ji_wx(qr1, w1)
    xi2, ji2 = bazi_liunian.xi_ji_wx(qr2, w2)
    hubu, hubu_notes = 0, []
    if w2 in xi1:
        hubu += 2
        hubu_notes.append(f"女方日主{w2}补男方所喜（+2）")
    if w1 in xi2:
        hubu += 2
        hubu_notes.append(f"男方日主{w1}补女方所喜（+2）")
    if w2 in ji1:
        hubu -= 2
        hubu_notes.append(f"女方日主{w2}为男方所忌（-2）")
    if w1 in ji2:
        hubu -= 2
        hubu_notes.append(f"男方日主{w1}为女方所忌（-2）")
    if not hubu_notes:
        hubu_notes.append("双方日主互不补亦不冲（0）")

    # —— 综合 ——
    total = sx_score + wx_score + gz_score + ny_score + zhucol_score + hubu
    if total >= 10:
        grade = "上婚(大吉)"
    elif total >= 6:
        grade = "中婚(吉)"
    elif total >= 1:
        grade = "下婚(平)"
    else:
        grade = "不宜(凶)"

    sx1 = _SHENGXIAO[_ZHI.index(z1)]
    sx2 = _SHENGXIAO[_ZHI.index(z2)]
    print("[八字合婚]")
    print(f"男方: {p1['年']} 日主{g1}({w1}) 身{qr1}({wscore1['得分']}分) 喜{''.join(sorted(xi1))} 忌{''.join(sorted(ji1))} 纳音{ny1} 生肖{sx1}({z1})")
    print(f"女方: {p2['年']} 日主{g2}({w2}) 身{qr2}({wscore2['得分']}分) 喜{''.join(sorted(xi2))} 忌{''.join(sorted(ji2))} 纳音{ny2} 生肖{sx2}({z2})")
    print(f"生肖: {sx_rel}({sx_score:+d})  日主五行: {wx_rel}({wx_score:+d})  "
          f"夫妻宫: {gz_rel}({gz_score:+d})  纳音: {ny_rel}({ny_score:+d})")
    print("四柱比对:")
    for c in zhucol:
        print(f"  {c['柱']}柱: 男{c['男']} vs 女{c['女']} → {c['关系']}（{c['分']:+d}）")
    if not time_known:
        print("  （时柱未知，按午时排，时柱比对已降级省略）")
    print(f"用神互补: {'；'.join(hubu_notes)}（{hubu:+d}）")
    print(f"综合: {total} 分 → {grade}")
    print("提示: 生肖六合/三合、日主相生、四柱多合、用神互补为吉；六冲/相刑/相克、四柱多冲、用神相冲宜留意。")
    return {
        "男方": {"四柱": p1, "日主": g1, "日主五行": w1, "身强弱": qr1,
                 "旺衰得分": wscore1["得分"], "喜": sorted(xi1), "忌": sorted(ji1),
                 "纳音": ny1, "生肖": sx1},
        "女方": {"四柱": p2, "日主": g2, "日主五行": w2, "身强弱": qr2,
                 "旺衰得分": wscore2["得分"], "喜": sorted(xi2), "忌": sorted(ji2),
                 "纳音": ny2, "生肖": sx2},
        "维度": {
            "生肖": {"关系": sx_rel, "分": sx_score},
            "日主五行": {"关系": wx_rel, "分": wx_score},
            "夫妻宫": {"关系": gz_rel, "分": gz_score},
            "纳音": {"关系": ny_rel, "分": ny_score},
            "四柱全盘": {"分": zhucol_score, "明细": zhucol},
            "用神互补": {"分": hubu, "说明": hubu_notes},
        },
        "总分": total, "等级": grade,
    }


if __name__ == "__main__":
    import sys
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    cast(1990, 5, 15, 1992, 8, 20)
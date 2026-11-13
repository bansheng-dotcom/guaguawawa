# -*- coding: utf-8 -*-
"""小六壬：月日时掌诀"""
import datetime

GONG = ["大安", "留连", "速喜", "赤口", "小吉", "空亡"]
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]


def cast(dt=None, y=None, m=None, d=None, h=None):
    now = dt or datetime.datetime.now()
    if y is None or m is None or d is None:
        try:
            from lunar_python import Solar
            l = Solar.fromYmd(now.year, now.month, now.day).getLunar()
            y, m, d = l.getYear(), abs(l.getMonth()), l.getDay()
        except Exception:
            y, m, d = now.year, now.month, now.day
            print("[小六壬] 警告：农历换算失败，退用公历月日，结果可能不准")
    if h is None:
        h = (now.hour + 1) // 2 % 12    # 时辰 0子...11亥
    pos = 0
    pos = (pos + (m - 1)) % 6
    pos = (pos + (d - 1)) % 6
    pos = (pos + h) % 6
    print(f"[小六壬] 农历{y}年{m}月{d}日 {DIZHI[h]}时")
    print(f"月->{GONG[(m - 1) % 6]}  日->{GONG[(m - 1 + d - 1) % 6]}  时->{GONG[pos]}")
    print(f"落宫: {GONG[pos]}")
    return GONG[pos]


_XLR_JX = {"大安": ("吉", "安稳顺遂，宜守宜静"), "留连": ("凶", "纠缠拖延，防口舌是非"),
           "速喜": ("吉", "快而喜，宜速行"), "赤口": ("凶", "口舌破财，防争斗"),
           "小吉": ("吉", "小有喜，宜周旋"), "空亡": ("凶", "落空，劳而无功")}


def summary(gong):
    """一眼摘要卡：落宫/吉凶（借鉴八字/紫微升级的「一眼看懂」层）。"""
    jx, duan = _XLR_JX.get(gong, ("？", ""))
    return "\n".join([f"【一眼摘要】小六壬 · 落宫：{gong}", f"  吉凶：{jx} · {duan}"])


def pan_json(gong):
    """盘面事实层 JSON（机读，schema=xiaoliuren-panfact-v1）。"""
    from judge.rules import pan_meta
    jx, duan = _XLR_JX.get(gong, ("？", ""))
    return {"schema": "xiaoliuren-panfact-v1", "落宫": gong, "吉凶": jx, "断": duan, **pan_meta("小六壬")}
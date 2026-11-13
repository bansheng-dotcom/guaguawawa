# -*- coding: utf-8 -*-
"""六爻纳甲（金钱卦）：铜钱摇卦 + 自动装卦（纳甲/世应/六亲/六神/旬空）"""
import datetime
import random
from gua import hexagram_name, tri_to_num
from pan import najia
NAMES = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]


def cast(dt=None, question="通用", seed=None):
    dt = dt or datetime.datetime.now()
    from lunar_python import Solar
    solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    lunar = solar.getLunar()
    day_gz = lunar.getDayInGanZhi()
    month_gz = lunar.getMonthInGanZhi()

    # STO 留痕（借鉴 mingyu seed/replay）：seed 缺省随机生成可重放，给定 seed 确定性复现
    if seed is None:
        seed = random.SystemRandom().randint(1, 2 ** 31)
    rng = random.Random(seed)
    lines = []
    print(f"[六爻·铜钱卦] 三枚铜钱摇六次(自下而上)，seed={seed}（重放: --seed {seed}）:")
    for nm in NAMES:
        backs = sum(rng.choice([0, 1]) for _ in range(3))  # 3 枚铜钱，1=背
        if backs == 3:
            r = ("阳(动)", 1)
        elif backs == 2:
            r = ("阴", 0)
        elif backs == 1:
            r = ("阳", 1)
        else:
            r = ("阴(动)", 0)
        lines.append(r)
        print(f"  {nm}: {r[0]}")
    yaos = [l[1] for l in lines]
    ben = hexagram_name(tri_to_num(yaos[3:]), tri_to_num(yaos[:3]))
    bians = [1 - x if "动" in lines[i][0] else x for i, x in enumerate(yaos)]
    bian = hexagram_name(tri_to_num(bians[3:]), tri_to_num(bians[:3]))
    dong = [i + 1 for i, l in enumerate(lines) if "动" in l[0]]
    print(f"本卦: {ben}  变卦: {bian}  动爻: {dong or '无(静卦)'}")
    print(f"占时: {lunar.toString()}  {day_gz}日  月建{month_gz}")
    r = najia.zhuang(ben, bian, dong, day_gz, month_gz)
    najia.print_zhuang(r, yaos)
    najia.print_yongshen(r, question)
    return ben, bian, dong, r


def summary(ben, bian, dong, r, question="通用"):
    """一眼摘要卡：本卦变卦/问事用神/世应/评分吉凶（借鉴八字/紫微升级的「一眼看懂」层）。"""
    a = najia.yongshen_analysis(r, question)
    return "\n".join([
        f"【一眼摘要】六爻 · {ben} → {bian}  动爻:{dong or '无(静卦)'}",
        f"  问事：{question} · 用神：{a['用神']} · 落：{a['落爻']} · 世{r['世爻']} 应{r['应爻']}",
        f"  评分：{a['评分']}/100({a['吉凶']}) · 用神{a['旺衰']['等级']} · {a['世应'][0]}({a['世应'][1]})",
    ])


def pan_json(ben, bian, dong, r, question="通用"):
    """盘面事实层 JSON（机读，schema=liuyao-panfact-v1）。"""
    from judge.rules import pan_meta
    return {"schema": "liuyao-panfact-v1", "问事": question, "本卦": ben, "变卦": bian,
            "动爻": dong, "装卦": r, "分析": najia.yongshen_analysis(r, question), **pan_meta("六爻")}
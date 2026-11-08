# -*- coding: utf-8 -*-
"""紫微斗数 · 排盘金标准校验（对照 py-iztro，字段级 parity 回归）。

把自写排盘 `zhiwei.cast` 与 py-iztro（iztro 的 Python 移植）逐字段比对，
锁定排盘正确性。对标 x-iztro「字段级 parity（716,314 golden cases）」，本模块
做同向的可复现抽样校验（默认 1000 例，可 `--n 10000`）。

比对字段：
  硬字段（必须一致，否则判错）：命宫支/身宫支/五行局/紫微支/天府支/每宫主星/
    生年四化/每宫大限/核心辅星(禄存擎羊陀罗天马魁钺左右昌曲火铃空劫)。
  软字段（只统计差异，不判错）：主星亮度（庙旺利陷各家亮度表有分歧）。

用法：
  python ziwei_crosscheck.py            # 默认 1000 例
  python ziwei_crosscheck.py --n 10000 --seed 42
"""
import sys
import re
import random
import contextlib
import io

try:
    from py_iztro import Astro
    _HAS_IZTRO = True
except ImportError:
    _HAS_IZTRO = False

from lunar_python import Solar
from pan import zhiwei
CORE_FU = {"禄存", "擎羊", "陀罗", "天马", "天魁", "天钺", "左辅", "右弼",
           "文昌", "文曲", "火星", "铃星", "地空", "地劫"}
_JU_NUM = {"二": 2, "三": 3, "四": 4, "五": 5, "六": 6}

# 农历中文数字解析（用于核对 iztro 农历日期 vs lunar_python）
_CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_MONTH = {"正": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
             "七": 7, "八": 8, "九": 9, "十": 10, "冬": 11, "腊": 12}


def _cn_day(s):
    s = s.lstrip("初")
    if s == "十":
        return 10
    if s == "二十":
        return 20
    if s == "三十":
        return 30
    if s.startswith("十"):
        return 10 + _CN.get(s[1], 0)
    if s.startswith("廿"):
        return 20 + _CN.get(s[1], 0)
    if s.startswith("二十"):
        return 20 + _CN.get(s[2], 0)
    return _CN.get(s)


def _cn_lunar_parse(s):
    """iztro lunar_date 字符串 -> (月, 日)。如 '二〇五七年闰七月廿八' -> (7, 28)。"""
    m = re.search(r"年(闰)?(正|二|三|四|五|六|七|八|九|十|冬|腊)月(.+)", s)
    if not m:
        return None
    return _CN_MONTH[m.group(2)], _cn_day(m.group(3))


def _shi_index(hour):
    return (hour + 1) // 2 % 12


def _parse_ju(s):
    for ch in s:
        if ch in _JU_NUM:
            return _JU_NUM[ch]
    return None


def _iz_star_zhi(d, name):
    for p in d["palaces"]:
        for s in p["major_stars"]:
            if s["scope"] == "origin" and s["name"] == name:
                return p["earthly_branch"]
    return None


def compare_one(sy, sm, sd, hour, gender):
    """单例比对，返回 (diffs, bright, cal_note)。
    cal_note 非空表示农历日期数据差异（lunar_python vs iztro JS 朔日计算），非算法错误。"""
    a = Astro().by_solar(f"{sy}-{sm}-{sd}", _shi_index(hour), "男" if gender else "女")
    d = a.model_dump()
    # 日历数据核对：农历月日一致才比字段，否则标日历差异并跳过
    lp = Solar.fromYmdHms(sy, sm, sd, hour, 0, 0).getLunar()
    iz = _cn_lunar_parse(d["lunar_date"])
    if iz is not None and (abs(lp.getMonth()) != iz[0] or lp.getDay() != iz[1]):
        return [], 0, f"{abs(lp.getMonth())}月{lp.getDay()}日 vs iztro {iz[0]}月{iz[1]}日"
    with contextlib.redirect_stdout(io.StringIO()):
        r = zhiwei.cast(sy, sm, sd, hour, gender)
    diffs = []

    # 命宫支
    if r["命宫"][1] != d["earthly_branch_of_soul_palace"]:
        diffs.append(("命宫支", r["命宫"][1], d["earthly_branch_of_soul_palace"]))
    # 身宫支
    if r["身宫"][1] != d["earthly_branch_of_body_palace"]:
        diffs.append(("身宫支", r["身宫"][1], d["earthly_branch_of_body_palace"]))
    # 五行局
    iz_ju = _parse_ju(d["five_elements_class"])
    if r["局数"] != iz_ju:
        diffs.append(("五行局", r["局数"], d["five_elements_class"]))
    # 紫微/天府支
    for name, our in (("紫微", r["紫微"]), ("天府", r["天府"])):
        iz = _iz_star_zhi(d, name)
        if our != iz:
            diffs.append((name + "支", our, iz))
    # 每宫主星 / 核心辅星 / 大限
    for i in range(12):
        ours = {n for n, b, s in r["十二宫"][i]["主星"]}
        izs = {s["name"] for s in d["palaces"][i]["major_stars"] if s["scope"] == "origin"}
        if ours != izs:
            diffs.append((f"{r['十二宫'][i]['宫']}主星", sorted(ours), sorted(izs)))
        ourf = set(r["十二宫"][i]["辅星"]) & CORE_FU
        izf = {s["name"] for s in d["palaces"][i]["minor_stars"]} & CORE_FU
        if ourf != izf:
            diffs.append((f"{r['十二宫'][i]['宫']}辅星", sorted(ourf), sorted(izf)))
        ourd = r["十二宫"][i]["大限"]
        izd = d["palaces"][i].get("decadal")
        izr = tuple(izd["range"]) if izd else None
        if ourd != izr:
            diffs.append((f"{r['十二宫'][i]['宫']}大限", ourd, izr))
    # 生年四化
    oursihua = {f["星"]: f["四化"] for f in r["四化飞星"]}
    izsihua = {}
    for p in d["palaces"]:
        for s in p["major_stars"] + p["minor_stars"]:
            if s.get("mutagen"):
                izsihua[s["name"]] = s["mutagen"]
    if oursihua != izsihua:
        diffs.append(("生年四化", oursihua, izsihua))
    # 亮度（软差异，只统计不判错）
    bright = 0
    for i in range(12):
        ourb = {n: b for n, b, s in r["十二宫"][i]["主星"]}
        izb = {s["name"]: s["brightness"] for s in d["palaces"][i]["major_stars"] if s["scope"] == "origin"}
        for n in ourb:
            if n in izb and ourb[n] != izb[n]:
                bright += 1
    return diffs, bright, None


def run(n=1000, seed=42):
    if not _HAS_IZTRO:
        return {"可用": False, "说明": "py-iztro 未安装，无法金标准校验"}
    rng = random.Random(seed)
    hard = {}      # 字段 -> 差异次数
    total = 0
    bright_total = 0
    cal_diffs = 0  # 农历日期数据差异例数
    cal_samples = []
    samples = []   # 前几例差异样本
    for _ in range(n):
        sy = rng.randint(1900, 2100)
        sm = rng.randint(1, 12)
        sd = rng.randint(1, 28)
        hour = rng.randint(0, 23)
        gender = rng.randint(0, 1)
        diffs, bright, cal_note = compare_one(sy, sm, sd, hour, gender)
        total += 1
        bright_total += bright
        if cal_note:
            cal_diffs += 1
            if len(cal_samples) < 5:
                cal_samples.append((f"{sy}-{sm:02d}-{sd:02d}", cal_note))
            continue
        for field, _, _ in diffs:
            hard[field] = hard.get(field, 0) + 1
        if diffs and len(samples) < 5:
            samples.append((f"{sy}-{sm:02d}-{sd:02d} {hour}h {'男' if gender else '女'}", diffs))
    return {"可用": True, "总数": total, "硬差异": hard,
            "亮度差异": bright_total, "日历差异": cal_diffs, "日历样本": cal_samples,
            "样本": samples}


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = sys.argv[1:]
    n = 1000
    seed = 42
    if "--n" in args:
        n = int(args[args.index("--n") + 1])
    if "--seed" in args:
        seed = int(args[args.index("--seed") + 1])
    r = run(n, seed)
    if not r["可用"]:
        print(r["说明"])
        return
    print(f"[紫微排盘金标准校验] 抽样 {r['总数']} 例（对照 py-iztro）")
    print(f"  亮度差异(软,不判错): {r['亮度差异']} 处")
    if r["日历差异"]:
        print(f"  农历日历数据差异: {r['日历差异']}/{r['总数']} 例（lunar_python 与 iztro JS 朔日不同，非算法错误）")
        for case, note in r["日历样本"]:
            print(f"    {case}: {note}")
    if not r["硬差异"]:
        print("  硬字段 parity: 全部一致 ✓")
    else:
        print("  硬字段差异统计:")
        for field, cnt in sorted(r["硬差异"].items(), key=lambda x: -x[1]):
            print(f"    {field}: {cnt}/{r['总数']} 例不一致")
        print("  差异样本:")
        for case, diffs in r["样本"]:
            print(f"    {case}:")
            for f, o, i in diffs:
                print(f"      {f}: 我方={o}  iztro={i}")


if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""奇门遁甲 1080 局全量回归 + 结构不变量 + 古籍局式对照。

三层体检（用「独立参考实现」重写标准转盘规则，不复用引擎函数；引擎作被验对象）：
  1. 穷举体检 sweep()：18 局(阳遁1-9 + 阴遁1-9) × 60 甲子时干支 = 1080 局，
     用独立参考排盘，统计参考崩溃 / 漏排 / 值符值使 / 门星神分布。
  2. 结构不变量 engine_check()：对真实日期用引擎起盘(置闰法)，解析其「排局」与
     「时干支」，与独立参考逐字比对：地盘六仪 / 值符值使 / 八门 / 九星 / 八神。
  3. 古籍局式对照 cross_check()：gold 样例(阴遁九局 2026-10-07)硬校验 +
     《秘笈大全》嵌入局式(榖雨例)软标记(该例阴阳遁与节气分组矛盾，见文末说明)。

【已修复的引擎 bug（回归守卫）】kinqimen 2019 旧代码，值符加时干法在「时干=甲」
的旬首时(甲戌/甲申/甲午/甲辰/甲寅，共 5/6 旬首时)原有 bug：引擎把值符落在「旬首
六仪宫」，而标准规则(甲遁戊)应落「戊宫」。后果：值符星落宫错 → 九星、八神整体
偏移；八门(值使寻时支)不受影响。证据《奇门遁甲统宗·值符加时干法》「看用时之干临
于地盘何宫，即以天盘值符加于此宫」。**已在 config.zhifu_n_zhishi 与 kinqimen.pan_sky
各一处 [PATCH] 修复**，本脚本层2 现应报「已知甲时值符bug = 0」。_KNOWN_XUNSHOU_KEYS
分类保留作回归守卫：若回退补丁，甲时值符错位会归入 known_bug 而非误报。

用法：
  python scripts/libs/qimen_regress.py           # 全部三层
  python scripts/libs/qimen_regress.py sweep     # 只跑穷举(独立参考层)
  python scripts/libs/qimen_regress.py engine    # 只跑引擎对拍(层2)
  python scripts/libs/qimen_regress.py cases     # 只跑古籍局式(层3)

参考实现的排盘规则（均为标准时家奇门转盘法，出处《奇门遁甲统宗》《烟波钓叟歌》）：
  - 地盘：戊落局数宫，己庚辛壬癸丁丙乙 阳顺(宫序+1)/阴逆(宫序-1) 排满九宫(含中5)。
  - 值符星 = 时旬首六仪落宫的原星；值符星宫 = 时干六仪所在地盘宫。
  - 值使门 = 时旬首六仪落宫的原门；值使门宫 = 值使原宫飞「时干序数」步
    (恒等式：时支-旬首支 ≡ 时干，故寻值使于时支等价于飞时干序数步)。
  - 九星/八门/八神沿洛书转盘序(坎艮震巽离坤兑乾)排布，阳顺阴逆；值符星值使门落
    中5宫则寄坤2；天芮与天禽同宫，排盘以「禽」占坤2位(值符星名仍可出「芮」)。
"""
import os
import sys
import re
import datetime
import collections

# Windows 控制台默认 GBK，统一转 UTF-8（与 cast.py / liuren_regress.py 一致）
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 本文件在 regress/ 子目录，需把上级 libs/ 加进 sys.path 才能 `from engines.qimen` 与
# `import engines.qimen.config`（否则 `python scripts/libs/regress/qimen_regress.py` 直接跑
# 会 ModuleNotFoundError: engines，docs 里的直跑用法即成死路径）。
LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from engines.qimen import Qimen  # noqa: E402

# 引擎的 jq/jq_distance 用 ephem 对每节气做收敛迭代，单次起盘 ~6s。
# 这些均为纯函数(仅依赖 datetime)，此处加缓存把引擎对拍降到毫秒级。
import functools  # noqa: E402
import engines.qimen.config as _config  # noqa: E402
for _fn in ("jq", "jq_distance", "gangzhi", "qimen_ju_name_zhirun", "qimen_ju_name_chaibu"):
    if hasattr(_config, _fn):
        setattr(_config, _fn, functools.lru_cache(maxsize=None)(getattr(_config, _fn)))

# ============================ 独立参考常量 ============================
_GAN = "甲乙丙丁戊己庚辛壬癸"
_ZHI = "子丑寅卯辰巳午未申酉戌亥"
# 宫数 -> 繁体卦（引擎输出以繁体卦为键）
_GONG_GUA = {1: "坎", 2: "坤", 3: "震", 4: "巽", 5: "中", 6: "乾", 7: "兌", 8: "艮", 9: "離"}
_GUA_GONG = {v: k for k, v in _GONG_GUA.items()}
# 宫数 -> 原九星 / 原八门（中5寄坤2=死）
_GONG_STAR = {1: "蓬", 2: "芮", 3: "沖", 4: "輔", 5: "禽", 6: "心", 7: "柱", 8: "任", 9: "英"}
_GONG_DOOR = {1: "休", 2: "死", 3: "傷", 4: "杜", 5: "死", 6: "開", 7: "驚", 8: "生", 9: "景"}
# 洛书转盘顺时针宫序（坎艮震巽离坤兑乾）
_CLOCKWISE = [1, 8, 3, 4, 9, 2, 7, 6]
# 九星 / 八门 转盘顺序（与顺时针宫序对齐；天禽占坤2位）
_STAR_R = ["蓬", "任", "沖", "輔", "英", "禽", "柱", "心"]
_DOOR_R = ["休", "生", "傷", "杜", "景", "死", "驚", "開"]
_GOD_YANG = ["符", "蛇", "陰", "合", "勾", "雀", "地", "天"]
_GOD_YIN = ["符", "蛇", "陰", "合", "虎", "玄", "地", "天"]
# 旬首支 -> 遁仪
_XUNSHOU_YI = {"子": "戊", "戌": "己", "申": "庚", "午": "辛", "辰": "壬", "寅": "癸"}
_YI_JIA = {"戊": "甲子", "己": "甲戌", "庚": "甲申", "辛": "甲午", "壬": "甲辰", "癸": "甲寅"}
# 时干 -> 六仪（甲遁于戊）
_GAN_YI = {"甲": "戊", "乙": "乙", "丙": "丙", "丁": "丁", "戊": "戊",
           "己": "己", "庚": "庚", "辛": "辛", "壬": "壬", "癸": "癸"}
_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_NUM_CN = {v: k for k, v in _CN_NUM.items()}


def all_jiazi():
    return [_GAN[i % 10] + _ZHI[i % 12] for i in range(60)]


def _next_gong(g):
    """阳遁顺飞（含中5，1..9循环）。"""
    return g % 9 + 1


def _prev_gong(g):
    """阴遁逆飞（含中5，9..1循环）。"""
    return (g - 2) % 9 + 1


# ============================ 独立参考实现 ============================
def ref_earth(yy, k):
    """地盘六仪：戊落k宫，己庚辛壬癸丁丙乙 阳顺/阴逆。返回 {宫数: 干}。"""
    earth = {}
    g = k
    for gan in ("戊", "己", "庚", "辛", "壬", "癸", "丁", "丙", "乙"):
        earth[g] = gan
        g = _next_gong(g) if yy == "阳" else _prev_gong(g)
    return earth


def ref_xunshou(hgz):
    """时干支 -> (旬首甲X, 遁仪, 旬首支)。"""
    g, z = hgz[0], hgz[1]
    gi, zi = _GAN.index(g), _ZHI.index(z)
    xun_zhi = _ZHI[(zi - gi) % 12]
    yi = _XUNSHOU_YI[xun_zhi]
    return _YI_JIA[yi], yi, xun_zhi


def ref_zhifu_zhishi(yy, k, hgz):
    """值符值使：返回 {值符星, 值符星宫, 值使门, 值使门宫, 旬首仪}。"""
    earth = ref_earth(yy, k)
    gan2gong = {v: kk for kk, v in earth.items()}
    _, yi, _ = ref_xunshou(hgz)
    xun_gong = gan2gong[yi]                 # 旬首六仪落宫
    zhifu_star = _GONG_STAR[xun_gong]       # 值符星（可出「芮」）
    zhishi_door = _GONG_DOOR[xun_gong]      # 值使门
    zhifu_gong = gan2gong[_GAN_YI[hgz[0]]]  # 值符星落宫 = 时干六仪宫
    g = xun_gong
    for _ in range(_GAN.index(hgz[0])):     # 值使门宫 = 值使原宫飞时干序数步
        g = _next_gong(g) if yy == "阳" else _prev_gong(g)
    return {"值符星": zhifu_star, "值符星宫": zhifu_gong,
            "值使门": zhishi_door, "值使门宫": g, "旬首仪": yi}


def _rot_place(start_gong, order, yy):
    """把 order 从 start_gong 起沿转盘序(阳顺阴逆)铺满 8 宫。返回 {宫数: 值}。"""
    if start_gong == 5:          # 中5寄坤2
        start_gong = 2
    gongs = list(_CLOCKWISE) if yy == "阳" else list(reversed(_CLOCKWISE))
    i = gongs.index(start_gong)
    gongs = gongs[i:] + gongs[:i]
    return dict(zip(gongs, order))


def ref_xing(yy, k, hgz):
    """九星转盘。返回 {宫数: 星}（芮已并入禽）。"""
    zz = ref_zhifu_zhishi(yy, k, hgz)
    star = "禽" if zz["值符星"] == "芮" else zz["值符星"]   # 天芮并入天禽
    order = _STAR_R if yy == "阳" else list(reversed(_STAR_R))
    order = order[order.index(star):] + order[:order.index(star)]
    return _rot_place(zz["值符星宫"], order, yy)


def ref_men(yy, k, hgz):
    """八门转盘。返回 {宫数: 门}。"""
    zz = ref_zhifu_zhishi(yy, k, hgz)
    order = _DOOR_R if yy == "阳" else list(reversed(_DOOR_R))
    order = order[order.index(zz["值使门"]):] + order[:order.index(zz["值使门"])]
    return _rot_place(zz["值使门宫"], order, yy)


def ref_shen(yy, k, hgz):
    """八神。返回 {宫数: 神}（值符落值符星宫，其余顺排）。"""
    zz = ref_zhifu_zhishi(yy, k, hgz)
    gods = _GOD_YANG if yy == "阳" else _GOD_YIN
    return _rot_place(zz["值符星宫"], gods, yy)


def ref_full(yy, k, hgz):
    """独立参考全盘。返回 {地盘, 值符值使, 门, 星, 神}。"""
    return {
        "地盘": ref_earth(yy, k),
        "值符值使": ref_zhifu_zhishi(yy, k, hgz),
        "门": ref_men(yy, k, hgz),
        "星": ref_xing(yy, k, hgz),
        "神": ref_shen(yy, k, hgz),
    }


# ============================ 层1：穷举 1080 ============================
def sweep():
    stats = {
        "total": 0, "crash": [], "门错": [], "星错": [], "神错": [],
        "值符分布": collections.Counter(), "值使分布": collections.Counter(),
        "局分布": collections.Counter(),
    }
    jiazi = all_jiazi()
    for yy in ("阳", "阴"):
        for k in range(1, 10):
            stats["局分布"][f"{yy}{k}"] = 0
            for hgz in jiazi:
                stats["total"] += 1
                stats["局分布"][f"{yy}{k}"] += 1
                try:
                    r = ref_full(yy, k, hgz)
                    zz = r["值符值使"]
                    stats["值符分布"][zz["值符星"]] += 1
                    stats["值使分布"][zz["值使门"]] += 1
                    # 门/星/神 各 8 宫，无重复无遗漏
                    for key, want in (("门", 8), ("星", 8), ("神", 8)):
                        vals = list(r[key].values())
                        if len(vals) != want or len(set(vals)) != want:
                            stats[f"{key}错"].append((yy, k, hgz, vals))
                except Exception as e:  # noqa: BLE001
                    stats["crash"].append((yy, k, hgz, repr(e)))
    return stats


def _fmt_sweep(stats):
    lines = [f"总计 {stats['total']} 局（应 1080）",
             f"参考崩溃: {len(stats['crash'])}"]
    for c in stats["crash"][:10]:
        lines.append(f"    {c}")
    lines.append(f"门排布错: {len(stats['门错'])}  星排布错: {len(stats['星错'])}  神排布错: {len(stats['神错'])}")
    lines.append("局分布: " + ", ".join(f"{k}={v}" for k, v in sorted(stats["局分布"].items())))
    lines.append("值符星分布: " + ", ".join(f"{k}={v}" for k, v in stats["值符分布"].most_common()))
    lines.append("值使门分布: " + ", ".join(f"{k}={v}" for k, v in stats["值使分布"].most_common()))
    return "\n".join(lines)


# ============================ 层2：引擎对拍 ============================
def _parse_ju(paiju):
    """'陰遁九局中元' -> (阴/阳, 局数) 或 None。"""
    if not paiju or "局" not in paiju:
        return None
    yy = "阴" if paiju[0] in "陰阴" else "阳"
    k = _CN_NUM.get(paiju[2])
    if k is None:
        return None
    return yy, k


def _parse_shiganzhi(ganzhi):
    """'丙午年丁酉月甲寅日己巳時' -> '己巳'。"""
    m = re.search(r"([%s][%s])時$" % (_GAN, _ZHI), ganzhi)
    return m.group(1) if m else None


def engine_compare(yy, k, hgz, r):
    """引擎盘 r 与独立参考逐字比对。返回错误列表(空=通过)。"""
    ref = ref_full(yy, k, hgz)
    errs = []

    def _norm(d, fan=None):
        # 繁体卦键 -> 宫数键
        out = {}
        for key, val in (d or {}).items():
            g = _GUA_GONG.get(key)
            if g is not None:
                out[g] = val
        return out

    # 地盘（9 宫含中5）
    eng_earth = _norm(r.get("地盤"))
    if eng_earth != ref["地盘"]:
        errs.append(("地盘", eng_earth, ref["地盘"]))

    # 值符值使
    zfzs = r.get("值符值使") or {}
    eng_zf = {
        "值符星": (zfzs.get("值符星宮") or ["", ""])[0],
        "值符星宫": _GUA_GONG.get((zfzs.get("值符星宮") or ["", ""])[1]),
        "值使门": (zfzs.get("值使門宮") or ["", ""])[0],
        "值使门宫": _GUA_GONG.get((zfzs.get("值使門宮") or ["", ""])[1]),
        "旬首仪": (zfzs.get("值符天干") or ["", ""])[1],
    }
    for key in ("值符星", "值符星宫", "值使门", "值使门宫", "旬首仪"):
        if eng_zf[key] != ref["值符值使"][key]:
            errs.append(("值符值使." + key, eng_zf[key], ref["值符值使"][key]))

    # 门 / 星 / 神（8 宫）
    for key in ("门", "星", "神"):
        eng = _norm(r.get("門" if key == "门" else "星" if key == "星" else "神"))
        if eng != ref[key]:
            errs.append((key, eng, ref[key]))
    return errs


# 已知引擎 bug：值符加时干法在旬首时(时干=甲)落「旬首六仪宫」而非「戊宫」，
# 波及值符星宫/九星/八神（八门值使不受影响）。
_KNOWN_XUNSHOU_KEYS = ("值符值使.值符星宫", "星", "神")


def engine_check(start=(2024, 1, 1), end=(2024, 12, 31), hours=(0, 6, 12, 18)):
    """对真实日期起盘(置闰法)，与独立参考对拍。返回统计 dict。"""
    stats = {
        "total": 0, "crash": [], "mismatch": [], "known_bug": [], "ok": 0,
        "局覆盖": collections.Counter(), "阴阳覆盖": collections.Counter(),
    }
    d = datetime.date(*start)
    end_d = datetime.date(*end)
    while d <= end_d:
        for h in hours:
            stats["total"] += 1
            try:
                r = Qimen(d.year, d.month, d.day, h, 0).pan(2)
            except Exception as e:  # noqa: BLE001
                stats["crash"].append((str(d), h, repr(e)))
                d += datetime.timedelta(days=1)
                continue
            ju = _parse_ju(r.get("排局"))
            hgz = _parse_shiganzhi(r.get("干支"))
            if not ju or not hgz:
                stats["mismatch"].append((str(d), h, "排局/时干支解析失败", r.get("排局"), r.get("干支")))
                d += datetime.timedelta(days=1)
                continue
            yy, k = ju
            stats["局覆盖"][f"{yy}遁{k}局"] += 1
            stats["阴阳覆盖"][yy] += 1
            errs = engine_compare(yy, k, hgz, r)
            if errs:
                if hgz[0] == "甲" and all(e[0] in _KNOWN_XUNSHOU_KEYS for e in errs):
                    stats["known_bug"].append((str(d), h, ju, hgz))
                else:
                    stats["mismatch"].append((str(d), h, ju, hgz, errs[:3]))
            else:
                stats["ok"] += 1
        d += datetime.timedelta(days=1)
    return stats


def _fmt_engine(stats):
    lines = [
        f"起盘 {stats['total']} 次（{stats['阴阳覆盖'].get('阳', 0)}阳 / {stats['阴阳覆盖'].get('阴', 0)}阴）",
        f"引擎崩溃: {len(stats['crash'])}",
        f"完全吻合: {stats['ok']}  意外不吻合: {len(stats['mismatch'])}  已知甲时值符bug: {len(stats['known_bug'])}",
    ]
    for c in stats["crash"][:10]:
        lines.append(f"    崩溃 {c}")
    for m in stats["mismatch"][:20]:
        lines.append(f"    意外不吻合 {m}")
    for k in stats["known_bug"][:8]:
        lines.append(f"    已知甲时值符bug {k}")
    lines.append("局覆盖: " + ", ".join(f"{k}={v}" for k, v in sorted(stats["局覆盖"].items())))
    return "\n".join(lines)


# ============================ 层3：古籍局式对照 ============================
def cross_check():
    """gold 样例硬校验 + 古籍嵌入局式软标记。返回 (findings, gold_ok)。"""
    findings = []
    # gold 样例：阴遁九局 2026-10-07 10:00（cases/_gold/qimen.md，双实现+手核锁定）
    r = Qimen(2026, 10, 7, 10, 0).pan(2)
    ju = _parse_ju(r.get("排局"))
    zfzs = r.get("值符值使") or {}
    gold_ok = (
        ju == ("阴", 9)
        and (zfzs.get("值符星宮") or ["", ""])[0] == "英"
        and (zfzs.get("值符星宮") or ["", ""])[1] == "艮"
        and (zfzs.get("值使門宮") or ["", ""])[0] == "景"
        and (zfzs.get("值使門宮") or ["", ""])[1] == "巽"
    )
    findings.append(
        f"gold 样例(2026-10-07 10:00 阴遁九局 天英值符 景门值使): {'✓ 吻合' if gold_ok else '✗ 不符: ' + str((ju, zfzs))}"
    )
    # 古籍嵌入局式：《秘笈大全》占胜败「如榖雨上元阴遁五局，丙辛日壬辰时，天柱为值符」。
    # 榖雨在冬至后夏至前，节气分组属阳遁(阴遁五局当为笔误/特例)，故仅软标记不硬卡。
    findings.append(
        "古籍局式(榖雨上元阴遁五局 丙辛日壬辰时 天柱值符): 待定位具体日期，"
        "且『榖雨→阴遁』与节气分组(阳遁)矛盾，疑原文笔误，仅作软标记不参与判定。"
    )
    return findings, gold_ok


# ============================ main ============================
if __name__ == "__main__":
    argv = sys.argv[1:]
    mode = argv[0] if argv else "all"
    if mode in ("all", "sweep"):
        print("=" * 64)
        print("[层1] 穷举体检（独立参考 · 18局 × 60时 = 1080 局）")
        print(_fmt_sweep(sweep()))
    if mode in ("all", "engine"):
        print("=" * 64)
        print("[层2] 引擎对拍（置闰法起盘 vs 独立参考，逐字比对）")
        print(_fmt_engine(engine_check()))
    if mode in ("all", "cases"):
        print("=" * 64)
        print("[层3] 古籍局式对照")
        findings, gold_ok = cross_check()
        for f in findings:
            print("  " + f)
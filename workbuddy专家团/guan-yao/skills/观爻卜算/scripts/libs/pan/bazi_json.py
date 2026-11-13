# -*- coding: utf-8 -*-
"""八字「结构化双轨输出 + 时间不确定逐分钟枚举」

借鉴 taibu-core 的 content/structuredContent 思路：散文（人读）之外，另给一份
**盘面事实层结构化 JSON**（机读、可程序化校验/渲染）；借鉴 chinese-fortune 的
「时间只记得范围→逐候选枚举」，标出哪些柱稳定、哪些随候选变化。

用法:
  python libs/bazi_json.py 2001 9 22 4 0 0 1 [--lon 118.9] [--dst]
      输出盘面事实层 JSON（schema=bazi-panfact-v1）
  python libs/bazi_json.py 2001 9 22 1 --range "03:00-05:00"
      时间不确定枚举：稳定柱 / 变化柱 / 结论稳定性
"""
import sys
import json
import datetime as _dt

from lifa import taiyangshi
from pan import bazi_liunian
from judge import bazi_evaluator as ev
from lunar_python import Solar


def _shishen(day_gan, g):
    return ev._shishen(day_gan, g)


def _pillar(ec, key):
    """lunar_python EightChar 一柱 -> 结构化 dict。"""
    gan = getattr(ec, f"get{key}Gan")()
    zhi = getattr(ec, f"get{key}Zhi")()
    hide = getattr(ec, f"get{key}HideGan")()
    return {
        "干支": gan + zhi,
        "十神": getattr(ec, f"get{key}ShiShenGan")(),
        "藏干": list(hide),
        "藏干十神": [_shishen(ec.getDayGan(), c) for c in hide],
        "五行": getattr(ec, f"get{key}WuXing")(),
        "纳音": getattr(ec, f"get{key}NaYin")(),
        "地势": getattr(ec, f"get{key}DiShi")(),
        "空亡": getattr(ec, f"get{key}XunKong")(),
    }


def _dayun(ec, gender):
    yun = ec.getYun(gender)
    out = []
    for d in yun.getDaYun():
        if d.getGanZhi():
            out.append({"干支": d.getGanZhi(), "起始年": d.getStartYear(), "起始岁": d.getStartAge()})
    start = yun.getStartSolar()
    return out, {
        "起运": f"{yun.getStartYear()}年{yun.getStartMonth()}月{yun.getStartDay()}天",
        "交运": f"{start.getYear():04d}-{start.getMonth():02d}-{start.getDay():02d}",
        "起运岁": yun.getStartYear() + yun.getStartMonth() / 12.0 + yun.getStartDay() / 365.0,
    }


def cast_json(y, mo, d, hh=12, mi=0, ss=0, gender=1, lon=None, dst=False, zishi="same"):
    """盘面事实层 JSON（含主路径 + 独立评估双层分析）。"""
    raw = _dt.datetime(y, mo, d, hh, mi, ss)
    corr, notes = taiyangshi.correct(raw, lon, dst)
    y2, mo2, d2, h2, mi2, s2 = corr.year, corr.month, corr.day, corr.hour, corr.minute, corr.second

    ec = Solar.fromYmdHms(y2, mo2, d2, h2, mi2, s2).getLunar().getEightChar()
    lun = Solar.fromYmdHms(y2, mo2, d2, h2, mi2, s2).getLunar()

    dayun, yunmeta = _dayun(ec, gender)

    # 主路径分析（旺衰/格局/喜忌/综合评分），捕获其打印、取返回 dict
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main = bazi_liunian.mingli_analysis(y2, mo2, d2, h2, mi2, s2, gender)

    # 独立评估（第二意见）
    indep = ev.derive_from_solar(y2, mo2, d2, h2, mi2, s2, gender)

    ws = main["旺衰"]
    from judge.rules import pan_meta
    return {
        "schema": "bazi-panfact-v1",
        **pan_meta("八字"),
        "元信息": {
            "公历": raw.strftime("%Y-%m-%d %H:%M:%S"),
            "校正后": corr.strftime("%Y-%m-%d %H:%M:%S") if (notes or lon) else None,
            "校正说明": notes,
            "农历": f"{lun.getYearInChinese()}年{lun.getMonthInChinese()}月{lun.getDayInChinese()}",
            "性别": "男" if gender == 1 else "女",
            "经度": lon,
        },
        "四柱": {
            "年": _pillar(ec, "Year"), "月": _pillar(ec, "Month"),
            "日": _pillar(ec, "Day"), "时": _pillar(ec, "Time"),
        },
        "日主": {"干支": ec.getDayGan() + ec.getDayZhi(), "五行": ev.WX[ec.getDayGan()]},
        "命宫": ec.getMingGong(), "胎元": ec.getTaiYuan(),
        "起运": yunmeta,
        "大运": dayun,
        "分析": {
            "旺衰": {
                "主路径": {"得分": ws["得分"], "判定": ws["档次"]},
                "独立评估": {"得分": indep["得分"], "判定": indep["旺衰"], "旺相休囚死": indep["旺相休囚死"]},
            },
            "格局": indep["格局"],
            "喜忌": {"喜": sorted(main["喜"]), "忌": sorted(main["忌"]),
                      "独立喜": indep["喜"], "独立忌": indep["忌"]},
            "综合评分": {"总分": main["综合评分"]["总分"], "等级": main["综合评分"]["等级"]},
        },
    }


def enumerate_range(y, mo, d, range_str, gender=1, step_min=1, lon=None, dst=False, zishi="same"):
    """出生时间只记得范围时，逐候选枚举四柱，标出稳定柱/变化柱。

    range_str 形如 "03:00-05:00"。返回：
      {候选数, 稳定柱{柱:干支}, 变化柱{柱: {干支: [起,止]}}, 结论稳定性}
    """
    a, b = range_str.split("-")
    h0, m0 = map(int, a.split(":"))
    h1, m1 = map(int, b.split(":"))
    t = _dt.datetime(y, mo, d, h0, m0)
    end = _dt.datetime(y, mo, d, h1, m1)
    if end <= t:
        end += _dt.timedelta(days=1)
    cand = {}
    cur = t
    while cur <= end:
        c, _ = taiyangshi.correct(cur, lon, dst)
        ec = Solar.fromYmdHms(c.year, c.month, c.day, c.hour, c.minute, c.second).getLunar().getEightChar()
        for key in ("Year", "Month", "Day", "Time"):
            gz = getattr(ec, f"get{key}")()
            cand.setdefault(key, []).append((cur.strftime("%H:%M"), gz))
        cur += _dt.timedelta(minutes=step_min)

    stable, varying = {}, {}
    for key, rows in cand.items():
        vals = sorted({gz for _, gz in rows})
        if len(vals) == 1:
            stable[key] = vals[0]
        else:
            spans = {}
            for hm, gz in rows:
                spans.setdefault(gz, []).append(hm)
            varying[key] = {gz: [spans[gz][0], spans[gz][-1]] for gz in vals}

    # 结论稳定性判定
    if "Time" in varying:
        msg = "时柱随候选变化 → 涉及时柱/子女/晚年的结论降级"
    elif "Day" in varying:
        msg = "日柱跨日界变化 → 日主及日柱结论需双盘对照"
    else:
        msg = "四柱全候选稳定，结论不受时间不确定影响"

    return {"候选数": len(cand.get("Year", [])), "步长分钟": step_min,
            "稳定柱": stable, "变化柱": varying, "结论稳定性": msg}


def _fmt_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)


# ---- 一眼摘要卡（借鉴卜易居/元亨利贞的"看得懂"层，但不牺牲可复核） ----
ZHI_WX = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
          "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}
_GONG = ["长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养"]
_CHANGSHENG = {
    "甲": "亥子丑寅卯辰巳午未申酉戌", "丙": "寅卯辰巳午未申酉戌亥子丑",
    "戊": "寅卯辰巳午未申酉戌亥子丑", "庚": "巳午未申酉戌亥子丑寅卯辰",
    "壬": "申酉戌亥子丑寅卯辰巳午未",
    "乙": "午巳辰卯寅丑子亥戌酉申未", "丁": "酉申未午巳辰卯寅丑子亥戌",
    "己": "酉申未午巳辰卯寅丑子亥戌", "辛": "子亥戌酉申未午巳辰卯寅丑",
    "癸": "卯寅丑子亥戌酉申未午巳辰",
}
_JIXIONG = {"长生": "吉", "沐浴": "平", "冠带": "吉", "临官": "吉", "帝旺": "大吉",
            "衰": "凶", "病": "凶", "死": "凶", "墓": "平", "绝": "凶", "胎": "平", "养": "平"}


def dishi(day_gan, zhi):
    """日主在某地支的长生十二宫名。"""
    seq = _CHANGSHENG.get(day_gan, "")
    i = seq.find(zhi)
    return _GONG[i] if i >= 0 else "?"


def wx_count(ec):
    """五行个数统计（天干4 + 地支本气4 = 8 字）。"""
    cnt = {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0}
    for key in ("Year", "Month", "Day", "Time"):
        cnt[ev.WX[getattr(ec, f"get{key}Gan")()]] += 1
        cnt[ZHI_WX[getattr(ec, f"get{key}Zhi")()]] += 1
    return cnt


def summary_card(y, mo, d, hh=12, mi=0, ss=0, gender=1, lon=None, dst=False):
    """一眼摘要卡：日主/身强弱/喜忌/五行统计/宫位/大运地势吉凶。"""
    import io
    import contextlib
    raw = _dt.datetime(y, mo, d, hh, mi, ss)
    corr, _ = taiyangshi.correct(raw, lon, dst)
    y2, mo2, d2, h2, mi2, s2 = corr.year, corr.month, corr.day, corr.hour, corr.minute, corr.second
    ec = Solar.fromYmdHms(y2, mo2, d2, h2, mi2, s2).getLunar().getEightChar()
    day_gan = ec.getDayGan()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main = bazi_liunian.mingli_analysis(y2, mo2, d2, h2, mi2, s2, gender)
    ws = main["旺衰"]
    dayun, _ = _dayun(ec, gender)
    return {
        "乾造坤造": "乾造" if gender == 1 else "坤造",
        "四柱": " ".join(getattr(ec, f"get{k}")() for k in ("Year", "Month", "Day", "Time")),
        "日主": f"{day_gan}({ev.WX[day_gan]})",
        "身强弱": f"{ws['档次']}({ws['得分']}分)",
        "喜": "、".join(sorted(main["喜"])),
        "忌": "、".join(sorted(main["忌"])),
        "综合评分": f"{main['综合评分']['总分']}/100 {main['综合评分']['等级']}",
        "五行统计": wx_count(ec),
        "宫位": {"年": "祖先宫", "月": "父母宫", "日": "自己宫", "时": "子孙宫"},
        "大运": [{"干支": d["干支"], "岁": d["起始岁"],
                   "地势": dishi(day_gan, d["干支"][1]),
                   "吉凶": _JIXIONG.get(dishi(day_gan, d["干支"][1]), "平")} for d in dayun],
    }


def _fmt_summary(c):
    wxs = "  ".join(f"{k}{v}" for k, v in c["五行统计"].items())
    dy = "  ".join(f"{d['干支']}({d['岁']}岁·{d['地势']}{d['吉凶']})" for d in c["大运"])
    return "\n".join([
        f"【一眼摘要】{c['乾造坤造']}  {c['四柱']}",
        f"  日元 {c['日主']} · {c['身强弱']} · 喜{c['喜']} 忌{c['忌']} · 综合 {c['综合评分']}",
        f"  五行：{wxs}（金/木/水/火/土）",
        f"  宫位：年=祖先宫  月=父母宫  日=自己宫  时=子孙宫",
        f"  大运：{dy}",
    ])


def _fmt_range(r):
    lines = [f"[时间不确定枚举] 候选 {r['候选数']} 个（步长 {r['步长分钟']} 分钟）"]
    for k, v in r["稳定柱"].items():
        lines.append(f"  稳定柱 {k}：{v}")
    for k, v in r["变化柱"].items():
        for gz, span in v.items():
            lines.append(f"  变化柱 {k}：{gz}（{span[0]}–{span[1]}）")
    lines.append(f"  → {r['结论稳定性']}")
    return "\n".join(lines)


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    a = [x for x in sys.argv[1:] if not x.startswith("-") and x not in ("--lon", "--dst", "--range")]
    lon = None
    dst = False
    rng = None
    args = sys.argv[1:]
    for i, x in enumerate(args):
        if x == "--lon" and i + 1 < len(args):
            lon = float(args[i + 1])
        elif x == "--dst":
            dst = True
        elif x == "--range" and i + 1 < len(args):
            rng = args[i + 1]
    if rng:
        y, mo, d = (int(a[0]), int(a[1]), int(a[2]))
        gender = int(a[3]) if len(a) > 3 else 1
        print(_fmt_range(enumerate_range(y, mo, d, rng, gender, lon=lon, dst=dst)))
    elif len(a) >= 7:
        y, mo, d, hh, mi, ss, gender = (int(a[i]) for i in range(7))
        print(_fmt_json(cast_json(y, mo, d, hh, mi, ss, gender, lon=lon, dst=dst)))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
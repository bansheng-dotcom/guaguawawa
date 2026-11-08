# -*- coding: utf-8 -*-
"""紫微斗数运限（大限/流年/流月/流日/流时）封装。

引擎：py-iztro（iztro 的 Python 移植，MIT；本技能已用其做排盘对照校验）。
本模块是「结构化排盘层」：给出运限命宫、干支、四化、流曜、十二宫（确定性，可复现）；
断卦仍须按「化禄/化权/化科/化忌、流年命宫、流曜」等去典籍 txt Grep 原文佐证（双重保证）。

出处：《紫微斗数全书》（运限/四化飞星断法）。

用法：
  from pan.ziwei_horoscope import horoscope, format_horoscope
  h = horoscope(1990, 5, 15, 8, 1, target="2026-10-07")
  print(format_horoscope(h))
"""
import datetime

try:
    from py_iztro import Astro
    _HAS_IZTRO = True
except ImportError:  # pragma: no cover - 环境已装 py-iztro
    _HAS_IZTRO = False

SOURCE = "《紫微斗数全书》·运限四化"

_ZHI = "子丑寅卯辰巳午未申酉戌亥"


def _shi_index(hour):
    return (hour + 1) // 2 % 12  # 子=0


def _section(model, label):
    """把 py-iztro 运限 section 转成结构化 dict。"""
    if model is None:
        return None
    return {
        "运限": label,
        "命宫": model.get("earthly_branch") if isinstance(model, dict) else model.earthly_branch,
        "干支": f"{model.get('heavenly_stem', '')}{model.get('earthly_branch', '')}"
        if isinstance(model, dict) else f"{model.heavenly_stem}{model.earthly_branch}",
        "四化": model.get("mutagen") if isinstance(model, dict) else model.mutagen,
        "十二宫": model.get("palace_names") if isinstance(model, dict) else model.palace_names,
        "流曜": _extract_stars(model.get("stars") if isinstance(model, dict) else model.stars),
    }


def _extract_stars(stars):
    """把流曜 stars（12 宫 × 列表）摊平成 [星名] 并去重保序。"""
    names = []
    if not stars:
        return names
    for palace in stars:
        for s in palace:
            n = s.get("name") if isinstance(s, dict) else getattr(s, "name", None)
            if n and n not in names:
                names.append(n)
    return names


def horoscope(sy, sm, sd, hour, gender, target=None):
    """排运限。target 为目标日期（YYYY-MM-DD，缺省今天）。gender 1 男 0 女。"""
    if not _HAS_IZTRO:
        return {"可用": False, "说明": "py-iztro 未安装，运限不可用"}

    target = target or datetime.datetime.now().strftime("%Y-%m-%d")
    a = Astro().by_solar(f"{sy}-{sm:02d}-{sd:02d}", _shi_index(hour),
                         "男" if gender else "女")
    h = a.horoscope(target, _shi_index(hour)).model_dump()

    out = {"可用": True, "出生": f"{sy}-{sm:02d}-{sd:02d}",
           "流日": target, "出处": SOURCE}
    for key, label in (("yearly", "流年"), ("monthly", "流月"),
                       ("daily", "流日"), ("hourly", "流时")):
        out[key] = _section(h.get(key), label)
    return out


def format_horoscope(h):
    """格式化运限输出（返回字符串）。"""
    if not h.get("可用"):
        return h.get("说明", "")
    lines = [f"【紫微运限】（{SOURCE}）"]
    for key, label in (("yearly", "流年"), ("monthly", "流月"),
                       ("daily", "流日"), ("hourly", "流时")):
        sec = h.get(key)
        if not sec:
            continue
        sihua = " ".join(f"{s}化{v}" for s, v in zip(sec["四化"], ("禄", "权", "科", "忌"))) if sec["四化"] else ""
        lines.append(f"• {label}：{sec['干支']}（命宫在{sec['命宫']}）  四化：{sihua}")
        if sec["流曜"]:
            lines.append(f"    流曜：{'、'.join(sec['流曜'][:16])}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print(format_horoscope(horoscope(1990, 5, 15, 8, 1, target="2026-10-07")))
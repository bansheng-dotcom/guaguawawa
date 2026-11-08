# -*- coding: utf-8 -*-
"""紫微斗数 · 验前事校验（用已知人生事件回验命盘结构）。

输入出生时间 + 若干已知事件（年份 + 类型），逐年核对命盘流年结构是否与该年事件吻合：
  - 吉事（婚/子/升/财）看流年化禄/化科是否飞入对应宫（夫妻/子女/官禄/财帛）；
  - 凶事（破财/病/灾）看流年化忌是否飞入对应宫（财帛/疾厄/命）；
  - 太岁支落宫、小限落宫 作为引动佐证。
命中率高 → 命盘可信；命中率≈随机 → 提示排盘可能需复核（年界/时辰/命宫）。

出处：化忌入宫断诀《紫微斗数全书》「诸星化忌不宜逢，更会凶星愈肆凶」；太岁/小限引动
同书「岁君…与诸凶神相遇」「论大小限星辰过十二宫」。校验逻辑为 [规则推演]。

用法：
  from judge.ziwei_yanqian import validate_events, format_validate
  r = validate_events(1990, 5, 15, 8, 1, [(2015, "婚"), (2018, "子"), (2022, "破财")])
  print(format_validate(r))
"""
from lunar_python import Solar
from pan import zhiwei
SRC = "《紫微斗数全书》"

# 事件类型 -> (目标宫, 吉凶)
EVENT_TYPES = {
    "婚": ("夫妻宫", "吉"),
    "子": ("子女宫", "吉"),
    "升": ("官禄宫", "吉"),
    "财": ("财帛宫", "吉"),
    "破财": ("财帛宫", "凶"),
    "病": ("疾厄宫", "凶"),
    "灾": ("命宫", "凶"),
}


def _star_palace(chart, name):
    for i, p in enumerate(chart["十二宫"]):
        if any(n == name for n, b, s in p["主星"]) or name in p["辅星"]:
            return i
    return None


def _ming_idx(chart):
    for i, p in enumerate(chart["十二宫"]):
        if p["命"]:
            return i
    return None


def _palace_name(chart, idx):
    return chart["十二宫"][idx]["宫"]


def validate_events(sy, sm, sd, hour, gender, events):
    """回验事件。events: [(年份, 类型), ...]。返回逐事件命中 + 总体命中率。"""
    chart = zhiwei.cast(sy, sm, sd, hour, gender)
    ming = _ming_idx(chart)
    birth_solar = Solar.fromYmdHms(sy, sm, sd, hour, 0, 0)
    birth_ln = birth_solar.getLunar().getYear()
    xiaoxian_dir = 1 if gender else -1

    rows = []
    for year, typ in events:
        t_solar = Solar.fromYmd(year, 6, 1)
        t_lun = t_solar.getLunar()
        lng = t_lun.getYearGanByLiChun()
        lnz = t_lun.getYearZhiByLiChun()
        xusui = t_lun.getYear() - birth_ln + 1
        target_palace, jx = EVENT_TYPES.get(typ, ("命宫", "吉"))

        # 流年干四化飞宫
        sihua_fly = {}
        for si_name, star in zip(("禄", "权", "科", "忌"), zhiwei.SIHUA[lng]):
            p = _star_palace(chart, star)
            sihua_fly[si_name] = _palace_name(chart, p) if p is not None else "—"

        # 太岁支落宫
        taishui_idx = (zhiwei.ZHI.index(lnz) - 2) % 12
        taishui_palace = _palace_name(chart, taishui_idx)

        # 小限宫
        xl_idx = (ming + (xusui - 1) * xiaoxian_dir) % 12
        xl_palace = _palace_name(chart, xl_idx)

        # 命中判定
        hit = False
        reasons = []
        if jx == "凶":
            if sihua_fly["忌"] == target_palace:
                hit = True
                reasons.append("化忌飞入")
        else:
            for si in ("禄", "科"):
                if sihua_fly[si] == target_palace:
                    hit = True
                    reasons.append(f"化{si}飞入")
        if taishui_palace == target_palace:
            hit = True
            reasons.append("太岁落宫")
        if xl_palace == target_palace:
            hit = True
            reasons.append("小限落宫")

        rows.append({
            "年份": year, "类型": typ, "目标宫": target_palace, "吉凶": jx,
            "流年": f"{lng}{lnz}", "虚岁": xusui,
            "四化飞": sihua_fly, "太岁宫": taishui_palace, "小限宫": xl_palace,
            "命中": hit, "理由": "、".join(reasons) if reasons else "—",
        })

    hits = sum(1 for r in rows if r["命中"])
    return {"出生": f"{sy}-{sm:02d}-{sd:02d}", "性别": "男" if gender else "女",
            "事件数": len(rows), "命中数": hits,
            "命中率": round(hits / len(rows), 3) if rows else 0.0,
            "事件": rows}


def format_validate(r):
    L = [f"[紫微验前事] {r['出生']}({r['性别']})  命中 {r['命中数']}/{r['事件数']}（{r['命中率']:.0%}）"]
    for e in r["事件"]:
        mark = "✓" if e["命中"] else "✗"
        fly = "  ".join(f"{k}{v}" for k, v in e["四化飞"].items())
        L.append(f"  {mark} {e['年份']} {e['类型']}({e['目标宫']})  流年{e['流年']} 虚岁{e['虚岁']}")
        L.append(f"      四化飞: {fly}  太岁宫={e['太岁宫']}  小限宫={e['小限宫']}  → {e['理由']}")
    L.append("  〔化忌入宫断诀「诸星化忌不宜逢」出处《紫微斗数全书》；校验逻辑为[规则推演]〕")
    return "\n".join(L)


if __name__ == "__main__":
    import sys
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    # 演示：1990-05-15 男，假设 2014 婚 / 2018 生子 / 2022 破财
    r = validate_events(1990, 5, 15, 8, 1, [(2014, "婚"), (2018, "子"), (2022, "破财")])
    print(format_validate(r))
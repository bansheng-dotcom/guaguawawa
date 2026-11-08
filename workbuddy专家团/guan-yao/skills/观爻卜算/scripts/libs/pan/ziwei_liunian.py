# -*- coding: utf-8 -*-
"""紫微斗数 · 流年化忌叠冲扫描（时空压力热力表）。

对某个流年，把「生年化忌 + 大限化忌 + 流年化忌 + 六煞冲照」叠加到十二宫，
输出各宫压力热力表，找出该年重点受压的宫位（防对应事项之失）。

方法说明（诚实标注）：
- 化忌入宫断诀有原文：《紫微斗数全书》化忌入命/入限诀「诸星化忌不宜逢，更会凶星愈肆凶」。
- 「多忌叠冲热力表」是现代整合方法（飞星派/流年叠冲，借鉴 mingli-master 时空压力扫描），
  非《全书》直接原文，标 [规则推演]；断卦仍按「化忌、大限、流年」Grep 原文佐证。

用法：
  from pan.ziwei_liunian import diji_scan, format_scan
  r = diji_scan(1990, 5, 15, 8, 1, 2026)
  print(format_scan(r))
"""
import datetime
from lunar_python import Solar
from pan import zhiwei
SRC = "《紫微斗数全书》"

SHA_STARS = ["擎羊", "陀罗", "火星", "铃星", "地空", "地劫"]
# 重点宫（压力落到这些宫更需留意）
KEY_PALACES = ["命宫", "身宫", "财帛宫", "官禄宫", "夫妻宫", "疾厄宫"]


def _star_palace(chart, name):
    for i, p in enumerate(chart["十二宫"]):
        if any(n == name for n, b, s in p["主星"]) or name in p["辅星"]:
            return i
    return None


def diji_scan(sy, sm, sd, hour, gender, target_year):
    """扫描某流年的化忌叠冲压力。返回 dict（含生年/大限/流年忌 + 煞星 + 热力表）。"""
    chart = zhiwei.cast(sy, sm, sd, hour, gender)

    # 出生农历年、年干
    sol = Solar.fromYmdHms(sy, sm, sd, hour, 0, 0)
    lun = sol.getLunar()
    year_gan = lun.getYearGan()
    birth_ln = lun.getYear()

    # 流年干支（取流年 6 月，确保落入该农历年）
    t_sol = Solar.fromYmd(target_year, 6, 1)
    t_lun = t_sol.getLunar()
    liunian_gan = t_lun.getYearGan()
    liunian_zhi = t_lun.getYearZhi()

    # 生年化忌
    sheng_ji = zhiwei.SIHUA[year_gan][3]
    sheng_ji_p = _star_palace(chart, sheng_ji)

    # 大限（虚岁定位）
    xusui = t_lun.getYear() - birth_ln + 1
    daxian_p = None
    for i, p in enumerate(chart["十二宫"]):
        if p["大限"] and p["大限"][0] <= xusui <= p["大限"][1]:
            daxian_p = i
            break
    daxian_gan = chart["十二宫"][daxian_p]["干"] if daxian_p is not None else None
    daxian_ji = zhiwei.SIHUA[daxian_gan][3] if daxian_gan else None
    daxian_ji_p = _star_palace(chart, daxian_ji) if daxian_ji else None

    # 流年化忌
    liunian_ji = zhiwei.SIHUA[liunian_gan][3]
    liunian_ji_p = _star_palace(chart, liunian_ji)

    # 煞星落宫
    sha = {s: _star_palace(chart, s) for s in SHA_STARS}

    # 压力叠加：忌 +2（生年/大限/流年），煞在本宫 +1，冲照（对宫+三合两宫）各 +0.5
    press = {i: {"忌": 0.0, "煞": 0.0} for i in range(12)}
    for p in (sheng_ji_p, daxian_ji_p, liunian_ji_p):
        if p is not None:
            press[p]["忌"] += 2.0
    for s, p in sha.items():
        if p is None:
            continue
        press[p]["煞"] += 1.0
        for q in zhiwei.sanfang_sizheng(p)[1:]:  # 对宫 + 三合两宫
            press[q]["煞"] += 0.5

    rows = []
    for i in range(12):
        p = chart["十二宫"][i]
        total = press[i]["忌"] + press[i]["煞"]
        label = "高压" if total >= 4 else ("中压" if total >= 2 else ("低压" if total >= 1 else "无"))
        rows.append({"宫": p["宫"], "支": p["支"], "忌": press[i]["忌"], "煞": press[i]["煞"],
                     "压力": round(total, 1), "档": label,
                     "命": p["命"], "身": p["身"], "重点": p["宫"] in KEY_PALACES})
    rows.sort(key=lambda r: -r["压力"])

    return {
        "出生": f"{sy}-{sm:02d}-{sd:02d}", "性别": "男" if gender else "女",
        "虚岁": xusui, "流年": f"{liunian_gan}{liunian_zhi}",
        "生年忌": {"星": sheng_ji, "宫": chart["十二宫"][sheng_ji_p]["宫"] if sheng_ji_p is not None else "—"},
        "大限": {"宫": chart["十二宫"][daxian_p]["宫"] if daxian_p is not None else "—",
                "宫干": daxian_gan or "—", "忌星": daxian_ji or "—",
                "飞入": chart["十二宫"][daxian_ji_p]["宫"] if daxian_ji_p is not None else "—"},
        "流年忌": {"星": liunian_ji, "宫": chart["十二宫"][liunian_ji_p]["宫"] if liunian_ji_p is not None else "—"},
        "煞星": {s: (chart["十二宫"][p]["宫"] if p is not None else "—") for s, p in sha.items()},
        "热力表": rows,
    }


def format_scan(r):
    """格式化输出叠冲扫描结果。"""
    L = []
    L.append(f"[紫微流年叠冲] {r['出生']}({r['性别']})  流年 {r['流年']}（虚岁{r['虚岁']}）")
    L.append(f"  生年化忌: {r['生年忌']['星']} → {r['生年忌']['宫']}")
    L.append(f"  大限化忌: {r['大限']['宫']}(干{r['大限']['宫干']}) 忌{r['大限']['忌星']} → {r['大限']['飞入']}")
    L.append(f"  流年化忌: {r['流年忌']['星']} → {r['流年忌']['宫']}")
    L.append(f"  六煞落宫: " + "  ".join(f"{s}{p}" for s, p in r['煞星'].items()))
    L.append("  压力热力表（忌+2/煞在本宫+1/煞冲照+0.5）:")
    for row in r["热力表"]:
        tag = []
        if row["命"]:
            tag.append("命")
        if row["身"]:
            tag.append("身")
        if row["重点"] and not row["命"] and not row["身"]:
            tag.append("重点")
        bar = "█" * int(round(row["压力"]))
        mark = f"[{'·'.join(tag)}]" if tag else ""
        L.append(f"    {row['宫']:<5}{row['支']}  忌{row['忌']:.0f} 煞{row['煞']:.1f}  {row['压力']:>4} {row['档']:<3} {bar} {mark}")
    top = r["热力表"][0]
    L.append(f"  → 本年压力最重：{top['宫']}（{top['档']}，压力{top['压力']}）")
    L.append(f"  〔出处{SRC}·化忌入命/入限诀「诸星化忌不宜逢，更会凶星愈肆凶」；叠冲热力为[规则推演]〕")
    return "\n".join(L)


if __name__ == "__main__":
    import sys
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print(format_scan(diji_scan(1990, 5, 15, 8, 1, 2026)))
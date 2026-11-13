# -*- coding: utf-8 -*-
"""紫微「入限诀」：星曜入大限（二限）的吉凶断语，限运 DSL 收口。

《紫微斗数全书》卷一「诸星问答论」每颗星曜的「歌曰」段里，有「二限若遇帝，喜气自然新」
「二限临此宿，事必有变更」等「入限」断语——星曜行入大限（二限）时的吉凶，与「入命/落宫」
断语分开。本模块把「入限诀」结构化 + 做成限运 DSL 判定：

- 数据 `XIAN_JU`：10 颗主星的「二限」断语（紫微/天机/太阳/武曲/天同/廉贞/贪狼/巨门/天相/七杀）。
- 判定 `find_xian(chart)`：遍历十二宫，凡某宫带「大限」岁数且宫内坐入限主星，输出
  「某星入某大限（某岁起）→ 断语」，供断大限吉凶引用。
- 限运 DSL 本质：把「大限宫」作为盘面维度——`zhiwei.cast` 已算每宫大限（`p["大限"]=(起,止)`），
  本模块只读它 + 查入限断语，不重算限运。

诚实边界：天府/太阴/天梁/破军 4 颗主星的「歌曰」原文无「二限/限」句，如实标注不在 XIAN_JU；
断语是「吉凶倾向」而非铁断，断卦仍按星名 Grep《紫微斗数全书》原文佐证。

用法：
  from judge.ziwei_xian import XIAN_JU, find_xian
  r = find_xian(zhiwei.cast(...)["十二宫"] 或 chart)
"""
import sys
import os

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass

SRC = "《紫微斗数全书》卷一·诸星问答论"

# 星名 -> (原文入限断语, 吉凶倾向)
XIAN_JU = {
    "紫微": ("二限若遇帝，喜气自然新", "吉"),
    "天机": ("二限临此宿，事必有变更", "中"),
    "太阳": ("二限若值此，必定卖田园", "凶"),
    "武曲": ("若与破军同位，更临二限之中，定主是非之挠", "凶"),
    "天同": ("限若逢之，一生得地", "吉"),
    "廉贞": ("限逢至此，灾不可攘", "凶"),
    "贪狼": ("二限为祸非轻", "凶"),
    "巨门": ("限逢凶曜灾难不轻", "凶"),
    "天相": ("二限若逢之，百事看充足", "吉"),
    "七杀": ("二限逢之遭殃破败", "凶"),
}

# 原文歌诀无「二限/限」句的主星（如实标注，不做入限判定）
_NO_XIAN_JU = ["天府", "太阴", "天梁", "破军"]


def find_xian(chart):
    """遍历十二宫，凡带大限岁数且宫内坐入限主星，返回入限断语列表。

    chart：zhiwei.cast 的返回 dict（含 "十二宫"），或 GejuAdapter 用的 chart。
    每宫 p = {"宫":宫名, "支":地支, "主星":[(星,庙旺,四化)], "辅星":[..], "大限":(起,止)或None}。
    返回 [{宫, 地支, 大限起, 大限止, 星, 断语, 吉凶, 出处}]，按大限起岁升序。
    """
    palaces = chart["十二宫"] if "十二宫" in chart else chart
    out = []
    for p in palaces:
        dx = p.get("大限")
        if not dx:
            continue
        for star, _b, _s in p["主星"]:
            if star in XIAN_JU:
                text, jx = XIAN_JU[star]
                out.append({"宫": p["宫"], "地支": p["支"],
                            "大限起": dx[0], "大限止": dx[1],
                            "星": star, "断语": text, "吉凶": jx, "出处": SRC})
    out.sort(key=lambda x: x["大限起"])
    return out


def _fmt(r):
    if not r:
        return "（无主星入限诀命中，或本命无正曜入限）"
    lines = ["🔬 入限诀（星曜入大限吉凶）"]
    for x in r:
        lines.append(f"  {x['大限起']:>2}-{x['大限止']:<2}岁 {x['宫']}({x['地支']}) {x['星']}〔{x['吉凶']}〕 {x['断语']}")
    lines.append(f"  〔出处 {SRC}，断卦按星名 Grep 原文佐证〕")
    return "\n".join(lines)


def main():
    a = sys.argv[1:]
    if len(a) < 4:
        print(__doc__)
        return
    from pan import zhiwei
    y, m, d, h = int(a[0]), int(a[1]), int(a[2]), int(a[3])
    g = int(a[4]) if len(a) > 4 else 1
    r = zhiwei.cast(y, m, d, h, g)
    print(_fmt(find_xian(r)))


if __name__ == "__main__":
    main()

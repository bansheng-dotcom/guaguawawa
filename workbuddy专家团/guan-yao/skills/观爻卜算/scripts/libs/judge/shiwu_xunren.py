# -*- coding: utf-8 -*-
"""失物·寻人·寻宠 结构化规则引擎（小六壬 / 六爻纳甲 / 金口诀）。

把三术的失物寻人断法落成可判定、可回归的规则函数，供「失物·寻人」断卦优先调用；
原文仍由 Grep 佐证。

覆盖：
  小六壬：六宫口诀自带「失物方位 + 远近 + 能否寻回」
  六爻纳甲：失物看财爻、官鬼为贼、子孙为捕捉；卦宫定方位、财爻入墓定藏处、
            内外卦定远近、财空动/鬼动定能否与是否被盗（《火珠林·占逃亡/失物/贼盗》）
  金口诀：四孟值课为遗失、四仲交易、四季婚姻；上克下寻人在家（《六壬神课金口诀古本》）

原则：失物寻人同样「降分辨率给候选」，方位/远近/能否/被盗分维输出，不铁口直断。
每条返回 {result, confidence, evidence, basis}，evidence 编号 R-SW-01~05。

用法：
  from judge.shiwu_xunren import xiaoliuren_shiwu, liuyao_shiwu_duan, liuyao_shiwu_fangwei, \
      liuyao_shiwu_cangchu, jinkoujue_shiwu, portrait_shiwu
"""

SOURCE_XLR = "《小六壬》"
SOURCE_HZL = "《火珠林》"
SOURCE_JKJ = "《六壬神课金口诀古本》"


def _r(result, conf, ev, basis):
    return {"result": result, "confidence": conf, "evidence": ev, "basis": basis}


# —— 小六壬：六宫失物方位/远近/能否 ——
_XLR_SHIWU = {
    "大安": ("东方", "去不远（在家/原处附近）", "易寻", "安稳未动、在常放处"),
    "留连": ("南方", "已移动、拖延", "难寻（急寻方明）", "纠缠不明、防口舌"),
    "速喜": ("西南（申未午）", "已出、需打听", "可寻（逢人打听）", "快而喜、有音信"),
    "赤口": ("西方", "需急寻", "难寻（口舌）", "口舌凶险、恐染瘟殃"),
    "小吉": ("西南（坤方）", "未远、路上", "可寻（阴人报喜）", "和合、行人立至"),
    "空亡": ("—", "已失", "寻不见", "落空、无果"),
}


def xiaoliuren_shiwu(gong):
    """小六壬失物/寻物：六宫 → 方位/远近/能否/状态。R-SW-01"""
    row = _XLR_SHIWU.get(gong)
    if not row:
        return _r(None, "低", "R-SW-01", f"落宫「{gong}」无失物映射")
    fang, yuanjin, nengfou, zhuangtai = row
    return _r(f"方位{fang}；{yuanjin}；{nengfou}（{zhuangtai}）", "高", "R-SW-01",
              f"落宫「{gong}」→ 失物在{fang}、{yuanjin}、{nengfou}（{SOURCE_XLR}·六宫口诀，断卦 Grep 宫名原文佐证）")


# —— 六爻：卦宫方位 + 财爻入墓藏处 ——
_GONG_FANGWEI = {"乾": "西北", "坤": "西南", "震": "东", "巽": "东南",
                 "坎": "北", "离": "南", "艮": "东北", "兑": "西"}


def liuyao_shiwu_fangwei(gong):
    """六爻失物方位：用神所在卦宫 → 八方。R-SW-02"""
    fw = _GONG_FANGWEI.get(gong)
    if not fw:
        return _r(None, "低", "R-SW-02", f"卦宫「{gong}」无方位映射")
    return _r(fw, "高", "R-SW-02",
              f"用神卦宫「{gong}」→ {fw}（{SOURCE_HZL}·占逃亡方位「世宫为方」，断卦 Grep 卦名原文佐证）")


# 财爻入墓藏处（五行 → 墓库方位）
_RU_MU = {"金": "丑（东北）", "水": "辰（东南）", "土": "辰（东南）",
          "木": "未（西南）", "火": "戌（西北）"}


def liuyao_shiwu_cangchu(cai_wx):
    """六爻失物藏处：财爻五行入墓 → 藏处方位。R-SW-03"""
    ch = _RU_MU.get(cai_wx)
    if not ch:
        return _r(None, "低", "R-SW-03", f"财爻五行「{cai_wx}」无入墓映射")
    return _r(ch, "高", "R-SW-03",
              f"财爻属{cai_wx}入墓 → 藏{ch}（{SOURCE_HZL}「丑东北辰东南未西南戌西北」，断卦 Grep 原文佐证）")


def _has(s, *keys):
    """关键词匹配，跳过「不X/未X/没X/非X」否定式（如「不空不动」不命中「空/动」）。"""
    import re
    s = str(s)
    return any(re.search(r"(?<![不未没非])" + re.escape(k), s) for k in keys)


def liuyao_shiwu_duan(cai="", gui="", zisun="", gong=""):
    """六爻失物综合断：能否寻回 / 远近 / 是否被盗 / 贼获应期 / 方位。R-SW-04
    cai/gui/zisun 为财爻/官鬼/子孙爻状态描述（可含 旺/相/空/动/伏/内卦/外卦/静/无气/克世/刑世 等），
    否定式（不空/不动/未动）自动跳过；gong 为用神所在卦宫。"""
    parts = []
    # 能否寻回
    if _has(cai, "空", "动") or _has(cai, "无气", "休囚", "死"):
        parts.append("财爻空/动/无气 → 物已出屋，难寻")
    elif _has(cai, "伏"):
        parts.append("财爻伏藏 → 按所伏爻之宫寻，较难")
    elif _has(cai, "旺", "相"):
        parts.append("财爻旺相不空不动 → 可见可寻")
    # 远近
    if _has(cai, "内卦"):
        parts.append("财在内卦 → 物未出家，在家中原处")
    elif _has(cai, "外卦"):
        parts.append("财在外卦 → 物已出外、转移")
    # 是否被盗
    if _has(gui, "无鬼", "安静"):
        parts.append("六爻无鬼/鬼安静 → 非贼偷，自失")
    elif _has(gui, "动", "化鬼", "克世", "刑世"):
        parts.append("官鬼动/克世 → 被盗（贼象，防再失）")
    if _has(gui, "空"):
        parts.append("鬼爻空 → 贼难觅、或寻不见")
    # 贼获应期
    if _has(zisun, "旺"):
        parts.append("子孙旺 → 贼可获、物可追（应子孙旺日）")
    elif _has(zisun, "空", "无气"):
        parts.append("子孙空/无气 → 贼难获")
    # 方位
    fw = _GONG_FANGWEI.get(gong)
    if fw:
        parts.append(f"用神卦宫「{gong}」→ 方位{fw}")
    if not parts:
        return _r(None, "低", "R-SW-04", "财爻/官鬼/子孙状态未给，失物难断")
    return _r("；".join(parts), "高", "R-SW-04",
              f"失物断：{'；'.join(parts)}（{SOURCE_HZL}·占失物/贼盗，断卦 Grep 原文佐证）")


# —— 金口诀：四孟遗失 / 四仲交易 / 四季婚姻 + 寻人在家 ——
_SI_MENG = "寅申巳亥"
_SI_ZHONG = "子午卯酉"
_SI_JI = "辰戌丑未"


def jinkoujue_shiwu(zhi):
    """金口诀失物/来意：课值四孟为遗失、四仲为交易、四季为婚姻。R-SW-05
    zhi 为四位中起关键作用之地支（或用爻支/地分）。"""
    if zhi in _SI_MENG:
        return _r("四孟值课为遗失（失物/寻物）", "高", "R-SW-05",
                  f"课值四孟（{zhi}）→ 遗失/失物（{SOURCE_JKJ}「四孟值课为遗失」，断卦 Grep 原文佐证）")
    if zhi in _SI_ZHONG:
        return _r("四仲来人问交易（行人/交易）", "高", "R-SW-05",
                  f"课值四仲（{zhi}）→ 交易/行人（{SOURCE_JKJ}「四仲来人问交易」）")
    if zhi in _SI_JI:
        return _r("四季（婚姻/出身）", "高", "R-SW-05",
                  f"课值四季（{zhi}）→ 婚姻/出身（{SOURCE_JKJ}「四季非问婚姻而问出身」）")
    return _r(None, "低", "R-SW-05", f"支「{zhi}」非孟仲季，难定事类")


def jinkoujue_xunren(ke_shangke):
    """金口诀寻人：上克下寻人在家、下克上人在外。R-SW-05"""
    if "上克下" in str(ke_shangke):
        return _r("寻人在家（上克下）", "高", "R-SW-05",
                  f"上克下 → 寻人在家（{SOURCE_JKJ}「占人人在家」）")
    return _r(None, "低", "R-SW-05", "非上克下，寻人方位另按神煞/方位断")


# —— 聚合画像 ——
def portrait_shiwu(术, **kw):
    """失物寻人画像聚合。术 ∈ {xiaoliuren, liuyao, jinkoujue}。"""
    if 术 == "xiaoliuren":
        return {"失物": xiaoliuren_shiwu(kw.get("落宫", ""))}
    if 术 == "liuyao":
        gong = kw.get("卦宫", "")
        return {
            "综合断": liuyao_shiwu_duan(kw.get("财爻", ""), kw.get("官鬼", ""), kw.get("子孙", ""), gong),
            "方位": liuyao_shiwu_fangwei(gong),
            "藏处": liuyao_shiwu_cangchu(kw.get("财爻五行", "")) if kw.get("财爻五行") else None,
        }
    if 术 == "jinkoujue":
        zhi = kw.get("地支", "")
        return {"事类": jinkoujue_shiwu(zhi), "寻人": jinkoujue_xunren(kw.get("生克", ""))}
    return {}


def _fmt(p):
    """失物寻人画像输出（降分辨率，分维 + 置信度，不铁口直断）。"""
    lines = ["🔍 失物寻人画像（降分辨率，不铁口直断）"]
    for k, v in p.items():
        if v and isinstance(v, dict) and v.get("result"):
            lines.append(f"  {k}  [{v['confidence']}] {v['result']}")
    lines.append("  诚实边界：方位为八卦/落宫粗指，非精确坐标；具体何日找回、是否必在某处不作铁断。")
    return "\n".join(lines)


def main():
    import sys
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    shu = a[0]
    if shu == "xiaoliuren":
        print(_fmt(portrait_shiwu("xiaoliuren", 落宫=a[1] if len(a) > 1 else "")))
    elif shu == "jinkoujue":
        print(_fmt(portrait_shiwu("jinkoujue", 地支=a[1] if len(a) > 1 else "",
                                  生克=a[2] if len(a) > 2 else "")))
    elif shu == "liuyao":
        # liuyao <卦宫> <财爻状态> <官鬼状态> [子孙状态] [财爻五行]
        gong = a[1] if len(a) > 1 else ""
        cai = a[2] if len(a) > 2 else ""
        gui = a[3] if len(a) > 3 else ""
        zisun = a[4] if len(a) > 4 else ""
        cai_wx = a[5] if len(a) > 5 else ""
        p = {"综合断": liuyao_shiwu_duan(cai, gui, zisun, gong),
             "方位": liuyao_shiwu_fangwei(gong) if gong else None,
             "藏处": liuyao_shiwu_cangchu(cai_wx) if cai_wx else None}
        print(_fmt(p))


if __name__ == "__main__":
    main()
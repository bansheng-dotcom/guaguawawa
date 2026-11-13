# -*- coding: utf-8 -*-
"""八字地支刑冲合害分析模块。

来源：dglijin-oss/chinese-metaphysics-skills `bazi-pan-skill/scripts/xing_chong_he_hai.py`（MIT）。
覆盖：六合 / 六冲 / 三合 / 半三合 / 三刑（无恩·恃势·无礼·自刑）/ 六害 / 相破，
支持四柱内部关系 + 流年对四柱的合冲害破交叉。

用法：
  from xingchong import analyze, from_eightchar, format_output
  zhi = from_eightchar(eight_char)                 # -> [年支, 月支, 日支, 时支]
  result = analyze(zhi, liu_nian_zhi='午')         # 流年地支可选
  print(format_output(result))
"""
from collections import Counter
from typing import Dict, List, Optional

# 地支五行 / 藏干
ZHI_WUXING = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

LIU_HE = {"子": "丑", "丑": "子", "寅": "亥", "亥": "寅", "卯": "戌", "戌": "卯",
          "辰": "酉", "酉": "辰", "巳": "申", "申": "巳", "午": "未", "未": "午"}
LIU_HE_MEANING = {
    ("子", "丑"): "子丑合土：智慧与包容相结合，利合作、婚姻",
    ("寅", "亥"): "寅亥合木：生机与滋养相合，利学业、发展",
    ("卯", "戌"): "卯戌合火：温柔与热情相合，利感情、社交",
    ("辰", "酉"): "辰酉合金：稳重与精明相合，利财运、事业",
    ("巳", "申"): "巳申合水：变化与灵活相合，利变动、创新",
    ("午", "未"): "午未合土：光明与包容相合，利名利、稳定",
}

LIU_CHONG = {"子": "午", "午": "子", "丑": "未", "未": "丑", "寅": "申", "申": "寅",
             "卯": "酉", "酉": "卯", "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳"}
LIU_CHONG_MEANING = {
    ("子", "午"): "子午冲：水火相冲，主变动、冲突、情绪波动",
    ("丑", "未"): "丑未冲：土土相冲，主内部矛盾、家庭纠纷",
    ("寅", "申"): "寅申冲：金木相冲，主出行变动、事业转折",
    ("卯", "酉"): "卯酉冲：金木相冲，主感情波折、口舌是非",
    ("辰", "戌"): "辰戌冲：土土相冲，主地产变动、居所迁移",
    ("巳", "亥"): "巳亥冲：水火相冲，主思想冲突、远行之象",
}

SAN_HE = {
    "申子辰": {"局": "水局", "五行": "水", "含义": "智慧流通，人脉广泛"},
    "亥卯未": {"局": "木局", "五行": "木", "含义": "生机旺盛，利成长发展"},
    "寅午戌": {"局": "火局", "五行": "火", "含义": "热情高涨，利名声事业"},
    "巳酉丑": {"局": "金局", "五行": "金", "含义": "刚毅果断，利财富积累"},
}

BAN_SAN_HE = {
    "申辰": {"局": "水局（拱）", "五行": "水", "含义": "水气暗聚，待机而发"},
    "亥未": {"局": "木局（拱）", "五行": "木", "含义": "木气暗聚，蓄势待发"},
    "寅戌": {"局": "火局（拱）", "五行": "火", "含义": "火气暗聚，伺机而动"},
    "巳丑": {"局": "金局（拱）", "五行": "金", "含义": "金气暗聚，隐忍待发"},
    "申子": {"局": "水局（半合）", "五行": "水", "含义": "水气渐旺，智慧增长"},
    "亥卯": {"局": "木局（半合）", "五行": "木", "含义": "木气渐旺，生机勃发"},
    "寅午": {"局": "火局（半合）", "五行": "火", "含义": "火气渐旺，热情上升"},
    "巳酉": {"局": "金局（半合）", "五行": "金", "含义": "金气渐旺，锐气渐增"},
    "子辰": {"局": "水局（半合）", "五行": "水", "含义": "水气收敛，蓄势内敛"},
    "卯未": {"局": "木局（半合）", "五行": "木", "含义": "木气收敛，根深蒂固"},
    "午戌": {"局": "火局（半合）", "五行": "火", "含义": "火气收敛，内敛含蓄"},
    "酉丑": {"局": "金局（半合）", "五行": "金", "含义": "金气收敛，精打细算"},
}

SAN_XING = {
    "寅巳申": {"类型": "无恩之刑", "含义": "忘恩负义，恩将仇报，人际关系复杂"},
    "丑戌未": {"类型": "恃势之刑", "含义": "仗势欺人，自以为是，易招是非"},
    "子卯": {"类型": "无礼之刑", "含义": "无礼粗鲁，缺乏修养，感情不顺"},
    "辰辰": {"类型": "自刑", "含义": "自我纠结，内心矛盾，自作自受"},
    "午午": {"类型": "自刑", "含义": "自我纠结，急躁冲动，自寻烦恼"},
    "酉酉": {"类型": "自刑", "含义": "自我纠结，过于挑剔，自困自缚"},
    "亥亥": {"类型": "自刑", "含义": "自我纠结，消极悲观，自我封闭"},
}

LIU_HAI = {"子": "未", "未": "子", "丑": "午", "午": "丑", "寅": "巳", "巳": "寅",
           "卯": "辰", "辰": "卯", "申": "亥", "亥": "申", "酉": "戌", "戌": "酉"}
LIU_HAI_MEANING = {
    ("子", "未"): "子未害：骨肉相害，亲情不和",
    ("丑", "午"): "丑午害：暗中相害，小人作祟",
    ("寅", "巳"): "寅巳害：口舌是非，意见不合",
    ("卯", "辰"): "卯辰害：暗藏危机，防小人暗算",
    ("申", "亥"): "申亥害：谋事难成，多劳少获",
    ("酉", "戌"): "酉戌害：嫉妒猜疑，感情不和",
}

XIANG_PO = {"子": "酉", "酉": "子", "丑": "辰", "辰": "丑", "寅": "亥", "亥": "寅",
            "卯": "午", "午": "卯", "巳": "申", "申": "巳", "未": "戌", "戌": "未"}
XIANG_PO_MEANING = {
    ("子", "酉"): "子酉破：破财之象，谨防损失",
    ("丑", "辰"): "丑辰破：内部不和，合作破裂",
    ("寅", "亥"): "寅亥破：先合后破，事与愿违",
    ("卯", "午"): "卯午破：感情波动，情绪不稳",
    ("巳", "申"): "巳申破：合中带破，好事多磨",
    ("未", "戌"): "未戌破：土破之象，根基动摇",
}

_POS = ["年", "月", "日", "时"]

# 天干五合 / 天干相克（用于流年、合婚的干干比对）
GAN_HE = {"甲": "己", "己": "甲", "乙": "庚", "庚": "乙", "丙": "辛", "辛": "丙",
          "丁": "壬", "壬": "丁", "戊": "癸", "癸": "戊"}
GAN_HE_MEANING = {"甲": "甲己合化土", "己": "甲己合化土", "乙": "乙庚合化金", "庚": "乙庚合化金",
                  "丙": "丙辛合化水", "辛": "丙辛合化水", "丁": "丁壬合化木", "壬": "丁壬合化木",
                  "戊": "戊癸合化火", "癸": "戊癸合化火"}
GAN_KE = {"甲": "戊", "乙": "己", "丙": "庚", "丁": "辛", "戊": "壬",
          "己": "癸", "庚": "甲", "辛": "乙", "壬": "丙", "癸": "丁"}


def _meaning(table, a, b):
    return table.get((a, b)) or table.get((b, a)) or ""


def zhi_relation(z1, z2):
    """两两地支关系（可同时命中多条，如巳申既六合又相破、寅巳既相刑又六害）。
    返回 {关系列表:[{关系,含义,吉凶}], 主关系, 吉凶}。"""
    rels = []
    if LIU_HE.get(z1) == z2:
        rels.append({"关系": "六合", "含义": _meaning(LIU_HE_MEANING, z1, z2), "吉凶": "吉"})
    if LIU_CHONG.get(z1) == z2:
        rels.append({"关系": "六冲", "含义": _meaning(LIU_CHONG_MEANING, z1, z2), "吉凶": "凶"})
    if LIU_HAI.get(z1) == z2:
        rels.append({"关系": "六害", "含义": _meaning(LIU_HAI_MEANING, z1, z2), "吉凶": "凶"})
    if XIANG_PO.get(z1) == z2:
        rels.append({"关系": "相破", "含义": _meaning(XIANG_PO_MEANING, z1, z2), "吉凶": "凶"})
    for combo, info in BAN_SAN_HE.items():
        if (z1 + z2 == combo) or (z2 + z1 == combo):
            rels.append({"关系": "半三合", "含义": info["含义"], "吉凶": "半吉"})
            break
    if z1 == z2 and z1 in "辰午酉亥":
        rels.append({"关系": "自刑", "含义": SAN_XING[z1 + z1]["含义"], "吉凶": "凶"})
    elif (z1 == "子" and z2 == "卯") or (z1 == "卯" and z2 == "子"):
        rels.append({"关系": "无礼之刑", "含义": SAN_XING["子卯"]["含义"], "吉凶": "凶"})
    elif {z1, z2} <= set("寅巳申"):
        rels.append({"关系": "无恩之刑（二刑）", "含义": "潜在刑伤，流年逢之则发", "吉凶": "半凶"})
    elif {z1, z2} <= set("丑戌未"):
        rels.append({"关系": "恃势之刑（二刑）", "含义": "潜在是非，流年逢之则发", "吉凶": "半凶"})
    if not rels:
        return {"关系列表": [], "主关系": "平", "吉凶": "中"}
    order = ["六冲", "自刑", "无礼之刑", "无恩之刑（二刑）", "恃势之刑（二刑）",
             "六害", "相破", "六合", "半三合"]
    main = rels[0]["关系"]
    for o in order:
        if any(r["关系"] == o for r in rels):
            main = o
            break
    if any(r["吉凶"] == "凶" for r in rels):
        jx = "凶"
    elif any(r["吉凶"] == "半凶" for r in rels):
        jx = "半凶"
    elif any(r["吉凶"] == "吉" for r in rels):
        jx = "吉"
    else:
        jx = "半吉"
    return {"关系列表": rels, "主关系": main, "吉凶": jx}


def gan_relation(g1, g2):
    """两天干关系（五合 / 相克 / 平）。返回 {关系, 含义, 吉凶}。"""
    if GAN_HE.get(g1) == g2:
        return {"关系": "五合", "含义": GAN_HE_MEANING[g1], "吉凶": "吉"}
    if GAN_KE.get(g1) == g2:
        return {"关系": "相克", "含义": f"{g1}克{g2}", "吉凶": "凶"}
    return {"关系": "平", "含义": f"{g1}{g2}无合无克", "吉凶": "中"}


class XingChongHeHai:
    """刑冲合害分析器"""

    @classmethod
    def analyze(cls, si_zhu_zhi: List[str], da_yun_zhi: Optional[List[str]] = None,
                liu_nian_zhi: Optional[str] = None) -> Dict:
        result = {"六合": [], "六冲": [], "三合": [], "半三合": [], "三刑": [],
                  "六害": [], "相破": [], "综合判断": "", "建议": []}

        # —— 四柱内部两两关系 ——
        zhi_set = set(si_zhu_zhi)
        cnt = Counter(si_zhu_zhi)
        seen = set()
        for i in range(len(si_zhu_zhi)):
            for j in range(i + 1, len(si_zhu_zhi)):
                a, b = si_zhu_zhi[i], si_zhu_zhi[j]
                pair = tuple(sorted([a, b]))
                if pair in seen:
                    continue
                seen.add(pair)
                pos = f"{_POS[i]}-{_POS[j]}"
                if LIU_HE.get(a) == b:
                    result["六合"].append({"关系": f"{a}{b}六合", "位置": pos,
                                           "含义": _meaning(LIU_HE_MEANING, a, b), "吉凶": "吉"})
                if LIU_CHONG.get(a) == b:
                    result["六冲"].append({"关系": f"{a}{b}相冲", "位置": pos,
                                           "含义": _meaning(LIU_CHONG_MEANING, a, b), "吉凶": "凶"})
                if LIU_HAI.get(a) == b:
                    result["六害"].append({"关系": f"{a}{b}相害", "位置": pos,
                                           "含义": _meaning(LIU_HAI_MEANING, a, b), "吉凶": "凶"})
                if XIANG_PO.get(a) == b:
                    result["相破"].append({"关系": f"{a}{b}相破", "位置": pos,
                                           "含义": _meaning(XIANG_PO_MEANING, a, b), "吉凶": "凶"})

        # —— 三合 / 半三合 ——
        for combo, info in SAN_HE.items():
            if all(z in zhi_set for z in combo):
                result["三合"].append({"关系": f"{combo}三合{info['局']}", "位置": "四柱中",
                                       "五行": info["五行"], "含义": info["含义"], "吉凶": "吉"})
        for combo, info in BAN_SAN_HE.items():
            if all(z in zhi_set for z in combo):
                result["半三合"].append({"关系": f"{combo}{info['局']}", "位置": "四柱中",
                                         "五行": info["五行"], "含义": info["含义"], "吉凶": "半吉"})

        # —— 三刑 ——
        if all(z in zhi_set for z in "寅巳申"):
            result["三刑"].append({"关系": "寅巳申三刑", "类型": "无恩之刑",
                                   "含义": SAN_XING["寅巳申"]["含义"], "吉凶": "凶"})
        elif sum(1 for z in "寅巳申" if z in zhi_set) == 2:
            result["三刑"].append({"关系": "寅巳申二刑（不全）", "类型": "无恩之刑（缺位）",
                                   "含义": "潜在刑伤，流年逢之则发", "吉凶": "半凶"})
        if all(z in zhi_set for z in "丑戌未"):
            result["三刑"].append({"关系": "丑戌未三刑", "类型": "恃势之刑",
                                   "含义": SAN_XING["丑戌未"]["含义"], "吉凶": "凶"})
        elif sum(1 for z in "丑戌未" if z in zhi_set) == 2:
            result["三刑"].append({"关系": "丑戌未二刑（不全）", "类型": "恃势之刑（缺位）",
                                   "含义": "潜在是非，流年逢之则发", "吉凶": "半凶"})
        if "子" in zhi_set and "卯" in zhi_set:
            result["三刑"].append({"关系": "子卯相刑", "类型": "无礼之刑",
                                   "含义": SAN_XING["子卯"]["含义"], "吉凶": "凶"})
        for self_xing in "辰午酉亥":
            if cnt.get(self_xing, 0) >= 2:
                result["三刑"].append({"关系": f"{self_xing}{self_xing}自刑", "类型": "自刑",
                                       "含义": SAN_XING[f"{self_xing}{self_xing}"]["含义"], "吉凶": "凶"})

        # —— 流年交叉（合/冲/害/破） ——
        if liu_nian_zhi:
            for i, z in enumerate(si_zhu_zhi):
                if LIU_HE.get(z) == liu_nian_zhi:
                    result["六合"].append({"关系": f"流年{liu_nian_zhi}与{_POS[i]}支{z}六合",
                                           "位置": f"流年+{_POS[i]}支",
                                           "含义": _meaning(LIU_HE_MEANING, z, liu_nian_zhi), "吉凶": "吉"})
                if LIU_CHONG.get(z) == liu_nian_zhi:
                    result["六冲"].append({"关系": f"流年{liu_nian_zhi}冲{_POS[i]}支{z}",
                                           "位置": f"流年+{_POS[i]}支",
                                           "含义": _meaning(LIU_CHONG_MEANING, z, liu_nian_zhi),
                                           "吉凶": "凶", "注意": f"{_POS[i]}柱对应领域需特别注意"})
                if LIU_HAI.get(z) == liu_nian_zhi:
                    result["六害"].append({"关系": f"流年{liu_nian_zhi}害{_POS[i]}支{z}",
                                           "位置": f"流年+{_POS[i]}支",
                                           "含义": _meaning(LIU_HAI_MEANING, z, liu_nian_zhi), "吉凶": "凶"})
                if XIANG_PO.get(z) == liu_nian_zhi:
                    result["相破"].append({"关系": f"流年{liu_nian_zhi}破{_POS[i]}支{z}",
                                           "位置": f"流年+{_POS[i]}支",
                                           "含义": _meaning(XIANG_PO_MEANING, z, liu_nian_zhi), "吉凶": "凶"})

        # —— 大运交叉（合/冲/害/破） ——
        if da_yun_zhi:
            for z in da_yun_zhi:
                for i, zz in enumerate(si_zhu_zhi):
                    if LIU_HE.get(zz) == z:
                        result["六合"].append({"关系": f"大运{z}与{_POS[i]}支{zz}六合",
                                               "位置": f"大运+{_POS[i]}支",
                                               "含义": _meaning(LIU_HE_MEANING, zz, z), "吉凶": "吉"})
                    if LIU_CHONG.get(zz) == z:
                        result["六冲"].append({"关系": f"大运{z}冲{_POS[i]}支{zz}",
                                               "位置": f"大运+{_POS[i]}支",
                                               "含义": _meaning(LIU_CHONG_MEANING, zz, z),
                                               "吉凶": "凶", "注意": f"{_POS[i]}柱对应领域在大运需特别注意"})
                    if LIU_HAI.get(zz) == z:
                        result["六害"].append({"关系": f"大运{z}害{_POS[i]}支{zz}",
                                               "位置": f"大运+{_POS[i]}支",
                                               "含义": _meaning(LIU_HAI_MEANING, zz, z), "吉凶": "凶"})
                    if XIANG_PO.get(zz) == z:
                        result["相破"].append({"关系": f"大运{z}破{_POS[i]}支{zz}",
                                               "位置": f"大运+{_POS[i]}支",
                                               "含义": _meaning(XIANG_PO_MEANING, zz, z), "吉凶": "凶"})

        # —— 综合判断 ——
        judgments = []
        if any("日" in it.get("位置", "") for it in result["六冲"]):
            judgments.append("日支逢冲，婚姻感情需特别注意，易有变动")
        if any("日" in it.get("位置", "") for it in result["六合"]):
            judgments.append("日支逢合，感情和睦，人际和谐")
        if result["三合"]:
            judgments.append("三合局成（%s），气势强旺" % "、".join(it["五行"] for it in result["三合"]))
        if result["六合"]:
            judgments.append("命中有合（%d 组），人缘佳，贵人多" % len(result["六合"]))
        if result["六冲"]:
            judgments.append("命中有冲（%d 组），一生变动较多" % len(result["六冲"]))
        if result["三刑"]:
            judgments.append("命中带刑（%d 组），需谨慎处事" % len(result["三刑"]))
        if result["六害"]:
            judgments.append("命中带害（%d 组），人际关系需用心经营" % len(result["六害"]))
        if result["相破"]:
            judgments.append("命中带破（%d 组），防破损耗" % len(result["相破"]))
        if not judgments:
            judgments.append("命局平和，无明显刑冲合害，一生较为平稳")
        result["综合判断"] = "；".join(judgments) + "。"

        # —— 建议 ——
        advice = []
        if any("日" in it.get("位置", "") for it in result["六冲"]):
            advice.append("婚姻宫（日支）逢冲，宜晚婚，择偶需谨慎")
        if result["三合"]:
            advice.append("三合局成，可借势而为，发挥所长")
        if len(result["六冲"]) >= 2:
            advice.append("命局冲多，一生多变动，宜顺应时势")
        if result["三刑"]:
            advice.append("命局带刑，处事需谨慎，防小人暗算")
        if result["六害"]:
            advice.append("命局带害，人际关系需用心经营")
        if not advice:
            advice.append("命局和谐，顺势而为即可")
        result["建议"] = advice
        return result


def from_eightchar(b) -> List[str]:
    """从 lunar_python 的 EightChar 对象提取四柱地支。"""
    return [b.getYearZhi(), b.getMonthZhi(), b.getDayZhi(), b.getTimeZhi()]


def analyze(si_zhu_zhi: List[str], da_yun_zhi: Optional[List[str]] = None,
            liu_nian_zhi: Optional[str] = None) -> Dict:
    return XingChongHeHai.analyze(si_zhu_zhi, da_yun_zhi=da_yun_zhi, liu_nian_zhi=liu_nian_zhi)


def format_output(result: Dict, indent: str = "  ") -> str:
    lines = []
    sections = [
        ("六合", "◈ 六合（和谐之象）"),
        ("六冲", "◆ 六冲（变动之象）"),
        ("三合", "◈ 三合（气势之象）"),
        ("半三合", "◇ 半三合"),
        ("三刑", "⚡ 三刑（刑伤之象）"),
        ("六害", "⚠ 六害（不和之象）"),
        ("相破", "⚠ 相破（破损之象）"),
    ]
    has_any = False
    for key, label in sections:
        items = result.get(key, [])
        if items:
            has_any = True
            lines.append(f"{indent}{label}：")
            for it in items:
                meta = it.get("位置", "") or it.get("类型", "")
                tail = it.get("注意", "")
                meta_str = f"（{meta}）" if meta else ""
                tail_str = f"【{tail}】" if tail else ""
                lines.append(f"{indent}    {it['关系']}{meta_str} — {it['含义']}{tail_str}")
    if not has_any:
        lines.append(f"{indent}四柱地支无明显刑冲合害关系，命局平和。")
    lines.append(f"{indent}【综合】{result['综合判断']}")
    if result["建议"]:
        lines.append(f"{indent}【建议】")
        for a in result["建议"]:
            lines.append(f"{indent}  • {a}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    try:
        from lunar_python import Solar
    except Exception as e:
        print(f"缺少 lunar_python：{e}")
        sys.exit(1)
    b = Solar.fromYmdHms(2000, 1, 1, 8, 0, 0).getLunar().getEightChar()
    print("四柱", b.getYear(), b.getMonth(), b.getDay(), b.getTime())
    print(format_output(analyze(from_eightchar(b))))
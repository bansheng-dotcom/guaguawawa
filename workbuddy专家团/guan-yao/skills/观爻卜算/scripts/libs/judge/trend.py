# -*- coding: utf-8 -*-
"""八字流年趋势评分（扶抑·得令简化模型）—— 供流年趋势曲线可视化用。

诚实边界：这是 [规则推演/HEURISTIC] 的简化模型（日主得令定旺弱 → 扶抑定喜忌 → 流年干支五行生克打分），
只给「大运流年大方向的喜忌起伏」，**不是精确吉凶**。精确年份+具体生平的判断上限见 SKILL.md 第十五节（MingLi-Bench 36.2%）。

评分：
  旺 → 喜 克泄耗（官杀/食伤/财），忌 生扶（印/比劫）
  弱 → 喜 生扶（印/比劫），忌 克泄耗（官杀/食伤/财）
  每流年 干+支 各 ±1，总分 -2..+2 映射到 10/30/50/70/90。
"""
import datetime
from lunar_python import Solar
from pan import bazi
from judge import rules
_ZHI_WX = {"寅": "木", "卯": "木", "巳": "火", "午": "火", "申": "金", "酉": "金",
           "亥": "水", "子": "水", "辰": "土", "戌": "土", "丑": "土", "未": "土"}

# 关系（bazi._liunian_rel 前缀）-> 喜/忌（按旺弱）
_REL_KE_XIE_HAO = ("我生·食伤泄", "克我·官杀", "我克·财")   # 克泄耗
_REL_SHENG_FU = ("生我·印", "比和·比劫")                     # 生扶


def wang_ruo(day_gan, month_zhi):
    """日主旺弱（得令一维）。返回 '旺'/'弱'。"""
    return rules.bazi_deling(day_gan, month_zhi)["judgment"]


def _xi_ji(wang):
    """按旺弱返回 (喜关系集合, 忌关系集合)。"""
    if wang == "旺":
        return set(_REL_KE_XIE_HAO), set(_REL_SHENG_FU)
    return set(_REL_SHENG_FU), set(_REL_KE_XIE_HAO)


def liunian_trend(y, mo, d, gender=1, start=None, n=10):
    """流年趋势。返回 {day_gan, day_zhi, wang, data:[{year,gz,score,rel_gan,rel_zhi}]}。"""
    b = Solar.fromYmdHms(y, mo, d, 12, 0, 0).getLunar().getEightChar()
    day_gan, day_zhi = b.getDayGan(), b.getDayZhi()
    wx_day = bazi._WX5[day_gan]
    month_zhi = b.getMonthZhi()
    wang = wang_ruo(day_gan, month_zhi)
    xi, ji = _xi_ji(wang)
    start = start or datetime.datetime.now().year

    data = []
    for yr in range(start, start + n):
        gz = bazi._ganzhi_year(yr)
        g, z = gz[0], gz[1]
        rel_gan = bazi._liunian_rel(wx_day, bazi._WX5[g])
        rel_zhi = bazi._liunian_rel(wx_day, _ZHI_WX[z])
        score = 0
        for rel in (rel_gan, rel_zhi):
            if rel in xi:
                score += 1
            elif rel in ji:
                score -= 1
        s100 = 50 + score * 20
        data.append({"year": yr, "gz": gz, "score": s100,
                     "rel_gan": rel_gan, "rel_zhi": rel_zhi})
    return {"day_gan": day_gan, "day_zhi": day_zhi, "wang": wang,
            "start": start, "n": n, "data": data}


def format_trend(t):
    """文本输出（供 cast.py 打印或调试）。"""
    lines = [f"[八字流年趋势] 日主 {t['day_gan']}{t['day_zhi']}（{t['wang']}）  "
             f"{t['start']}~{t['start'] + t['n'] - 1} 年（扶抑·得令简化模型，仅示喜忌起伏）"]
    for d in t["data"]:
        bar = "█" * (d["score"] // 20)
        lines.append(f"  {d['year']} {d['gz']}  {d['score']:>3}分 {bar}  "
                     f"干{d['rel_gan']} 支{d['rel_zhi']}")
    return "\n".join(lines)
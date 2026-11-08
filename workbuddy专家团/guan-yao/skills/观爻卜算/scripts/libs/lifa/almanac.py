# -*- coding: utf-8 -*-
"""老黄历补全（彭祖百忌 / 每日值神 / 吉神凶煞 / 吉神方位 / 胎神 / 冲煞 / 宜忌）。

数据源：lunar_python（纯 Python，无 C 依赖，已在依赖清单内），其神煞宜忌以
《钦定协纪辨方书》《御定星历考原》为据。

定位：**结构化补全层** —— 给出确定性字段 + 出处指针。断卦/择日时仍须按出处
去典籍 txt 用 Grep 检索原文佐证（双重保证）；找不到原文就照实说明「依通书推演，
非直接引文」。

用法：
  from almanac import almanac, format_almanac
  a = almanac(2026, 10, 7)
  print(format_almanac(a))
"""
import datetime

try:
    from lunar_python import Lunar
    _HAS_LUNAR = True
except ImportError:  # pragma: no cover - 环境已装 lunar_python
    _HAS_LUNAR = False

# 出处统一指针（典籍库已有这两本 txt）
SOURCE_XJBFS = "《钦定协纪辨方书》"
SOURCE_XLK = "《御定星历考原》"


def almanac(year, month, day):
    """返回某日老黄历补全字段。lunar_python 不可用时返回可用=False 并说明。"""
    if not _HAS_LUNAR:
        return {"可用": False, "说明": "lunar_python 未安装，老黄历补全字段不可用"}

    l = Lunar.fromDate(datetime.datetime(year, month, day))

    return {
        "可用": True,
        "农历": l.toString(),
        "值神": {
            "值神": l.getDayTianShen(),
            "吉凶": l.getDayTianShenLuck(),
            "出处": f"{SOURCE_XJBFS}·十二值神（青龙明堂等）",
        },
        "彭祖百忌": {
            "日干": l.getPengZuGan(),
            "日支": l.getPengZuZhi(),
            "出处": f"{SOURCE_XJBFS}·彭祖百忌",
        },
        "吉神": {
            "神煞": l.getDayJiShen(),
            "出处": f"{SOURCE_XJBFS}·每日吉神",
        },
        "凶煞": {
            "神煞": l.getDayXiongSha(),
            "出处": f"{SOURCE_XJBFS}·每日凶煞",
        },
        "吉神方位": {
            "喜神": l.getDayPositionXiDesc(),
            "财神": l.getDayPositionCaiDesc(),
            "福神": l.getDayPositionFuDesc(),
            "阳贵": l.getDayPositionYangGuiDesc(),
            "阴贵": l.getDayPositionYinGuiDesc(),
            "出处": f"{SOURCE_XJBFS}·喜神/财神/福神/贵人方位",
        },
        "胎神": {
            "方位": l.getDayPositionTai(),
            "出处": f"{SOURCE_XJBFS}·胎神占方",
        },
        "冲煞": {
            "冲": l.getDayChongDesc(),
            "煞": l.getDaySha(),
            "出处": f"{SOURCE_XJBFS}·日冲/日煞",
        },
        "宜": {
            "事项": l.getDayYi(),
            "出处": f"{SOURCE_XJBFS}·宜忌",
        },
        "忌": {
            "事项": l.getDayJi(),
            "出处": f"{SOURCE_XJBFS}·宜忌",
        },
    }


def format_almanac(a):
    """格式化输出老黄历补全字段（返回字符串，供 cast.py 打印）。"""
    if not a.get("可用"):
        return a.get("说明", "")

    lines = [f"【老黄历补全】（{SOURCE_XJBFS} / {SOURCE_XLK}）"]
    lines.append(f"• 农历：{a['农历']}")
    lines.append(f"• 值神：{a['值神']['值神']}（{a['值神']['吉凶']}）")
    lines.append(f"• 彭祖百忌：{a['彭祖百忌']['日干']}；{a['彭祖百忌']['日支']}")

    if a["吉神"]["神煞"]:
        lines.append(f"• 吉神：{'、'.join(a['吉神']['神煞'])}")
    if a["凶煞"]["神煞"]:
        lines.append(f"• 凶煞：{'、'.join(a['凶煞']['神煞'])}")

    fw = a["吉神方位"]
    lines.append(
        f"• 吉神方位：喜神{fw['喜神']} 财神{fw['财神']} 福神{fw['福神']} "
        f"阳贵{fw['阳贵']} 阴贵{fw['阴贵']}"
    )
    lines.append(f"• 胎神：{a['胎神']['方位']}")
    lines.append(f"• 冲煞：冲{a['冲煞']['冲']} 煞{a['冲煞']['煞']}")

    if a["宜"]["事项"]:
        lines.append(f"• 宜：{'、'.join(a['宜']['事项'][:12])}")
    if a["忌"]["事项"]:
        lines.append(f"• 忌：{'、'.join(a['忌']['事项'][:12])}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    now = datetime.datetime.now()
    print(format_almanac(almanac(now.year, now.month, now.day)))
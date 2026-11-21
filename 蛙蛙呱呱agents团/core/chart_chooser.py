# -*- coding: utf-8 -*-
"""core.chart_chooser —— 按语义换图型，别让整本报告都是柱状图。

2026-11-21：用户一句「你就会柱状图啊」——升级引擎只让柱子变好看，没换过图型。
这里在契约层做一次选择：同一份 label/value 数据，能画成条形、点图、棒棒糖、
帕累托、占比条、矩形树图；按本节语义挑，并避免连续重复同一型。
"""
from __future__ import annotations

from typing import Any, Dict, List

BAR_LIKE = {"hbar", "vbar"}
ITEMS_OK = {"hbar", "vbar", "lollipop", "pareto", "share_bar", "treemap"}
POINTS_OK = {"dot"}

# 语义 → 候选图型（顺序即优先级）
RULES = [
    (("集中度", "CR", "前五", "前 5", "排名", "头部", "梯队"), "pareto"),
    (("构成", "份额", "结构", "各部分", "占比结构"), "share_bar"),
    (("对比", "四城", "城市", "品牌", "价带", "价格带", "分布"), "dot"),
]


def _text(section: Dict[str, Any], chart: Dict[str, Any]) -> str:
    # 只看图自己的标题与本节问题；节标题里的"只占社零 0.93%"会把图误判成占比图
    return " ".join(str(x or "") for x in (
        section.get("question"), chart.get("title")))


def _convert(chart: Dict[str, Any], t: str) -> Dict[str, Any]:
    out = dict(chart)
    items = chart.get("bars") or chart.get("vbars") or chart.get("items") or []
    out["type"] = t
    # 契约里 items 型统一用 items；charts_pro 的 dot 需要 points，由 compat 转
    out["items"] = [{"label": str(b.get("label", "")),
                     "value": float(b.get("value", 0))} for b in items]
    out.pop("bars", None)
    out.pop("points", None)
    return out


def choose(chart: Dict[str, Any], section: Dict[str, Any],
           history: List[str]) -> Dict[str, Any]:
    t = str(chart.get("type") or "")
    if t not in BAR_LIKE:
        history.append(t)
        return chart
    items = chart.get("bars") or chart.get("vbars") or []
    n = len(items)
    if n < 2:
        history.append("hbar")
        return _convert(chart, "hbar")
    if n == 2:
        # 两个值不需要点图/中位线；柱状 + 一句差值，比换图型更有信息量
        out = _convert(chart, "vbar")
        a, b = items[0], items[1]
        va, vb = float(a.get("value", 0)), float(b.get("value", 0))
        out["accent"] = str(a.get("label")) if va >= vb else str(b.get("label"))
        if not chart.get("accent_note"):
            out["accent_note"] = f"差 {abs(va - vb):g}"
        history.append("vbar")
        return out
    text = _text(section, chart)
    vals = [float(i.get("value", 0)) for i in items]
    # 有负数就不是"构成/排序"：正负条才对
    if any(v < 0 for v in vals):
        history.append("diverging")
        return _convert(chart, "diverging")
    cands: List[str] = []
    for keys, typ in RULES:
        if any(k in text for k in keys):
            if typ == "pareto" and n < 4:
                continue
            if typ == "share_bar":
                # 构成图的前提是"加起来是 100%"，不是关键词命中
                if not (3 <= n <= 6 and 88 <= sum(vals) <= 112):
                    continue
            cands.append(typ)
    # 条目少时点图更清楚；再兜底回条形
    cands += (["dot"] if n <= 4 else ["lollipop"] if n <= 6 else [])
    cands.append("hbar" if n > 4 else "vbar")
    # 先按语义优先级，再把"已用过的型"往后排——避免一本报告全是点图
    used: Dict[str, int] = {}
    for h in history:
        used[h] = used.get(h, 0) + 1
    ordered = sorted(range(len(cands)), key=lambda i: (used.get(cands[i], 0), i))
    for i in ordered:
        c = cands[i]
        if history[-2:] == [c, c]:
            continue
        history.append(c)
        return _convert(chart, c)
    history.append(cands[-1])
    return _convert(chart, cands[-1])

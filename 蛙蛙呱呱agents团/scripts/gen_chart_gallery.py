#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 80 个图表示例（48 型注册表 + 70 个 spec 渲染器的可渲染样例）。

为什么不是手绘：图库的价值是「什么关系配什么图」，不是 80 张好看的画。
每个例子带：型名、适用关系、渲染引擎、最小 payload。

用法：
    python scripts/gen_chart_gallery.py
输出：
    docs/CHART-GALLERY.html
    docs/chart-gallery.json
"""
from __future__ import annotations

import copy
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.report_theme.charts_pro import spec
from samples import samples  # noqa: E402
from core.chart_capabilities import CATALOG  # noqa: E402

TARGET = 80


def _perturb(obj):
    """把数值放大 1.2 倍，制造第二个变体（只用于画廊，不当数据）。"""
    if isinstance(obj, dict):
        return {k: _perturb(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_perturb(v) for v in obj]
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        v = obj * 1.2
        return int(round(v)) if isinstance(obj, int) else round(v, 2)
    return obj


def _meta(key: str) -> dict:
    for c in CATALOG:
        if c.get("key") == key:
            return c
    return {"title": key, "group": "其他", "use_when": ""}


CURATED = [
    ("dot", "盈亏平衡：社区自雇 5.85 万落在 5–6 万饱和区间",
     "比较一组业态的盈亏平衡点，并标出行业饱和带",
     {"unit_meta": "万元/月", "points": [
         {"label": "社区自雇", "value": 5.85}, {"label": "社区雇人", "value": 8.97},
         {"label": "线上", "value": 12.48}, {"label": "商场", "value": 30.18},
         {"label": "前置仓", "value": 46.81}], "band": [5, 6]}),
    ("share_bar", "渠道：线上 53%、专业店 24%、商超 9%",
     "看构成：各渠道份额能否加总到 100%",
     {"unit_meta": "%", "items": [
         {"label": "线上", "value": 53}, {"label": "专业店", "value": 24},
         {"label": "商超", "value": 9}, {"label": "医院", "value": 7},
         {"label": "行业展会", "value": 7}]}),
    ("funnel", "漏斗：首单 100 → 90 天留存 41 → 复购 28",
     "看阶段流失：每一段还剩多少",
     {"unit_meta": "%", "stages": [
         {"label": "首单", "value": 100}, {"label": "30 天", "value": 68},
         {"label": "90 天", "value": 41}, {"label": "复购", "value": 28}]}),
    ("line", "13 期趋势：先涨后跌，拐点在 9 月",
     "看方向与拐点：连续时间用线，不用柱",
     {"unit_meta": "元/件", "points": [
         {"label": "1 月", "value": 5.2}, {"label": "3 月", "value": 5.8},
         {"label": "5 月", "value": 6.3}, {"label": "7 月", "value": 5.9},
         {"label": "9 月", "value": 5.4}, {"label": "11 月", "value": 5.1}]}),
    ("pct_stacked", "预算构成：内容/私域/付费 三年变化",
     "看结构变化：总量 + 占比同时展示",
     {"unit_meta": "%", "categories": ["2024", "2025", "2026"],
      "series": [{"name": "内容", "values": [25, 28, 31]},
                 {"name": "私域", "values": [20, 25, 29]},
                 {"name": "付费", "values": [30, 25, 22]},
                 {"name": "其他", "values": [25, 22, 18]}]}),
    ("waterfall", "利润桥：毛利 +70 → 投流 -45 → 净利 25",
     "看增减拆解：从起点到终点每一笔是什么",
     {"unit_meta": "万元", "start": 70,
      "deltas": [{"label": "投流", "value": -45},
                 {"label": "房租", "value": -12}, {"label": "人力", "value": -8}]}),
    ("choropleth", "北京分区：朝阳/海淀/通州存量",
     "看空间分布：区域本身是信息",
     {"unit_meta": "万只", "values": {"朝阳": 45, "海淀": 38, "通州": 22,
                                      "昌平": 18, "大兴": 15}}),
    ("network", "渠道关系：品牌—平台—网点",
     "看节点与关系：谁连谁、强弱如何",
     {"nodes": ["品牌", "平台", "网点", "用户"],
      "edges": [["品牌", "平台", 0.8], ["平台", "网点", 0.6],
                ["网点", "用户", 0.9], ["平台", "用户", 0.7]]}),
    ("hbar", "品类排名：猫砂 140、智能 102、玩具 60",
     "看排名：类别多、标签长时用横条",
     {"unit_meta": "亿元", "items": [
         {"label": "猫砂", "value": 140}, {"label": "智能用品", "value": 102},
         {"label": "玩具", "value": 60}, {"label": "出行", "value": 35}]}),
    ("vbar", "增速：智能 180%、猫砂 12%、玩具 3%",
     "看增速比较：同一单位、同一期次",
     {"unit_meta": "%", "items": [
         {"label": "智能", "value": 180}, {"label": "猫砂", "value": 12},
         {"label": "玩具", "value": 3}]}),
]


def main() -> int:
    items = []
    # 1) 70 个 spec 渲染器的原生样例
    for key in sorted(samples.SAMPLE):
        try:
            svg = spec.render({"type": key, **samples.SAMPLE[key]})
        except Exception:  # noqa: BLE001
            continue
        m = _meta(key)
        items.append({
            "type": key, "title": m.get("title") or key,
            "group": m.get("group") or "其他",
            "use_when": m.get("use_when") or "",
            "svg": svg, "variant": 1,
        })
        if len(items) >= TARGET:
            break
    # 2) 10 个业务例：真实报告里的 slice，不用「变体」凑数
    for key, title, use_when, payload in CURATED:
        if len(items) >= TARGET:
            break
        try:
            svg = spec.render({"type": key, **payload})
        except Exception:  # noqa: BLE001
            continue
        m = _meta(key)
        items.append({
            "type": key, "title": title,
            "group": (m.get("group") or "业务例") + " · 业务例",
            "use_when": use_when, "svg": svg, "variant": 2,
        })
    # 3) 如果某个业务例渲染失败，才用变体补足 80
    i = 0
    while len(items) < TARGET and i < len(samples.SAMPLE):
        key = sorted(samples.SAMPLE)[i]
        i += 1
        try:
            payload = _perturb(copy.deepcopy(samples.SAMPLE[key]))
            svg = spec.render({"type": key, **payload})
        except Exception:  # noqa: BLE001
            continue
        m = _meta(key)
        items.append({
            "type": key, "title": (m.get("title") or key) + "（变体）",
            "group": m.get("group") or "其他",
            "use_when": m.get("use_when") or "",
            "svg": svg, "variant": 3,
        })

    groups = {}
    for it in items:
        groups.setdefault(it["group"], []).append(it)

    cards = []
    n = 0
    for g, rows in groups.items():
        cards.append(f'<h2>{html.escape(g)}（{len(rows)}）</h2>')
        for it in rows:
            n += 1
            cards.append(
                f'<div class="card"><div class="no">{n:02d}</div>'
                f'<h3>{html.escape(it["title"])} <small>{html.escape(it["type"])}</small></h3>'
                f'<div class="use">{html.escape(it["use_when"])}</div>'
                f'<div class="fig">{it["svg"]}</div></div>')
    doc = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>图表画廊 · {len(items)} 例</title>
<style>
body{{font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;margin:24px;color:#1f2d33}}
h1{{font-size:22px}} h2{{font-size:16px;margin-top:28px;border-bottom:1px solid #ddd;padding-bottom:6px}}
.card{{display:inline-block;vertical-align:top;width:360px;margin:10px;padding:12px;border:1px solid #e3e7ea;border-radius:6px}}
.no{{font-size:10px;color:#9aa7ad}} h3{{font-size:13px;margin:4px 0}} h3 small{{color:#7a8b92;font-weight:400}}
.use{{font-size:11px;color:#5b6b73;min-height:28px}} .fig svg{{width:100%;height:auto}}
</style></head><body>
<h1>图表画廊 · {len(items)} 例</h1>
<p>每个例子都是一个 spec 的最小可渲染 payload；选图先看「关系 → 型」，再看样例。</p>
{''.join(cards)}
</body></html>"""
    out = ROOT / "docs" / "CHART-GALLERY.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    (ROOT / "docs" / "chart-gallery.json").write_text(
        json.dumps([{k: v for k, v in it.items() if k != "svg"} for it in items],
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {out} count={len(items)} groups={len(groups)}")
    return 0 if len(items) >= TARGET else 1


if __name__ == "__main__":
    raise SystemExit(main())

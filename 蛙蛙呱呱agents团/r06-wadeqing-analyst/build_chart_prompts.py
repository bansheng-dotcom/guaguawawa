# -*- coding: utf-8 -*-
"""把 ai-data-visualization-prompts 的 48 个提示词 .md 编译成机器可读注册表。

产出：references/chart_prompts_48.json
用法：python build_chart_prompts.py            （源目录缺省为 ../../补充技能/...）
      python build_chart_prompts.py --src <dir> --out <file>
每个条目：id / key(规范图表名，与 s08_viz.CHART_TYPES 及 chart_lib.CHART_INDEX 对齐) /
number / title / level / group / learn / use_when / prepare[] / prompt_template /
outcome / checklist[] / source_file。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import io

_HERE = os.path.dirname(os.path.abspath(__file__))
CANON = [
    "vertical-bar", "horizontal-bar", "grouped-bar", "stacked-bar",
    "100pct-stacked", "line", "area", "pie", "donut", "histogram", "slope",
    "dumbbell", "dot", "lollipop", "waffle", "boxplot", "scatter", "bubble",
    "heatmap", "radar", "violin", "ridgeline", "parallel-coordinates",
    "error-bar", "forest", "control", "waterfall", "pareto", "funnel",
    "bullet", "gauge", "calendar-heatmap", "gantt", "candlestick", "sankey",
    "streamgraph", "treemap", "sunburst", "choropleth", "symbol-map",
    "geographic-flow", "network", "rose", "bar-line-target-band",
    "contribution-bridge", "dual-axis-bar-line", "kpi-trend-breakdown",
    "small-multiples",
]


def _section(md: str, name: str, bullets: bool = False):
    m = re.search(r"##\s*" + name + r"\s*\n(.*?)(?=\n##\s|\Z)", md, re.S)
    if not m:
        return [] if bullets else ""
    body = m.group(1).strip()
    if bullets:
        return [l.lstrip("-").strip() for l in body.splitlines()
                if l.strip().startswith("-")]
    return body


def build(src_dir: str, out_path: str) -> dict:
    idx = json.load(io.open(os.path.join(src_dir, "index.json"),
                            encoding="utf-8-sig"))
    items = idx["items"]
    assert len(items) == 48 == len(CANON), f"条目数不齐: {len(items)}"
    out = []
    for it, key in zip(items, CANON):
        md = io.open(os.path.join(src_dir, it["file"]), encoding="utf-8").read()
        pm = re.search(r"##\s*提示词\s*\n.*?```text\s*\n(.*?)```", md, re.S)
        out.append({
            "id": it["id"], "key": key, "number": it["number"],
            "title": it["title"], "level": it["level"], "group": it["group"],
            "source_file": "补充技能/数据分析可视化图片提示词/prompts/" + it["file"],
            "learn": _section(md, "学会什么"),
            "use_when": _section(md, "什么时候用"),
            "prepare": _section(md, "需要准备", bullets=True),
            "prompt_template": pm.group(1).strip() if pm else "",
            "outcome": _section(md, "你会得到"),
            "checklist": _section(md, "怎么检查", bullets=True),
        })
    registry = {"schema_id": "r06.chart-prompts-48.v1",
                "source": os.path.relpath(src_dir, _HERE).replace("\\", "/"),
                "count": len(out), "items": out}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    io.open(out_path, "w", encoding="utf-8").write(
        json.dumps(registry, ensure_ascii=False, indent=1))
    return registry


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=os.path.join(
        os.path.dirname(os.path.dirname(_HERE)), "补充技能",
        "数据分析可视化图片提示词", "prompts"))
    ap.add_argument("--out", default=os.path.join(
        _HERE, "references", "chart_prompts_48.json"))
    args = ap.parse_args()
    reg = build(args.src, args.out)
    bad = [i["id"] for i in reg["items"] if not i["prompt_template"]]
    print(json.dumps({
        "ok": True, "out": args.out, "count": reg["count"],
        "missing_prompt": bad,
        "empty_checklist": [i["id"] for i in reg["items"] if not i["checklist"]],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

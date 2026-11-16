# -*- coding: utf-8 -*-
"""图表六要素门禁：48 型每张至少满足 4/6。

六要素：结论式标题（含数字）/ 口径副标题 / 直接标注 / 参考线或参考结构 /
异常或重点归因 / 来源 + 图注。

    python scripts/check_chart_fullness.py [theme]
退出码：0 = 全部 ≥4；1 = 存在 <4 的图型。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import chart_gallery_v2 as G  # noqa: E402
from core.charts.v2 import render  # noqa: E402

# 结构即参考：环刻度、坐标网、轴框架、100% 网格等
STRUCT_REF = {
    "pct_stacked", "violin", "parallel", "pie", "donut", "treemap", "heatmap",
    "waffle", "rose", "sunburst", "sankey", "network", "choropleth", "symbol_map",
    "kpi_break", "geo_flow", "gantt", "bullet", "gauge", "radar", "cal_heatmap",
}
ATTRIBUTION = (
    "最大", "最高", "最低", "峰值", "主路径", "主通道", "偏离", "瓶颈", "漏点",
    "越限", "离散", "差距", "缺口", "最繁忙", "度数最高", "最分散", "集中",
    "流失", "占比最高", "匹配率", "最长", "唯一", "过半", "达成", "距", "最",
)


def _texts(svg: str) -> list:
    raw = re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S)
    out = []
    for item in raw:
        s = re.sub(r"<[^>]+>", "", item).replace("&#160;", " ").strip()
        if s:
            out.append(s)
    return out


def score(key: str, spec: dict, svg: str) -> tuple:
    texts = _texts(svg)
    joined = " ".join(texts)
    checks = {
        "结论式标题": bool(re.search(r"\d", str(spec.get("title") or ""))),
        "口径副标题": bool(str(spec.get("subtitle") or "").strip()),
        "直接标注": len(texts) >= 8,
        "参考线/结构": ("stroke-dasharray" in svg) or key in STRUCT_REF,
        "异常/重点归因": any(k in joined for k in ATTRIBUTION),
        "来源+图注": bool(str(spec.get("source") or "").strip())
                     and bool(str(spec.get("note") or "").strip()),
    }
    return sum(checks.values()), [k for k, v in checks.items() if not v]


def main() -> int:
    theme = sys.argv[1] if len(sys.argv) > 1 else "paper"
    weak, total = [], 0
    for key, spec in G.SAMPLES.items():
        svg = render(spec, theme) or ""
        n, missing = score(key, spec, svg)
        total += n
        flag = "" if n >= 4 else "  <-- 不达标"
        print(f"{key:<14} {n}/6  缺：{'、'.join(missing) if missing else '无'}{flag}")
        if n < 4:
            weak.append(key)
    print(f"\n均值 {total / max(len(G.SAMPLES), 1):.2f}/6 · 不达标 {len(weak)} 型")
    if weak:
        print("不达标：", ", ".join(weak))
    return 0 if not weak else 1


if __name__ == "__main__":
    raise SystemExit(main())

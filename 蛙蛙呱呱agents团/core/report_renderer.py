# -*- coding: utf-8 -*-
"""共享确定性 HTML 报告渲染器（core 层，全 20 角色通用）。

来源：由 R06 蛙得清的 report_renderer.py 抽取上收为核心库（对齐
《角色Agent生成SOP》第十节 qiuqiu 编辑级证据报告标准），供所有角色复用。

职责：
- 校验 report contract JSON（缺必填字段即 FAIL，退出码非 0）
- 确定性渲染自包含 HTML（内联 CSS + 内嵌 SVG，无外部依赖）

与 R06 专用版的关键差异：**图表渲染可插拔**。
- 内建支持 hbar / vbar 两种基础图（任何角色都可用，无需额外依赖）；
- 其余 46 型图表通过 `--chart-dir` 指向某角色的目录（内含 chart_lib.py），
  运行时动态加载 `chart_lib.RENDERERS` 路由。非数据角色（如 R03/R16）不传该参数，
  纯文字报告照常可渲染。

用法：
    python core/report_renderer.py --contract report.json --output out.html
    python core/report_renderer.py --contract r.json --output o.html \
        --chart-dir agents/r06-wadeqing-analyst
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional

# 图表解析目录（--chart-dir 注入）；None 表示仅用内建 hbar/vbar。
_CHART_DIR: Optional[str] = None
_CHART_MOD = None  # 缓存已加载的 chart_lib 模块


def set_chart_dir(path: Optional[str]) -> None:
    global _CHART_DIR, _CHART_MOD
    _CHART_DIR = os.path.abspath(path) if path else None
    _CHART_MOD = None


def _load_chart_lib():
    """动态加载 _CHART_DIR 下的 chart_lib 模块（含 48 型 RENDERERS 路由）。"""
    global _CHART_MOD
    if _CHART_MOD is not None:
        return _CHART_MOD
    if not _CHART_DIR:
        return None
    lib_path = os.path.join(_CHART_DIR, "chart_lib.py")
    if not os.path.exists(lib_path):
        return None
    if _CHART_DIR not in sys.path:
        sys.path.insert(0, _CHART_DIR)
    spec = importlib.util.spec_from_file_location("_shared_chart_lib", lib_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _CHART_MOD = mod
    return mod



# ------------------------------------------------------------------------- #
# 以下为移植自 R06 report_renderer.py 的确定性部分（校验 + CSS + 渲染）
# ------------------------------------------------------------------------- #

REQUIRED_TOP = ["doc_type", "title_lines", "standfirst", "metric_strip",
                "summary", "sections", "notes", "footer"]
REQUIRED_METRIC = ["label", "value", "note"]
REQUIRED_SECTION = ["index", "title", "question"]
VALID_STATUS = {"critical", "watch", "healthy", "accent", "none"}
VALID_WEIGHT = {"critical", "context", "reference", "healthy"}


def validate_contract(c: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    for k in REQUIRED_TOP:
        if k not in c:
            errs.append(f"缺顶层字段: {k}")
    for i, m in enumerate(c.get("metric_strip", [])):
        for k in REQUIRED_METRIC:
            if not m.get(k):
                errs.append(f"metric_strip[{i}] 缺 {k}")
        if m.get("status", "none") not in VALID_STATUS:
            errs.append(f"metric_strip[{i}] status 非法: {m.get('status')}")
    for i, s in enumerate(c.get("sections", [])):
        for k in REQUIRED_SECTION:
            if not s.get(k):
                errs.append(f"sections[{i}] 缺 {k}")
    for i, sec in enumerate(c.get("sections", [])):
        ch = sec.get("chart")
        if ch:
            for k in ("title", "unit_meta", "source", "type"):
                if not ch.get(k):
                    errs.append(f"sections[{i}].chart 缺 {k}")
            t = ch.get("type", "")
            if t in ("hbar",):
                for j, b in enumerate(ch.get("bars", [])):
                    if "label" not in b or "value" not in b:
                        errs.append(f"sections[{i}].chart bars[{j}] 缺 label/value")
                    if b.get("weight", "context") not in VALID_WEIGHT:
                        errs.append(f"sections[{i}].chart bars[{j}] weight 非法")
            elif t == "vbar":
                for j, b in enumerate(ch.get("vbars", [])):
                    if "label" not in b or "value" not in b:
                        errs.append(f"sections[{i}].chart vbars[{j}] 缺 label/value")
            elif t == "line":
                if not ch.get("xlabels") or not ch.get("series"):
                    errs.append(f"sections[{i}].chart line 缺 xlabels/series")
                for s in ch.get("series", []):
                    if len(s.get("values", [])) != len(ch.get("xlabels", [])):
                        errs.append(f"sections[{i}].chart series 值数与 xlabels 不一致")
            elif t == "waterfall":
                if not ch.get("steps"):
                    errs.append(f"sections[{i}].chart waterfall 缺 steps")
            elif t == "slope":
                if not ch.get("items"):
                    errs.append(f"sections[{i}].chart slope 缺 items")
            elif t == "box":
                for j, g in enumerate(ch.get("groups", [])):
                    if "label" not in g or not g.get("values"):
                        errs.append(f"sections[{i}].chart groups[{j}] 缺 label/values")
            elif t == "control":
                for k in ("xlabels", "series", "center", "band"):
                    if ch.get(k) is None:
                        errs.append(f"sections[{i}].chart control 缺 {k}")
            elif t == "funnel":
                if not ch.get("stages"):
                    errs.append(f"sections[{i}].chart funnel 缺 stages")
                else:
                    for j, s in enumerate(ch["stages"]):
                        if "label" not in s or s.get("value") is None:
                            errs.append(f"sections[{i}].chart stages[{j}] 缺 label/value")
            elif t == "pareto":
                if not ch.get("items"):
                    errs.append(f"sections[{i}].chart pareto 缺 items")
                else:
                    for j, s in enumerate(ch["items"]):
                        if "label" not in s or s.get("value") is None:
                            errs.append(f"sections[{i}].chart items[{j}] 缺 label/value")
            elif t == "histogram":
                if not ch.get("values"):
                    errs.append(f"sections[{i}].chart histogram 缺 values")
            elif t == "scatter":
                if not ch.get("points"):
                    errs.append(f"sections[{i}].chart scatter 缺 points")
                else:
                    for j, p in enumerate(ch["points"]):
                        if p.get("x") is None or p.get("y") is None:
                            errs.append(f"sections[{i}].chart points[{j}] 缺 x/y")
            elif t == "grouped_bar":
                for k in ("categories", "series"):
                    if not ch.get(k):
                        errs.append(f"sections[{i}].chart grouped_bar 缺 {k}")
                if ch.get("series") and len(ch["series"]) > 3:
                    errs.append(f"sections[{i}].chart grouped_bar 系列超过 3（viz-03 纪律）")
            else:
                errs.extend(_validate_ext_chart(ch, i))
    return errs


def _validate_ext_chart(ch: Dict[str, Any], i: int) -> List[str]:
    """38 型扩展图（chart_renderers_ext）：必填字段 + 渲染纪律数据门禁。"""
    errs: List[str] = []
    t = ch.get("type", "")
    P = f"sections[{i}].chart"
    ok = True

    def need(*keys: str) -> None:
        nonlocal ok
        for k in keys:
            if ch.get(k) is None:
                errs.append(f"{P} {t} 缺 {k}")
                ok = False

    def items_need(key: str, *fields: str) -> None:
        nonlocal ok
        lst = ch.get(key)
        if not isinstance(lst, list) or not lst:
            if lst is None:
                errs.append(f"{P} {t} 缺 {key}")
                ok = False
            return
        for j, it in enumerate(lst):
            if not isinstance(it, dict):
                errs.append(f"{P} {t} {key}[{j}] 结构非法")
                ok = False
                continue
            for f in fields:
                if it.get(f) is None:
                    errs.append(f"{P} {t} {key}[{j}] 缺 {f}")
                    ok = False

    if t == "stacked_bar" or t == "pct_stacked":
        need("categories", "segments")
        items_need("segments", "name", "values")
        for j, s in enumerate(ch.get("segments", [])):
            if isinstance(s, dict) and len(s.get("values", [])) != len(ch.get("categories", [])):
                errs.append(f"{P} {t} segments[{j}].values 数与 categories 不一致")
    elif t == "area":
        need("xlabels", "series")
        if len(ch.get("series", [])) > 1:
            errs.append(f"{P} area 多系列（viz-07 纪律：严重遮挡，只允许单系列）")
        if ch.get("series") and len(ch["series"][0].get("values", [])) != len(ch.get("xlabels", [])):
            errs.append(f"{P} area series 值数与 xlabels 不一致")
    elif t in ("pie", "donut"):
        items_need("items", "label", "value")
    elif t in ("dot", "lollipop", "waffle", "treemap"):
        items_need("items", "label", "value")
    elif t == "dumbbell":
        items_need("items", "label", "a", "b")
    elif t == "bubble":
        items_need("points", "x", "y", "size")
    elif t == "heatmap":
        need("rows", "cols", "cells")
        cells = ch.get("cells")
        if isinstance(cells, list):
            if len(cells) != len(ch.get("rows", [])) or any(
                    not isinstance(r, list) or len(r) != len(ch.get("cols", [])) for r in cells):
                errs.append(f"{P} heatmap cells 必须是 rows×cols 完整矩阵（缺失用 null）")
    elif t == "radar":
        need("axes", "series")
        if len(ch.get("series", [])) > 2:
            errs.append(f"{P} radar 对象超过 2 组（viz-20 纪律），拆分展示")
        items_need("series", "name", "values")
        for s in ch.get("series", []):
            if isinstance(s, dict) and len(s.get("values", [])) != len(ch.get("axes", [])):
                errs.append(f"{P} radar series 值数与 axes 不一致")
    elif t in ("violin", "ridgeline"):
        need("groups")
        items_need("groups", "label", "values")
    elif t == "parallel":
        need("axes", "items")
        items_need("items", "name", "values")
        for it in ch.get("items", []):
            if isinstance(it, dict) and len(it.get("values", [])) != len(ch.get("axes", [])):
                errs.append(f"{P} parallel items values 数与 axes 不一致")
    elif t == "error_bar":
        need("items", "err_type")
        items_need("items", "label", "value", "err")
        if ch.get("err_type") not in ("SD", "SE", "CI"):
            errs.append(f"{P} error_bar err_type 必须明确为 SD/SE/CI 之一（viz-24 纪律：口径不混用）")
    elif t == "forest":
        items_need("items", "label", "est", "lo", "hi")
    elif t == "bullet":
        need("label", "value", "target")
    elif t == "gauge":
        need("value", "min", "max")
        v, lo, hi = ch.get("value"), ch.get("min"), ch.get("max")
        if None not in (v, lo, hi) and not (lo <= v <= hi):
            errs.append(f"{P} gauge 当前值 {v} 不在 [{lo}, {hi}] 范围内")
    elif t == "cal_heatmap":
        items_need("days", "date", "value")
        for j, d in enumerate(ch.get("days", [])):
            if isinstance(d, dict):
                try:
                    from datetime import date as _d
                    _d.fromisoformat(str(d["date"])[:10])
                except Exception:
                    errs.append(f"{P} cal_heatmap days[{j}].date 须为 YYYY-MM-DD")
    elif t == "gantt":
        items_need("tasks", "label", "start", "end")
        for j, tk in enumerate(ch.get("tasks", [])):
            if isinstance(tk, dict):
                try:
                    from datetime import date as _d
                    _d.fromisoformat(str(tk["start"])[:10])
                    _d.fromisoformat(str(tk["end"])[:10])
                except Exception:
                    errs.append(f"{P} gantt tasks[{j}] start/end 须为 YYYY-MM-DD")
    elif t == "candlestick":
        items_need("candles", "label", "open", "high", "low", "close")
        for j, c in enumerate(ch.get("candles", [])):
            if isinstance(c, dict) and None not in (c.get("high"), c.get("low"), c.get("open"), c.get("close")):
                if not (c["high"] >= max(c["open"], c["close"]) and c["low"] <= min(c["open"], c["close"])):
                    errs.append(f"{P} candlestick candles[{j}] 开高低收关系非法（high≥max(open,close)、low≤min(open,close)）")
    elif t == "sankey":
        need("nodes", "links")
        items_need("nodes", "id", "label")
        items_need("links", "from", "to", "value")
        ids = {n.get("id") for n in ch.get("nodes", []) if isinstance(n, dict)}
        for lk in ch.get("links", []):
            if isinstance(lk, dict) and (lk.get("from") not in ids or lk.get("to") not in ids):
                errs.append(f"{P} sankey links 引用未注册节点")
    elif t == "streamgraph":
        need("xlabels", "series")
        if len(ch.get("series", [])) > 6:
            errs.append(f"{P} streamgraph 类别超过 6（viz-36 纪律）")
        items_need("series", "name", "values")
        for s in ch.get("series", []):
            if isinstance(s, dict) and len(s.get("values", [])) != len(ch.get("xlabels", [])):
                errs.append(f"{P} streamgraph series 值数与 xlabels 不一致")
    elif t == "sunburst":
        need("root")
        root = ch.get("root") or {}
        for j, c in enumerate(root.get("children", [])):
            if not isinstance(c, dict) or c.get("label") is None or c.get("value") is None:
                errs.append(f"{P} sunburst root.children[{j}] 缺 label/value")
    elif t == "choropleth":
        items_need("regions", "name")
        for j, r in enumerate(ch.get("regions", [])):
            if isinstance(r, dict) and "value" not in r:
                errs.append(f"{P} choropleth regions[{j}] 缺 value（缺失用 null，不是省略）")
    elif t == "symbol_map":
        items_need("points", "name", "lon", "lat", "value")
    elif t == "geo_flow":
        need("points", "flows")
        items_need("points", "id", "name", "lon", "lat")
        items_need("flows", "from", "to", "value")
        ids = {p.get("id") for p in ch.get("points", []) if isinstance(p, dict)}
        for f in ch.get("flows", []):
            if isinstance(f, dict) and (f.get("from") not in ids or f.get("to") not in ids):
                errs.append(f"{P} geo_flow flows 引用未注册点位")
    elif t == "network":
        need("nodes", "edges")
        items_need("nodes", "id", "label")
        ids = {n.get("id") for n in ch.get("nodes", []) if isinstance(n, dict)}
        for e in ch.get("edges", []):
            if isinstance(e, dict) and (e.get("a") not in ids or e.get("b") not in ids):
                errs.append(f"{P} network edges 引用未注册节点")
    elif t == "rose":
        items_need("sectors", "label", "value")
    elif t == "target_band":
        need("xlabels", "series", "band")
        band = ch.get("band") or {}
        if band.get("lo") is None or band.get("hi") is None:
            errs.append(f"{P} target_band band 缺 lo/hi")
        if ch.get("series") and len(ch["series"][0].get("values", [])) != len(ch.get("xlabels", [])):
            errs.append(f"{P} target_band series 值数与 xlabels 不一致")
    elif t == "bridge":
        need("start", "deltas", "end")
        items_need("deltas", "label", "value")
        s = (ch.get("start") or {}).get("value")
        e = (ch.get("end") or {}).get("value")
        ds = [d.get("value") for d in ch.get("deltas", []) if isinstance(d, dict) and d.get("value") is not None]
        if None not in (s, e) and ds is not None and len(ds) == len(ch.get("deltas", [])):
            if abs(s + sum(ds) - e) > 1e-6:
                errs.append(f"{P} bridge 贡献项无法回到终点（{s} + Δ {sum(ds)} ≠ {e}，viz-45 纪律：禁止硬凑）")
    elif t == "dual_axis":
        need("xlabels", "bars", "line")
        for k in ("bars", "line"):
            b = ch.get(k) or {}
            for f in ("name", "values", "unit"):
                if b.get(f) is None:
                    errs.append(f"{P} dual_axis {k} 缺 {f}")
            if b.get("values") is not None and len(b["values"]) != len(ch.get("xlabels", [])):
                errs.append(f"{P} dual_axis {k}.values 数与 xlabels 不一致")
    elif t == "kpi_break":
        need("kpi", "trend", "breakdown")
        if (ch.get("kpi") or {}).get("value") is None:
            errs.append(f"{P} kpi_break kpi 缺 value")
        bd = ch.get("breakdown") or {}
        for j, it in enumerate(bd.get("items", [])):
            if not isinstance(it, dict) or it.get("label") is None or it.get("value") is None:
                errs.append(f"{P} kpi_break breakdown.items[{j}] 缺 label/value")
        tr = ch.get("trend") or {}
        if not tr.get("xlabels") or tr.get("values") is None:
            errs.append(f"{P} kpi_break trend 缺 xlabels/values")
    elif t == "small_mult":
        need("panels")
        if len(ch.get("panels", [])) > 6:
            errs.append(f"{P} small_mult 超过 6 格（viz-48 纪律），拆页")
        for j, p in enumerate(ch.get("panels", [])):
            if not isinstance(p, dict) or not p.get("title") or not p.get("xlabels") or p.get("values") is None:
                errs.append(f"{P} small_mult panels[{j}] 缺 title/xlabels/values")
    else:
        errs.append(f"{P} type 非法: {t}")
    return errs


# --------------------------------------------------------------------------- #
# CSS：internet-reporting 风格（自样张移植，色板 graphite-cobalt）
# --------------------------------------------------------------------------- #

CSS = """    :root {
      --theme-base: #F2F3F4; --theme-primary: #292F36; --theme-accent: #315E9B;
      --critical: #B33A32; --watch: #8A6500; --healthy: #19704B;
      --canvas: color-mix(in srgb, var(--theme-primary) 8%, var(--theme-base));
      --paper: var(--theme-base); --ink: var(--theme-primary);
      --muted: color-mix(in srgb, var(--theme-primary) 66%, var(--theme-base));
      --line: color-mix(in srgb, var(--theme-primary) 16%, var(--theme-base));
      --line-strong: color-mix(in srgb, var(--theme-primary) 34%, var(--theme-base));
      --surface: color-mix(in srgb, var(--theme-primary) 3%, var(--theme-base));
      --surface-strong: color-mix(in srgb, var(--theme-primary) 7%, var(--theme-base));
      --accent-soft: color-mix(in srgb, var(--theme-accent) 10%, var(--theme-base));
      --critical-soft: color-mix(in srgb, var(--critical) 11%, var(--theme-base));
      --watch-soft: color-mix(in srgb, var(--watch) 11%, var(--theme-base));
      --healthy-soft: color-mix(in srgb, var(--healthy) 11%, var(--theme-base));
      --series-context: color-mix(in srgb, var(--theme-primary) 54%, var(--theme-base));
      --series-reference: color-mix(in srgb, var(--theme-primary) 38%, var(--theme-base));
      --page-columns: 12; --page-gap: 22px;
    }
    * { box-sizing: border-box; }
    html { background: var(--canvas); scroll-behavior: smooth; }
    body {
      margin: 0; background: var(--canvas); color: var(--ink);
      font-family: "Microsoft YaHei", "Microsoft YaHei UI", Arial, sans-serif;
      font-size: 15px; font-weight: 400; line-height: 1.68;
      font-synthesis: none; -webkit-font-smoothing: antialiased;
      font-variant-numeric: tabular-nums;
    }
    svg { font-family: inherit; }
    a { color: inherit; }
    strong, b { font-weight: 700; }
    .document {
      width: min(1180px, calc(100% - 48px));
      margin: 28px auto 54px; padding: 40px 54px 46px;
      background: var(--paper); border: 1px solid var(--line); border-radius: 2px;
    }
    .page-grid {
      display: grid; grid-template-columns: repeat(var(--page-columns), minmax(0, 1fr));
      column-gap: var(--page-gap);
    }
    .doc-header { padding-bottom: 28px; border-bottom: 1px solid var(--line-strong); }
    .doc-type {
      display: flex; align-items: center; gap: 10px; margin-bottom: 18px;
      color: var(--muted); font-size: 12px;
    }
    .doc-glyph {
      width: 28px; height: 28px; display: inline-flex; align-items: flex-end;
      justify-content: center; gap: 2px; padding: 6px;
      border: 1px solid var(--line-strong); border-radius: 2px;
    }
    .doc-glyph i { width: 3px; display: block; background: var(--theme-accent); }
    .doc-glyph i:nth-child(1) { height: 6px; }
    .doc-glyph i:nth-child(2) { height: 11px; }
    .doc-glyph i:nth-child(3) { height: 8px; }
    h1 {
      max-width: 980px; margin: 0; font-size: clamp(36px, 3vw, 40px);
      font-weight: 700; line-height: 1.18; letter-spacing: -.025em; text-wrap: balance;
    }
    .title-line { display: block; }
    .standfirst {
      max-width: 850px; margin: 17px 0 0; color: var(--muted);
      font-size: 16px; line-height: 1.72;
    }
    .doc-meta {
      display: flex; flex-wrap: wrap; gap: 8px 24px; margin-top: 20px;
      color: var(--muted); font-size: 11.5px;
    }
    .doc-meta span { position: relative; white-space: nowrap; }
    .doc-meta span + span::before {
      position: absolute; left: -13px; content: "·"; color: var(--line-strong);
    }
    .metric-strip {
      margin-top: 26px; border-top: 1px solid var(--line-strong);
      border-bottom: 1px solid var(--line-strong);
    }
    .metric { grid-column: span 3; min-height: 124px; padding: 16px 10px 15px 0; }
    .metric-label {
      display: flex; align-items: center; gap: 7px; min-height: 22px;
      color: var(--muted); font-size: 12px; line-height: 1.45;
    }
    .metric-value {
      display: block; margin-top: 6px; font-size: 30px; font-weight: 700;
      line-height: 1.06; letter-spacing: -.02em;
    }
    .metric-value.critical { color: var(--critical); }
    .metric-value.watch { color: var(--watch); }
    .metric-value.healthy { color: var(--healthy); }
    .metric-note {
      display: block; margin-top: 8px; color: var(--muted);
      font-size: 11.5px; line-height: 1.5;
    }
    .shape { display: inline-block; flex: 0 0 auto; }
    .shape-diamond { width: 7px; height: 7px; background: var(--critical); transform: rotate(45deg); }
    .shape-circle { width: 7px; height: 7px; border-radius: 50%; background: var(--healthy); }
    .shape-triangle {
      width: 0; height: 0; border-left: 5px solid transparent;
      border-right: 5px solid transparent; border-bottom: 8px solid var(--watch);
    }
    .shape-accent { width: 7px; height: 7px; border-radius: 50%; background: var(--theme-accent); }
    .microbar { width: min(154px, 100%); height: 5px; margin-top: 10px; background: var(--line); }
    .microbar span { display: block; height: 100%; background: var(--theme-accent); }
    .summary { margin-top: 30px; }
    .summary-label, .notes-label {
      grid-column: 1 / span 9; display: flex; align-items: center; gap: 9px;
      margin: 0 0 13px; color: var(--theme-accent); font-size: 13px;
      font-weight: 700; line-height: 1.45;
    }
    .summary-label::before, .notes-label::before {
      width: 7px; height: 7px; content: ""; flex: 0 0 auto;
      border-radius: 50%; background: var(--theme-accent);
    }
    .summary-copy { grid-column: 1 / span 9; max-width: 830px; }
    .summary-copy p { margin: 0 0 10px; }
    .summary-copy .summary-close {
      margin-top: 13px; padding-top: 12px; border-top: 1px solid var(--line);
    }
    mark { padding: 1px 3px; background: var(--accent-soft); color: inherit; }
    .report-section { margin-top: 48px; scroll-margin-top: 20px; }
    .section-head {
      display: flex; align-items: flex-start; gap: 10px; padding-bottom: 14px;
      border-bottom: 1px solid var(--line-strong);
    }
    .section-index {
      flex: 0 0 auto; padding-top: 5px; color: var(--theme-accent);
      font-size: 12px; font-weight: 700; line-height: 1.4;
    }
    .section-heading-copy { min-width: 0; }
    .section-title {
      margin: 0; font-size: 23px; font-weight: 700; line-height: 1.34;
      letter-spacing: -.012em;
    }
    .section-question {
      margin: 6px 0 0; color: var(--muted); font-size: 12px; line-height: 1.55;
    }
    .section-intro { grid-column: 1 / span 8; margin-top: 18px; }
    .section-intro p { margin: 0 0 9px; }
    .embed { margin: 22px 0 0; border: 1px solid var(--line-strong); border-radius: 2px; }
    .embed-head {
      display: flex; align-items: flex-start; justify-content: space-between;
      gap: 18px; padding: 12px 15px; border-bottom: 1px solid var(--line);
    }
    .embed-title {
      display: flex; align-items: flex-start; gap: 9px; min-width: 0;
      font-size: 13px; font-weight: 700; line-height: 1.5;
    }
    .embed-icon {
      width: 14px; height: 14px; margin-top: 2px; flex: 0 0 auto;
      border: 1px solid var(--theme-accent); position: relative;
    }
    .embed-icon::before, .embed-icon::after {
      position: absolute; left: 3px; content: ""; width: 6px;
      border-top: 1px solid var(--theme-accent);
    }
    .embed-icon::before { top: 4px; }
    .embed-icon::after { top: 8px; }
    .embed-meta {
      flex: 0 0 auto; color: var(--muted); font-size: 11.5px;
      line-height: 1.5; white-space: nowrap;
    }
    .chart-wrap { padding: 14px 16px 10px; }
    .chart-wrap svg { display: block; width: 100%; height: auto; }
    .embed-source {
      padding: 0 16px 12px; color: var(--muted); font-size: 11.5px; line-height: 1.55;
    }
    .post-chart { margin-top: 17px; align-items: start; }
    .reading-block { grid-column: 1 / span 7; }
    .reading-block h3, .boundary-block h3, .block-note h3 {
      margin: 0 0 8px; font-size: 14px; font-weight: 700; line-height: 1.5;
    }
    .reading-list { margin: 0; padding: 0; list-style: none; }
    .reading-list li {
      display: grid; grid-template-columns: 22px minmax(0, 1fr); gap: 7px;
      padding: 7px 0; border-top: 1px solid var(--line);
    }
    .reading-list li:first-child { border-top: 0; }
    .reading-no { color: var(--theme-accent); font-size: 12px; font-weight: 700; }
    .reading-text { font-size: 13px; line-height: 1.58; }
    .boundary-block {
      grid-column: 8 / -1; padding: 12px 15px;
      border-left: 3px solid var(--watch); background: var(--watch-soft);
    }
    .boundary-label {
      display: flex; align-items: center; gap: 8px; color: var(--watch);
      font-size: 12px; font-weight: 700;
    }
    .boundary-block p, .block-note p {
      margin: 7px 0 0; color: var(--muted); font-size: 12px; line-height: 1.58;
    }
    .evidence-table-wrap {
      margin-top: 22px; overflow-x: auto; border: 1px solid var(--line-strong);
    }
    table { width: 100%; border-collapse: collapse; }
    .evidence-table { min-width: 860px; table-layout: fixed; }
    .evidence-table th, .evidence-table td {
      padding: 11px 12px; border-right: 1px solid var(--line);
      border-bottom: 1px solid var(--line); vertical-align: top;
      text-align: left; font-size: 12px; line-height: 1.55;
    }
    .evidence-table th:last-child, .evidence-table td:last-child { border-right: 0; }
    .evidence-table tr:last-child td { border-bottom: 0; }
    .evidence-table th { background: var(--surface-strong); color: var(--muted); font-weight: 700; }
    .evidence-table .num { text-align: right; white-space: nowrap; }
    .row-label { display: flex; align-items: flex-start; gap: 8px; font-weight: 700; }
    .row-mark { width: 4px; height: 18px; margin-top: 1px; flex: 0 0 auto; background: var(--critical); }
    .row-mark.watch { background: var(--watch); }
    .row-mark.healthy { background: var(--healthy); }
    .cell-line { display: block; margin-top: 3px; }
    .cell-line:first-child { margin-top: 0; }
    .cell-key {
      display: inline-block; min-width: 34px; color: var(--muted);
      font-size: 11.5px; font-weight: 700;
    }
    .delta-critical { color: var(--critical); font-weight: 700; }
    .delta-watch { color: var(--watch); font-weight: 700; }
    .delta-healthy { color: var(--healthy); font-weight: 700; }
    .block-note {
      margin-top: 16px; max-width: 760px; padding: 13px 16px;
      border-left: 3px solid var(--theme-accent); background: var(--accent-soft);
    }
    .notes { margin-top: 46px; padding-top: 22px; border-top: 1px solid var(--line-strong); }
    details { grid-column: 1 / span 9; border-bottom: 1px solid var(--line); }
    summary {
      padding: 8px 0; cursor: pointer; font-size: 13px; font-weight: 700; list-style: none;
    }
    summary::-webkit-details-marker { display: none; }
    summary::before {
      display: inline-block; width: 18px; content: "▾"; color: var(--theme-accent);
    }
    .notes-copy { padding: 0 0 12px 18px; color: var(--muted); font-size: 11.5px; line-height: 1.6; }
    .notes-copy p { margin: 5px 0; }
    .doc-footer {
      display: flex; justify-content: space-between; gap: 20px;
      margin-top: 26px; color: var(--muted); font-size: 11.5px;
    }
    @media (max-width: 980px) {
      .document { width: calc(100% - 28px); padding: 34px 28px 40px; }
      .evidence-table { min-width: 800px; }
    }
    @media (max-width: 860px) {
      .document { width: min(100% - 28px, 760px); padding: 32px 28px 38px; }
      .metric { grid-column: span 6; }
      .summary-label, .summary-copy, .section-intro, details { grid-column: 1 / -1; }
      .reading-block, .boundary-block { grid-column: 1 / -1; }
      .boundary-block { margin-top: 16px; }
    }
    @media (max-width: 720px) {
      .document { width: calc(100% - 20px); margin: 10px auto 26px; padding: 26px 20px 32px; }
      h1 { font-size: 30px; line-height: 1.24; }
      .title-line { display: inline; }
      .title-line + .title-line::before { content: " "; }
      .metric { grid-column: 1 / -1; min-height: auto; border-top: 1px solid var(--line); }
      .metric:first-child { border-top: 0; }
      .section-title { font-size: 21px; }
      .embed-head { display: block; }
      .embed-meta { margin-top: 5px; white-space: normal; }
      .chart-wrap { min-width: 680px; }
      .embed { overflow-x: auto; }
      .doc-footer { display: block; }
    }
    .doc-toc { grid-column: 1 / -1; margin: 2px 0 18px; padding: 12px 16px; border: 1px solid var(--line); }
    .doc-toc ol { margin: 0; padding-left: 20px; columns: 2; column-gap: 28px; }
    .doc-toc li { margin: 3px 0; font-size: 13px; }
    .doc-toc a { color: var(--ink-2); text-decoration: none; }
    .doc-toc a:hover { text-decoration: underline; }
    @media print {
      html, body { background: var(--paper); }
      .document { width: auto; margin: 0; border: 0; }
      a { text-decoration: none; }
      details { break-inside: avoid; }
.report-appendix { grid-column: 1 / -1; margin: 28px 0; border-top: 1px solid var(--line); }
.report-appendix > summary { cursor: pointer; padding: 14px 0; font-weight: 600; color: var(--ink-2); list-style: none; }
.report-appendix > summary::-webkit-details-marker { display: none; }
.report-appendix > summary::before { content: "▸"; margin-right: 10px; color: var(--muted); }
.report-appendix[open] > summary::before { content: "▾"; }
    }"""

# --------------------------------------------------------------------------- #
# SVG 图表生成（确定性：坐标由数值计算，非手摆）
# --------------------------------------------------------------------------- #
WEIGHT_FILL = {
    "critical": "var(--critical)",
    "context": "var(--series-context)",
    "reference": "var(--series-reference)",
    "healthy": "var(--healthy)",
}

def _fmt(v: float) -> str:
    if v == int(v):
        return f"{int(v):,}"
    return f"{v:,.2f}"


def hbar_chart(title: str, bars: List[Dict[str, Any]], footnote: Optional[List[str]] = None) -> str:
    """横向贡献条形图（对齐样张 Section 2 形态）。bars: label/sub/value/value_label/weight。"""
    n = len(bars)
    W, TOP, BOT = 980, 45, 44
    row_h = 63
    H = TOP + n * row_h + BOT
    vals = [b["value"] for b in bars]
    vmax = max(max(vals), 0)
    vmin = min(min(vals), 0)
    span = (vmax - vmin) or 1.0
    x0 = 224            # 零轴基线（负值向左延伸）
    x1 = 902            # 右侧刻度
    def xw(v: float) -> float:
        return x0 + (v - vmin) / span * (x1 - x0)
    zero = xw(0)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{title}">']
    # 刻度线（零轴 + 最右）
    ticks = [0, vmax if vmax != 0 else 1]
    for t in ticks:
        x = xw(t)
        out.append(f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" y2="{TOP + n * row_h - 12}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{TOP - 12}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{_fmt(t)}</text>')
    # 行：标签 + 副标 + 条 + 值
    for i, b in enumerate(bars):
        cy = TOP + i * row_h + 4
        out.append(f'<text x="18" y="{cy + 8}" fill="var(--ink)" font-size="12.5" font-weight="700">{b["label"]}</text>')
        if b.get("sub"):
            out.append(f'<text x="18" y="{cy + 26}" fill="var(--muted)" font-size="11.5">{b["sub"]}</text>')
        v = b["value"]
        bx = min(zero, xw(v))
        bw = max(abs(xw(v) - zero), 1)
        fill = WEIGHT_FILL.get(b.get("weight", "context"), "var(--series-context)")
        if v < 0:  # 负贡献向左，从零轴往左画
            out.append(f'<rect x="{xw(0) - bw:.1f}" y="{cy}" width="{bw:.1f}" height="18" fill="{fill}"/>')
        else:
            out.append(f'<rect x="{xw(0):.1f}" y="{cy}" width="{bw:.1f}" height="18" fill="{fill}"/>')
        vl = b.get("value_label") or _fmt(v)
        color = {"critical": "var(--critical)", "healthy": "var(--healthy)"}.get(b.get("weight", ""), "var(--ink)")
        anchor = "end" if v < 0 else "start"
        tx = (xw(0) - bw - 6) if v < 0 else (xw(0) + bw + 6)
        out.append(f'<text x="{tx:.1f}" y="{cy + 14}" fill="{color}" font-size="12" font-weight="700" text-anchor="{anchor}">{vl}</text>')
    # 底部合计脚注（可选）
    if footnote:
        fy = TOP + n * row_h + 18
        out.append(f'<line x1="18" y1="{fy - 22}" x2="{x1}" y2="{fy - 22}" stroke="var(--line-strong)"/>')
        fx = 18
        for seg in footnote:
            txt, val, color = seg.get("text", ""), seg.get("value", ""), seg.get("color", "var(--muted)")
            bold = seg.get("bold", False)
            out.append(f'<text x="{fx}" y="{fy}" fill="{color}" font-size="11.5"{" font-weight=\"700\"" if bold else ""}>{txt}</text>')
            fx += max(len(txt) * 12, 90)
            if val:
                out.append(f'<text x="{fx}" y="{fy}" fill="{color}" font-size="12" font-weight="700">{val}</text>')
                fx += max(len(val) * 12, 80)
    out.append("</svg>")
    return "\n          ".join(out)


def vbar_compare(title: str, vbars: List[Dict[str, Any]], annotate: Optional[Dict[str, Any]] = None) -> str:
    """竖向对比柱（A/B 均值对比形态）。vbars: label/value/value_label/weight/sub。"""
    n = len(vbars)
    W = 980
    TOP, BOT = 56, 52
    H = 360
    vmax = max(v["value"] for v in vbars) * 1.18
    plot_h = H - TOP - BOT
    zone_w = (W - 160) / n
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{title}">']
    # 横向刻度
    for i in range(5):
        y = TOP + plot_h * i / 4
        out.append(f'<line x1="80" y1="{y:.1f}" x2="{W - 40}" y2="{y:.1f}" stroke="var(--line)" stroke-width="1"/>')
        val = vmax * (1 - i / 4)
        out.append(f'<text x="72" y="{y + 4:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="end">{val:.1f}</text>')
    for i, b in enumerate(vbars):
        cx = 80 + zone_w * i + zone_w / 2
        bw = min(zone_w * 0.44, 130)
        h = b["value"] / vmax * plot_h
        y = TOP + plot_h - h
        fill = WEIGHT_FILL.get(b.get("weight", "context"), "var(--series-context)")
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{fill}"/>')
        vl = b.get("value_label") or _fmt(b["value"])
        color = {"critical": "var(--critical)", "healthy": "var(--healthy)"}.get(b.get("weight", ""), "var(--ink)")
        out.append(f'<text x="{cx:.1f}" y="{y - 12:.1f}" fill="{color}" font-size="13" font-weight="700" text-anchor="middle">{vl}</text>')
        out.append(f'<text x="{cx:.1f}" y="{TOP + plot_h + 24:.1f}" fill="var(--ink)" font-size="12.5" font-weight="700" text-anchor="middle">{b["label"]}</text>')
        if b.get("sub"):
            out.append(f'<text x="{cx:.1f}" y="{TOP + plot_h + 42:.1f}" fill="var(--muted)" font-size="11.5" text-anchor="middle">{b["sub"]}</text>')
    if annotate:
        ax, ay = annotate.get("x", 0.5), annotate.get("y", 0.28)
        x, y = W * ax, H * ay
        out.append(f'<rect x="{x - 96:.1f}" y="{y - 20:.1f}" width="192" height="34" fill="var(--healthy-soft)" stroke="var(--healthy)" stroke-width="1"/>')
        t1, t2 = annotate.get("line1", ""), annotate.get("line2", "")
        out.append(f'<text x="{x:.1f}" y="{y - 4:.1f}" fill="var(--healthy)" font-size="12" font-weight="700" text-anchor="middle">{t1}</text>')
        out.append(f'<text x="{x:.1f}" y="{y + 9:.1f}" fill="var(--muted)" font-size="11" text-anchor="middle">{t2}</text>')
        # 连接线到实验柱顶
        out.append(f'<line x1="{x:.1f}" y1="{y + 14:.1f}" x2="{x:.1f}" y2="{y + 40:.1f}" stroke="var(--healthy)" stroke-width="1" stroke-dasharray="4 3"/>')
    out.append("</svg>")
    return "\n          ".join(out)


def render_chart(chart: Dict[str, Any]) -> str:
    """内建 hbar/vbar；其余型走 --chart-dir 注入的 chart_lib.RENDERERS。"""
    if chart["type"] == "hbar":
        return hbar_chart(chart["title"], chart["bars"], chart.get("footnote"))
    if chart["type"] == "vbar":
        return vbar_compare(chart["title"], chart["vbars"], chart.get("annotate"))
    lib = _load_chart_lib()
    if lib is not None and chart["type"] in getattr(lib, "RENDERERS", {}):
        return lib.RENDERERS[chart["type"]](chart)
    raise ValueError(
        f"未知图表类型: {chart['type']}（该型需 --chart-dir 指向含 chart_lib 的角色目录）")


# --------------------------------------------------------------------------- #
# HTML 组装
# --------------------------------------------------------------------------- #
SHAPE = {
    "critical": '<span class="shape shape-diamond" aria-hidden="true"></span>',
    "watch": '<span class="shape shape-triangle" aria-hidden="true"></span>',
    "healthy": '<span class="shape shape-circle" aria-hidden="true"></span>',
    "accent": '<span class="shape shape-accent" aria-hidden="true"></span>',
    "none": "",
}


def esc(s: Any) -> str:
    s = "" if s is None else str(s)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))

def render(c: Dict[str, Any]) -> str:
    parts: List[str] = []
    A = parts.append
    A('<!doctype html>')
    A(f'<html lang="zh-CN" data-style="internet-reporting" data-palette="graphite-cobalt">')
    A('<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">')
    A(f'<title>{esc(c["title_lines"][0])}</title>')
    A(f'<style>{CSS}</style></head>')
    A('<body><main class="document">')

    # -- header
    A('<header class="doc-header">')
    A('<div class="doc-type"><span class="doc-glyph" aria-hidden="true"><i></i><i></i><i></i></span>')
    A(f'<span>{esc(c["doc_type"])}</span></div>')
    A('<h1>')
    for line in c["title_lines"]:
        A(f'<span class="title-line">{esc(line)}</span>')
    A('</h1>')
    A(f'<p class="standfirst">{esc(c["standfirst"])}</p>')
    A('<div class="doc-meta" aria-label="文档信息">')
    for m in c.get("meta", []):
        A(f'<span>{esc(m)}</span>')
    A('</div></header>')

    # -- optional TOC（仅 contract.toc 为真时输出，避免影响既有报告）
    if c.get("toc"):
        A('<nav class="doc-toc" aria-label="目录"><ol>')
        for s in c["sections"]:
            if s.get("appendix"):
                continue
            A(f'<li><a href="#section-{esc(s["index"])}">{esc(s["title"])}</a></li>')
        A('</ol></nav>')

    # -- metric strip
    A('<section class="metric-strip page-grid" aria-label="数据速览">')
    for m in c["metric_strip"]:
        status = m.get("status", "none")
        cls = f" {status}" if status in ("critical", "watch", "healthy") else ""
        A(f'<div class="metric">')
        A(f'<span class="metric-label">{SHAPE.get(status, "")}{esc(m["label"])}</span>')
        A(f'<strong class="metric-value{cls}">{esc(m["value"])}</strong>')
        if m.get("microbar") is not None:
            pct = int(m["microbar"] * 100)
            A(f'<div class="microbar" role="img" aria-label="已完成百分之{pct}"><span style="width:{pct}%"></span></div>')
        A(f'<small class="metric-note">{esc(m["note"])}</small></div>')
    A('</section>')

    # -- summary
    A('<section class="summary page-grid" aria-labelledby="summary-title">')
    A('<h2 class="summary-label" id="summary-title">全文结论</h2>')
    A('<div class="summary-copy">')
    paras = c["summary"]
    for i, p in enumerate(paras):
        close = ' summary-close' if i == len(paras) - 1 else ""
        mark = f'<mark>{esc(p["mark"])}</mark>' if p.get("mark") else ""
        body = esc(p["text"])
        if mark:
            body = body.replace(esc(p["mark"]), mark, 1)
        label = f'<strong>{esc(p["label"])}</strong>'
        A(f'<p{(" class=\"" + close.strip() + "\"") if close else ""}>{label}{body}</p>')
    A('</div></section>')

    # -- sections
    for s in c["sections"]:
        sid = f'section-{s["index"]}'
        if s.get("appendix"):
            A(f'<details class="report-appendix" id="{sid}"><summary>附录 · {esc(s["title"])}</summary>')
        else:
            A(f'<section class="report-section" id="{sid}">')
        A('<header class="section-head">')
        A(f'<div class="section-index">{esc(s["index"])}</div>')
        A('<div class="section-heading-copy">')
        A(f'<h2 class="section-title">{esc(s["title"])}</h2>')
        A(f'<p class="section-question">{esc(s["question"])}</p>')
        A('</div></header>')
        if s.get("intro"):
            A('<div class="page-grid"><div class="section-intro">')
            for p in s["intro"]:
                strong = f'<strong>{esc(p["strong"])}</strong>' if p.get("strong") else ""
                A(f'<p>{strong}{esc(p["text"])}</p>')
            A('</div></div>')
        ch = s.get("chart")
        if ch:
            A('<figure class="embed">')
            A('<figcaption class="embed-head">')
            A(f'<div class="embed-title"><span class="embed-icon" aria-hidden="true"></span><span>{esc(ch["title"])}</span></div>')
            A(f'<div class="embed-meta">{esc(ch["unit_meta"])}</div>')
            A('</figcaption><div class="chart-wrap">')
            A(render_chart(ch))
            A('</div>')
            A(f'<div class="embed-source">{esc(ch["source"])}</div></figure>')
        # post-chart: reading + boundary
        if s.get("reading") or s.get("boundary"):
            A('<div class="post-chart page-grid">')
            if s.get("reading"):
                label = "图后解读" if s.get("chart") else "本节说明"
                A(f'<div class="reading-block"><h3>{label}</h3><ol class="reading-list">')
                for i, r in enumerate(s["reading"], 1):
                    strong = f'<strong>{esc(r["strong"])}</strong>' if r.get("strong") else ""
                    A(f'<li><span class="reading-no">{i}</span><span class="reading-text">{strong}{esc(r["text"])}</span></li>')
                A('</ol></div>')
            if s.get("boundary"):
                b = s["boundary"]
                A('<aside class="boundary-block">')
                A(f'<div class="boundary-label"><span class="shape shape-triangle" aria-hidden="true"></span>{esc(b.get("title", "证据边界"))}</div>')
                A(f'<p>{esc(b["text"])}</p></aside>')
            A('</div>')
        # evidence table
        t = s.get("table")
        if t:
            A(f'<div class="evidence-table-wrap"><table class="evidence-table" aria-label="{esc(t.get("caption", ""))}">')
            if t.get("col_widths"):
                A('<colgroup>' + ''.join(f'<col style="width:{w}">' for w in t["col_widths"]) + '</colgroup>')
            A('<thead><tr>')
            for h in t["columns"]:
                num = ' class="num"' if h.get("num") else ""
                A(f'<th{num}>{esc(h["text"])}</th>')
            A('</tr></thead><tbody>')
            for row in t["rows"]:
                A('<tr>')
                for cell in row:
                    if cell.get("row_label"):
                        mark = f'<span class="row-mark{(" " + cell["mark"]) if cell.get("mark") else ""}" aria-hidden="true"></span>'
                        A(f'<td><span class="row-label">{mark}{esc(cell["text"])}</span></td>')
                    elif cell.get("lines"):
                        A('<td>')
                        for ln in cell["lines"]:
                            A(f'<span class="cell-line"><span class="cell-key">{esc(ln["key"])}</span>{esc(ln["text"])}</span>')
                        A('</td>')
                    elif cell.get("num"):
                        cls = f' class="num {cell["delta"]}"' if cell.get("delta") else ' class="num"'
                        A(f'<td{cls}>{esc(cell["text"])}</td>')
                    else:
                        A(f'<td>{esc(cell["text"])}</td>')
                A('</tr>')
            A('</tbody></table></div>')
        if s.get("block_note"):
            bn = s["block_note"]
            A(f'<div class="block-note"><h3>{esc(bn["title"])}</h3><p>{esc(bn["text"])}</p></div>')
        A('</details>' if s.get("appendix") else '</section>')

    # -- notes
    A('<section class="notes page-grid" aria-labelledby="notes-title">')
    A('<h2 class="notes-label" id="notes-title">数据口径与说明</h2>')
    A(f'<details open><summary>{esc(c["notes"].get("summary", "口径、来源与证据边界"))}</summary>')
    A('<div class="notes-copy">')
    for it in c["notes"].get("items", []):
        label = f'<strong>{esc(it["label"])}</strong>' if it.get("label") else ""
        A(f'<p>{label}{esc(it["text"])}</p>')
    if c["notes"].get("tail"):
        A(f'<p>{esc(c["notes"]["tail"])}</p>')
    A('</div></details></section>')

    # -- footer
    A('<footer class="doc-footer">')
    for f in c["footer"]:
        A(f'<span>{esc(f)}</span>')
    A('</footer>')
    A('</main></body></html>')
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="共享确定性 HTML 报告渲染器（core）")
    ap.add_argument("--contract", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--chart-dir", default=None,
                    help="含 chart_lib.py 的角色目录（用于 46 型扩展图）")
    args = ap.parse_args()
    if args.chart_dir:
        set_chart_dir(args.chart_dir)
    with open(args.contract, encoding="utf-8") as f:
        c = json.load(f)
    errs = validate_contract(c)
    if errs:
        print(json.dumps({"ok": False, "errors": errs}, ensure_ascii=False))
        return 1
    try:
        html = render(c)
    except ValueError as e:
        print(json.dumps({"ok": False, "errors": [str(e)]}, ensure_ascii=False))
        return 1
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    print(json.dumps({"ok": True, "output": os.path.abspath(args.output),
                      "bytes": len(html.encode("utf-8")),
                      "sections": len(c["sections"]),
                      "metrics": len(c["metric_strip"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

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

THEMES = ("sticker", "paper", "editorial", "mono", "annual", "swiss", "slate", "noir")

CSS = """
    :root {
      --ink: #18211D; --ink-2: #2C3A33; --muted: #5F6B64; --faint: #8A948D;
      --paper: #FBFAF7; --card: #FFFFFF; --canvas: #F2F0E9;
      --line: #E4E0D6; --line-strong: #CFC9BC;
      --accent: #1F5C4A; --accent-2: #A8894F; --accent-soft: #EDF2EE;
      --critical: #A8322A; --critical-soft: #FBEDEB;
      --watch: #9A6A12; --watch-soft: #FBF3E4;
      --healthy: #146B52; --healthy-soft: #EAF4EF;
      --series-context: #8A948D; --series-reference: #B9B3A5;
      /* 兼容 38 型扩展图沿用的旧令牌 */
      --theme-base: #FBFAF7; --theme-primary: #18211D; --theme-accent: #1F5C4A;
      --surface: #F4F2EB; --surface-strong: #EBE8DF;
      --page-columns: 12; --page-gap: 22px;
    }
    * { box-sizing: border-box; }
    html { background: var(--canvas); scroll-behavior: smooth; }
    body {
      margin: 0; background: var(--paper); color: var(--ink);
      font-family: "PingFang SC", "Microsoft YaHei", "Microsoft YaHei UI", "Noto Sans SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15.2px; font-weight: 400; line-height: 1.8;
      -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;
      font-variant-numeric: tabular-nums;
    }
    a { color: inherit; }
    strong, b { font-weight: 600; }

    /* ---------- 封面 ---------- */
    .cover {
      position: relative; overflow: hidden; color: #fff;
      background: linear-gradient(135deg, #101D18 0%, #1F5C4A 62%, #6B5730 138%);
      padding: 58px 0 46px;
    }
    .cover::after {
      content: ""; position: absolute; right: -120px; top: -140px;
      width: 420px; height: 420px; border-radius: 50%;
      background: rgba(200, 168, 106, .14);
    }
    .wrap { max-width: 1040px; margin: 0 auto; padding: 0 30px; }
    .cover .wrap { position: relative; z-index: 1; }
    .kicker {
      display: inline-flex; align-items: center; gap: 10px;
      padding: 5px 14px; border: 1px solid rgba(255,255,255,.28);
      border-radius: 999px; background: rgba(255,255,255,.10);
      font-size: 12.2px; letter-spacing: .08em; color: rgba(255,255,255,.94);
    }
    .glyph { display: inline-flex; align-items: flex-end; gap: 2px; height: 12px; }
    .glyph i { width: 2.5px; background: #D8C08A; display: block; }
    .glyph i:nth-child(1) { height: 5px; }
    .glyph i:nth-child(2) { height: 11px; }
    .glyph i:nth-child(3) { height: 8px; }
    h1 {
      margin: 20px 0 0; font-size: 34px; line-height: 1.3;
      font-weight: 700; letter-spacing: -.02em; max-width: 900px;
    }
    .h1-sub {
      display: block; margin-top: 10px; font-size: 18.5px;
      font-weight: 400; letter-spacing: 0; color: rgba(255,255,255,.82);
    }
    .deck {
      margin: 18px 0 0; max-width: 780px; font-size: 15.2px;
      line-height: 1.75; color: rgba(255,255,255,.93);
    }
    .meta {
      display: flex; flex-wrap: wrap; gap: 8px 30px; margin-top: 26px;
      font-size: 12.2px; color: rgba(255,255,255,.80);
    }
    .meta span { position: relative; }
    .meta span + span::before {
      content: ""; position: absolute; left: -16px; top: 7px;
      width: 4px; height: 4px; border-radius: 50%; background: rgba(216,192,138,.75);
    }

    /* ---------- 正文 ---------- */
    main.wrap { padding-bottom: 84px; }
    .body-top { padding-top: 42px; }

    h2.sec {
      display: flex; align-items: baseline; gap: 12px;
      margin: 56px 0 10px; padding-left: 16px;
      border-left: 5px solid var(--accent-2);
      font-size: 22px; line-height: 1.42; font-weight: 700;
      letter-spacing: -.01em; color: var(--accent);
    }
    h2.sec .num {
      font-family: Georgia, "Times New Roman", serif;
      font-size: 20px; font-weight: 400; color: var(--accent-2);
      letter-spacing: .02em; min-width: 26px;
    }
    h3 { margin: 26px 0 8px; font-size: 16px; color: var(--ink-2); }
    p { margin: 11px 0; color: var(--ink-2); }
    .sec-lede { font-size: 15.8px; color: var(--ink); }

    .q {
      margin: 12px 0 20px; padding: 10px 16px;
      background: var(--accent-soft); border-left: 3px solid var(--accent);
      border-radius: 0 8px 8px 0; font-size: 13.6px; color: #2C4A40;
    }
    .q b { color: var(--accent); }

    /* ---------- 指标 ---------- */
    .kpis {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(178px, 1fr));
      gap: 14px; margin: 22px 0 6px;
    }
    .kpi {
      background: var(--card); border: 1px solid var(--line);
      border-radius: 14px; padding: 18px 18px 16px;
      box-shadow: 0 2px 10px rgba(31,92,74,.05);
    }
    .kpi .k { font-size: 12.2px; color: var(--muted); margin-bottom: 8px; }
    .kpi .v {
      font-size: 27px; font-weight: 700; line-height: 1.12;
      color: var(--accent); letter-spacing: -.02em;
    }
    .kpi .v small { font-size: 13px; font-weight: 600; margin-left: 2px; }
    .kpi .d { font-size: 11.8px; color: var(--faint); margin-top: 8px; line-height: 1.55; }
    .kpi.critical .v { color: var(--critical); }
    .kpi.watch .v { color: var(--watch); }
    .kpi.healthy .v { color: var(--healthy); }

    /* ---------- 结论卡 ---------- */
    .insight {
      background: var(--card); border: 1px solid var(--line);
      border-left: 5px solid var(--accent); border-radius: 12px;
      padding: 17px 21px; margin: 14px 0;
    }
    .insight.lead { padding: 20px 23px; }
    .insight .t { font-size: 14.4px; font-weight: 700; color: var(--accent); margin-bottom: 5px; }
    .insight p { margin: 4px 0; font-size: 14.4px; }
    .insight.lead p { font-size: 15.2px; }
    mark { background: #F6E3A8; color: #3A2C08; padding: 0 3px; border-radius: 3px; }

    /* ---------- 目录 ---------- */
    .toc {
      margin: 30px 0 0; padding: 13px 0;
      border-top: 1px solid var(--line-strong); border-bottom: 1px solid var(--line-strong);
      display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 5px 26px; font-size: 12.8px;
    }
    .toc a { color: var(--ink-2); text-decoration: none; border: 0; }
    .toc a:hover { color: var(--accent); }
    .toc .n { color: var(--accent-2); margin-right: 7px; font-family: Georgia, serif; }

    /* ---------- 图表 ---------- */
    .fig-card {
      background: var(--card); border: 1px solid var(--line);
      border-radius: 14px; margin: 22px 0 6px; overflow: hidden;
      box-shadow: 0 2px 10px rgba(31,92,74,.045);
    }
    .fig-head {
      display: flex; align-items: baseline; justify-content: space-between; gap: 18px;
      padding: 11px 18px; background: var(--surface);
      border-bottom: 1px solid var(--line); font-size: 12.6px; font-weight: 600;
    }
    .fig-unit { color: var(--muted); font-weight: 400; font-size: 11.8px; white-space: nowrap; }
    .fig-body { padding: 16px 16px 8px; overflow-x: auto; }
    .fig-body svg { display: block; width: 100%; height: auto; min-width: 660px; }
    .fig-src {
      padding: 8px 18px 12px; font-size: 11.6px; color: var(--faint);
      border-top: 1px dashed var(--line);
    }

    .reading { margin: 14px 0 4px; }
    .reading h3 {
      margin: 0 0 8px; font-size: 12.6px; font-weight: 700;
      color: var(--accent-2); letter-spacing: .10em;
    }
    .reading ol { margin: 0; padding: 0; list-style: none; counter-reset: rd; }
    .reading li {
      position: relative; padding-left: 30px; margin: 8px 0;
      font-size: 14.2px; line-height: 1.72; color: var(--ink-2);
    }
    .reading li::before {
      counter-increment: rd; content: counter(rd);
      position: absolute; left: 0; top: 3px; width: 20px; height: 20px;
      display: flex; align-items: center; justify-content: center;
      border-radius: 50%; background: var(--accent-soft);
      color: var(--accent); font-size: 11.4px; font-weight: 700;
    }
    .reading li strong { color: var(--ink); }

    /* ---------- 表 ---------- */
    .table-wrap { overflow-x: auto; margin: 14px 0 2px; }
    table { width: 100%; border-collapse: collapse; font-size: 13.2px; }
    th {
      background: #EFF2EE; color: var(--accent); font-weight: 600;
      padding: 10px 10px; text-align: right; font-size: 12.2px;
      border-bottom: 2px solid #D7DED6; white-space: nowrap;
    }
    th:first-child { text-align: left; }
    td {
      padding: 9px 10px; text-align: right; color: var(--ink-2);
      border-bottom: 1px solid #F0EEE7; vertical-align: top;
    }
    td:first-child { text-align: left; font-weight: 600; color: #173C32; white-space: nowrap; }
    tbody tr:hover td { background: #FAFBF8; }
    td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
    td.lines { text-align: left; }
    .tcap { margin: 6px 0 22px; font-size: 11.8px; color: var(--faint); }

    /* ---------- 边界 ---------- */
    .boundary {
      margin: 18px 0; padding: 12px 16px;
      background: #F7F5EF; border: 1px dashed var(--line-strong);
      border-radius: 10px; font-size: 12.8px; color: #5D665F;
    }
    .boundary b { color: #3B4A42; }

    /* ---------- 口径 ---------- */
    .notes { margin-top: 58px; }
    .notes-title {
      margin: 0 0 10px; padding-left: 16px;
      border-left: 5px solid var(--accent-2);
      font-size: 19px; color: var(--accent); letter-spacing: -.01em;
    }
    details {
      border: 1px solid var(--line); border-radius: 12px;
      background: var(--card); margin: 14px 0 0; overflow: hidden;
    }
    summary {
      cursor: pointer; padding: 13px 20px; font-weight: 600;
      color: var(--accent); font-size: 14px; list-style: none;
    }
    summary::-webkit-details-marker { display: none; }
    summary::before { content: "▸ "; color: var(--accent-2); }
    details[open] > summary::before { content: "▾ "; }
    .appendix .inner { padding: 2px 18px 12px; }
    .notes-copy { padding: 0 20px 16px; }
    .notes-copy p { margin: 6px 0; font-size: 13px; color: var(--muted); }
    .notes-copy strong { color: var(--ink-2); }

    footer {
      margin-top: 54px; padding-top: 20px; border-top: 1px solid var(--line-strong);
      display: flex; flex-wrap: wrap; gap: 8px 26px;
      font-size: 12.2px; color: var(--faint);
    }

    /* ================= 主题二：paper（白纸研究风，对齐水果系报告） ================= */
    body[data-theme="paper"] {
      --ink: #0F172A; --ink-2: #334155; --muted: #475569; --faint: #64748B;
      --paper: #FFFFFF; --canvas: #F8FAFC; --card: #FFFFFF;
      --line: #E2E8F0; --line-strong: #94A3B8;
      --accent: #B45309; --accent-2: #1F2937; --accent-soft: #FFFBEB;
      --critical: #B91C1C; --healthy: #15803D; --watch: #B45309;
      --surface: #F1F5F9; --surface-strong: #E2E8F0;
      --series-context: #94A3B8; --series-reference: #64748B;
      --theme-primary: #1F2937; --theme-accent: #B45309; --theme-base: #FFFFFF;
      background: #E9EDF2;
    }
    body[data-theme="paper"] .page {
      max-width: 1080px; margin: 28px auto 48px; background: #fff;
      border: 1px solid #DCE3EA; border-radius: 2px;
      box-shadow: 0 6px 30px rgba(15,23,42,.09); overflow: hidden;
    }
    body[data-theme="paper"] .cover {
      background: var(--paper); color: var(--ink);
      border-bottom: 2px solid var(--ink); padding: 42px 56px 24px;
    }
    body[data-theme="paper"] .cover .wrap { padding: 0; max-width: none; }
    body[data-theme="paper"] main.wrap { padding: 0 56px 56px; max-width: none; }
    body[data-theme="paper"] .cover::after { display: none; }
    body[data-theme="paper"] .kicker {
      background: var(--surface); border: 1px solid var(--line); color: var(--muted);
    }
    body[data-theme="paper"] .kicker .glyph i { background: var(--accent); }
    body[data-theme="paper"] h1 { font-size: 27px; letter-spacing: -.01em; }
    body[data-theme="paper"] .h1-sub { color: var(--muted); font-size: 16px; }
    body[data-theme="paper"] .deck { color: var(--muted); font-size: 15px; }
    body[data-theme="paper"] .meta { color: var(--muted); }
    body[data-theme="paper"] .meta span + span::before { background: var(--line-strong); }
    body[data-theme="paper"] .body-top { padding-top: 26px; }
    body[data-theme="paper"] .wrap { max-width: 1120px; }
    body[data-theme="paper"] h2.sec {
      margin: 40px 0 10px; padding: 22px 0 0; border-left: 0;
      border-top: 1px solid var(--line); font-size: 19px; color: var(--ink);
    }
    body[data-theme="paper"] h2.sec .num { color: var(--accent); font-size: 15px; }
    body[data-theme="paper"] .q {
      background: var(--surface); border-left: 3px solid var(--line-strong);
      color: var(--muted); border-radius: 0;
    }
    body[data-theme="paper"] .kpis {
      gap: 20px 0; border-top: 1px solid var(--line-strong);
      border-bottom: 1px solid var(--line-strong); padding: 18px 0; margin: 24px 0 4px;
    }
    body[data-theme="paper"] .kpi {
      background: transparent; border: 0; border-left: 2px solid var(--line);
      border-radius: 0; box-shadow: none; padding: 0 12px 0 14px;
    }
    body[data-theme="paper"] .kpi .v { color: var(--ink); font-size: 25px; }
    body[data-theme="paper"] .kpi.critical .v { color: var(--critical); }
    body[data-theme="paper"] .kpi.watch .v { color: var(--watch); }
    body[data-theme="paper"] .kpi.healthy .v { color: var(--healthy); }
    body[data-theme="paper"] .insight {
      background: var(--surface); border: 1px solid var(--line);
      border-left: 4px solid var(--ink); border-radius: 2px;
      box-shadow: none; padding: 16px 20px;
    }
    body[data-theme="paper"] .insight .t { color: var(--ink); }
    body[data-theme="paper"] .fig-card { border-radius: 3px; box-shadow: none; }
    body[data-theme="paper"] .fig-head { background: var(--surface); }
    body[data-theme="paper"] .reading h3 { color: var(--muted); }
    body[data-theme="paper"] .reading li::before {
      background: var(--surface); color: var(--accent);
    }
    body[data-theme="paper"] .boundary {
      background: #FFFBEB; border: 1px dashed #E2C08A; border-radius: 2px;
    }
    body[data-theme="paper"] th { background: var(--surface-strong); color: var(--ink); }
    body[data-theme="paper"] .notes-title { color: var(--ink); border-left-color: var(--accent); }
    body[data-theme="paper"] details { border-radius: 3px; }
    body[data-theme="paper"] summary { color: var(--ink); }

    /* ================= 主题三：mono（麦肯锡式黑白，纯排版） ================= */
    body[data-theme="mono"] {
      --ink: #111111; --ink-2: #1F1F1F; --muted: #555555; --faint: #777777;
      --paper: #FFFFFF; --canvas: #EDEDED; --card: #FFFFFF;
      --line: #DADADA; --line-strong: #111111;
      --accent: #111111; --accent-2: #111111; --accent-soft: #F2F2F2;
      --critical: #111111; --healthy: #555555; --watch: #333333;
      --surface: #F4F4F4; --surface-strong: #E8E8E8;
      --series-context: #9A9A9A; --series-reference: #C9C9C9;
      --theme-primary: #111111; --theme-accent: #111111; --theme-base: #FFFFFF;
      background: #EDEDED;
    }
    body[data-theme="mono"] .page {
      max-width: 1040px; margin: 26px auto 44px; background: #fff;
      border: 0; border-radius: 0; box-shadow: none;
    }
    body[data-theme="mono"] .cover {
      background: #fff; color: #111; border-bottom: 3px solid #111;
      padding: 44px 52px 22px;
    }
    body[data-theme="mono"] .cover::after { display: none; }
    body[data-theme="mono"] .cover .wrap { padding: 0; max-width: none; }
    body[data-theme="mono"] main.wrap { padding: 0 52px 56px; max-width: none; }
    body[data-theme="mono"] .kicker {
      background: #fff; border: 1px solid #111; color: #111;
      border-radius: 0; letter-spacing: .12em; font-weight: 600;
    }
    body[data-theme="mono"] .kicker .glyph i { background: #111; }
    body[data-theme="mono"] h1 { font-size: 31px; letter-spacing: -.015em; }
    body[data-theme="mono"] .h1-sub { color: #333; font-size: 17px; }
    body[data-theme="mono"] .deck { color: #333; }
    body[data-theme="mono"] .meta { color: #555; }
    body[data-theme="mono"] .meta span + span::before { background: #111; }
    body[data-theme="mono"] h2.sec {
      border-left: 0; border-top: 2px solid #111; padding: 20px 0 0;
      margin-top: 42px; color: #111; font-size: 20px;
    }
    body[data-theme="mono"] h2.sec .num {
      color: #111; font-family: inherit; font-size: 14px; font-weight: 700;
    }
    body[data-theme="mono"] .q {
      background: #fff; border-left: 0; border-bottom: 1px solid #DDD;
      border-radius: 0; padding: 4px 0 10px; color: #555;
    }
    body[data-theme="mono"] .kpis {
      gap: 0; border-top: 2px solid #111; border-bottom: 1px solid #111; padding: 16px 0;
    }
    body[data-theme="mono"] .kpi {
      background: #fff; border: 0; border-left: 1px solid #DADADA;
      border-radius: 0; box-shadow: none; padding: 0 14px;
    }
    body[data-theme="mono"] .kpi:first-child { border-left: 0; padding-left: 0; }
    body[data-theme="mono"] .kpi .v { color: #111; font-size: 30px; }
    body[data-theme="mono"] .kpi.critical .v,
    body[data-theme="mono"] .kpi.watch .v,
    body[data-theme="mono"] .kpi.healthy .v { color: #111; }
    body[data-theme="mono"] .insight {
      background: #fff; border: 0; border-top: 2px solid #111;
      border-radius: 0; box-shadow: none; padding: 14px 0 2px;
    }
    body[data-theme="mono"] .insight .t {
      color: #111; font-size: 12.5px; letter-spacing: .10em;
    }
    body[data-theme="mono"] .fig-card {
      border: 0; border-top: 2px solid #111; border-radius: 0; box-shadow: none;
    }
    body[data-theme="mono"] .fig-head { background: #fff; border-bottom: 1px solid #DDD; }
    body[data-theme="mono"] th { background: #fff; color: #111; border-bottom: 2px solid #111; }
    body[data-theme="mono"] td { border-bottom: 1px solid #E6E6E6; }
    body[data-theme="mono"] .boundary {
      background: #F7F7F7; border: 0; border-left: 3px solid #111; border-radius: 0;
    }
    body[data-theme="mono"] .notes-title { color: #111; border-left-color: #111; }

    /* ================= 主题四：annual（年报衬线，米纸+酒红+金线） ================= */
    body[data-theme="annual"] {
      --ink: #2B2118; --ink-2: #463726; --muted: #6B5A3E; --faint: #8C7A5C;
      --paper: #FCFAF4; --canvas: #EFE9DC; --card: #FCFAF4;
      --line: #E3D9C4; --line-strong: #B9A57E;
      --accent: #7A2E2E; --accent-2: #A8894F; --accent-soft: #F6F1E5;
      --critical: #8C2F2F; --healthy: #3F6B4A; --watch: #A8894F;
      --surface: #F6F1E5; --surface-strong: #EFE7D6;
      --series-context: #B9A57E; --series-reference: #DCCFB6;
      --theme-primary: #2B2118; --theme-accent: #7A2E2E; --theme-base: #FCFAF4;
      background: #EFE9DC;
    }
    body[data-theme="annual"] .page {
      max-width: 1040px; margin: 26px auto 44px; background: #FCFAF4;
      border: 1px solid #E3D9C4; border-radius: 0;
      box-shadow: 0 6px 28px rgba(60,40,20,.12);
    }
    body[data-theme="annual"] .cover {
      background: #FCFAF4; color: #2B2118;
      border-bottom: 3px double #A8894F; padding: 44px 54px 24px;
    }
    body[data-theme="annual"] .cover::after { display: none; }
    body[data-theme="annual"] .cover .wrap { padding: 0; max-width: none; }
    body[data-theme="annual"] main.wrap { padding: 0 54px 56px; max-width: none; }
    body[data-theme="annual"] h1,
    body[data-theme="annual"] h2.sec,
    body[data-theme="annual"] .h1-sub {
      font-family: Georgia, "Songti SC", "SimSun", "Times New Roman", serif;
    }
    body[data-theme="annual"] h1 { font-size: 32px; }
    body[data-theme="annual"] .h1-sub { color: #6B5A3E; font-size: 17px; }
    body[data-theme="annual"] .kicker {
      background: transparent; border: 1px solid #B9A57E; color: #6B5A3E;
      border-radius: 0; letter-spacing: .14em;
    }
    body[data-theme="annual"] .kicker .glyph i { background: #7A2E2E; }
    body[data-theme="annual"] .deck { color: #4A3B2A; }
    body[data-theme="annual"] .meta { color: #6B5A3E; }
    body[data-theme="annual"] .meta span + span::before { background: #A8894F; }
    body[data-theme="annual"] h2.sec {
      border-left: 0; border-bottom: 1px solid #DCCFB6; padding: 0 0 8px;
      margin-top: 44px; color: #3A2C1E; font-size: 21px;
    }
    body[data-theme="annual"] h2.sec .num { color: #A8894F; }
    body[data-theme="annual"] .q {
      background: #F6F1E5; border-left: 3px solid #A8894F; color: #5A4630;
      border-radius: 0;
    }
    body[data-theme="annual"] .kpis {
      gap: 0; border-top: 2px solid #A8894F; border-bottom: 1px solid #DCCFB6; padding: 16px 0;
    }
    body[data-theme="annual"] .kpi {
      background: transparent; border: 0; border-left: 1px solid #E3D9C4;
      border-radius: 0; box-shadow: none; padding: 0 14px;
    }
    body[data-theme="annual"] .kpi:first-child { border-left: 0; padding-left: 0; }
    body[data-theme="annual"] .kpi .v {
      font-family: Georgia, serif; color: #7A2E2E; font-size: 29px;
    }
    body[data-theme="annual"] .insight {
      background: #F6F1E5; border: 1px solid #E3D9C4;
      border-left: 4px solid #7A2E2E; border-radius: 0; box-shadow: none;
    }
    body[data-theme="annual"] .insight .t { color: #7A2E2E; }
    body[data-theme="annual"] .fig-card {
      border: 1px solid #E3D9C4; border-radius: 0; box-shadow: none; background: #FCFAF4;
    }
    body[data-theme="annual"] .fig-head { background: #F6F1E5; border-bottom: 1px solid #E3D9C4; }
    body[data-theme="annual"] th { background: #F3EDDF; color: #5A4630; border-bottom: 1.5px solid #A8894F; }
    body[data-theme="annual"] td { border-bottom: 1px solid #EDE4D2; }
    body[data-theme="annual"] .boundary { background: #F6F1E5; border: 1px dashed #C9B78F; border-radius: 0; }

    /* ================= 主题五：swiss（瑞士网格，红黑大字号） ================= */
    body[data-theme="swiss"] {
      --ink: #000000; --ink-2: #1A1A1A; --muted: #444444; --faint: #6B6B6B;
      --paper: #FFFFFF; --canvas: #F0F0F0; --card: #FFFFFF;
      --line: #D8D8D8; --line-strong: #000000;
      --accent: #E30613; --accent-2: #000000; --accent-soft: #F5F5F5;
      --critical: #E30613; --healthy: #00693E; --watch: #8A6A00;
      --surface: #F4F4F4; --surface-strong: #E9E9E9;
      --series-context: #8A8A8A; --series-reference: #C4C4C4;
      --theme-primary: #000000; --theme-accent: #E30613; --theme-base: #FFFFFF;
      background: #F0F0F0;
    }
    body[data-theme="swiss"] .page {
      max-width: 1080px; margin: 24px auto 44px; background: #fff;
      border: 0; border-radius: 0; box-shadow: 0 4px 24px rgba(0,0,0,.10);
    }
    body[data-theme="swiss"] .cover {
      background: #fff; color: #000; border-bottom: 8px solid #E30613;
      padding: 42px 48px 24px;
    }
    body[data-theme="swiss"] .cover::after { display: none; }
    body[data-theme="swiss"] .cover .wrap { padding: 0; max-width: none; }
    body[data-theme="swiss"] main.wrap { padding: 0 48px 56px; max-width: none; }
    body[data-theme="swiss"] .kicker {
      background: #000; border: 0; color: #fff; border-radius: 0;
      letter-spacing: .18em; font-weight: 700;
    }
    body[data-theme="swiss"] .kicker .glyph i { background: #E30613; }
    body[data-theme="swiss"] h1 {
      font-size: 38px; line-height: 1.14; letter-spacing: -.03em; font-weight: 800;
    }
    body[data-theme="swiss"] .h1-sub { color: #000; font-size: 19px; }
    body[data-theme="swiss"] .deck { color: #222; }
    body[data-theme="swiss"] .meta { color: #444; }
    body[data-theme="swiss"] .meta span + span::before { background: #E30613; }
    body[data-theme="swiss"] h2.sec {
      border-left: 0; border-top: 1px solid #000; padding-top: 14px;
      color: #000; font-size: 21px;
    }
    body[data-theme="swiss"] h2.sec .num {
      color: #E30613; font-family: inherit; font-weight: 800; font-size: 26px;
    }
    body[data-theme="swiss"] .q {
      background: #fff; border-left: 6px solid #E30613; border-radius: 0;
      color: #333; padding: 6px 14px;
    }
    body[data-theme="swiss"] .kpis {
      gap: 0; border-top: 1px solid #000; border-bottom: 1px solid #000; padding: 14px 0;
    }
    body[data-theme="swiss"] .kpi {
      background: #fff; border: 0; border-left: 1px solid #DDD;
      border-radius: 0; box-shadow: none; padding: 0 14px;
    }
    body[data-theme="swiss"] .kpi:first-child { border-left: 0; padding-left: 0; }
    body[data-theme="swiss"] .kpi .v { color: #000; font-weight: 800; }
    body[data-theme="swiss"] .insight {
      background: #fff; border: 0; border-left: 6px solid #000;
      border-radius: 0; box-shadow: none; padding: 12px 18px;
    }
    body[data-theme="swiss"] .insight .t { color: #E30613; letter-spacing: .08em; }
    body[data-theme="swiss"] .fig-card {
      border: 0; border-top: 2px solid #000; border-radius: 0; box-shadow: none;
    }
    body[data-theme="swiss"] .fig-head { background: #fff; border-bottom: 1px solid #000; }
    body[data-theme="swiss"] th { background: #000; color: #fff; border: 0; }
    body[data-theme="swiss"] td { border-bottom: 1px solid #E2E2E2; }
    body[data-theme="swiss"] .boundary { background: #fff; border: 1px dashed #000; border-radius: 0; }

    /* ================= 主题六：slate（科技商务，深蓝+亮蓝） ================= */
    body[data-theme="slate"] {
      --ink: #0B1220; --ink-2: #1E293B; --muted: #475569; --faint: #64748B;
      --paper: #FFFFFF; --canvas: #EEF2F8; --card: #FFFFFF;
      --line: #E2E8F0; --line-strong: #CBD5E1;
      --accent: #2563EB; --accent-2: #1E40AF; --accent-soft: #EFF6FF;
      --critical: #DC2626; --healthy: #059669; --watch: #D97706;
      --surface: #F8FAFC; --surface-strong: #F1F5F9;
      --series-context: #94A3B8; --series-reference: #CBD5E1;
      --theme-primary: #0B1220; --theme-accent: #2563EB; --theme-base: #FFFFFF;
      background: #EEF2F8;
    }
    body[data-theme="slate"] .page {
      max-width: 1080px; margin: 26px auto 46px; background: #fff;
      border: 1px solid #E2E8F0; border-radius: 14px;
      box-shadow: 0 12px 34px rgba(15,23,42,.12); overflow: hidden;
    }
    body[data-theme="slate"] .cover {
      background: linear-gradient(135deg, #0B1220 0%, #1E293B 68%, #334155 130%);
      color: #fff; padding: 52px 52px 34px; border-bottom: 0;
    }
    body[data-theme="slate"] .cover .wrap { padding: 0; max-width: none; }
    body[data-theme="slate"] main.wrap { padding: 0 52px 56px; max-width: none; }
    body[data-theme="slate"] .kicker {
      background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.22);
      color: rgba(255,255,255,.92);
    }
    body[data-theme="slate"] .kicker .glyph i { background: #60A5FA; }
    body[data-theme="slate"] .h1-sub { color: rgba(255,255,255,.82); }
    body[data-theme="slate"] .deck { color: rgba(255,255,255,.90); }
    body[data-theme="slate"] .meta { color: rgba(255,255,255,.72); }
    body[data-theme="slate"] .meta span + span::before { background: #60A5FA; }
    body[data-theme="slate"] h2.sec { color: #0B1220; border-left-color: #2563EB; }
    body[data-theme="slate"] .q { background: #EFF6FF; border-left-color: #2563EB; color: #1E3A8A; }
    body[data-theme="slate"] .kpi { border-radius: 14px; box-shadow: 0 4px 16px rgba(15,23,42,.06); }
    body[data-theme="slate"] .kpi .v { color: #2563EB; }
    body[data-theme="slate"] .insight { border-left-color: #2563EB; border-radius: 12px; }
    body[data-theme="slate"] .insight .t { color: #1E40AF; }
    body[data-theme="slate"] .fig-card { border-radius: 0 0 14px 14px; border-color: #E2E8F0; }
    body[data-theme="slate"] .fig-head { background: #F8FAFC; }

    /* ================= 主题七：noir（深色高端，炭黑+香槟金） ================= */
    body[data-theme="noir"] {
      --ink: #EDEAE3; --ink-2: #CFCAC0; --muted: #9A9488; --faint: #6E6A62;
      --paper: #121418; --canvas: #0B0C0E; --card: #171A1F;
      --line: #2A2E35; --line-strong: #3A3F47;
      --accent: #C9A227; --accent-2: #C9A227; --accent-soft: #1E2126;
      --critical: #D46A5F; --healthy: #6FBF9A; --watch: #C9A227;
      --surface: #1A1D22; --surface-strong: #22262C;
      --series-context: #8C877C; --series-reference: #5E5A52;
      --theme-primary: #EDEAE3; --theme-accent: #C9A227; --theme-base: #121418;
      background: #0B0C0E;
    }
    body[data-theme="noir"] .page {
      max-width: 1060px; margin: 26px auto 46px; background: #121418;
      border: 1px solid #24272D; border-radius: 2px;
      box-shadow: 0 14px 44px rgba(0,0,0,.55);
    }
    body[data-theme="noir"] .cover {
      background: linear-gradient(160deg, #0B0C0E 0%, #15171B 62%, #1E1A12 130%);
      border-bottom: 1px solid #C9A227; padding: 50px 52px 32px;
    }
    body[data-theme="noir"] .cover .wrap { padding: 0; max-width: none; }
    body[data-theme="noir"] main.wrap { padding: 0 52px 56px; max-width: none; }
    body[data-theme="noir"] .kicker {
      background: rgba(201,162,39,.08); border: 1px solid rgba(201,162,39,.4); color: #E6D8AE;
    }
    body[data-theme="noir"] .kicker .glyph i { background: #C9A227; }
    body[data-theme="noir"] h1 { color: #F4F1EA; }
    body[data-theme="noir"] .h1-sub { color: #BDB8AD; }
    body[data-theme="noir"] .deck { color: #BDB8AD; }
    body[data-theme="noir"] .meta { color: #8F8A80; }
    body[data-theme="noir"] .meta span + span::before { background: #C9A227; }
    body[data-theme="noir"] h2.sec { color: #EDEAE3; border-left-color: #C9A227; }
    body[data-theme="noir"] h2.sec .num { color: #C9A227; }
    body[data-theme="noir"] .q { background: #1A1D22; border-left-color: #C9A227; color: #CFCAC0; }
    body[data-theme="noir"] .kpi { background: #171A1F; border-color: #2A2E35; box-shadow: none; }
    body[data-theme="noir"] .kpi .v { color: #E9C46A; }
    body[data-theme="noir"] .insight { background: #171A1F; border-color: #2A2E35; border-left-color: #C9A227; }
    body[data-theme="noir"] .insight .t { color: #C9A227; }
    body[data-theme="noir"] .fig-card { background: #171A1F; border-color: #2A2E35; }
    body[data-theme="noir"] .fig-head { background: #1A1D22; border-color: #2A2E35; }
    body[data-theme="noir"] th { background: #1E2126; color: #C9A227; border-bottom-color: #3A3F47; }
    body[data-theme="noir"] td { border-bottom-color: #24272D; }
    body[data-theme="noir"] .boundary { background: #171A1F; border-color: #3A3F47; color: #BDB8AD; }
    body[data-theme="noir"] .notes-title { color: #EDEAE3; border-left-color: #C9A227; }
    body[data-theme="noir"] details { background: #171A1F; border-color: #2A2E35; }
    body[data-theme="noir"] .notes-copy p { color: #9A9488; }

    @media (max-width: 860px) {
      .wrap { padding: 0 20px; }
      .cover { padding: 40px 0 34px; }
      h1 { font-size: 26px; }
      .h1-sub { font-size: 16px; }
      .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .toc { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      h2.sec { font-size: 19px; margin-top: 44px; }
    }
    @media (max-width: 560px) {
      .kpis { grid-template-columns: 1fr; }
      .toc { grid-template-columns: 1fr; }
      .fig-body svg { min-width: 560px; }
    }
    /* ================= 默认主题：sticker（墨绿封面 + 粗黑描边 + 贴纸卡片） ================= */
    body[data-theme="sticker"] {
      --ink: #14231C; --ink-2: #24352C; --muted: #5B6B62; --faint: #7C8B81;
      --paper: #FFFFFF; --canvas: #F6F9F4; --card: #FFFFFF;
      --line: #DCE5DD; --line-strong: #14231C;
      --accent: #2F6F4F; --accent-2: #C99A1A; --accent-soft: #EEF6F0;
      --critical: #B02A20; --critical-soft: #FDEDEA;
      --watch: #9A6A12; --watch-soft: #FDF3DE;
      --healthy: #1E7A57; --healthy-soft: #E8F5EE;
      --series-context: #8A948D; --series-reference: #C4BBAA;
      --theme-base: #FFFFFF; --theme-primary: #14231C; --theme-accent: #2F6F4F;
      --surface: #F1F7F2; --surface-strong: #E6F0E8;
      background:
        radial-gradient(circle at 1px 1px, rgba(47,111,79,.045) 1.2px, transparent 1.3px) 0 0/28px 28px,
        var(--paper);
    }
    body[data-theme="sticker"] .cover {
      background: linear-gradient(135deg, #0E2F22 0%, #2F6F4F 100%);
      margin: 28px auto 0; max-width: 1040px; border-radius: 26px;
      box-shadow: 8px 10px 0 rgba(20,35,28,.12);
      padding: 46px 0 40px; border-bottom: 7px solid #FFD43B;
    }
    body[data-theme="sticker"] .cover .wrap { padding: 0 44px; }
    body[data-theme="sticker"] h1 { font-size: clamp(30px, 3.9vw, 46px); line-height: 1.14; font-weight: 900; letter-spacing: -.03em; text-wrap: balance; }
    /* 长标题自动降档：中文标题超过 22 字时不再用 46px，避免三行压满封面 */
    body[data-theme="sticker"] h1.long { font-size: clamp(20px, 2.1vw, 28px); line-height: 1.32; letter-spacing: -.01em; }
    body[data-theme="sticker"] h1 .hl { font-style: normal; background: #FFD43B; color: #14231C; padding: 0 .07em; border-radius: 4px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
    /* 黄色下划线样式：不要色块，只要一条标记笔式的底线 */
    body[data-theme="sticker"] h1.hl-under .hl,
    h1.hl-under .hl {
      background: none; color: inherit; padding: 0 .02em; border-radius: 0;
      border-bottom: .14em solid #FFD43B; box-decoration-break: clone;
      -webkit-box-decoration-break: clone;
    }
    body[data-theme="sticker"] .h1-sub { font-size: 19px; margin-top: 12px; color: rgba(255,255,255,.88); }
    body[data-theme="sticker"] .deck { font-size: 16.5px; line-height: 1.78; max-width: 720px; }
    body[data-theme="sticker"] .meta { gap: 8px; margin-top: 24px; }
    body[data-theme="sticker"] .meta span {
      border: 1px solid rgba(255,255,255,.38); border-radius: 999px;
      padding: 5px 12px; font-size: 12px; color: rgba(255,255,255,.92);
    }
    body[data-theme="sticker"] .meta span + span::before { display: none; }
    body[data-theme="sticker"] main.wrap { max-width: 1040px; padding: 0 0 96px; margin: 0 auto; }
    @media (max-width: 1120px) {
      body[data-theme="sticker"] .cover { margin: 18px 18px 0; max-width: none; }
      body[data-theme="sticker"] main.wrap { padding: 0 24px 80px; max-width: none; }
    }
    @media (max-width: 720px) {
      body[data-theme="sticker"] .cover { margin: 12px 12px 0; border-radius: 18px; padding: 30px 0 28px; }
      body[data-theme="sticker"] .cover .wrap { padding: 0 22px; }
      body[data-theme="sticker"] main.wrap { padding: 0 16px 70px; }
    }
    body[data-theme="sticker"] .cover::after { background: rgba(255,255,255,.08); }
    body[data-theme="sticker"] .kicker { border-color: rgba(255,255,255,.42); background: rgba(255,255,255,.12); }
    body[data-theme="sticker"] .glyph i { background: #FFD43B; }
    body[data-theme="sticker"] h1 { font-weight: 800; letter-spacing: -.025em; }
    body[data-theme="sticker"] .h1-sub { font-weight: 500; }
    body[data-theme="sticker"] h2.sec {
      border-left: 0; padding-left: 0; align-items: center; color: #14231C; font-weight: 800;
    }
    body[data-theme="sticker"] h2.sec .num {
      font-family: inherit; font-size: 12px; font-weight: 800; color: #fff;
      background: #14231C; border-radius: 7px; padding: 3px 8px; min-width: 0;
    }
    body[data-theme="sticker"] .q {
      border: 1.5px solid #14231C; border-left: 6px solid var(--accent);
      border-radius: 12px; background: var(--accent-soft); color: #24352C;
      box-shadow: 2px 2px 0 rgba(20,35,28,.08);
    }
    body[data-theme="sticker"] .kpis { gap: 16px; }
    body[data-theme="sticker"] .kpi {
      border: 2px solid #14231C; border-radius: 16px;
      box-shadow: 4px 5px 0 rgba(20,35,28,.10);
    }
    body[data-theme="sticker"] .insight {
      border: 2px solid #14231C; border-left: 6px solid var(--accent);
      border-radius: 14px; box-shadow: 3px 4px 0 rgba(20,35,28,.08);
    }
    body[data-theme="sticker"] .fig-card {
      border: 2px solid #14231C; border-radius: 16px;
      box-shadow: 4px 5px 0 rgba(20,35,28,.10);
    }
    body[data-theme="sticker"] .fig-head { background: var(--surface); border-bottom: 2px solid #14231C; }
    body[data-theme="sticker"] .table-wrap {
      border: 2px solid #14231C; border-radius: 14px; background: #fff;
      box-shadow: 3px 4px 0 rgba(20,35,28,.08);
    }
    body[data-theme="sticker"] table { margin: 0; }
    body[data-theme="sticker"] th { background: var(--surface-strong); color: #14231C; border-bottom: 2px solid #14231C; }
    body[data-theme="sticker"] td { border-bottom: 1px solid #E4EBE5; }
    body[data-theme="sticker"] td:first-child { color: #14231C; }
    body[data-theme="sticker"] .boundary {
      background: #FFFBEB; border: 1.5px dashed #C99A1A; border-radius: 12px; color: #5B4A1F;
    }
    body[data-theme="sticker"] .boundary b { color: #3E3212; }
    body[data-theme="sticker"] .toc {
      border-top: 2px dashed rgba(20,35,28,.25); border-bottom: 2px dashed rgba(20,35,28,.25);
    }
    body[data-theme="sticker"] .notes-title { border-left: 0; padding-left: 0; }
    body[data-theme="sticker"] details { border: 2px solid #14231C; border-radius: 14px; }
    body[data-theme="sticker"] summary { color: #14231C; }
    body[data-theme="sticker"] footer { border-top: 2px dashed rgba(20,35,28,.25); }
    body[data-theme="sticker"] mark { background: #FFD43B; }

    @media print {
      @page { size: A4; margin: 16mm 15mm; }
      * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      html, body { background: #fff; }
      body[data-theme="editorial"] .cover { background: linear-gradient(135deg, #101D18 0%, #1F5C4A 62%, #6B5730 138%) !important; }
      .cover { break-after: page; }
      .page { margin: 0 !important; max-width: none !important; border: 0 !important; box-shadow: none !important; }
      body[data-theme="paper"] { background: #fff !important; }
      body[data-theme="sticker"] { background: #fff !important; }
      body[data-theme="sticker"] .cover {
        background: linear-gradient(135deg, #0E2F22 0%, #2F6F4F 100%) !important;
        margin: 0 !important; max-width: none !important; border-radius: 0 !important; box-shadow: none !important;
        border-bottom: 7px solid #FFD43B !important;
        min-height: 250mm; display: flex; align-items: center;
      }
      body[data-theme="sticker"] .cover .wrap { width: 100%; }
      body[data-theme="sticker"] .cover::before { display: none; }
      body[data-theme="sticker"] main.wrap { padding: 0 0 40px !important; max-width: none !important; }
      .fig-card, .kpi, .insight { break-inside: avoid; box-shadow: none; }
      h2.sec { break-after: avoid; }
      a { text-decoration: none; }
    }
"""

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

def _auto_highlight(title: str) -> str:
    """没有显式 title_highlight 时，取标题末段做高亮：优先冒号后，其次问句主语，最后逗号后。"""
    if "｜" in title:
        return title.rsplit("｜", 1)[1]
    if "：" in title:
        return title.rsplit("：", 1)[1]
    if "？" in title:
        body = title.rsplit("？", 1)[0]
        for m in ("还是", "能不能", "值不值得", "是不是", "有没有", "是否", "会不会", "能否"):
            i = body.rfind(m)
            if i >= 0:
                return title[i:]
        if "，" in body:
            return body.rsplit("，", 1)[1] + "？"
        return (body[-6:] + "？") if len(body) > 6 else title
    if "，" in title:
        return title.rsplit("，", 1)[1]
    return ""


def render(c: Dict[str, Any]) -> str:
    parts: List[str] = []
    A = parts.append
    A('<!doctype html>')
    A('<html lang="zh-CN">')
    A('<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">')
    A(f'<title>{esc(c["title_lines"][0])}</title>')
    A(f'<style>{CSS}</style></head>')
    theme = str(c.get("theme", "sticker"))
    if theme not in THEMES:
        theme = "sticker"
    A(f'<body data-theme="{theme}"><div class="page">')

    # ---------------- 封面 ----------------
    A('<header class="cover"><div class="wrap">')
    A(f'<div class="kicker"><span class="glyph"><i></i><i></i><i></i></span>{esc(c.get("doc_type", ""))}</div>')
    lines = c["title_lines"]
    sub = f'<span class="h1-sub">{esc(lines[1])}</span>' if len(lines) > 1 and lines[1] else ""
    t0 = esc(lines[0]).replace("\n", "<br>")
    hl = c.get("title_highlight")
    if hl is None:
        hl = _auto_highlight(lines[0])
    if hl:
        ehl = esc(hl)
        if ehl and ehl in t0:
            t0 = t0.replace(ehl, f'<em class="hl">{ehl}</em>', 1)
    _cls = []
    if len(lines[0].replace("\n", "")) > 18:
        _cls.append("long")
    if str(c.get("title_highlight_style") or "") == "underline":
        _cls.append("hl-under")
    _attr = f' class="{" ".join(_cls)}"' if _cls else ""
    A(f'<h1{_attr}>{t0}{sub}</h1>')
    if c.get("standfirst"):
        A(f'<p class="deck">{esc(c["standfirst"])}</p>')
    if c.get("meta"):
        A('<div class="meta">')
        for m in c["meta"]:
            A(f'<span>{esc(m)}</span>')
        A('</div>')
    A('</div></header>')

    A('<main class="wrap"><div class="body-top"></div>')

    # ---------------- 结论先行 ----------------
    sections = list(c["sections"])
    lead = None
    if sections and str(sections[0].get("title", "")).startswith("结论先行"):
        lead = sections.pop(0)
    for i, s in enumerate([x for x in sections if not x.get("appendix")], 1):
        s["index"] = i

    if c.get("summary") or lead:
        A('<section id="summary">')
        A('<h2 class="sec"><span class="num">00</span>结论先行</h2>')
        for i, p in enumerate(c.get("summary", [])):
            label = str(p.get("label", "") or "").rstrip("：:")
            body = esc(p["text"])
            if p.get("mark"):
                body = body.replace(esc(p["mark"]), f'<mark>{esc(p["mark"])}</mark>', 1)
            cls = "insight lead" if i == 0 else "insight"
            t = f'<div class="t">{esc(label)}</div>' if label else ""
            A(f'<div class="{cls}">{t}<p>{body}</p></div>')
        if lead and lead.get("reading"):
            A('<div class="reading"><h3>支撑事实</h3><ol>')
            for r in lead["reading"]:
                st = f'<strong>{esc(r["strong"])}</strong>' if r.get("strong") else ""
                A(f'<li>{st}{esc(r["text"])}</li>')
            A('</ol></div>')
        A('</section>')

    # ---------------- 指标带 ----------------
    if c.get("metric_strip"):
        n = len(c["metric_strip"])
        cols = n if n <= 5 else (3 if n == 6 else 4)
        A(f'<div class="kpis" style="grid-template-columns:repeat({cols},minmax(0,1fr))">')
        for m in c["metric_strip"]:
            status = m.get("status", "none")
            cls = f' {status}' if status in ("critical", "watch", "healthy") else ""
            A(f'<div class="kpi{cls}"><div class="k">{esc(m["label"])}</div>'
              f'<div class="v">{esc(m["value"])}</div>'
              f'<div class="d">{esc(m.get("note", ""))}</div></div>')
        A('</div>')

    # ---------------- 目录 ----------------
    visible = [s for s in sections if not s.get("appendix")]
    if len(visible) >= 3:
        A('<nav class="toc" aria-label="目录">')
        for s in visible:
            A(f'<a href="#s-{esc(s["index"])}"><span class="n">{esc(s["index"])}</span>{esc(s["title"])}</a>')
        A('</nav>')

    # ---------------- 分节 ----------------
    table_no = 0
    for s in sections:
        sid = f's-{s["index"]}'
        appendix = bool(s.get("appendix"))
        if appendix:
            A(f'<details class="appendix" id="{sid}"><summary>附录 {esc(s["index"])} · {esc(s["title"])}</summary>'
              '<div class="inner">')
        else:
            A(f'<section id="{sid}">')
            A(f'<h2 class="sec"><span class="num">{esc(s["index"])}</span>{esc(s["title"])}</h2>')
            q = str(s.get("question") or "")
            if q.startswith(str(s["title"]) + "："):
                q = q[len(str(s["title"])) + 1:]
            if q:
                A(f'<p class="q"><b>本节问题</b>　{esc(q)}</p>')

        intro = s.get("intro") or []
        for i, p in enumerate(intro):
            st = f'<strong>{esc(p["strong"])}</strong>' if p.get("strong") else ""
            cls = ' class="sec-lede"' if i == 0 else ""
            A(f'<p{cls}>{st}{esc(p["text"])}</p>')

        ch = s.get("chart")
        if ch:
            A('<figure class="fig-card">')
            A('<figcaption class="fig-head">')
            A(f'<span>{esc(ch["title"])}</span>')
            A(f'<span class="fig-unit">{esc(ch.get("unit_meta", ""))}</span>')
            A('</figcaption><div class="fig-body">')
            A(render_chart(ch))
            A('</div>')
            if ch.get("source"):
                A(f'<div class="fig-src">{esc(ch["source"])}</div>')
            A('</figure>')

        if s.get("reading"):
            label = "读图" if ch else ("缺口" if "边界" in str(s.get("title", "")) else "要点")
            A(f'<div class="reading"><h3>{label}</h3><ol>')
            for r in s["reading"]:
                st = f'<strong>{esc(r["strong"])}</strong>' if r.get("strong") else ""
                A(f'<li>{st}{esc(r["text"])}</li>')
            A('</ol></div>')

        if s.get("boundary"):
            b = s["boundary"]
            A(f'<div class="boundary"><b>{esc(b.get("title", "证据边界"))}</b>　{esc(b["text"])}</div>')

        t = s.get("table")
        if t:
            table_no += 1
            if t.get("caption"):
                A(f'<p class="tcap">表 {table_no} · {esc(t["caption"])}</p>')
            A('<div class="table-wrap"><table>')
            if t.get("col_widths"):
                A('<colgroup>' + ''.join(f'<col style="width:{w}">' for w in t["col_widths"]) + '</colgroup>')
            A('<thead><tr>')
            for h in t["columns"]:
                cls = ' class="num"' if h.get("num") else ""
                A(f'<th{cls}>{esc(h["text"])}</th>')
            A('</tr></thead><tbody>')
            for row in t["rows"]:
                A('<tr>')
                for cell in row:
                    if cell.get("row_label"):
                        A(f'<td>{esc(cell["text"])}</td>')
                    elif cell.get("lines"):
                        A('<td class="lines">')
                        for ln in cell["lines"]:
                            A(f'<span>{esc(ln.get("key", ""))}{esc(ln["text"])}</span><br>')
                        A('</td>')
                    elif cell.get("num"):
                        A(f'<td class="num">{esc(cell["text"])}</td>')
                    else:
                        A(f'<td>{esc(cell["text"])}</td>')
                A('</tr>')
            A('</tbody></table></div>')
            if not t.get("caption"):
                A('<p class="tcap">　</p>')

        A('</div></details>' if appendix else '</section>')

    # ---------------- 口径 ----------------
    if c.get("notes"):
        A('<section class="notes" id="notes">')
        A('<h3 class="notes-title">口径、来源与证据边界</h3>')
        A(f'<details open><summary>{esc(c["notes"].get("summary", "口径、来源与证据边界"))}</summary>')
        A('<div class="notes-copy">')
        for it in c["notes"].get("items", []):
            label = f'<strong>{esc(it["label"])}</strong>' if it.get("label") else ""
            A(f'<p>{label}{esc(it["text"])}</p>')
        if c["notes"].get("tail"):
            A(f'<p>{esc(c["notes"]["tail"])}</p>')
        A('</div></details></section>')

    # ---------------- 页脚 ----------------
    A('<footer>')
    for f in c.get("footer", []):
        A(f'<span>{esc(f)}</span>')
    A('</footer>')
    A('</main></div></body></html>')
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="共享确定性 HTML 报告渲染器（core）")
    ap.add_argument("--contract", required=False)
    ap.add_argument("--output", required=False)
    ap.add_argument("--chart-dir", default=None,
                    help="含 chart_lib.py 的角色目录（用于 46 型扩展图）")
    ap.add_argument("--theme", choices=list(THEMES), default=None,
                    help="版式主题：editorial 深色封面杂志风（默认）/ paper 白纸研究风")
    ap.add_argument("--list-themes", action="store_true",
                    help="列出全部版式主题后退出")
    args = ap.parse_args()
    if args.list_themes:
        print("\n".join(THEMES))
        return 0
    if not args.contract or not args.output:
        print(json.dumps({"ok": False, "errors": ["缺少 --contract/--output"]}, ensure_ascii=False))
        return 2
    if args.chart_dir:
        set_chart_dir(args.chart_dir)
    with open(args.contract, encoding="utf-8") as f:
        c = json.load(f)
    if args.theme:
        c["theme"] = args.theme
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

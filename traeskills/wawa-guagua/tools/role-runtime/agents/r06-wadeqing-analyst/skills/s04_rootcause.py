# -*- coding: utf-8 -*-
"""S04 根因与贡献度 —— 能力域 4。

整合自 data-analytics-skills 的 `root-cause-investigation`（drilldown + 贡献分解）。
主张：**贡献度 = (分段变化 / 总变化)**，并按 体积/率/结构(mix) 拆解的意识驱动，
先定位「谁在拉动整体变化」，再谈为何。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from . import _common as c

NAME = "rootcause"
DESC = "根因与贡献度：贡献分解 / 下钻与帕累托"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)

    d = act.add_parser("decompose", help="分段贡献分解：谁在拉动 before→after 的总变化")
    d.add_argument("--input", required=True)
    d.add_argument("--dim", required=True, help="分段维度列")
    d.add_argument("--value", required=True, help="指标数值列")
    d.add_argument("--period", required=True, help="区分前后期的列")
    d.add_argument("--before", required=True, help="period 列中「前期」的取值")
    d.add_argument("--after", required=True, help="period 列中「后期」的取值")

    dr = act.add_parser("drilldown", help="下钻 + 帕累托：维度对指标贡献排序")
    dr.add_argument("--input", required=True)
    dr.add_argument("--dim", required=True)
    dr.add_argument("--value", required=True)


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    if args.action == "decompose":
        return _decompose(rows, args.dim, args.value, args.period,
                          args.before, args.after)
    if args.action == "drilldown":
        return _drilldown(rows, args.dim, args.value)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _decompose(rows, dim, value, period, before, after):
    th = c.load_thresholds().get("rootcause", {})
    impact_min = th.get("impact_min_pct", 3.0)
    agg: Dict[str, Dict[str, float]] = defaultdict(lambda: {"before": 0.0, "after": 0.0})
    for r in rows:
        key = str(r.get(dim, ""))
        seg = "before" if str(r.get(period, "")) == before else "after"
        try:
            agg[key][seg] += float(r.get(value, 0) or 0)
        except (KeyError, ValueError):
            continue
    total_change = sum(v["after"] - v["before"] for v in agg.values())
    segments = []
    for k, v in agg.items():
        d = v["after"] - v["before"]
        pct = round(d / total_change * 100, 2) if total_change else 0.0
        segments.append({"segment": k, "before": round(v["before"], 2),
                         "after": round(v["after"], 2), "delta": round(d, 2),
                         "contribution_pct": pct,
                         "below_impact_min": abs(pct) < impact_min})
    segments.sort(key=lambda x: -abs(x["contribution_pct"]))
    return {"total_change": round(total_change, 2),
            "dimension": dim, "segments": segments,
            "impact_min_pct": impact_min,
            "note": "contribution_pct = (after-before)/总变化；正=拉动增长，负=拖累；"
                    "|contribution| < impact_min_pct 的分支判定为 minor，可停止下钻"}


def _drilldown(rows, dim, value):
    agg: Dict[str, float] = defaultdict(float)
    for r in rows:
        try:
            agg[str(r.get(dim, ""))] += float(r.get(value, 0) or 0)
        except (KeyError, ValueError):
            continue
    total = sum(agg.values())
    items = sorted(agg.items(), key=lambda kv: -kv[1])
    out, cum = [], 0.0
    for i, (k, v) in enumerate(items):
        cum += v
        share = v / total * 100 if total else 0.0
        out.append({"segment": k, "value": round(v, 2), "share_pct": round(share, 2),
                    "cum_share_pct": round(cum / total * 100, 2) if total else 0.0,
                    "rank": i + 1})
    # 帕累托：前 N 项贡献（阈值外置）
    pareto_cut = c.load_thresholds().get("rootcause", {}).get("pareto_threshold_pct", 80)
    top_n = 0
    cump = 0.0
    for it in out:
        cump += it["share_pct"]
        top_n += 1
        if cump >= pareto_cut:
            break
    return {"dimension": dim, "total": round(total, 2), "items": out,
            "pareto_top_n_for_80pct": top_n,
            "pareto_threshold_pct": pareto_cut}
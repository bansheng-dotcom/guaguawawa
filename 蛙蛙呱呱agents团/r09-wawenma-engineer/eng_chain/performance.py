# -*- coding: utf-8 -*-
"""第 8 段 Performance：剖析计划 + 性能预算 + 优化项。

先有基线，再定预算，最后才优化：没有基线的“优化”无法证明有效，
没有预算的“性能”无法验收。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import (ck, gate, md_table, nonempty_str, render_stage)


def build(brief: Dict[str, Any]) -> Dict[str, Any]:
    perf = brief.get("performance") or {}
    art: Dict[str, Any] = {
        "artifact": "performance",
        "stage": "performance",
        "project": brief.get("project", ""),
        "baseline": perf.get("baseline") or {},
        "budget": perf.get("budget") or {},
        "profiling": perf.get("profiling") or [],
        "optimizations": [{"item": o.get("item", ""),
                           "expected_gain": o.get("expected_gain", "")}
                          for o in perf.get("optimizations") or []],
        "measurement": perf.get("measurement") or {},
    }
    art["gate"] = check(art)
    return art


def check(art: Dict[str, Any]) -> Dict[str, Any]:
    """性能门禁：基线可用、预算优于基线、剖析≥2、优化≥2、测量方法明确。"""
    base = art.get("baseline") or {}
    budget = art.get("budget") or {}
    base_p95 = float(base.get("p95_ms", 0) or 0)
    budget_p95 = float(budget.get("p95_ms", 0) or 0)
    m = art.get("measurement") or {}
    checks = [
        ck(base_p95 > 0 and float(base.get("throughput_rps", 0) or 0) > 0,
           "有可复现基线（p95/吞吐）", "performance:baseline", "CRITICAL"),
        ck(budget_p95 > 0 and budget_p95 <= base_p95,
           "预算不高于基线，且给出目标值", "performance:budget", "CRITICAL"),
        ck(len(art.get("profiling") or []) >= 2,
           "≥2 项剖析计划", "performance:profiling", "CRITICAL"),
        ck(len(art.get("optimizations") or []) >= 2 and
           all(nonempty_str(o.get("item")) and nonempty_str(o.get("expected_gain"))
               for o in art.get("optimizations") or []),
           "≥2 个优化项并标注预期收益", "performance:optimizations", "CRITICAL"),
        ck(nonempty_str(m.get("method")) and nonempty_str(m.get("noise")),
           "测量方法与噪声控制明确", "performance:measurement", "CRITICAL"),
    ]
    return gate(checks, "performance")


def render(art: Dict[str, Any]) -> str:
    base, budget = art.get("baseline") or {}, art.get("budget") or {}
    opt_rows = [[o.get("item"), o.get("expected_gain")]
                for o in art.get("optimizations") or []]
    summary = (f"基线 p95={base.get('p95_ms')}ms / {base.get('throughput_rps')} rps；"
               f"预算 p95={budget.get('p95_ms')}ms / {budget.get('throughput_rps')} rps。")
    tables = [
        "## 剖析计划", "", "\n".join(f"- {x}" for x in art.get("profiling") or []),
        "", "## 优化项", "", md_table(["优化", "预期收益"], opt_rows),
        "", "## 测量", "",
        f"- 方法：{(art.get('measurement') or {}).get('method', '')}",
        f"- 噪声控制：{(art.get('measurement') or {}).get('noise', '')}",
    ]
    return render_stage(art, summary, tables)

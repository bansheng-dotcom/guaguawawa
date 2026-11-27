# -*- coding: utf-8 -*-
"""第 4 段 explore：按预注册的分母与分段出发现，不做归因结论。

方案 §13.4 的硬要求：
  - 分母与分段来自 plan，不得在看到数据后临时改；
  - 每个发现必须带分母定义、分母引用、分段来源；
  - 只描述“发生了什么”，不解释“为什么”。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from skills import _common as c

from .common import ck, gate, now_iso


def _period(date_str: str, split: str) -> str:
    d = str(date_str)[:10]
    return "before" if d <= split else "after"


def build(data_path: str, plan: Dict[str, Any], date: Optional[str] = None,
          stage: Optional[str] = None, stage_order: Optional[str] = None,
          qty: Optional[str] = None, cost: Optional[str] = None) -> Dict[str, Any]:
    pg = plan.get("gate") or {}
    if not pg.get("ok"):
        return {"artifact": "findings", "gate": gate(
            [ck(False, "plan 门禁未通过，不能进入 explore", "upstream", "CRITICAL")],
            "explore")}
    rows = c.load_csv(data_path)
    if not rows:
        return {"artifact": "findings", "gate": gate(
            [ck(False, "空数据或无法读取", "existence", "CRITICAL")], "explore")}
    fields = list(rows[0].keys())
    metric = plan.get("metric", "")
    dims = [d for d in (plan.get("dimensions") or []) if d in fields]
    split = plan.get("split", "")
    date_col = date or "date"
    if metric not in fields:
        return {"artifact": "findings", "gate": gate(
            [ck(False, f"指标列 {metric} 不存在", "schema", "CRITICAL")], "explore")}
    if not split or date_col not in fields:
        return {"artifact": "findings", "gate": gate(
            [ck(False, "缺少 split 或日期列，无法切分前后期", "window", "CRITICAL")],
            "explore")}

    ref = "plan.rounds[0].query_spec.group_by"
    findings: List[Dict[str, Any]] = []
    total = {"before": 0.0, "after": 0.0, "n_before": 0, "n_after": 0}
    daily: Dict[str, Dict[str, float]] = {}
    by_dim: Dict[str, Dict[str, Dict[str, float]]] = {d: {} for d in dims}
    funnel_counts: Dict[str, Dict[str, int]] = {}
    econ = {"before": {"revenue": 0.0, "cost": 0.0}, "after": {"revenue": 0.0, "cost": 0.0}}

    for r in rows:
        d = str(r.get(date_col, ""))[:10]
        if not d:
            continue
        per = _period(d, split)
        try:
            v = float(r.get(metric, 0) or 0)
        except ValueError:
            continue
        total[per] += v
        total[f"n_{per}"] += 1
        daily.setdefault(d, {"before": 0.0, "after": 0.0})[per] += v
        for dim in dims:
            seg = str(r.get(dim, ""))
            slot = by_dim[dim].setdefault(seg, {"before": 0.0, "after": 0.0,
                                                "n_before": 0, "n_after": 0})
            slot[per] += v
            slot[f"n_{per}"] += 1
        if stage and stage in fields:
            s = str(r.get(stage, ""))
            funnel_counts.setdefault(s, {"before": 0, "after": 0})[per] += 1
        if cost and cost in fields:
            try:
                econ[per]["revenue"] += v
                econ[per]["cost"] += float(r.get(cost, 0) or 0)
            except ValueError:
                pass

    def add(type_: str, segment: str, before: float, after: float, n1: int, n2: int,
            segment_definition: Dict[str, Any], denominator: str,
            denominator_value: float, extra: Optional[Dict[str, Any]] = None) -> None:
        delta = after - before
        findings.append({
            "id": f"F{len(findings) + 1}",
            "type": type_,
            "segment": segment,
            "metric": metric,
            "before": round(before, 2),
            "after": round(after, 2),
            "delta": round(delta, 2),
            "delta_pct": round(delta / before * 100, 2) if before else None,
            "denominator": denominator,
            "denominator_value": round(denominator_value, 2),
            "denominator_ref": "plan.rounds[0].query_spec.metrics[0]",
            "segment_definition": segment_definition,
            "evidence": {"rows_before": n1, "rows_after": n2,
                         "split": split, "date_column": date_col},
            **(extra or {}),
        })

    add("overall", "全部", total["before"], total["after"],
        total["n_before"], total["n_after"],
        {"column": "__all__", "values": ["全部"], "source": ref},
        "期内同口径总量（全部分段合计）", total["before"])

    for dim in dims:
        for seg, v in sorted(by_dim[dim].items(),
                             key=lambda kv: -abs(kv[1]["after"] - kv[1]["before"])):
            add("segment", seg, v["before"], v["after"],
                int(v["n_before"]), int(v["n_after"]),
                {"column": dim, "values": sorted(by_dim[dim]), "source": ref},
                "期内同口径总量（全部分段合计）", total["before"])

    series = [{"date": d, "period": "before" if d <= split else "after",
               "value": round(s["before"] + s["after"], 2)} for d, s in sorted(daily.items())]
    findings.append({
        "id": f"F{len(findings) + 1}",
        "type": "trend",
        "segment": "按日",
        "metric": metric,
        "before": round(total["before"], 2),
        "after": round(total["after"], 2),
        "delta": round(total["after"] - total["before"], 2),
        "delta_pct": round((total["after"] - total["before"]) / total["before"] * 100, 2)
        if total["before"] else None,
        "denominator": "期内同口径总量（全部分段合计）",
        "denominator_value": round(total["before"], 2),
        "denominator_ref": "plan.rounds[0].query_spec.metrics[0]",
        "segment_definition": {"column": date_col, "values": sorted(daily),
                               "source": "plan.rounds[0].query_spec.date_range"},
        "evidence": {"rows_before": total["n_before"], "rows_after": total["n_after"]},
        "series": series,
    })

    if stage and stage in fields and funnel_counts:
        if stage_order:
            order = [s.strip() for s in stage_order.split(",") if s.strip() in funnel_counts]
        else:
            order = sorted(funnel_counts, key=lambda s: -(funnel_counts[s]["before"]
                                                          + funnel_counts[s]["after"]))
        base = funnel_counts[order[0]]["before"] if order else 0
        findings.append({
            "id": f"F{len(findings) + 1}",
            "type": "funnel",
            "segment": stage,
            "metric": "stage_count",
            "before": base,
            "after": funnel_counts[order[0]]["after"] if order else 0,
            "delta": (funnel_counts[order[0]]["after"] - base) if order else 0,
            "delta_pct": None,
            "denominator": "漏斗首环节计数",
            "denominator_value": base,
            "denominator_ref": "plan.rounds[0].query_spec.filters",
            "segment_definition": {"column": stage, "values": order,
                                   "source": "plan.rounds[0].query_spec.filters"},
            "evidence": {"rows_before": total["n_before"], "rows_after": total["n_after"]},
            "stages": [{"stage": s, **funnel_counts[s]} for s in order],
        })

    if cost and cost in fields and econ["before"]["revenue"]:
        gm_b = (econ["before"]["revenue"] - econ["before"]["cost"]) / econ["before"]["revenue"]
        gm_a = ((econ["after"]["revenue"] - econ["after"]["cost"]) / econ["after"]["revenue"]
                if econ["after"]["revenue"] else 0.0)
        findings.append({
            "id": f"F{len(findings) + 1}",
            "type": "unit_economics",
            "segment": "整体",
            "metric": "gross_margin",
            "before": round(gm_b, 4),
            "after": round(gm_a, 4),
            "delta": round(gm_a - gm_b, 4),
            "delta_pct": round((gm_a - gm_b) / gm_b * 100, 2) if gm_b else None,
            "denominator": "期内收入（同口径）",
            "denominator_value": round(econ["before"]["revenue"], 2),
            "denominator_ref": "plan.rounds[0].query_spec.metrics[0]",
            "segment_definition": {"column": "__all__", "values": ["整体"],
                                   "source": "plan.rounds[0].query_spec.metrics[0]"},
            "evidence": {"revenue_before": round(econ["before"]["revenue"], 2),
                         "revenue_after": round(econ["after"]["revenue"], 2),
                         "cost_before": round(econ["before"]["cost"], 2),
                         "cost_after": round(econ["after"]["cost"], 2)},
        })

    out = {
        "artifact": "findings",
        "version": "1.0",
        "generated_at": now_iso(),
        "plan_ref": {"metric": metric, "dimensions": dims, "split": split,
                     "preregistered": plan.get("preregistered", False)},
        "metric": metric,
        "totals": {"before": round(total["before"], 2), "after": round(total["after"], 2),
                   "delta": round(total["after"] - total["before"], 2),
                   "n_before": total["n_before"], "n_after": total["n_after"]},
        "findings": findings,
    }
    out["gate"] = check(out, plan)
    return out


def check(findings: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    items = findings.get("findings") or []
    checks.append(ck(bool(items), f"发现数={len(items)}", "structure",
                     "CRITICAL" if not items else "OK"))
    ids = [f.get("id") for f in items]
    checks.append(ck(len(ids) == len(set(ids)), "发现 ID 唯一", "structure",
                     "CRITICAL" if len(ids) != len(set(ids)) else "OK"))
    for f in items:
        tag = f.get("id", "?")
        for k in ("type", "metric", "denominator", "denominator_ref", "segment_definition"):
            empty = f.get(k) in (None, "", [], {})
            checks.append(ck(not empty, f"{tag} 含 {k}", "denominator",
                             "CRITICAL" if empty else "OK"))
        ev = f.get("evidence") or {}
        checks.append(ck("rows_before" in ev and "rows_after" in ev,
                         f"{tag} 有样本量证据", "evidence",
                         "CRITICAL" if not ev else "OK"))
        den = f.get("denominator_value")
        checks.append(ck(isinstance(den, (int, float)), f"{tag} 分母是数值",
                         "denominator",
                         "CRITICAL" if not isinstance(den, (int, float)) else "OK"))
        if isinstance(den, (int, float)) and den == 0 and abs(f.get("delta") or 0) > 0:
            checks.append(ck(False, f"{tag} 分母为 0 但有变化（禁止补零/改分母）",
                             "denominator", "CRITICAL"))
        checks.append(ck(f.get("denominator_ref") == "plan.rounds[0].query_spec.metrics[0]"
                         or "plan" in str(f.get("denominator_ref", "")),
                         f"{tag} 分母可追到计划", "traceability",
                         "HIGH" if "plan" not in str(f.get("denominator_ref", "")) else "OK"))
    plan_dims = set(plan.get("dimensions") or [])
    used = {f.get("segment_definition", {}).get("column") for f in items
            if f.get("type") == "segment"}
    missing = plan_dims - used
    checks.append(ck(not missing, f"计划维度都产出了分段发现 {sorted(plan_dims)}",
                     "coverage", "CRITICAL" if missing else "OK", missing=sorted(missing)))
    for f in items:
        col = f.get("segment_definition", {}).get("column")
        if f.get("type") == "segment":
            checks.append(ck(col in plan_dims, f"{f.get('id')} 分段维度来自计划（{col}）",
                             "preregistration", "CRITICAL" if col not in plan_dims else "OK"))
    # 分段加总 = 整体（防止改分母制造增长）
    overall = next((f for f in items if f.get("type") == "overall"), None)
    if overall:
        for dim in plan_dims:
            segs = [f for f in items if f.get("type") == "segment"
                    and f.get("segment_definition", {}).get("column") == dim]
            if not segs:
                continue
            sb = sum(f.get("before", 0) for f in segs)
            sa = sum(f.get("after", 0) for f in segs)
            tol_b = max(0.5, abs(overall.get("before", 0)) * 0.005)
            tol_a = max(0.5, abs(overall.get("after", 0)) * 0.005)
            checks.append(ck(abs(sb - overall.get("before", 0)) <= tol_b,
                             f"{dim} 分段前合计={round(sb, 2)} vs 整体={overall.get('before')}",
                             "denominator", "CRITICAL"))
            checks.append(ck(abs(sa - overall.get("after", 0)) <= tol_a,
                             f"{dim} 分段后合计={round(sa, 2)} vs 整体={overall.get('after')}",
                             "denominator", "CRITICAL"))
    return gate(checks, "explore")

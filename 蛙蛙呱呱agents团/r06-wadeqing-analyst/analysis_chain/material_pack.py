# -*- coding: utf-8 -*-
"""第 7 段前置 material_pack：把分析工件压成“可写、可审”的断言材料。

方案 §13.4 / §13.5 要求：
  - 报告文字只消费 material pack，不再直接读 result.json；
  - 每条断言带数字、分母、证据引用；
  - 证据不足的断言进 bounded_modules，不混进主结论。

本模块不改变 nonce/claims 体系，只在分析链内部产出一份材料包。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .common import ck, gate, now_iso, read_json

ARTIFACTS = {
    "findings": "findings.json",
    "explanation": "explanation.json",
    "stats": "stats.json",
    "profile": "data_profile.json",
    "frame": "frame.json",
    "plan": "analysis_plan.json",
}


def _num(claim_id: str, i: int, value: Any, unit: str, evidence: str) -> Dict[str, Any]:
    return {"id": f"{claim_id}-N{i}", "value": value, "unit": unit,
            "display": _fmt(value, unit), "evidence": evidence}


def _fmt(v: Any, unit: str) -> str:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return str(v)
    if unit == "%":
        return f"{x:.1f}%"
    if unit == "分":
        return f"{x:.1f}分"
    if unit == "":
        return f"{x:,.2f}"
    if unit in ("元", "个", "次", "人", "行"):
        return f"{x:,.0f}{unit}"
    return f"{x:,.2f}{unit}"


def build(chain_dir: str) -> Dict[str, Any]:
    arts: Dict[str, Any] = {}
    for k, fn in ARTIFACTS.items():
        p = os.path.join(chain_dir, fn)
        if not os.path.exists(p):
            return {"artifact": "analysis_material_pack",
                    "gate": gate([ck(False, f"缺少 {fn}", "existence", "CRITICAL")],
                                 "material_pack")}
        arts[k] = read_json(p)
    fg = arts["findings"].get("gate") or {}
    eg = arts["explanation"].get("gate") or {}
    sg = arts["stats"].get("gate") or {}
    if not (fg.get("ok") and eg.get("ok") and sg.get("ok")):
        return {"artifact": "analysis_material_pack",
                "gate": gate([ck(False, "上游 findings/explanation/stats 门禁未过",
                                 "upstream", "CRITICAL")], "material_pack")}

    metric = arts["plan"].get("metric", "")
    dim = arts["explanation"].get("dimension", "")
    unit = "元" if metric in ("profit", "revenue", "cost", "mrr", "gmv") else (
        "%" if str(metric).endswith("rate") else "个")
    stats_unit = "%" if (str(metric).endswith("rate") or metric == "churn_flag") else unit
    flag_metric = metric == "churn_flag"

    def _stat(v: Any) -> Any:
        try:
            x = float(v)
            return x * 100 if flag_metric else x
        except (TypeError, ValueError):
            return v
    claims: List[Dict[str, Any]] = []
    numbers: Dict[str, Any] = {}
    bounded: List[Dict[str, Any]] = []
    stop_pct = _stop_threshold(arts["plan"])

    overall = next((x for x in arts["findings"].get("findings", [])
                    if x.get("type") == "overall"), None)
    if overall:
        cid = "C0"
        n = [
            _num(cid, 1, overall.get("before"), unit, "findings:overall"),
            _num(cid, 2, overall.get("after"), unit, "findings:overall"),
            _num(cid, 3, overall.get("delta"), unit, "findings:overall"),
            _num(cid, 4, overall.get("delta_pct"), "%", "findings:overall"),
        ]
        claims.append(_claim(cid, "overall", "全部", metric,
                             f"整体{metric}由{_fmt(overall.get('before'), unit)}变为"
                             f"{_fmt(overall.get('after'), unit)}，变化"
                             f"{_fmt(overall.get('delta'), unit)}",
                             overall, unit, n, "high",
                             {"findings_id": overall.get("id"),
                              "denominator": overall.get("denominator"),
                              "denominator_value": overall.get("denominator_value")}))
        numbers.update({x["id"]: x for x in n})

    drivers = sorted([x for x in arts["findings"].get("findings", [])
                      if x.get("type") == "segment"
                      and (x.get("segment_definition") or {}).get("column") == dim],
                     key=lambda x: -abs(x.get("delta") or 0))[:5]
    for i, f in enumerate(drivers, 1):
        cid = f"C{i}"
        dec = next((d for d in arts["explanation"].get("drivers", [])
                    if d.get("segment") == f.get("segment")), None)
        n = [
            _num(cid, 1, f.get("before"), unit, f"findings:{f.get('id')}"),
            _num(cid, 2, f.get("after"), unit, f"findings:{f.get('id')}"),
            _num(cid, 3, f.get("delta"), unit, f"findings:{f.get('id')}"),
            _num(cid, 4, f.get("delta_pct"), "%", f"findings:{f.get('id')}"),
        ]
        if dec and dec.get("contribution_pct") is not None:
            n.append(_num(cid, 5, dec.get("contribution_pct"), "%", "explanation:drivers"))
        if dec and dec.get("effect_decomposition"):
            eff = dec["effect_decomposition"]
            n.append(_num(cid, 6, eff.get("quantity"), unit, "explanation:quantity"))
            n.append(_num(cid, 7, eff.get("price"), unit, "explanation:price"))
            n.append(_num(cid, 8, eff.get("residual"), unit, "explanation:residual"))
        claim = _claim(cid, "segment", f.get("segment"), metric,
                       f"{f.get('segment')}段{metric}变化"
                       f"{_fmt(f.get('delta'), unit)}（{_fmt(f.get('delta_pct'), '%')}）",
                       f, unit, n, "high" if dec and dec.get("effect_decomposition") else "medium",
                       {"findings_id": f.get("id"), "explanation_driver": dec.get("driver") if dec else None,
                        "denominator": f.get("denominator"),
                        "denominator_value": f.get("denominator_value"),
                        "effect_decomposition": dec.get("effect_decomposition") if dec else None,
                        "decomposition_unavailable_reason":
                            dec.get("decomposition_unavailable_reason") if dec else "未找到驱动拆解"})
        claims.append(claim)
        numbers.update({x["id"]: x for x in n})
        if not dec:
            bounded.append({"claim_id": cid, "reason": "缺少驱动拆解记录，不能作为主结论",
                            "route": "analysis"})
        elif not dec.get("effect_decomposition") and not dec.get("decomposition_unavailable_reason"):
            bounded.append({"claim_id": cid, "reason": "缺少量价拆解且未说明原因",
                            "route": "analysis"})
        if abs(f.get("delta") or 0) and abs(f.get("delta") or 0) < abs(overall.get("delta") or 1) * stop_pct / 100:
            bounded.append({"claim_id": cid, "reason": f"贡献低于停止阈值 {stop_pct}%",
                            "route": "drop"})

    prof = arts["profile"]
    if prof.get("overall_score") is not None:
        cid = "CQ"
        n = [
            _num(cid, 1, prof.get("overall_score"), "分", "profile:overall_score"),
            _num(cid, 2, ((prof.get("dimensions", {}).get("coverage") or {}).get("day_coverage") or 0) * 100,
                 "%", "profile:coverage"),
            _num(cid, 3, (prof.get("dimensions", {}).get("coverage") or {}).get("rows"),
                 "行", "profile:coverage"),
        ]
        claims.append(_claim(cid, "quality", "数据质量", metric,
                             f"数据质量 {_fmt(prof.get('overall_score'), '分')}，"
                             f"覆盖 {(prof.get('dimensions', {}).get('coverage') or {}).get('rows')} 行",
                             {}, "分", n, "high",
                             {"profile": "data_profile.json"}))
        numbers.update({x["id"]: x for x in n})

    h = arts["stats"].get("headline") or {}
    if h:
        cid = "CS"
        n = [
            _num(cid, 1, _stat(h.get("diff")), stats_unit, "stats:headline"),
            _num(cid, 2, h.get("relative_lift_pct"), "%", "stats:headline"),
            _num(cid, 3, h.get("cohens_d"), "", "stats:headline"),
            _num(cid, 4, _stat((h.get("ci") or {}).get("lo")), stats_unit, "stats:ci"),
            _num(cid, 5, _stat((h.get("ci") or {}).get("hi")), stats_unit, "stats:ci"),
        ]
        claims.append(_claim(cid, "statistics", "统计稳健性", metric,
                             f"前后差异 {_fmt(_stat(h.get('diff')), stats_unit)}，"
                             f"95% 区间 [{_fmt(_stat((h.get('ci') or {}).get('lo')), stats_unit)}, "
                             f"{_fmt(_stat((h.get('ci') or {}).get('hi')), stats_unit)}]",
                             h, stats_unit, n, "high",
                             {"stats": "stats.json",
                              "p_raw": h.get("p_raw"), "effect_grade": h.get("effect_grade")}))
        numbers.update({x["id"]: x for x in n})
        a = arts["stats"].get("assumptions") or {}
        if not a.get("sample_ok"):
            bounded.extend({"claim_id": c.get("claim_id"), "reason": "样本量不足 30",
                            "route": "analysis"} for c in claims)

    pack = {
        "artifact": "analysis_material_pack",
        "version": "1.0",
        "generated_at": now_iso(),
        "metric": metric,
        "dimension": dim,
        "window": (arts["plan"].get("window") or ""),
        "split": arts["plan"].get("split", ""),
        "claims": claims,
        "numbers": numbers,
        "bounded_modules": _dedupe_bounded(bounded),
        "totals": arts["findings"].get("totals") or {},
        "source_artifacts": {k: v for k, v in ARTIFACTS.items()},
    }
    pack["gate"] = check(pack)
    return pack


def _stop_threshold(plan: Dict[str, Any]) -> float:
    for r in plan.get("rounds", []):
        v = (r.get("stop_condition") or {}).get("if_impact_below_pct")
        if isinstance(v, (int, float)):
            return float(v)
    return 3.0


def _claim(cid: str, kind: str, segment: str, metric: str, statement: str,
           src: Dict[str, Any], unit: str, nums: List[Dict[str, Any]],
           confidence: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "claim_id": cid, "kind": kind, "segment": segment, "metric": metric,
        "statement": statement, "unit": unit,
        "before": src.get("before"), "after": src.get("after"),
        "delta": src.get("delta"), "delta_pct": src.get("delta_pct"),
        "numbers": nums, "confidence": confidence, "evidence": evidence,
    }


def _dedupe_bounded(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for x in items:
        k = (x.get("claim_id"), x.get("reason"))
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def check(pack: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    claims = pack.get("claims") or []
    checks.append(ck(bool(claims), f"断言数={len(claims)}", "structure",
                     "CRITICAL" if not claims else "OK"))
    ids = [c.get("claim_id") for c in claims]
    checks.append(ck(len(ids) == len(set(ids)), "断言 ID 唯一", "structure",
                     "CRITICAL" if len(ids) != len(set(ids)) else "OK"))
    for c in claims:
        cid = c.get("claim_id", "?")
        checks.append(ck(bool(c.get("statement")), f"{cid} 有陈述", "claim", "CRITICAL"))
        checks.append(ck(bool(c.get("numbers")), f"{cid} 带数字", "traceability",
                         "CRITICAL" if not c.get("numbers") else "OK"))
        checks.append(ck(bool(c.get("evidence")), f"{cid} 有证据引用", "traceability",
                         "CRITICAL" if not c.get("evidence") else "OK"))
        for n in c.get("numbers", []):
            checks.append(ck(bool(n.get("evidence")), f"{cid} 数字 {n.get('id')} 可追",
                             "traceability", "CRITICAL" if not n.get("evidence") else "OK"))
    bounded_ids = {b.get("claim_id") for b in pack.get("bounded_modules", [])}
    checks.append(ck(len(bounded_ids) < len(claims),
                     f"至少一条主结论（bounded={len(bounded_ids)}/{len(claims)}）",
                     "value", "CRITICAL" if bounded_ids >= set(ids) else "OK"))
    return gate(checks, "material_pack")

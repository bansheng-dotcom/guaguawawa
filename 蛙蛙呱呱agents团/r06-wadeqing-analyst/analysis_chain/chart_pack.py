# -*- coding: utf-8 -*-
"""第 8 段 chart：claim-bound 图表规格包 + fail_if_missing。

方案 §13.4 / §13.5 的硬要求：
  - 每张图必须绑定一条已验证断言（claim_id），不画“装饰图”；
  - required_series / series_completeness / focus_metric / annotation_plan /
    fail_if_missing / visual_check 六件齐全；
  - 缺必绘系列、缺标注、覆盖不全 → 图表失败，回流 analysis。

渲染仍走 core.report.report_renderer（静态 SVG，适配 A4 打印）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import ck, gate, now_iso

ALLOWED = ("line", "hbar", "dumbbell", "vbar")


def build(pack: Dict[str, Any], findings: Dict[str, Any],
          verification: Dict[str, Any]) -> Dict[str, Any]:
    vg = verification.get("gate") or {}
    if not vg.get("ok"):
        return {"artifact": "chart_spec_pack", "gate": gate(
            [ck(False, "verification 门禁未过", "upstream", "CRITICAL")], "chart")}
    verified = {u.get("claim_id") for u in verification.get("units", [])
                if u.get("verdict") == "verified"}
    claims = {c.get("claim_id"): c for c in pack.get("claims", [])}
    metric = pack.get("metric", "")
    unit = "元" if metric in ("profit", "revenue", "cost", "gmv", "mrr") else (
        "%" if str(metric).endswith("rate") else "个")
    specs: List[Dict[str, Any]] = []

    overall = claims.get("C0")
    if overall and "C0" in verified:
        series = _series(findings)
        if series:
            labels = [p["date"] for p in series]
            vals = [p["value"] for p in series]
            specs.append(_spec(
                "CH1", "C0", "line", f"整体{metric}走势：从{_f(vals[0])}到{_f(vals[-1])}",
                metric, unit, ["整体"], labels, [{"name": "整体", "values": vals}],
                {"start": vals[0], "end": vals[-1], "delta": round(vals[-1] - vals[0], 2)},
                {"points": [{"label": p["date"], "value": p["value"]} for p in series]}))

    seg_claim = claims.get("C1")
    segs = sorted([f for f in findings.get("findings", [])
                   if f.get("type") == "segment"],
                  key=lambda x: -abs(x.get("delta") or 0))[:5]
    if seg_claim and "C1" in verified and segs:
        labels = [f"{s.get('segment')}" for s in segs]
        bars = [{"label": f"{s.get('segment')}（{_signed(s.get('delta'))}）",
                 "value": abs(float(s.get("delta") or 0))} for s in segs]
        specs.append(_spec(
            "CH2", "C1", "hbar",
            f"{segs[0].get('segment')}贡献最大：{_signed(segs[0].get('delta'))}{unit}",
            metric, unit, labels, labels, bars,
            {"start": segs[-1].get("delta"), "end": segs[0].get("delta"),
             "delta": round((segs[0].get("delta") or 0) - (segs[-1].get("delta") or 0), 2)},
            {"bars": bars}))
        items = [{"label": s.get("segment"), "a": float(s.get("before") or 0),
                  "b": float(s.get("after") or 0)} for s in segs]
        specs.append(_spec(
            "CH3", "C1", "dumbbell",
            f"{segs[0].get('segment')}前后对比：{_f(segs[0].get('before'))}→{_f(segs[0].get('after'))}",
            metric, unit, labels, labels, items,
            {"start": segs[0].get("before"), "end": segs[0].get("after"),
             "delta": segs[0].get("delta")},
            {"items": items}))

    out = {
        "artifact": "chart_spec_pack",
        "version": "1.0",
        "generated_at": now_iso(),
        "metric": metric,
        "chart_count": len(specs),
        "charts": specs,
    }
    out["gate"] = check(out, claims, verified)
    return out


def _series(findings: Dict[str, Any]) -> List[Dict[str, Any]]:
    trend = next((f for f in findings.get("findings", [])
                  if f.get("type") == "trend"), None)
    return list((trend or {}).get("series") or [])


def _spec(chart_id: str, claim_id: str, typ: str, title: str, metric: str,
          unit: str, required: List[str], labels: List[str], actual: Any,
          annotations: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    present = [s.get("name") for s in actual] if typ == "line" else labels
    missing = [x for x in required if x not in present]
    ratio = 0.0 if not required else round((len(required) - len(missing)) / len(required), 4)
    return {
        "chart_id": chart_id, "claim_id": claim_id, "type": typ, "title": title,
        "source": "analysis_chain/findings.json",
        "unit_meta": unit,
        "claim_to_prove": f"{claim_id}",
        "focus_metric": metric,
        "required_series": required,
        "series_completeness": {"required": len(required),
                                "present": len(required) - len(missing),
                                "ratio": ratio, "missing": missing},
        "annotation_plan": {
            "start": annotations.get("start"), "end": annotations.get("end"),
            "delta": annotations.get("delta"),
            "min_spacing_px": 12, "avoid_overlap": True,
            "anchor": "first_last",
        },
        "fail_if_missing": ["required_series", "annotation_start_end",
                            "series_completeness"],
        "visual_check": ["axis_from_zero", "unit_in_annotation",
                         "no_label_overlap", "title_matches_claim"],
        "payload": payload,
        "series": actual,
    }


def _f(v: Any) -> str:
    try:
        return f"{float(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _signed(v: Any) -> str:
    try:
        x = float(v)
        return f"{x:+,.0f}"
    except (TypeError, ValueError):
        return str(v)


def check(pack: Dict[str, Any], claims: Dict[str, Any],
          verified: set) -> Dict[str, Any]:
    checks = []
    charts = pack.get("charts") or []
    checks.append(ck(bool(charts), f"图表数={len(charts)}", "structure",
                     "CRITICAL" if not charts else "OK"))
    for c in charts:
        cid = c.get("chart_id", "?")
        checks.append(ck(c.get("type") in ALLOWED, f"{cid} 图型合法={c.get('type')}",
                         "type", "CRITICAL" if c.get("type") not in ALLOWED else "OK"))
        claim_id = c.get("claim_id")
        checks.append(ck(claim_id in claims, f"{cid} 绑定已有断言 {claim_id}",
                         "traceability", "CRITICAL" if claim_id not in claims else "OK"))
        checks.append(ck(claim_id in verified, f"{cid} 绑定的是已验证断言",
                         "traceability", "CRITICAL" if claim_id not in verified else "OK"))
        comp = c.get("series_completeness") or {}
        checks.append(ck(comp.get("ratio") == 1.0 and not comp.get("missing"),
                         f"{cid} 必绘系列完整 {comp.get('present')}/{comp.get('required')}",
                         "completeness", "CRITICAL" if comp.get("ratio") != 1.0 else "OK"))
        checks.append(ck(bool(c.get("focus_metric")), f"{cid} 声明焦点指标", "focus",
                         "CRITICAL" if not c.get("focus_metric") else "OK"))
        ap = c.get("annotation_plan") or {}
        checks.append(ck(all(ap.get(k) is not None for k in ("start", "end", "delta")),
                         f"{cid} 起止/差值标注齐全", "annotation",
                         "CRITICAL" if not all(ap.get(k) is not None
                                               for k in ("start", "end", "delta")) else "OK"))
        checks.append(ck(ap.get("avoid_overlap") is True and
                         isinstance(ap.get("min_spacing_px"), (int, float)),
                         f"{cid} 标注避让与最小间距", "annotation",
                         "CRITICAL" if not ap.get("avoid_overlap") else "OK"))
        fim = c.get("fail_if_missing") or []
        checks.append(ck("required_series" in fim and "annotation_start_end" in fim,
                         f"{cid} fail_if_missing 已声明", "fail_if_missing",
                         "CRITICAL" if "required_series" not in fim else "OK"))
        checks.append(ck(bool(c.get("payload")), f"{cid} 有渲染 payload", "payload",
                         "CRITICAL" if not c.get("payload") else "OK"))
        checks.append(ck(len(c.get("visual_check") or []) >= 3,
                         f"{cid} 视觉自检项 ≥3", "visual",
                         "HIGH" if len(c.get("visual_check") or []) < 3 else "OK"))
    ids = [c.get("chart_id") for c in charts]
    checks.append(ck(len(ids) == len(set(ids)), "图表 ID 唯一", "structure",
                     "CRITICAL" if len(ids) != len(set(ids)) else "OK"))
    return gate(checks, "chart")

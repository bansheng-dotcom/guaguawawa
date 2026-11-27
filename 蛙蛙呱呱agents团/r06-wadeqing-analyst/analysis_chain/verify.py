# -*- coding: utf-8 -*-
"""第 7 段 verify：Chain of Verification（CoV 六问）+ 回流码。

方案 §13.4 的硬要求：
  1. 每条结论先问：指标状态、分子分母、对比基准、驱动、反证、边界；
  2. 点名驱动必须有拆解；证据不支持就回 analysis，不许直接写；
  3. 无报告价值的结论丢弃，有限证据进 bounded_modules。

回流码只允许三值：analysis / text / chart；丢弃单独标 drop。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import ck, gate, now_iso

QUESTIONS = (
    ("metric_state", "指标与单位是否明确"),
    ("denominator", "分子分母是否同口径且非零"),
    ("baseline", "是否有可比的对照基准"),
    ("driver", "点名驱动是否有拆解"),
    ("counter_evidence", "是否有替代解释/反证"),
    ("boundary", "边界与数据质量是否声明"),
)
ROUTES = ("pass", "analysis", "text", "chart", "drop")


def build(pack: Dict[str, Any], findings: Dict[str, Any],
          explanation: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    pg = pack.get("gate") or {}
    if not pg.get("ok"):
        return {"artifact": "verification", "gate": gate(
            [ck(False, "material pack 门禁未过", "upstream", "CRITICAL")], "verify")}
    bounded = {b.get("claim_id"): b for b in pack.get("bounded_modules", [])}
    alts = explanation.get("alternatives") or []
    cov = (profile.get("dimensions") or {}).get("coverage") or {}
    units: List[Dict[str, Any]] = []

    for claim in pack.get("claims", []):
        cid = claim.get("claim_id", "?")
        kind = claim.get("kind")
        answers = []
        answers.append(_ans(cid, "metric_state",
                            bool(claim.get("metric")) and bool(claim.get("unit"))
                            and bool(claim.get("statement")),
                            "指标/单位/陈述齐备", "claim"))
        if kind in ("quality", "statistics"):
            answers.append(_ans(cid, "denominator", True, "该单元不涉及分段分母", "n/a"))
        else:
            den = (claim.get("evidence") or {}).get("denominator_value")
            answers.append(_ans(cid, "denominator",
                                isinstance(den, (int, float)) and den != 0,
                                f"分母={den}", "claim.evidence"))
        if kind == "statistics":
            answers.append(_ans(cid, "baseline", "ci" in (claim.get("evidence") or {})
                                or (claim.get("numbers") or []) != [],
                                "有区间/效应量作为基准", "claim.numbers"))
        elif kind == "quality":
            answers.append(_ans(cid, "baseline", bool(claim.get("numbers")),
                                "质量指标自带分值与覆盖", "claim.numbers"))
        else:
            answers.append(_ans(cid, "baseline",
                                claim.get("before") is not None and claim.get("after") is not None,
                                f"前期={claim.get('before')} 本期={claim.get('after')}",
                                "claim.before_after"))
        dec = (claim.get("evidence") or {}).get("effect_decomposition")
        if kind == "segment":
            reason = (claim.get("evidence") or {}).get("decomposition_unavailable_reason")
            answers.append(_ans(cid, "driver", bool(dec),
                                "有量价拆解" if dec else (reason or "点名驱动无拆解"),
                                "explanation.drivers", soft=bool(reason)))
        else:
            answers.append(_ans(cid, "driver", True, "整体/质量/统计单元不点名单一驱动", "n/a"))
        answers.append(_ans(cid, "counter_evidence", len(alts) >= 2,
                            f"替代解释 {len(alts)} 条", "explanation.alternatives"))
        boundary_ok = (cov.get("date_min") and cov.get("day_coverage", 0) >= 0.8
                       and (profile.get("overall_score") or 0) >= 60)
        answers.append(_ans(cid, "boundary", bool(boundary_ok),
                            f"覆盖={cov.get('day_coverage')} 质量分={profile.get('overall_score')}"
                            "；季节性不可验证已声明", "profile"))

        hard_fail = [a for a in answers if not a["ok"] and not a.get("soft")]
        if cid in bounded:
            route = bounded[cid].get("route", "analysis")
            verdict = "bounded"
        elif hard_fail:
            dims = {a["question"] for a in hard_fail}
            route = "analysis" if "driver" in dims or "denominator" in dims else "text"
            verdict = "rework"
        elif abs(claim.get("delta") or 0) == 0 and kind in ("overall", "segment"):
            route = "drop"
            verdict = "drop"
        else:
            route = "pass"
            verdict = "verified"
        units.append({"claim_id": cid, "kind": kind, "verdict": verdict,
                      "route": route, "cov": answers,
                      "bounded": cid in bounded})

    main = [u for u in units if u["verdict"] == "verified"]
    bounded_units = [u for u in units if u["verdict"] == "bounded"]
    out = {
        "artifact": "verification",
        "version": "1.0",
        "generated_at": now_iso(),
        "questions": [{"id": q, "text": t} for q, t in QUESTIONS],
        "units": units,
        "summary": {
            "total": len(units), "verified": len(main),
            "bounded": len(bounded_units),
            "rework": len([u for u in units if u["verdict"] == "rework"]),
            "drop": len([u for u in units if u["verdict"] == "drop"]),
        },
        "bounded_modules": [{"claim_id": u["claim_id"], "route": u["route"],
                             "reason": next((a["detail"] for a in u["cov"]
                                             if not a["ok"]), "证据不足")}
                            for u in units if u["verdict"] != "verified"],
    }
    out["gate"] = check(out)
    return out


def _ans(cid: str, q: str, ok: bool, detail: str, evidence: str,
         soft: bool = False) -> Dict[str, Any]:
    return {"claim_id": cid, "question": q, "ok": bool(ok),
            "soft": soft, "detail": detail, "evidence": evidence}


def check(ver: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    units = ver.get("units") or []
    checks.append(ck(bool(units), f"核验单元={len(units)}", "structure",
                     "CRITICAL" if not units else "OK"))
    main = [u for u in units if u.get("verdict") == "verified"]
    checks.append(ck(bool(main), f"可进主结论的单元={len(main)}", "value",
                     "CRITICAL" if not main else "OK"))
    for u in units:
        cid = u.get("claim_id", "?")
        qs = {a.get("question") for a in u.get("cov", [])}
        checks.append(ck(qs == {q for q, _ in QUESTIONS},
                         f"{cid} CoV 六问齐全", "cov",
                         "CRITICAL" if qs != {q for q, _ in QUESTIONS} else "OK"))
        checks.append(ck(u.get("route") in ROUTES,
                         f"{cid} 回流码合法={u.get('route')}", "route",
                         "CRITICAL" if u.get("route") not in ROUTES else "OK"))
        if u.get("verdict") == "verified":
            bad = [a["question"] for a in u.get("cov", [])
                   if not a.get("ok") and not a.get("soft")]
            checks.append(ck(not bad, f"{cid} 主结论无硬失败 {bad}", "value",
                             "CRITICAL" if bad else "OK"))
    return gate(checks, "verify")

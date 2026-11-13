# -*- coding: utf-8 -*-
"""s03 外置判据审查（criteria）：review / delta 两动作。

口径来源：Intense-Visions__harness-engineering · harness-release-readiness。
- review：每条判据三态 pass/warn/fail；PASS 仅当 0 fail（warn 不阻断）；
  判据必须带可定位证据（file:line / 字段名），"看起来没问题"不算证据。
- delta：复跑不信任缓存，全查后对照上态输出 fixed/new/remaining。
阈值：thresholds.json → criteria.*。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from . import _common as c

NAME = "criteria"
DESC = "外置判据审查：review（三态 pass/warn/fail，PASS 仅当 0 fail）与 delta（复跑全查 + fixed/new/remaining 对照）"

ACTIONS = {
    "review": "逐条判据出 pass/warn/fail 三态，无证据即 fail",
    "delta": "全查复跑并对照上一态，输出 fixed/new/remaining",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    ap = act.add_parser("review", help=ACTIONS["review"])
    ap.add_argument("--input", required=True)
    ap = act.add_parser("delta", help=ACTIONS["delta"])
    ap.add_argument("--input", required=True)
    ap.add_argument("--state", required=True, help="上一态 criteria_results JSON")


# --------------------------------------------------------------------------- #
# 单条判据三态判定（确定性）
# --------------------------------------------------------------------------- #
def _evidence_specific(evidence: str, th: Dict[str, Any]) -> bool:
    """证据必须可定位：file:line / 字段名 / verified: 前缀，否则不算证据。"""
    if not evidence or not str(evidence).strip():
        return False
    if re.search(th["evidence_line_re"], evidence):
        return True
    if re.search(th["evidence_field_re"], evidence):
        return True
    low = str(evidence).lower()
    if low.startswith("verified:") or low.startswith("not verified:"):
        return True
    return False


def _judge(crit: Dict[str, Any], th: Dict[str, Any]) -> Dict[str, Any]:
    cid = str(crit.get("id") or "")
    evidence = str(crit.get("evidence") or "")
    issues = list(crit.get("issues") or [])
    partial = bool(crit.get("partial", False))
    if not _evidence_specific(evidence, th):
        status = "fail"
        reason = "no_evidence" if not evidence.strip() else "evidence_not_specific"
    elif issues:
        status = "fail"
        reason = "declared_issues"
    elif partial:
        status = "warn"
        reason = "partial_with_evidence"
    else:
        status = "pass"
        reason = "evidence_specific"
    return {"id": cid, "description": crit.get("description", ""),
            "severity": crit.get("severity", "major"), "status": status,
            "reason": reason, "evidence": evidence, "issues": issues}


def _review_core(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["criteria"]
    criteria = data.get("criteria") or []
    checks: List[Dict[str, Any]] = []
    if not criteria:
        checks.append(c.ck(False, "判据清单为空（无 criteria 字段或为空数组）",
                           "criteria:review", "CRITICAL"))
    results = [_judge(x, th) for x in criteria]
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for r in results:
        counts[r["status"]] += 1
    verdict = "PASS" if counts["fail"] == 0 else "FAIL"
    for r in results:
        if r["status"] == "pass":
            checks.append(c.ck(True, f"{r['id']} pass：{r['evidence'][:60]}",
                               f"criteria:{r['id']}"))
        elif r["status"] == "warn":
            checks.append(c.ck(True, f"{r['id']} warn（带证据部分达标，不阻断）",
                               f"criteria:{r['id']}", "INFO", **{"status": "warn"}))
        else:
            checks.append(c.ck(False, f"{r['id']} fail（{r['reason']}）",
                               f"criteria:{r['id']}", "CRITICAL", **{"status": "fail"}))
    out = c.result(checks,
                   criteria_results=results,
                   counts=counts,
                   verdict=verdict,
                   next="0 fail：可出具验收通过结论" if verdict == "PASS"
                        else "存在 fail 判据：交回生产方补证据/修复后复跑（评审只记录不代改）",
                   )
    out["ok"] = out["ok"] and verdict == "PASS"
    return out


def review(data: Dict[str, Any]) -> Dict[str, Any]:
    return _review_core(data)


# --------------------------------------------------------------------------- #
# delta：复跑全查 + 对照上态
# --------------------------------------------------------------------------- #
def _delta_core(data: Dict[str, Any], prev_state: Dict[str, Any]) -> Dict[str, Any]:
    current = _review_core(data)
    prev_results = list(prev_state.get("criteria_results") or [])
    prev_by_id = {str(r.get("id")): str(r.get("status")) for r in prev_results}
    cur_by_id = {str(r.get("id")): str(r.get("status"))
                 for r in current.get("criteria_results", [])}
    fixed, new, remaining = [], [], []
    for cid, cur_status in cur_by_id.items():
        prev_status = prev_by_id.get(cid)
        if prev_status == "fail" and cur_status != "fail":
            fixed.append(cid)
        elif prev_status != "fail" and cur_status == "fail":
            new.append(cid)
        elif prev_status == "fail" and cur_status == "fail":
            remaining.append(cid)
    checks = list(current.get("checks") or [])
    checks.append(c.ck(True, f"delta：fixed={len(fixed)} new={len(new)} remaining={len(remaining)}",
                       "criteria:delta", "OK",
                       **{"fixed": fixed, "new": new, "remaining": remaining}))
    current_verdict = current.get("verdict", "FAIL")
    out = c.result(checks,
                   current=current,
                   delta={"fixed": fixed, "new": new, "remaining": remaining},
                   fixed_count=len(fixed), new_count=len(new),
                   remaining_count=len(remaining),
                   previous_verdict=prev_state.get("verdict"),
                   verdict=current_verdict,
                   next="本轮全查已复跑（不信任缓存）；fixed 判据归档，new/remaining 交回生产方"
                        if current_verdict == "FAIL" else "本轮全查 0 fail：验收闭环",
                   )
    out["ok"] = out["ok"] and current_verdict == "PASS"
    return out


def delta(data: Dict[str, Any], prev_state: Dict[str, Any]) -> Dict[str, Any]:
    return _delta_core(data, prev_state)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "review":
        return review(data)
    if args.action == "delta":
        prev = c.load_json(args.state)
        return delta(data, prev)
    raise SystemExit(f"未知动作：{args.action}")

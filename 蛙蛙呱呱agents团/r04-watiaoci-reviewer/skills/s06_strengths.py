# -*- coding: utf-8 -*-
"""s06 保留优点与复评（strengths）：mark / recheck 两动作。

口径：独立评审"保留优点"原则 + harness-soundness-review 收敛纪律。
- mark：从评审输入提取 keep_list[]（{id, what, why_keep, evidence}），
  keep 项缺 why_keep（或缺任一必填字段）即 FAIL——优点必须给出保留理由。
- recheck：只复评本轮修改——①prev keep 项被降级为 FAIL 必须带 resolution_reason
  ②新增 FAIL 必须能定位到本轮 change 区（new 中 changed=true 的项）
  ③prev 已 resolved 项不重复报。
阈值：thresholds.json → strengths.keep_required_fields。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "strengths"
DESC = "保留优点与复评：mark（keep_list 必带 why_keep/evidence）与 recheck（只评本轮修改：降级须理由/新 FAIL 须落在 change 区/resolved 不重报）"

ACTIONS = {
    "mark": "提取并校验 keep_list：每条优点必须有保留理由与证据",
    "recheck": "对照上轮批评只复评本轮修改：降级/新增/复活三查",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    ap = act.add_parser("mark", help=ACTIONS["mark"])
    ap.add_argument("--input", required=True)
    ap = act.add_parser("recheck", help=ACTIONS["recheck"])
    ap.add_argument("--input", required=True, help="上一轮批评 JSON（prev_critique）")
    ap.add_argument("--new", required=True, help="本轮批评 JSON（new_critique，含 changed 标记）")


# --------------------------------------------------------------------------- #
# mark
# --------------------------------------------------------------------------- #
def _mark_core(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["strengths"]
    required = list(th["keep_required_fields"])
    keep_in = data.get("keep_list") or []
    checks: List[Dict[str, Any]] = []
    if not keep_in:
        checks.append(c.ck(False, "keep_list 为空：评审必须先标记要保留的优点", "strengths:mark", "CRITICAL"))
    keep_list: List[Dict[str, Any]] = []
    invalid: List[Dict[str, Any]] = []
    for item in keep_in:
        kid = str(item.get("id") or "")
        missing = [f for f in required
                   if f not in item or (isinstance(item.get(f), str) and not str(item.get(f)).strip())
                   or item.get(f) in (None, [], {})]
        ok = not missing
        keep_list.append({"id": kid, "what": item.get("what", ""),
                          "why_keep": item.get("why_keep", ""),
                          "evidence": item.get("evidence", ""),
                          "valid": ok, "missing_fields": missing})
        if ok:
            checks.append(c.ck(True, f"keep {kid}：{str(item.get('what'))[:40]}",
                               f"strengths:{kid}"))
        else:
            invalid.append({"id": kid, "missing_fields": missing})
            checks.append(c.ck(False, f"keep {kid} 缺必填字段：{missing}",
                               f"strengths:{kid}", "CRITICAL"))
    verdict = "PASS" if not invalid and keep_in else "FAIL"
    out = c.result(checks,
                   keep_list=keep_list,
                   keep_count=len(keep_list),
                   invalid=invalid,
                   verdict=verdict,
                   next="keep_list 有效：新方案改动不得破坏这些优点" if verdict == "PASS"
                        else "keep 项必须补齐 why_keep/evidence（无理由不叫保留优点）",
                   )
    out["ok"] = out["ok"] and verdict == "PASS"
    return out


def mark(data: Dict[str, Any]) -> Dict[str, Any]:
    return _mark_core(data)


# --------------------------------------------------------------------------- #
# recheck
# --------------------------------------------------------------------------- #
def _recheck_core(prev: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    prev_keeps = {str(k.get("id")): k for k in (prev.get("keep_list") or [])}
    new_keeps = {str(k.get("id")): k for k in (new.get("keep_list") or [])}
    new_findings = list(new.get("findings") or [])
    prev_findings = list(prev.get("findings") or [])
    changed_ids = {str(ch.get("id")) for ch in (new.get("changed") or [])
                   if isinstance(ch, dict) and ch.get("changed") is True}

    checks: List[Dict[str, Any]] = []
    downgrades: List[Dict[str, Any]] = []
    untraceable_new_fails: List[Dict[str, Any]] = []
    resurfaced: List[Dict[str, Any]] = []
    dropped: List[str] = []
    violations: List[Dict[str, Any]] = []

    # ① prev keep 项不得无理由降级为 FAIL
    for f in new_findings:
        keep_id = str(f.get("keep_id") or "")
        if keep_id and keep_id in prev_keeps and f.get("severity") == "error":
            reason = str(f.get("resolution_reason") or "").strip()
            downgrades.append({"keep_id": keep_id,
                               "what": prev_keeps[keep_id].get("what", ""),
                               "resolution_reason": reason or None,
                               "documented": bool(reason)})
            if not reason:
                violations.append({
                    "rule": "keep_downgrade_without_reason",
                    "detail": f"keep {keep_id} 被降级为 FAIL 但无 resolution_reason",
                    "finding_id": f.get("id")})
    for kid, entry in new_keeps.items():
        if kid in prev_keeps and str(entry.get("status") or "").upper() == "FAIL":
            reason = str(entry.get("resolution_reason") or "").strip()
            downgrades.append({"keep_id": kid,
                               "what": prev_keeps[kid].get("what", ""),
                               "resolution_reason": reason or None,
                               "documented": bool(reason)})
            if not reason:
                violations.append({
                    "rule": "keep_downgrade_without_reason",
                    "detail": f"keep {kid} 在新批评中标记 FAIL 但无 resolution_reason",
                    "finding_id": kid})

    # ② 新增 FAIL 必须能定位到本轮 change 区
    prev_fail_ids = {str(f.get("id")) for f in prev_findings
                     if f.get("severity") == "error"}
    for f in new_findings:
        if f.get("severity") != "error":
            continue
        fid = str(f.get("id") or "")
        if fid in prev_fail_ids:
            continue
        anchor = str(f.get("changed_ref") or "")
        if anchor and anchor in changed_ids:
            continue
        untraceable_new_fails.append({"id": fid, "title": f.get("title", ""),
                                      "changed_ref": anchor or None})
        violations.append({
            "rule": "untraceable_new_fail",
            "detail": f"新 FAIL {fid} 无法定位到本轮 change 区（changed=true 项）",
            "finding_id": fid})

    # ③ prev 已 resolved 项不重复报
    for f in prev_findings:
        if f.get("resolved") is True:
            fid = str(f.get("id") or "")
            again = [g for g in new_findings if str(g.get("id") or "") == fid]
            if again:
                resurfaced.append({"id": fid, "title": f.get("title", "")})
                violations.append({
                    "rule": "resolved_resurfaced",
                    "detail": f"prev 已 resolved 的 {fid} 在本轮被重复报",
                    "finding_id": fid})

    # dropped：prev keep 在新 keep_list 中消失（观察项，不判违例）
    for kid in prev_keeps:
        if kid not in new_keeps:
            dropped.append(kid)
            checks.append(c.ck(True, f"keep {kid} 在新版 keep_list 中消失（记录为 dropped，供追因）",
                               f"strengths:dropped:{kid}", "INFO"))

    for kid in prev_keeps:
        if kid in new_keeps:
            checks.append(c.ck(True, f"keep {kid} 保持保留", f"strengths:recheck:{kid}"))
    for v in violations:
        checks.append(c.ck(False, f"{v['rule']}：{v['detail']}",
                           f"strengths:{v['rule']}", "CRITICAL"))
    if not violations and prev_keeps:
        checks.append(c.ck(True, "复评三查全过：降级有理由/新 FAIL 落在 change 区/resolved 未重报",
                           "strengths:recheck"))

    recheck_verdict = "PASS" if not violations else "FAIL"
    out = c.result(checks,
                   downgrades=downgrades,
                   untraceable_new_fails=untraceable_new_fails,
                   resurfaced_resolved=resurfaced,
                   dropped_keeps=dropped,
                   violations=violations,
                   recheck_verdict=recheck_verdict,
                   next="复评通过：本轮修改未破坏保留优点" if recheck_verdict == "PASS"
                        else "复评违例：降级补理由/新 FAIL 补 change 区定位后重评",
                   )
    out["ok"] = out["ok"] and recheck_verdict == "PASS"
    return out


def recheck(prev: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    return _recheck_core(prev, new)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "mark":
        return mark(data)
    if args.action == "recheck":
        new = c.load_json(args.new)
        return recheck(data, new)
    raise SystemExit(f"未知动作：{args.action}")

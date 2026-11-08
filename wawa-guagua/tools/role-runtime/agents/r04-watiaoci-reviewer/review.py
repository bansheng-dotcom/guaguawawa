# -*- coding: utf-8 -*-
"""R04 T7 对抗评审（低温确定性，无 LLM 调用）。

对"评审产出本身"再评审，防止蛙挑刺自己出现五类系统病：
1. self_review_gate   reviewer==producer → BLOCKER（身份红线：评审者≠实现者）
2. evidence_gate       verdict=PASS 却无任何 evidence 字段 → BLOCKER 回 react
3. hedge_words        评审报告文本含 should/probably/seems to/I believe → 回 writer
4. never_fixes        评审输出含修复后内容声明（applied_fixes/modified 非空）→ BLOCKER
                      （评审只记录不修复）
5. keep_list_integrity keep 项被降级为 FAIL 无 resolution_reason → BLOCKER

三路由语义：react（重做/重算）/ writer（改写措辞）/ controller（丢弃）。
阈值：thresholds.json → review.*。
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from skills import _common as c

# 检查优先级：身份 > 修复红线 > 证据 > 降级 > 措辞
_CHECK_ORDER: List[str] = ["self_review_gate", "never_fixes", "evidence_gate",
                           "keep_list_integrity", "hedge_words"]
_ROUTES = {
    "self_review_gate": "react",
    "evidence_gate": "react",
    "hedge_words": "writer",
    "never_fixes": "react",
    "keep_list_integrity": "react",
}
_MESSAGES = {
    "self_review_gate": "评审者与生产者同体：实现者不得自评，必须换独立评审者重做",
    "evidence_gate": "verdict=PASS 却没有任何 evidence 字段：PASS 必须有证据链，回补证据重算",
    "hedge_words": "评审报告用了推测措辞（should/probably/seems to/I believe）：只能写 verified / not verified",
    "never_fixes": "评审输出含修复后内容声明（评审只记录不修复）：去掉 applied_fixes/modified 类字段重做",
    "keep_list_integrity": "keep 项被降级为 FAIL 却没有 resolution_reason：补理由或撤销降级",
}


def _walk(node: Any):
    """深度遍历，产出 (container, key, value)。"""
    if isinstance(node, dict):
        for k, v in node.items():
            yield node, k, v
            yield from _walk(v)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield node, i, v
            yield from _walk(v)


def _has_evidence(result: Dict[str, Any]) -> bool:
    """证据链 = 任一 evidence 字段在任何层级有非空值。"""
    evidence_keys = set(c.load_thresholds()["review"]["evidence_keys"])
    for _, k, v in _walk(result):
        if k in evidence_keys and _truthy(v):
            return True
    return False


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return True
    if isinstance(v, (str, list, dict)):
        return len(v) > 0
    return bool(v)


def _hedge_hits(result: Dict[str, Any]) -> List[str]:
    """hedge 扫描只看结论性文本（summary/conclusion/overall_note 等），
    不扫 msg/detail/quote 等元说明或用户原话（r06 第八节教训）。"""
    conclusion_keys = set(c.load_thresholds()["review"]["conclusion_keys"])
    hedge_words = c.load_thresholds()["review"]["hedge_words"]
    hits: List[str] = []
    for _, k, v in _walk(result):
        if k in conclusion_keys and isinstance(v, str):
            low = v.lower()
            hits.extend(w for w in hedge_words if w in low)
    return hits


def _fix_key_hits(result: Dict[str, Any]) -> List[str]:
    fix_keys = set(c.load_thresholds()["review"]["fix_keys"])
    return [k for _, k, v in _walk(result)
            if k in fix_keys and _truthy(v)]


def _keep_violations(result: Dict[str, Any]) -> List[str]:
    """downgrades/keep_list 条目：被降级为 FAIL 却没有 resolution_reason。"""
    bad: List[str] = []
    for _, k, v in _walk(result):
        entries: List[Any] = []
        if k in ("downgrades", "keep_list") and isinstance(v, list):
            entries = v
        for e in entries:
            if not isinstance(e, dict):
                continue
            failed = (str(e.get("new_status") or "").upper() == "FAIL"
                      or str(e.get("status") or "").upper() == "FAIL")
            if failed and not str(e.get("resolution_reason") or "").strip():
                bad.append(str(e.get("keep_id") or e.get("id") or "?"))
    return bad


def review_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    """对抗评审一个产出包 {run_id?, skill, action, result}。"""
    result = packet.get("result") or {}
    checks: List[Dict[str, Any]] = []
    failures: List[str] = []

    # 1) 身份红线：reviewer == producer
    producer = result.get("producer")
    reviewer = result.get("reviewer")
    pkg = result.get("review_package")
    if isinstance(pkg, dict):
        producer = producer or pkg.get("producer")
        reviewer = reviewer or pkg.get("reviewer")
    same = bool(producer) and bool(reviewer) and str(producer) == str(reviewer)
    checks.append(c.ck(not same,
                       f"身份核验：producer={producer!r} reviewer={reviewer!r}",
                       "review:self_review_gate",
                       "OK" if not same else "CRITICAL",
                       **{"producer": producer, "reviewer": reviewer, "same": same}))
    if same:
        failures.append("self_review_gate")

    # 2) never_fixes：评审不许修复
    fix_hits = _fix_key_hits(result)
    checks.append(c.ck(not fix_hits,
                       "无修复后内容声明（评审只记录不修复）" if not fix_hits
                       else f"检出修复后内容声明字段：{fix_hits}",
                       "review:never_fixes",
                       "OK" if not fix_hits else "CRITICAL",
                       **{"fix_keys_hit": fix_hits}))
    if fix_hits:
        failures.append("never_fixes")

    # 3) evidence_gate：PASS 必须有证据链
    verdict = result.get("verdict")
    has_ev = _has_evidence(result)
    ev_gate_ok = (verdict != "PASS") or has_ev
    checks.append(c.ck(ev_gate_ok,
                       f"verdict={verdict!r} 证据链={'有' if has_ev else '无'}",
                       "review:evidence_gate",
                       "OK" if ev_gate_ok else "CRITICAL",
                       **{"verdict": verdict, "has_evidence": has_ev}))
    if not ev_gate_ok:
        failures.append("evidence_gate")

    # 4) keep_list_integrity：降级须理由
    keep_bad = _keep_violations(result)
    checks.append(c.ck(not keep_bad,
                       "keep 项降级均有 resolution_reason" if not keep_bad
                       else f"keep 项降级无理由：{keep_bad}",
                       "review:keep_list_integrity",
                       "OK" if not keep_bad else "CRITICAL",
                       **{"keep_ids_without_reason": keep_bad}))
    if keep_bad:
        failures.append("keep_list_integrity")

    # 5) hedge_words：结论文本禁推测措辞
    hedge_hits = _hedge_hits(result)
    checks.append(c.ck(not hedge_hits,
                       "结论措辞干净（无 should/probably/seems to/I believe）"
                       if not hedge_hits else f"结论含推测措辞：{sorted(set(hedge_hits))}",
                       "review:hedge_words",
                       "OK" if not hedge_hits else "CRITICAL",
                       **{"hedge_words_hit": sorted(set(hedge_hits))}))
    if hedge_hits:
        failures.append("hedge_words")

    passed = not failures
    failure_category = failures[0] if failures else None
    if passed:
        next_step = "评审产出合格：可归档/签发"
    else:
        route = _ROUTES.get(failure_category, "react")
        if route == "react":
            next_step = f"回 react 重做：{_MESSAGES[failure_category]}"
        elif route == "writer":
            next_step = f"回 writer 改写：{_MESSAGES[failure_category]}"
        else:
            next_step = f"交 controller 丢弃：{_MESSAGES[failure_category]}"
    out = c.result(checks,
                   skill=packet.get("skill"),
                   action=packet.get("action"),
                   verdict="PASS" if passed else "FAIL",
                   failure_category=failure_category,
                   route=_ROUTES.get(failure_category) if failure_category else None,
                   next=next_step,
                   )
    out["ok"] = out["ok"] and passed
    return out


# --------------------------------------------------------------------------- #
# CLI：python review.py --packet packet.json
# --------------------------------------------------------------------------- #
def _cli() -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="R04 对抗评审器")
    ap.add_argument("--packet", required=True, help="待评审的产出包 JSON")
    args = ap.parse_args()
    packet = json.load(open(args.packet, encoding="utf-8"))
    out = review_packet(packet)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())

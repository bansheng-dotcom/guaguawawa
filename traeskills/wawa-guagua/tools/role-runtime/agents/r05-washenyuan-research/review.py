# -*- coding: utf-8 -*-
"""R05 对抗评审（T7）：对研究产出本身再评审。

角色化五检查（按优先级）：
1. unsourced_gate  —— verdict=PASS 却有 orphan_claims / coverage_gaps /
                      evidence_coverage<1 → BLOCKER，route=react（防幻觉核心）
2. evidence_gate   —— verdict=PASS 却无任何证据字段 → BLOCKER，route=react
3. decision_gate   —— 结论文本含决策词（建议/应该/决定…）→ route=writer
                      （R05 不替你拍板，决策权归老板）
4. scope_boundary  —— 结论文本含越界词（回归分析/审计意见/法律意见…）
                      → route=writer（须改写为移交 R06/R03）
5. hedge_words     —— 结论文本含推测措辞（可能/大概/预计…）→ route=writer

r06 教训：hedge/decision/scope 只扫 conclusion_keys 对应的文本值，
不扫 msg/detail/quote（评审建议文本必然含这些词，扫了全是误报）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from skills import _common as c


def _walk(node: Any, container=None, key=None,
          out: List[Tuple[Any, Any, Any]] = None):
    if out is None:
        out = []
    if isinstance(node, dict):
        for k, v in node.items():
            out.append((node, k, v))
            _walk(v, node, k, out)
    elif isinstance(node, list):
        for v in node:
            _walk(v, container, key, out)
    return out


def _text_values_by_keys(result: Dict[str, Any], keys: List[str]) -> List[str]:
    vals: List[str] = []
    for cont, k, v in _walk(result):
        if k in keys and isinstance(v, str):
            vals.append(v)
    return vals


def _has_evidence(result: Dict[str, Any]) -> bool:
    evidence_keys = set(c.load_thresholds()["review"]["evidence_keys"])

    def walk(node: Any) -> bool:
        if isinstance(node, dict):
            for k, v in node.items():
                if k in evidence_keys and _truthy(v):
                    return True
                if walk(v):
                    return True
        elif isinstance(node, list):
            for v in node:
                if walk(v):
                    return True
        return False

    return walk(result)


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


def review_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["review"]
    result = packet.get("result") or {}
    skill = str(packet.get("skill") or "")
    action = str(packet.get("action") or "")
    verdict = result.get("verdict")
    checks: List[Dict[str, Any]] = []

    conclusion_texts = _text_values_by_keys(result, list(th["conclusion_keys"]))

    # 1. unsourced_gate：PASS 却存在无源断言（防幻觉核心）
    orphan = result.get("orphan_claims") or []
    gaps = result.get("coverage_gaps") or []
    ev_cov = result.get("evidence_coverage")
    unsourced_hit = (bool(orphan) or bool(gaps)
                     or (isinstance(ev_cov, (int, float)) and ev_cov < 1.0))
    if verdict == "PASS" and unsourced_hit:
        checks.append(c.ck(False,
                           f"unsourced_gate：verdict=PASS 但存在无源断言"
                           f"（orphan_claims={len(orphan)} coverage_gaps={len(gaps)} "
                           f"evidence_coverage={ev_cov}）",
                           "review:unsourced", "BLOCKER",
                           **{"route": "react"}))
    else:
        checks.append(c.ck(True, "unsourced_gate：无矛盾（PASS 产出无无源断言）",
                           "review:unsourced"))

    # 2. evidence_gate：PASS 却无任何证据字段
    if verdict == "PASS" and not _has_evidence(result):
        checks.append(c.ck(False,
                           "evidence_gate：verdict=PASS 却无任何证据字段"
                           "（evidence/sources/claims/… 任一非空）",
                           "review:evidence", "BLOCKER",
                           **{"route": "react"}))
    else:
        checks.append(c.ck(True, "evidence_gate：证据字段在", "review:evidence"))

    # 3. decision_gate：R05 不替你拍板
    decision_words = list(th["decision_words"])
    decision_hits: List[str] = []
    for t in conclusion_texts:
        for w in decision_words:
            if w.lower() in t.lower():
                decision_hits.append(w)
    if decision_hits:
        checks.append(c.ck(False,
                           f"decision_gate：结论文本含决策词 {sorted(set(decision_hits))}，"
                           "R05 不替你拍板，须改为呈现选项与证据",
                           "review:decision", "BLOCKER",
                           **{"route": "writer"}))
    else:
        checks.append(c.ck(True, "decision_gate：结论未越权", "review:decision"))

    # 4. scope_boundary：数据分析/审计/法律判断须移交
    scope_words = list(th["scope_violation_words"])
    scope_hits: List[str] = []
    for t in conclusion_texts:
        for w in scope_words:
            if w.lower() in t.lower():
                scope_hits.append(w)
    if scope_hits:
        checks.append(c.ck(False,
                           f"scope_boundary：结论含越界词 {sorted(set(scope_hits))}，"
                           "数据分析结论移交 R06、正式财务/法律判断移交 R03",
                           "review:scope", "BLOCKER",
                           **{"route": "writer"}))
    else:
        checks.append(c.ck(True, "scope_boundary：未越界", "review:scope"))

    # 5. hedge_words：结论须陈述化
    hedge_words = list(th["hedge_words"])
    hedge_hits: List[str] = []
    for t in conclusion_texts:
        for w in hedge_words:
            if w.lower() in t.lower():
                hedge_hits.append(w)
    if hedge_hits:
        checks.append(c.ck(False,
                           f"hedge_words：结论文本含推测措辞 {sorted(set(hedge_hits))}，"
                           "改为『证据→结论』陈述式",
                           "review:hedge", "BLOCKER",
                           **{"route": "writer"}))
    else:
        checks.append(c.ck(True, "hedge_words：结论为陈述式", "review:hedge"))

    blockers = [ch for ch in checks if not ch.get("ok") and ch.get("sev") == "BLOCKER"]
    if blockers:
        first = blockers[0]
        out = {"ok": False, "skill": skill, "action": action,
               "verdict": "FAIL",
               "failure_category": first["dim"],
               "route": first.get("route", "react"),
               "checks": checks,
               "next": f"{first['msg']}；按 route={first.get('route')} 处置后重验"}
        return out
    return {"ok": True, "skill": skill, "action": action,
            "verdict": "PASS", "failure_category": None, "route": None,
            "checks": checks, "next": "研究产出通过对抗评审"}


if __name__ == "__main__":
    import json
    import sys
    packet_path = sys.argv[1] if len(sys.argv) > 1 else ""
    if not packet_path:
        print("用法：python review.py <packet.json>", file=sys.stderr)
        raise SystemExit(2)
    with open(packet_path, encoding="utf-8") as f:
        pkt = json.load(f)
    out = review_packet(pkt)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if out["ok"] else 1)

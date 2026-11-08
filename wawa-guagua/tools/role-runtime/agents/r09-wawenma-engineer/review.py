# -*- coding: utf-8 -*-
"""R09 对抗评审（T7）：对代码工程产出本身再评审。

角色化五检查（按优先级，对齐 R09 三条边界）：
1. test_skipped_gate  —— verdict=PASS 却有 skipped>0 / failed>0 / flaky>0 /
                         coverage<coverage_min → BLOCKER，route=react
                         （核心红线：不靠跳过测试制造假通过）
2. irreversible_gate  —— 产出含不可逆操作词但无 handoff/owner（未声明授权）
                         → BLOCKER，route=writer（不可逆线上操作需授权）
3. concrete_artifact  —— 无具体可运行/可交付物（缺 modules/services/tables/
                         endpoints/targets/suites/… 等）→ controller
4. scope_boundary     —— 产出含持续监控/备份/告警等越界词（R20 职责）但未声明
                         handoff/owner → writer（移交 R20）
5. evidence_gate      —— verdict=PASS 却无任何证据字段 → BLOCKER，route=react

r06/r08 教训：irreversible/scope 只扫 conclusion_keys 对应的文本值，
不扫 msg/dim/checks（评审建议文本必然含这些词，扫了全是误报）。
契约校验（T6）由 verify_loop 独立执行，不并入本评审器。
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


def _num_values_by_key(result: Dict[str, Any], key: str) -> List[Any]:
    vals: List[Any] = []
    for cont, k, v in _walk(result):
        if k == key and isinstance(v, (int, float)) and not isinstance(v, bool):
            vals.append(v)
    return vals


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


def review_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["review"]
    result = packet.get("result") or {}
    skill = str(packet.get("skill") or "")
    action = str(packet.get("action") or "")
    verdict = result.get("verdict")
    checks: List[Dict[str, Any]] = []

    conclusion_texts = _text_values_by_keys(result, list(th["conclusion_keys"]))
    declared_handoff = isinstance(result, dict) and any(
        k in result for k in th["handoff_keys"])

    # 1. test_skipped_gate：PASS 却存在跳过/失败/flaky/覆盖率不足
    skipped = sum(_num_values_by_key(result, "skipped"))
    failed = sum(_num_values_by_key(result, "failed"))
    flaky = sum(_num_values_by_key(result, "flaky"))
    coverage_vals = _num_values_by_key(result, "coverage")
    coverage = min(coverage_vals) if coverage_vals else None
    coverage_min = float(th.get("coverage_min", 0.8))
    test_broken = (skipped > 0 or failed > 0 or flaky > 0
                   or (coverage is not None and coverage < coverage_min))
    if verdict == "PASS" and test_broken:
        checks.append(c.ck(False,
                           f"test_skipped_gate：verdict=PASS 却存在测试缺口"
                           f"（skipped={skipped} failed={failed} flaky={flaky} "
                           f"coverage={coverage}）",
                           "review:test_skipped", "BLOCKER",
                           **{"route": "react"}))
    else:
        checks.append(c.ck(True, "test_skipped_gate：无假通过", "review:test_skipped"))

    # 2. irreversible_gate：不可逆操作词但无 handoff/owner
    irreversible_hits: List[str] = []
    for t in conclusion_texts:
        for w in th["irreversible_words"]:
            if w.lower() in t.lower():
                irreversible_hits.append(w)
    if irreversible_hits and not declared_handoff:
        checks.append(c.ck(False,
                           f"irreversible_gate：产出含不可逆操作词 "
                           f"{sorted(set(irreversible_hits))} 但未声明授权/handoff",
                           "review:irreversible", "BLOCKER",
                           **{"route": "writer"}))
    else:
        checks.append(c.ck(True, "irreversible_gate：不可逆操作有授权声明",
                           "review:irreversible"))

    # 3. concrete_artifact：至少一键可运行/可交付物
    concrete = isinstance(result, dict) and any(
        k in result for k in th["concrete_keys"])
    if not concrete:
        checks.append(c.ck(False, "无具体产物（缺可运行/可交付键）",
                           "review:concrete_artifact", "BLOCKER",
                           **{"route": "controller"}))
    else:
        checks.append(c.ck(True, "产出具体（可运行/可交付）",
                           "review:concrete_artifact"))

    # 4. scope_boundary：持续监控/备份/告警越界（R20 职责）
    scope_hits: List[str] = []
    for t in conclusion_texts:
        for w in th["scope_terms"]:
            if w.lower() in t.lower():
                scope_hits.append(w)
    if scope_hits and not declared_handoff:
        checks.append(c.ck(False,
                           f"scope_boundary：产出含持续监控/备份/告警词 "
                           f"{sorted(set(scope_hits))} 但未声明 handoff（移交 R20）",
                           "review:scope", "BLOCKER",
                           **{"route": "writer"}))
    else:
        checks.append(c.ck(True, "scope_boundary：未越界到 R20 监控/备份",
                           "review:scope"))

    # 5. evidence_gate：PASS 却无任何证据字段
    if verdict == "PASS" and not _has_evidence(result):
        checks.append(c.ck(False,
                           "evidence_gate：verdict=PASS 却无任何证据字段",
                           "review:evidence", "BLOCKER",
                           **{"route": "react"}))
    else:
        checks.append(c.ck(True, "evidence_gate：证据字段在", "review:evidence"))

    blockers = [ch for ch in checks if not ch.get("ok") and ch.get("sev") == "BLOCKER"]
    if blockers:
        first = blockers[0]
        out = {"ok": False, "skill": skill, "action": action,
               "verdict": "FAIL",
               "failure_category": first["dim"],
               "route": first.get("route", "react"),
               "execution_temperature": 0.0,
               "context_isolation": {"sees_full_material_pack": False,
                                     "sees_writer_hidden_reasoning": False,
                                     "input_scope": ["unit_packet", "contract"]},
               "checks": checks,
               "next": f"{first['msg']}；按 route={first.get('route')} 处置后重验"}
        return out
    return {"ok": True, "skill": skill, "action": action,
            "verdict": "PASS", "failure_category": None, "route": None,
            "execution_temperature": 0.0,
            "context_isolation": {"sees_full_material_pack": False,
                                  "sees_writer_hidden_reasoning": False,
                                  "input_scope": ["unit_packet", "contract"]},
            "checks": checks, "next": "代码工程产出通过对抗评审"}


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

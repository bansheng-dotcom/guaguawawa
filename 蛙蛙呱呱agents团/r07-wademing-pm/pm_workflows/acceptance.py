# -*- coding: utf-8 -*-
"""W4 acceptance：Given/When/Then → 边界/失败态 → 测试场景 → 发布门禁。

门禁：
  - 主路径至少 1 条、边界至少 1 条、失败态至少 1 条；
  - 每条场景必须有 Given/When/Then；
  - 每个场景至少映射 1 条测试场景（步骤 + 预期）；
  - 发布门禁检查项全部通过，且无阻断项，才允许 go。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import common as c

STAGE = "acceptance"
ARTIFACT = "acceptance_pack"

_TYPES = ("main", "boundary", "failure")
_PASS_STATUS = ("pass", "passed", "ok", "green")
_BLOCK_STATUS = ("block", "blocked", "fail", "failed", "red")


def _scenarios(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [x for x in (data.get("scenarios") or []) if isinstance(x, dict)]


def _tests(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [x for x in (data.get("test_scenarios") or []) if isinstance(x, dict)]


def build(data: Dict[str, Any]) -> Dict[str, Any]:
    data = data if isinstance(data, dict) else {}
    feature = str(data.get("feature") or "").strip()
    scenarios = _scenarios(data)
    tests = _tests(data)
    release = data.get("release_gate") if isinstance(data.get("release_gate"), dict) else {}
    checks: List[Dict[str, Any]] = []

    checks.append(c.ck(bool(feature), "缺少验收对象（feature）", "feature", "BLOCKER"))

    counts = {t: 0 for t in _TYPES}
    for idx, sc in enumerate(scenarios):
        kind = str(sc.get("type") or "").strip().lower()
        checks.append(c.ck(kind in _TYPES,
                           f"场景 {idx} type={kind!r} 不在 {_TYPES}", "scenario.type", "BLOCKER"))
        if kind in counts:
            counts[kind] += 1
        for key in ("given", "when", "then"):
            checks.append(c.ck(not c.blank(sc.get(key)),
                               f"场景 {idx} 缺少 {key}", f"scenario.{key}", "BLOCKER"))
        checks.append(c.ck(not c.blank(sc.get("expected")),
                           f"场景 {idx} 缺少预期结果（expected）",
                           "scenario.expected", "MAJOR"))

    checks.append(c.ck(counts["main"] >= 1, "缺少主路径场景（type=main）",
                       "scenario.main", "BLOCKER"))
    checks.append(c.ck(counts["boundary"] >= 1, "缺少边界场景（type=boundary）",
                       "scenario.boundary", "BLOCKER"))
    checks.append(c.ck(counts["failure"] >= 1, "缺少失败态场景（type=failure）",
                       "scenario.failure", "BLOCKER"))

    scenario_ids = [str(sc.get("id") or "") for sc in scenarios]
    covered = set()
    checks.append(c.ck(bool(tests), "缺少测试场景（test_scenarios）",
                       "test.input", "BLOCKER"))
    for idx, test in enumerate(tests):
        sid = str(test.get("scenario_id") or "")
        checks.append(c.ck(sid in scenario_ids,
                           f"测试 {idx} 映射的场景 {sid!r} 不存在",
                           "test.mapping", "BLOCKER"))
        if sid in scenario_ids:
            covered.add(sid)
        steps = test.get("steps")
        steps = steps if isinstance(steps, list) else []
        checks.append(c.ck(bool([s for s in steps if not c.blank(s)]),
                           f"测试 {idx} 缺少步骤（steps）", "test.steps", "BLOCKER"))
        checks.append(c.ck(not c.blank(test.get("expected")),
                           f"测试 {idx} 缺少预期（expected）", "test.expected", "BLOCKER"))
    missing = [sid for sid in scenario_ids if sid not in covered]
    checks.append(c.ck(not missing, f"场景未覆盖测试：{missing}", "test.coverage", "BLOCKER"))

    # 发布门禁
    gate_checks = release.get("checks")
    gate_checks = gate_checks if isinstance(gate_checks, list) else []
    checks.append(c.ck(bool(gate_checks), "缺少发布门禁检查项（release_gate.checks）",
                       "release.checks", "BLOCKER"))
    blockers = 0
    for idx, item in enumerate(gate_checks):
        item = item if isinstance(item, dict) else {}
        status = str(item.get("status") or "").strip().lower()
        checks.append(c.ck(not c.blank(item.get("name")),
                           f"发布检查 {idx} 缺少名称", "release.name", "BLOCKER"))
        ok_status = status in _PASS_STATUS
        checks.append(c.ck(ok_status,
                           f"发布检查「{item.get('name')}」状态 {status!r} 未通过",
                           "release.status", "BLOCKER"))
        if status in _BLOCK_STATUS or not ok_status:
            blockers += 1
    decision = "go" if gate_checks and blockers == 0 else "no-go"
    checks.append(c.ck(decision == "go", "存在未通过检查，发布门禁判定 no-go",
                       "release.decision", "BLOCKER"))

    g = c.gate(checks, STAGE)
    return {
        "artifact": ARTIFACT,
        "stage": STAGE,
        "feature": feature,
        "scenario_counts": counts,
        "scenarios": scenarios,
        "test_scenarios": tests,
        "release_gate": {"checks": gate_checks, "blockers": blockers,
                         "decision": decision},
        "gate": g,
    }

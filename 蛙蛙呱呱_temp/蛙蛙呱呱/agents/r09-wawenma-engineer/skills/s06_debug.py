# -*- coding: utf-8 -*-
"""s06 调试性能重构（debug）：debug / refactor 两动作。

- debug：稳定复现→根因——复现步骤、根因、修复（Iron Law：无根因不修复）。
- refactor：测试保护下重构——回归测试、性能热点、测试覆盖。
阈值：thresholds.json → debug.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "debug"
DESC = "调试性能重构：稳定复现、定位根因、剖析热点、测试保护重构"

ACTIONS = {
    "debug": "复现与根因定位",
    "refactor": "性能剖析与测试保护重构",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# debug
# --------------------------------------------------------------------------- #
def debug(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["debug"]
    min_repro_steps = th["min_repro_steps"]

    symptom = str(data.get("symptom") or "")
    steps = data.get("repro_steps") or []
    root_cause = str(data.get("root_cause") or "")
    fix = str(data.get("fix") or "")
    checks: List[Dict[str, Any]] = []

    if not symptom:
        checks.append(c.ck(False, "缺 symptom 症状描述", "debug:symptom", "CRITICAL"))

    if len(steps) < min_repro_steps:
        checks.append(c.ck(False, f"复现步骤 {len(steps)} < {min_repro_steps}（须稳定复现）", "debug:repro", "CRITICAL"))
    else:
        checks.append(c.ck(True, f"复现步骤 {len(steps)} 条", "debug:repro", **{"step_count": len(steps)}))

    if not root_cause:
        checks.append(c.ck(False, "缺 root_cause（无根因不修复）", "debug:root_cause", "CRITICAL"))
    else:
        checks.append(c.ck(True, "根因已定位", "debug:root_cause"))

    if not fix:
        checks.append(c.ck(False, "缺 fix 修复方案", "debug:fix", "CRITICAL"))
    else:
        checks.append(c.ck(True, "修复方案已给出", "debug:fix"))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   symptom=symptom,
                   repro_step_count=len(steps),
                   root_cause=root_cause,
                   verdict=verdict,
                   next="根因清晰、修复方案齐全" if ok else "补齐复现步骤/根因/修复后重新 debug",
                   )
    return out


# --------------------------------------------------------------------------- #
# refactor
# --------------------------------------------------------------------------- #
def refactor(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["debug"]

    hotspots = data.get("hotspots") or []
    regression = data.get("regression_tests") or []
    checks: List[Dict[str, Any]] = []

    if not hotspots:
        checks.append(c.ck(False, "hotspots 为空，无性能热点可剖析", "debug:hotspots", "CRITICAL"))

    for i, h in enumerate(hotspots):
        name = str(h.get("name") or "")
        before = h.get("before_ms")
        after = h.get("after_ms")
        if not name:
            checks.append(c.ck(False, f"hotspots[{i}] 缺 name", "debug:hotspot_name", "HIGH", **{"index": i}))
        if before is None or after is None:
            checks.append(c.ck(False, f"热点 {name!r} 缺 before_ms/after_ms", "debug:hotspot_measure", "HIGH", **{"name": name}))
        elif after > before:
            checks.append(c.ck(False, f"热点 {name!r} 优化后 {after}ms > 优化前 {before}ms（劣化）", "debug:hotspot_regress", "HIGH", **{"name": name}))
        else:
            checks.append(c.ck(True, f"热点 {name!r} {before}ms → {after}ms", "debug:hotspot", **{"name": name}))

    if not regression:
        checks.append(c.ck(False, "regression_tests 为空（重构必须在测试保护下进行）", "debug:regression", "CRITICAL"))
    else:
        bad = [t for t in regression if str(t.get("status") or "") == "failed"]
        if bad:
            checks.append(c.ck(False, f"回归测试失败 {len(bad)} 条", "debug:regression_failed", "CRITICAL", **{"failed": len(bad)}))
        else:
            checks.append(c.ck(True, f"回归测试 {len(regression)} 条全绿", "debug:regression", **{"count": len(regression)}))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   hotspot_count=len(hotspots),
                   regression_count=len(regression),
                   verdict=verdict,
                   next="重构在测试保护下完成、热点无劣化" if ok else "修复热点劣化/回归失败后重新 refactor",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "debug":
        result = debug(data)
    elif args.action == "refactor":
        result = refactor(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result

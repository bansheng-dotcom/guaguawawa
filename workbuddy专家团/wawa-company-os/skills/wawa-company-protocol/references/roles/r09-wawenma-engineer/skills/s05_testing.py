# -*- coding: utf-8 -*-
"""s05 测试与浏览器验证（testing）：suites / browser 两动作。

- suites：测试套件——suite_type 白名单、跳过测试拦截、覆盖率门槛。
- browser：浏览器关键路径——flow 结果枚举、flaky 拦截、playwright_trace。
阈值：thresholds.json → testing.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "testing"
DESC = "测试与浏览器验证：单元/集成/契约/E2E 与真实浏览器关键路径"

ACTIONS = {
    "suites": "测试套件与覆盖率",
    "browser": "浏览器关键路径验证",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# suites
# --------------------------------------------------------------------------- #
def suites(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["testing"]
    suite_types = th["suite_types"]
    coverage_min = th["coverage_min"]
    max_skipped = th["max_skipped"]

    suites_list = data.get("suites") or []
    coverage = data.get("coverage")
    checks: List[Dict[str, Any]] = []

    if not suites_list:
        checks.append(c.ck(False, "suites 为空，无测试套件可校验", "testing:suites", "CRITICAL"))

    skipped = 0
    for i, s in enumerate(suites_list):
        stype = str(s.get("suite_type") or "")
        skipped_n = s.get("skipped") or 0
        failed_n = s.get("failed") or 0
        if stype not in suite_types:
            checks.append(c.ck(False, f"suites[{i}] suite_type={stype!r} 不在白名单 {suite_types}", "testing:suite_type", "HIGH", **{"index": i}))
        else:
            checks.append(c.ck(True, f"套件类型 {stype} 合规", "testing:suite_type", **{"suite_type": stype}))
        if skipped_n:
            skipped += skipped_n
            checks.append(c.ck(False, f"套件 {stype} 跳过测试 {skipped_n} 条", "testing:skipped", "HIGH", **{"suite_type": stype, "skipped": skipped_n}))
        if failed_n:
            checks.append(c.ck(False, f"套件 {stype} 失败测试 {failed_n} 条", "testing:failed", "HIGH", **{"suite_type": stype, "failed": failed_n}))

    if skipped > max_skipped:
        checks.append(c.ck(False, f"总跳过测试 {skipped} > 上限 {max_skipped}（不靠跳过测试制造假通过）", "testing:skip_cap", "CRITICAL"))

    if coverage is None or not isinstance(coverage, (int, float)):
        checks.append(c.ck(False, "缺覆盖率 coverage 数值", "testing:coverage", "CRITICAL"))
    elif coverage < coverage_min:
        checks.append(c.ck(False, f"覆盖率 {coverage} < 门槛 {coverage_min}", "testing:coverage_min", "CRITICAL", **{"coverage": coverage}))
    else:
        checks.append(c.ck(True, f"覆盖率 {coverage} 达标（≥{coverage_min}）", "testing:coverage_min", **{"coverage": coverage}))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   suite_count=len(suites_list),
                   skipped=skipped,
                   coverage=coverage,
                   verdict=verdict,
                   next="测试套件与覆盖率达标" if ok else "消除跳过/失败测试或提覆盖率后重新 suites",
                   )
    return out


# --------------------------------------------------------------------------- #
# browser
# --------------------------------------------------------------------------- #
def browser(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["testing"]
    flow_results = th["flow_results"]

    flows = data.get("flows") or []
    trace = str(data.get("playwright_trace") or "")
    checks: List[Dict[str, Any]] = []

    if not flows:
        checks.append(c.ck(False, "flows 为空，无浏览器关键路径可验证", "testing:flows", "CRITICAL"))

    passed = 0
    flaky = 0
    failed = 0
    for i, f in enumerate(flows):
        result = str(f.get("result") or "")
        if result not in flow_results:
            checks.append(c.ck(False, f"flows[{i}] result={result!r} 不在枚举 {flow_results}", "testing:flow_result", "HIGH", **{"index": i}))
        elif result == "passed":
            passed += 1
            checks.append(c.ck(True, f"流程 {f.get('name')!r} 通过", "testing:flow", **{"name": f.get("name")}))
        elif result == "flaky":
            flaky += 1
            checks.append(c.ck(False, f"流程 {f.get('name')!r} flaky", "testing:flaky", "HIGH", **{"name": f.get("name")}))
        elif result == "failed":
            failed += 1
            checks.append(c.ck(False, f"流程 {f.get('name')!r} 失败", "testing:flow_failed", "HIGH", **{"name": f.get("name")}))

    if not trace:
        checks.append(c.ck(False, "缺 playwright_trace（浏览器验证必须留轨迹）", "testing:trace", "HIGH"))
    else:
        checks.append(c.ck(True, "playwright_trace 已记录", "testing:trace"))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   flow_count=len(flows),
                   passed=passed,
                   flaky=flaky,
                   failed=failed,
                   playwright_trace=trace,
                   verdict=verdict,
                   next="浏览器关键路径验证通过" if ok else "消除 flaky/failed 流程或补轨迹后重新 browser",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "suites":
        result = suites(data)
    elif args.action == "browser":
        result = browser(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result

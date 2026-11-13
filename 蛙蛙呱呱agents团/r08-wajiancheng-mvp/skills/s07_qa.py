# -*- coding: utf-8 -*-
"""S07 质量验证与交接 —— 能力域 7。

整合自 makerskills（quality-gate / handoff）+ product-manager。把 MVP 快速
跑过质量门禁并交接：五大必需检查（build/typecheck/screenshot/design_qa/a11y）
状态合法、无障碍项≥3、测试点带预期；交接时产出物≥2、可运行命令、验收
与责任人齐备。

动作：
  qa       校验质量验证（五检查 + a11y_items + test_points）
  handoff  校验交接（artifacts + run_commands + acceptance + owner）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "qa"
DESC = "质量验证与交接：qa/handoff"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    q = act.add_parser("qa", help="校验质量验证结果")
    q.add_argument("--input", required=True)
    h = act.add_parser("handoff", help="校验交接包")
    h.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "qa":
        return _validate_qa(data)
    if args.action == "handoff":
        return _validate_handoff(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _normalize_checks(qa_checks: Any) -> List[Dict[str, Any]]:
    """把 dict（{name: status|{status}}）或 list（[{name,status}]）规范化。"""
    out: List[Dict[str, Any]] = []
    if isinstance(qa_checks, list):
        return [x for x in qa_checks if isinstance(x, dict)]
    if isinstance(qa_checks, dict):
        for k, v in qa_checks.items():
            if isinstance(v, str):
                out.append({"name": k, "status": v})
            elif isinstance(v, dict):
                out.append({"name": k, **v})
    return out


def _validate_qa(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    required_checks = th["qa"]["required_checks"]
    status_types = th["qa"]["status_types"]
    a11y_min = th["qa"]["a11y_min"]

    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    qa_checks = _normalize_checks(data.get("checks"))
    if not qa_checks:
        checks.append(_ck(False, "checks 缺失或为空", "qa.checks"))

    ok = True
    present = {str(c.get("name", "")): c for c in qa_checks}
    for rc in required_checks:
        item = present.get(rc)
        if item is None:
            checks.append(_ck(False, f"缺必需检查 {rc}", f"qa.{rc}"))
            ok = False
            continue
        status = str(item.get("status", "")).strip().lower()
        if status in status_types:
            checks.append(_ck(True, f"{rc} status={status}", f"qa.{rc}"))
        else:
            checks.append(_ck(False, f"{rc} status 非法/缺失（应 {status_types}）",
                              f"qa.{rc}.status"))
            ok = False

    a11y = data.get("a11y_items")
    ok_a = isinstance(a11y, list) and len(a11y) >= a11y_min
    checks.append(_ck(ok_a,
                      f"a11y_items ≥{a11y_min}（实际 {len(a11y) if isinstance(a11y, list) else 0}）",
                      "qa.a11y"))
    if not ok_a:
        ok = False

    test_points = data.get("test_points")
    ok_tp = isinstance(test_points, list) and len(test_points) >= 1
    checks.append(_ck(ok_tp,
                      f"test_points ≥1（实际 {len(test_points) if isinstance(test_points, list) else 0}）",
                      "qa.test_points"))
    tp_ok = ok_tp
    if isinstance(test_points, list):
        for i, tp in enumerate(test_points):
            if not isinstance(tp, dict):
                checks.append(_ck(False, f"test_point[{i}] 非对象", "qa.test_point"))
                tp_ok = False
                continue
            for k in ("name", "expectation"):
                if not str(tp.get(k, "")).strip():
                    checks.append(_ck(False, f"test_point[{i}] 缺 {k}",
                                      f"qa.test_point.{k}"))
                    tp_ok = False

    ok = ok and tp_ok
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    check_count=len(qa_checks))


# --------------------------------------------------------------------------- #
def _validate_handoff(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    artifacts = data.get("artifacts")
    ok_a = isinstance(artifacts, list) and len(artifacts) >= 2
    checks.append(_ck(ok_a,
                      f"artifacts ≥2（实际 {len(artifacts) if isinstance(artifacts, list) else 0}）",
                      "handoff.artifacts"))

    run_commands = data.get("run_commands")
    ok_r = isinstance(run_commands, list) and len(run_commands) >= 1
    checks.append(_ck(ok_r,
                      f"run_commands ≥1（实际 {len(run_commands) if isinstance(run_commands, list) else 0}）",
                      "handoff.run_commands"))

    acceptance = data.get("acceptance")
    ok_ac = isinstance(acceptance, list) and len(acceptance) >= 1
    checks.append(_ck(ok_ac,
                      f"acceptance ≥1（实际 {len(acceptance) if isinstance(acceptance, list) else 0}）",
                      "handoff.acceptance"))

    owner = str(data.get("owner", "")).strip()
    ok_o = bool(owner)
    checks.append(_ck(ok_o, "owner 非空" if ok_o else "owner 缺失",
                      "handoff.owner"))

    ok = ok_a and ok_r and ok_ac and ok_o
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    artifact_count=len(artifacts) if isinstance(artifacts, list) else 0)
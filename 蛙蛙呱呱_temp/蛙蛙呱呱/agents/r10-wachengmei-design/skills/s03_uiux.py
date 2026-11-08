# -*- coding: utf-8 -*-
"""S03 产品与 UI/UX —— 能力域 3。

整合自 mae616__design-skills(ui-designer / frontend-implementation /
accessibility-engineer / usability-psychologist)。
把「UI 不是艺术，是决策支持」落成确定性校验：屏幕目标/成功标准必填、
信息分区 ≥3、组件带状态、完整状态集合（normal/loading/empty/error/disabled）、
无障碍三底线（键盘可达/焦点可见/对比度）。

动作：
  screen  校验屏幕设计（goal/zones/components/a11y）
  ux      校验可用性评估（problem/causes/improvements/a11y/validation）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "uiux"
DESC = "产品与UI/UX：screen/ux"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    sc = act.add_parser("screen", help="校验屏幕设计")
    sc.add_argument("--input", required=True)
    ux = act.add_parser("ux", help="校验可用性评估")
    ux.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "screen":
        return _validate_screen(data)
    if args.action == "ux":
        return _validate_ux(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _validate_screen(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    goal = str(data.get("goal", "")).strip()
    checks.append(_ck(bool(goal), f"goal 非空（屏幕目的）", "screen.goal"))
    criteria = str(data.get("success_criteria", "")).strip()
    checks.append(_ck(bool(criteria), f"success_criteria 非空", "screen.success_criteria"))

    zones = data.get("zones")
    ok_z = isinstance(zones, list) and len(zones) >= th["uiux"]["zones_min"]
    checks.append(_ck(ok_z,
                      f"信息分区 ≥{th['uiux']['zones_min']}（实际 {len(zones) if isinstance(zones, list) else 0}）",
                      "screen.zones"))

    components = data.get("components")
    if not isinstance(components, list) or len(components) < 1:
        checks.append(_ck(False, "components ≥1 缺失", "screen.components"))
        comp_ok = False
    else:
        comp_ok = True
        for i, comp in enumerate(components):
            if not isinstance(comp, dict):
                checks.append(_ck(False, f"component[{i}] 非对象", "screen.components"))
                comp_ok = False
                continue
            if not str(comp.get("name", "")).strip():
                checks.append(_ck(False, f"component[{i}] 缺 name", "screen.components"))
                comp_ok = False
            states = comp.get("states")
            if not isinstance(states, list) or len(states) < 1:
                checks.append(_ck(False, f"component[{i}] states ≥1 缺失",
                                  "screen.components.states"))
                comp_ok = False

    # 完整状态集合：整屏至少覆盖 normal/loading/empty/error/disabled
    state_set = set()
    if isinstance(components, list):
        for comp in components:
            if isinstance(comp, dict) and isinstance(comp.get("states"), list):
                state_set.update(comp["states"])
    missing_states = [s for s in th["uiux"]["states"] if s not in state_set]
    ok_st = not missing_states
    checks.append(_ck(ok_st,
                      f"状态集合覆盖 {th['uiux']['states']}（缺 {missing_states or '无'}）",
                      "screen.states.coverage"))

    a11y = data.get("a11y")
    if not isinstance(a11y, dict):
        checks.append(_ck(False, "a11y 缺失或非对象", "screen.a11y"))
        a11y_ok = False
    else:
        ok_kb = bool(a11y.get("keyboard_operable"))
        ok_focus = bool(a11y.get("focus_visible"))
        ok_contrast = bool(a11y.get("contrast_ok"))
        checks.append(_ck(ok_kb, "a11y 键盘可达", "screen.a11y.keyboard"))
        checks.append(_ck(ok_focus, "a11y 焦点可见", "screen.a11y.focus"))
        checks.append(_ck(ok_contrast, "a11y 对比度达标", "screen.a11y.contrast"))
        a11y_ok = ok_kb and ok_focus and ok_contrast

    ok = bool(goal) and bool(criteria) and ok_z and comp_ok and ok_st and a11y_ok
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    zone_count=len(zones) if isinstance(zones, list) else 0,
                    component_count=len(components) if isinstance(components, list) else 0,
                    states_covered=sorted(state_set))


# --------------------------------------------------------------------------- #
def _validate_ux(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    problem = str(data.get("problem", "")).strip()
    checks.append(_ck(bool(problem), f"problem 非空（问题陈述）", "ux.problem"))

    causes = data.get("causes")
    ok_c = isinstance(causes, list) and len(causes) >= 1
    checks.append(_ck(ok_c,
                      f"causes ≥1（实际 {len(causes) if isinstance(causes, list) else 0}）",
                      "ux.causes"))

    improvements = data.get("improvements")
    ok_i = isinstance(improvements, list) and len(improvements) >= 1
    checks.append(_ck(ok_i,
                      f"improvements ≥1（实际 {len(improvements) if isinstance(improvements, list) else 0}）",
                      "ux.improvements"))

    validation = data.get("validation")
    ok_v = isinstance(validation, dict) and bool(validation.get("metrics"))
    checks.append(_ck(ok_v, f"validation.metrics 非空（可测指标）", "ux.validation"))

    ok = bool(problem) and ok_c and ok_i and ok_v
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    cause_count=len(causes) if isinstance(causes, list) else 0,
                    improvement_count=len(improvements) if isinstance(improvements, list) else 0)

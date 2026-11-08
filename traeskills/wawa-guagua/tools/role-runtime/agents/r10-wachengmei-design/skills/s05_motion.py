# -*- coding: utf-8 -*-
"""S05 交互原型与动效 —— 能力域 5。

整合自 LottieFiles__motion-design-skill（三支柱：情绪意图/视觉叙事/动效工艺；
四人格：playful/premium/corporate/energetic）+ mae616__design-skills(creative-coder)。
把「动效是信息，不是噪音」落成确定性校验：人格白名单、时长区间、
入场减速/出场加速、减少动效(reduced motion)、三层次（主/次/环境）。

动作：
  motion   校验动效规格（personality/duration/easing/layers）
  prototype 校验交互原型（flow/screens/trigger）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "motion"
DESC = "交互原型与动效：motion/prototype"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    mo = act.add_parser("motion", help="校验动效规格")
    mo.add_argument("--input", required=True)
    pt = act.add_parser("prototype", help="校验交互原型")
    pt.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "motion":
        return _validate_motion(data)
    if args.action == "prototype":
        return _validate_prototype(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _validate_motion(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    personality = data.get("personality")
    ok_p = personality in th["motion"]["personalities"]
    checks.append(_ck(ok_p,
                      f"personality={personality!r} 在白名单 {th['motion']['personalities']}",
                      "motion.personality"))

    # 时长区间：按人格取阈值区间
    duration = data.get("duration_ms")
    ok_dur = isinstance(duration, (int, float))
    if ok_dur and ok_p:
        lo, hi = th["motion"]["duration_ms"][personality]
        ok_dur = lo <= duration <= hi
        checks.append(_ck(ok_dur,
                          f"duration={duration}ms 在 [{lo}, {hi}]（{personality}）",
                          "motion.duration"))
    else:
        checks.append(_ck(ok_dur,
                          f"duration_ms 为数字（实际 {duration!r}）",
                          "motion.duration"))

    easing = str(data.get("easing", "")).strip()
    ok_e = bool(easing)
    checks.append(_ck(ok_e, f"easing 非空（{easing or '缺失'}）", "motion.easing"))
    # 入场减速/出场加速：acceleration 字段须标明 enter/exit 方向
    accel = data.get("acceleration")
    if not isinstance(accel, dict):
        checks.append(_ck(False, "acceleration 缺失（enter/exit 方向）",
                          "motion.acceleration"))
        acc_ok = False
    else:
        ok_acc = (str(accel.get("enter", "")).strip() in
                  ("decelerate", "ease-out")) and \
                 (str(accel.get("exit", "")).strip() in ("accelerate", "ease-in"))
        checks.append(_ck(ok_acc,
                          f"enter=decelerate / exit=accelerate（{accel}）",
                          "motion.acceleration"))
        acc_ok = ok_acc

    # reduced motion：减少动效必须开启
    reduced = data.get("reduced_motion")
    ok_rm = reduced is True or reduced == "supported"
    checks.append(_ck(ok_rm,
                      f"reduced_motion 支持（{reduced!r}）",
                      "motion.reduced_motion"))

    # 三层动效（主/次/环境）
    layers = data.get("layers")
    if not isinstance(layers, dict):
        checks.append(_ck(False, "layers 缺失（primary/secondary/ambient）",
                          "motion.layers"))
        layer_ok = False
    else:
        missing = [l for l in ("primary", "secondary", "ambient")
                   if not str(layers.get(l, "")).strip()]
        checks.append(_ck(not missing,
                          f"三层动效齐备（缺 {missing or '无'}）",
                          "motion.layers"))
        layer_ok = not missing

    ok = ok_p and ok_dur and ok_e and acc_ok and ok_rm and layer_ok
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    personality=personality,
                    duration_ms=duration if isinstance(duration, (int, float)) else None)


# --------------------------------------------------------------------------- #
def _validate_prototype(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    flow = data.get("flow")
    ok_f = isinstance(flow, list) and len(flow) >= 1
    checks.append(_ck(ok_f,
                      f"flow ≥1（实际 {len(flow) if isinstance(flow, list) else 0}）",
                      "prototype.flow"))

    screens = data.get("screens")
    ok_s = isinstance(screens, list) and len(screens) >= 1
    checks.append(_ck(ok_s,
                      f"screens ≥1（实际 {len(screens) if isinstance(screens, list) else 0}）",
                      "prototype.screens"))

    trigger = str(data.get("trigger", "")).strip()
    checks.append(_ck(bool(trigger), f"trigger 非空（触发方式）", "prototype.trigger"))

    ok = ok_f and ok_s and bool(trigger)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    flow_count=len(flow) if isinstance(flow, list) else 0,
                    screen_count=len(screens) if isinstance(screens, list) else 0)

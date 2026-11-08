# -*- coding: utf-8 -*-
"""S05 跨平台原型 —— 能力域 5。

整合自 flutter（Flutter 跨端）+ makerskills（prototype）。把 PRD 快速搭成
跨平台可跑原型：结构键六件套（main/app/core/features/shared_widgets/router）、
feature 分层（data/domain/presentation/providers）、平台白名单；单屏校验
Widget 类型、常量构造、断点与表单三件套。

动作：
  prototype  校验跨平台原型（六结构键 + feature 四层 + 平台白名单）
  screen     校验单屏（widget_type/const_constructor/breakpoints/form）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "prototype"
DESC = "跨平台原型：prototype/screen"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    pr = act.add_parser("prototype", help="校验跨平台原型结构")
    pr.add_argument("--input", required=True)
    sc = act.add_parser("screen", help="校验单屏 Widget")
    sc.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "prototype":
        return _validate_prototype(data)
    if args.action == "screen":
        return _validate_screen(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _validate_prototype(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    structure_keys = th["prototype"]["structure_keys"]
    feature_layers = th["prototype"]["feature_layers"]
    platforms_whitelist = th["prototype"]["platforms"]

    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    ok = True
    for k in structure_keys:
        if k in data:
            checks.append(_ck(True, f"结构键 {k} 存在", f"prototype.{k}"))
        else:
            checks.append(_ck(False, f"缺结构键 {k}", f"prototype.{k}"))
            ok = False

    features = data.get("features")
    ok_f = isinstance(features, list) and len(features) >= 1
    checks.append(_ck(ok_f,
                      f"features ≥1（实际 {len(features) if isinstance(features, list) else 0}）",
                      "prototype.features"))
    feat_ok = ok_f
    if isinstance(features, list):
        for i, f in enumerate(features):
            if not isinstance(f, dict):
                checks.append(_ck(False, f"feature[{i}] 非对象",
                                  "prototype.feature"))
                feat_ok = False
                continue
            if not str(f.get("name", "")).strip():
                checks.append(_ck(False, f"feature[{i}] 缺 name",
                                  "prototype.feature.name"))
                feat_ok = False
            layers = f.get("layers")
            if not isinstance(layers, dict):
                checks.append(_ck(False, f"feature[{i}] 缺 layers（dict）",
                                  "prototype.feature.layers"))
                feat_ok = False
            else:
                for layer in feature_layers:
                    if layer in layers:
                        checks.append(_ck(True, f"feature[{i}].layers.{layer}",
                                          "prototype.feature.layers"))
                    else:
                        checks.append(_ck(False, f"feature[{i}] layers 缺 {layer}",
                                          "prototype.feature.layers"))
                        feat_ok = False

    platforms = data.get("platforms")
    ok_p = isinstance(platforms, list) and len(platforms) >= 1
    checks.append(_ck(ok_p,
                      f"platforms ≥1（实际 {len(platforms) if isinstance(platforms, list) else 0}）",
                      "prototype.platforms"))
    p_ok = ok_p
    if isinstance(platforms, list):
        for p in platforms:
            if str(p) in platforms_whitelist:
                checks.append(_ck(True, f"平台 {p} 合法", "prototype.platforms"))
            else:
                checks.append(_ck(False, f"平台 {p!r} 非法（应 {platforms_whitelist}）",
                                  "prototype.platforms"))
                p_ok = False

    ok = ok and feat_ok and p_ok
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    feature_count=len(features) if isinstance(features, list) else 0)


# --------------------------------------------------------------------------- #
def _validate_screen(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    widget_type = str(data.get("widget_type", "")).strip().lower()
    ok_w = widget_type in ("stateless", "stateful")
    checks.append(_ck(ok_w,
                      f"widget_type={widget_type or '缺失'}（应 stateless/stateful）",
                      "screen.widget_type"))

    const_constructor = data.get("const_constructor")
    const_ok = True
    if not isinstance(const_constructor, bool):
        checks.append(_ck(False, "const_constructor 应为布尔",
                          "screen.const_constructor"))
        const_ok = False
    elif widget_type == "stateless" and const_constructor is not True:
        checks.append(_ck(False, "stateless 未声明 const_constructor=True",
                          "screen.const_constructor"))
        const_ok = False
    else:
        checks.append(_ck(True, f"const_constructor={const_constructor}",
                          "screen.const_constructor"))

    ok = ok_w and const_ok

    breakpoints = data.get("breakpoints")
    if not isinstance(breakpoints, dict):
        checks.append(_ck(False, "breakpoints 缺失或非对象", "screen.breakpoints"))
        ok = False
    else:
        for bp in ("mobile", "tablet", "desktop"):
            if bp in breakpoints:
                checks.append(_ck(True, f"breakpoints.{bp} 存在",
                                  "screen.breakpoints"))
            else:
                checks.append(_ck(False, f"breakpoints 缺 {bp}",
                                  "screen.breakpoints"))
                ok = False

    form = data.get("form")
    if form is not None:
        if not isinstance(form, dict):
            checks.append(_ck(False, "form 应为对象", "screen.form"))
            ok = False
        else:
            for f in ("form_key", "controller", "validator"):
                if str(form.get(f, "")).strip():
                    checks.append(_ck(True, f"form.{f} 非空", "screen.form"))
                else:
                    checks.append(_ck(False, f"form 缺 {f}", f"screen.form.{f}"))
                    ok = False

    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    widget_type=widget_type)
# -*- coding: utf-8 -*-
"""S06 组件与设计实现 —— 能力域 6。

整合自 makerskills（design-system / design-token）+ flutter（组件库）。
把设计稿实现为可复用的 token 与组件：tokens 三分类（color/typography/spacing）
每项 name+value，components 每个带 name/platform/states；单套 token 需
primary/secondary 主色 + scale 阶梯。

动作：
  design  校验设计系统（tokens 三类 + components ≥1）
  token   校验单套 token（primary/secondary + scale）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "design"
DESC = "组件与设计实现：design/token"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    d = act.add_parser("design", help="校验设计系统")
    d.add_argument("--input", required=True)
    t = act.add_parser("token", help="校验单套 token")
    t.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "design":
        return _validate_design(data)
    if args.action == "token":
        return _validate_token(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _validate_design(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    token_types = th["design"]["token_types"]

    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    tokens = data.get("tokens")
    ok = True
    token_count = 0
    if not isinstance(tokens, dict):
        checks.append(_ck(False, "tokens 缺失或非对象", "design.tokens"))
        ok = False
    else:
        for tt in token_types:
            grp = tokens.get(tt)
            if not isinstance(grp, list) or len(grp) < 1:
                checks.append(_ck(False, f"tokens.{tt} 缺失或为空",
                                  f"design.tokens.{tt}"))
                ok = False
            else:
                token_count += len(grp)
                for i, item in enumerate(grp):
                    if not isinstance(item, dict):
                        checks.append(_ck(False, f"tokens.{tt}[{i}] 非对象",
                                          f"design.tokens.{tt}"))
                        ok = False
                        continue
                    for k in ("name", "value"):
                        if not str(item.get(k, "")).strip():
                            checks.append(_ck(False, f"tokens.{tt}[{i}] 缺 {k}",
                                              f"design.tokens.{tt}"))
                            ok = False

    components = data.get("components")
    ok_c = isinstance(components, list) and len(components) >= 1
    checks.append(_ck(ok_c,
                      f"components ≥1（实际 {len(components) if isinstance(components, list) else 0}）",
                      "design.components"))
    c_ok = ok_c
    if isinstance(components, list):
        for i, comp in enumerate(components):
            if not isinstance(comp, dict):
                checks.append(_ck(False, f"component[{i}] 非对象",
                                  "design.component"))
                c_ok = False
                continue
            for k in ("name", "platform"):
                if not str(comp.get(k, "")).strip():
                    checks.append(_ck(False, f"component[{i}] 缺 {k}",
                                      f"design.component.{k}"))
                    c_ok = False
            states = comp.get("states")
            if not isinstance(states, list) or len(states) < 1:
                checks.append(_ck(False, f"component[{i}] states ≥1 缺失",
                                  "design.component.states"))
                c_ok = False

    ok = ok and c_ok
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    token_count=token_count,
                    component_count=len(components) if isinstance(components, list) else 0)


# --------------------------------------------------------------------------- #
def _validate_token(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    primary = str(data.get("primary", "")).strip()
    secondary = str(data.get("secondary", "")).strip()
    checks.append(_ck(bool(primary), f"primary={primary or '缺失'}", "token.primary"))
    checks.append(_ck(bool(secondary), f"secondary={secondary or '缺失'}",
                      "token.secondary"))

    scale = data.get("scale")
    ok_scale = isinstance(scale, list) and len(scale) >= 1
    checks.append(_ck(ok_scale,
                      f"scale ≥1（实际 {len(scale) if isinstance(scale, list) else 0}）",
                      "token.scale"))
    s_ok = ok_scale
    if isinstance(scale, list):
        for i, s in enumerate(scale):
            if not isinstance(s, dict):
                checks.append(_ck(False, f"scale[{i}] 非对象", "token.scale"))
                s_ok = False
                continue
            for k in ("name", "value"):
                if not str(s.get(k, "")).strip():
                    checks.append(_ck(False, f"scale[{i}] 缺 {k}",
                                      f"token.scale.{k}"))
                    s_ok = False

    ok = bool(primary) and bool(secondary) and s_ok
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    scale_count=len(scale) if isinstance(scale, list) else 0)
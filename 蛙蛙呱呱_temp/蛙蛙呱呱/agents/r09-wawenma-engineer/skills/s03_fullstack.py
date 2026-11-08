# -*- coding: utf-8 -*-
"""s03 前端后端全栈（fullstack）：feature / auth 两动作。

- feature：功能切片——前端组件 + 后端服务，端到端连线覆盖。
- auth：认证——auth_method 白名单、受保护路由引用。
阈值：thresholds.json → fullstack.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "fullstack"
DESC = "前端后端全栈：UI、状态、服务、认证与端到端功能"

ACTIONS = {
    "feature": "端到端功能切片",
    "auth": "认证与受保护路由",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# feature
# --------------------------------------------------------------------------- #
def feature(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["fullstack"]
    min_components = th["min_components"]
    min_services = th["min_services"]

    components = data.get("frontend") or []
    services = data.get("backend") or []
    wiring = data.get("wiring") or []
    checks: List[Dict[str, Any]] = []

    if len(components) < min_components:
        checks.append(c.ck(False, f"frontend 组件数 {len(components)} < {min_components}", "fullstack:components", "CRITICAL"))
    if len(services) < min_services:
        checks.append(c.ck(False, f"backend 服务数 {len(services)} < {min_services}", "fullstack:services", "CRITICAL"))

    service_names = {str(s.get("name") or "") for s in services}
    component_names = {str(x.get("name") or "") for x in components}
    for i, comp in enumerate(components):
        if not str(comp.get("name") or ""):
            checks.append(c.ck(False, f"frontend[{i}] 缺 name", "fullstack:component_name", "HIGH", **{"index": i}))

    covered_services: set = set()
    for w in wiring:
        comp = str(w.get("component") or "")
        svc = str(w.get("service") or "")
        if comp not in component_names:
            checks.append(c.ck(False, f"wiring 引用了不存在的组件 {comp!r}", "fullstack:wiring_comp", "HIGH", **{"component": comp}))
        if svc not in service_names:
            checks.append(c.ck(False, f"wiring 引用了不存在的服务 {svc!r}", "fullstack:wiring_svc", "HIGH", **{"service": svc}))
        if comp in component_names and svc in service_names:
            covered_services.add(svc)
            checks.append(c.ck(True, f"连线 {comp}→{svc} 有效", "fullstack:wiring", **{"component": comp, "service": svc}))

    uncovered = sorted(service_names - covered_services)
    if uncovered:
        checks.append(c.ck(False, f"后端服务未被任何前端组件覆盖：{uncovered}", "fullstack:e2e_coverage", "HIGH", **{"uncovered": uncovered}))

    e2e_coverage = (len(covered_services) / len(services)) if services else 0.0
    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   component_count=len(components),
                   service_count=len(services),
                   e2e_coverage=round(e2e_coverage, 4),
                   verdict=verdict,
                   next="端到端功能切片完整" if ok else "补齐前端组件或后端服务连线后重新 feature",
                   )
    return out


# --------------------------------------------------------------------------- #
# auth
# --------------------------------------------------------------------------- #
def auth(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["fullstack"]
    auth_methods = th["auth_methods"]

    auth_method = str(data.get("auth_method") or "")
    routes = data.get("routes") or []
    protected = data.get("protected_routes") or []
    checks: List[Dict[str, Any]] = []

    if auth_method not in auth_methods:
        checks.append(c.ck(False, f"auth_method={auth_method!r} 不在白名单 {auth_methods}", "fullstack:auth_method", "CRITICAL"))
    else:
        checks.append(c.ck(True, f"auth_method={auth_method}", "fullstack:auth_method"))

    route_names = {str(r.get("path") or "") for r in routes}
    for p in protected:
        if p not in route_names:
            checks.append(c.ck(False, f"受保护路由 {p!r} 不存在于 routes", "fullstack:protected_route", "HIGH", **{"route": p}))
        else:
            checks.append(c.ck(True, f"受保护路由 {p!r} 有效", "fullstack:protected_route", **{"route": p}))

    if not routes:
        checks.append(c.ck(False, "routes 为空，无认证边界可校验", "fullstack:routes", "CRITICAL"))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   auth_method=auth_method,
                   route_count=len(routes),
                   protected_count=len(protected),
                   verdict=verdict,
                   next="认证边界清晰" if ok else "修复 auth_method/受保护路由引用后重新 auth",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "feature":
        result = feature(data)
    elif args.action == "auth":
        result = auth(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result

# -*- coding: utf-8 -*-
"""s01 技术规格与架构（spec）：spec / arch 两动作。

- spec：技术规格——模块边界（inputs/outputs）、命名唯一、工程约束。
- arch：架构拓扑——topology 枚举、服务命名、边引用无悬空。
阈值：thresholds.json → spec.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "spec"
DESC = "技术规格与架构：模块边界、拓扑、工程约束"

ACTIONS = {
    "spec": "技术规格与模块边界",
    "arch": "架构拓扑与服务连线",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# spec
# --------------------------------------------------------------------------- #
def spec(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["spec"]
    module_required = th["module_required"]

    modules = data.get("modules") or []
    checks: List[Dict[str, Any]] = []

    if not modules:
        checks.append(c.ck(False, "modules 为空，无技术规格可校验", "spec:modules", "CRITICAL"))

    seen_names: set = set()
    for i, m in enumerate(modules):
        name = str(m.get("name") or "")
        missing = [k for k in module_required if k not in m]
        if missing:
            checks.append(c.ck(False, f"modules[{i}] 缺必填字段 {missing}", "spec:module_fields", "HIGH", **{"index": i}))
        if not name:
            checks.append(c.ck(False, f"modules[{i}] name 为空", "spec:module_name", "HIGH", **{"index": i}))
        elif name in seen_names:
            checks.append(c.ck(False, f"模块名重复：{name!r}", "spec:module_dup", "HIGH", **{"name": name}))
        else:
            seen_names.add(name)
            checks.append(c.ck(True, f"模块 {name!r} 字段齐备", "spec:module_fields", **{"name": name}))

    boundary_ok = bool(modules) and all(
        all(k in m for k in module_required) for m in modules
    ) and len(seen_names) == len(modules)

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   module_count=len(modules),
                   boundary_ok=boundary_ok,
                   verdict=verdict,
                   next="技术规格模块边界完整" if ok else "修复模块缺字段/重名后重新 spec",
                   )
    return out


# --------------------------------------------------------------------------- #
# arch
# --------------------------------------------------------------------------- #
def arch(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["spec"]
    topology_types = th["topology_types"]

    topology = str(data.get("topology") or "")
    services = data.get("services") or []
    edges = data.get("edges") or []
    checks: List[Dict[str, Any]] = []

    if topology not in topology_types:
        checks.append(c.ck(False, f"topology={topology!r} 不在枚举 {topology_types}", "spec:topology", "CRITICAL"))
    else:
        checks.append(c.ck(True, f"topology={topology}", "spec:topology"))

    if not services:
        checks.append(c.ck(False, "services 为空，无拓扑可构建", "spec:services", "CRITICAL"))

    service_names = {str(s.get("name") or "") for s in services}
    for i, s in enumerate(services):
        if not str(s.get("name") or ""):
            checks.append(c.ck(False, f"services[{i}] 缺 name", "spec:service_name", "HIGH", **{"index": i}))

    dangling_edges: List[Dict[str, str]] = []
    for e in edges:
        src = str(e.get("from") or "")
        dst = str(e.get("to") or "")
        bad = []
        if src not in service_names:
            bad.append("from")
        if dst not in service_names:
            bad.append("to")
        if bad:
            dangling_edges.append({"from": src, "to": dst})
            checks.append(c.ck(False, f"边 {src}→{dst} 引用了不存在的服务（{','.join(bad)}）", "spec:dangling_edge", "HIGH", **{"from": src, "to": dst}))
        else:
            checks.append(c.ck(True, f"边 {src}→{dst} 有效", "spec:edge", **{"from": src, "to": dst}))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   service_count=len(services),
                   topology=topology,
                   edge_count=len(edges),
                   dangling_edges=dangling_edges,
                   verdict=verdict,
                   next="架构拓扑连线完整" if ok else "修复拓扑枚举/悬空边后重新 arch",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "spec":
        result = spec(data)
    elif args.action == "arch":
        result = arch(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result

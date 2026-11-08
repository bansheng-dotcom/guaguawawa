# -*- coding: utf-8 -*-
"""s08 特殊技术载体（special）：mcp / godot 两动作。

- mcp：MCP 工具服务——transport 枚举、工具命名、manifest 一致性。
- godot：Godot 可加载脚本——project_config、场景、脚本引用。
阈值：thresholds.json → special.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "special"
DESC = "特殊技术载体：Godot、MCP 与工程 Agent 工作流"

ACTIONS = {
    "mcp": "MCP 工具服务",
    "godot": "Godot 可加载脚本",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# mcp
# --------------------------------------------------------------------------- #
def mcp(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["special"]
    mcp_transports = th["mcp_transports"]

    transport = str(data.get("transport") or "")
    tools = data.get("tools") or []
    manifest = data.get("manifest") or {}
    checks: List[Dict[str, Any]] = []

    if transport not in mcp_transports:
        checks.append(c.ck(False, f"transport={transport!r} 不在枚举 {mcp_transports}", "special:transport", "CRITICAL"))
    else:
        checks.append(c.ck(True, f"transport={transport}", "special:transport"))

    if not tools:
        checks.append(c.ck(False, "tools 为空，无 MCP 工具可校验", "special:tools", "CRITICAL"))

    tool_names = {str(t.get("name") or "") for t in tools}
    for i, t in enumerate(tools):
        name = str(t.get("name") or "")
        if not name:
            checks.append(c.ck(False, f"tools[{i}] 缺 name", "special:tool_name", "HIGH", **{"index": i}))

    declared = {str(x) for x in (manifest.get("tools") or [])}
    if declared and declared != tool_names:
        missing = sorted(tool_names - declared)
        extra = sorted(declared - tool_names)
        checks.append(c.ck(False, f"manifest 与 tools 不一致（缺 {missing}，多 {extra}）", "special:manifest", "HIGH"))
    else:
        checks.append(c.ck(True, "manifest 与 tools 一致", "special:manifest"))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   transport=transport,
                   tool_count=len(tools),
                   verdict=verdict,
                   next="MCP 工具服务合规" if ok else "修复 transport/工具命名/manifest 后重新 mcp",
                   )
    return out


# --------------------------------------------------------------------------- #
# godot
# --------------------------------------------------------------------------- #
def godot(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["special"]

    project_config = data.get("project_config") or {}
    scenes = data.get("scenes") or []
    scripts = data.get("scripts") or []
    checks: List[Dict[str, Any]] = []

    if not project_config:
        checks.append(c.ck(False, "project_config 为空（缺 project.godot）", "special:project_config", "CRITICAL"))
    else:
        checks.append(c.ck(True, "project_config 在", "special:project_config"))

    if not scenes:
        checks.append(c.ck(False, "scenes 为空，无可加载场景", "special:scenes", "CRITICAL"))

    script_paths = {str(s.get("path") or "") for s in scripts}
    for i, sc in enumerate(scenes):
        path = str(sc.get("path") or "")
        attached = str(sc.get("script") or "")
        if not path:
            checks.append(c.ck(False, f"scenes[{i}] 缺 path", "special:scene_path", "HIGH", **{"index": i}))
        if attached and attached not in script_paths:
            checks.append(c.ck(False, f"场景 {path!r} 挂载的脚本 {attached!r} 不存在", "special:scene_script", "HIGH", **{"scene": path}))
        else:
            checks.append(c.ck(True, f"场景 {path!r} 脚本有效", "special:scene_script", **{"scene": path}))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   scene_count=len(scenes),
                   script_count=len(scripts),
                   verdict=verdict,
                   next="Godot 项目脚本引用完整" if ok else "修复场景/脚本引用后重新 godot",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "mcp":
        result = mcp(data)
    elif args.action == "godot":
        result = godot(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result

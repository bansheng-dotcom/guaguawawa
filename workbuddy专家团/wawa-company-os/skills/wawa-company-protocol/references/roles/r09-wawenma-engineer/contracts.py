# -*- coding: utf-8 -*-
"""R09 技能契约登记表：8 技能 × 2 动作 = 16 契约。

- 输入 schema：validate_input(skill, action, data)，缺必填字段即 fail。
- 输出 schema：validate_output(skill, action, result)，供 verify_loop 闭环。
- CLI：`python agent.py contract validate --skill S --action A --output result.json`。
口径：所有输出必须有 ok:boolean 与 checks:array（对齐 r05 _out 模板）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c

# --------------------------------------------------------------------------- #
# 通用构造
# --------------------------------------------------------------------------- #
_REQ = lambda props, required: {"type": "object", "required": required,  # noqa: E731
                               "properties": props}
_ARR = lambda items: {"type": "array", "items": items}                  # noqa: E731
_STR = {"type": "string"}
_STR_NE = {"type": "string", "minLength": 1}
_BOOL = {"type": "boolean"}
_NUM = {"type": "number"}
_INT = {"type": "integer"}


def _out(required: List[str]) -> Dict[str, Any]:
    """输出通用：ok/checks 必填 + 动作专属必填字段。"""
    props: Dict[str, Any] = {"ok": _BOOL, "capability_status": {"type": "string", "enum": ["real", "simulated", "blocked"]}, "capability_evidence": _STR, "checks": _ARR({"type": "object"}),
                             "next": _STR}
    for k in required:
        props[k] = {}
    return {"type": "object", "required": ["ok", "checks"] + required,
            "properties": props}


# --------------------------------------------------------------------------- #
# 共享 item schema
# --------------------------------------------------------------------------- #
_MODULE = _REQ({"name": _STR_NE, "inputs": _ARR(_STR), "outputs": _ARR(_STR)},
               ["name"])
_SERVICE = _REQ({"name": _STR_NE, "dependencies": _ARR(_STR)}, ["name"])
_EDGE = _REQ({"from": _STR_NE, "to": _STR_NE}, ["from", "to"])
_COLUMN = _REQ({"name": _STR_NE, "type": _STR}, ["name"])
_TABLE = _REQ({"name": _STR_NE, "columns": _ARR(_COLUMN),
               "primary_key": _STR, "indexes": _ARR(
                   _REQ({"name": _STR_NE, "columns": _ARR(_STR)}, ["name"]))},
              ["name", "columns"])
_INDEX = _REQ({"name": _STR_NE, "columns": _ARR(_STR)}, ["name", "columns"])
_ENDPOINT = _REQ({"method": _STR_NE, "path": _STR_NE,
                  "error_codes": _ARR(_STR)}, ["method", "path"])
_COMPONENT = _REQ({"name": _STR_NE}, ["name"])
_BACKEND = _REQ({"name": _STR_NE}, ["name"])
_WIRING = _REQ({"component": _STR_NE, "service": _STR_NE},
               ["component", "service"])
_ROUTE = _REQ({"path": _STR_NE}, ["path"])
_TARGET = _REQ({"platform": _STR_NE, "status": _STR,
                "state_management": _STR}, ["platform"])
_DIFF = _REQ({"platform": _STR_NE, "note": _STR}, ["platform", "note"])
_SUITE = _REQ({"suite_type": _STR_NE, "passed": _INT, "failed": _INT,
               "skipped": _INT}, ["suite_type"])
_FLOW = _REQ({"name": _STR_NE, "result": _STR}, ["name", "result"])
_HOTSPOT = _REQ({"name": _STR_NE, "before_ms": _NUM, "after_ms": _NUM},
                ["name"])
_REGRESSION = _REQ({"name": _STR_NE, "status": _STR}, ["name", "status"])
_MIGRATION_STEP = _REQ({"operation": _STR_NE}, ["operation"])
_CVE = _REQ({"id": _STR_NE, "severity": _STR}, ["id", "severity"])
_DEPENDENCY = _REQ({"name": _STR_NE, "cves": _ARR(_CVE)}, ["name"])
_TOOL = _REQ({"name": _STR_NE}, ["name"])
_SCENE = _REQ({"path": _STR_NE, "script": _STR}, ["path"])
_SCRIPT = _REQ({"path": _STR_NE}, ["path"])


# --------------------------------------------------------------------------- #
# 各技能契约
# --------------------------------------------------------------------------- #
CONTRACTS: Dict[str, Dict[str, Any]] = {
    "spec": {
        "desc": "技术规格与架构",
        "input": {
            "spec": _REQ({"modules": _ARR(_MODULE)}, ["modules"]),
            "arch": _REQ({"topology": _STR_NE, "services": _ARR(_SERVICE),
                          "edges": _ARR(_EDGE)},
                         ["topology", "services", "edges"]),
        },
        "output": {
            "spec": _out(["module_count", "boundary_ok", "verdict"]),
            "arch": _out(["service_count", "topology", "edge_count",
                          "dangling_edges", "verdict"]),
        },
    },
    "data_api": {
        "desc": "数据库与 API",
        "input": {
            "schema": _REQ({"tables": _ARR(_TABLE)}, ["tables"]),
            "api": _REQ({"endpoints": _ARR(_ENDPOINT)}, ["endpoints"]),
        },
        "output": {
            "schema": _out(["table_count", "column_count", "verdict"]),
            "api": _out(["endpoint_count", "error_codes_total", "verdict"]),
        },
    },
    "fullstack": {
        "desc": "前端后端全栈",
        "input": {
            "feature": _REQ({"frontend": _ARR(_COMPONENT),
                             "backend": _ARR(_BACKEND),
                             "wiring": _ARR(_WIRING)},
                            ["frontend", "backend", "wiring"]),
            "auth": _REQ({"auth_method": _STR_NE, "routes": _ARR(_ROUTE),
                          "protected_routes": _ARR(_STR)},
                         ["auth_method", "routes", "protected_routes"]),
        },
        "output": {
            "feature": _out(["component_count", "service_count",
                             "e2e_coverage", "verdict"]),
            "auth": _out(["auth_method", "route_count", "protected_count",
                          "verdict"]),
        },
    },
    "crossplatform": {
        "desc": "跨端生产工程",
        "input": {
            "build": _REQ({"targets": _ARR(_TARGET)}, ["targets"]),
            "platform": _REQ({"targets": _ARR(_TARGET), "diffs": _ARR(_DIFF)},
                             ["targets", "diffs"]),
        },
        "output": {
            "build": _out(["target_count", "skipped", "verdict"]),
            "platform": _out(["target_count", "state_management",
                              "diff_count", "verdict"]),
        },
    },
    "testing": {
        "desc": "测试与浏览器验证",
        "input": {
            "suites": _REQ({"suites": _ARR(_SUITE), "coverage": _NUM},
                           ["suites", "coverage"]),
            "browser": _REQ({"flows": _ARR(_FLOW), "playwright_trace": _STR},
                            ["flows", "playwright_trace"]),
        },
        "output": {
            "suites": _out(["suite_count", "skipped", "coverage", "verdict"]),
            "browser": _out(["flow_count", "passed", "flaky", "failed",
                             "playwright_trace", "verdict"]),
        },
    },
    "debug": {
        "desc": "调试性能重构",
        "input": {
            "debug": _REQ({"symptom": _STR_NE, "repro_steps": _ARR(_STR),
                           "root_cause": _STR_NE, "fix": _STR_NE},
                          ["symptom", "repro_steps", "root_cause", "fix"]),
            "refactor": _REQ({"hotspots": _ARR(_HOTSPOT),
                              "regression_tests": _ARR(_REGRESSION)},
                             ["hotspots", "regression_tests"]),
        },
        "output": {
            "debug": _out(["symptom", "repro_step_count", "root_cause",
                           "verdict"]),
            "refactor": _out(["hotspot_count", "regression_count", "verdict"]),
        },
    },
    "ops": {
        "desc": "迁移 CI/CD 安全",
        "input": {
            "migration": _REQ({"steps": _ARR(_MIGRATION_STEP),
                               "rollback_plan": _ARR(_STR),
                               "authorization": _BOOL},
                              ["steps", "rollback_plan", "authorization"]),
            "security": _REQ({"dependencies": _ARR(_DEPENDENCY),
                              "leaked_keys": _ARR(_STR)},
                             ["dependencies", "leaked_keys"]),
        },
        "output": {
            "migration": _out(["step_count", "irreversible_found",
                               "rollback_steps", "verdict"]),
            "security": _out(["dependency_count", "cve_counts",
                              "leaked_key_count", "verdict"]),
        },
    },
    "special": {
        "desc": "特殊技术载体",
        "input": {
            "mcp": _REQ({"transport": _STR_NE, "tools": _ARR(_TOOL),
                         "manifest": {"type": "object"}},
                        ["transport", "tools", "manifest"]),
            "godot": _REQ({"project_config": {"type": "object"},
                           "scenes": _ARR(_SCENE), "scripts": _ARR(_SCRIPT)},
                          ["project_config", "scenes", "scripts"]),
        },
        "output": {
            "mcp": _out(["transport", "tool_count", "verdict"]),
            "godot": _out(["scene_count", "script_count", "verdict"]),
        },
    },
}


def skill_names() -> List[str]:
    return list(CONTRACTS.keys())


def actions(skill: str) -> List[str]:
    return list(CONTRACTS[skill]["output"].keys())


def input_schema(skill: str, action: str) -> Dict[str, Any]:
    return CONTRACTS[skill]["input"][action]


def output_schema(skill: str, action: str) -> Dict[str, Any]:
    return CONTRACTS[skill]["output"][action]


def validate_input(skill: str, action: str, data: Any) -> Dict[str, Any]:
    if skill not in CONTRACTS or action not in CONTRACTS[skill]["input"]:
        return {"ok": False, "errors": [f"未登记的契约：{skill}/{action}"]}
    errs = c.validate_schema(data, input_schema(skill, action))
    return {"ok": not errs, "errors": errs}


def validate_output(skill: str, action: str, result: Any) -> Dict[str, Any]:
    if skill not in CONTRACTS or action not in CONTRACTS[skill]["output"]:
        return {"ok": False, "errors": [f"未登记的契约：{skill}/{action}"]}
    errs = c.validate_schema(result, output_schema(skill, action))
    return {"ok": not errs, "errors": errs}


# --------------------------------------------------------------------------- #
# CLI（python contracts.py validate --skill S --action A --output result.json）
# --------------------------------------------------------------------------- #
def _cli() -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="R09 技能契约校验器")
    sub = ap.add_subparsers(dest="cmd", required=True)
    vp = sub.add_parser("validate", help="校验一份输出 result.json 是否符合契约")
    vp.add_argument("--skill", required=True, choices=skill_names())
    vp.add_argument("--action", required=True)
    vp.add_argument("--output", required=True, help="待校验的 result.json 路径")
    ip = sub.add_parser("list", help="列出全部登记的 skill/action")
    args = ap.parse_args()
    if args.cmd == "list":
        rows = [(s, a) for s in skill_names() for a in actions(s)]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    data = json.load(open(args.output, encoding="utf-8"))
    v = validate_output(args.skill, args.action, data)
    print(json.dumps(v, ensure_ascii=False, indent=2))
    return 0 if v["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())

# -*- coding: utf-8 -*-
"""R17 技能契约登记表：8 技能 × 16 动作契约。

- 输入 schema：validate_input(skill, action, data)，缺必填字段即 fail。
- 输出 schema：validate_output(skill, action, result)，供 verify_loop 闭环。
- CLI：`python agent.py contract validate --skill S --action A --output result.json`。
口径：所有输出必须有 ok:boolean 与 checks:array（对齐 r05..r16 模板）。
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
_BOOL = {"type": "boolean"}
_NUM = {"type": "number"}
_ID = {"type": ["string", "integer"]}


def _out(required: List[str]) -> Dict[str, Any]:
    """输出通用：ok/checks 必填 + 动作专属必填字段。"""
    props: Dict[str, Any] = {"ok": _BOOL, "checks": _ARR({"type": "object"}),
                             "next": _STR,
                             "verdict": {"type": "string",
                                         "enum": ["PASS", "FAIL"]}}
    for k in required:
        props[k] = {}
    return {"type": "object", "required": ["ok", "checks"] + required,
            "properties": props}


# --------------------------------------------------------------------------- #
# 各技能契约
# --------------------------------------------------------------------------- #
CONTRACTS: Dict[str, Dict[str, Any]] = {
    "integration": {
        "desc": "SaaS/API 集成：workflow/credential",
        "input": {
            "workflow": _REQ({
                "name": _STR,
                "nodes": _ARR(_REQ({"name": _STR, "type": _STR},
                                   ["name", "type"])),
                "connections": {"type": "object"},
            }, ["nodes"]),
            "credential": _REQ({
                "credentials": _ARR(_REQ({"name": _STR, "credential_type": _STR},
                                         ["name", "credential_type"])),
            }, ["credentials"]),
        },
        "output": {
            "workflow": _out(["node_count", "trigger_count", "dangling_edges"]),
            "credential": _out(["credential_count", "unresolved_count"]),
        },
    },
    "webhook": {
        "desc": "Webhook 与事件处理：webhook/event",
        "input": {
            "webhook": _REQ({"path": _STR, "method": _STR,
                             "handlers": _ARR({"type": "object"})},
                            ["path", "handlers"]),
            "event": _REQ({"events": _ARR(_REQ({"type": _STR, "entity_id": _ID},
                                              ["type", "entity_id"]))},
                          ["events"]),
        },
        "output": {
            "webhook": _out(["webhook_count", "path", "method"]),
            "event": _out(["event_count", "route_count"]),
        },
    },
    "mapping": {
        "desc": "字段与身份映射：mapping/table",
        "input": {
            "mapping": _REQ({
                "mappings": _ARR(_REQ({"source_field": _STR, "target_field": _STR,
                                       "target_type": _STR},
                                      ["source_field", "target_field",
                                       "target_type"])),
                "primary_key": {"type": "object"},
            }, ["mappings"]),
            "table": _REQ({
                "table_name": _STR,
                "columns": _ARR(_REQ({"name": _STR, "type": _STR},
                                     ["name", "type"])),
            }, ["table_name", "columns"]),
        },
        "output": {
            "mapping": _out(["mapping_count"]),
            "table": _out(["column_count", "table_name"]),
        },
    },
    "schedule": {
        "desc": "定时与批处理：schedule/batch",
        "input": {
            "schedule": _REQ({"schedule_type": _STR, "timezone": _STR},
                             ["schedule_type", "timezone"]),
            "batch": _REQ({"batches": _ARR(_REQ({"batch_id": _STR, "item_count": _NUM,
                                                 "status": _STR},
                                                ["batch_id", "item_count",
                                                 "status"]))},
                          ["batches"]),
        },
        "output": {
            "schedule": _out(["schedule_type"]),
            "batch": _out(["batch_count", "failed_count"]),
        },
    },
    "approval": {
        "desc": "人工审批节点：approval/publish",
        "input": {
            "approval": _REQ({
                "approvals": _ARR(_REQ({"action": _STR, "risk_level": _STR},
                                       ["action", "risk_level"])),
            }, ["approvals"]),
            "publish": _REQ({"workflow_name": _STR}, ["workflow_name"]),
        },
        "output": {
            "approval": _out(["approval_count", "high_risk_count"]),
            "publish": _out(["publish_ready"]),
        },
    },
    "retry": {
        "desc": "失败处理与重试：retry/errorflow",
        "input": {
            "retry": _REQ({"policy": {"type": "object"}}, ["policy"]),
            "errorflow": _REQ({"target_workflow_id": _ID},
                              ["target_workflow_id"]),
        },
        "output": {
            "retry": _out(["retry_count", "idempotency_declared"]),
            "errorflow": _out(["errorflow_count"]),
        },
    },
    "aiworkflow": {
        "desc": "AI 工作流接入：aiagent/model",
        "input": {
            "aiagent": _REQ({
                "ai_nodes": _ARR(_REQ({"name": _STR, "type": _STR},
                                      ["name", "type"])),
            }, ["ai_nodes"]),
            "model": _REQ({"anchor": _STR, "model": _STR}, ["anchor", "model"]),
        },
        "output": {
            "aiagent": _out(["ai_count"]),
            "model": _out(["workflow_count"]),
        },
    },
    "audit": {
        "desc": "自动化审计：audit/runlog",
        "input": {
            "audit": _REQ({"records": _ARR({"type": "object"})}, ["records"]),
            "runlog": _REQ({"executions": _ARR({"type": "object"})}, ["executions"]),
        },
        "output": {
            "audit": _out(["audit_count"]),
            "runlog": _out(["execution_count", "failed_count", "success_rate"]),
        },
    },
}


def skill_names() -> List[str]:
    return list(CONTRACTS.keys())


def get(skill: str) -> Dict[str, Any]:
    return CONTRACTS.get(skill, {})


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
# CLI
# --------------------------------------------------------------------------- #
def _cli() -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="R17 技能契约校验器")
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

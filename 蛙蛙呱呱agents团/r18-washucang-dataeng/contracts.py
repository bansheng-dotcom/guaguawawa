# -*- coding: utf-8 -*-
"""R18 技能契约登记表：7 技能 × 14 动作契约。

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
# 主键类字段：DB 自增主键是 int，API 序列化后可能是 str，两者都合法。
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
    "profile": {
        "desc": "数据画像：缺失/基数/PSI",
        "input": {},
        "output": {"profile": _out(["profile"])},
    },
    "elt": {
        "desc": "数据连接与 ELT：connection/sync",
        "input": {
            "connection": _REQ({"connection_id": _STR, "source_connector": _STR,
                                "destination_connector": _STR},
                               ["connection_id", "source_connector",
                                "destination_connector"]),
            "sync": _REQ({"connection_id": _STR, "sync_mode": _STR,
                          "streams": _ARR({"type": "object"})},
                         ["connection_id", "sync_mode", "streams"]),
        },
        "output": {
            "connection": _out(["connection_id", "source_connector",
                                "destination_connector"]),
            "sync": _out(["connection_id", "stream_count", "mode"]),
        },
    },
    "transform": {
        "desc": "数仓转换：model/test",
        "input": {
            "model": _REQ({"model_name": _STR, "materialized": _STR,
                           "depends_on": _ARR({"type": "string"})},
                          ["model_name", "materialized"]),
            "test": _REQ({"tests": _ARR({"type": "object"})}, ["tests"]),
        },
        "output": {
            "model": _out(["model_name", "mode", "dep_count"]),
            "test": _out(["test_count"]),
        },
    },
    "pipeline": {
        "desc": "管道调度与编排：dag/run",
        "input": {
            "dag": _REQ({"dag_id": _STR, "tasks": _ARR({"type": "string"}),
                         "edges": _ARR({"type": "array"})},
                        ["dag_id", "tasks"]),
            "run": _REQ({"dag_id": _STR, "tasks": _ARR({"type": "object"})},
                        ["dag_id", "tasks"]),
        },
        "output": {
            "dag": _out(["dag_id", "task_count", "edge_count"]),
            "run": _out(["dag_id", "task_count", "failed_count"]),
        },
    },
    "quality": {
        "desc": "数据质量门禁：check/fresh",
        "input": {
            "check": _REQ({"table": _STR, "row_count": _NUM,
                           "null_ratio": _NUM, "dup_ratio": _NUM},
                          ["table", "row_count"]),
            "fresh": _REQ({"table": _STR, "age_hours": _NUM},
                          ["table", "age_hours"]),
        },
        "output": {
            "check": _out(["table", "check_count", "row_count"]),
            "fresh": _out(["table", "age_hours", "max_age_hours"]),
        },
    },
    "incremental": {
        "desc": "批流与增量边界：strategy/backfill",
        "input": {
            "strategy": _REQ({"stream": _STR, "mode": _STR},
                             ["stream", "mode"]),
            "backfill": _REQ({"start": _STR, "end": _STR, "authorized": _BOOL},
                             ["start", "end"]),
        },
        "output": {
            "strategy": _out(["stream", "mode"]),
            "backfill": _out(["operation", "authorized"]),
        },
    },
    "catalog": {
        "desc": "数据目录与口径接口：entry/lineage",
        "input": {
            "entry": _REQ({"table": _STR, "fields": _ARR({"type": "object"})},
                          ["table", "fields"]),
            "lineage": _REQ({"tables": _ARR({"type": "string"}),
                             "edges": _ARR({"type": "array"})},
                            ["tables"]),
        },
        "output": {
            "entry": _out(["table", "field_count"]),
            "lineage": _out(["table_count", "edge_count"]),
        },
    },
    "ops": {
        "desc": "人工审批与运维接口：request/alert",
        "input": {
            "request": _REQ({"operation": _STR, "authorization": _STR},
                            ["operation", "authorization"]),
            "alert": _REQ({"rules": _ARR({"type": "object"})}, ["rules"]),
        },
        "output": {
            "request": _out(["operation", "authorized"]),
            "alert": _out(["alert_count"]),
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
    ap = argparse.ArgumentParser(description="R18 技能契约校验器")
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

# -*- coding: utf-8 -*-
"""R19 技能契约登记表：7 技能 × 14 动作契约。

- 输入 schema：validate_input(skill, action, data)，缺必填字段即 fail。
- 输出 schema：validate_output(skill, action, result)，供 verify_loop 闭环。
- CLI：`python agent.py contract validate --skill S --action A --output result.json`。
口径：所有输出必须有 ok:boolean 与 checks:array（对齐 r01..r18 模板）。
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
    "eval-ci": {
        "desc": "评测 Wilson CI",
        "input": {},
        "output": {"eval-ci": _out(["eval_ci"])},
    },
    "tracking": {
        "desc": "实验与运行追踪：experiment/run",
        "input": {
            "experiment": _REQ({"experiment_id": _ID, "name": _STR,
                                "use_case": _STR, "experiment_kind": _STR},
                               ["experiment_id", "name", "use_case",
                                "experiment_kind"]),
            "run": _REQ({"run_id": _ID, "experiment_id": _ID,
                         "metrics": {"type": "object"}, "params": {"type": "object"}},
                        ["run_id", "experiment_id"]),
        },
        "output": {
            "experiment": _out(["experiment_id", "use_case", "experiment_kind"]),
            "run": _out(["run_id", "metric_count", "param_count"]),
        },
    },
    "registry": {
        "desc": "模型注册与版本：register/version",
        "input": {
            "register": _REQ({"model_name": _STR, "version": _STR, "stage": _STR,
                              "source": _STR},
                             ["model_name", "version", "stage", "source"]),
            "version": _REQ({"model_name": _STR,
                             "versions": _ARR({"type": "object"})},
                            ["model_name", "versions"]),
        },
        "output": {
            "register": _out(["model_name", "version", "stage"]),
            "version": _out(["model_name", "version_count"]),
        },
    },
    "evaluation": {
        "desc": "评估数据集与评分器：dataset/scorer",
        "input": {
            "dataset": _REQ({"dataset_id": _ID, "records": _ARR({})},
                            ["dataset_id", "records"]),
            "scorer": _REQ({"scorer_name": _STR, "scorer_type": _STR,
                            "feedback_source": _STR},
                           ["scorer_name", "scorer_type"]),
        },
        "output": {
            "dataset": _out(["dataset_id", "record_count"]),
            "scorer": _out(["scorer_name", "scorer_type", "feedback_source"]),
        },
    },
    "trace": {
        "desc": "Agent Trace 与调试：analyze/retrieval",
        "input": {
            "analyze": _REQ({"trace_id": _ID, "state": _STR, "spans": _ARR({})},
                            ["trace_id", "state", "spans"]),
            "retrieval": _REQ({"max_results": {"type": "integer"}},
                              ["max_results"]),
        },
        "output": {
            "analyze": _out(["trace_id", "state", "span_count"]),
            "retrieval": _out(["trace_count"]),
        },
    },
    "release": {
        "desc": "回归与发布候选：regression/candidate",
        "input": {
            "regression": _REQ({"candidate_id": _ID, "diagnosis_layer": _STR,
                                "old_version": _STR, "new_version": _STR},
                               ["candidate_id", "diagnosis_layer"]),
            "candidate": _REQ({"candidate_id": _ID, "verdict": _STR,
                               "evidence": _ARR({})},
                              ["candidate_id", "verdict", "evidence"]),
        },
        "output": {
            "regression": _out(["candidate_id", "diagnosis_layer", "check_count"]),
            "candidate": _out(["candidate_id", "verdict"]),
        },
    },
    "monitor": {
        "desc": "模型监控接口：metrics/drift",
        "input": {
            "metrics": _REQ({"metric_name": _STR, "view": _STR,
                             "aggregation": _STR},
                            ["metric_name", "view", "aggregation"]),
            "drift": _REQ({"metric": _STR, "threshold": _STR},
                          ["metric", "threshold"]),
        },
        "output": {
            "metrics": _out(["metric_name", "view", "aggregation", "metric_count"]),
            "drift": _out(["metric", "alert_count"]),
        },
    },
    "modelcard": {
        "desc": "模型卡与资产证据：card/asset",
        "input": {
            "card": _REQ({"model_name": _STR, "intended_use": _STR,
                          "limitations": _STR, "risk_tier": _STR,
                          "license": _STR},
                         ["model_name", "intended_use", "limitations",
                          "risk_tier", "license"]),
            "asset": _REQ({"assets": _ARR({"type": "object"})}, ["assets"]),
        },
        "output": {
            "card": _out(["model_name", "risk_tier", "license_type"]),
            "asset": _out(["asset_count"]),
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
    ap = argparse.ArgumentParser(description="R19 技能契约校验器")
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

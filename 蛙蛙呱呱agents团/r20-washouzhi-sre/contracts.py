# -*- coding: utf-8 -*-
"""R20 技能契约登记表：7 技能 × 14 动作契约。

- 输入 schema：validate_input(skill, action, data)，缺必填字段即 fail。
- 输出 schema：validate_output(skill, action, result)，供 verify_loop 闭环。
- CLI：`python agent.py contract validate --skill S --action A --output result.json`。
口径：所有输出必须有 ok:boolean 与 checks:array（对齐 r05..r18 模板）。
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
    "slo": {
        "desc": "SLO 错误预算：允许/已用/燃尽",
        "input": {},
        "output": {"slo": _out(["slo"])},
    },
    "monitor": {
        "desc": "可用性监控：monitor/uptime",
        "input": {
            "monitor": _REQ({"monitor_id": _STR, "type": _STR, "target": _STR},
                            ["monitor_id", "type", "target"]),
            "uptime": _REQ({"monitor_id": _STR, "checks_total": _NUM,
                            "up_count": _NUM},
                           ["monitor_id", "checks_total", "up_count"]),
        },
        "output": {
            "monitor": _out(["monitor_id", "monitor_count", "monitor_type"]),
            "uptime": _out(["monitor_id", "uptime_ratio"]),
        },
    },
    "alert": {
        "desc": "告警与升级：alert/escalation",
        "input": {
            "alert": _REQ({"rules": _ARR({"type": "object"})}, ["rules"]),
            "escalation": _REQ({"chain": _ARR({"type": "object"})}, ["chain"]),
        },
        "output": {
            "alert": _out(["alert_count"]),
            "escalation": _out(["escalation_count"]),
        },
    },
    "statuspage": {
        "desc": "状态页与事件沟通：statuspage/incident",
        "input": {
            "statuspage": _REQ({"page_id": _STR, "components": _ARR({"type": "object"})},
                               ["page_id", "components"]),
            "incident": _REQ({"incident_id": _STR, "timeline": _ARR({"type": "object"})},
                             ["incident_id", "timeline"]),
        },
        "output": {
            "statuspage": _out(["component_id", "component_count"]),
            "incident": _out(["incident_id", "timeline_count"]),
        },
    },
    "backup": {
        "desc": "加密增量备份：backup/snapshot",
        "input": {
            "backup": _REQ({"repo": _STR, "encrypted": _BOOL}, ["repo", "encrypted"]),
            "snapshot": _REQ({"repo": _STR, "snapshots": _ARR({"type": "object"})},
                             ["repo", "snapshots"]),
        },
        "output": {
            "backup": _out(["repo", "encrypted"]),
            "snapshot": _out(["repo", "snapshot_count"]),
        },
    },
    "restore": {
        "desc": "恢复演练：restore/drill",
        "input": {
            "restore": _REQ({"restore_id": _STR, "target": _STR,
                             "snapshot_id": _STR},
                            ["restore_id", "target", "snapshot_id"]),
            "drill": _REQ({"drill_id": _STR, "restored_count": _NUM,
                           "result": _STR},
                          ["drill_id", "restored_count", "result"]),
        },
        "output": {
            "restore": _out(["restore_id", "target"]),
            "drill": _out(["drill_id", "restored_count", "result"]),
        },
    },
    "dr": {
        "desc": "灾难恢复与回滚接口：rpo_rto/rollback",
        "input": {
            "rpo_rto": _REQ({"rpo_hours": _NUM, "rto_hours": _NUM,
                             "recovery_type": _STR},
                            ["rpo_hours", "rto_hours", "recovery_type"]),
            "rollback": _REQ({"rollback_plan": _STR}, ["rollback_plan"]),
        },
        "output": {
            "rpo_rto": _out(["rpo_hours", "rto_hours", "recovery_type"]),
            "rollback": _out(["rollback_plan", "step_count"]),
        },
    },
    "postmortem": {
        "desc": "运行复盘：postmortem/improvement",
        "input": {
            "postmortem": _REQ({"postmortem_id": _STR, "severity": _STR},
                               ["postmortem_id", "severity"]),
            "improvement": _REQ({"actions": _ARR({"type": "object"})}, ["actions"]),
        },
        "output": {
            "postmortem": _out(["postmortem_id", "severity"]),
            "improvement": _out(["action_count"]),
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
    ap = argparse.ArgumentParser(description="R20 技能契约校验器")
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

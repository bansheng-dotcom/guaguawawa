# -*- coding: utf-8 -*-
"""R13 技能契约登记表：8 技能 × 16 动作契约。

- 输入 schema：validate_input(skill, action, data)，缺必填字段即 fail。
- 输出 schema：validate_output(skill, action, result)，供 verify_loop 闭环。
- CLI：`python agent.py contract validate --skill S --action A --output result.json`。
口径：所有输出必须有 ok:boolean 与 checks:array（对齐 r05/r08/r10/r11/r12 模板）。
probe 类动作：探测是「如实降级」而非门禁，输出 ok:true + status(ready/blocked)。
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


def _out(required: List[str]) -> Dict[str, Any]:
    """输出通用：ok/checks 必填 + 动作专属必填字段。"""
    props: Dict[str, Any] = {"ok": _BOOL, "capability_status": {"type": "string", "enum": ["real", "simulated", "blocked"]}, "capability_evidence": _STR, "checks": _ARR({"type": "object"}),
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
    "crm": {
        "desc": "客户与联系人管理：person/company",
        "input": {
            "person": _REQ({
                "person": _REQ({"name": _STR, "lifecycle": _STR,
                                "channels": _ARR({"type": "object"}),
                                "timeline": _ARR({"type": "object"})},
                               ["name", "lifecycle", "channels", "timeline"]),
            }, ["person"]),
            "company": _REQ({
                "company": _REQ({"name": _STR, "people": _ARR({"type": "object"}),
                                 "opportunities": _ARR({"type": "object"})},
                                ["name", "people", "opportunities"]),
            }, ["company"]),
        },
        "output": {
            "person": _out(["record_count", "channel_count", "timeline_count"]),
            "company": _out(["record_count", "person_count", "opp_count"]),
        },
    },
    "pipeline": {
        "desc": "销售管道：pipeline/opp",
        "input": {
            "pipeline": _REQ({
                "opportunities": _ARR(_REQ({
                    "name": _STR, "stage": _STR, "amount": _NUM,
                    "company": _STR, "owner": _STR, "next_step": _STR,
                    "days_in_stage": _NUM,
                }, ["name", "stage", "amount"])),
            }, ["opportunities"]),
            "opp": _REQ({
                "name": _STR, "stage": _STR, "amount": _NUM,
                "close_date": _STR, "owner": _STR,
            }, ["name", "stage", "amount"]),
        },
        "output": {
            "pipeline": _out(["opp_count", "stage_count", "weighted_value",
                              "stale_count", "concentration_hhi"]),
            "opp": _out(["opp_count", "weighted_value"]),
        },
    },
    "activity": {
        "desc": "销售活动与跟进：activity/log",
        "input": {
            "activity": _REQ({
                "activities": _ARR(_REQ({"type": _STR, "what": _STR,
                                         "owner": _STR, "due": _STR},
                                        ["type", "what", "owner", "due"])),
            }, ["activities"]),
            "log": _REQ({"type": _STR, "what": _STR, "owner": _STR,
                         "due": _STR, "summary": _STR},
                        ["type", "what", "owner", "due", "summary"]),
        },
        "output": {
            "activity": _out(["activity_count", "overdue_count"]),
            "log": _out(["activity_count"]),
        },
    },
    "support": {
        "desc": "全渠道客服：inbox/ticket",
        "input": {
            "inbox": _REQ({
                "conversations": _ARR(_REQ({"id": _STR, "channel": _STR,
                                            "status": _STR},
                                           ["id", "channel", "status"])),
            }, ["conversations"]),
            "ticket": _REQ({
                "id": _STR, "channel": _STR, "status": _STR,
                "messages": _ARR({"type": "object"}),
            }, ["id", "channel", "status", "messages"]),
        },
        "output": {
            "inbox": _out(["ticket_count", "channel_count"]),
            "ticket": _out(["ticket_count", "message_count"]),
        },
    },
    "voc": {
        "desc": "客户反馈与 VOC：survey/voc",
        "input": {
            "survey": _REQ({
                "name": _STR, "type": _STR, "status": _STR,
                "questions": _ARR(_REQ({"title": _STR, "type": _STR},
                                       ["title", "type"])),
            }, ["name", "type", "status", "questions"]),
            "voc": _REQ({"responses": _ARR({"type": "object"})}, ["responses"]),
        },
        "output": {
            "survey": _out(["element_count"]),
            "voc": _out(["response_count", "nps_score", "theme_count"]),
        },
    },
    "health": {
        "desc": "客户健康与续约输入：health/risk",
        "input": {
            "health": _REQ({
                "customers": _ARR(_REQ({"name": _STR}, ["name"])),
            }, ["customers"]),
            "risk": _REQ({"name": _STR}, ["name"]),
        },
        "output": {
            "health": _out(["customer_count", "avg_health", "at_risk_count"]),
            "risk": _out(["customer_count", "health_score", "band"]),
        },
    },
    "knowledge": {
        "desc": "服务知识与升级：faq/escalation",
        "input": {
            "faq": _REQ({"faqs": _ARR(_REQ({"question": _STR, "answer": _STR,
                                            "owner": _STR},
                                           ["question", "answer", "owner"]))},
                        ["faqs"]),
            "escalation": _REQ({"symptom": _STR, "repro": _STR, "impact": _STR,
                                "owner_route": _STR, "evidence": {"type": "object"}},
                               ["symptom", "repro", "impact", "owner_route"]),
        },
        "output": {
            "faq": _out(["faq_count"]),
            "escalation": _out(["escalation_count", "route"]),
        },
    },
    "automation": {
        "desc": "客户运营自动化接口：automation/probe",
        "input": {
            "automation": _REQ({
                "trigger": _STR, "condition": _STR, "action": _STR,
                "owner": _STR, "approval_point": _STR, "audit": _STR,
                "fields": _ARR({"type": "object"}),
            }, ["trigger", "condition", "action", "owner",
                "approval_point", "audit"]),
            "probe": {"type": "object"},
        },
        "output": {
            "automation": _out(["automation_count", "field_count", "high_risk"]),
            "probe": _out(["status"]),
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
    ap = argparse.ArgumentParser(description="R13 技能契约校验器")
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

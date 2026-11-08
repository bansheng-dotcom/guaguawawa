# -*- coding: utf-8 -*-
"""R16 技能契约登记表：7 技能 × 16 动作契约。

- 输入 schema：validate_input(skill, action, data)，缺必填字段即 fail。
- 输出 schema：validate_output(skill, action, result)，供 verify_loop 闭环。
- CLI：`python agent.py contract validate --skill S --action A --output result.json`。
口径：所有输出必须有 ok:boolean 与 checks:array（对齐 r05..r14 模板）。
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
    "recruit": {
        "desc": "招聘与入职：opening/applicant/offer",
        "input": {
            "opening": _REQ({"job_title": _STR, "designation": _STR,
                             "status": _STR, "vacancies": _NUM},
                            ["job_title", "designation"]),
            "applicant": _REQ({"applicant_name": _STR, "email_id": _STR,
                               "status": _STR},
                              ["applicant_name", "email_id"]),
            "offer": _REQ({"applicant_name": _STR, "applicant_email": _STR,
                           "offer_date": _STR, "designation": _STR, "status": _STR},
                          ["applicant_name", "applicant_email", "offer_date",
                           "designation"]),
        },
        "output": {
            "opening": _out(["opening_count", "status"]),
            "applicant": _out(["applicant_count", "status"]),
            "offer": _out(["offer_count", "status"]),
        },
    },
    "people": {
        "desc": "人员与合同档案：employee/profile/contract",
        "input": {
            "employee": _REQ({"first_name": _STR, "gender": _STR,
                              "date_of_birth": _STR, "date_of_joining": _STR,
                              "status": _STR},
                             ["first_name", "gender", "date_of_birth",
                              "date_of_joining"]),
            "profile": _REQ({"employee": _STR,
                             "emergency_contacts": _ARR({"type": "object"}),
                             "attachments": _ARR({"type": "object"})},
                            ["employee", "emergency_contacts", "attachments"]),
            "contract": _REQ({"employee": _STR, "start_date": _STR,
                              "end_date": _STR},
                             ["employee", "start_date", "end_date"]),
        },
        "output": {
            "employee": _out(["employee_count", "status"]),
            "profile": _out(["employee_count"]),
            "contract": _out(["contract_count"]),
        },
    },
    "attendance": {
        "desc": "考勤与休假：attendance/leave",
        "input": {
            "attendance": _REQ({"employee": _STR, "attendance_date": _STR,
                                "status": _STR},
                               ["employee", "attendance_date"]),
            "leave": _REQ({"employee": _STR, "leave_type": _STR,
                           "from_date": _STR, "to_date": _STR, "status": _STR},
                          ["employee", "leave_type", "from_date", "to_date"]),
        },
        "output": {
            "attendance": _out(["attendance_count", "status"]),
            "leave": _out(["leave_count", "status"]),
        },
    },
    "performance": {
        "desc": "绩效与目标：appraisal/goal",
        "input": {
            "appraisal": _REQ({"appraisal_cycle": _STR, "total_score": _NUM},
                              ["appraisal_cycle", "total_score"]),
            "goal": _REQ({"status": _STR, "progress": _NUM},
                         ["status", "progress"]),
        },
        "output": {
            "appraisal": _out(["appraisal_count"]),
            "goal": _out(["goal_count", "status", "progress"]),
        },
    },
    "payroll": {
        "desc": "薪酬准备：input/calc",
        "input": {
            "input": _REQ({"employee": _STR, "payroll_frequency": _STR,
                           "components": _ARR({"type": "object"})},
                          ["employee", "payroll_frequency", "components"]),
            "calc": _REQ({"gross_pay": _NUM, "net_pay": _NUM,
                          "components": _ARR({"type": "object"})},
                         ["gross_pay", "net_pay", "components"]),
        },
        "output": {
            "input": _out(["payroll_input_count", "component_count"]),
            "calc": _out(["payroll_input_count", "gross_pay", "net_pay"]),
        },
    },
    "expense": {
        "desc": "费用与福利业务：claim/benefit",
        "input": {
            "claim": _REQ({"employee": _STR, "approval_status": _STR,
                           "status": _STR, "total_claimed_amount": _NUM,
                           "expense_details": _ARR({"type": "object"})},
                          ["employee", "approval_status", "status",
                           "total_claimed_amount", "expense_details"]),
            "benefit": _REQ({"employee": _STR, "payroll_period": _STR,
                             "benefit": _STR, "amount": _NUM},
                            ["employee", "payroll_period", "benefit", "amount"]),
        },
        "output": {
            "claim": _out(["claim_count", "total_amount"]),
            "benefit": _out(["benefit_count", "amount"]),
        },
    },
    "report": {
        "desc": "组织运营报表：headcount/report",
        "input": {
            "headcount": _REQ({"total": _NUM, "groups": _ARR({"type": "object"})},
                              ["total", "groups"]),
            "report": _REQ({"metrics": {"type": "object"}}, ["metrics"]),
        },
        "output": {
            "headcount": _out(["headcount", "group_count"]),
            "report": _out(["metric_count"]),
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
    ap = argparse.ArgumentParser(description="R16 技能契约校验器")
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

# -*- coding: utf-8 -*-
"""R12 技能契约登记表：9 技能 × 18 动作契约。

- 输入 schema：validate_input(skill, action, data)，缺必填字段即 fail。
- 输出 schema：validate_output(skill, action, result)，供 verify_loop 闭环。
- CLI：`python agent.py contract validate --skill S --action A --output result.json`。
口径：所有输出必须有 ok:boolean 与 checks:array（对齐 r05/r08/r10/r11 模板）。
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
    "power": {
        "desc": "实验功效：样本量/MDE",
        "input": {},
        "output": {"power": _out(["power"])},
    },
    "mmm": {
        "desc": "营销组合模型（简化 OLS）：系数/R²/贡献",
        "input": {},
        "output": {"mmm": _out(["mmm"])},
    },
    "ltv-cac": {
        "desc": "LTV/CAC：回收月数与健康判定",
        "input": {},
        "output": {"ltv-cac": _out(["ltv_cac"])},
    },
    "diagnose": {
        "desc": "增长诊断与基线：diagnose/unit",
        "input": {
            "diagnose": _REQ({
                "northstar": _REQ({"primary": _STR, "secondary": _STR},
                                  ["primary", "secondary"]),
                "funnel": _ARR(_STR),
                "pmf_signals": _ARR(_STR),
            }, ["northstar", "funnel", "pmf_signals"]),
            "unit": _REQ({
                "arpa": _NUM, "gross_margin": _NUM, "churn_rate": _NUM,
                "spend": _NUM, "new_customers": _NUM,
            }, ["arpa", "gross_margin", "churn_rate", "spend", "new_customers"]),
        },
        "output": {
            "diagnose": _out(["funnel_count", "signal_count"]),
            "unit": _out(["ltv", "cac", "payback_months", "ltv_cac"]),
        },
    },
    "loops": {
        "desc": "增长循环与自然获客：flywheel/content",
        "input": {
            "flywheel": _REQ({
                "rings": _ARR(_STR),
                "loop": _REQ({
                    "trigger": _STR, "acts_when": _STR, "purpose": _STR,
                    "self_check": _STR, "stop_condition": _STR, "output": _STR,
                }, ["trigger", "acts_when", "purpose", "self_check",
                    "stop_condition", "output"]),
            }, ["rings", "loop"]),
            "content": _REQ({"channels": _ARR(_STR), "flywheel_link": _STR},
                            ["channels", "flywheel_link"]),
        },
        "output": {
            "flywheel": _out(["ring_count"]),
            "content": _out(["channel_count"]),
        },
    },
    "outreach": {
        "desc": "冷启动与外联：coldemail/sequence",
        "input": {
            "coldemail": _REQ({
                "observation": _STR, "problem": _STR, "proof": _STR, "ask": _STR,
                "compliance": _REQ({
                    "secondary_domain": _STR, "opt_out": _STR,
                    "postal_address": _STR,
                }, ["secondary_domain", "opt_out", "postal_address"]),
            }, ["observation", "problem", "proof", "ask", "compliance"]),
            "sequence": _REQ({
                "emails": _ARR(_REQ({"subject": _STR, "body": _STR},
                                    ["subject", "body"])),
            }, ["emails"]),
        },
        "output": {
            "coldemail": _out(["ai_tell_count"]),
            "sequence": _out(["email_count"]),
        },
    },
    "partner": {
        "desc": "红人与合作增长：influencer/comarketing",
        "input": {
            "influencer": _REQ({
                "tier": _STR, "disclosure": _STR, "fraud_signals": _ARR(_STR),
            }, ["tier", "disclosure"]),
            "comarketing": _REQ({
                "partner": _STR, "audience": _STR, "offer": _STR,
                "channel": _STR, "measure": _STR,
            }, ["partner", "audience", "offer", "channel", "measure"]),
        },
        "output": {
            "influencer": _out(["tier", "partner_count"]),
            "comarketing": _out(["element_count"]),
        },
    },
    "launch": {
        "desc": "ASO 与发布：aso/ph",
        "input": {
            "aso": _REQ({
                "store": _STR, "title": _STR, "subtitle": _STR,
                "scores": _REQ({
                    "title": _NUM, "description": _NUM, "visual": _NUM,
                    "rating": _NUM, "metadata": _NUM, "conversion": _NUM,
                }, ["title", "description", "visual", "rating", "metadata",
                    "conversion"]),
            }, ["store", "title", "subtitle", "scores"]),
            "ph": _REQ({
                "tagline": _STR, "maker_comment": _STR, "first_comment": _STR,
                "links": _STR, "stages": _ARR(_STR),
            }, ["tagline", "maker_comment", "first_comment", "links", "stages"]),
        },
        "output": {
            "aso": _out(["store", "score", "grade"]),
            "ph": _out(["stage_count"]),
        },
    },
    "paid": {
        "desc": "付费投放与 CRO：media/cro",
        "input": {
            "media": _REQ({
                "channel": _STR, "audience": _STR, "creative": _STR,
                "budget": _STR, "return": _NUM, "spend": _NUM,
            }, ["channel", "audience", "creative", "budget", "return", "spend"]),
            "cro": _REQ({
                "hypothesis": _STR, "metric": _STR, "significance": _NUM,
            }, ["hypothesis", "metric", "significance"]),
        },
        "output": {
            "media": _out(["channel", "roi"]),
            "cro": _out(["significance"]),
        },
    },
    "retention": {
        "desc": "激活留存推荐：activation/referral",
        "input": {
            "activation": _REQ({
                "aha_moment": _STR, "time_to_value": _STR, "funnel": _STR,
                "churn_warning_days": _NUM, "recall_channels": _ARR(_STR),
            }, ["aha_moment", "time_to_value", "funnel", "churn_warning_days",
                "recall_channels"]),
            "referral": _REQ({
                "invites_per_customer": _NUM, "conversion_rate": _NUM,
                "incentive_type": _STR,
            }, ["invites_per_customer", "conversion_rate", "incentive_type"]),
        },
        "output": {
            "activation": _out(["recall_count"]),
            "referral": _out(["kfactor", "incentive_type"]),
        },
    },
    "revops": {
        "desc": "归因与 RevOps：attribution/roi",
        "input": {
            "attribution": _REQ({
                "model": _STR, "dedup_source": _STR,
                "tracking_fields": _ARR(_STR),
            }, ["model", "dedup_source", "tracking_fields"]),
            "roi": _REQ({
                "arpa": _NUM, "gross_margin": _NUM, "churn_rate": _NUM,
                "spend": _NUM, "new_customers": _NUM,
            }, ["arpa", "gross_margin", "churn_rate", "spend", "new_customers"]),
        },
        "output": {
            "attribution": _out(["model", "field_count"]),
            "roi": _out(["ltv", "cac", "payback_months", "roi", "ltv_cac"]),
        },
    },
    "selfmedia": {
        "desc": "自媒体运营：daily/probe",
        "input": {
            "daily": _REQ({
                "date": _STR, "platform_summary": _ARR({"type": "object"}),
                "conclusion": _STR,
            }, ["date", "platform_summary", "conclusion"]),
            "probe": {"type": "object"},
        },
        "output": {
            "daily": _out(["platform_count"]),
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
    ap = argparse.ArgumentParser(description="R12 技能契约校验器")
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

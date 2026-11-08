# -*- coding: utf-8 -*-
"""R04 技能契约登记表：7 技能 × 每动作 输入/输出 JSON Schema 全登记。

- 输入 schema：validate_input(skill, action, data)，缺必填字段即 fail。
- 输出 schema：validate_output(skill, action, result)，供 verify_loop 闭环。
- CLI：`python agent.py contract validate --skill S --action A --output result.json`。
口径：所有输出必须有 ok:boolean 与 checks:array（对齐 r03/r07 _ok 模板）。
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


def _out(required: List[str]) -> Dict[str, Any]:
    """输出通用：ok/checks 必填 + 动作专属必填字段。"""
    props: Dict[str, Any] = {"ok": _BOOL, "checks": _ARR({"type": "object"}),
                             "next": _STR}
    for k in required:
        props[k] = {}
    return {"type": "object", "required": ["ok", "checks"],
            "properties": props}


# --------------------------------------------------------------------------- #
# 各技能契约
# --------------------------------------------------------------------------- #
_ITEM = _REQ({"path": _STR, "type": _STR, "required": _BOOL}, ["path"])
_ARTIFACT = _REQ({
    "path": _STR, "type": _STR, "content": _STR, "exists": _BOOL,
    "size_bytes": {"type": "integer"}, "references": _ARR(_STR),
    "tested": _ARR(_STR), "entry_point": _BOOL,
}, ["path"])
_GATE = _REQ({"name": _STR, "command": _STR,
              "timeout_s": {"type": "integer", "minimum": 1}}, ["command"])
_CRIT = _REQ({"id": _STR_NE, "description": _STR, "evidence": _STR,
              "severity": _STR, "partial": _BOOL, "issues": _ARR(_STR)}, ["id"])
_CLAIM = _REQ({"id": _STR_NE, "text": _STR, "kind": _STR,
               "evidence_refs": _ARR(_STR)}, ["id", "text"])
_FACT = _REQ({"id": _STR_NE, "claim": _STR, "numbers": _ARR(_STR_NE),
              "source": _STR, "source_type": _STR,
              "key_assertions": _ARR(_STR_NE)}, ["id", "claim"])
_KEEP = _REQ({"id": _STR_NE, "what": _STR, "why_keep": _STR, "evidence": _STR},
             ["id"])
_COMMENT = _REQ({"id": _STR, "kind": _STR, "quote": _STR, "feedback": _STR,
                 "anchor": _REQ({"prefix": _STR, "quote": _STR, "suffix": _STR}, [])},
                ["kind"])
_EDIT = _REQ({"label": _STR, "kind": _STR, "before": _STR, "after": _STR,
              "after_html": _STR, "truncated": _BOOL, "moved_after": _STR,
              "moved_before": _STR}, ["kind"])
_PAGE = _REQ({"file": _STR, "edits_saved": _BOOL, "comments": _ARR(_COMMENT),
              "edits": _ARR(_EDIT)}, [])

CONTRACTS: Dict[str, Dict[str, Any]] = {
    "artifact": {
        "desc": "成品实体核验",
        "input": {
            "inventory": _REQ({"items": _ARR(_ITEM)}, ["items"]),
            "verify": _REQ({"artifacts": _ARR(_ARTIFACT)}, ["artifacts"]),
        },
        "output": {
            "inventory": _out(["items", "item_count", "verdict"]),
            "verify": _out(["level_results", "per_artifact", "verdict", "gaps"]),
        },
    },
    "gate": {
        "desc": "硬门禁复核",
        "input": {
            "run": _REQ({"gates": _ARR(_GATE)}, ["gates"]),
            "audit": {"type": "object"},
        },
        "output": {
            "run": _out(["records", "overall", "pass_count", "fail_count",
                         "skipped_count"]),
            "audit": _out(["findings", "error_count", "warning_count", "score",
                           "tier", "verdict", "evaluated_patterns"]),
        },
    },
    "criteria": {
        "desc": "外置判据审查",
        "input": {
            "review": _REQ({"criteria": _ARR(_CRIT)}, ["criteria"]),
            "delta": _REQ({"criteria": _ARR(_CRIT)}, ["criteria"]),
        },
        "output": {
            "review": _out(["criteria_results", "counts", "verdict"]),
            "delta": _out(["current", "delta", "fixed_count", "new_count",
                           "remaining_count", "verdict"]),
        },
    },
    "quality": {
        "desc": "独立质量评价",
        "input": {
            "critique": _REQ({"claims": _ARR(_CLAIM)}, ["claims"]),
            "converge": _REQ({"findings": {}}, ["findings"]),
        },
        "output": {
            "critique": _out(["claims_checked", "findings", "error_count",
                              "verdict"]),
            "converge": _out(["v1_count", "v2_count", "converged", "verdict"]),
        },
    },
    "facts": {
        "desc": "事实与来源检查",
        "input": {
            "check": _REQ({"facts": _ARR(_FACT)}, ["facts"]),
            "trace": _REQ({"numbers": _ARR(_STR_NE)}, ["numbers"]),
        },
        "output": {
            "check": _out(["dimension_results", "violations", "violation_count",
                           "verdict"]),
            "trace": _out(["traces", "verified_count", "drift_count",
                           "hallucinated_count", "verdict"]),
        },
    },
    "strengths": {
        "desc": "保留优点与复评",
        "input": {
            "mark": _REQ({"keep_list": _ARR(_KEEP)}, ["keep_list"]),
            "recheck": {"type": "object", "required": [],
                        "properties": {"keep_list": _ARR(_KEEP),
                                       "findings": _ARR({"type": "object"})}},
        },
        "output": {
            "mark": _out(["keep_list", "keep_count", "verdict"]),
            "recheck": _out(["downgrades", "untraceable_new_fails",
                             "resurfaced_resolved", "recheck_verdict"]),
        },
    },
    "human": {
        "desc": "人工评审工作流",
        "input": {
            "package": _REQ({
                "artifact": _STR, "review_dimensions": _ARR(_STR),
                "criteria_ref": _STR, "producer": _STR, "reviewer": _STR,
                "deadline": _STR,
            }, ["artifact", "review_dimensions", "criteria_ref", "producer",
                "reviewer", "deadline"]),
            "ingest": _REQ({"status": _STR, "pages": _ARR(_PAGE),
                            "overall_note": _STR,
                            "staged_assets": _ARR({"type": "object"})},
                           ["status", "pages"]),
            "ack": _REQ({"status": _STR,
                         "staged_assets": _ARR(_REQ({"path": _STR, "copied": _BOOL},
                                                    []))},
                        []),
        },
        "output": {
            "package": _out(["review_package", "self_review_blocked",
                             "package_valid"]),
            "ingest": _out(["violations", "applied_plan", "comments_total",
                            "edits_total", "batch_status"]),
            "ack": _out(["staged_assets", "uncopied", "ack_status",
                         "acknowledged"]),
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
    ap = argparse.ArgumentParser(description="R04 技能契约校验器")
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

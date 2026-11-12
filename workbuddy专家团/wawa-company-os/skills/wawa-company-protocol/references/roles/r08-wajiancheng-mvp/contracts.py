# -*- coding: utf-8 -*-
"""R08 技能契约登记表：7 技能 × 2 动作 = 14 契约。

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
_BOOL = {"type": "boolean"}
_NUM = {"type": "number"}


def _out(required: List[str]) -> Dict[str, Any]:
    """输出通用：ok/checks 必填 + 动作专属必填字段；verdict/next 类型校验。"""
    props: Dict[str, Any] = {"ok": _BOOL, "capability_status": {"type": "string", "enum": ["real", "simulated", "blocked"]}, "capability_evidence": _STR, "checks": _ARR({"type": "object"}),
                             "next": _STR,
                             "verdict": {"type": "string",
                                         "enum": ["PASS", "FAIL"]}}
    for k in required:
        props[k] = {}
    return {"type": "object", "required": ["ok", "checks"] + required,
            "properties": props}


# --------------------------------------------------------------------------- #
# 共享 item schema
# --------------------------------------------------------------------------- #
_SLICE = _REQ({"name": _STR, "testable_hypothesis": _STR,
               "success_criterion": _STR},
              ["name", "testable_hypothesis", "success_criterion"])
_FILE = _REQ({"path": _STR, "purpose": _STR}, ["path", "purpose"])
_ENV = _REQ({"name": _STR, "description": _STR}, ["name", "description"])
_FIELD = _REQ({"name": _STR, "label": _STR}, ["name", "label"])
_ROUTE = _REQ({"path": _STR, "page": _STR}, ["path", "page"])
_TEMPLATE = _REQ({"name": _STR, "subject": _STR, "body": _STR},
                 ["name", "subject", "body"])
_FEATURE = _REQ({"name": _STR, "layers": {"type": "object"}}, ["name", "layers"])
_COMPONENT = _REQ({"name": _STR, "platform": _STR, "states": _ARR(_STR)},
                  ["name", "platform", "states"])
_TOKEN_ITEM = _REQ({"name": _STR, "value": _STR}, ["name", "value"])
_TEST_POINT = _REQ({"name": _STR, "expectation": _STR}, ["name", "expectation"])


# --------------------------------------------------------------------------- #
# 各技能契约
# --------------------------------------------------------------------------- #
CONTRACTS: Dict[str, Dict[str, Any]] = {
    "slice": {
        "desc": "产品切片与MVP：slice/mvp",
        "input": {
            "slice": _REQ({"artifact_type": _STR, "slices": _ARR(_SLICE)},
                          ["artifact_type", "slices"]),
            "mvp": _REQ({
                "assumption": _REQ({"risk_type": _STR, "statement": _STR},
                                   ["risk_type", "statement"]),
                "mvp": _REQ({"goal": _STR}, ["goal"]),
                "experiment": _ARR(_REQ({"method": _STR, "metric": _STR},
                                        ["method", "metric"])),
                "criteria": _REQ({"success": _STR, "fail": _STR},
                                 ["success", "fail"]),
                "handoff": _STR,
            }, ["assumption", "mvp", "experiment", "criteria", "handoff"]),
        },
        "output": {
            "slice": _out(["artifact_type", "slice_count"]),
            "mvp": _out(["passed_gates"]),
        },
    },
    "scaffold": {
        "desc": "Spec转仓库：scaffold/spec",
        "input": {
            "scaffold": _REQ({"stack": _STR, "tree": _ARR(_STR),
                              "files": _ARR(_FILE),
                              "run_commands": _ARR(_STR), "auth": _STR,
                              "env_vars": _ARR(_ENV)},
                             ["stack", "tree", "files", "run_commands", "auth"]),
            "spec": _REQ({"trigger": _STR, "stack": _STR, "delivery": _STR,
                          "auth": _STR},
                         ["trigger", "stack", "delivery", "auth"]),
        },
        "output": {
            "scaffold": _out(["file_count", "stack"]),
            "spec": _out(["stack"]),
        },
    },
    "landing": {
        "desc": "落地页与H5：landing/form",
        "input": {
            "landing": _REQ({
                "goal": _STR, "headline": _STR, "subhead": _STR,
                "proof_points": _ARR(_STR), "form": _STR, "button": _STR,
                "faq": _STR, "post_submit": _STR,
                "single_file_index_html": _BOOL, "no_js_library": _BOOL,
                "form_deliverable": _BOOL, "mobile_first": _BOOL,
                "button_single_accent": _BOOL, "max_objection": _STR,
            }, ["goal", "headline", "subhead", "proof_points", "form",
                "button", "faq", "post_submit", "single_file_index_html",
                "no_js_library", "form_deliverable", "mobile_first",
                "button_single_accent", "max_objection"]),
            "form": _REQ({"formspree_endpoint": _STR, "mailto": _STR,
                          "fields": _ARR(_FIELD)}, ["fields"]),
        },
        "output": {
            "landing": _out(["proof_count"]),
            "form": _out(["field_count"]),
        },
    },
    "saas": {
        "desc": "SaaS与邮件脚手架：saas/email",
        "input": {
            "saas": _REQ({"pages": _ARR(_STR), "routes": _ARR(_ROUTE),
                          "auth": _STR, "entry_point": _STR},
                         ["pages", "routes", "auth", "entry_point"]),
            "email": _REQ({"templates": _ARR(_TEMPLATE),
                           "preview_text": _STR, "unsubscribe_link": _STR},
                          ["templates", "preview_text", "unsubscribe_link"]),
        },
        "output": {
            "saas": _out(["page_count"]),
            "email": _out(["template_count"]),
        },
    },
    "prototype": {
        "desc": "跨平台原型：prototype/screen",
        "input": {
            "prototype": _REQ({
                "main": _STR, "app": _STR, "core": _STR,
                "features": _ARR(_FEATURE), "shared_widgets": _ARR(_STR),
                "router": _STR, "platforms": _ARR(_STR),
            }, ["main", "app", "core", "features", "shared_widgets",
                "router", "platforms"]),
            "screen": _REQ({
                "widget_type": _STR, "const_constructor": _BOOL,
                "breakpoints": _REQ({"mobile": _STR, "tablet": _STR,
                                     "desktop": _STR},
                                    ["mobile", "tablet", "desktop"]),
                "form": _REQ({"form_key": _STR, "controller": _STR,
                              "validator": _STR}, []),
            }, ["widget_type", "const_constructor", "breakpoints"]),
        },
        "output": {
            "prototype": _out(["feature_count"]),
            "screen": _out(["widget_type"]),
        },
    },
    "design": {
        "desc": "组件与设计实现：design/token",
        "input": {
            "design": _REQ({
                "tokens": _REQ({"color": _ARR(_TOKEN_ITEM),
                                "typography": _ARR(_TOKEN_ITEM),
                                "spacing": _ARR(_TOKEN_ITEM)},
                               ["color", "typography", "spacing"]),
                "components": _ARR(_COMPONENT),
            }, ["tokens", "components"]),
            "token": _REQ({"primary": _STR, "secondary": _STR,
                           "scale": _ARR(_TOKEN_ITEM)},
                          ["primary", "secondary", "scale"]),
        },
        "output": {
            "design": _out(["token_count", "component_count"]),
            "token": _out(["scale_count"]),
        },
    },
    "qa": {
        "desc": "质量验证与交接：qa/handoff",
        "input": {
            "qa": _REQ({"checks": {"type": "object"},
                        "a11y_items": _ARR(_STR),
                        "test_points": _ARR(_TEST_POINT)},
                       ["checks", "a11y_items", "test_points"]),
            "handoff": _REQ({"artifacts": _ARR(_STR),
                             "run_commands": _ARR(_STR),
                             "acceptance": _ARR(_STR), "owner": _STR},
                            ["artifacts", "run_commands", "acceptance", "owner"]),
        },
        "output": {
            "qa": _out(["check_count"]),
            "handoff": _out(["artifact_count"]),
        },
    },
    "deck": {
        "desc": "单文件 HTML 幻灯片：plan/html",
        "input": {
            "plan": _REQ({"title": _STR,
                          "slides": _ARR(_REQ({"title": _STR, "message": _STR},
                                              ["title", "message"]))},
                         ["title", "slides"]),
            "html": _REQ({"title": _STR,
                          "slides": _ARR(_REQ({"title": _STR, "message": _STR},
                                              ["title", "message"]))},
                         ["title", "slides"]),
        },
        "output": {
            "plan": _out(["slide_count"]),
            "html": _out(["out", "size_bytes"]),
        },
    },
    "htmlreport": {
        "desc": "单文件 HTML 报告：plan/html",
        "input": {
            "plan": _REQ({"title": _STR, "chapters": _ARR({"type": "object"})},
                         ["title", "chapters"]),
            "html": _REQ({"title": _STR, "chapters": _ARR({"type": "object"})},
                         ["title", "chapters"]),
        },
        "output": {
            "plan": _out(["chapter_count"]),
            "html": _out(["out", "size_bytes"]),
        },
    },
    "miniapp": {
        "desc": "小程序工程脚手架：plan/scaffold",
        "input": {
            "plan": _REQ({"name": _STR, "pages": _ARR({"type": "object"})}, ["name", "pages"]),
            "scaffold": _REQ({"name": _STR, "pages": _ARR({"type": "object"})}, ["name", "pages"]),
        },
        "output": {
            "plan": _out(["page_count"]),
            "scaffold": _out(["out", "file_count"]),
        },
    },
    "office": {
        "desc": "Office 交付物：probe/xlsx/docx",
        "input": {
            "probe": _REQ({}, []),
            "xlsx": _REQ({"sheets": _ARR({"type": "object"})}, ["sheets"]),
            "docx": _REQ({"title": _STR, "sections": _ARR({"type": "object"})}, ["title"]),
        },
        "output": {
            "probe": _out(["status"]),
            "xlsx": _out(["out", "size_bytes"]),
            "docx": _out(["out", "size_bytes"]),
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
# CLI（python contracts.py validate --skill S --action A --output result.json）
# --------------------------------------------------------------------------- #
def _cli() -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="R08 技能契约校验器")
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

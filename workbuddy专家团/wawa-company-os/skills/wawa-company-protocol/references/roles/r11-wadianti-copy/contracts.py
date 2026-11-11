# -*- coding: utf-8 -*-
"""R11 技能契约登记表：8 技能 × 16 动作契约。

- 输入 schema：validate_input(skill, action, data)，缺必填字段即 fail。
- 输出 schema：validate_output(skill, action, result)，供 verify_loop 闭环。
- CLI：`python agent.py contract validate --skill S --action A --output result.json`。
口径：所有输出必须有 ok:boolean 与 checks:array（对齐 r05/r08/r10 模板）。
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
    "topic": {
        "desc": "内容策略与选题：brief/plan",
        "input": {
            "brief": _REQ({
                "audience": _STR, "pain_point": _STR, "channel": _STR,
                "differentiator": _STR,
            }, ["audience", "pain_point", "channel", "differentiator"]),
            "plan": _REQ({
                "items": _ARR(_REQ({"topic": _STR, "owner": _STR,
                                    "due": _STR, "status": _STR},
                                   ["topic", "owner", "due", "status"])),
            }, ["items"]),
        },
        "output": {
            "brief": _out(["topic_count"]),
            "plan": _out(["item_count"]),
        },
    },
    "seo": {
        "desc": "SEO/AEO 与搜索发现：keyword/audit",
        "input": {
            "keyword": _REQ({
                "primary": _STR, "longtail": _STR, "intent": _STR,
                "difficulty": _STR, "aeo_opportunity": _STR,
            }, ["primary", "longtail", "intent", "difficulty",
                "aeo_opportunity"]),
            "audit": _REQ({"content": _STR}, ["content"]),
        },
        "output": {
            "keyword": _out(["keyword_count"]),
            "audit": _out(["h2_count", "external_links"]),
        },
    },
    "hook": {
        "desc": "钩子提纲立场：hook/outline",
        "input": {
            "hook": _REQ({"hook_type": _STR, "titles": _ARR(_STR)},
                         ["hook_type", "titles"]),
            "outline": _REQ({
                "outline": _STR,
                "stance": _REQ({"claim": _STR, "audience": _STR,
                                "boundary": _STR},
                               ["claim", "audience", "boundary"]),
            }, ["outline", "stance"]),
        },
        "output": {
            "hook": _out(["title_count"]),
            "outline": _out(["h2_count"]),
        },
    },
    "copy": {
        "desc": "文案与长文：article/script",
        "input": {
            "article": _REQ({"text": _STR}, ["text"]),
            "script": _REQ({"text": _STR}, ["text"]),
        },
        "output": {
            "article": _out(["char_count"]),
            "script": _out(["char_count"]),
        },
    },
    "voice": {
        "desc": "品牌语调与编辑：guide/edit",
        "input": {
            "guide": _REQ({
                "audience": _STR, "tone": _STR, "terms": _ARR(_STR),
                "forbidden": _ARR(_STR), "grammar": _STR,
                "dimensions": _ARR(_STR),
            }, ["audience", "tone", "terms", "forbidden", "grammar"]),
            "edit": _REQ({
                "text": _STR, "forbidden_hits": _ARR(_STR),
                "term_fixes": _ARR({"type": "object"}),
            }, ["text", "forbidden_hits", "term_fixes"]),
        },
        "output": {
            "guide": _out(["dimension_count"]),
            "edit": _out(["forbidden_count", "fix_count"]),
        },
    },
    "pr": {
        "desc": "广告公关新闻稿：ad/press",
        "input": {
            "ad": _REQ({"headline": _STR, "benefit": _STR, "cta": _STR},
                       ["headline", "benefit", "cta"]),
            "press": _REQ({
                "headline": _STR, "dateline": _STR, "lead": _STR,
                "body": _STR, "boilerplate": _STR, "contact": _STR,
            }, ["headline", "dateline", "lead", "body", "boilerplate", "contact"]),
        },
        "output": {
            "ad": _out(["banned_count"]),
            "press": _out(["section_count"]),
        },
    },
    "platform": {
        "desc": "多平台适配：adapt/publish/visual",
        "input": {
            "adapt": _REQ({
                "platform": _STR, "title": _STR, "length_limit": _STR,
                "tone_shift": _STR, "hashtags": _ARR(_STR),
            }, ["platform", "title", "length_limit", "tone_shift", "hashtags"]),
            "publish": _REQ({
                "items": _ARR(_REQ({"platform": _STR, "url": _STR,
                                    "status": _STR, "authorized": _BOOL},
                                   ["platform", "url", "status", "authorized"])),
            }, ["items"]),
            "visual": _REQ({"need": _STR}, ["need"]),
        },
        "output": {
            "adapt": _out(["platform"]),
            "publish": _out(["item_count"]),
            "visual": _out(["prompt", "delegated_to"]),
        },
    },
    "localize": {
        "desc": "持续本地化：term/review/probe",
        "input": {
            "term": _REQ({
                "source": _STR, "target": _STR,
                "glossary": _ARR(_REQ({"source": _STR, "target": _STR},
                                      ["source", "target"])),
            }, ["source", "target", "glossary"]),
            "review": _REQ({
                "term": _STR, "source_lang": _STR, "target_lang": _STR,
                "status": _STR, "reviewer": _STR,
            }, ["term", "source_lang", "target_lang", "status", "reviewer"]),
            "probe": {"type": "object"},
        },
        "output": {
            "term": _out(["glossary_count"]),
            "review": _out(["status"]),
            "probe": _out(["status"]),
        },
    },
    "xhs": {
        "desc": "小红书发布包：note/score/compliance（评分卡+合规扫描）",
        "input": {
            "note": _REQ({"title": _STR, "body": _STR, "cta": _STR,
                          "tags": _ARR(_STR)}, ["title", "body", "tags"]),
            "score": _REQ({"title": _STR, "body": _STR, "cta": _STR,
                           "format_type": _STR}, ["title", "body"]),
            "compliance": _REQ({"title": _STR, "body": _STR}, ["title", "body"]),
        },
        "output": {
            "note": _out(["title_len", "body_len"]),
            "score": _out(["passed", "ces_reference"]),
            "compliance": _out([]),
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
    ap = argparse.ArgumentParser(description="R11 技能契约校验器")
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

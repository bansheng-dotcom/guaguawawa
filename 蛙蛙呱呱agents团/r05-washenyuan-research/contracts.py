# -*- coding: utf-8 -*-
"""R05 技能契约登记表：7 技能 × 2 动作 = 14 契约。

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
    return {"type": "object", "required": ["ok", "checks"] + required,
            "properties": props}


# --------------------------------------------------------------------------- #
# 共享 item schema
# --------------------------------------------------------------------------- #
_SOURCE = _REQ({"id": _STR_NE, "title": _STR, "type": _STR, "url": _STR},
               ["id", "title"])
_CLAIM = _REQ({"id": _STR_NE, "text": _STR, "source_ids": _ARR(_STR)},
              ["id", "text"])
_PLAYER = _REQ({"name": _STR_NE, "role": _STR, "segment": _STR,
                "share": _NUM}, ["name"])
_SEGMENT = _REQ({"name": _STR_NE, "desc": _STR}, ["name"])
_VALUE_CHAIN_STAGE = _REQ({"stage": _STR_NE, "players": _ARR(_STR),
                           "margin_pct": _NUM}, ["stage"])
_SHARE = _REQ({"player": _STR_NE, "share": _NUM}, ["player", "share"])
# matrix 用：竞品名 + features 对照表（feature → yes/no/partial/unknown）
_MATRIX_COMPETITOR = _REQ({"name": _STR_NE, "features": {"type": "object"}},
                           ["name", "features"])
# battlecard 用：单竞品档案（与 s03.battlecard 读取口径一致）
_BATTLECARD_COMPETITOR = _REQ({
    "name": _STR_NE, "positioning": _STR, "strengths": _ARR(_STR),
    "weaknesses": _ARR(_STR), "strategy": _STR, "pricing": _STR,
}, ["name"])
_SCENARIO = _REQ({"name": _STR_NE, "desc": _STR, "probability": _STR,
                  "impact": _STR, "risk_level": _STR, "mitigation": _STR,
                  "early_warning": _STR},
                 ["name", "desc", "probability", "impact"])
_DRIVER = _REQ({"name": _STR_NE, "base_value": _NUM, "low": _NUM, "high": _NUM},
               ["name", "base_value", "low", "high"])
_PESTEL_FACTOR = _REQ({"category": _STR_NE, "factor": _STR, "evidence": _STR,
                       "impact": _STR}, ["category", "factor"])
_RUN = _REQ({"skill": _STR, "action": _STR, "status": _STR,
             "questions_covered": _ARR(_STR)}, ["status"])
_QUESTION = _REQ({"id": _STR_NE, "text": _STR}, ["id", "text"])
_SECTION = _REQ({"title": _STR_NE, "content": _STR, "claims": _ARR(_STR),
                 "sources": _ARR(_STR)}, ["title"])


# --------------------------------------------------------------------------- #
# 各技能契约
# --------------------------------------------------------------------------- #
CONTRACTS: Dict[str, Dict[str, Any]] = {
    "research": {
        "desc": "证据台账与研究报告",
        "input": {
            "ledger": _REQ({"sources": _ARR(_SOURCE), "claims": _ARR(_CLAIM)},
                           ["sources", "claims"]),
            "report": _REQ({"claims": _ARR(_CLAIM), "sources": _ARR(_SOURCE),
                            "sections": _ARR(_SECTION)},
                           ["claims", "sources", "sections"]),
        },
        "output": {
            "ledger": _out(["source_count", "claim_count", "orphan_claims",
                            "coverage_rate", "verdict"]),
            "report": _out(["sections_checked", "citation_coverage",
                            "orphan_claims", "verdict"]),
        },
    },
    "industry": {
        "desc": "行业格局与集中度",
        "input": {
            "landscape": _REQ({"players": _ARR(_PLAYER),
                               "segments": _ARR(_SEGMENT),
                               "value_chain": _ARR(_VALUE_CHAIN_STAGE)},
                              ["players", "segments", "value_chain"]),
            "concentration": _REQ({"shares": _ARR(_SHARE)}, ["shares"]),
        },
        "output": {
            "landscape": _out(["player_count", "segment_count",
                               "value_chain_stages", "profit_structure", "verdict"]),
            "concentration": _out(["hhi", "cr4", "cr8", "market_structure",
                                   "verdict"]),
        },
    },
    "competitor": {
        "desc": "竞品矩阵与战斗卡",
        "input": {
            "matrix": _REQ({"competitors": _ARR(_MATRIX_COMPETITOR),
                            "features": _ARR(_STR_NE),
                            "our_product": _REQ(
                                {"name": _STR, "features": {"type": "object"}},
                                [])},
                           ["competitors", "features", "our_product"]),
            "battlecard": _REQ({"competitor": _BATTLECARD_COMPETITOR,
                                "our_positioning": _STR,
                                "key_differentiators": _ARR(_STR)},
                               ["competitor", "our_positioning"]),
        },
        "output": {
            "matrix": _out(["competitor_count", "feature_count", "gaps",
                            "verdict"]),
            "battlecard": _out(["threat_level", "verdict"]),
        },
    },
    "business": {
        "desc": "商业模式画布与变现",
        "input": {
            "canvas": _REQ({"blocks": {"type": "object"}}, ["blocks"]),
            "monetize": _REQ({"model": _REQ(
                {"type": _STR, "pricing_tiers": _ARR({"type": "object"}),
                 "unit_economics": _REQ({}, [])},
                ["type", "pricing_tiers", "unit_economics"])},
                ["model"]),
        },
        "output": {
            "canvas": _out(["blocks_complete", "fit_gaps", "verdict"]),
            "monetize": _out(["gross_margin", "ltv_cac_ratio", "break_even",
                              "verdict"]),
        },
    },
    "sizing": {
        "desc": "市场规模与敏感性",
        "input": {
            "size": _REQ({
                "top_down": _REQ({"components": _ARR(_REQ(
                    {"name": _STR_NE, "value": _NUM}, ["name", "value"]))},
                    ["components"]),
                "bottom_up": _REQ({"customer_count": _NUM,
                                   "addressable_fraction": _NUM,
                                   "annual_quantity": _NUM,
                                   "price_per_unit": _NUM},
                                  ["customer_count", "addressable_fraction",
                                   "annual_quantity", "price_per_unit"]),
                "scenarios": _ARR(_REQ(
                    {"name": _STR_NE, "serviceable_fraction": _NUM,
                     "obtainable_share": _NUM},
                    ["name", "serviceable_fraction", "obtainable_share"])),
            }, ["top_down", "bottom_up", "scenarios"]),
            "sensitivity": _REQ({"drivers": _ARR(_DRIVER),
                                 "base_value": _NUM},
                                ["drivers", "base_value"]),
        },
        "output": {
            "size": _out(["tam", "tam_top", "tam_bottom", "variance",
                          "by_scenario", "verdict"]),
            "sensitivity": _out(["sensitivity_matrix", "key_drivers", "verdict"]),
        },
    },
    "scenario": {
        "desc": "PESTEL 宏观与失效推演",
        "input": {
            "pestel": _REQ({"factors": _ARR(_PESTEL_FACTOR)}, ["factors"]),
            "premortem": _REQ({"scenarios": _ARR(_SCENARIO)}, ["scenarios"]),
        },
        "output": {
            "pestel": _out(["categories_checked", "total_factors",
                            "evidence_coverage", "verdict"]),
            "premortem": _out(["scenario_count", "risk_ranking",
                               "highest_risk", "verdict"]),
        },
    },
    "auto": {
        "desc": "研究计划与追踪",
        "input": {
            "plan": _REQ({"topic": _STR_NE,
                          "research_questions": _ARR(_QUESTION),
                          "source_types": _ARR(_STR),
                          "methods": _ARR(_STR),
                          "timeline": _REQ({}, [])},
                         ["topic", "research_questions", "source_types",
                          "methods", "timeline"]),
            "track": _REQ({"runs": _ARR(_RUN),
                           "planned_questions": _ARR(_QUESTION)},
                          ["runs", "planned_questions"]),
        },
        "output": {
            "plan": _out(["question_count", "coverage_matrix", "verdict"]),
            "track": _out(["run_count", "completion_rate", "coverage_gaps",
                           "verdict"]),
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
    ap = argparse.ArgumentParser(description="R05 技能契约校验器")
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

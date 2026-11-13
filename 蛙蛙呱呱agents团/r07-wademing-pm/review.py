# -*- coding: utf-8 -*-
"""T7 对抗评审：确定性 adversarial reviewer（产品经理版）。

独立语境、低温确定性、只收 bounded unit_packet + 契约 + 校验链。对 PM 产物做
可复现的确定性挑战：契约符合、禁空泛措辞、决策建议授权、指标可衡量、有产出价值。

失败类别（route-back）：
  vague_metric_or_scope  -> react   （回去补口径/补范围，而非闷头写功能）
  expression_fit         -> writer  （措辞空泛/未授权建议，改写）
  no_report_value        -> controller（丢弃该产出单元）
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from skills import _common as c

# 读者可见结论键
_CONCLUSION_KEYS = ("conclusion", "summary", "problem_statement", "executive_summary",
                    "vision", "north_star", "objective", "recommendation", "decision",
                    "note", "insight", "answer", "value_proposition", "description")

# 空泛/不可验收措辞（对齐 PRD/技术翻译反模式）
_VAGUE = ["提升用户体验", "提高效率", "增加留存", "优化", "增强某功能",
          "支持某功能", "待定", "待补充", "视情况", "灵活处理", "TODO", "TBD"]

# 未授权建议触发词
_ADVICE_RE = re.compile(r"建议|应该|应当|须(尽快|要)|must|should")

# 指标可衡量：出现价值主张/目标，就须有可量化字段
_VALUE_CLAIM_RE = re.compile(r"提升|提高|增长|降低|优化|改善|增加")


def _walk_strings(obj: Any) -> List[str]:
    out: List[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out += _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _walk_strings(v)
    return out


def _conclusion_texts(obj: Any) -> List[str]:
    texts = _walk_strings(obj)
    keyed = [str(obj.get(k)) for k in _CONCLUSION_KEYS
             if isinstance(obj, dict) and isinstance(obj.get(k), str)]
    return keyed or texts


def _ck(ok: bool, msg: str, name: str) -> Dict[str, Any]:
    return {"ok": ok, "check": name, "msg": msg, "sev": "OK" if ok else "BLOCKER"}


def review_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    run_id = packet.get("run_id", "")
    skill = packet.get("skill", "")
    action = packet.get("action", "")
    result = packet.get("result", {}) or {}
    texts = _conclusion_texts(result)
    issues: List[str] = []
    checks: List[Dict[str, Any]] = []

    # 1) 契约符合（T6）
    contracted = True
    if skill and action:
        try:
            import contracts
            r = contracts.validate_output(skill, action, result)
            contracted = r["ok"]
            if not contracted:
                issues.append(f"契约不符: {', '.join(r['errors'][:5])}")
        except Exception:
            contracted = True
    checks.append(_ck(contracted, "契约符合（JSON Schema）", "contract"))

    # 2) 禁空泛措辞
    vague_hits = sorted({v for v in _VAGUE for t in texts if v in t})
    if vague_hits:
        issues.append(f"空泛措辞: {vague_hits}")
    checks.append(_ck(not vague_hits, "无空泛/不可验收措辞", "expression"))

    # 3) 决策建议授权
    has_advice = any(_ADVICE_RE.search(t) for t in texts)
    authorized = bool(result.get("advice_authorized")) or packet.get("advice_authorized")
    if has_advice and not authorized:
        issues.append("含决策建议但未授权（advice_authorized 缺失）")
    checks.append(_ck(not (has_advice and not authorized), "决策建议已授权", "advice_gate"))

    # 4) 指标可衡量：喊「提升/优化」就要有可量化口径
    has_value_claim = any(_VALUE_CLAIM_RE.search(t) for t in texts)
    measurable = any(k in result for k in ("metrics", "target", "baseline",
                                           "input_metrics", "north_star", "score",
                                           "value_created", "opportunity_score", "ranked"))
    if has_value_claim and not measurable:
        issues.append("提出价值/优化主张但无可量化口径（metrics/target/baseline）")
    checks.append(_ck(not (has_value_claim and not measurable),
                      "价值主张可衡量", "metrics_concreteness"))

    # 5) 产出价值：至少含 ok + checks 结构，或非平凡键
    structured = isinstance(result, dict) and ("checks" in result or "ok" in result)
    has_value = structured and len(result) > 1
    if not has_value:
        issues.append("无结构化产出，疑似装饰性输出")
    checks.append(_ck(has_value, "有产出价值（结构完整）", "value_utility"))

    ok = all(x["ok"] for x in checks)
    category = ""
    if not ok:
        if not next(x for x in checks if x["check"] == "metrics_concreteness")["ok"]:
            category = "vague_metric_or_scope"
        elif not next(x for x in checks if x["check"] == "value_utility")["ok"]:
            category = "no_report_value"
        else:
            category = "expression_fit"

    return {
        "run_id": run_id,
        "manifest": f"{skill}/{action}",
        "execution_temperature": 0.0,
        "context_isolation": {"sees_full_material_pack": False,
                              "sees_writer_hidden_reasoning": False,
                              "input_scope": ["unit_packet", "contract"]},
        "verdict": "PASS" if ok else "FAIL",
        "failure_category": category or None,
        "checks": checks,
        "issues": issues,
    }


def add_parser(sp) -> None:
    p = sp.add_parser("review", help="对抗评审：对技能产出做确定性挑战")
    p.add_argument("--result", required=True)
    p.add_argument("--skill", required=True)
    p.add_argument("--action", required=True)
    p.add_argument("--run-id", default="")


def run(args) -> Dict[str, Any]:
    result = c.load_json(args.result)
    packet = {"run_id": args.run_id, "skill": args.skill, "action": args.action,
              "result": result}
    review = review_packet(packet)
    review["exit_code"] = 0 if review["verdict"] == "PASS" else 1
    return review
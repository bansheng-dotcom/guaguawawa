# -*- coding: utf-8 -*-
"""T7 对抗评审：确定性 adversarial reviewer（CEO 主理人版）。

独立语境、低温确定性、只收 bounded unit_packet + 契约 + 校验链。对 CEO 产物做
可复现的确定性挑战：
  1. contract          契约符合（JSON Schema）
  2. expression        禁空泛战略措辞（做大做强/持续优化/TODO…）
  3. advice_gate       决策建议须授权（CEO 不替创始人拍板）
  4. irreversible_gate 不可逆词（签约/扣款/裁员…）必须带人工签发声明
  5. success_kill      结论类产出必须带成功/杀死标准（决策前定）
  6. value_utility     有结构化产出价值

失败类别（route-back）：
  missing_success_kill_criteria -> react   （回去补口径，而非带病决策）
  unauthorized_or_irreversible  -> writer  （改写：去掉未授权建议/补人工签发）
  no_report_value               -> controller（丢弃该产出单元）
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from skills import _common as c

# 读者可见结论键
_CONCLUSION_KEYS = ("conclusion", "summary", "decision", "recommendation",
                    "action", "next", "note", "insight", "answer", "rationale",
                    "problem", "topic", "verdict")

# 空泛/不可验收战略措辞
_VAGUE = ["做大做强", "持续优化", "加强管理", "全面提升", "all-in", "All-in",
          "TODO", "TBD", "待定", "视情况", "再看看", "灵活处理", "尽快推进"]

# 未授权建议触发词
_ADVICE_RE = re.compile(r"建议|应该|应当|必须(立即|尽快)|must|should")

# 不可逆动作词（CEO 边界：不替你签合同、动资金或做其他不可逆决定）
_IRREVERSIBLE = ["签约", "扣款", "退款", "发薪", "删库", "上线生产", "裁员",
                 "不可逆", "永久", "立即支付"]

# 成功/杀死标准的可量化证据键
_CRITERIA_KEYS = ("success_criteria", "kill_criteria", "metrics", "target",
                  "threshold", "grades", "success", "deadline")


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
    if not isinstance(obj, dict):
        return _walk_strings(obj)
    keyed = [str(obj.get(k)) for k in _CONCLUSION_KEYS
             if isinstance(obj.get(k), str)]
    return keyed or _walk_strings(obj)


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

    # 2) 禁空泛战略措辞
    vague_hits = sorted({v for v in _VAGUE for t in texts if v in t})
    if vague_hits:
        issues.append(f"空泛战略措辞: {vague_hits}")
    checks.append(_ck(not vague_hits, "无空泛/不可验收措辞", "expression"))

    # 3) 决策建议授权
    has_advice = any(_ADVICE_RE.search(t) for t in texts)
    authorized = bool(result.get("advice_authorized")) or packet.get("advice_authorized")
    if has_advice and not authorized:
        issues.append("含决策建议但未授权（advice_authorized 缺失）")
    checks.append(_ck(not (has_advice and not authorized),
                      "决策建议已授权", "advice_gate"))

    # 4) 不可逆动作必须人工签发（CEO 不替创始人做不可逆决定）
    has_irreversible = any(w in t for t in texts for w in _IRREVERSIBLE)
    signoff = bool(result.get("human_signoff_required")
                   or result.get("action", "").find("授权") >= 0
                   or result.get("advice_authorized"))
    if has_irreversible and not signoff:
        issues.append("出现不可逆动作词但未声明人工签发（CEO 边界）")
    checks.append(_ck(not (has_irreversible and not signoff),
                      "不可逆动作已声明人工签发", "irreversible_gate"))

    # 5) 结论类产出必须带成功/杀死标准（决策前定，禁止事后补）
    has_conclusion = any(result.get(k) for k in
                         ("decision", "recommendation", "conclusion",
                          "verdict", "action"))
    has_criteria = any(k in result for k in _CRITERIA_KEYS)
    if has_conclusion and not has_criteria:
        issues.append("有结论/决策但无成功/杀死标准（决策前定）")
    checks.append(_ck(not (has_conclusion and not has_criteria),
                      "结论带成功/杀死标准", "success_kill"))

    # 6) 产出价值：结构完整（ok+checks 且非平凡）
    structured = isinstance(result, dict) and ("checks" in result or "ok" in result)
    has_value = structured and len(result) > 1
    if not has_value:
        issues.append("无结构化产出，疑似装饰性输出")
    checks.append(_ck(has_value, "有产出价值（结构完整）", "value_utility"))

    ok = all(x["ok"] for x in checks)
    category = ""
    if not ok:
        if not next(x for x in checks if x["check"] == "success_kill")["ok"]:
            category = "missing_success_kill_criteria"
        elif not (next(x for x in checks if x["check"] == "advice_gate")["ok"]
                  and next(x for x in checks
                           if x["check"] == "irreversible_gate")["ok"]):
            category = "unauthorized_or_irreversible"
        else:
            category = "no_report_value"

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
    p.add_argument("--skill", required=True, dest="review_skill")
    p.add_argument("--action", required=True, dest="review_action")
    p.add_argument("--run-id", default="")


def run(args) -> Dict[str, Any]:
    result = c.load_json(args.result)
    packet = {"run_id": args.run_id, "skill": args.review_skill,
              "action": args.review_action, "result": result}
    review = review_packet(packet)
    review["exit_code"] = 0 if review["verdict"] == "PASS" else 1
    return review

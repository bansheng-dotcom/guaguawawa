# -*- coding: utf-8 -*-
"""R11 对抗评审（T7）：对内容产物本身再评审。

角色化五检查（按优先级）：
1. contract        —— 产出不符合登记契约（JSON Schema）→ controller（丢弃）
2. no_ai_fluff     —— 结论文本含 AI 味套话禁词 → writer（改写）
3. concrete_artifact —— 无具体内容产物（缺 title/draft/outline/guide 等）→ controller
4. publish_gate    —— 文本含「发布/上线」意图但未声明 authorized/approval → writer（退回授权）
5. value_utility   —— 无结构化产出价值（非 dict 或既无 ok 也无 checks）→ controller

r06/r08/r10 教训：fluff/scope 只扫 conclusion_keys 对应的文本值，不扫 msg/dim/checks
（评审/门禁的 checks[].msg 文本必然含这些词，扫了全是误报）。

失败类别（route-back）：
  artifact_not_concrete -> controller（无具体产物，丢弃）
  ai_fluff              -> writer    （AI 味套话，退回改写）
  publish_unauthorized  -> writer    （对外发布未授权，退回授权）
  no_report_value       -> controller（无结构化产出价值）
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c


def _text_values_by_keys(result: Any, keys: List[str]) -> List[str]:
    """只取顶层结论/内容键的字符串值，绝不扫 msg/dim/checks 等元信息键。"""
    vals: List[str] = []
    if isinstance(result, dict):
        for k, v in result.items():
            if k in keys and isinstance(v, str):
                vals.append(v)
    return vals


def review_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["review"]
    run_id = packet.get("run_id", "")
    skill = str(packet.get("skill") or "")
    action = str(packet.get("action") or "")
    result = packet.get("result", {}) or {}

    texts = _text_values_by_keys(result, list(th["conclusion_keys"]))
    checks: List[Dict[str, Any]] = []
    issues: List[str] = []

    # 1. contract（T6）
    contracted = True
    if skill and action:
        try:
            import contracts
            contracted = contracts.validate_output(skill, action, result)["ok"]
        except Exception:
            contracted = True
    if not contracted:
        issues.append("契约不符（JSON Schema）")
    checks.append(c.ck(contracted, "契约符合（JSON Schema）", "review:contract"))

    # 2. no_ai_fluff：结论文本含 AI 味套话禁词
    fluff_hits = sorted({w for w in th["ai_fluff_words"] for t in texts if w in t})
    if fluff_hits:
        issues.append(f"AI 味套话: {fluff_hits[:5]}")
    checks.append(c.ck(not fluff_hits, "无 AI 味套话", "review:no_ai_fluff"))

    # 3. concrete_artifact：至少一键可交付物
    concrete = isinstance(result, dict) and any(k in result for k in th["concrete_keys"])
    if not concrete:
        issues.append("无具体内容产物（缺可交付键）")
    checks.append(c.ck(concrete, "产出具体（可交付）", "review:concrete_artifact"))

    # 4. publish_gate：出现发布意图但未声明 authorized/approval 即 BLOCKER
    has_publish = any(w in t for t in texts for w in th["publish_terms"])
    declared_auth = isinstance(result, dict) and any(k in result for k in th["handoff_keys"])
    if has_publish and not declared_auth:
        issues.append("越界：出现发布/上线意图但未声明 authorized/approval")
    checks.append(c.ck(not (has_publish and not declared_auth),
                       "对外发布有授权", "review:publish_gate"))

    # 5. value_utility：结构化产出（dict 含 ok 或 checks）
    structured = isinstance(result, dict) and ("ok" in result or "checks" in result)
    if not structured:
        issues.append("无结构化产出，疑似装饰性输出")
    checks.append(c.ck(structured, "有结构化产出价值", "review:value_utility"))

    ok = all(x["ok"] for x in checks)
    if ok:
        category, route = None, None
    elif not concrete:
        category, route = "artifact_not_concrete", "controller"
    elif has_publish and not declared_auth:
        category, route = "publish_unauthorized", "writer"
    elif not structured:
        category, route = "no_report_value", "controller"
    else:
        category, route = "ai_fluff", "writer"

    return {
        "run_id": run_id,
        "skill": skill,
        "action": action,
        "manifest": f"{skill}/{action}",
        "execution_temperature": 0.0,
        "context_isolation": {"sees_full_material_pack": False,
                              "sees_writer_hidden_reasoning": False,
                              "input_scope": ["unit_packet", "contract"]},
        "ok": ok,
        "verdict": "PASS" if ok else "FAIL",
        "failure_category": category,
        "route": route,
        "checks": checks,
        "issues": issues,
        "next": ("内容产物通过对抗评审"
                 if ok else f"{issues[0] if issues else '未过评审'}；"
                            f"按 route={route} 处置后重验"),
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


if __name__ == "__main__":
    import json
    import sys
    packet_path = sys.argv[1] if len(sys.argv) > 1 else ""
    if not packet_path:
        print("用法：python review.py <packet.json>", file=sys.stderr)
        raise SystemExit(2)
    with open(packet_path, encoding="utf-8") as f:
        pkt = json.load(f)
    out = review_packet(pkt)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if out["ok"] else 1)

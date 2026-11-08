# -*- coding: utf-8 -*-
"""R19 对抗评审（T7）：对模型工程工件本身再评审。

角色化五检查（按优先级）：
1. contract         —— 产出不符合登记契约（JSON Schema）→ controller（丢弃）
2. credential_gate  —— 结论文本含「api_key/secret/password/token/私钥/密钥/密码/
                       连接串」且未声明交接 → writer（红线 1：不携带凭据）
3. fake_pass_gate   —— 结论文本含「效果不错/看起来好/应该没问题/主观感觉/凭经验
                       判断/直接上线/跳过评估」且未声明 handoff → writer
                       （红线 2：不许「效果看起来不错」直接上线）
4. scope_boundary   —— 结论文本含「统计结论/相关性/显著性/业务归因/决策建议/p值/
                       置信区间」等越界词且未声明移交 → writer（红线 3：不做统计
                       结论与业务归因，移交 R06）
5. concrete_artifact—— 无具体模型工程工件（缺 experiment_id/run_id/model_name/
                       version/dataset_id/scorer_name/trace_id/metric_name/
                       candidate_id/stage/verdict 等）→ controller

复用 r06/r08/r10/r13/r14/r16/r18 教训：fluff/scope 只扫 conclusion_keys 对应的
文本值，不扫 msg/dim/checks（评审/门禁的 checks[].msg 文本必然含这些词，扫了全是
误报）。concrete_keys 绝不含 ok/checks（R15 教训：否则 concrete_artifact 恒真）。

失败类别（route-back）：
  credential_gate       -> writer      （凭据入工件，退回走密钥管理）
  fake_pass             -> writer      （「效果不错」绕过评估/回归，退回补证据）
  scope_overlap         -> writer      （统计结论/业务归因，退回移交 R06）
  artifact_not_concrete -> controller  （无具体模型工程工件，丢弃）
  no_report_value       -> controller  （无结构化产出价值）
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

    declared_handoff = isinstance(result, dict) and any(
        k in result for k in th["handoff_keys"])

    # 2. credential_gate：结论文本含凭据词，未声明交接
    has_cred = any(w in t for t in texts for w in th["credential_words"])
    if has_cred and not declared_handoff:
        issues.append("越界：凭据入工件，须走密钥管理，未声明交接")
    checks.append(c.ck(not (has_cred and not declared_handoff),
                       "凭据已走密钥管理", "review:credential_gate"))

    # 3. fake_pass_gate：结论文本含「效果不错」类绕过评估词，未声明 handoff
    has_fake = any(w in t for t in texts for w in th["fake_pass_words"])
    if has_fake and not declared_handoff:
        issues.append("越界：「效果看起来不错」类结论绕过评估/回归，须补证据链，未声明交接")
    checks.append(c.ck(not (has_fake and not declared_handoff),
                       "上线结论有评估证据（非主观感受）", "review:fake_pass_gate"))

    # 4. scope_boundary：越界词却未声明移交
    has_scope = any(w in t for t in texts for w in th["scope_terms"])
    if has_scope and not declared_handoff:
        issues.append("越界：统计结论/业务归因属 R06，未声明移交")
    checks.append(c.ck(not (has_scope and not declared_handoff),
                       "越界内容已声明移交", "review:scope_boundary"))

    # 5. concrete_artifact：至少一键可交付物
    concrete = isinstance(result, dict) and any(k in result for k in th["concrete_keys"])
    if not concrete:
        issues.append("无具体模型工程工件（缺可交付键）")
    checks.append(c.ck(concrete, "产出具体（可交付）", "review:concrete_artifact"))

    ok = all(x["ok"] for x in checks)
    if ok:
        category, route = None, None
    elif has_cred and not declared_handoff:
        category, route = "credential_gate", "writer"
    elif has_fake and not declared_handoff:
        category, route = "fake_pass", "writer"
    elif has_scope and not declared_handoff:
        category, route = "scope_overlap", "writer"
    elif not concrete:
        category, route = "artifact_not_concrete", "controller"
    else:
        category, route = "no_report_value", "controller"

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
        "next": ("模型工程工件通过对抗评审"
                 if ok else f"{issues[0] if issues else '未过评审'}；"
                            f"按 route={route} 处置后重验"),
    }


def add_parser(sp) -> None:
    p = sp.add_parser("review", help="对抗评审：对模型工程工件做确定性挑战")
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

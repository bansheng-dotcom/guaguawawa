# -*- coding: utf-8 -*-
"""R17 对抗评审（T7）：对自动化工件本身再评审。

角色化五检查（按优先级）：
1. contract            —— 产出不符合登记契约（JSON Schema）→ controller（丢弃）
2. unauthorized_exec   —— 文本含「直接发布/绕过审批/自动扣款」等擅自执行词却未声明
                          handoff → writer（红线：不在无审批情况下自动执行高风险动作）
3. credential_leak     —— 文本含「写死密钥/明文密钥/token=/写进工作流」等泄露词
                          → writer（红线：不把凭据写入技能文档或公开工作流）
4. scope_invent        —— 文本含「业务规则/替业务决定/财务结论」等越界词却未声明移交
                          → writer（红线：不替业务角色发明规则）
5. concrete_artifact   —— 无具体自动化工件（缺 node_count/webhook_count/audit_count
                          等可交付键）→ controller

复用 r06/r08/r10/r13/r14/r16 教训：fluff/scope 只扫 conclusion_keys 对应的文本值，
不扫 msg/dim/checks（评审/门禁的 checks[].msg 文本必然含这些词，扫了全是误报）。

失败类别（route-back）：
  unauthorized_exec   -> writer      （擅自发布/扣款/删除，退回授权）
  credential_leak     -> writer      （凭据写进工作流/文档，退回脱敏）
  scope_invent        -> writer      （替业务角色发明规则，退回移交业务角色）
  artifact_not_concrete -> controller（无具体自动化工件，丢弃）
  no_report_value     -> controller  （无结构化产出价值）
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

    # 2. unauthorized_exec：结论文本含擅自执行词，未声明 handoff
    has_exec = any(w in t for t in texts for w in th["execution_words"])
    declared_handoff = isinstance(result, dict) and any(
        k in result for k in th["handoff_keys"])
    if has_exec and not declared_handoff:
        issues.append("越界：发布/扣款/删除等高风险动作未经审批，未声明 handoff")
    checks.append(c.ck(not (has_exec and not declared_handoff),
                       "高风险动作已声明审批", "review:unauthorized_exec"))

    # 3. credential_leak：结论文本含凭据泄露词
    has_leak = any(w in t for t in texts for w in th["credential_words"])
    if has_leak:
        issues.append("凭据泄露：密钥/凭据写入工作流或文档")
    checks.append(c.ck(not has_leak, "无凭据泄露", "review:credential_leak"))

    # 4. scope_invent：替业务角色发明规则/越界词却未声明移交
    has_scope = any(w in t for t in texts for w in th["scope_terms"])
    if has_scope and not declared_handoff:
        issues.append("越界：替业务角色发明规则/财务结论，未声明移交")
    checks.append(c.ck(not (has_scope and not declared_handoff),
                       "业务规则未越界或已声明移交", "review:scope_invent"))

    # 5. concrete_artifact：至少一键可交付物
    concrete = isinstance(result, dict) and any(k in result for k in th["concrete_keys"])
    if not concrete:
        issues.append("无具体自动化工件（缺可交付键）")
    checks.append(c.ck(concrete, "产出具体（可交付）", "review:concrete_artifact"))

    ok = all(x["ok"] for x in checks)
    if ok:
        category, route = None, None
    elif has_exec and not declared_handoff:
        category, route = "unauthorized_exec", "writer"
    elif has_leak:
        category, route = "credential_leak", "writer"
    elif has_scope and not declared_handoff:
        category, route = "scope_invent", "writer"
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
        "next": ("自动化工件通过对抗评审"
                 if ok else f"{issues[0] if issues else '未过评审'}；"
                            f"按 route={route} 处置后重验"),
    }


def add_parser(sp) -> None:
    p = sp.add_parser("review", help="对抗评审：对自动化工件做确定性挑战")
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

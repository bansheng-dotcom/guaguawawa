# -*- coding: utf-8 -*-
"""R18 对抗评审（T7）：对数据管道工件本身再评审。

角色化五检查（按优先级）：
1. contract            —— 产出不符合登记契约（JSON Schema）→ controller（丢弃）
2. credential_gate     —— 结论文本含「api_key/secret/password/token/私钥/密钥/密码/连接串」且未声明交接 → writer（红线 1）
3. execution_gate      —— 结论文本含「直接回填/直接删除/直接外发/直接迁移/改生产」且未声明 handoff → writer（红线 2）
4. scope_boundary      —— 结论文本含「统计结论/相关性/显著性/业务归因/决策建议」等越界词且未声明移交 → writer（红线 3）
5. concrete_artifact   —— 无具体数据管道工件（缺 connection_id/model_name/dag_id/table/operation/alert_count 等）→ controller

复用 r06/r08/r10/r13/r14/r16 教训：fluff/scope 只扫 conclusion_keys 对应的文本值，
不扫 msg/dim/checks（评审/门禁的 checks[].msg 文本必然含这些词，扫了全是误报）。
concrete_keys 绝不含 ok/checks（R15 教训：否则 concrete_artifact 恒真）。

失败类别（route-back）：
  credential_gate  -> writer      （凭据入工件，退回走密钥管理）
  execution_gate   -> writer      （擅自回填/删除/外发/迁移，退回人工授权）
  scope_overlap    -> writer      （统计结论/业务归因，退回移交 R06）
  artifact_not_concrete -> controller（无具体数据管道工件，丢弃）
  no_report_value  -> controller  （无结构化产出价值）
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
    # L10 硬教训：这里是历史 fail-open 点（except → contracted=True 把校验器崩溃
    # 伪装成「契约符合」）。改为 fail-closed：契约无法确认即视为不符，由人类复核。
    contracted = True
    if skill and action:
        try:
            import contracts
            contracted = contracts.validate_output(skill, action, result)["ok"]
        except Exception as exc:  # noqa: BLE001 - 契约校验器故障必须阻断而非放行
            contracted = False
            issues.append(f"契约校验器异常（fail-closed）：{exc}")
    if not contracted:
        issues.append("契约不符（JSON Schema）")
    checks.append(c.ck(contracted, "契约符合（JSON Schema）", "review:contract"))

    # 2. credential_gate：结论文本含凭据词，未声明交接
    has_cred = any(w in t for t in texts for w in th["credential_words"])
    declared_handoff = isinstance(result, dict) and any(
        k in result for k in th["handoff_keys"])
    if has_cred and not declared_handoff:
        issues.append("越界：凭据入工件，须走密钥管理，未声明交接")
    checks.append(c.ck(not (has_cred and not declared_handoff),
                       "凭据已走密钥管理", "review:credential_gate"))

    # 3. execution_gate：结论文本含擅自执行词，未声明 handoff
    has_exec = any(w in t for t in texts for w in th["execution_words"])
    if has_exec and not declared_handoff:
        issues.append("越界：回填/删除/外发/迁移属高风险，须人工授权，未声明 handoff")
    checks.append(c.ck(not (has_exec and not declared_handoff),
                       "高风险动作已声明授权", "review:execution_gate"))

    # 4. scope_boundary：越界词却未声明移交
    has_scope = any(w in t for t in texts for w in th["scope_terms"])
    if has_scope and not declared_handoff:
        issues.append("越界：统计结论/业务归因属 R06，未声明移交")
    checks.append(c.ck(not (has_scope and not declared_handoff),
                       "越界内容已声明移交", "review:scope_boundary"))

    # 5. concrete_artifact：至少一键可交付物
    concrete = isinstance(result, dict) and any(k in result for k in th["concrete_keys"])
    if not concrete:
        issues.append("无具体数据管道工件（缺可交付键）")
    checks.append(c.ck(concrete, "产出具体（可交付）", "review:concrete_artifact"))

    ok = all(x["ok"] for x in checks)
    if ok:
        category, route = None, None
    elif has_cred and not declared_handoff:
        category, route = "credential_gate", "writer"
    elif has_exec and not declared_handoff:
        category, route = "execution_gate", "writer"
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
        "next": ("数据管道工件通过对抗评审"
                 if ok else f"{issues[0] if issues else '未过评审'}；"
                            f"按 route={route} 处置后重验"),
    }


def add_parser(sp) -> None:
    p = sp.add_parser("review", help="对抗评审：对数据管道工件做确定性挑战")
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

# -*- coding: utf-8 -*-
"""S05 人工审批节点 —— 能力域 5。

整合自 n8n-io__n8n 的 publishing / progressive-building skills：
  - 人工审批节点（高危动作必须 approver/authorization，HITL 卡片）
  - 发布门禁（发布必须显式请求 + live run 证据；未验证节点必须披露）

关键立场：**发布/退款/合同/敏感数据等高风险动作必须有授权记录，绝不能无审批
自动执行**（红线）。本门禁只做确定性结构校验：风险等级 + 高危动作 + 审批人 +
发布前 live run 证据 + 未验证披露。

动作：
  approval  人工审批节点校验
  publish   发布前门禁校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "approval"
DESC = "人工审批节点：approval/publish"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("approval", help="校验人工审批节点（高危动作须授权）")
    a.add_argument("--input", required=True)
    b = act.add_parser("publish", help="校验发布前门禁（live run 证据/未验证披露）")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "approval":
        return _validate_approval(data)
    if args.action == "publish":
        return _validate_publish(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_approval(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["approval"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", approval_count=0,
                        high_risk_count=0)

    approvals = data.get("approvals")
    if not isinstance(approvals, list) or not approvals:
        return c.result([_ck(False, "approvals 必须是非空列表", "approval.list")],
                        ok=False, verdict="FAIL", approval_count=0,
                        high_risk_count=0)

    checks.append(_ck(True, f"审批节点 {len(approvals)} 个", "approval.count"))

    bad_action: List[str] = []
    bad_level: List[str] = []
    high_risk: List[Dict[str, Any]] = []
    for a in approvals:
        if not isinstance(a, dict):
            bad_action.append("(非对象)")
            continue
        act = str(a.get("action", ""))
        lvl = str(a.get("risk_level", ""))
        if lvl not in th["risk_levels"]:
            bad_level.append(act or "?")
        if act in th["high_risk_actions"] or lvl in th["approval_required_levels"]:
            high_risk.append(a)
    checks.append(_ck(not bad_level,
                      f"risk_level 白名单（异常 {bad_level or '无'}）",
                      "approval.risk_level"))

    # 高风险动作必须有 approver 或 authorization（人工签发）
    no_authin: List[str] = []
    for a in high_risk:
        has_approver = bool(a.get("approver"))
        has_auth = bool(a.get("authorization"))
        if not (has_approver or has_auth):
            no_authin.append(str(a.get("action", "?")))
    checks.append(_ck(not no_authin,
                      f"高危动作有审批人/授权（缺 {no_authin or '无'}）",
                      "approval.authorized"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        approval_count=len(approvals), high_risk_count=len(high_risk),
        narrative=f"审批节点 {len(approvals)} 个，高危 {len(high_risk)} 个")


# --------------------------------------------------------------------------- #
def _validate_publish(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", publish_ready=False)

    name = str(data.get("workflow_name", "")).strip()
    checks.append(_ck(bool(name), "workflow_name 非空", "publish.name"))

    # 发布必须显式请求（用户明确要求），或已有 live run 证据
    requested = data.get("publish_requested") is True
    has_evidence = data.get("has_live_run_evidence") is True
    checks.append(_ck(requested or has_evidence,
                      f"发布有显式请求或 live run 证据"
                      f"（requested={requested}, evidence={has_evidence}）",
                      "publish.gate"))

    # 未验证披露：有 simulated/unreached 节点且未 acknowledge → 拦截
    unreached = data.get("nodes_unreached") or []
    simulated = data.get("simulated") is True
    ack = data.get("acknowledge_unverified") is True
    if (unreached or simulated) and not ack:
        checks.append(_ck(False,
                          f"存在未验证节点（unreached={len(unreached)}, "
                          f"simulated={simulated}）但未披露 acknowledge",
                          "publish.disclosure"))
    else:
        checks.append(_ck(True, "未验证节点已披露或不存在", "publish.disclosure"))

    # 错误工作流：涉及 errorWorkflow 必须 publish-before-assign
    if data.get("uses_error_workflow"):
        assigned = data.get("error_workflow_published") is True
        checks.append(_ck(assigned,
                          "错误工作流先发布再指派（publish-before-assign）",
                          "publish.error_flow"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        publish_ready=ok,
        narrative=f"发布门禁 {name or '?'}："
                  f"{'可发布' if ok else '未通过，需修复'}")

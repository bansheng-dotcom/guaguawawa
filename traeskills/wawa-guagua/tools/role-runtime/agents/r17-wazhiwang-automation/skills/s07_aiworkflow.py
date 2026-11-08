# -*- coding: utf-8 -*-
"""S07 AI 工作流接入 —— 能力域 7。

整合自 n8n-io__n8n 的 intent-recognition / model-selection skills：
  - AI 节点接入（模型显式声明 + 用途 + 权限 + 输入输出记录）
  - 意图分类（agent-anchored 动态决策 vs workflow-anchored 固定管道）

关键立场：**在明确模型、输入、评估和权限后才接入 AI 节点**（不隐式兜底默认
模型）。本门禁只做确定性结构校验：模型显式声明 + 用途 + 锚点分类 + 权限边界。

动作：
  aiagent  AI 工作流节点接入校验
  model    模型选择与锚点分类校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "aiworkflow"
DESC = "AI 工作流接入：aiagent/model"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("aiagent", help="校验 AI 节点接入（模型/用途/权限/记录）")
    a.add_argument("--input", required=True)
    b = act.add_parser("model", help="校验模型选择与意图锚点分类")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "aiagent":
        return _validate_aiagent(data)
    if args.action == "model":
        return _validate_model(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_aiagent(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["aiworkflow"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", ai_count=0)

    nodes = data.get("ai_nodes")
    if not isinstance(nodes, list) or not nodes:
        return c.result([_ck(False, "ai_nodes 必须是非空列表", "ai.list")],
                        ok=False, verdict="FAIL", ai_count=0)

    checks.append(_ck(True, f"AI 节点 {len(nodes)} 个", "ai.count"))

    # 节点类型白名单
    bad_type = [str(n.get("name", "?")) for n in nodes
                if isinstance(n, dict) and str(n.get("type", "")) not in th["node_types"]]
    checks.append(_ck(not bad_type,
                      f"AI 节点类型白名单（异常 {bad_type or '无'}）", "ai.node_type"))

    # 模型必须显式声明（不允许隐式默认兜底）+ 用途
    no_model: List[str] = []
    no_purpose: List[str] = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        if not n.get("model"):
            no_model.append(str(n.get("name", "?")))
        if not n.get("purpose"):
            no_purpose.append(str(n.get("name", "?")))
    checks.append(_ck(not no_model,
                      f"每个 AI 节点显式声明 model（缺 {no_model or '无'}）",
                      "ai.model"))
    checks.append(_ck(not no_purpose,
                      f"每个 AI 节点声明 purpose（缺 {no_purpose or '无'}）",
                      "ai.purpose"))

    # 输入输出记录：必须有 evaluation 或 io_record
    io_recorded = bool(data.get("io_record")) or bool(data.get("evaluation"))
    checks.append(_ck(io_recorded,
                      "AI 节点有输入输出记录或评估（io_record/evaluation）",
                      "ai.io_record"))

    # 权限边界：高风险 AI 动作必须有权限声明
    risky = [n for n in nodes if isinstance(n, dict)
             and str(n.get("risk_level")) == "high"]
    no_perm = [str(n.get("name", "?")) for n in risky if not n.get("permission")]
    checks.append(_ck(not no_perm,
                      f"高风险 AI 节点声明权限（缺 {no_perm or '无'}）",
                      "ai.permission"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        ai_count=len(nodes),
        narrative=f"AI 节点 {len(nodes)} 个，高风险 {len(risky)} 个")


# --------------------------------------------------------------------------- #
def _validate_model(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["aiworkflow"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", workflow_count=0)

    # 锚点分类：agent（需要动态决策）vs workflow（固定管道）
    anchor = str(data.get("anchor", ""))
    checks.append(_ck(anchor in th["anchors"],
                      f"锚点={anchor!r} ∈ {th['anchors']}", "model.anchor"))

    # 模型显式声明 + 用途
    model = data.get("model")
    purpose = data.get("purpose")
    checks.append(_ck(bool(model), f"显式声明模型 model={model!r}", "model.declared"))
    checks.append(_ck(bool(purpose), f"声明用途 purpose={purpose!r}", "model.purpose"))

    # agent 锚点必须有工具/护栏声明（动态决策需边界）
    if anchor == "agent":
        has_guard = bool(data.get("tools")) and bool(data.get("guardrails"))
        checks.append(_ck(has_guard,
                          "agent 锚点声明 tools 与护栏（guardrails）",
                          "model.agent_guard"))
    else:
        checks.append(_ck(True, "workflow 锚点无需 agent 护栏", "model.agent_guard"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        workflow_count=1,
        narrative=f"意图锚点 {anchor or '?'}，模型 {model or '?'}")

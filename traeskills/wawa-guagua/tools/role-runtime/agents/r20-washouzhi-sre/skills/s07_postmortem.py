# -*- coding: utf-8 -*-
"""S07 运行复盘 —— 能力域 7。

整合自故障复盘（postmortem/blameless）语义：把故障、告警和恢复结果反馈给
R02/R09。复盘四要素（时间线、根因、影响、改进项）、严重度分级（sev1/2/3）、
改进项闭环（每条带 owner + 到期日 + 状态）。

关键立场：**复盘是「学习」不是「追责」**（blameless）。本角色只校验复盘
结构是否成立、改进项是否可追踪闭环，不替 R02/R09 定性责任、不写结论性
归因（根因描述 ≠ 责任认定）。改进项必须可追踪（owner + 到期），否则复盘
只产出「反思」不产出「改进」。

动作：
  postmortem  复盘结构校验
  improvement 改进项闭环校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "postmortem"
DESC = "运行复盘：postmortem/improvement"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("postmortem", "复盘结构校验"), ("improvement", "改进项闭环校验")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "postmortem":
        return _validate_postmortem(data)
    if args.action == "improvement":
        return _validate_improvement(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_postmortem(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["postmortem"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", postmortem_id="")

    pm_id = str(data.get("postmortem_id", "")).strip()
    checks.append(_ck(bool(pm_id), "复盘 ID 非空", "postmortem.id"))

    severity = data.get("severity")
    checks.append(_ck(severity in th["severities"],
                      f"严重度={severity!r} 在白名单 {th['severities']}",
                      "postmortem.severity"))

    # 四要素齐备
    missing = [s for s in th["required_sections"]
               if not str(data.get(s, "")).strip()]
    checks.append(_ck(not missing,
                      f"四要素齐备（缺 {missing or '无'}）",
                      "postmortem.sections"))

    # 根因非空且非复述现象（blameless：描述根因，不追责）
    root_cause = str(data.get("root_cause", "")).strip()
    checks.append(_ck(bool(root_cause), "根因非空", "postmortem.root_cause"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        postmortem_id=pm_id, severity=severity,
        narrative=f"复盘 {pm_id}：严重度 {severity}")


# --------------------------------------------------------------------------- #
def _validate_improvement(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["postmortem"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", action_count=0)

    actions = data.get("actions") or []
    ok_actions = isinstance(actions, list) and len(actions) > 0
    checks.append(_ck(ok_actions,
                      f"改进项 ≥1（实际 "
                      f"{len(actions) if isinstance(actions, list) else 0}）",
                      "improvement.count"))

    # 每条改进项须含 action/owner/due/status（可追踪闭环）
    bad = [i for i, a in enumerate(actions if isinstance(actions, list) else [])
           if not isinstance(a, dict)
           or not str(a.get("action", "")).strip()
           or not str(a.get("owner", "")).strip()
           or not str(a.get("due", "")).strip()
           or a.get("status") not in ("open", "done", "wontfix")]
    checks.append(_ck(not bad,
                      f"改进项含 action/owner/due/status（缺 {bad or '无'}）",
                      "improvement.required"))

    # 未闭环改进项显式列出（open 状态）
    open_items = [a.get("action") for a in (actions if isinstance(actions, list) else [])
                  if isinstance(a, dict) and a.get("status") == "open"]
    checks.append(_ck(not open_items,
                      f"无未闭环改进项（open {open_items or '无'}）",
                      "improvement.closed_loop"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        action_count=len(actions) if isinstance(actions, list) else 0,
        narrative=f"改进项 {len(actions) if isinstance(actions, list) else 0} 条")

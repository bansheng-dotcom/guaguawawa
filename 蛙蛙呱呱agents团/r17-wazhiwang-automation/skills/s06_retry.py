# -*- coding: utf-8 -*-
"""S06 失败处理与重试 —— 能力域 6。

整合自 n8n-io__n8n 的 debugging-executions / error-workflows skills：
  - 重试/超时/幂等/死信设计（写操作必须幂等；失败须有死信/告警/恢复路径）
  - 错误工作流（errorWorkflow 必须是已发布的 Error Trigger，按目标挂载）

关键立场：**失败不能静默——写操作必须幂等，失败必须有死信与人工恢复路径**。
本门禁只做确定性结构校验：重试上限 + 超时 + 幂等声明 + 死信 + 错误工作流发布。

动作：
  retry      重试/超时/幂等/死信设计校验
  errorflow  错误工作流与恢复路径校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "retry"
DESC = "失败处理与重试：retry/errorflow"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("retry", help="校验重试/超时/幂等/死信设计")
    a.add_argument("--input", required=True)
    b = act.add_parser("errorflow", help="校验错误工作流与恢复路径")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "retry":
        return _validate_retry(data)
    if args.action == "errorflow":
        return _validate_errorflow(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_retry(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["retry"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", retry_count=0,
                        idempotency_declared=False)

    policy = data.get("policy")
    if not isinstance(policy, dict):
        return c.result([_ck(False, "policy 必须是对象", "retry.policy")],
                        ok=False, verdict="FAIL", retry_count=0,
                        idempotency_declared=False)

    max_retries = int(c._num(policy.get("max_retries")))
    checks.append(_ck(0 <= max_retries <= th["max_retries_cap"],
                      f"max_retries={max_retries} 在 [0,{th['max_retries_cap']}]",
                      "retry.max_retries"))

    timeout_s = c._num(policy.get("timeout_s"))
    checks.append(_ck(timeout_s >= th["min_timeout_s"],
                      f"timeout_s={timeout_s} ≥ {th['min_timeout_s']}",
                      "retry.timeout"))

    # 写操作必须声明幂等（idempotency_key 或 poll cursor 去重）
    op = str(policy.get("operation", "")).lower()
    is_write = op in th["write_ops"]
    idem_key = policy.get("idempotency_key")
    poll_dedupe = policy.get("poll_cursor_dedupe") is True
    idem = bool(idem_key) or poll_dedupe
    if is_write:
        checks.append(_ck(idem,
                          f"写操作 {op!r} 已声明幂等（key/去重）",
                          "retry.idempotency"))
    else:
        checks.append(_ck(True, f"操作 {op or 'read'!r} 无需幂等声明",
                          "retry.idempotency"))

    # 死信/告警：失败必须有死信或人工恢复路径
    dead_letter = bool(policy.get("dead_letter")) or bool(data.get("dead_letter"))
    notify = bool(policy.get("notify")) or bool(data.get("notify"))
    checks.append(_ck(dead_letter or notify,
                      f"有死信或告警路径（dead_letter={dead_letter}, "
                      f"notify={notify}）", "retry.dead_letter"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        retry_count=max_retries, idempotency_declared=idem,
        narrative=f"重试策略：max={max_retries}, timeout={timeout_s}s, "
                  f"幂等={idem}")


# --------------------------------------------------------------------------- #
def _validate_errorflow(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["audit"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", errorflow_count=0)

    err_id = data.get("error_workflow_id")
    target = data.get("target_workflow_id")
    checks.append(_ck(bool(target), "target_workflow_id 非空（错误流挂载目标）",
                      "errorflow.target"))

    # errorWorkflow 必须是已发布的 Error Trigger，且按目标挂载（不全局）
    published = data.get("published") is True
    trigger_active = data.get("error_trigger_active") is True
    per_target = data.get("per_target") is True
    checks.append(_ck(bool(err_id),
                      f"声明 error_workflow_id={err_id!r}", "errorflow.id"))
    checks.append(_ck(published and trigger_active,
                      f"错误工作流已发布且 Error Trigger 激活"
                      f"（published={published}, active={trigger_active}）",
                      "errorflow.published"))
    checks.append(_ck(per_target or data.get("global") is not True,
                      "错误流按目标挂载（非全局兜底）", "errorflow.per_target"))

    # 恢复路径：必须有通知或人工恢复手册
    notify = bool(data.get("notification"))
    recovery_doc = bool(data.get("recovery_doc"))
    checks.append(_ck(notify or recovery_doc,
                      f"有通知或人工恢复路径（notify={notify}, doc={recovery_doc}）",
                      "errorflow.recovery"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        errorflow_count=1 if err_id else 0,
        narrative=f"错误工作流 {err_id or '?'} → 目标 {target or '?'}")

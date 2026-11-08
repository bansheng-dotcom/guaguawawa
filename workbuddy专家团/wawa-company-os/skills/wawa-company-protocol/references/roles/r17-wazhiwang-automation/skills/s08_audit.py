# -*- coding: utf-8 -*-
"""S08 自动化审计 —— 能力域 8。

整合自 n8n-io__n8n 的 debugging-executions skills：
  - 执行审计轨迹（触发/输入/执行/输出/错误/操作者证据完整）
  - 执行日志统计（成功/失败/崩溃分布 + 失败可追溯）

关键立场：**保留触发、输入、执行、输出、错误和操作者证据**——审计轨迹是自动化
可运维、可追责的基础。本门禁只做确定性结构校验：证据字段齐备 + 状态白名单 +
失败可追溯。

动作：
  audit   执行审计轨迹校验
  runlog  执行日志统计校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "audit"
DESC = "自动化审计：audit/runlog"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("audit", help="校验执行审计轨迹（证据字段齐备）")
    a.add_argument("--input", required=True)
    b = act.add_parser("runlog", help="校验执行日志统计（状态分布/失败可追溯）")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "audit":
        return _validate_audit(data)
    if args.action == "runlog":
        return _validate_runlog(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_audit(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["audit"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", audit_count=0)

    records = data.get("records")
    if not isinstance(records, list) or not records:
        return c.result([_ck(False, "records 必须是非空列表", "audit.list")],
                        ok=False, verdict="FAIL", audit_count=0)

    checks.append(_ck(True, f"审计记录 {len(records)} 条", "audit.count"))

    # 每条记录必须有触发/输入/执行/输出/操作者证据
    missing: List[str] = []
    bad_status: List[str] = []
    for r in records:
        if not isinstance(r, dict):
            missing.append("(非对象)")
            continue
        rid = str(r.get("execution_id", "?"))
        miss = [f for f in th["required"] if not r.get(f)]
        if miss:
            missing.append(f"{rid}:{','.join(miss)}")
        if str(r.get("status", "")) not in th["statuses"]:
            bad_status.append(rid)
    checks.append(_ck(not missing,
                      f"证据字段齐备（缺 {missing[:5] or '无'}）", "audit.evidence"))
    checks.append(_ck(not bad_status,
                      f"执行状态白名单（异常 {bad_status or '无'}）", "audit.status"))

    # 失败可追溯：error 状态的记录必须有 error 字段
    no_error = [str(r.get("execution_id", "?")) for r in records
                if isinstance(r, dict) and str(r.get("status")) == "error"
                and not r.get("error")]
    checks.append(_ck(not no_error,
                      f"失败记录含 error 详情（缺 {no_error or '无'}）",
                      "audit.error_traceable"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        audit_count=len(records),
        narrative=f"审计轨迹 {len(records)} 条")


# --------------------------------------------------------------------------- #
def _validate_runlog(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["audit"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", execution_count=0)

    executions = data.get("executions")
    if not isinstance(executions, list) or not executions:
        return c.result([_ck(False, "executions 必须是非空列表", "runlog.list")],
                        ok=False, verdict="FAIL", execution_count=0)

    checks.append(_ck(True, f"执行 {len(executions)} 次", "runlog.count"))

    # 状态白名单
    bad_status = [str(e.get("execution_id", "?")) for e in executions
                  if isinstance(e, dict) and str(e.get("status", "")) not in th["statuses"]]
    checks.append(_ck(not bad_status,
                      f"执行状态白名单（异常 {bad_status or '无'}）", "runlog.status"))

    # 证据字段齐备（trigger/input/execution/output/operator 至少有）
    missing: List[str] = []
    for e in executions:
        if not isinstance(e, dict):
            continue
        miss = [f for f in th["evidence_fields"] if f in ("trigger", "input",
                "execution", "output", "operator") and not e.get(f)]
        if miss:
            missing.append(f"{e.get('execution_id', '?')}:{','.join(miss)}")
    checks.append(_ck(not missing,
                      f"执行证据齐备（缺 {missing[:5] or '无'}）", "runlog.evidence"))

    # 统计分布（确定性实算）
    dist: Dict[str, int] = {}
    for e in executions:
        if isinstance(e, dict):
            st = str(e.get("status", "unknown"))
            dist[st] = dist.get(st, 0) + 1
    total = len(executions)
    failed = dist.get("error", 0) + dist.get("crashed", 0)
    success_rate = round(c.safe_div(dist.get("success", 0), total), 4)

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        execution_count=total, failed_count=failed,
        success_rate=success_rate,
        narrative=f"执行 {total} 次：成功 {dist.get('success', 0)} / "
                  f"失败 {failed}，成功率 {success_rate}")

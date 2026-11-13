# -*- coding: utf-8 -*-
"""S07 人工审批与运维接口 —— 能力域 7。

整合自 apache__airflow（运维动作 backfill/清理，高风险动作需人工触发）
+ airbyte（连接删除/重置）+ dbt（run/clean）。把「高风险回填、迁移或外发动作
设置审批和告警」转成确定性校验：操作白名单、授权状态、审批人、告警规则、
运行手册。

关键立场：**运维接口是「请求闸口」不是「执行器」**。高风险动作（回填/迁移/
外发/删除）必须显式授权 + 有审批人 + 有告警规则，否则不放行（红线 2：不擅自
回填/迁移/外发/删数据）。本角色只产出**审批单/告警配置/运维手册**，
**绝不执行**任何高风险动作。

动作：
  request  运维请求审批校验
  alert    告警规则校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "ops"
DESC = "人工审批与运维接口：request/alert"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("request", "运维请求审批校验"), ("alert", "告警规则校验")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "request":
        return _validate_request(data)
    if args.action == "alert":
        return _validate_alert(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_request(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["ops"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", operation="")

    op = data.get("operation")
    checks.append(_ck(op in th["operations"],
                      f"操作={op!r} 在白名单 {th['operations']}",
                      "ops.operation"))

    # 高风险动作必须授权
    auth = data.get("authorization")
    checks.append(_ck(auth in th["authorizations"],
                      f"授权状态={auth!r} 在白名单", "ops.authorization"))
    checks.append(_ck(auth in ("authorized", "approved"),
                      f"高风险操作已授权（{auth!r}）", "ops.authorized"))

    # 审批人非空
    checks.append(_ck(bool(str(data.get("approver", "")).strip()),
                      "审批人非空", "ops.approver"))

    # 运行手册非空（出事有据可查）
    checks.append(_ck(bool(str(data.get("runbook", "")).strip()),
                      "运行手册非空", "ops.runbook"))

    # 操作回滚/恢复计划（高风险动作必须有退路）
    checks.append(_ck(bool(str(data.get("rollback_plan", "")).strip()),
                      "回滚计划非空", "ops.rollback"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        operation=op, authorized=auth in ("authorized", "approved"),
        narrative=f"运维请求 {op}：授权={auth}")


# --------------------------------------------------------------------------- #
def _validate_alert(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", alert_count=0)

    rules = data.get("rules") or []
    ok_rules = isinstance(rules, list) and len(rules) > 0
    checks.append(_ck(ok_rules,
                      f"告警规则 ≥1（实际 "
                      f"{len(rules) if isinstance(rules, list) else 0}）",
                      "alert.count"))

    # 每条规则须有 metric/condition/channel/severity
    bad = [i for i, r in enumerate(rules if isinstance(rules, list) else [])
           if not isinstance(r, dict)
           or not str(r.get("metric", "")).strip()
           or not str(r.get("condition", "")).strip()
           or not str(r.get("channel", "")).strip()
           or not str(r.get("severity", "")).strip()]
    checks.append(_ck(not bad,
                      f"规则含 metric/condition/channel/severity（缺 {bad or '无'}）",
                      "alert.required"))

    # 严重度在白名单（避免随意分级）
    sev_ok = {"critical", "warning", "info"}
    bad_sev = [r.get("severity") for r in (rules if isinstance(rules, list) else [])
               if isinstance(r, dict) and r.get("severity") not in sev_ok]
    checks.append(_ck(not bad_sev,
                      f"严重度在 {{critical,warning,info}}（越界 {bad_sev or '无'}）",
                      "alert.severity"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        alert_count=len(rules) if isinstance(rules, list) else 0,
        narrative=f"告警规则 {len(rules) if isinstance(rules, list) else 0} 条")

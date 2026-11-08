# -*- coding: utf-8 -*-
"""S08 客户运营自动化接口 —— 能力域 8。

R13 不实现自动化（那是 R17 蛙织网的事），但负责给 R17 提「自动化需求卡」：
触发条件、字段映射、人工审批点、审计要求。把「自动化需求卡」转成确定性校验：
触发类型白名单、必填六要素、字段类型白名单、敏感字段禁入、高危动作必须挂人工审批点。

关键立场：**R13 只定义「该自动什么」，不定义「怎么自动」**；审批点永远由业务方
（本角色）提出，R17 只负责实现。敏感字段（password/api_key/token/credit_card）
一律禁入自动化字段映射，这是把「不把凭据写进工作流」落成机器判据。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "automation"
DESC = "客户运营自动化接口：automation/probe"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("automation", help="校验自动化需求卡")
    a.add_argument("--input", required=True)
    b = act.add_parser("probe", help="自动化实现能力探测（R17 可用性，如实降级）")


def run(args) -> Dict[str, Any]:
    if args.action == "automation":
        data = c.load_json(args.input)
        return _validate_automation(data)
    if args.action == "probe":
        return _probe()
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_automation(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    ath = c.load_thresholds()["automation"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", automation_count=0)

    missing = [k for k in ath["required_fields"] if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"自动化需求卡六要素齐备（缺 {missing or '无'}）",
                      "automation.fields"))

    trigger = data.get("trigger")
    ok_trigger = trigger in ath["trigger_types"]
    checks.append(_ck(ok_trigger, f"触发类型={trigger!r} 在白名单", "automation.trigger"))

    # 字段映射：类型白名单 + 敏感字段禁入
    fields = data.get("fields") or []
    ok_fields = isinstance(fields, list)
    bad_type: List[Any] = []
    forbidden: List[str] = []
    if ok_fields:
        for f in fields:
            if not isinstance(f, dict):
                bad_type.append(f)
                continue
            if f.get("type") not in ath["field_types"]:
                bad_type.append(f.get("name", f.get("type")))
            key = str(f.get("name", "")).lower()
            if any(w in key for w in ath["forbidden_fields"]):
                forbidden.append(f.get("name"))
    checks.append(_ck(not bad_type, f"字段类型在白名单（越界 {bad_type or '无'}）",
                      "automation.field_type"))
    checks.append(_ck(not forbidden, f"敏感字段禁入（{forbidden or '无'}）",
                      "automation.forbidden"))

    # 高危动作必须挂人工审批点
    action = str(data.get("action", ""))
    is_high_risk = any(w in action for w in ath["approval_actions"])
    approval = str(data.get("approval_point", "")).strip()
    if is_high_risk:
        checks.append(_ck(bool(approval),
                          f"高危动作「{action}」必须挂人工审批点", "automation.approval"))
    else:
        checks.append(_ck(True, "非高危动作，审批点可选", "automation.approval"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        automation_count=1, field_count=len(fields) if isinstance(fields, list) else 0,
        trigger=trigger, high_risk=is_high_risk,
        narrative=(f"自动化需求「{data.get('action', '?')}」触发 {trigger}、"
                   f"字段 {len(fields) if isinstance(fields, list) else 0} 个"
                   f"{'（高危，需审批）' if is_high_risk else ''}"))


# --------------------------------------------------------------------------- #
def _probe() -> Dict[str, Any]:
    """自动化实现能力探测：如实降级，恒 ok=true（探测非门禁，对应 R12 selfmedia.probe）。"""
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    # 探测 R17 是否已落地：读 registry 里 r17 状态
    n8n_present = os.path.exists(
        os.path.join(os.path.dirname(os.path.dirname(here)), "r17-wazhiwang-automation"))
    status = "ready" if n8n_present else "blocked"
    checks = [c.ck(True, "自动化实现能力探测完成（探测非门禁）", "automation.probe",
                   r17_present=n8n_present)]
    return c.result(checks, ok=True, verdict="PASS", status=status,
                    r17_present=n8n_present,
                    next=("R17 已就绪，可交付自动化需求卡"
                          if n8n_present else "R17 未落地，需求卡校验仍可用，"
                          "实现需等 R17 接入"))

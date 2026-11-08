# -*- coding: utf-8 -*-
"""S01 招聘与入职 —— 能力域 1。

整合自 frappe__hrms 的招聘模块：`hr/doctype/job_opening/job_opening.json`
（status = Open | Closed）、`hr/doctype/job_applicant/job_applicant.json`
（status = Open | Replied | Shortlisted | Rejected | Hold | Accepted）、
`hr/doctype/job_offer/job_offer.json`（status = Draft | Ready to Send |
Awaiting Response | Accepted | Rejected | Cancelled）、
`hr/doctype/employee_onboarding/employee_onboarding.json`
（boarding_status = Pending | In Process | Completed）。把「职位 → 候选人 →
录用 → 入职」管道转成确定性校验：状态白名单、必填字段、录用前置。

关键立场：**招聘管道的每个跃迁都有前置条件**。没有把候选人标记为
Shortlisted 就发 Offer，等于跳过筛选直接录用——这是招聘事故的头号来源。
本角色只产出招聘工件，**不擅自发 Offer / 不替人入职**（红线 1）。

动作：
  opening    职位空缺校验
  applicant  候选人记录校验
  offer      录用通知校验
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from . import _common as c

NAME = "recruit"
DESC = "招聘与入职：opening/applicant/offer"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("opening", "校验职位空缺"), ("applicant", "校验候选人记录"),
                 ("offer", "校验录用通知")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "opening":
        return _validate_opening(data)
    if args.action == "applicant":
        return _validate_applicant(data)
    if args.action == "offer":
        return _validate_offer(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_opening(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["opening"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", opening_count=0)

    missing = [k for k in th["required"] if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"职位必填齐备（缺 {missing or '无'}）",
                      "opening.required"))

    status = data.get("status")
    ok_status = status in th["statuses"]
    checks.append(_ck(ok_status, f"职位状态={status!r} 在白名单", "opening.status"))

    vacancies = c._num(data.get("vacancies"))
    checks.append(_ck(vacancies >= 1, f"招聘人数={vacancies:g} ≥ 1",
                      "opening.vacancies"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        opening_count=1, status=status, vacancies=int(vacancies),
        narrative=(f"职位 {data.get('job_title', '?')}"
                   f"（{status}）{int(vacancies)} 人"))


# --------------------------------------------------------------------------- #
def _validate_applicant(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["applicant"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", applicant_count=0)

    missing = [k for k in th["required"] if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"候选人必填齐备（缺 {missing or '无'}）",
                      "applicant.required"))

    email = str(data.get("email_id", "")).strip()
    checks.append(_ck(bool(_EMAIL_RE.match(email)),
                      f"邮箱格式合法（{email or '空'}）", "applicant.email"))

    status = data.get("status")
    ok_status = status in th["statuses"]
    checks.append(_ck(ok_status, f"候选人状态={status!r} 在白名单",
                      "applicant.status"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        applicant_count=1, status=status,
        narrative=f"候选人 {data.get('applicant_name', '?')}（{status}）")


# --------------------------------------------------------------------------- #
def _validate_offer(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["offer"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", offer_count=0)

    missing = [k for k in th["required"] if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"录用必填齐备（缺 {missing or '无'}）",
                      "offer.required"))

    email = str(data.get("applicant_email", "")).strip()
    checks.append(_ck(bool(_EMAIL_RE.match(email)),
                      f"候选人邮箱合法（{email or '空'}）", "offer.email"))

    status = data.get("status")
    ok_status = status in th["statuses"]
    checks.append(_ck(ok_status, f"录用状态={status!r} 在白名单", "offer.status"))

    # 录用前置：Accepted 只能来自 Shortlisted/Accepted（不许跳过筛选直接接受）
    if status == "Accepted":
        prior = str(data.get("prior_status", "")).strip()
        ok_prior = prior in th["accept_prior_statuses"]
        checks.append(_ck(ok_prior,
                          f"接受前置状态={prior!r} ∈ {th['accept_prior_statuses']}",
                          "offer.prior"))
    else:
        checks.append(_ck(True, f"{status} 非接受态，前置不要求", "offer.prior"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        offer_count=1, status=status,
        narrative=(f"录用 {data.get('applicant_name', '?')}"
                   f"（{status}）职位 {data.get('designation', '?')}"))

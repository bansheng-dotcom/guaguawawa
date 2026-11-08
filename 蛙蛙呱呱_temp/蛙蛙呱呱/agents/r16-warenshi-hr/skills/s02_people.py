# -*- coding: utf-8 -*-
"""S02 人员与合同档案 —— 能力域 2。

整合自 frappe__erpnext 的 Employee doctype：`erpnext/setup/doctype/employee/
employee.json`（status = Active | Inactive | Suspended | Left；first_name/
gender/date_of_birth/date_of_joining 必填；salary_mode = Bank | Cash | Cheque）
与 frappe__hrms 的合同/附件口径。把「人员档案 → 合同期限 → 到期提醒」转成
确定性校验：必填、状态白名单、合同到期窗口、附件齐备、紧急联系人。

关键立场：**人员档案是敏感个人信息的最小必要集**。身份证号/银行卡号/家庭
住址等超必要字段不得进入档案（红线 2，PII 最小化）；档案只维护劳动关系所需
的最小字段。合同到期提醒是主动治理，不是事后救火。

动作：
  employee   人员档案必填与状态校验
  profile    紧急联系人/附件齐备校验
  contract   合同期限与到期提醒校验
"""
from __future__ import annotations

import datetime
import re
from typing import Any, Dict, List

from . import _common as c

NAME = "people"
DESC = "人员与合同档案：employee/profile/contract"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# 超必要个人信息（PII 最小化红线，档案层直接拒绝落库）
_PII_FIELDS = ["id_card", "id_number", "bank_account", "bank_card",
               "home_address", "religion", "ethnicity", "medical_report"]


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("employee", "校验人员档案"), ("profile", "校验联系人与附件"),
                 ("contract", "校验合同期限与到期")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "employee":
        return _validate_employee(data)
    if args.action == "profile":
        return _validate_profile(data)
    if args.action == "contract":
        return _validate_contract(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _parse_date(s: Any):
    if not isinstance(s, str):
        return None
    s = s.strip().replace("T", " ")[:10]
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
def _validate_employee(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["employee"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", employee_count=0)

    missing = [k for k in th["required"] if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"档案必填齐备（缺 {missing or '无'}）",
                      "employee.required"))

    status = data.get("status")
    ok_status = status in th["statuses"]
    checks.append(_ck(ok_status, f"在职状态={status!r} 在白名单", "employee.status"))

    dob = _parse_date(data.get("date_of_birth"))
    doj = _parse_date(data.get("date_of_joining"))
    checks.append(_ck(dob is not None, "出生日期可解析", "employee.dob"))
    checks.append(_ck(doj is not None, "入职日期可解析", "employee.doj"))
    if dob and doj:
        checks.append(_ck(dob < doj, "出生早于入职（时序正确）", "employee.order"))

    # PII 最小化：超必要字段不得落库（红线 2）
    overreach = [k for k in _PII_FIELDS if k in data]
    checks.append(_ck(not overreach,
                      f"无超必要个人信息字段（越界 {overreach or '无'}）",
                      "employee.pii"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        employee_count=1, status=status,
        narrative=f"人员 {data.get('first_name', '?')}（{status}）")


# --------------------------------------------------------------------------- #
def _validate_profile(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", employee_count=0)

    emp = str(data.get("employee", "")).strip()
    checks.append(_ck(bool(emp), "人员标识非空", "profile.employee"))

    # 紧急联系人：至少 1 名 + 姓名与电话齐备
    contacts = data.get("emergency_contacts") or []
    ok_contacts = isinstance(contacts, list) and len(contacts) > 0
    checks.append(_ck(ok_contacts,
                      f"紧急联系人 ≥1（实际 "
                      f"{len(contacts) if isinstance(contacts, list) else 0}）",
                      "profile.contacts"))
    bad_contact = [ct.get("name") for ct in contacts if isinstance(ct, dict)
                   and (not str(ct.get("name", "")).strip()
                        or not str(ct.get("phone", "")).strip())]
    checks.append(_ck(not bad_contact,
                      f"联系人姓名与电话齐备（缺 {bad_contact or '无'}）",
                      "profile.contact_fields"))

    # 附件齐备（身份/合同扫描件）
    attachments = data.get("attachments") or []
    ok_attach = isinstance(attachments, list) and len(attachments) > 0
    checks.append(_ck(ok_attach,
                      f"必要附件 ≥1（实际 "
                      f"{len(attachments) if isinstance(attachments, list) else 0}）",
                      "profile.attachments"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        employee_count=1,
        contact_count=len(contacts) if isinstance(contacts, list) else 0,
        narrative=(f"档案 {emp}：联系人 "
                   f"{len(contacts) if isinstance(contacts, list) else 0} 名、"
                   f"附件 {len(attachments) if isinstance(attachments, list) else 0} 份"))


# --------------------------------------------------------------------------- #
def _validate_contract(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    cth = c.load_thresholds()["contract"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", contract_count=0)

    emp = str(data.get("employee", "")).strip()
    checks.append(_ck(bool(emp), "合同关联人员非空", "contract.employee"))

    start = _parse_date(data.get("start_date"))
    end = _parse_date(data.get("end_date"))
    checks.append(_ck(start is not None, "合同起始可解析", "contract.start"))
    checks.append(_ck(end is not None, "合同到期可解析", "contract.end"))
    if start and end:
        checks.append(_ck(start < end, "合同起止顺序正确", "contract.order"))

    # 到期提醒：as_of 在 [end - window, end] 内即触发提醒
    as_of = _parse_date(data.get("as_of"))
    days_left = None
    if end and as_of:
        days_left = (end - as_of).days
        within = 0 <= days_left <= cth["expiry_window_days"]
        checks.append(_ck(True,
                          f"距到期 {days_left} 天（窗口 "
                          f"{cth['expiry_window_days']} 天"
                          f"{'，触发提醒' if within else ''}）",
                          "contract.expiry"))
    else:
        checks.append(_ck(True, "未提供 as_of，跳过到期提醒", "contract.expiry"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        contract_count=1, days_left=days_left,
        narrative=(f"合同 {emp}：{start} → {end}"
                   + (f"，距到期 {days_left} 天" if days_left is not None else "")))

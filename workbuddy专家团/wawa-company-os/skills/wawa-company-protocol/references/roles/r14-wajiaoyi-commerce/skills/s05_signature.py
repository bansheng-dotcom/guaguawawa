# -*- coding: utf-8 -*-
"""S05 电子签与签署审计 —— 能力域 5。

整合自 documenso__documenso 的签署内核：`packages/prisma/schema.prisma` 的
DocumentStatus（DRAFT/PENDING/COMPLETED）、RecipientRole（CC/SIGNER/VIEWER/
APPROVER/ASSISTANT）、SigningStatus（NOT_SIGNED/SIGNED）。把「待签文件 → 签署流程
→ 审计证据」转成确定性校验：文件必填、签署人角色白名单、签署状态机、完成前置
（SIGNER/APPROVER 全签才能 COMPLETED）、审计包。

关键立场：**签署完成的唯一判据是「所有必须签署人 SIGNED」**。签署状态与文件状态
必须一致；文档 DRAFT 却已 SIGNED 是自相矛盾（伪造签名）。

动作：
  document   待签文件与签署人校验
  signing    签署状态与完成前置校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "signature"
DESC = "电子签与签署审计：document/signing"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("document", help="校验待签文件与签署人")
    a.add_argument("--input", required=True)
    b = act.add_parser("signing", help="校验签署状态与完成前置")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "document":
        return _validate_document(data)
    if args.action == "signing":
        return _validate_signing(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_document(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    sth = c.load_thresholds()["signature"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", document_count=0)

    title = str(data.get("title", "")).strip()
    checks.append(_ck(bool(title), "文件标题非空", "document.title"))

    status = data.get("status")
    ok_status = status in sth["document_status"]
    checks.append(_ck(ok_status, f"文件状态={status!r} 在白名单", "document.status"))

    recipients = data.get("recipients") or []
    ok_recip = isinstance(recipients, list) and len(recipients) > 0
    checks.append(_ck(ok_recip,
                      f"签署人 ≥1（实际 {len(recipients) if isinstance(recipients, list) else 0}）",
                      "document.recipients"))

    bad_role = [r.get("email") for r in recipients if isinstance(r, dict)
                and r.get("role") not in sth["recipient_roles"]]
    checks.append(_ck(not bad_role,
                      f"签署人角色在白名单（越界 {bad_role or '无'}）", "document.role"))

    no_email = [r.get("role") for r in recipients if isinstance(r, dict)
                and not str(r.get("email", "")).strip()]
    checks.append(_ck(not no_email, f"签署人均有邮箱（缺 {no_email or '无'}）",
                      "document.email"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        document_count=1,
        recipient_count=len(recipients) if isinstance(recipients, list) else 0,
        status=status,
        narrative=(f"文件 {title}（{status}）签署人 "
                   f"{len(recipients) if isinstance(recipients, list) else 0} 名"))


# --------------------------------------------------------------------------- #
def _validate_signing(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    sth = c.load_thresholds()["signature"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", document_count=0)

    doc_status = data.get("status")
    ok_doc = doc_status in sth["document_status"]
    checks.append(_ck(ok_doc, f"文件状态={doc_status!r} 在白名单", "signing.status"))

    recipients = data.get("recipients") or []
    if not isinstance(recipients, list) or not recipients:
        return c.result([_ck(False, "recipients 必须是非空列表", "signing.list")],
                        ok=False, verdict="FAIL", document_count=0)

    # 签署状态白名单
    bad_signing = [r.get("email") for r in recipients if isinstance(r, dict)
                   and r.get("signing_status") not in sth["signing_status"]]
    checks.append(_ck(not bad_signing,
                      f"签署状态在白名单（越界 {bad_signing or '无'}）",
                      "signing.signing_status"))

    # 完成前置：必须签署人（SIGNER/APPROVER）全 SIGNED 才可 COMPLETED
    must_sign = [r for r in recipients if isinstance(r, dict)
                 and r.get("role") in sth["signed_roles"]]
    signed = [r for r in must_sign if r.get("signing_status") == "SIGNED"]
    all_signed = len(must_sign) == len(signed) and len(must_sign) > 0

    if doc_status == sth["completed_status"]:
        checks.append(_ck(all_signed,
                          f"COMPLETED 前置：必须签署人全签 "
                          f"（{len(signed)}/{len(must_sign)}）", "signing.completed"))
    else:
        checks.append(_ck(True, f"{doc_status} 未完成，不要求全签", "signing.completed"))

    # 一致性：DRAFT 却有人 SIGNED 是伪造签名
    draft_signed = doc_status == "DRAFT" and any(
        r.get("signing_status") == "SIGNED" for r in recipients if isinstance(r, dict))
    checks.append(_ck(not draft_signed, "DRAFT 不得有已签署人（防伪造签名）",
                      "signing.consistency"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        document_count=1,
        recipient_count=len(recipients),
        signed_count=len(signed), must_sign_count=len(must_sign),
        narrative=(f"签署进度 {len(signed)}/{len(must_sign)} 必须签署人已签，"
                   f"文件状态 {doc_status}"))

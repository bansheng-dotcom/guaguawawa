# -*- coding: utf-8 -*-
"""S03 冷启动与外联 —— 能力域 3。

整合自 coreyhaines31__marketingskills（cold-email / prospecting）。
把「冷外联」从口头建议转成确定性校验：冷邮件四要素（观察→问题→证明→请求）、
AI 腔禁词、发送前合规三件套（域名/退订/地址）、序列 3-5 封逐封新增价值。

动作：
  coldemail  冷邮件（四要素 + AI 腔禁词 + 发送前合规）
  sequence   外联序列（3-5 封 + 逐封新增价值）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "outreach"
DESC = "冷启动与外联：coldemail/sequence"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    b = act.add_parser("coldemail", help="校验冷邮件")
    b.add_argument("--input", required=True)
    u = act.add_parser("sequence", help="校验外联序列")
    u.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "coldemail":
        return _validate_coldemail(data)
    if args.action == "sequence":
        return _validate_sequence(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_coldemail(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    required = th["outreach"]["email_required"]
    missing = [k for k in required if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"冷邮件四要素齐备（缺 {missing or '无'}）",
                      "outreach.email_fields"))

    body = " ".join(str(data.get(k, "")) for k in required)
    ai_tells = th["outreach"]["ai_tells"]
    hits = [w for w in ai_tells if w.lower() in body.lower()]
    checks.append(_ck(not hits, f"无 AI 腔禁词（命中 {hits[:5] or '无'}）",
                      "outreach.ai_tells"))

    compliance = data.get("compliance")
    ok_comp = isinstance(compliance, dict)
    checks.append(_ck(ok_comp, "发送前合规项存在", "outreach.compliance"))
    if ok_comp:
        comp_missing = [k for k in th["outreach"]["compliance_required"]
                        if not str(compliance.get(k, "")).strip()]
        checks.append(_ck(not comp_missing,
                          f"合规三件套齐备（缺 {comp_missing or '无'}）",
                          "outreach.compliance_fields"))
    else:
        checks.append(_ck(False, "合规三件套缺失", "outreach.compliance_fields"))

    ok = (not missing and not hits and ok_comp and not any(
        not str(compliance.get(k, "")).strip()
        for k in th["outreach"]["compliance_required"]))
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    ai_tell_count=len(hits))


# --------------------------------------------------------------------------- #
def _validate_sequence(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    emails = data.get("emails")
    ok_list = isinstance(emails, list)
    checks.append(_ck(ok_list, "外联序列为列表", "sequence.list"))
    if not ok_list:
        return c.result(checks, ok=False, verdict="FAIL", email_count=0)

    lo, hi = th["outreach"]["sequence_min"], th["outreach"]["sequence_max"]
    n = len(emails)
    ok_count = lo <= n <= hi
    checks.append(_ck(ok_count, f"序列 {n} 封（区间 {lo}-{hi}）", "sequence.count"))

    # 逐封新增价值：每封主题/正文不得与前封完全相同
    bodies = [str(e.get("body", "")).strip() if isinstance(e, dict) else "" for e in emails]
    ok_distinct = len(set(bodies)) == n and all(bodies)
    checks.append(_ck(ok_distinct, "逐封新增价值（无重复/无空）", "sequence.distinct"))

    # breakup 收尾
    last = bodies[-1].lower() if bodies else ""
    has_breakup = c.has_any(last, th["outreach"]["breakup_keywords"])
    checks.append(_ck(has_breakup, "末封为 breakup 收尾", "sequence.breakup"))

    ok = ok_count and ok_distinct and has_breakup
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL", email_count=n)

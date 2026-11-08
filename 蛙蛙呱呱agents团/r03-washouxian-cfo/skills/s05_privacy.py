# -*- coding: utf-8 -*-
"""S05 隐私与数据安全（能力域 5）。

来源：JoelLewis__finance_skills privacy-data-security
（Reg S-P：初始隐私通知于建立客户关系当时送达、6 项内容、
年度通知每 12 个月、FAST Act 网站张贴替代两前提、
退出权与 5 类例外白名单；2024 修正案：敏感信息泄露 ≤30 天通知个人；
NY DFS 72 小时监管通知；供应商合同 24–72 小时违约通知条款；
访问审查至少每年 + 最小权限；NPI 传输 TLS ≥1.2；双态加密）
+ GDPR 口径（数据主体请求 30 天响应、六类合法利益基础、
跨境传输 adequacy/SCC/BCR/derogation）。

不确定性最小化：字段级最小化校验 + 记录留存/销毁对齐 17a-4。
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c

NAME = "privacy"
DESC = "隐私与数据安全：map/dsr/minimize"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("map", "数据流与隐私通知校验（合法基础/跨境/通知时限）"),
                 ("dsr", "数据主体请求处理门禁（30 天时钟 + 完成校验）"),
                 ("minimize", "字段级最小化 + 留存销毁 + 访问控制")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"map": _map, "dsr": _dsr, "minimize": _minimize}[args.action]
    return fn(data)


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------------------------------- #
def _map(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["privacy"]
    flows = data.get("data_flows", []) or []
    checks: List[Dict[str, Any]] = []
    if not flows:
        checks.append(c.ck(False, "data_flows 为空（隐私保护始于数据映射）",
                           "structure", "CRITICAL"))
        return c.result(checks, next="先盘点数据流")
    gaps: List[Dict[str, Any]] = []
    for i, fl in enumerate(flows):
        fid = str(fl.get("id", f"flow-{i + 1}"))
        basis = str(fl.get("lawful_basis", ""))
        if fl.get("personal_data") and basis not in th["lawful_bases"]:
            gaps.append({"flow": fid, "issue": f"非法合法基础 {basis or '缺失'}"})
            checks.append(c.ck(False,
                               f"{fid} 个人数据缺合法基础"
                               f"（{basis or '缺失'}）",
                               "lawful_basis", "CRITICAL", flow=fid))
        retention = _num(fl.get("retention_days", 0))
        if fl.get("personal_data") and retention < th["min_days_retention"]:
            gaps.append({"flow": fid, "issue": "缺留存期定义"})
            checks.append(c.ck(False, f"{fid} 缺留存期定义",
                               "retention", "HIGH", flow=fid))
        if fl.get("cross_border") and \
                str(fl.get("cross_border_basis", "")) \
                not in th["cross_border_basis"]:
            gaps.append({"flow": fid, "issue": "跨境传输缺合法机制"})
            checks.append(c.ck(False,
                               f"{fid} 跨境传输缺机制"
                               f"（adequacy/scc/bcr/derogation）",
                               "cross_border", "CRITICAL", flow=fid))
    # 隐私通知时限：初始通知须在建关系当时；年度通知每 12 个月
    notice = data.get("privacy_notice", {}) or {}
    if notice:
        checks.append(c.ck(bool(notice.get("initial_delivered")),
                           "初始隐私通知须于建立客户关系当时送达",
                           "initial_notice", "CRITICAL"
                           if not notice.get("initial_delivered") else "OK"))
        months = _num(notice.get("months_since_annual_notice", 99))
        checks.append(c.ck(months <= 12,
                           f"年度通知距今 {months:.0f} 个月（≤12）",
                           "annual_notice", "HIGH" if months > 12 else "OK"))
        # FAST Act 两前提网站张贴替代
        if notice.get("website_posted"):
            ok = notice.get("only_exception_sharing") and \
                notice.get("no_policy_change")
            checks.append(c.ck(bool(ok),
                               "网站张贴替代年度邮寄须同时满足：仅例外项共享"
                               "+政策未变", "fast_act", "HIGH"
                               if not ok else "OK"))
        # 非关联第三方共享须先给退出机会（5 类例外白名单）
        if notice.get("shares_nonaffiliated"):
            checks.append(c.ck(bool(notice.get("opt_out_offered"))
                               or bool(notice.get("exception_applies")),
                               "向非关联第三方共享 NPI 前须提供退出机会"
                               "（或适用 248.14/15 例外）", "opt_out",
                               "CRITICAL"
                               if not (notice.get("opt_out_offered")
                                       or notice.get("exception_applies"))
                               else "OK"))
    checks.append(c.ck(not gaps,
                       f"数据流合规 {len(flows) - len({g['flow'] for g in gaps})}"
                       f"/{len(flows)}", "flows", "HIGH" if gaps else "OK"))
    return c.result(checks, flow_count=len(flows), gaps=gaps[:15],
                    next="先补齐映射再谈控制；共享前走退出流程")


# --------------------------------------------------------------------------- #
def _dsr(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["privacy"]
    requests = data.get("requests", []) or []
    checks: List[Dict[str, Any]] = []
    if not requests:
        checks.append(c.ck(False, "requests 为空", "structure", "CRITICAL"))
        return c.result(checks, next="补 DSR 工单")
    overdue: List[Dict[str, Any]] = []
    for i, r in enumerate(requests):
        rid = str(r.get("id", f"dsr-{i + 1}"))
        rtype = str(r.get("type", ""))
        if rtype not in th["dsr_types"]:
            checks.append(c.ck(False, f"{rid} 非法请求类型 {rtype}",
                               "dsr_type", "MEDIUM", request=rid))
        days_open = _num(r.get("days_open", 0))
        done = bool(r.get("completed"))
        if not done and days_open > th["dsr_deadline_days"]:
            overdue.append({"id": rid, "days_open": days_open})
            checks.append(c.ck(False,
                               f"{rid} 开启 {days_open:.0f} 天未完成"
                               f"（> {th['dsr_deadline_days']} 天）",
                               "dsr_deadline", "CRITICAL", request=rid))
        # 完成的请求必须有身份验证 + 完成记录
        if done and not (r.get("identity_verified") and r.get("completed_at")):
            checks.append(c.ck(False, f"{rid} 已完成但缺身份验证或完成时间戳",
                               "dsr_evidence", "HIGH", request=rid))
    checks.append(c.ck(not overdue,
                       f"DSR 处理 {len(requests)} 件，逾期 {len(overdue)} 件",
                       "dsr", "CRITICAL" if overdue else "OK"))
    # 数据泄露通知时钟：个人通知 ≤30 天；DFS 72 小时；供应商 24–72 小时
    breach = data.get("breach", {})
    if breach:
        hours = _num(breach.get("hours_since_detection", 0))
        checks.append(c.ck(breach.get("dfs_notified", False)
                           or hours <= th["breach_notification_hours"],
                           f"泄露后 {hours:.0f} 小时：DFS 须 72 小时内通知",
                           "breach_dfs", "CRITICAL"
                           if not (breach.get("dfs_notified")
                                   or hours <= th["breach_notification_hours"])
                           else "OK"))
        days = hours / 24.0
        checks.append(c.ck(breach.get("individuals_notified", False)
                           or days <= 30,
                           f"泄露后 {days:.1f} 天：敏感信息须 ≤30 天通知个人",
                           "breach_notice", "CRITICAL"
                           if not (breach.get("individuals_notified")
                                   or days <= 30) else "OK"))
    return c.result(checks, overdue=overdue,
                    next="DSR 全闭环留痕；泄露事件 72 小时/30 天双时钟")


# --------------------------------------------------------------------------- #
def _minimize(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["privacy"]
    fields = data.get("collected_fields", []) or []
    checks: List[Dict[str, Any]] = []
    if not fields:
        checks.append(c.ck(False, "collected_fields 为空", "structure",
                           "CRITICAL"))
        return c.result(checks, next="补字段清单")
    unnecessary: List[Dict[str, Any]] = []
    for i, f in enumerate(fields):
        fid = str(f.get("field", f"field-{i + 1}"))
        if not str(f.get("purpose", "")).strip():
            unnecessary.append({"field": fid, "issue": "无收集目的"})
            checks.append(c.ck(False, f"{fid} 缺收集目的（purpose）",
                               "purpose", "HIGH", field=fid))
        elif f.get("necessary") is False:
            unnecessary.append({"field": fid, "issue": "标记为非必要仍在收集"})
            checks.append(c.ck(False, f"{fid} 非必要但仍在收集",
                               "necessity", "HIGH", field=fid))
        # 敏感字段须加密（静态+传输 TLS ≥1.2）
        if f.get("sensitive"):
            checks.append(c.ck(bool(f.get("encrypted_at_rest"))
                               and bool(f.get("tls_1_2_plus")),
                               f"{fid} 敏感字段须双态加密 + TLS ≥1.2",
                               "encryption", "CRITICAL", field=fid))
    checks.append(c.ck(not unnecessary,
                       f"最小化合规 {len(fields) - len({u['field'] for u in unnecessary})}"
                       f"/{len(fields)}", "minimization",
                       "HIGH" if unnecessary else "OK"))
    # 访问审查：至少每年一次 + 特权账户更频繁
    access = data.get("access_review", {}) or {}
    if access:
        months = _num(access.get("months_since_last_review", 99))
        checks.append(c.ck(months <= 12,
                           f"访问审查距今 {months:.0f} 个月（≤12）",
                           "access_review", "HIGH" if months > 12 else "OK"))
        if access.get("privileged_accounts") and \
                not access.get("privileged_reviewed_more_frequently"):
            checks.append(c.ck(False, "特权账户须比年度更频繁地复审",
                               "privileged_review", "HIGH"))
    # 过期销毁：到期数据须安全销毁（物理粉碎/密码学擦除）
    expired = [f for f in fields if _num(f.get("retention_expired", 0))]
    if expired:
        destroyed = [f for f in expired if f.get("securely_destroyed")]
        checks.append(c.ck(len(destroyed) == len(expired),
                           f"到期字段销毁 {len(destroyed)}/{len(expired)}",
                           "secure_destruction", "CRITICAL"
                           if len(destroyed) != len(expired) else "OK"))
    return c.result(checks, unnecessary=unnecessary[:15],
                    next="非必要字段停采；到期数据安全销毁留痕")

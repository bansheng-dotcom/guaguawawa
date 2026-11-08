# -*- coding: utf-8 -*-
"""S04 合同与政策（能力域 4）。

来源：alirezarezvani__claude-skills general-counsel-advisor
（contract_risk_scanner 12 条规则：auto-renewal / unilateral price change /
unlimited liability / termination-for-convenience 拒绝 / vague IP ownership /
uncapped customer indemnity / one-sided indemnity / non-compete /
exclusive dealing / assignment / payment terms / notice period，
每条含 severity + why + redline）。

契约（12 条规则 × severity/why/redline）+ 政策字段门禁全部确定性可测。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from skills import _common as c

NAME = "contract"
DESC = "合同与政策：scan/policy/redline"

# 12 条规则移植自 contract_risk_scanner.py，补充中文条款模式
# (id, severity, patterns[regex], why, redline)
RULES: List[Dict[str, Any]] = [
    {"id": "AUTO_RENEWAL", "severity": "HIGH",
     "patterns": [r"auto[\s-]?renew", r"automatic(?:ally)? renew",
                  r"renew(s|ed|al)? (?:for|unless)",
                  r"自动续约", r"自动续期"],
     "why": "未设上限的自动续约会把双方锁进长期承诺",
     "redline": "增加续约期限上限与退出窗口：须在续约期开始前书面确认"},
    {"id": "AUTO_RENEWAL_NOTICE", "severity": "CRITICAL",
     "patterns": [r"(?:sixty|60|ninety|90|one hundred (?:and )?eighty|180)"
                  r" days? (?:prior )?notice (?:of )?(?:to )?"
                  r"(?:cancel|terminat|nonrenew)", r"提前\s*(60|90|180)\s*天",
                  r"不得早于.*天.*通知"],
     "why": "过长的解约通知期实质上剥夺了退出权",
     "redline": "将通知期缩短至 ≤30 天，且允许到期前任意时点发出"},
    {"id": "UNILATERAL_PRICE_CHANGE", "severity": "CRITICAL",
     "patterns": [r"may (?:change|modify|adjust).{0,40}(?:price|fees|rates)"
                  r"(?:.{0,40}at any time)?", r"有权.{0,10}(?:调整|变更)"
                  r".{0,10}(?:价格|费用|费率)", r"价格.{0,6}单方(?:调整|变更)"],
     "why": "单方任意调价权让成本不可预算",
     "redline": "改为：调价须提前 ≥30 天书面通知，且客户可拒绝并按原价"
                "履约至期末"},
    {"id": "UNLIMITED_LIABILITY", "severity": "CRITICAL",
     "patterns": [r"liability.{0,60}(?:unlimited|without limit)",
                  r"no (?:limit|cap) on liability", r"不设.{0,6}责任上限",
                  r"责任.{0,4}无上限"],
     "why": "无上限责任对一方是生存性风险",
     "redline": "加入责任上限（如过去 12 个月费用额），排除间接损失"},
    {"id": "NO_TERMINATION_FOR_CONVENIENCE", "severity": "MEDIUM",
     "patterns": [r"(?:may not|shall not|cannot) terminat.{0,40}"
                  r"(?:convenience|without cause)", r"不得.{0,8}无因"
                  r".{0,4}解约", r"无正当理由不得解约"],
     "why": "剥夺便利终止权意味着只能违约退出",
     "redline": "加入 30 天通知的便利终止条款（可付合理取消费）"},
    {"id": "VAGUE_IP_OWNERSHIP", "severity": "CRITICAL",
     "patterns": [r"all (?:right|title|interest).{0,30}(?:work product"
                  r"|deliverables?|materials?)", r"全部(?:工作成果|交付物"
                  r"|知识产权).{0,12}(?:归|属于)"],
     "why": "宽泛的 IP 转让条款会吞掉可复用资产与背景 IP",
     "redline": "限定转让范围为「按本合同专门创建的交付物」，明确背景 IP "
                "与复用组件的保留"},
    {"id": "UNCAPPED_CUSTOMER_INDEMNITY", "severity": "CRITICAL",
     "patterns": [r"indemnif.{0,120}(?:any and all|all) (?:claims|losses"
                  r"|damages|liabilit)", r"(?:任何及全部|一切)"
                  r".{0,8}(?:索赔|损失|损害)"],
     "why": "无限赔付范围的补偿义务等于无上限责任",
     "redline": "限缩补偿范围为第三方直接索赔 + 设共同上限"},
    {"id": "ONE_SIDED_INDEMNITY", "severity": "HIGH",
     "patterns": [r"客户.{0,10}须赔偿.{0,40}(?:一切|全部)", r"one[- ]sided"
                  r".{0,20}indemnif"],
     "why": "单向补偿义务打破风险对价平衡",
     "redline": "改为交叉补偿（mutual indemnity）"},
    {"id": "NON_COMPETE", "severity": "HIGH",
     "patterns": [r"non[\s-]?compet", r"不得.{0,10}(?:从事|经营)"
                  r".{0,15}(?:竞争|相同|类似).{0,8}(?:业务|业务)"],
     "why": "过宽竞业限制在多数法域不可执行且限制经营",
     "redline": "删除或限缩至具体竞争产品 + ≤12 个月 + 合理地域"},
    {"id": "EXCLUSIVE_DEALING", "severity": "HIGH",
     "patterns": [r"exclusiv(?:e|ity).{0,40}(?:deal|partnership"
                  r"|supplier|vendor)", r"独家(?:合作|供应|代理)"],
     "why": "排他承诺切断替代供应与议价能力",
     "redline": "限定排他的产品范围与期限（≤12 个月），保留替代来源"},
    {"id": "ASSIGNMENT_RESTRICTION", "severity": "MEDIUM",
     "patterns": [r"may not assign.{0,60}without.{0,30}consent",
                  r"未经.{0,8}书面同意.{0,10}不得转让"],
     "why": "绝对禁转让条款阻碍并购重组与融资尽调",
     "redline": "增加例外：关联方重组与收购情形下可自由转让"},
    {"id": "NET_PAYMENT_TERMS", "severity": "MEDIUM",
     "patterns": [r"net\s+(?:60|75|90|120)", r"(?:60|90|120)\s*天.{0,6}"
                  r"(?:付款|账期)"],
     "why": "超长账期形成对供应商的隐性融资",
     "redline": "压缩至 net 30/45，或加逾期利息条款"},
]
_RULES_BY_ID = {r["id"]: r for r in RULES}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("scan", "12 条规则扫描合同文本（severity/why/redline）"),
                 ("policy", "内部政策初稿字段完整性门禁"),
                 ("redline", "整改跟踪：每个 CRITICAL/HIGH 必须有 redline 状态")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"scan": _scan, "policy": _policy, "redline": _redline}[args.action]
    return fn(data)


# --------------------------------------------------------------------------- #
def _scan(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["contract"]
    text = str(data.get("text", ""))
    checks: List[Dict[str, Any]] = []
    if len(text.strip()) < 50:
        checks.append(c.ck(False, "合同文本为空或过短（<50 字符）", "structure",
                           "CRITICAL"))
        return c.result(checks, findings=[], next="补全文合同文本")
    findings: List[Dict[str, Any]] = []
    for r in RULES:
        hits: List[str] = []
        for pat in r["patterns"]:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                hits.append(m.group(0)[:40])
        if hits:
            findings.append({"rule": r["id"], "severity": r["severity"],
                             "matched": hits[0], "why": r["why"],
                             "redline": r["redline"]})
    critical = [f for f in findings if f["severity"] == "CRITICAL"]
    high = [f for f in findings if f["severity"] == "HIGH"]
    checks.append(c.ck(not critical,
                       f"扫描命中 {len(findings)} 条"
                       f"（CRITICAL {len(critical)} / HIGH {len(high)}）",
                       "critical_findings", "CRITICAL" if critical else "OK"))
    if data.get("pending"):
        # 待签合同存在 CRITICAL 红线时禁止进入签署建议
        checks.append(c.ck(not critical and not high,
                           "待签合同须零 CRITICAL/HIGH 才可送签（"
                           + ("不满足" if (critical or high) else "满足") + "）",
                           "sign_gate", "HIGH" if (critical or high) else "OK"))
    return c.result(checks, findings=findings,
                    critical_count=len(critical), high_count=len(high),
                    next="CRITICAL 未消不可签；本技能不做正式法律意见")


# --------------------------------------------------------------------------- #
def _policy(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["contract"]
    policy = data.get("policy", {}) or {}
    checks: List[Dict[str, Any]] = []
    if not policy:
        checks.append(c.ck(False, "policy 为空", "structure", "CRITICAL"))
        return c.result(checks, next="补政策字段")
    for f in th["policy_required_fields"]:
        v = policy.get(f)
        ok = v is not None and str(v).strip() != ""
        checks.append(c.ck(ok, f"政策字段「{f}」"
                           + ("齐全" if ok else "缺失"),
                           "policy_field", "HIGH" if not ok else "OK",
                           field=f))
    cycle = _to_int(policy.get("review_cycle_days"))
    checks.append(c.ck(cycle is not None and 0 < cycle
                       <= th["policy_review_cycle_days"],
                       f"评审周期 {cycle} 天"
                       + (f"（≤ {th['policy_review_cycle_days']}）"
                          if cycle else "（缺失或非法）"),
                       "review_cycle", "HIGH"
                       if (cycle is None or cycle <= 0
                           or cycle > th["policy_review_cycle_days"])
                       else "OK"))
    # 政策必须有 enforcement 动作描述（不能只写原则）
    enf = str(policy.get("enforcement", ""))
    has_action = any(w in enf for w in ("阻止", "拦截", "拒绝", "禁止",
                                        "驳回", "block", "reject", "deny"))
    checks.append(c.ck(bool(enf) and has_action,
                       "enforcement 须含可执行动作（阻止/拦截/拒绝/驳回）",
                       "enforcement_actionable", "HIGH"
                       if not (enf and has_action) else "OK"))
    return c.result(checks, next="字段齐全 + 可执行 enforcement 后发布")


def _to_int(v: Any):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
def _redline(data: Any) -> Dict[str, Any]:
    """整改门禁：scan 命中的 CRITICAL/HIGH 每条必须有 redline 状态。"""
    th = c.load_thresholds()["contract"]
    findings = data.get("findings", []) or []
    fixes = data.get("fixes", {}) or {}
    checks: List[Dict[str, Any]] = []
    if not findings:
        checks.append(c.ck(False, "findings 为空（先跑 scan）", "structure",
                           "CRITICAL"))
        return c.result(checks, next="先跑 contract.scan")
    open_items: List[Dict[str, Any]] = []
    for f in findings:
        sev = str(f.get("severity", "MEDIUM"))
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        if order.get(sev, 2) > order.get(th["min_severity"], 2):
            continue
        rule = str(f.get("rule", "?"))
        fx = fixes.get(rule) or {}
        if not fx.get("status"):
            open_items.append({"rule": rule, "severity": sev,
                               "issue": "无整改状态"})
            checks.append(c.ck(False, f"{rule}（{sev}）无整改状态",
                               "redline_status", "HIGH", rule=rule))
        elif str(fx.get("status")) not in ("negotiated", "accepted_risk",
                                           "removed", "rejected"):
            open_items.append({"rule": rule, "severity": sev,
                               "issue": f"非法状态 {fx.get('status')}"})
            checks.append(c.ck(False, f"{rule} 整改状态非法"
                               f"（{fx.get('status')}）", "redline_status",
                               "HIGH", rule=rule))
        elif str(fx.get("status")) == "accepted_risk" and \
                sev == "CRITICAL" and not fx.get("approver"):
            open_items.append({"rule": rule, "severity": sev,
                               "issue": "CRITICAL 风险接受须有 approver"})
            checks.append(c.ck(False, f"{rule} CRITICAL 接受风险须有 approver",
                               "risk_acceptance", "CRITICAL", rule=rule))
    checks.append(c.ck(not open_items,
                       f"整改跟踪 {len(findings)} 条，未闭合 "
                       f"{len(open_items)} 条", "redline",
                       "HIGH" if open_items else "OK"))
    return c.result(checks, open_items=open_items,
                    next="全闭合或风险经审批接受后方可签署")

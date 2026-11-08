# -*- coding: utf-8 -*-
"""S08 广告 / KYC-AML / 投资风控（能力域 8）。

来源：anthropics__financial-services kyc-screener
（kyc-rules 规则引擎：六因子风险评级 jurisdiction/applicant_type/
ownership_opacity/pep/sanctions/source_of_funds，低≤2 / 中≤4 / 高；
处置 clear/request-docs/escalate-edd/decline-recommend——**永不直接批准**）
+ JoelLewis__finance_skills anti-money-laundering
（CTR 现金 >$10,000 / 15 天申报；SAR ≥$5,000 / 30 天（60 天无嫌疑人）、
持续活动每 90 天续报；结构化拆分检测）
+ know-your-customer（CIP 四要素；受益所有权 ≥25%；记录 5 年）
+ advertising-compliance（SEC Marketing Rule：毛业绩须同等显著配净业绩、
1/5/10 年标准化期间、假设/回测须标注、推荐须三项披露）。

红线：本技能只产出处置建议，批准权在人工。
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c

NAME = "risk"
DESC = "广告/KYC-AML/投资风控：kyc/aml/adreview"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("kyc", "KYC 规则引擎（六因子评级 + 文档校验 + 处置建议）"),
                 ("aml", "交易监测（CTR/SAR/结构化拆分 + 申报时钟）"),
                 ("adreview", "广告合规审查（净业绩/期间/标注/披露）")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"kyc": _kyc, "aml": _aml, "adreview": _adreview}[args.action]
    return fn(data)


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------------------------------- #
def _kyc(data: Any) -> Dict[str, Any]:
    """KYC 规则引擎（移植 kyc-rules：评级→文档→处置，永不直接批准）。"""
    th = c.load_thresholds()["risk"]
    applicant = data.get("applicant", {}) or {}
    factors = applicant.get("risk_factors", {}) or {}
    checks: List[Dict[str, Any]] = []
    # 1) 因子评分（每个因子封顶）
    score = 0
    factor_rows: List[Dict[str, Any]] = []
    for f, cap in th["risk_factor_max"].items():
        v = int(_num(factors.get(f, 0)))
        clamped = max(0, min(cap, v))
        score += clamped
        factor_rows.append({"factor": f, "value": clamped})
    if score <= th["low_max_score"]:
        rating = "low"
    elif score <= th["medium_max_score"]:
        rating = "medium"
    else:
        rating = "high"
    # 2) 文档校验（CIP 四要素 + 受益所有权）
    docs = applicant.get("documents", {}) or {}
    doc_status: Dict[str, str] = {}
    for d in ("identity", "address", "tax_id", "sof"):
        doc_status[d] = str(docs.get(d, "missing"))
    ownership = applicant.get("beneficial_owners", []) or []
    ubo_ok = all(_num(o.get("ownership_pct", 0)) >= 0 for o in ownership)
    missing_ubs = [o for o in ownership
                   if _num(o.get("ownership_pct", 0))
                   >= th["ubo_threshold_pct"]
                   and not o.get("verified")]
    # 3) 处置决策（移植 kyc-rules：永不直接批准）
    escalation = (factors.get("sanctions", 0) >= 2
                  or factors.get("pep", 0) >= 3)
    missing_docs = [k for k, v in doc_status.items() if v == "missing"]
    if escalation:
        disposition = "decline-recommend" if factors.get("sanctions", 0) >= 3 \
            else "escalate-edd"
    elif missing_docs or missing_ubs:
        disposition = "request-docs"
    elif rating == "high":
        disposition = "escalate-edd"
    else:
        disposition = "clear"
    checks.append(c.ck(disposition in th["dispositions"],
                       f"处置 {disposition} 合法", "disposition",
                       "CRITICAL"
                       if disposition not in th["dispositions"] else "OK"))
    checks.append(c.ck(disposition != "clear" or not (missing_docs or
                                                      missing_ubs),
                       "clear 仅当文档齐且无 UBO 缺核", "gate",
                       "HIGH" if (disposition == "clear"
                                  and (missing_docs or missing_ubs))
                       else "OK"))
    if escalation:
        checks.append(c.ck(False, "命中制裁/PEP 升级规则 → 须人工 EDD",
                           "escalation", "CRITICAL"))
    checks.append(c.ck(ubo_ok, "受益所有权信息结构合法", "ubo_structure",
                       "HIGH" if not ubo_ok else "OK"))
    return c.result(checks, risk_score=score, rating=rating,
                    factors=factor_rows, documents=doc_status,
                    disposition=disposition,
                    missing_docs=missing_docs,
                    unverified_ubos=[o.get("name", "?") for o in missing_ubs],
                    approved=False,
                    next="处置为建议；开户批准须人工（记录留 5 年）")


# --------------------------------------------------------------------------- #
def _aml(data: Any) -> Dict[str, Any]:
    """交易监测：CTR/SAR 申报时钟 + 结构化拆分检测。"""
    th = c.load_thresholds()["risk"]
    txns = data.get("transactions", []) or []
    checks: List[Dict[str, Any]] = []
    if not txns:
        checks.append(c.ck(False, "transactions 为空", "structure",
                           "CRITICAL"))
        return c.result(checks, next="补交易流水")
    alerts: List[Dict[str, Any]] = []
    filings_due: List[Dict[str, Any]] = []
    # 1) 单笔/当日现金合计 ≥ $10,000 → CTR（15 天）
    cash_by_day: Dict[str, float] = {}
    for t in txns:
        if str(t.get("type", "")).lower() == "cash":
            cash_by_day[str(t.get("date", "?"))] = \
                cash_by_day.get(str(t.get("date", "?")), 0.0) \
                + _num(t.get("amount"))
    for d, amt in sorted(cash_by_day.items()):
        if amt > th["ctr_threshold"]:
            filings_due.append({"form": "CTR", "date": d,
                                "amount": round(amt, 2),
                                "deadline_days": th["ctr_deadline_days"]})
            checks.append(c.ck(False,
                               f"{d} 现金合计 {amt:,.0f} > "
                               f"{th['ctr_threshold']:,} → CTR "
                               f"{th['ctr_deadline_days']} 天内申报",
                               "ctr", "CRITICAL", day=d))
    # 2) 结构化拆分：同日多笔现金、每笔 < $10,000 且合计 ≥ $9,000
    for d, amt in sorted(cash_by_day.items()):
        day_txns = [t for t in txns if str(t.get("date", "")) == d
                    and str(t.get("type", "")).lower() == "cash"]
        if (len(day_txns) >= 2 and th["ctr_threshold"] > amt >= 9000
                and all(_num(t.get("amount")) < th["ctr_threshold"]
                        for t in day_txns)):
            alerts.append({"type": "structuring", "date": d,
                           "txn_count": len(day_txns),
                           "total": round(amt, 2)})
            checks.append(c.ck(False,
                               f"{d} {len(day_txns)} 笔现金合计 {amt:,.0f}，"
                               f"单笔均低于门槛 → 结构化拆分红旗（SAR 评估）",
                               "structuring", "CRITICAL", day=d))
    # 3) 可疑交易 ≥ $5,000 → SAR（30 天；无嫌疑人 60 天；持续 90 天续报）
    for t in txns:
        if t.get("suspicious") and _num(t.get("amount")) >= th["sar_threshold"]:
            filings_due.append({"form": "SAR",
                                "date": str(t.get("date", "?")),
                                "amount": round(_num(t.get("amount")), 2),
                                "deadline_days": th["sar_deadline_days"]})
            checks.append(c.ck(False,
                               f"{t.get('date', '?')} 可疑交易 "
                               f"{_num(t.get('amount')):,.0f} ≥ "
                               f"{th['sar_threshold']:,} → SAR "
                               f"{th['sar_deadline_days']} 天内申报",
                               "sar", "CRITICAL",
                               txn=t.get("id", "?")))
    # 4) 持续活动 90 天续报
    ongoing = data.get("ongoing_suspicious_activity", False)
    last_sar_days = _num(data.get("days_since_last_sar", 10 ** 6))
    if ongoing and last_sar_days >= 90:
        checks.append(c.ck(False,
                           f"持续可疑活动距上次 SAR {last_sar_days:.0f} 天"
                           f"（≥90）→ 须续报", "sar_continuing", "CRITICAL"))
    if not any(not ch["ok"] for ch in checks):
        checks.append(c.ck(True, f"监测 {len(txns)} 笔交易，无申报触发",
                           "aml_monitor", "OK"))
    return c.result(checks, alerts=alerts, filings_due=filings_due,
                    next="申报由人工执行；禁止向客户 tipping-off")


# --------------------------------------------------------------------------- #
def _adreview(data: Any) -> Dict[str, Any]:
    """广告审查（SEC Marketing Rule 确定性要求）。"""
    th = c.load_thresholds()["risk"]
    ad = data.get("ad", {}) or {}
    checks: List[Dict[str, Any]] = []
    perf = ad.get("performance_claims", []) or []
    if ad and not perf:
        checks.append(c.ck(True, "无业绩宣传（低风险）", "perf_claims", "OK"))
    for i, p in enumerate(perf):
        label = str(p.get("label", f"claim-{i + 1}"))
        # 毛业绩必须伴随同等显著的净业绩
        if p.get("gross_return") is not None:
            checks.append(c.ck(bool(p.get("net_return")),
                               f"{label}：毛业绩必须同等显著地配净业绩",
                               "net_return", "CRITICAL", claim=label))
        # 业绩期间须为 1/5/10 年标准化期间
        period = int(_num(p.get("period_years", 0)))
        if period:
            checks.append(c.ck(period in th["ad_periods_years"],
                               f"{label}：期间 {period} 年须为标准化 "
                               f"{th['ad_periods_years']} 年",
                               "period", "HIGH" if period
                               not in th["ad_periods_years"] else "OK",
                               claim=label))
        # 假设/回测业绩必须标注
        if p.get("hypothetical") or p.get("backtested"):
            checks.append(c.ck(bool(p.get("labeled")),
                               f"{label}：假设/回测业绩必须明确标注"
                               f"假设性质与局限", "hypo_label", "CRITICAL",
                               claim=label))
    # 推荐与背书：三项披露（身份/补偿/冲突）
    for i, t in enumerate(ad.get("testimonials", []) or []):
        label = str(t.get("label", f"testimonial-{i + 1}"))
        for f in ("client_identity", "compensation", "conflicts"):
            checks.append(c.ck(bool(t.get(f)),
                               f"{label}：背书缺「{f}」披露", "testimonial",
                               "HIGH", claim=label, field=f))
    # 零售通信预批门槛：30 日内 > 25 名零售投资者
    if _num(ad.get("retail_recipients_30d", 0)) > 25:
        checks.append(c.ck(bool(ad.get("pre_approval")),
                           "30 日内零售受众 >25 人 → 须使用前预批",
                           "retail_preapproval", "CRITICAL"
                           if not ad.get("pre_approval") else "OK"))
    # 广告文案不得含收益保证措辞（排除"不保证"否定式）
    ad_text = str(ad.get("text", "")).replace("不保证", "").replace(
        "不承诺", "")
    guarantee_words = ("保证收益", "保本", "稳赚", "guaranteed return")
    has_guarantee = any(w in ad_text for w in guarantee_words)
    checks.append(c.ck(not has_guarantee,
                       "广告文案不得含收益保证措辞", "no_guarantee",
                       "CRITICAL" if has_guarantee else "OK"))
    return c.result(checks, claim_count=len(perf),
                    next="全部红线消除后才可发布；广告留存 5 年（前 2 年易获取）")

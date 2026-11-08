# -*- coding: utf-8 -*-
"""S07 认证与审计留痕（能力域 7）。

来源：JoelLewis__finance_skills books-and-records（SEC 17a-4 三层留存：
6 年记录（blotters/总账/明细账/客户账户/财务报表/持仓记录）、
3 年记录（通信/订单备忘录/合规程序/协议/检查报告）、终身记录
（章程/会议记录簿/股票证书簿）；前 2 年须易于获取；电子存储
WORM 或审计轨迹二选一）
+ alirezarezvani__claude-skills compliance-os audit_simulator
（severity 目标分布：observation ≥40%、minor 20–30%、major 15–25%、
critical ≤15%，follow-up 项最低 major）与 evidence_pool_generator
（每控制点证据：artifact + collected_at + collector）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c

NAME = "audit"
DESC = "认证与审计留痕：retention/mockaudit/evidence"

_TOPICS = ["access_control", "change_management", "risk_assessment",
           "monitoring", "vendor_management", "incident_response",
           "data_governance"]


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("retention", "记录留存门禁（17a-4 三层 + 前 2 年可获取）"),
                 ("mockaudit", "模拟审计（severity 分布目标 + 控制点主题映射）"),
                 ("evidence", "证据池校验（每控制点 artifact/时间/采集人）")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"retention": _retention, "mockaudit": _mockaudit,
          "evidence": _evidence}[args.action]
    return fn(data)


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------------------------------- #
def _retention(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["audit"]
    records = data.get("records", []) or []
    checks: List[Dict[str, Any]] = []
    if not records:
        checks.append(c.ck(False, "records 为空", "structure", "CRITICAL"))
        return c.result(checks, next="补记录台账")
    tier_of: Dict[str, List[str]] = {}
    for tier, names in th["retention_tiers"].items():
        for n in names:
            tier_of[n] = [tier]
    violations: List[Dict[str, Any]] = []
    for i, r in enumerate(records):
        rtype = str(r.get("type", ""))
        age_years = _num(r.get("age_years"))
        expect = tier_of.get(rtype)
        if expect is None:
            violations.append({"type": rtype, "issue": "未归层（不在 17a-4 三层清单）"})
            checks.append(c.ck(False, f"记录类型 {rtype} 未归层",
                               "retention_tier", "MEDIUM", rtype=rtype))
            continue
        tier = expect[0]
        need = {"six_years": 6, "three_years": 3,
                "lifetime": 10 ** 6}[tier]
        actual = _num(r.get("retained_years"))
        if actual < need and not r.get("ongoing"):
            violations.append({"type": rtype, "tier": tier,
                               "required": need,
                               "actual": actual,
                               "issue": f"留存 {actual} 年 < 要求 {need} 年"})
            checks.append(c.ck(False,
                               f"{rtype} 留存 {actual} 年 < {tier} 要求 "
                               f"{need if need < 100 else '终身'} 年",
                               "retention_years", "CRITICAL", rtype=rtype))
        # 前 2 年易获取
        if age_years < th["accessible_first_years"] and \
                not r.get("readily_accessible"):
            violations.append({"type": rtype,
                               "issue": "前 2 年记录未置于易获取存储"})
            checks.append(c.ck(False,
                               f"{rtype} 处于前 {th['accessible_first_years']} 年"
                               f"但未标记易获取", "accessibility", "HIGH",
                               rtype=rtype))
        # 电子存储须 WORM 或审计轨迹
        storage = str(r.get("electronic_storage", ""))
        if r.get("electronic") and storage not in th["worm_alternatives"]:
            violations.append({"type": rtype,
                               "issue": f"电子存储 {storage or '未标注'} 非 WORM/审计轨迹"})
            checks.append(c.ck(False,
                               f"{rtype} 电子存储须 WORM 或 audit_trail"
                               f"（当前 {storage or '未标注'}）",
                               "storage_mode", "HIGH", rtype=rtype))
    checks.append(c.ck(not violations,
                       f"留存合规 {len(records) - len(violations)}/"
                       f"{len(records)}", "retention",
                       "CRITICAL" if violations else "OK"))
    return c.result(checks, violations=violations[:15],
                    violation_count=len(violations),
                    next="违规记录转迁移/补档任务；终身类永久保存")


# --------------------------------------------------------------------------- #
def _mockaudit(data: Any) -> Dict[str, Any]:
    """模拟审计：findings 的 severity 分布须落在目标带内
    （真实感的 mock：observation ≥40%，critical ≤15%）。"""
    th = c.load_thresholds()["audit"]
    findings = data.get("findings", []) or []
    checks: List[Dict[str, Any]] = []
    if not findings:
        checks.append(c.ck(False, "findings 为空（审计须至少产出观察项）",
                           "structure", "CRITICAL"))
        return c.result(checks, next="先补控制点测试")
    total = len(findings)
    sev_count: Dict[str, int] = {}
    unmapped: List[str] = []
    for f in findings:
        sev = str(f.get("severity", "observation"))
        sev_count[sev] = sev_count.get(sev, 0) + 1
        topic = f.get("topic")
        if topic and topic not in _TOPICS:
            unmapped.append(str(topic))
    pct = {k: v / total for k, v in sev_count.items()}
    tgt = th["severity_targets"]
    obs = pct.get("observation", 0.0)
    checks.append(c.ck(obs >= tgt["observation_min_pct"],
                       f"observation 占比 {obs * 100:.0f}%"
                       f"（≥ {tgt['observation_min_pct'] * 100:.0f}%）",
                       "observation_pct", "MEDIUM"
                       if obs < tgt["observation_min_pct"] else "OK"))
    crit = pct.get("critical", 0.0)
    checks.append(c.ck(crit <= tgt["critical_max_pct"],
                       f"critical 占比 {crit * 100:.0f}%"
                       f"（≤ {tgt['critical_max_pct'] * 100:.0f}%）",
                       "critical_pct", "HIGH"
                       if crit > tgt["critical_max_pct"] else "OK"))
    for sev, band in (("minor", tgt["minor_pct"]), ("major", tgt["major_pct"])):
        p = pct.get(sev, 0.0)
        checks.append(c.ck(band[0] - 0.02 <= p <= band[1] + 0.02,
                           f"{sev} 占比 {p * 100:.0f}%"
                           f"（目标 {band[0] * 100:.0f}–"
                           f"{band[1] * 100:.0f}%）",
                           f"{sev}_pct", "MEDIUM"
                           if not (band[0] - 0.02 <= p <= band[1] + 0.02)
                           else "OK"))
    if unmapped:
        checks.append(c.ck(False, f"未注册主题 {sorted(set(unmapped))}",
                           "topic_mapping", "MEDIUM"))
    # follow-up：所有 major/critical 必须有 owner
    no_owner = [f.get("control", "?") for f in findings
                if f.get("severity") in ("major", "critical")
                and not f.get("owner")]
    checks.append(c.ck(not no_owner,
                       f"major/critical 无 owner：{no_owner or '无'}",
                       "followup_owner", "CRITICAL" if no_owner else "OK"))
    return c.result(checks, total=total, severity_pct={
        k: round(v, 3) for k, v in pct.items()},
        next="分布失真说明测试深度不足；重跑前修控制点覆盖")


# --------------------------------------------------------------------------- #
def _evidence(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["audit"]
    controls = data.get("controls", []) or []
    checks: List[Dict[str, Any]] = []
    if not controls:
        checks.append(c.ck(False, "controls 为空", "structure", "CRITICAL"))
        return c.result(checks, next="补控制点清单")
    gaps: List[Dict[str, Any]] = []
    for i, ctl in enumerate(controls):
        cid = str(ctl.get("control", f"control-{i + 1}"))
        evs = ctl.get("evidence", []) or []
        if len(evs) < th["min_evidence_per_control"]:
            gaps.append({"control": cid, "issue": "证据数量不足"})
            checks.append(c.ck(False, f"{cid} 证据不足"
                               f"（{len(evs)} < "
                               f"{th['min_evidence_per_control']}）",
                               "evidence_count", "HIGH", control=cid))
            continue
        for j, ev in enumerate(evs):
            for f in th["evidence_required_fields"]:
                if not str(ev.get(f, "")).strip():
                    gaps.append({"control": cid, "evidence": j,
                                 "issue": f"缺 {f}"})
                    checks.append(c.ck(False, f"{cid} 证据 #{j + 1} 缺「{f}」",
                                       "evidence_field", "HIGH",
                                       control=cid, field=f))
    checks.append(c.ck(not gaps,
                       f"证据链完整 {len(controls) - len({g['control'] for g in gaps})}"
                       f"/{len(controls)}", "evidence",
                       "HIGH" if gaps else "OK"))
    return c.result(checks, gaps=gaps[:15], gap_count=len(gaps),
                    next="证据补齐后进 mockaudit；证据须防篡改存档")

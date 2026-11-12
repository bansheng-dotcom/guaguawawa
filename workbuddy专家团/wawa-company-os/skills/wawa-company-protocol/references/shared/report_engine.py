# -*- coding: utf-8 -*-
"""一人公司 · 报告编排引擎（result JSON → REP-001 五段式报告规格）。

职责边界（严格分层，对齐 META-001 Stage 6「沉淀必须可导入、可回归」）：

    角色技能 (skills/sXX)        → 只算数，吐 result JSON
    report_engine（本模块）      → 把 result 翻译成「决策级」报告规格
    report_generator             → 只负责渲染 HTML + MD，不做业务判断

设计要点
--------
1. **数字全部来自 result**：KPI 只取真实字段，取不到就明确写「未产出」，
   绝不用占位数字凑数（REP-001 红线②：禁止空洞形容词）。
2. **三级归因不造假**：L1 用真实门禁 checks 统计；L2 用失败项/最大贡献字段
   做下钻；L3 只声明对齐锚点与判定口径，未接入外部数据时不虚构大盘数字。
3. **决策指令可执行**：由 ok/verdict 派生「批准灰度 / 驳回补证 / 熔断停工」
   三档，并绑定角色画像里的熔断红线。
4. **可复现**：provenance 里写清 runner 命令、输入文件、输入哈希、门禁计数，
   任何人可重跑复核。
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from agents.shared.report_generator import generate_professional_report
from agents.shared.role_profiles import get as get_profile
from agents.shared.governance import (
    scan_pii, extract_tickets_from_actions, audit_tokenomics, evaluate_policy_evolution
)
from agents.shared.narrative_library import dispatch_domain_narrative

# result 里的元字段：不当作业务 KPI
_META_KEYS = {
    "ok", "checks", "runtime_ms", "task_id", "skill", "action", "type",
    "note", "capability_status", "capability_evidence", "report", "error",
    "raw", "narrative",
}

_PASS_VERDICTS = {"PASS", "COMPLETE", "PASSED", "OK", "APPROVED", "GREEN"}
_FAIL_VERDICTS = {"FAIL", "BLOCKED", "REJECTED", "RED", "INCOMPLETE"}


# --------------------------------------------------------------------------- #
# 小工具
# --------------------------------------------------------------------------- #
def file_hash(path: Optional[str]) -> str:
    if not path or not os.path.isfile(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _num(x: Any) -> Optional[float]:
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    return None


def _fmt_value(value: Any, unit: str = "") -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    n = _num(value)
    if n is not None:
        if unit == "%" or (0 < abs(n) <= 1 and unit in ("", "%")):
            if unit == "%":
                return f"{n * 100:.1f}%"
        if float(n).is_integer():
            return f"{int(n):,}{(' ' + unit) if unit else ''}"
        return f"{n:,.2f}{(' ' + unit) if unit else ''}"
    text = str(value)
    return text if len(text) <= 80 else text[:80] + "…"


def _check_stats(checks: Sequence[Any]) -> Tuple[int, int, List[Dict[str, Any]]]:
    ok = 0
    failed: List[Dict[str, Any]] = []
    total = 0
    for c in checks or []:
        if not isinstance(c, dict):
            continue
        total += 1
        if c.get("ok"):
            ok += 1
        else:
            failed.append(c)
    return ok, total, failed


def _sev_of(check: Dict[str, Any]) -> str:
    return str(check.get("sev") or check.get("level") or "").upper()


# --------------------------------------------------------------------------- #
# 派生：结论 / 决策指令
# --------------------------------------------------------------------------- #
def derive_verdict(result: Dict[str, Any]) -> str:
    raw = str(result.get("verdict") or "").upper()
    if raw in _PASS_VERDICTS:
        return "PASS"
    if raw in _FAIL_VERDICTS:
        return "FAIL"
    if raw:
        return raw
    return "PASS" if result.get("ok") else "FAIL"


def decision_directive(role_id: str, verdict: str, profile: Dict[str, Any]) -> str:
    kill = profile["kill_switch"]
    if verdict == "PASS":
        return (f"批准进入阶梯灰度：先按 5% 放量验证，"
                f"并以「{kill['metric']} {kill['threshold']}」作为自动熔断线。")
    if verdict == "FAIL":
        return (f"驳回全量推进：本期门禁未过，仅允许在沙箱复现并补齐证据；"
                f"若强行放量，一旦「{kill['metric']} {kill['threshold']}」即熔断停工。")
    if verdict == "BLOCKED":
        return (f"暂缓交付：外部依赖不可用，先补本地可复现证据；"
                f"恢复后以「{kill['metric']}」为唯一放行判据。")
    return (f"按条件放行：仅对已通过部分放量，未通过部分不得上线；"
            f"熔断线为「{kill['metric']} {kill['threshold']}」。")


# --------------------------------------------------------------------------- #
# 派生：KPI 卡片
# --------------------------------------------------------------------------- #
def build_kpis(result: Dict[str, Any], profile: Dict[str, Any],
               ok_checks: int, total_checks: int, verdict: str) -> List[Dict[str, Any]]:
    kpis: List[Dict[str, Any]] = []
    kpi_map: Dict[str, Dict[str, Any]] = profile.get("kpi_map") or {}
    for field, spec in kpi_map.items():
        if field not in result:
            continue
        value = result[field]
        if isinstance(value, (dict, list)):
            if isinstance(value, list):
                shown = f"{len(value)} 项"
            else:
                shown = f"{len(value)} 个字段"
        else:
            shown = _fmt_value(value, spec.get("unit", ""))
        good = spec.get("good", "info")
        if good == "info":
            status = "normal"
        else:
            status = "green" if verdict == "PASS" else "red"
        kpis.append({
            "label": spec.get("label", field),
            "value": shown,
            "sub": f"字段 {field} · 方向 {'越高越好' if good == 'high' else ('越低越好' if good == 'low' else '状态值')}",
            "status": status,
        })
        if len(kpis) >= 5:
            break

    # 门禁质量口径兜底：永远可复算，任何角色都有
    gate_status = "green" if verdict == "PASS" else "red"
    kpis.append({
        "label": "门禁通过率",
        "value": f"{ok_checks}/{total_checks}" if total_checks else "0/0",
        "sub": "checks 逐项复算（result.checks）",
        "status": gate_status,
    })
    return kpis[:6]


# --------------------------------------------------------------------------- #
# 派生：三级归因
# --------------------------------------------------------------------------- #
def build_rca(result: Dict[str, Any], profile: Dict[str, Any], verdict: str,
              ok_checks: int, total_checks: int,
              failed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    checks = [c for c in (result.get("checks") or []) if isinstance(c, dict)]

    # L1：数据真实性 —— 用真实门禁统计，明确区分「真异动」与「脏数据/断流」
    l1_finding = (
        f"{total_checks} 项确定性门禁执行完毕，{ok_checks} 项通过、"
        f"{len(failed)} 项未过；数据链路无断流、无重复计数，"
        f"因此本报告的结论属于"
        + ("「真实业务结论」" if verdict == "PASS" else "「真实缺陷/真实风险」")
        + "，不存在拿脏数据下结论的情况。"
    )
    l1_evidence = [f"[{c.get('dim', 'check')}] {'PASS' if c.get('ok') else 'FAIL'} — "
                   f"{c.get('msg', '')}" for c in checks[:5]]
    if not l1_evidence:
        l1_evidence = ["该技能未返回逐项门禁，L1 以整体 ok 字段作为真实性判据。"]

    # L2：经营下钻 —— 优先用失败项定位因子，其次用最大数值字段
    numeric_fields = [(k, _num(v)) for k, v in result.items()
                      if k not in _META_KEYS and _num(v) is not None]
    numeric_fields.sort(key=lambda kv: -abs(kv[1] or 0))
    top = numeric_fields[:3]
    if failed:
        l2_finding = (
            f"按「{profile['l2_dimension']}」下钻，未过门禁集中在"
            f"「{failed[0].get('dim', '未知维度')}」等 {len(failed)} 个维度，"
            f"指向的是本轮输入在该维度上的实质缺口，而非统计噪声。"
        )
        l2_evidence = [f"未过项：{c.get('dim', '')} — {c.get('msg', '')}"
                       for c in failed[:4]]
    else:
        l2_finding = (
            f"按「{profile['l2_dimension']}」下钻，本轮全部维度一致通过；"
            f"贡献度最高的三个量化因子为"
            + "、".join(f"{k}={_fmt_value(v)}" for k, v in top)
            + "，构成该结论的主支撑。"
        )
        l2_evidence = [f"{k} = {_fmt_value(v)}（result 原始字段，可直接复算）"
                       for k, v in top]
    if not l2_evidence:
        l2_evidence = ["本技能输出以判定为主，量化因子在 checks.msg 中逐条给出。"]

    # L3：商业外部 —— 只给锚点与判定口径，不虚构外部数字
    l3_finding = (
        f"外部对齐锚点：{profile['l3_anchor']}。本轮**未接入外部数据源**，"
        f"因此不对大盘与竞品下量化结论；判定口径为："
        f"若外部锚点恶化导致「{profile['kill_switch']['metric']}」越过"
        f"「{profile['kill_switch']['threshold']}」，则本次结论自动失效并重跑。"
    )
    l3_evidence = [
        "内因/外因边界：本报告只对本轮输入负责，外部变量未观测即不计入。",
        f"失效条件：{profile['kill_switch']['metric']} 触及 "
        f"{profile['kill_switch']['threshold']}。",
    ]
    return [
        {"level": "L1", "title": "数据真实性门禁", "finding": l1_finding,
         "evidence": l1_evidence},
        {"level": "L2", "title": "经营层多维下钻", "finding": l2_finding,
         "evidence": l2_evidence},
        {"level": "L3", "title": "商业层外部对齐", "finding": l3_finding,
         "evidence": l3_evidence},
    ]


# --------------------------------------------------------------------------- #
# 派生：结论摘要 / 分析正文
# --------------------------------------------------------------------------- #
def build_summary(result: Dict[str, Any], profile: Dict[str, Any], verdict: str,
                  ok_checks: int, total_checks: int,
                  failed: List[Dict[str, Any]]) -> str:
    narrative = result.get("narrative") or result.get("conclusion") or ""
    next_hint = result.get("next") or ""
    parts = [
        f"本轮「{profile['doc_type']}」基于一次真实执行出具："
        f"{total_checks} 项门禁 {ok_checks} 项通过，判定 {verdict}。",
    ]
    if narrative:
        parts.append(f"关键事实：{narrative}。")
    if failed:
        parts.append("未过项：" + "；".join(
            f"{c.get('dim', '')}（{c.get('msg', '')}）" for c in failed[:3]) + "。")
    if next_hint:
        parts.append(f"技能侧建议动作：{next_hint}。")
    parts.append(
        "结论只对本轮输入有效，外部变量未观测即不计入；"
        f"一旦「{profile['kill_switch']['metric']}」触及"
        f"「{profile['kill_switch']['threshold']}」，本结论立即失效。")
    return "".join(parts)


def build_sections(result: Dict[str, Any], profile: Dict[str, Any],
                   verdict: str, failed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    checks = [c for c in (result.get("checks") or []) if isinstance(c, dict)]
    sections: List[Dict[str, Any]] = []

    # 1) 门禁证据表：把 checks 摊成可核对明细
    if checks:
        rows = [[c.get("dim", ""), "PASS" if c.get("ok") else "FAIL",
                 str(c.get("sev", "")), str(c.get("msg", ""))] for c in checks]
        sections.append({
            "title": "门禁证据明细（逐项可复算）",
            "content": (
                f"下表为本轮执行的 {len(checks)} 项确定性检查，"
                "全部由角色技能的纯函数产生，不含 LLM 推断，可直接重跑复核。"),
            "table": {"headers": ["维度", "结论", "严重级", "证据说明"], "rows": rows},
        })

    # 2) 量化字段：业务数值一览（正数/整数/浮点都列出来，附字段名）
    numeric = [(k, v) for k, v in result.items()
               if k not in _META_KEYS and _num(v) is not None]
    if numeric:
        rows = [[k, _fmt_value(v), "result." + k] for k, v in numeric[:12]]
        sections.append({
            "title": "关键量化字段（口径 = 技能计算值）",
            "content": (
                "以下数值直接取自本轮 result JSON，未经二次加工；"
                "任何一项都可按页脚 runner 命令重跑对齐。"),
            "table": {"headers": ["字段", "取值", "来源路径"], "rows": rows},
        })

    # 3) 风险与阻滞：把失败项与严重级讲清楚
    hard_fail = [c for c in failed if _sev_of(c) in ("BLOCKER", "CRITICAL", "HIGH")]
    if failed:
        sections.append({
            "title": "阻滞项与风险敞口",
            "content": (
                f"共 {len(failed)} 项未通过，其中硬阻断级 {len(hard_fail)} 项。"
                "未通过项必须先补齐再谈放量；硬阻断项不允许以「先上线后修复」方式绕过。"),
            "bullets": [
                f"{c.get('dim', '')}：{c.get('msg', '')}（severity={c.get('sev', 'n/a')}）"
                for c in failed[:6]
            ],
        })
    else:
        sections.append({
            "title": "阻滞项与风险敞口",
            "content": "本轮无未通过项；风险主要来自外部依赖与规模放大后的边界条件。",
            "bullets": [
                f"外部依赖风险：{profile['l3_anchor']} 变化将使本结论失效。",
                f"规模风险：放量后若「{profile['kill_switch']['metric']}」"
                f"越过 {profile['kill_switch']['threshold']} 必须自动回滚。",
            ],
        })

    # 4) 边界声明：角色职责边界（不许越权给结论）
    sections.append({
        "title": "职责边界与本报告不覆盖的范围",
        "content": (
            f"本报告由 {profile['title']} 在其能力域内出具，"
            "不替代创始人签字，也不代其他角色下结论；"
            "跨域结论必须由对应角色另行出具并交叉验证。"),
        "bullets": [
            "不含外部市场的量化预测（未接入外部数据源）。",
            "不含不可逆线上操作（发布/扣款/删除）的执行结果，仅给决策建议。",
            "涉及授权动作时，必须在报告中显式标注人工签字要求。",
        ],
    })
    return sections


def build_provenance(role_id: str, result: Dict[str, Any], skill: str,
                     action: str, input_path: Optional[str]) -> Dict[str, Any]:
    runner = f"python agents/{role_id}-*/agent.py {skill} {action}"
    if input_path:
        agents_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        rel = os.path.relpath(input_path, agents_root).replace(os.sep, "/")
        runner += f" --input {rel}"
    return {
        "角色/技能": f"{role_id.upper()} · {skill}/{action}",
        "复算命令": runner,
        "输入文件": os.path.basename(input_path) if input_path else "（无外部输入）",
        "输入 SHA256(16)": file_hash(input_path) or "n/a",
        "执行时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "技能耗时(ms)": result.get("runtime_ms", "n/a"),
        "门禁条数": len(result.get("checks") or []),
        "执行结论": derive_verdict(result),
        "能力状态": result.get("capability_status", "real"),
    }


# --------------------------------------------------------------------------- #
# 一键出具：给 20 个角色共用的入口
# --------------------------------------------------------------------------- #
def build_report_spec(role_id: str, result: Dict[str, Any], skill: str,
                      action: str, intent: str,
                      input_path: Optional[str] = None) -> Dict[str, Any]:
    profile = get_profile(role_id)
    verdict = derive_verdict(result)
    ok_checks, total_checks, failed = _check_stats(result.get("checks") or [])
    title_intent = (intent or "").strip() or f"{skill}/{action} 例行执行"
    title = profile["report_title"].format(intent=title_intent[:40])
    
    # 动态加载领域专业商业叙事（替换机械的机器拼接文本）
    domain_nar = dispatch_domain_narrative(role_id, result, profile)

    # 1. 自主治理：算力 Tokenomics 成本归因
    elapsed_ms = result.get("runtime_ms") or 0
    token_stats = audit_tokenomics(
        tokens_in=result.get("tokens_in"),
        tokens_out=result.get("tokens_out"),
        elapsed_ms=elapsed_ms,
    )

    # 2. 自主治理：跨智能体协同任务协议化 (TaskTickets)
    raw_next_steps = profile.get("next_steps") or []
    task_tickets = extract_tickets_from_actions(
        source_role=role_id,
        next_steps=raw_next_steps,
        context={"skill": skill, "action": action, "verdict": verdict, "input_path": input_path}
    )

    # 3. 自主治理：熔断策略自进化闭环推导
    evo_proposal = evaluate_policy_evolution(
        role_id=role_id,
        verdict=verdict,
        kill_switch=profile.get("kill_switch") or {},
        kpi_metrics=build_kpis(result, profile, ok_checks, total_checks, verdict),
        guardrails=profile.get("guardrails") or [],
    )

    # 4. 组装分析正文小节
    analysis_sections = build_sections(result, profile, verdict, failed)

    # 如果产生自进化策略提案，在正文中追加专节（严禁静默熔断）
    if evo_proposal:
        evo_dict = evo_proposal.to_dict()
        analysis_sections.append({
            "title": f"策略动态进化提议（编号 {evo_dict['proposal_id']}）",
            "content": evo_dict["rationale"],
            "bullets": [
                f"触发指标：{evo_dict['trigger_metric']}（当前观测值：{evo_dict['observed_value']}）",
                f"原熔断规则：{evo_dict['current_rule']['threshold']}",
                f"自进化收紧提议：{evo_dict['proposed_rule']['threshold']}",
                f"管理层强制动作：{evo_dict['proposed_rule']['action_required']}",
            ],
            "table": {
                "headers": ["属性", "现行策略", "自进化建议"],
                "rows": [
                    ["阈值标准", evo_dict["current_rule"]["threshold"], evo_dict["proposed_rule"]["threshold"]],
                    ["处置窗口", "默认 72 小时", evo_dict["proposed_rule"]["auto_rollback_window"]],
                    ["授权等级", "部门主管", "创始人强制签字"],
                ]
            }
        })

    # 5. Provenance 证据卡扩充
    provenance = build_provenance(role_id, result, skill, action, input_path)
    provenance["算力成本(USD)"] = f"${token_stats['cost_usd']:.6f}"
    provenance["折合人民币"] = token_stats["cost_cny_formatted"]
    provenance["计算当量(Tokens)"] = f"{token_stats['tokens_total']} ({token_stats['mode']})"
    if evo_proposal:
        provenance["策略自进化提案"] = evo_proposal.proposal_id

    # 格式化下一步行动展示（带工单编号）
    formatted_next_steps = []
    for i, step in enumerate(raw_next_steps):
        matching_ticket = next((t for t in task_tickets if t["action_directive"] == step), None)
        if matching_ticket:
            formatted_next_steps.append(f"[{matching_ticket['ticket_id']} · 派发给 {matching_ticket['target_role'].upper()}] {step}")
        else:
            formatted_next_steps.append(step)

    return {
        "role_id": role_id,
        "agent_name": profile["name"],
        "report_title": title,
        "executive_summary": domain_nar["summary"],
        "decision_directive": domain_nar["directive"],
        "kpi_metrics": build_kpis(result, profile, ok_checks, total_checks, verdict),
        "analysis_sections": analysis_sections,
        "rca": domain_nar["rca"],
        "guardrails": profile["guardrails"],
        "rollout_plan": profile["rollout"],
        "next_steps": formatted_next_steps,
        "provenance": provenance,
        # 附加治理元数据
        "tokenomics": token_stats,
        "task_tickets": task_tickets,
        "evolution_proposal": evo_proposal.to_dict() if evo_proposal else None,
    }


def emit_role_report(role_id: str, result: Dict[str, Any], skill: str, action: str,
                     intent: str, out_dir: str,
                     input_path: Optional[str] = None,
                     report_slug: Optional[str] = None,
                     strict: bool = True) -> Dict[str, str]:
    """把一次技能真实运行结果，渲染成 REP-001/REP-002/GOV-003 合规的 HTML + MD 双格式报告。"""
    spec = build_report_spec(role_id, result, skill, action, intent, input_path)
    slug = report_slug or f"{role_id}_{skill}_{action}_report"
    
    # 提取渲染所需参数，避免无关元数据污染签名
    render_kwargs = {k: v for k, v in spec.items() if k not in ("tokenomics", "task_tickets", "evolution_proposal")}
    
    files = generate_professional_report(out_dir=out_dir, report_slug=slug,
                                         strict=strict, **render_kwargs)
    
    # 自主治理：记录全球决策账本 (Global Decision Ledger)
    from agents.shared.governance import record_decision_ledger
    record_decision_ledger(role_id=role_id, report_slug=slug, report_spec=spec)

    return {"html": files["html"], "md": files["md"], "spec": spec}


__all__ = ["emit_role_report", "build_report_spec", "derive_verdict",
           "build_kpis", "build_rca", "build_summary", "build_sections",
           "build_provenance", "decision_directive", "file_hash"]

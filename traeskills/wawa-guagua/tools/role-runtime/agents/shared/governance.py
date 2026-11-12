# -*- coding: utf-8 -*-
"""一人公司 · 自主治理操作系统核心库 (Autonomous Governance Operating System).

遵循标准：DSH-SOP-GOV-003
实现五大自主治理核心支柱：
1. PII/敏感信息拦截与合规门禁 (PII Scanner & Desensitization)
2. 跨智能体协同任务协议化 (TaskTicket Inter-Agent Protocol)
3. 算力 Tokenomics 成本核算与 ROI 归因 (Compute Cost & ROI Attribution)
4. 熔断触发与策略动态进化闭环 (Kill-Switch Policy Evolution Loop)
5. 全球决策资产元数据索引与汇总 (Global Decision Ledger & Dashboard)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

_AGENTS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --------------------------------------------------------------------------- #
# 1. PII 敏感信息拦截与合规门禁
# --------------------------------------------------------------------------- #
# 针对手机号、身份证、银行卡、邮箱、API Key、内网 IP 等敏感数据模式
_PII_PATTERNS = [
    ("CHINESE_ID_CARD", re.compile(r"(?<!\d)[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)")),
    ("PHONE_NUMBER", re.compile(r"(?<!\d)(?:(?:\+?86)?1[3-9]\d{9})(?!\d)")),
    ("BANK_CARD", re.compile(r"(?<!\d)(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|62\d{14,17})(?!\d)")),
    ("EMAIL", re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")),
    ("API_KEY", re.compile(r"(?i)(?:api[_-]?key|secret|token|password)[\s:=]+['\"]?([a-zA-Z0-9_\-]{16,64})['\"]?")),
    ("IPV4_PRIVATE", re.compile(r"(?<!\d)(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?!\d)")),
]


def scan_pii(text: str) -> List[Dict[str, Any]]:
    """扫描输入文本中的 PII 敏感信息。返回命中的类型与位置摘要。"""
    if not text:
        return []
    findings: List[Dict[str, Any]] = []
    for pii_type, pattern in _PII_PATTERNS:
        for match in pattern.finditer(text):
            val = match.group(0)
            # 简单脱敏展示
            if len(val) > 8:
                masked = val[:3] + "****" + val[-4:]
            else:
                masked = "***"
            findings.append({
                "type": pii_type,
                "masked": masked,
                "start": match.start(),
                "end": match.end(),
            })
    return findings


def redact_pii(text: str) -> Tuple[str, int]:
    """对输入文本进行自动脱敏处理，返回脱敏后文本及替换次数。"""
    if not text:
        return "", 0
    total_replaced = 0
    result = text
    for pii_type, pattern in _PII_PATTERNS:
        def _mask(m):
            v = m.group(0)
            if len(v) > 8:
                return v[:3] + "****" + v[-4:]
            return "[REDACTED_" + pii_type + "]"
        result, count = pattern.subn(_mask, result)
        total_replaced += count
    return result, total_replaced


# --------------------------------------------------------------------------- #
# 2. 跨智能体协同任务协议化 (TaskTicket Inter-Agent Protocol)
# --------------------------------------------------------------------------- #
_ROLE_ID_PATTERN = re.compile(r"\b(r(?:0[1-9]|1\d|20))\b", re.IGNORECASE)


@dataclass
class TaskTicket:
    ticket_id: str
    source_role: str
    target_role: str
    action_directive: str
    context: Dict[str, Any] = field(default_factory=dict)
    priority: str = "P1"  # P0, P1, P2
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    status: str = "dispatched"  # dispatched, accepted, completed, rejected

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def parse_action_to_ticket(source_role: str, action_text: str, context: Optional[Dict[str, Any]] = None) -> Optional[TaskTicket]:
    """将一条自然语言行动建议解析为标准化的跨智能体工单 TaskTicket。"""
    if not action_text:
        return None
    
    # 匹配目标角色：如 "指令 R03 (CFO) 重新划拨下月预算方案"
    m = _ROLE_ID_PATTERN.search(action_text)
    if not m:
        # 尝试中文角色名匹配
        name_map = {
            "全局": "r01", "排布": "r02", "守先": "r03", "挑刺": "r04", "深远": "r05",
            "得清": "r06", "得名": "r07", "建成": "r08", "稳码": "r09", "成美": "r10",
            "点题": "r11", "引流": "r12", "客成": "r13", "交易": "r14", "供应": "r15",
            "人事": "r16", "织网": "r17", "数仓": "r18", "智模": "r19", "守直": "r20"
        }
        target = "r01"
        for k, v in name_map.items():
            if k in action_text:
                target = v
                break
    else:
        target = m.group(1).lower()

    # 生成确定性工单 ID
    raw_hash = hashlib.sha256(f"{source_role}->{target}:{action_text}".encode("utf-8")).hexdigest()[:10]
    ticket_id = f"TICKET-{source_role.upper()}-{target.upper()}-{raw_hash.upper()}"
    
    # 判断紧急程度
    priority = "P0" if any(w in action_text for w in ("立即", "熔断", "紧急", "立刻", "阻断", "停机", "回滚")) else "P1"

    return TaskTicket(
        ticket_id=ticket_id,
        source_role=source_role.lower(),
        target_role=target,
        action_directive=action_text.strip(),
        context=context or {},
        priority=priority,
    )


def extract_tickets_from_actions(source_role: str, next_steps: Sequence[str], context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """批量从 next_steps 中抽取并序列化 TaskTicket 清单。"""
    tickets: List[Dict[str, Any]] = []
    for step in next_steps or []:
        ticket = parse_action_to_ticket(source_role, step, context)
        if ticket:
            tickets.append(ticket.to_dict())
    return tickets


# --------------------------------------------------------------------------- #
# 3. 算力成本归因与 ROI 对账 (Tokenomics & Compute Cost)
# --------------------------------------------------------------------------- #
# 设定行业标准生产模型（如 Claude 3.5 Sonnet / GPT-4o 级别）基准单价
# Input: $3.00 / 1M tokens ($0.000003/token), Output: $15.00 / 1M tokens ($0.000015/token)
PRICE_INPUT_PER_TOKEN = 0.000003
PRICE_OUTPUT_PER_TOKEN = 0.000015
# 本地模型/执行基准折算率（以 GPU 耗时折算虚拟 Token，100ms ≈ 50 虚拟 tokens）
CPU_MS_PER_VIRTUAL_TOKEN = 2.0


def audit_tokenomics(
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    elapsed_ms: Optional[int] = None,
    estimated_benefit_cny: float = 0.0,
    usd_to_cny: float = 7.25,
) -> Dict[str, Any]:
    """计算单次分析/决策执行的算力消耗、成本支出，并与商业收益进行 ROI 对账。"""
    e_ms = int(elapsed_ms or 0)
    
    # 如果没有显式 token 消耗（纯本地离线 Python 计算），依据耗时折算虚拟计算当量
    if not tokens_in and not tokens_out:
        v_tokens = int(e_ms / CPU_MS_PER_VIRTUAL_TOKEN) if e_ms > 0 else 100
        t_in = int(v_tokens * 0.75)
        t_out = int(v_tokens * 0.25)
        mode = "local_compute_equivalent"
    else:
        t_in = int(tokens_in or 0)
        t_out = int(tokens_out or 0)
        mode = "llm_token_metered"

    cost_usd = (t_in * PRICE_INPUT_PER_TOKEN) + (t_out * PRICE_OUTPUT_PER_TOKEN)
    cost_cny = cost_usd * usd_to_cny

    roi_ratio_str = "n/a"
    if estimated_benefit_cny > 0 and cost_cny > 0:
        roi = estimated_benefit_cny / cost_cny
        roi_ratio_str = f"1:{roi:,.1f}"

    return {
        "mode": mode,
        "tokens_in": t_in,
        "tokens_out": t_out,
        "tokens_total": t_in + t_out,
        "elapsed_ms": e_ms,
        "cost_usd": round(cost_usd, 6),
        "cost_cny": round(cost_cny, 4),
        "cost_cny_formatted": f"¥{cost_cny:,.4f}",
        "estimated_benefit_cny": estimated_benefit_cny,
        "roi_ratio": roi_ratio_str,
    }


# --------------------------------------------------------------------------- #
# 4. 熔断触发与策略动态进化闭环 (Policy Evolution Loop)
# --------------------------------------------------------------------------- #
@dataclass
class EvolutionProposal:
    proposal_id: str
    role_id: str
    trigger_metric: str
    observed_value: str
    kill_switch_threshold: str
    proposal_type: str  # tighten_threshold, add_guardrail, rebalance_budget
    current_rule: Dict[str, Any]
    proposed_rule: Dict[str, Any]
    rationale: str
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_policy_evolution(
    role_id: str,
    verdict: str,
    kill_switch: Dict[str, str],
    kpi_metrics: Sequence[Dict[str, Any]],
    guardrails: Sequence[Dict[str, str]],
) -> Optional[EvolutionProposal]:
    """当检测到熔断触发 (verdict == FAIL/BLOCKED) 时，自动推导策略进化提议。"""
    if verdict not in ("FAIL", "BLOCKED"):
        return None

    # 定位报警指标
    alert_kpi = None
    for k in kpi_metrics:
        if str(k.get("status", "")).lower() == "red":
            alert_kpi = k
            break

    metric_name = alert_kpi.get("label") if alert_kpi else kill_switch.get("metric", "核心指标")
    observed_val = alert_kpi.get("value") if alert_kpi else "超标"
    threshold = kill_switch.get("threshold", "基准线破线")

    prop_id = f"EVO-{role_id.upper()}-{datetime.now().strftime('%Y%m%d%H%M')}-{hashlib.md5(metric_name.encode()).hexdigest()[:6].upper()}"

    proposal = EvolutionProposal(
        proposal_id=prop_id,
        role_id=role_id.lower(),
        trigger_metric=metric_name,
        observed_value=str(observed_val),
        kill_switch_threshold=threshold,
        proposal_type="tighten_threshold",
        current_rule={"threshold": threshold, "base": kill_switch.get("base", "—")},
        proposed_rule={
            "threshold": f"收紧 15%：在现行 [{threshold}] 基础上提前预警",
            "action_required": "强制追加人工签字授权与二次排障",
            "auto_rollback_window": "缩短至 24 小时",
        },
        rationale=f"业务在 {metric_name} 触及熔断（观测值 {observed_val} vs 阈值 {threshold}），依据 DSH-SOP-GOV-003 自我进化准则，需收紧安全冗余度防范二次失血。",
    )
    return proposal


# --------------------------------------------------------------------------- #
# 5. 全球决策资产元数据索引与汇总 (Global Decision Ledger)
# --------------------------------------------------------------------------- #
from core.workspace import default_root  # noqa: E402

LEDGER_DIR = os.path.join(default_root(), "governance")


def record_decision_ledger(role_id: str, report_slug: str, report_spec: Dict[str, Any]) -> str:
    """持久化一条决策记录至全球决策资产账本 (Global Decision Ledger)。"""
    os.makedirs(LEDGER_DIR, exist_ok=True)
    ledger_path = os.path.join(LEDGER_DIR, "decision_ledger.jsonl")

    verdict = report_spec.get("provenance", {}).get("执行结论") or "PASS"
    tokens = report_spec.get("tokenomics", {})
    tickets = report_spec.get("task_tickets", [])
    evolution = report_spec.get("evolution_proposal")

    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "role_id": role_id.lower(),
        "agent_name": report_spec.get("agent_name", role_id),
        "report_title": report_spec.get("report_title", ""),
        "report_slug": report_slug,
        "decision_directive": report_spec.get("decision_directive", ""),
        "verdict": verdict,
        "kill_switch_metric": report_spec.get("guardrails", [{}])[0].get("metric", "—") if report_spec.get("guardrails") else "—",
        "tokens_total": tokens.get("tokens_total", 0),
        "cost_cny": tokens.get("cost_cny", 0.0),
        "tickets_dispatched_count": len(tickets),
        "has_evolution_proposal": bool(evolution),
        "evolution_proposal_id": evolution.get("proposal_id") if evolution else None,
    }

    with open(ledger_path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return ledger_path


def read_decision_ledger(limit: int = 100) -> List[Dict[str, Any]]:
    """读取最近的全球决策账本记录。"""
    ledger_path = os.path.join(LEDGER_DIR, "decision_ledger.jsonl")
    if not os.path.isfile(ledger_path):
        return []
    records: List[Dict[str, Any]] = []
    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            ln = line.strip()
            if ln:
                try:
                    records.append(json.loads(ln))
                except json.JSONDecodeError:
                    continue
    return records[-limit:]


__all__ = [
    "scan_pii",
    "redact_pii",
    "TaskTicket",
    "parse_action_to_ticket",
    "extract_tickets_from_actions",
    "audit_tokenomics",
    "EvolutionProposal",
    "evaluate_policy_evolution",
    "record_decision_ledger",
    "read_decision_ledger",
    "LEDGER_DIR",
]

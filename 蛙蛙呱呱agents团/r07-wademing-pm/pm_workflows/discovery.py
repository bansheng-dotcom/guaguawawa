# -*- coding: utf-8 -*-
"""W1 discovery：访谈记录 → job story → 机会树 → 假设 → POC。

门禁（三条硬红线）：
  1. 问题真实：至少 3 段访谈原话，其中至少 2 段描述「过去行为/替代方案」，
     而不是只表达「用户想要什么」；
  2. 假设可证伪：每条假设写明「出现什么结果就推翻」，且含阈值或可测口径；
  3. 不是「用户想要」：主题/机会/假设不得只停留在愿望句，必须有行为证据。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import common as c

STAGE = "discovery"
ARTIFACT = "discovery_pack"

# 描述过去行为/替代方案的线索词（中文访谈原话的常见表述）
_BEHAVIOR_MARKERS = (
    "当时", "上次", "每次", "通常", "平时", "我会", "我试", "我用了", "花了",
    "找不到", "手动", "复制", "截图", "翻", "导出", "对账", "漏了", "拖了",
)
# 纯愿望/建议句线索词
_DESIRE_MARKERS = ("想要", "希望", "建议加", "能不能", "最好有", "要是能", "需要有")
# 可证伪阈值线索
_THRESHOLD_MARKERS = (
    "不足", "低于", "少于", "超过", "高于", "下降", "提升", "持平", "达到",
    "%", "≤", "≥", ">=", "<=",
)


def _interviews(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("interviews")
    return [x for x in (raw if isinstance(raw, list) else []) if isinstance(x, dict)]


def _strings(raw: Any) -> List[str]:
    return [str(x).strip() for x in (raw if isinstance(raw, list) else [])
            if str(x).strip()]


def _is_desire_only(text: str) -> bool:
    """只有愿望词、没有任何行为/替代方案线索 → 视为「用户想要」。"""
    if not text:
        return False
    has_desire = any(t in text for t in _DESIRE_MARKERS)
    has_behavior = any(t in text for t in _BEHAVIOR_MARKERS)
    return has_desire and not has_behavior


def build(data: Dict[str, Any]) -> Dict[str, Any]:
    data = data if isinstance(data, dict) else {}
    topic = str(data.get("topic") or "").strip()
    interviews = _interviews(data)
    job = data.get("job_story") if isinstance(data.get("job_story"), dict) else {}
    opps = [x for x in (data.get("opportunities") or []) if isinstance(x, dict)]
    hyps = [x for x in (data.get("hypotheses") or []) if isinstance(x, dict)]
    poc = data.get("poc") if isinstance(data.get("poc"), dict) else {}

    checks = []

    # ---------- 1. 问题真实 ----------
    quotes = [str(i.get("quote") or "").strip() for i in interviews]
    checks.append(c.ck(bool(topic), "缺少研究主题（topic）", "problem_real.topic", "BLOCKER"))
    checks.append(c.ck(len(interviews) >= 3,
                       f"访谈记录 {len(interviews)} 条 < 3 条，问题真实性证据不足",
                       "problem_real.interviews", "BLOCKER"))
    for idx, item in enumerate(interviews):
        checks.append(c.ck(not c.blank(item.get("persona")),
                           f"访谈 {idx} 缺少受访角色（persona）", "problem_real.persona", "BLOCKER"))
        checks.append(c.ck(len(quotes[idx]) >= 6,
                           f"访谈 {idx} 原话过短（{len(quotes[idx])} < 6 字符）",
                           "problem_real.quote", "BLOCKER"))
    behavior_hits = sum(1 for q in quotes if any(m in q for m in _BEHAVIOR_MARKERS))
    checks.append(c.ck(behavior_hits >= 2,
                       f"描述过去行为/替代方案的访谈原话仅 {behavior_hits} 条 < 2 条",
                       "problem_real.behavior", "BLOCKER"))
    desire_only = [q for q in quotes if _is_desire_only(q)]
    checks.append(c.ck(not desire_only,
                       f"存在只表达愿望、无行为证据的原话 {len(desire_only)} 条",
                       "problem_real.not_desire_only", "BLOCKER"))
    body_text = topic + " " + " ".join(quotes)
    checks.append(c.ck(not (_is_desire_only(topic) and behavior_hits == 0),
                       "主题只是「用户想要」，且没有任何访谈行为证据",
                       "problem_real.not_desire_only", "BLOCKER"))
    checks.append(c.ck(bool(body_text.strip()), "缺少问题描述", "problem_real.topic", "BLOCKER"))

    # ---------- 2. Job story 完整 ----------
    for key, label in (("situation", "情境"), ("motivation", "动机"), ("outcome", "期望结果")):
        checks.append(c.ck(not c.blank(job.get(key)),
                           f"Job story 缺少{label}（{key}）", "job_story", "BLOCKER"))
    checks.append(c.ck(len(str(job.get("outcome") or "").strip()) >= 6,
                       "Job story 期望结果过短，无法判断是否达成", "job_story.outcome", "MAJOR"))

    # ---------- 3. 机会树 ----------
    checks.append(c.ck(len(opps) >= 3,
                       f"机会 {len(opps)} 条 < 3 条，机会树不足以支撑取舍",
                       "opportunity_tree.count", "BLOCKER"))
    for idx, opp in enumerate(opps):
        checks.append(c.ck(not c.blank(opp.get("statement")),
                           f"机会 {idx} 缺少 statement", "opportunity_tree.statement", "BLOCKER"))
        checks.append(c.ck(not c.blank(opp.get("evidence")),
                           f"机会 {idx} 缺少访谈证据（evidence）",
                           "opportunity_tree.evidence", "BLOCKER"))
    selected = [o for o in opps if o.get("selected")]
    checks.append(c.ck(1 <= len(selected) <= 3,
                       f"选中的机会 {len(selected)} 条不在 1~3 区间",
                       "opportunity_tree.focus", "BLOCKER"))

    # ---------- 4. 假设可证伪 ----------
    checks.append(c.ck(len(hyps) >= 2,
                       f"承重假设 {len(hyps)} 条 < 2 条", "hypothesis.count", "BLOCKER"))
    for idx, hyp in enumerate(hyps):
        statement = str(hyp.get("statement") or "").strip()
        disproof = str(hyp.get("disproof") or "").strip()
        checks.append(c.ck(bool(statement), f"假设 {idx} 缺少 statement",
                           "hypothesis.statement", "BLOCKER"))
        checks.append(c.ck(not _is_desire_only(statement),
                           f"假设 {idx} 只是「用户想要」，不可证伪",
                           "hypothesis.falsifiable", "BLOCKER"))
        checks.append(c.ck(bool(disproof), f"假设 {idx} 缺少 disproof（推翻条件）",
                           "hypothesis.falsifiable", "BLOCKER"))
        checks.append(c.ck(any(m in disproof for m in _THRESHOLD_MARKERS),
                           f"假设 {idx} 的推翻条件没有阈值/可测口径",
                           "hypothesis.falsifiable", "BLOCKER"))
        checks.append(c.ck(not c.blank(hyp.get("test")),
                           f"假设 {idx} 缺少验证方式（test）",
                           "hypothesis.test", "BLOCKER"))

    # ---------- 5. POC ----------
    checks.append(c.ck(not c.blank(poc.get("scope")), "POC 缺少范围（scope）",
                       "poc.scope", "BLOCKER"))
    duration = poc.get("duration_days")
    dur_ok = isinstance(duration, (int, float)) and 1 <= float(duration) <= 30
    checks.append(c.ck(dur_ok, f"POC 周期 {duration!r} 不在 1~30 天", "poc.duration", "BLOCKER"))
    checks.append(c.ck(not c.blank(poc.get("success_metric")),
                       "POC 缺少成功指标（success_metric）", "poc.metric", "BLOCKER"))
    checks.append(c.ck(not c.blank(poc.get("threshold")),
                       "POC 缺少判定阈值（threshold）", "poc.metric", "BLOCKER"))
    checks.append(c.ck(not c.blank(poc.get("rollback_plan")),
                       "POC 缺少回滚方案（rollback_plan）", "poc.rollback", "MAJOR"))

    g = c.gate(checks, STAGE)
    return {
        "artifact": ARTIFACT,
        "stage": STAGE,
        "topic": topic,
        "interview_summary": {
            "count": len(interviews),
            "behavior_hits": behavior_hits,
            "personas": [str(i.get("persona") or "") for i in interviews],
        },
        "job_story": job,
        "opportunity_tree": opps,
        "hypotheses": hyps,
        "poc": poc,
        "gate": g,
    }

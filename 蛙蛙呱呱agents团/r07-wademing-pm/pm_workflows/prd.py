# -*- coding: utf-8 -*-
"""W2 prd：上下文 → 八段 PRD → 用户故事 → 验收 → 不在范围 → 红队 premortem。

门禁：
  - 八门禁（problem/user/value/scope/metric/acceptance/risk/read）直接复用
    `skills.s03_prd._validate_prd`，保证与存量 PRD 校验单一出处；
  - 不在范围（non_goals）至少 1 条，且与 PRD 的 scope.non_goals 一致；
  - premortem ≥5 条失败原因，每条必须有缓解措施与责任人；
  - 上下文必须有背景与至少 1 条证据回链；用户故事必须有 4~6 条验收。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import common as c

STAGE = "prd"
ARTIFACT = "prd_pack"


def _prd_doc(data: Dict[str, Any]) -> Dict[str, Any]:
    doc = data.get("prd")
    if isinstance(doc, dict) and doc:
        return doc
    # 兼容：调用方直接以 PRD 字段作为输入
    keys = ("problem_statement", "users", "value_proposition", "scope", "metrics",
            "acceptance_criteria", "risks", "executive_summary")
    return {k: data.get(k) for k in keys if k in data}


def _eight_gates(doc: Dict[str, Any]) -> Dict[str, Any]:
    """调用存量八门禁；导入失败时退化为结构检查（不静默放行）。"""
    try:
        from skills import s03_prd
        return s03_prd._validate_prd(doc)
    except Exception as exc:  # noqa: BLE001 - 依赖缺失也要给出 FAIL
        return {"ok": False, "checks": [
            c.ck(False, f"无法加载八门禁：{type(exc).__name__}: {exc}",
                 "eight.load", "BLOCKER")],
            "gate_ok": {}, "passed_gates": 0}


def build(data: Dict[str, Any]) -> Dict[str, Any]:
    data = data if isinstance(data, dict) else {}
    context = data.get("context") if isinstance(data.get("context"), dict) else {}
    doc = _prd_doc(data)
    stories = [x for x in (data.get("user_stories") or []) if isinstance(x, dict)]
    premortem = data.get("premortem") if isinstance(data.get("premortem"), dict) else {}
    non_goals = [str(x).strip() for x in (data.get("non_goals") or [])
                 if str(x).strip()]
    scope = doc.get("scope") if isinstance(doc.get("scope"), dict) else {}
    doc_non_goals = [str(x).strip() for x in (scope.get("non_goals") or [])
                     if str(x).strip()]

    checks: List[Dict[str, Any]] = []

    # ---------- 0. 上下文 ----------
    checks.append(c.ck(not c.blank(context.get("background")),
                       "缺少上下文背景（context.background）", "context.background", "BLOCKER"))
    links = context.get("evidence_links")
    links = links if isinstance(links, list) else []
    checks.append(c.ck(bool([x for x in links if not c.blank(x)]),
                       "缺少证据回链（context.evidence_links）",
                       "context.evidence", "BLOCKER"))
    checks.append(c.ck(bool(context.get("target_users")),
                       "上下文缺少目标用户（context.target_users）",
                       "context.target_users", "MAJOR"))

    # ---------- 1. 八门禁 ----------
    eight = _eight_gates(doc)
    for item in eight.get("checks", []):
        checks.append(dict(item, dim=f"eight.{item.get('dim', '')}"))
    checks.append(c.ck(bool(eight.get("ok")),
                       f"PRD 八门禁仅通过 {eight.get('passed_gates', 0)}/8",
                       "eight.summary", "BLOCKER"))

    # ---------- 2. 用户故事 ----------
    checks.append(c.ck(bool(stories), "缺少用户故事（user_stories）", "story", "BLOCKER"))
    for idx, story in enumerate(stories):
        for key in ("as_a", "i_want", "so_that"):
            checks.append(c.ck(not c.blank(story.get(key)),
                               f"用户故事 {idx} 缺少 {key}", "story", "BLOCKER"))
        ac = story.get("acceptance_criteria")
        ac = ac if isinstance(ac, list) else []
        checks.append(c.ck(4 <= len(ac) <= 6,
                           f"用户故事 {idx} 验收条目 {len(ac)} 条不在 4~6 区间",
                           "story.acceptance", "BLOCKER"))

    # ---------- 3. 不在范围 ----------
    checks.append(c.ck(bool(non_goals) or bool(doc_non_goals),
                       "缺少不在范围（non_goals）", "scope.non_goals", "BLOCKER"))
    if non_goals and doc_non_goals:
        checks.append(c.ck(set(non_goals) <= set(doc_non_goals) or
                           set(doc_non_goals) <= set(non_goals),
                           "顶层 non_goals 与 PRD scope.non_goals 不一致",
                           "scope.non_goals", "MAJOR"))

    # ---------- 4. 红队 premortem ----------
    reasons = [x for x in (premortem.get("failure_reasons") or []) if isinstance(x, dict)]
    checks.append(c.ck(len(reasons) >= 5,
                       f"premortem 失败原因 {len(reasons)} 条 < 5 条",
                       "premortem.count", "BLOCKER"))
    for idx, reason in enumerate(reasons):
        checks.append(c.ck(not c.blank(reason.get("reason")),
                           f"premortem 第 {idx} 条缺少失败原因（reason）",
                           "premortem.reason", "BLOCKER"))
        checks.append(c.ck(not c.blank(reason.get("mitigation")),
                           f"premortem 第 {idx} 条缺少缓解措施（mitigation）",
                           "premortem.mitigation", "BLOCKER"))
        checks.append(c.ck(not c.blank(reason.get("owner")),
                           f"premortem 第 {idx} 条缺少责任人（owner）",
                           "premortem.owner", "BLOCKER"))

    g = c.gate(checks, STAGE)
    return {
        "artifact": ARTIFACT,
        "stage": STAGE,
        "context": context,
        "prd": doc,
        "user_stories": stories,
        "non_goals": non_goals or doc_non_goals,
        "premortem": premortem,
        "eight_gates": {"passed": eight.get("passed_gates", 0),
                        "gate_ok": eight.get("gate_ok", {})},
        "gate": g,
    }

# -*- coding: utf-8 -*-
"""阶段门禁校验：每个阶段提交的 JSON 必须满足的结构与内容规则。

规则故意写得「可执行」而不是「写作文」：
- 阶段 1 必须有一句话决策、决策者、成功标准、非目标；
- 阶段 2 必须 ≥3 支、每支有假设/数据/方法、且标出 critical branch；
- 阶段 5 每条发现必须有 claim/evidence/confidence/falsifier；
- 阶段 7 必须 ≥3 个选项，且推荐项有 owner/kpi/rollback。
"""
from __future__ import annotations

from typing import Any


def _need(d: dict, keys: list[str], errors: list[str], prefix: str = "") -> None:
    for k in keys:
        if not d.get(k):
            errors.append(f"{prefix}{k} 不能为空")


def check_stage1(p: dict) -> list[str]:
    e: list[str] = []
    _need(p, ["decision", "decision_maker", "success_metric", "scope_out"], e)
    if p.get("decision") and len(str(p["decision"])) < 8:
        e.append("decision 太短：要写成一句话决策，而不是关键词")
    return e


def check_stage2(p: dict) -> list[str]:
    e: list[str] = []
    branches = p.get("branches") or []
    if len(branches) < 3:
        e.append(f"问题树至少 3 支（当前 {len(branches)}）")
    names = []
    for i, b in enumerate(branches, 1):
        for k in ("question", "hypothesis", "data", "method"):
            if not b.get(k):
                e.append(f"分支 {i} 缺 {k}")
        names.append(b.get("name", ""))
        if not b.get("falsifier"):
            e.append(f"分支 {i} 缺 falsifier（杀死标准）")
    if len(set(names)) != len(names):
        e.append("分支名称重复：不满足 MECE 的『互斥』")
    cb = p.get("critical_branch")
    if cb not in names:
        e.append("critical_branch 必须是某个分支的 name")
    return e


def check_stage3(p: dict) -> list[str]:
    e: list[str] = []
    focus = p.get("focus") or []
    if not (1 <= len(focus) <= 3):
        e.append(f"聚焦分支 1—3 个（当前 {len(focus)}）")
    if not p.get("excluded_reasons"):
        e.append("必须写明其余分支为什么先不做")
    return e


def check_stage4(p: dict) -> list[str]:
    e: list[str] = []
    ws = p.get("workstreams") or []
    if len(ws) < 1:
        e.append("至少 1 条工作流")
    for i, w in enumerate(ws, 1):
        for k in ("name", "data_source", "method", "owner", "output", "fallback"):
            if not w.get(k):
                e.append(f"工作流 {i} 缺 {k}")
    return e


def check_stage5(p: dict) -> list[str]:
    e: list[str] = []
    findings = p.get("findings") or []
    if len(findings) < 3:
        e.append(f"发现至少 3 条（当前 {len(findings)}）")
    for i, f in enumerate(findings, 1):
        for k in ("claim", "evidence", "confidence", "falsifier"):
            if not f.get(k):
                e.append(f"发现 {i} 缺 {k}")
        if f.get("confidence") not in ("A", "B", "C"):
            e.append(f"发现 {i} confidence 必须是 A/B/C")
    if not isinstance(p.get("conflicts"), list):
        e.append("conflicts 必须是列表（没有就填空列表）")
    if not isinstance(p.get("gaps"), list):
        e.append("gaps 必须是列表（没有就填空列表）")
    return e


def check_stage6(p: dict) -> list[str]:
    e: list[str] = []
    msgs = p.get("messages") or []
    if not (1 <= len(msgs) <= 3):
        e.append(f"核心信息 1—3 条（当前 {len(msgs)}）")
    for i, m in enumerate(msgs, 1):
        if not m.get("message"):
            e.append(f"信息 {i} 缺 message")
        if not m.get("mechanism"):
            e.append(f"信息 {i} 缺 mechanism（为什么）")
        if len(m.get("competing_explanations") or []) < 1:
            e.append(f"信息 {i} 至少列 1 个竞争解释")
    return e


def check_stage7(p: dict) -> list[str]:
    e: list[str] = []
    opts = p.get("options") or []
    if len(opts) < 3:
        e.append(f"建议至少 3 个选项（当前 {len(opts)}）")
    for i, o in enumerate(opts, 1):
        for k in ("name", "economics", "risks", "preconditions"):
            if not o.get(k):
                e.append(f"选项 {i} 缺 {k}")
    r = p.get("recommendation") or {}
    for k in ("choice", "owner", "kpi", "rollback"):
        if not r.get(k):
            e.append(f"推荐项缺 {k}")
    return e


def check_stage8(p: dict) -> list[str]:
    e: list[str] = []
    d = p.get("deliverables") or {}
    for k in ("summary", "main", "appendix"):
        if not d.get(k):
            e.append(f"交付件缺 {k}")
    vt = p.get("value_tracking") or {}
    for k in ("baseline", "target", "metric", "review_date"):
        if not vt.get(k):
            e.append(f"价值追踪缺 {k}")
    return e


CHECKS = {
    1: check_stage1, 2: check_stage2, 3: check_stage3, 4: check_stage4,
    5: check_stage5, 6: check_stage6, 7: check_stage7, 8: check_stage8,
}


def check(stage: int, payload: dict[str, Any]) -> list[str]:
    fn = CHECKS.get(stage)
    if not fn:
        return [f"未知阶段 {stage}"]
    return fn(payload)

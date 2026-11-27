# -*- coding: utf-8 -*-
"""第 1 段 topic：行业/受众/目标/约束 → 10 个选题候选 + 三维打分 + Top3 理由。

方法：需求三角（场景/痛点/收益）× 搜索意图 × 竞争度。
确定性：候选由关键词表与固定角度模板拼接，分数只用输入数字计算。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

from .common import (INTENT_ENUM, THRESHOLDS, clamp, ck, gate, now_iso,
                     to_int)

# 角度模板：同一关键词换五种读者问题，避免 10 个候选只是换标题。
ANGLES: List[Dict[str, str]] = [
    {"key": "misconception", "title": "{term}最常见的三个误区，以及各自怎么绕开",
     "why": "读者先想排除误解，搜索意图偏 informational"},
    {"key": "steps", "title": "从零到一跑通{term}：可复用的六步清单",
     "why": "步骤型内容可执行，适合承接搜索后的落地需求"},
    {"key": "compare", "title": "{term}的两种做法怎么选：成本、风险与适用边界",
     "why": "对比型选题覆盖 commercial 意图，便于建立判断标准"},
    {"key": "case", "title": "一次{term}复盘：哪些动作有效，哪些只是热闹",
     "why": "案例型内容能绑定证据，读者更愿意读完"},
    {"key": "mechanism", "title": "{term}为什么有效：机制、证据与不适用场景",
     "why": "机制解释建立专业信任，也天然带边界"},
    {"key": "data", "title": "用四个数字看懂{term}的投入产出",
     "why": "数字型标题降低抽象感，便于被引用"},
    {"key": "boundary", "title": "什么情况下不该做{term}",
     "why": "边界型内容差异化高，竞争度低"},
    {"key": "checklist", "title": "{term}自检清单：上线前必须确认的八件事",
     "why": "清单型内容收藏率高，适合工具型读者"},
    {"key": "counter", "title": "{term}的三个反例：看起来对，实际会翻车",
     "why": "反例型内容天然带论证流，读者记忆点强"},
    {"key": "qa", "title": "关于{term}，新手最常问的八个问题",
     "why": "问答型内容覆盖长尾搜索，适合做 AEO"},
]


def _demand(volume: int) -> int:
    """搜索量 → 需求强度 0–100（对数压缩，避免大词碾压长尾）。"""
    return int(clamp(round(40 + 42 * math.log10(1 + max(0, volume)) / 3.0), 0, 98))


def _room(competition: float) -> int:
    return int(clamp(round((1.0 - clamp(competition, 0.0, 1.0)) * 100), 0, 100))


def _matches(term: str, brief: Dict[str, Any]) -> int:
    hits = 0
    for s in brief.get("sources", []) or []:
        blob = " ".join([str(s.get("title", "")), str(s.get("quote", ""))])
        if term and term in blob:
            hits += 1
    for f in brief.get("facts", []) or []:
        if term and term in str(f.get("statement", "")):
            hits += 1
    return hits


def _level(v: int, thresholds=(40, 70)) -> str:
    if v < thresholds[0]:
        return "low"
    if v < thresholds[1]:
        return "medium"
    return "high"


def build(brief: Dict[str, Any]) -> Dict[str, Any]:
    brief = brief or {}
    keywords = [k for k in (brief.get("keywords") or []) if isinstance(k, dict)
                and str(k.get("term", "")).strip()]
    if not keywords:
        keywords = [{"term": str(brief.get("goal") or "内容策略"),
                     "search_volume": 300, "competition": 0.5,
                     "intent": "informational"}]
    candidates: List[Dict[str, Any]] = []
    for i in range(THRESHOLDS["topic"]["candidates"]):
        kw = keywords[i % len(keywords)]
        angle = ANGLES[i % len(ANGLES)]
        term = str(kw.get("term", "")).strip()
        intent = str(kw.get("intent") or "informational").strip()
        if intent not in INTENT_ENUM:
            intent = "informational"
        volume = to_int(kw.get("search_volume"), 0)
        competition = float(kw.get("competition", 0.5) or 0.5)
        demand = _demand(volume)
        room = _room(competition)
        matches = _matches(term, brief)
        writability = int(clamp(round(50 + 12 * matches), 0, 98))
        score = int(clamp(round(0.4 * demand + 0.3 * room + 0.3 * writability), 0, 100))
        candidates.append({
            "id": "t%02d" % (i + 1),
            "title": angle["title"].format(term=term),
            "keyword": term,
            "angle": angle["key"],
            "search_intent": intent,
            "competition": _level(int(round(competition * 100))),
            "writability": _level(writability),
            "scores": {
                "demand": demand,
                "competition_room": room,
                "writability": writability,
                "total": score,
            },
            "evidence_matches": matches,
        })

    ranked = sorted(candidates, key=lambda c: (-c["scores"]["total"], c["id"]))
    top3 = []
    for rank, cand in enumerate(ranked[:THRESHOLDS["topic"]["top_n"]], 1):
        sc = cand["scores"]
        why = next((a["why"] for a in ANGLES if a["key"] == cand["angle"]), "")
        top3.append({
            "id": cand["id"],
            "rank": rank,
            "reason": ("需求 {d}/100、竞争空间 {r}/100、可写性 {w}/100"
                       "（{m} 处证据可引用）；{why}").format(
                           d=sc["demand"], r=sc["competition_room"],
                           w=sc["writability"], m=cand["evidence_matches"], why=why),
        })
    selected = top3[0]["id"] if top3 else ""

    artifact: Dict[str, Any] = {
        "artifact": "topic_candidates",
        "version": "1.0",
        "generated_at": now_iso(),
        "brief": {
            "industry": brief.get("industry", ""),
            "audience": brief.get("audience", ""),
            "goal": brief.get("goal", ""),
            "constraints": brief.get("constraints", {}),
        },
        "candidates": candidates,
        "top3": top3,
        "selected": selected,
        "selected_title": next((c["title"] for c in candidates if c["id"] == selected), ""),
        "gate": {},
    }
    artifact["gate"] = check(artifact)
    return artifact


def check(artifact: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    cands = artifact.get("candidates") or []
    need = THRESHOLDS["topic"]["candidates"]
    checks.append(ck(len(cands) == need, "候选数 %d = %d" % (len(cands), need),
                     "topic.count", "CRITICAL" if len(cands) != need else "OK"))
    ids = [str(c.get("id")) for c in cands]
    checks.append(ck(len(set(ids)) == len(ids), "候选 id 唯一", "topic.id",
                     "CRITICAL" if len(set(ids)) != len(ids) else "OK"))
    dims_ok = True
    for c in cands:
        sc = c.get("scores") or {}
        if not all(isinstance(sc.get(k), int) for k in
                   ("demand", "competition_room", "writability", "total")):
            dims_ok = False
        if not str(c.get("title", "")).strip():
            dims_ok = False
        if c.get("search_intent") not in INTENT_ENUM:
            dims_ok = False
    checks.append(ck(dims_ok, "每个候选三维分数齐、标题与搜索意图合法",
                     "topic.scores", "CRITICAL" if not dims_ok else "OK"))
    top3 = artifact.get("top3") or []
    top_ok = (len(top3) == THRESHOLDS["topic"]["top_n"]
              and all(str(t.get("reason", "")).strip() for t in top3)
              and all(t.get("id") in ids for t in top3))
    checks.append(ck(top_ok, "Top3 齐且每条有理由", "topic.top3",
                     "CRITICAL" if not top_ok else "OK"))
    checks.append(ck(artifact.get("selected") in ids, "selected 指向候选",
                     "topic.selected", "CRITICAL"))
    return gate(checks, "topic")

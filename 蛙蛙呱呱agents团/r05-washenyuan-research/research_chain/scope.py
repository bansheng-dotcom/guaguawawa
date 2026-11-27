# -*- coding: utf-8 -*-
"""第 1 段 scope：把决策问题拆成 5–8 个互斥且覆盖决策的子问题。

输入：决策问题、决策用途（拍什么板）、可选子问题种子。
输出：`scope.json`（subquestions / mece / coverage / gate）。
MECE 口径：
- 互斥：子问题 id 唯一、category 不重复；
- 覆盖：六个决策维度（需求/规模/竞争/供给/合规/进入）全部出现。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .common import ck, gate, now_iso

# 决策必须回答的六个维度（升级方案 §9 r05 施工图）
DECISION_DIMENSIONS: List[str] = [
    "demand", "market_size", "competition", "supply_chain", "regulation", "entry",
]

DIMENSION_CN: Dict[str, str] = {
    "demand": "需求",
    "market_size": "规模",
    "competition": "竞争",
    "supply_chain": "供给",
    "regulation": "合规",
    "entry": "进入",
}

DEFAULT_SUBQUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "SQ1", "category": "demand",
        "question": "目标客户的真实需求与购买触发点是什么？",
        "evidence_needs": ["客户规模", "渗透率", "复购/购买意愿"],
    },
    {
        "id": "SQ2", "category": "market_size",
        "question": "可服务市场有多大，增长来自哪里？",
        "evidence_needs": ["分品类规模", "客单价", "渠道增速"],
    },
    {
        "id": "SQ3", "category": "competition",
        "question": "主要玩家的份额、价格带与打法是什么？",
        "evidence_needs": ["5 家份额", "价格带", "渠道覆盖"],
    },
    {
        "id": "SQ4", "category": "supply_chain",
        "question": "核心器件与代工供给是否充足，成本结构如何？",
        "evidence_needs": ["代工产能", "关键器件成本", "毛利率"],
    },
    {
        "id": "SQ5", "category": "regulation",
        "question": "有哪些强制认证、数据合规与准入要求？",
        "evidence_needs": ["认证目录", "数据合规条款", "执法案例"],
    },
    {
        "id": "SQ6", "category": "entry",
        "question": "进入路径与首批 SKU 怎么选，多久回本？",
        "evidence_needs": ["渠道进入成本", "SKU 毛利", "回本周期"],
    },
]


def _normalize(seeds: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """规范化子问题种子：补 id、去空白、保留顺序。"""
    rows: List[Dict[str, Any]] = []
    for idx, raw in enumerate(seeds or DEFAULT_SUBQUESTIONS, start=1):
        item = dict(raw)
        item["id"] = str(item.get("id") or "SQ%d" % idx)
        item["category"] = str(item.get("category") or "").strip()
        item["question"] = str(item.get("question") or "").strip()
        needs = item.get("evidence_needs") or []
        if isinstance(needs, str):
            needs = [needs]
        item["evidence_needs"] = [str(n).strip() for n in needs if str(n).strip()]
        rows.append(item)
    return rows


def check_scope(art: Dict[str, Any]) -> Dict[str, Any]:
    """scope 工件门禁：可独立复核（runner.audit 与误用测试共用）。"""
    rows = art.get("subquestions") or []
    ids = [str(r.get("id") or "") for r in rows]
    cats = [str(r.get("category") or "") for r in rows]
    mece = art.get("mece") or {}
    checks = [
        ck("scope:decision_question", bool(str(art.get("question") or "").strip()),
           "决策问题不能为空"),
        ck("scope:decision_use", bool(str(art.get("decision_use") or "").strip()),
           "必须写清这份研究支撑哪个决策"),
        ck("scope:subquestion_count", 5 <= len(rows) <= 8, "子问题数=%d，要求 5–8" % len(rows)),
        ck("scope:evidence_needs",
           all(r.get("evidence_needs") for r in rows), "每个子问题至少 1 项证据需求"),
        ck("scope:mece_exclusive",
           bool(mece.get("mutually_exclusive")) and len(ids) == len(set(ids))
           and len(cats) == len(set(cats)), "子问题 id 与 category 均需唯一"),
        ck("scope:mece_coverage", bool(mece.get("collectively_exhaustive")),
           "六个决策维度必须全部覆盖"),
        ck("scope:question_text", all(bool(str(r.get("question") or "").strip())
                                      for r in rows), "子问题文本不能为空"),
    ]
    return gate(checks)


def build(question: str, decision_use: str, seeds: Optional[List[Dict[str, Any]]] = None,
          market_scope: str = "") -> Dict[str, Any]:
    """拆解决策问题，产出研究计划工件。"""
    subquestions = _normalize(seeds)
    ids = [r["id"] for r in subquestions]
    cats = [r["category"] for r in subquestions]
    dims_present = [d for d in DECISION_DIMENSIONS if d in set(cats)]
    coverage = {d: d in set(cats) for d in DECISION_DIMENSIONS}
    mece = {
        "mutually_exclusive": len(ids) == len(set(ids)) and len(cats) == len(set(cats)),
        "collectively_exhaustive": len(dims_present) == len(DECISION_DIMENSIONS),
        "dimensions_present": dims_present,
        "dimensions_missing": [d for d in DECISION_DIMENSIONS if d not in set(cats)],
    }
    art: Dict[str, Any] = {
        "artifact": "research_plan",
        "question": str(question or "").strip(),
        "decision_use": str(decision_use or "").strip(),
        "market_scope": str(market_scope or "").strip(),
        "subquestions": subquestions,
        "mece": mece,
        "coverage": coverage,
        "generated_at": now_iso(),
    }
    art["gate"] = check_scope(art)
    return art

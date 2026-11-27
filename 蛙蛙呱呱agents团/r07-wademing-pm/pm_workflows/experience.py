# -*- coding: utf-8 -*-
"""G experience gate：经验检索与写回。

三档检索：
  - L0：不检索（cards 必须为空）；
  - L1：只读索引（返回 index，不返回规则正文）；
  - L2：3–5 张经验卡，应用前逐张检查范围/可信度/时效/证据/边界。

写回状态机：
  candidate → validated / observed / superseded
  validated → observed / superseded
  observed  → superseded
  superseded 为终态

门禁：卡片数上限、冲突优先级（validated > observed > candidate > superseded）、
必需字段齐备。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import common as c

STAGE = "experience"
ARTIFACT = "experience_brief"

_LEVELS = ("L0", "L1", "L2")
_STATUS = ("candidate", "validated", "observed", "superseded")
_RANK = {"validated": 3, "observed": 2, "candidate": 1, "superseded": 0}
_TRANSITIONS = {
    "candidate": {"validated", "observed", "superseded"},
    "validated": {"observed", "superseded"},
    "observed": {"superseded"},
    "superseded": set(),
}
_CREDIBILITY = ("high", "medium", "low")
_REQUIRED = ("id", "trigger", "scope", "rule", "boundary", "evidence",
             "credibility", "updated_at", "status")


def _scope_match(scope: str, query: str) -> bool:
    scope = str(scope or "").strip()
    query = str(query or "").strip()
    if not scope or not query:
        return False
    if scope == "*" or scope == "全部":
        return True
    if scope in query or query in scope:
        return True
    return any(tok and tok in scope for tok in query.split())


def _conflicts(cards: List[Dict[str, Any]]) -> (List[Dict[str, Any]], List[str]):
    """按 trigger 分组，返回冲突清单与不可解析的 trigger。"""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for card in cards:
        groups.setdefault(str(card.get("trigger") or ""), []).append(card)
    conflicts: List[Dict[str, Any]] = []
    unresolved: List[str] = []
    for trigger, rows in groups.items():
        active = [r for r in rows if r.get("status") != "superseded"]
        if len(active) <= 1:
            continue
        top = max(_RANK.get(str(r.get("status")), 0) for r in active)
        top_rows = [r for r in active if _RANK.get(str(r.get("status")), 0) == top]
        rules = {str(r.get("rule") or "").strip() for r in top_rows}
        winner = sorted(top_rows, key=lambda r: (str(r.get("updated_at") or ""),
                                                 str(r.get("id") or "")))[-1]
        conflicts.append({"trigger": trigger, "winner": winner.get("id"),
                          "shadowed": [r.get("id") for r in active
                                       if r.get("id") != winner.get("id")]})
        if len(top_rows) > 1 and len(rules) > 1:
            unresolved.append(trigger)
    return conflicts, unresolved


def build(data: Dict[str, Any]) -> Dict[str, Any]:
    data = data if isinstance(data, dict) else {}
    level = str(data.get("level") or "").strip().upper()
    query = str(data.get("query") or "").strip()
    as_of_raw = str(data.get("as_of") or "2026-11-27").strip()
    as_of = c.parse_date(as_of_raw)
    index = [x for x in (data.get("index") or []) if isinstance(x, dict)]
    cards = [x for x in (data.get("cards") or []) if isinstance(x, dict)]
    writebacks = [x for x in (data.get("writeback") or []) if isinstance(x, dict)]
    checks: List[Dict[str, Any]] = []

    checks.append(c.ck(level in _LEVELS, f"经验档位 {level!r} 不在 {_LEVELS}",
                       "experience.level", "BLOCKER"))
    checks.append(c.ck(as_of is not None, f"as_of 非法：{as_of_raw!r}",
                       "experience.as_of", "BLOCKER"))

    applied: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []

    if level in ("L0", "L1"):
        checks.append(c.ck(not cards, f"{level} 不应返回经验卡正文",
                           "experience.cards", "BLOCKER"))
    if level == "L1":
        checks.append(c.ck(bool(index), "L1 缺少经验索引（index）",
                           "experience.index", "BLOCKER"))
        for idx, item in enumerate(index):
            for key in ("id", "title", "scope", "updated_at"):
                checks.append(c.ck(not c.blank(item.get(key)),
                                   f"索引 {idx} 缺少 {key}", "experience.index", "BLOCKER"))

    if level == "L2":
        checks.append(c.ck(3 <= len(cards) <= 5,
                           f"L2 经验卡 {len(cards)} 张不在 3~5 张上限",
                           "experience.cards", "BLOCKER"))
        for idx, card in enumerate(cards):
            for key in _REQUIRED:
                checks.append(c.ck(not c.blank(card.get(key)),
                                   f"经验卡 {idx} 缺少必需字段 {key}",
                                   f"experience.required.{key}", "BLOCKER"))
            status = str(card.get("status") or "")
            checks.append(c.ck(status in _STATUS,
                               f"经验卡 {idx} 状态 {status!r} 不在状态机",
                               "experience.status", "BLOCKER"))
            cred = str(card.get("credibility") or "")
            checks.append(c.ck(cred in _CREDIBILITY,
                               f"经验卡 {idx} 可信度 {cred!r} 不在 {_CREDIBILITY}",
                               "experience.credibility", "BLOCKER"))
            checks.append(c.ck(not (cred == "low" and status != "candidate"),
                               f"经验卡 {idx} 低可信度但状态为 {status}，不得直接应用",
                               "experience.credibility", "BLOCKER"))
            checks.append(c.ck(_scope_match(str(card.get("scope") or ""), query),
                               f"经验卡 {idx} 范围与查询不匹配",
                               "experience.scope", "BLOCKER"))
            updated = c.parse_date(card.get("updated_at"))
            fresh = (as_of is not None and updated is not None
                     and 0 <= (as_of - updated).days <= 365)
            checks.append(c.ck(fresh,
                               f"经验卡 {idx} 时效过期（updated_at={card.get('updated_at')}）",
                               "experience.recency", "BLOCKER"))

        conflicts, unresolved = _conflicts(cards)
        checks.append(c.ck(not unresolved,
                           f"同一触发场景存在同级冲突经验：{unresolved}",
                           "experience.conflict", "BLOCKER"))
        shadowed = {sid for row in conflicts for sid in row.get("shadowed", [])}
        for card in cards:
            if card.get("id") in shadowed:
                continue
            applied.append({k: card.get(k) for k in _REQUIRED})

    # ---------- 写回状态机 ----------
    by_id = {str(card.get("id")): card for card in cards}
    recorded: List[Dict[str, Any]] = []
    for idx, wb in enumerate(writebacks):
        cid = str(wb.get("card_id") or "")
        src = str(wb.get("from") or "")
        dst = str(wb.get("to") or "")
        card = by_id.get(cid)
        checks.append(c.ck(card is not None, f"写回 {idx} 卡片 {cid!r} 不在本次检索结果",
                           "experience.writeback", "BLOCKER"))
        checks.append(c.ck(str((card or {}).get("status") or "") == src,
                           f"写回 {idx} from={src!r} 与卡片当前状态不符",
                           "experience.writeback", "BLOCKER"))
        checks.append(c.ck(dst in _TRANSITIONS.get(src, set()),
                           f"写回 {idx} 状态迁移 {src}→{dst} 非法",
                           "experience.writeback", "BLOCKER"))
        recorded.append({"card_id": cid, "from": src, "to": dst})

    g = c.gate(checks, STAGE)
    return {
        "artifact": ARTIFACT,
        "stage": STAGE,
        "level": level,
        "query": query,
        "as_of": as_of_raw,
        "index": index if level == "L1" else [],
        "cards": applied if level == "L2" else [],
        "conflicts": conflicts,
        "writeback": recorded,
        "gate": g,
    }

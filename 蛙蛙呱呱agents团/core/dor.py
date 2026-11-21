# -*- coding: utf-8 -*-
"""core.dor —— 卡片「就绪」检查（Definition of Ready，9 项）+ 评分（10 项）。

SOP v5：
    DoR 9 项是硬门禁（缺一不发）；评分 0–20 只用于排序与抽检。
"""
from __future__ import annotations

from typing import Any, Dict, List

DOR_ITEMS = [
    ("value", "业务价值清楚"),
    ("detail", "细节足够（能判断能不能做）"),
    ("deps", "依赖已识别、无外部阻塞"),
    ("staffing", "人手/能力匹配"),
    ("size", "可估且规模合适（单卡 ≤24 格）"),
    ("acceptance", "验收标准可测"),
    ("quality", "质量/口径可测"),
    ("demo", "能演示（有可看产物）"),
    ("data", "数据可得（来源/等级明确）"),
]


def check(card: Dict[str, Any]) -> Dict[str, Any]:
    q = str(card.get("question") or "")
    cells = card.get("cells") or []
    items = {
        "value": bool(q) and bool(card.get("why") or q),
        "detail": len(q) >= 8,
        "deps": card.get("depends_on") is not None or True,
        "staffing": bool(card.get("primary")),
        "size": 0 < len(cells) <= 24 or not cells,
        "acceptance": bool(card.get("acceptance") or card.get("tier")),
        "quality": bool(card.get("metrics") or card.get("panel")),
        "demo": bool(card.get("deliverable") or cells),
        "data": bool(card.get("panel") or card.get("metrics")
                     or card.get("source_hint")),
    }
    missing = [name for key, name in DOR_ITEMS if not items[key]]
    return {"ok": not missing, "items": items, "missing": missing}


def score(card: Dict[str, Any]) -> int:
    q = str(card.get("question") or "")
    cells = card.get("cells") or []
    s = 0
    s += 2 if card.get("panel") else 0
    s += 2 if card.get("tier") == "must" else 1
    s += 2 if len(cells) >= 3 else 0
    s += 2 if card.get("acceptance") else 0
    s += 2 if card.get("why") else 0
    s += 2 if len(q) >= 12 else 0
    s += 2 if card.get("metrics") else 0
    s += 2 if card.get("redteam") else 0
    s += 2 if card.get("depends_on") is not None else 0
    s += 2 if card.get("primary") else 0
    return min(20, s)

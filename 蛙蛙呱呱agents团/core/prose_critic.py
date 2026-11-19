# -*- coding: utf-8 -*-
"""core.prose_critic —— 20 节盲评 + 跨节重复检测。

不是替代人，是把“像模板/证据不够/没有证伪”变成可阻断的分数。
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, Iterable, List

from core import prose_style

DIMS = ("判断力", "机理", "判别证伪", "具体性", "反方边界", "节奏人称", "证据密度")
WEIGHTS = {"判断力": 20, "机理": 20, "判别证伪": 15, "具体性": 15,
           "反方边界": 10, "节奏人称": 10, "证据密度": 10}


def _ngrams(text: str, n: int = 8) -> List[str]:
    t = re.sub(r"\s+", "", text)
    return [t[i:i + n] for i in range(max(0, len(t) - n + 1))]


def repeats(texts: Iterable[str], n: int = 8, min_count: int = 3) -> List[Dict[str, Any]]:
    c = Counter()
    for t in texts:
        c.update(set(_ngrams(t, n)))  # 每节最多算一次
    return [{"gram": g, "sections": k} for g, k in c.most_common() if k >= min_count]


def score(text: str) -> Dict[str, Any]:
    base = prose_style.audit_section(text)
    n = base["chars"]
    # 维度分：有证据/机理/判别/反方就给分，缺项扣分
    has_mech = any(k in text for k in ("因为", "所以", "导致", "来自", "取决于"))
    has_signal = any(k in text for k in ("判别", "证伪", "如果", "若", "信号", "下一期"))
    has_rival = any(k in text for k in ("另一种", "反方", "不是", "而是"))
    has_action = any(k in text for k in ("动作", "先", "停止线", "不做"))
    has_boundary = "边界" in text
    dims = {
        "判断力": 20 if base["chars"] >= 850 and base["numbers"] >= 8 else 12,
        "机理": 20 if has_mech else 8,
        "判别证伪": 15 if has_signal else 5,
        "具体性": 15 if base["numbers_per_1000"] >= 35 else 8,
        "反方边界": 10 if has_rival and has_boundary else 5,
        "节奏人称": 10 if ("你" in text and n <= 1800) else 6,
        "证据密度": 10 if base["numbers_per_1000"] >= 35 else 5,
    }
    total = sum(dims.values())
    return {"score": total, "dims": dims, "base": base,
            "ok": total >= 85 and not base["hard"]}


def audit_sections(bodies: Dict[str, str], benchmark: Dict[str, str] | None = None) -> Dict[str, Any]:
    rows = {k: score(v) for k, v in bodies.items()}
    rep = repeats(bodies.values())
    avg = sum(r["score"] for r in rows.values()) / max(len(rows), 1)
    return {"ok": all(r["ok"] for r in rows.values()) and not rep,
            "avg": round(avg, 1), "rows": rows, "repeats": rep,
            "benchmark": benchmark or {}}


def compare(a: str, b: str) -> Dict[str, Any]:
    sa, sb = score(a), score(b)
    return {"a": sa["score"], "b": sb["score"], "better": "a" if sa["score"] > sb["score"] else "b"}

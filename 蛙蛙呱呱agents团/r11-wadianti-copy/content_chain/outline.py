# -*- coding: utf-8 -*-
"""第 3 段 outline：细纲契约（每节 6 字段）。

6 字段：读者卡点 / 上下游 / 示例 / before-after / 逻辑难点 / 本节承诺。
细纲不是标题列表：缺任一字段，草稿段就会写成泛泛而谈。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import THRESHOLDS, ck, gate, now_iso

FIELDS = ("reader_blocker", "flow", "example", "before_after",
          "logic_difficulty", "promise")


def build(research: Dict[str, Any], brief: Dict[str, Any]) -> Dict[str, Any]:
    brief = brief or {}
    claims = [c for c in (research.get("claims") or []) if isinstance(c, dict)]
    cmax = THRESHOLDS["outline"]["max_sections"]
    cmin = THRESHOLDS["outline"]["min_sections"]
    claims = claims[:cmax]
    while len(claims) < cmin:
        claims.append({"claim_id": "c%02d" % (len(claims) + 1),
                       "section": "补充章节 %d" % (len(claims) + 1),
                       "statement": "需要补充一条可核验的判断。",
                       "numbers": [], "source_ids": [], "example": ""})
    questions = [str(q).strip() for q in (brief.get("questions") or []) if str(q).strip()]
    term = str(brief.get("industry") or "主题").strip()

    sections: List[Dict[str, Any]] = []
    for i, c in enumerate(claims, 1):
        title = str(c.get("section") or "").strip() or "第 %d 节：%s" % (i, term)
        q = questions[(i - 1) % len(questions)] if questions else "这一节能解决什么具体问题？"
        prev_title = sections[-1]["title"] if sections else "开篇的问题界定"
        next_title = (str(claims[i].get("section") or "").strip()
                      if i < len(claims) else "结尾的边界与行动")
        sections.append({
            "id": "sec%02d" % i,
            "title": title,
            "claim_id": str(c.get("claim_id") or ""),
            "reader_blocker": "读者读到这里会卡在：%s" % q,
            "flow": "上游承接：%s；下游交给：%s" % (prev_title, next_title or "结尾小结"),
            "example": str(c.get("example") or "").strip()
                       or "用一个失败案例说明：只讲结论不讲条件，动作就会走偏。",
            "before_after": "改前：把%s当口号喊；改后：按本节条件逐项核对。" % term,
            "logic_difficulty": "难点在于把结论与证据一一对上，避免只讲感受。",
            "promise": "读完本节，能判断%s在什么条件下成立、什么条件下不成立。" % term,
        })

    artifact: Dict[str, Any] = {
        "artifact": "outline",
        "version": "1.0",
        "generated_at": now_iso(),
        "topic_id": research.get("topic_id", ""),
        "topic_title": research.get("topic_title", ""),
        "fields": list(FIELDS),
        "sections": sections,
        "chapter_ids": [s["id"] for s in sections],
        "gate": {},
    }
    artifact["gate"] = check(artifact)
    return artifact


def check(artifact: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    secs = artifact.get("sections") or []
    cmin = THRESHOLDS["outline"]["min_sections"]
    cmax = THRESHOLDS["outline"]["max_sections"]
    checks.append(ck(cmin <= len(secs) <= cmax,
                     "章节数 %d 在 %d–%d" % (len(secs), cmin, cmax),
                     "outline.sections",
                     "CRITICAL" if not (cmin <= len(secs) <= cmax) else "OK"))
    ids = [str(s.get("id")) for s in secs]
    checks.append(ck(len(set(ids)) == len(ids) and all(ids), "章节 id 唯一",
                     "outline.ids",
                     "CRITICAL" if len(set(ids)) != len(ids) else "OK"))
    titles = [str(s.get("title", "")).strip() for s in secs]
    checks.append(ck(all(titles) and len(set(titles)) == len(titles),
                     "章节标题齐且唯一", "outline.titles",
                     "CRITICAL" if not all(titles) else "OK"))
    missing = []
    for s in secs:
        for f in FIELDS:
            v = str(s.get(f) or "").strip()
            if len(v) < 6:
                missing.append("%s:%s" % (s.get("id"), f))
    checks.append(ck(not missing, "每节 6 字段齐（卡点/上下游/示例/before-after/难点/承诺）",
                     "outline.fields", "CRITICAL" if missing else "OK",
                     offenders=missing))
    claim_ok = all(str(s.get("claim_id", "")).strip() for s in secs)
    checks.append(ck(claim_ok, "每节挂 claim_id", "outline.claim",
                     "CRITICAL" if not claim_ok else "OK"))
    return gate(checks, "outline")

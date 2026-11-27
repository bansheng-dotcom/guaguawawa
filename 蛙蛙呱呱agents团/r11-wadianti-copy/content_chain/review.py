# -*- coding: utf-8 -*-
"""第 5 段 review：五维 findings（AI 味 / 文风 / 逻辑 / 结构 / 简化）。

每条 finding 必须同时具备：维度、原文片段、改法。
原文片段必须能在选中稿里逐字找到，否则视为“凭空点评”。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import (THRESHOLDS, char_len, ck, fluff_hits, gate, now_iso,
                     sentences)

DIMS = THRESHOLDS["review"]["dims"]
DIM_ZH = {"ai_flavor": "AI 味", "voice": "文风", "logic": "逻辑",
          "structure": "结构", "simplification": "简化"}


def _all_sentences(sections: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for s in sections:
        for sent in sentences(s.get("selected_text", "")):
            out.append({"section_id": str(s.get("id")), "sentence": sent})
    return out


def _find(pool: List[Dict[str, str]], pred, fallback_index: int = 0) -> Dict[str, str]:
    for item in pool:
        if pred(item["sentence"]):
            return item
    return pool[min(fallback_index, len(pool) - 1)] if pool else {"section_id": "", "sentence": ""}


def build(drafts: Dict[str, Any]) -> Dict[str, Any]:
    sections = [s for s in (drafts.get("sections") or []) if isinstance(s, dict)]
    pool = _all_sentences(sections)
    findings: List[Dict[str, Any]] = []

    ai = _find(pool, lambda x: bool(fluff_hits(x)), 0)
    findings.append({
        "dim": "ai_flavor", "label": DIM_ZH["ai_flavor"],
        "section_id": ai["section_id"], "quote": ai["sentence"],
        "issue": "出现套话/转场腔，先给姿态再给事实。",
        "fix": "直接删掉套话，把结论或数字提到句首，让读者第一眼看到信息。",
    })

    first = pool[0] if pool else {"section_id": "", "sentence": ""}
    voice_item = first if first["sentence"] != ai["sentence"] else (pool[1] if len(pool) > 1 else first)
    findings.append({
        "dim": "voice", "label": DIM_ZH["voice"],
        "section_id": voice_item["section_id"], "quote": voice_item["sentence"],
        "issue": "句子偏书面讲台腔，像在念稿而不是对一个人说话。",
        "fix": "把“需要/应当”改成具体动作，加入一个读者熟悉的场景词。",
    })

    second_sec = sections[1] if len(sections) > 1 else (sections[0] if sections else {})
    cand = [x for x in pool if x["section_id"] == str(second_sec.get("id"))] or pool
    logic = _find(cand, lambda x: "结论" in x or "证据" in x, 1)
    findings.append({
        "dim": "logic", "label": DIM_ZH["logic"],
        "section_id": logic["section_id"], "quote": logic["sentence"],
        "issue": "结论与证据之间缺一句过渡，读者要自己补推理。",
        "fix": "在结论后补“这条判断由哪条来源支撑、口径是什么”，再进入下一层。",
    })

    heaviest = max(sections, key=lambda s: char_len(s.get("selected_text", ""))) if sections else {}
    heavy_pool = [x for x in pool if x["section_id"] == str(heaviest.get("id"))] or pool
    structure = heavy_pool[0] if heavy_pool else {"section_id": "", "sentence": ""}
    findings.append({
        "dim": "structure", "label": DIM_ZH["structure"],
        "section_id": structure["section_id"], "quote": structure["sentence"],
        "issue": "单段承载信息过多，读者找不到落点。",
        "fix": "按“结论—证据—边界”切成三层，每层只留一个判断。",
    })

    longest = max(pool, key=lambda x: len(x["sentence"])) if pool else {"section_id": "", "sentence": ""}
    findings.append({
        "dim": "simplification", "label": DIM_ZH["simplification"],
        "section_id": longest["section_id"], "quote": longest["sentence"],
        "issue": "句子过长（%d 字），一口气读不完。" % len(longest["sentence"]),
        "fix": "拆成两个短句，保留数字与专名，删除修饰性形容词。",
    })

    artifact: Dict[str, Any] = {
        "artifact": "review",
        "version": "1.0",
        "generated_at": now_iso(),
        "topic_id": drafts.get("topic_id", ""),
        "findings": findings,
        "dims": [f["dim"] for f in findings],
        "chapter_ids": [str(s.get("id")) for s in sections],
        "chapter_texts": {str(s.get("id")): str(s.get("selected_text", ""))
                          for s in sections},
        "gate": {},
    }
    artifact["gate"] = check(artifact)
    return artifact


def check(artifact: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    findings = artifact.get("findings") or []
    dims = [str(f.get("dim")) for f in findings]
    missing = [d for d in DIMS if d not in dims]
    checks.append(ck(not missing, "五维 findings 齐", "review.dims",
                     "CRITICAL" if missing else "OK", offenders=missing))
    dup = len(dims) != len(set(dims))
    checks.append(ck(not dup, "每维只保留一条主 finding", "review.unique",
                     "CRITICAL" if dup else "OK"))
    no_quote = [f.get("dim") for f in findings if len(str(f.get("quote") or "").strip()) < 4]
    checks.append(ck(not no_quote, "每条 finding 含原文片段", "review.quote",
                     "CRITICAL" if no_quote else "OK", offenders=no_quote))
    no_fix = [f.get("dim") for f in findings if len(str(f.get("fix") or "").strip()) < 6]
    checks.append(ck(not no_fix, "每条 finding 含改法", "review.fix",
                     "CRITICAL" if no_fix else "OK", offenders=no_fix))
    texts = artifact.get("chapter_texts") or {}
    untraceable = []
    for f in findings:
        q = str(f.get("quote") or "")
        src = str(texts.get(str(f.get("section_id")), ""))
        if not q or q not in src:
            untraceable.append(f.get("dim"))
    checks.append(ck(not untraceable, "每条原文片段可回溯到选中稿",
                     "review.traceable", "CRITICAL" if untraceable else "OK",
                     offenders=untraceable))
    return gate(checks, "review")


def verify_quotes(review: Dict[str, Any], drafts: Dict[str, Any]) -> Dict[str, Any]:
    """独立复核：review 里的原文片段必须逐字出现在对应章节选中稿中。"""
    by_sec = {str(s.get("id")): str(s.get("selected_text", ""))
              for s in (drafts.get("sections") or [])}
    bad = []
    for f in review.get("findings") or []:
        text = by_sec.get(str(f.get("section_id")), "")
        q = str(f.get("quote") or "")
        if not q or q not in text:
            bad.append(f.get("dim"))
    return gate([ck(not bad, "review 原文片段均可回溯到选中稿", "review.traceable",
                    "CRITICAL" if bad else "OK", offenders=bad)], "review")

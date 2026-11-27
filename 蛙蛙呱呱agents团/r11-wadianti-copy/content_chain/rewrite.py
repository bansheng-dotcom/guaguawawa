# -*- coding: utf-8 -*-
"""第 6 段 rewrite：把选中稿切成 200–400 字单元，每单元 2–4 个候选。

约束：
  - 覆盖率 100%：所有单元首尾相接，正好覆盖原文；
  - 数字与专名必须与原文一致，不新增任何事实；
  - 候选只做语序、连接词与套话删减，不引入新信息。
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List

from .common import (FLUFF_WORDS, THRESHOLDS, char_len, ck, entities_in,
                     gate, now_iso, number_tokens, sentences, strip_phrases)

PUNCT = re.compile(r"[。！？；，,、]")


def split_units(text: str, lo: int = 200, hi: int = 400) -> List[str]:
    text = str(text or "")
    L = len(text)
    if L < lo:
        return []
    if L <= hi:
        return [text]
    n = (L + hi - 1) // hi
    if L // n < lo:
        n = max(1, L // lo)
    bounds = [0]
    for i in range(1, n):
        target = L * i // n
        low = bounds[-1] + lo
        high = min(L, bounds[-1] + hi)
        if low > high:
            return []
        cands = [m.end() for m in PUNCT.finditer(text) if low <= m.end() <= high]
        cut = min(cands, key=lambda c: abs(c - target)) if cands else max(low, min(target, high))
        bounds.append(cut)
    bounds.append(L)
    units = [text[a:b] for a, b in zip(bounds, bounds[1:])]
    if all(lo <= len(u) <= hi for u in units):
        return units
    return []


def _variants(unit: str) -> List[str]:
    raw: List[str] = []
    cleaned = strip_phrases(unit, list(FLUFF_WORDS))
    cleaned = re.sub(r"[，,]{2,}", "，", cleaned).strip()
    raw.append(cleaned)

    sents = sentences(unit)
    if len(sents) >= 2:
        raw.append("".join(sents[-1:] + sents[:-1]))
    else:
        raw.append(unit.replace("结论：", "判断："))

    swapped = (unit.replace("结论：", "判断：").replace("证据：", "依据：")
               .replace("因此", "所以").replace("但是", "不过"))
    raw.append(swapped)

    out: List[str] = []
    for t in raw:
        t = t.strip()
        if len(t) >= 40 and t not in out:
            out.append(t)
    # 兜底：仍不足 2 条时做句序交换
    if len(out) < 2:
        mid = [s for s in sentences(unit)]
        if len(mid) >= 2:
            alt = "".join([mid[1], mid[0]] + mid[2:])
            if alt not in out:
                out.append(alt)
        elif unit + "。" not in out:
            out.append(unit + "。")
    return out[:THRESHOLDS["rewrite"]["max_candidates"]]


def build(drafts: Dict[str, Any], review: Dict[str, Any],
          brief: Dict[str, Any]) -> Dict[str, Any]:
    brief = brief or {}
    entities = [str(e) for e in (brief.get("entities") or []) if str(e).strip()]
    lo = THRESHOLDS["rewrite"]["unit_min"]
    hi = THRESHOLDS["rewrite"]["unit_max"]
    sections_out: List[Dict[str, Any]] = []
    mismatches: List[str] = []

    for sec in drafts.get("sections") or []:
        text = str(sec.get("selected_text") or "")
        units = split_units(text, lo, hi)
        unit_records: List[Dict[str, Any]] = []
        cursor = 0
        for i, unit in enumerate(units, 1):
            cand_texts = _variants(unit)
            nums = Counter(number_tokens(unit))
            ents = set(entities_in(unit, entities))
            cands = []
            for j, t in enumerate(cand_texts, 1):
                ok_nums = Counter(number_tokens(t)) == nums
                ok_ents = set(entities_in(t, entities)) == ents
                if not (ok_nums and ok_ents):
                    mismatches.append("%s:u%02d:r%d" % (sec.get("id"), i, j))
                cands.append({
                    "id": "r%d" % j,
                    "text": t,
                    "char_len": char_len(t),
                    "number_ok": ok_nums,
                    "entity_ok": ok_ents,
                })
            unit_records.append({
                "id": "u%02d" % i,
                "start": cursor,
                "end": cursor + len(unit),
                "original": unit,
                "char_len": len(unit),
                "candidates": cands,
                "selected": "r1",
                "selected_text": cands[0]["text"] if cands else "",
            })
            cursor += len(unit)
        covered = sum(len(u["original"]) for u in unit_records)
        sections_out.append({
            "id": str(sec.get("id")),
            "title": str(sec.get("title")),
            "source_chars": len(text),
            "unit_count": len(unit_records),
            "units": unit_records,
            "coverage": round(covered / len(text), 4) if text else 0.0,
            "char_len": sum(len(u["original"]) for u in unit_records),
        })

    artifact: Dict[str, Any] = {
        "artifact": "rewrite",
        "version": "1.0",
        "generated_at": now_iso(),
        "topic_id": drafts.get("topic_id", ""),
        "sections": sections_out,
        "chapter_ids": [s["id"] for s in sections_out],
        "review_dims": [f.get("dim") for f in (review.get("findings") or [])],
        "mismatches": mismatches,
        "gate": {},
    }
    artifact["gate"] = check(artifact, drafts)
    return artifact


def recheck_facts(artifact: Dict[str, Any], entities: List[str] | None = None) -> Dict[str, Any]:
    """独立复核单元候选的数字/专名是否与原文一致（不信任生成时写入的 mismatches）。"""
    entities = entities or []
    bad: List[str] = []
    for sec in artifact.get("sections") or []:
        for u in sec.get("units") or []:
            ref_nums = Counter(number_tokens(str(u.get("original") or "")))
            ref_ents = set(entities_in(str(u.get("original") or ""), entities))
            for c in u.get("candidates") or []:
                t = str(c.get("text") or "")
                if Counter(number_tokens(t)) != ref_nums:
                    bad.append("%s:%s:%s:数字" % (sec.get("id"), u.get("id"), c.get("id")))
                if entities and set(entities_in(t, entities)) != ref_ents:
                    bad.append("%s:%s:%s:专名" % (sec.get("id"), u.get("id"), c.get("id")))
    return gate([ck(not bad, "数字/专名与原文一致且不新增事实", "rewrite.facts",
                    "CRITICAL" if bad else "OK", offenders=bad)], "rewrite")


def check(artifact: Dict[str, Any], drafts: Dict[str, Any] | None = None) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    secs = artifact.get("sections") or []
    if drafts is not None:
        same = [s.get("id") for s in secs] == [s.get("id") for s in (drafts.get("sections") or [])]
        checks.append(ck(same, "改写章节与草稿章节一致", "rewrite.chapters",
                         "CRITICAL" if not same else "OK"))
    lo = THRESHOLDS["rewrite"]["unit_min"]
    hi = THRESHOLDS["rewrite"]["unit_max"]
    bad_units, bad_counts = [], []
    for s in secs:
        for u in s.get("units") or []:
            if not (lo <= len(str(u.get("original", ""))) <= hi):
                bad_units.append("%s:%s" % (s.get("id"), u.get("id")))
            n = len(u.get("candidates") or [])
            if not (THRESHOLDS["rewrite"]["min_candidates"] <= n
                    <= THRESHOLDS["rewrite"]["max_candidates"]):
                bad_counts.append("%s:%s=%d" % (s.get("id"), u.get("id"), n))
    checks.append(ck(not bad_units, "每个单元 %d–%d 字" % (lo, hi), "rewrite.units",
                     "CRITICAL" if bad_units else "OK", offenders=bad_units))
    checks.append(ck(not bad_counts, "每单元 2–4 个候选", "rewrite.candidates",
                     "CRITICAL" if bad_counts else "OK", offenders=bad_counts))
    low = ["%s=%.2f" % (s.get("id"), float(s.get("coverage") or 0))
           for s in secs if float(s.get("coverage") or 0) < 1.0]
    checks.append(ck(not low, "覆盖率 100%", "rewrite.coverage",
                     "CRITICAL" if low else "OK", offenders=low))
    mism = list(artifact.get("mismatches") or [])
    checks.append(ck(not mism, "数字/专名与原文一致且不新增事实", "rewrite.facts",
                     "CRITICAL" if mism else "OK", offenders=mism))
    return gate(checks, "rewrite")

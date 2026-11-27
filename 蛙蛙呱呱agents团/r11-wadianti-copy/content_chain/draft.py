# -*- coding: utf-8 -*-
"""第 4 段 draft：单节三候选（结论先行 / 数字先行 / 反例先行）。

硬约束：
  - 确定性生成：模板 + 输入事实拼接，不调用模型；
  - 先删公共轨道表达，再算多样性（≥0.6）与分数（≥85）；
  - 三条候选共享事实但组织方式不同，禁止只换形容词。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import (THRESHOLDS, char_len, ck, claim_index, diversity,
                     entities_in, fluff_count, gate, max_similarity, now_iso,
                     number_tokens, source_index, strip_common_tracks)

VAGUE_WORDS = ("很多", "一些", "大家", "往往", "通常", "相关", "某种")


def _score(text: str) -> int:
    penalty = 4 * fluff_count(text) + 2 * sum(text.count(w) for w in VAGUE_WORDS)
    if char_len(text) < 150:
        penalty += 10
    return int(max(0, 100 - penalty))


def _question_of(blocker: str) -> str:
    return str(blocker or "").replace("读者读到这里会卡在：", "").strip()


def _end(text: Any) -> str:
    """去掉句末标点，避免模板拼接出「。。」「？。」。"""
    return str(text or "").strip().rstrip("。！？；;.!?")


def _tracks(section: Dict[str, Any], claim: Dict[str, Any],
            src: Dict[str, Any], idx: int, audience: str) -> List[Dict[str, str]]:
    statement = _end(claim.get("statement"))
    quote = _end(src.get("quote"))
    title = _end(src.get("title")) or "来源"
    nums = [str(n) for n in (claim.get("numbers") or []) if str(n).strip()]
    num_sentence = ("数字核对：%s。" % "、".join(nums)) if nums else ""
    blocker = str(section.get("reader_blocker") or "").strip()
    example = _end(section.get("example"))
    difficulty = _end(section.get("logic_difficulty"))
    promise = _end(section.get("promise"))
    question = _end(_question_of(blocker))

    track_a = "".join([
        "需要指出的是，结论：%s。" % statement,
        "证据：%s。" % quote,
        num_sentence,
        "边界：这条判断只在来源可回溯、口径一致时成立；%s。" % difficulty,
        "%s。" % _end(blocker),
        "%s。" % promise,
        "对%s来说，这一条直接决定下一步动作是否值得做。" % (audience or "读者"),
        "这一步不做，后面的动作就缺少判断依据，返工概率会明显上升。",
    ])
    if idx == 0:
        track_a += "从这个角度看，这一节是整条链的起点。"

    track_b = "".join([
        "需要指出的是，%s" % ("先看数字：%s，这是本节要核对的全部数字。" % "、".join(nums)
                              if nums else "先看一个具体场景。"),
        "%s。" % example,
        "证据来自%s：%s。" % (title, quote),
        "%s。" % promise,
        "复用成本在于每次都要重新核对来源；%s。" % difficulty,
    ])

    track_c = "".join([
        "需要指出的是，先讲一个反例：%s。" % question,
        "如果只记住结论，很容易忽略条件；%s。" % statement,
        "%s。" % example,
        "反过来看，条件不成立时，这条证据并不能支撑同样的判断。",
        "来源仍是%s：%s。" % (title, quote),
    ])

    return [
        {"id": "A", "track": "结论先行", "text": strip_common_tracks(track_a)},
        {"id": "B", "track": "数字先行", "text": strip_common_tracks(track_b)},
        {"id": "C", "track": "反例先行", "text": strip_common_tracks(track_c)},
    ]


def build(outline: Dict[str, Any], research: Dict[str, Any],
          brief: Dict[str, Any]) -> Dict[str, Any]:
    brief = brief or {}
    entities = [str(e) for e in (brief.get("entities") or []) if str(e).strip()]
    audience = str(brief.get("audience") or "读者").strip()
    srcs = source_index(research)
    claims = claim_index(research)
    sections_out: List[Dict[str, Any]] = []

    for idx, sec in enumerate(outline.get("sections") or []):
        claim = claims.get(str(sec.get("claim_id"))) or {}
        src_id = (claim.get("source_ids") or [""])[0]
        src = srcs.get(str(src_id)) or {"title": "待补来源", "quote": "来源原文待补，需先完成证据台账。"}
        cands = _tracks(sec, claim, src, idx, audience)
        for c in cands:
            c["score"] = _score(c["text"])
            c["char_len"] = char_len(c["text"])
            c["fluff"] = fluff_count(c["text"])
            c["numbers"] = number_tokens(c["text"])
            c["entities"] = entities_in(c["text"], entities)
        # 选稿规则固定：结论先行轨为默认稿；它承载“结论→证据→边界”的完整结构，
        # 另两轨作为对照，防止编辑部只看分数挑到结构不完整的版本。
        best = cands[0]
        texts = [c["text"] for c in cands]
        sections_out.append({
            "id": str(sec.get("id")),
            "title": str(sec.get("title")),
            "claim_id": str(sec.get("claim_id")),
            "candidates": cands,
            "diversity": diversity(texts),
            "max_similarity": max_similarity(texts),
            "selected_id": best["id"],
            "selected_track": best["track"],
            "selected_text": best["text"],
            "selected_score": best["score"],
            "selected_reason": ("结论先行轨得分 %d（≥%d），且完整覆盖结论、证据、边界三层；"
                                "三候选两两最大相似度 %.2f，多样性 %.2f；事实均来自 %s。") % (
                                    best["score"], THRESHOLDS["draft"]["min_score"],
                                    max_similarity(texts), diversity(texts),
                                    str(src.get("title"))),
        })

    artifact: Dict[str, Any] = {
        "artifact": "drafts",
        "version": "1.0",
        "generated_at": now_iso(),
        "topic_id": outline.get("topic_id", ""),
        "sections": sections_out,
        "chapter_ids": [s["id"] for s in sections_out],
        "gate": {},
    }
    artifact["gate"] = check(artifact, outline)
    return artifact


def check(artifact: Dict[str, Any], outline: Dict[str, Any] | None = None) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    secs = artifact.get("sections") or []
    if outline is not None:
        same = [s.get("id") for s in secs] == [s.get("id") for s in (outline.get("sections") or [])]
        checks.append(ck(same, "草稿章节与细纲章节一致", "draft.chapters",
                         "CRITICAL" if not same else "OK"))
    need = THRESHOLDS["draft"]["candidates"]
    bad_counts = [s.get("id") for s in secs if len(s.get("candidates") or []) != need]
    checks.append(ck(not bad_counts, "每节候选数 = %d" % need, "draft.candidates",
                     "CRITICAL" if bad_counts else "OK", offenders=bad_counts))
    low_div = ["%s=%.2f" % (s.get("id"), float(s.get("diversity") or 0))
               for s in secs if float(s.get("diversity") or 0) < THRESHOLDS["draft"]["min_diversity"]]
    checks.append(ck(not low_div, "多样性 ≥ %.1f" % THRESHOLDS["draft"]["min_diversity"],
                     "draft.diversity", "CRITICAL" if low_div else "OK",
                     offenders=low_div))
    low_score = ["%s=%s" % (s.get("id"), s.get("selected_score"))
                 for s in secs if int(s.get("selected_score") or 0) < THRESHOLDS["draft"]["min_score"]]
    checks.append(ck(not low_score, "选中稿分数 ≥ %d" % THRESHOLDS["draft"]["min_score"],
                     "draft.score", "CRITICAL" if low_score else "OK",
                     offenders=low_score))
    lacks_reason = [s.get("id") for s in secs
                    if not str(s.get("selected_reason", "")).strip()]
    checks.append(ck(not lacks_reason, "选中稿有理由", "draft.reason",
                     "CRITICAL" if lacks_reason else "OK", offenders=lacks_reason))
    has_track = []
    for s in secs:
        if "需要指出的是" in str(s.get("selected_text", "")):
            has_track.append(s.get("id"))
        for c in s.get("candidates") or []:
            if "需要指出的是" in str(c.get("text", "")):
                has_track.append("%s:%s" % (s.get("id"), c.get("id")))
    checks.append(ck(not has_track, "公共轨道表达已删除", "draft.common_track",
                     "CRITICAL" if has_track else "OK", offenders=has_track))
    return gate(checks, "draft")

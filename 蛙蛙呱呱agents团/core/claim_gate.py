# -*- coding: utf-8 -*-
"""core/claim_gate —— 把 ClaimCard 的“头条资格”接进 report build（P9）。

只做三条硬规则（不替代完整 ClaimCard.validate）：

1. 头条必须是 actionable；
2. actionable 必须有 falsifier；
3. 头条引用的来源必须 verified 且 grade ≤ B。

不满足 → 该断言不进标题（standfirst 降级为“待验证”），正文保留。
可用 REPORT_CLAIM_GATE=0 临时关闭（只用于回滚）。
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Tuple

from core.claim_card import ClaimCard, Rival, validate

SAFE_HEADLINE = "本报告含 1 条待验证判断；标题不承载未核验断言，见正文。"


def _source_map(pack: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    recs = {str(r.get("id")): r for r in (pack.get("source_records") or [])}
    num_src: Dict[str, str] = {}
    for n in pack.get("numbers") or []:
        sid = str(n.get("source_ref") or "")
        if sid:
            num_src[str(n.get("id"))] = sid
    return recs, num_src


def _resolve(refs: List[str], pack: Dict[str, Any]) -> List[str]:
    recs, num_src = _source_map(pack)
    nums = {str(n.get("id")): n for n in (pack.get("numbers") or [])}
    out: List[str] = []
    for ref in refs:
        sid = str(ref).split("#")[0]
        if sid in recs:
            out.append(sid)
        elif sid in num_src and num_src[sid] in recs:
            out.append(num_src[sid])
        elif sid in nums and str((nums[sid] or {}).get("source_file") or "").strip():
            # 内部数据文件：按 B 级可复现数据处理，不需要 web quote。
            out.append("FILE:" + str(nums[sid]["source_file"]))
        elif re.fullmatch(r"S\d+", sid):
            out.append(sid)
    return sorted(set(out))


def _falsifier(draft: Dict[str, Any], findings: List[Any] | None = None) -> str:
    if str(draft.get("falsifier") or "").strip():
        return str(draft["falsifier"])
    for f in findings or []:
        cl = getattr(f, "claim", None) or (getattr(f, "meta", None) or {}).get("claim")
        if cl is not None and str(getattr(cl, "falsifier", "") or "").strip():
            return str(cl.falsifier)
    for s in draft.get("sections") or []:
        if str(s.get("falsifier") or "").strip():
            return str(s["falsifier"])
    for s in draft.get("sections") or []:
        for r in s.get("reading") or []:
            if "证伪" in str(r.get("strong") or "") or "证伪" in str(r.get("text") or "")[:8]:
                return str(r.get("text") or "")
    return ""


def assess(draft: Dict[str, Any], pack: Dict[str, Any],
           findings: List[Any] | None = None) -> Dict[str, Any]:
    """返回 {ok, actionable, demoted, reasons, sources, grades, falsifier}。"""
    sections = draft.get("sections") or []
    refs: List[str] = []
    lead_falsifier = ""
    for f in findings or []:
        cl = getattr(f, "claim", None) or (getattr(f, "meta", None) or {}).get("claim")
        if cl is not None and str(getattr(cl, "falsifier", "") or "").strip() \
                and (getattr(cl, "refs", None) or []):
            refs = [str(x) for x in cl.refs]
            lead_falsifier = str(cl.falsifier)
            break
    if not refs:
        for s in sections:
            if s.get("falsifier") and s.get("refs"):
                refs = [str(x) for x in (s.get("refs") or [])]
                lead_falsifier = str(s.get("falsifier"))
                break
    if not refs and sections:
        refs = [str(x) for x in (sections[0].get("refs") or [])]
    sources = _resolve(refs, pack)
    recs, _ = _source_map(pack)
    grades: List[str] = []
    statuses: List[str] = []
    for s in sources:
        if s.startswith("FILE:"):
            grades.append("B")
            statuses.append("internal")
        else:
            grades.append(str((recs.get(s) or {}).get("grade") or "D").upper()[:1])
            statuses.append(str((recs.get(s) or {}).get("quote_status") or "unverified"))
    falsifier = lead_falsifier or _falsifier(draft, findings)
    decision = str(draft.get("intent") or "")

    reasons: List[str] = []
    if not refs:
        reasons.append("没有 refs")
    if not sources:
        reasons.append("refs 无法解析到来源")
    bad_grade = [s for s, g in zip(sources, grades) if g not in ("A", "B")]
    if bad_grade:
        reasons.append("来源等级 > B：" + ", ".join(bad_grade))
    bad_quote = [s for s, st in zip(sources, statuses) if st not in ("ok", "internal")]
    if bad_quote:
        reasons.append("来源未核验：" + ", ".join(bad_quote))
    if not falsifier:
        reasons.append("没有 falsifier")
    if not decision:
        reasons.append("没有 decision")

    actionable = not reasons

    # P11：完整 ClaimCard（comparability/rivals）审计；REPORT_CLAIM_CARD_GATE=1 时硬门禁。
    nums = {str(n.get("id")): n for n in (pack.get("numbers") or [])}
    periods = set()
    units = set()
    files = set()
    for ref in refs:
        sid = str(ref).split("#")[0]
        n = nums.get(sid) or {}
        if n.get("period"):
            periods.add(str(n["period"]))
        if n.get("unit"):
            units.add(str(n["unit"]))
        if n.get("source_file"):
            files.add(str(n["source_file"]))
    all_file = bool(sources) and all(s.startswith("FILE:") for s in sources)
    comparability = {
        "same_product": "yes" if all_file and len(files) == 1 else "n/a",
        "same_period": "yes" if periods and len(periods) == 1 else "unknown",
        "same_unit": "yes" if units and len(units) == 1 else "unknown",
        "same_channel": "n/a" if all_file else "unknown",
    }
    rivals = [Rival("口径/时点差异", "partially_ruled",
                    "引用同项目来源；期次与单位已记录")] if sources else []
    grade = "A" if grades and all(g == "A" for g in grades) else (
        "B" if grades and all(g in ("A", "B") for g in grades) else "C")
    card = ClaimCard(
        id="H1", statement=str(draft.get("standfirst") or ""), refs=refs,
        values={"sources": len(sources)}, comparability=comparability,
        rivals=rivals, falsifier=falsifier, confidence="medium", grade=grade,
        actionable=actionable, headline=actionable, decision=decision,
        owner="r01", kind="headline",
    )
    v = validate(card)
    full_ok = bool(v["ok"])
    if (os.environ.get("REPORT_CLAIM_CARD_GATE", "0") == "1"
            and actionable and not full_ok):
        actionable = False
        reasons = reasons + ["完整 ClaimCard：" + e for e in v["errors"]]

    return {
        "schema": "dsh.claim_gate/v1",
        "ok": True,                 # 门禁本身可用；是否降级看 demoted
        "actionable": actionable,
        "demoted": not actionable,
        "reasons": reasons,
        "sources": sources,
        "grades": grades,
        "falsifier": falsifier,
        "decision": decision,
        "comparability": comparability,
        "rivals": [r.__dict__ for r in rivals],
        "full_schema_ok": full_ok,
        "card_errors": v["errors"],
        "card": card.to_dict(),
    }


def apply(draft: Dict[str, Any], pack: Dict[str, Any],
          findings: List[Any] | None = None) -> Dict[str, Any]:
    info = assess(draft, pack, findings)
    if not info["actionable"]:
        draft["standfirst"] = SAFE_HEADLINE
        draft["headline_demoted"] = True
    draft["claim_gate"] = info
    return info

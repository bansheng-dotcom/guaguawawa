# -*- coding: utf-8 -*-
"""s01 深度研究（research）：ledger / report 两动作。

- ledger：构建/校验证据台账——claims 与 sources 的交叉引用、类型白名单、覆盖率。
- report：生成研究报告脚手架——sections 引用的 claim 必须存在且每条 claim 须有来源。
阈值：thresholds.json → research.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "research"
DESC = "深度研究：证据台账与研究报告"

ACTIONS = {
    "ledger": "构建/校验证据台账",
    "report": "生成研究报告脚手架",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# ledger
# --------------------------------------------------------------------------- #
def ledger(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["research"]
    claim_kinds = th["claim_kinds"]
    source_types = th["source_types"]
    min_sources = th["min_sources_per_claim"]

    sources = data.get("sources") or []
    claims = data.get("claims") or []
    checks: List[Dict[str, Any]] = []

    if not sources and not claims:
        checks.append(c.ck(False, "sources 与 claims 均为空，无台账可构建", "research:ledger", "CRITICAL"))

    source_ids = {str(s.get("id") or "") for s in sources}

    orphan_claims: List[Dict[str, Any]] = []
    unverified_sources: List[str] = [str(s.get("id") or "") for s in sources]
    cited_source_ids: set = set()

    for cl in claims:
        cl_id = str(cl.get("id") or "")
        kind = str(cl.get("kind") or "")
        text = str(cl.get("text") or "")
        sids = [str(sid) for sid in (cl.get("source_ids") or [])]

        # claim.kind 白名单
        if kind not in claim_kinds:
            checks.append(c.ck(False, f"claim {cl_id} kind={kind!r} 不在白名单", "research:claim_kind", "HIGH", **{"claim_id": cl_id}))
        else:
            checks.append(c.ck(True, f"claim {cl_id} kind={kind} 合规", "research:claim_kind", **{"claim_id": cl_id}))

        # source_ids 指向存在的 source
        for sid in sids:
            if sid not in source_ids:
                checks.append(c.ck(False, f"claim {cl_id} 引用了不存在的 source {sid!r}", "research:dangling_ref", "HIGH", **{"claim_id": cl_id, "source_id": sid}))
            else:
                cited_source_ids.add(sid)

        # orphan claim
        if not sids:
            orphan_claims.append({"claim_id": cl_id, "text": text[:80]})
            checks.append(c.ck(False, f"claim {cl_id} 无来源引用（orphan）", "research:orphan_claim", "HIGH", **{"claim_id": cl_id}))
        elif len(sids) < min_sources:
            checks.append(c.ck(False, f"claim {cl_id} 来源数 {len(sids)} < 最低要求 {min_sources}", "research:min_sources", "HIGH", **{"claim_id": cl_id}))
        else:
            checks.append(c.ck(True, f"claim {cl_id} 来源充足（{len(sids)} 条）", "research:min_sources", **{"claim_id": cl_id}))

    # source type 白名单
    for s in sources:
        sid = str(s.get("id") or "")
        stype = str(s.get("type") or "")
        if stype not in source_types:
            checks.append(c.ck(False, f"source {sid} type={stype!r} 不在白名单", "research:source_type", "HIGH", **{"source_id": sid}))
        else:
            checks.append(c.ck(True, f"source {sid} type={stype} 合规", "research:source_type", **{"source_id": sid}))

    unverified_sources = [sid for sid in [str(s.get("id") or "") for s in sources] if sid not in cited_source_ids]
    claims_with_sources = sum(1 for cl in claims if (cl.get("source_ids") or []))
    total_claims = len(claims)
    coverage_rate = (claims_with_sources / total_claims) if total_claims > 0 else 0.0

    for sid in unverified_sources:
        checks.append(c.ck(True, f"source {sid} 未被任何 claim 引用", "research:unverified_source", "INFO", **{"source_id": sid}))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   source_count=len(sources),
                   claim_count=len(claims),
                   orphan_claims=orphan_claims,
                   unverified_sources=unverified_sources,
                   coverage_rate=round(coverage_rate, 4),
                   verdict=verdict,
                   next="证据台账完整" if ok else "修复 orphan claims 与无效引用后重新 ledger",
                   )
    return out


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def report(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["research"]
    claims = data.get("claims") or []
    sources = data.get("sources") or []
    sections = data.get("sections") or []
    checks: List[Dict[str, Any]] = []

    if not sections:
        checks.append(c.ck(False, "sections 为空，无报告可生成", "research:report", "CRITICAL"))

    claim_ids = {str(cl.get("id") or "") for cl in claims}
    source_ids = {str(s.get("id") or "") for s in sources}

    orphan_claims: List[str] = []
    sections_with_full_citation = 0

    for sec in sections:
        title = str(sec.get("title") or "")
        sec_claim_ids = [str(cid) for cid in (sec.get("claim_ids") or [])]
        all_sourced = True

        for cid in sec_claim_ids:
            if cid not in claim_ids:
                orphan_claims.append(cid)
                checks.append(c.ck(False, f"section {title!r} 引用了不存在的 claim {cid!r}", "research:dangling_claim", "HIGH", **{"section": title, "claim_id": cid}))
                all_sourced = False
            else:
                # 检查该 claim 是否有 source_ids
                cl = next((x for x in claims if str(x.get("id") or "") == cid), None)
                if cl:
                    cl_sids = [str(sid) for sid in (cl.get("source_ids") or [])]
                    if not cl_sids:
                        checks.append(c.ck(False, f"claim {cid} 无来源引用", "research:unsourced_claim", "HIGH", **{"claim_id": cid}))
                        all_sourced = False
                    else:
                        for sid in cl_sids:
                            if sid not in source_ids:
                                checks.append(c.ck(False, f"claim {cid} 引用了不存在的 source {sid!r}", "research:dangling_source", "HIGH", **{"claim_id": cid, "source_id": sid}))
                                all_sourced = False

        if sec_claim_ids and all_sourced:
            sections_with_full_citation += 1
            checks.append(c.ck(True, f"section {title!r} 全部 claim 有来源", "research:section_citation", **{"section": title}))

    total_sections = len(sections)
    citation_coverage = (sections_with_full_citation / total_sections) if total_sections > 0 else 0.0

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   sections_checked=total_sections,
                   citation_coverage=round(citation_coverage, 4),
                   orphan_claims=orphan_claims,
                   verdict=verdict,
                   next="报告脚手架完整" if ok else "修复悬空 claim 引用与无来源 claim 后重新 report",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "ledger":
        result = ledger(data)
    elif args.action == "report":
        result = report(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result

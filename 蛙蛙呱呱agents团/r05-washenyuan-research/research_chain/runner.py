# -*- coding: utf-8 -*-
"""研究链编排器：一条命令跑完 8 段，产出 8 个 JSON + research_manifest.json。

manifest 记录：
- 每个工件的 sha256、阶段门禁是否通过；
- 跨段一致性（结论引用存在源、矩阵每格有源、份额与 size 口径一致、
  假设挂证据、子问题有证据）；
- 总门禁 `ok` 与等级 `grade`。

`audit(out_dir)` 会重算 sha256 与全部门禁，用于发现“文件被手改”或“门禁被绕过”。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from . import collect, compete, report, scope, size, source, triangulate, verify
from .common import (MANIFEST_FILE, REPORT_HTML, REPORT_MD, STAGE_FILES, STAGE_ORDER,
                     ck, file_sha256, gate, now_iso, read_json, write_json, write_text)

CHECKERS = {
    "scope": scope.check_scope,
    "source": source.check_source_map,
    "collect": collect.check_ledger,
    "verify": verify.check_verification,
    "triangulate": triangulate.check_synthesis,
    "size": size.check_sizing,
    "compete": compete.check_competition,
    "report": report.check_report,
}


def _source_ids(source_map: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    for entry in source_map.get("entries") or []:
        for cand in entry.get("candidates") or []:
            ids.append(str(cand.get("id")))
    return sorted(set(ids))


def cross_checks(plan: Dict[str, Any], source_map: Dict[str, Any],
                 ledger: Dict[str, Any], sizing: Dict[str, Any],
                 competition: Dict[str, Any], synthesis: Dict[str, Any],
                 report_art: Dict[str, Any]) -> List[Dict[str, Any]]:
    """跨段一致性检查：任何一条失败都说明链内自相矛盾。"""
    ledger_sources = {str(e.get("source_id")) for e in ledger.get("entries") or []}
    ledger_evidence = {str(e.get("evidence_id")) for e in ledger.get("entries") or []}
    map_sources = set(_source_ids(source_map))
    conclusions = synthesis.get("conclusions") or []

    conclusion_ok = all(sid in ledger_sources for c in conclusions
                        for sid in (c.get("source_ids") or []))
    cell_sources = {str((p.get("cells") or {}).get(d, {}).get("source_id"))
                    for p in competition.get("competitors") or []
                    for d in competition.get("dimensions") or []}
    cell_ok = cell_sources <= map_sources
    p50 = float((sizing.get("monte_carlo") or {}).get("p50") or 0)
    market = float(competition.get("market_size") or 0)
    size_ok = p50 > 0 and abs(market - p50) / p50 <= 0.05
    shares = [float(s.get("share") or 0) for s in competition.get("shares") or []]
    share_ok = len(shares) == 5 and all(0 < s <= 100 for s in shares) and sum(shares) <= 100.5
    assumption_ok = all(str(a.get("evidence_id")) in ledger_evidence
                        for a in sizing.get("assumptions") or [])
    sq_with_evidence = {str(e.get("subquestion_id")) for e in ledger.get("entries") or []}
    sq_ok = all(str(sq.get("id")) in sq_with_evidence
                for sq in plan.get("subquestions") or [])
    report_ok = all(sid in ledger_sources for row in report_art.get("conclusions_trace") or []
                    for sid in (row.get("source_ids") or []))

    return [
        ck("cross:conclusion_sources_exist", conclusion_ok,
           "结论来源必须存在于证据台账"),
        ck("cross:cell_sources_exist", cell_ok,
           "竞品矩阵每格来源必须存在于源地图"),
        ck("cross:market_size_consistency", size_ok,
           "竞争格局市场规模=%.2f，size p50=%.2f，偏差需 ≤5%%" % (market, p50)),
        ck("cross:shares_sum", share_ok, "5 家份额需为正且合计 ≤100%"),
        ck("cross:assumption_evidence", assumption_ok,
           "测算假设必须挂到台账证据"),
        ck("cross:subquestion_coverage", sq_ok,
           "每个子问题至少 1 条证据"),
        ck("cross:report_traceability", report_ok,
           "报告结论的来源必须存在于台账"),
    ]


def run_fixture(fixture_path: str, out_dir: str, seed: int = size.MC_SEED) -> Dict[str, Any]:
    """执行 8 段并落盘；返回 manifest。"""
    data = read_json(fixture_path)
    os.makedirs(out_dir, exist_ok=True)

    plan = scope.build(data.get("question", ""), data.get("decision_use", ""),
                       data.get("subquestions"), data.get("market_scope", ""))
    source_map = source.build(plan, data.get("sources") or [])
    ledger = collect.build(plan, source_map, data.get("evidence") or [])
    verification = verify.build(ledger, source_map, str(data.get("as_of") or ""))
    synthesis = triangulate.build(plan, ledger, verification)
    sizing = size.build(data.get("sizing") or {}, seed=seed)
    competition = compete.build(data.get("competition") or {}, source_map, ledger)
    report_art = report.build(plan, ledger, verification, synthesis, sizing,
                              competition, data.get("limits") or [])

    artifacts = {
        "scope": plan, "source": source_map, "collect": ledger, "verify": verification,
        "triangulate": synthesis, "size": sizing, "compete": competition,
        "report": report_art,
    }
    stages: List[Dict[str, Any]] = []
    for stage in STAGE_ORDER:
        path = os.path.join(out_dir, STAGE_FILES[stage])
        digest = write_json(path, artifacts[stage])
        stages.append({
            "stage": stage,
            "file": STAGE_FILES[stage],
            "sha256": digest,
            "gate": artifacts[stage].get("gate", {}).get("ok", False),
            "gate_failed": artifacts[stage].get("gate", {}).get("failed", []),
        })
    md_digest = write_text(os.path.join(out_dir, REPORT_MD), report_art["markdown"])
    html_digest = write_text(os.path.join(out_dir, REPORT_HTML), report_art["html"])
    stages.append({"stage": "report_markdown", "file": REPORT_MD, "sha256": md_digest,
                   "gate": True, "gate_failed": []})
    stages.append({"stage": "report_html", "file": REPORT_HTML, "sha256": html_digest,
                   "gate": True, "gate_failed": []})

    cross = cross_checks(plan, source_map, ledger, sizing, competition, synthesis, report_art)
    cross_gate = gate(cross)
    stage_ok = all(s["gate"] for s in stages)
    manifest: Dict[str, Any] = {
        "artifact": "research_manifest",
        "version": "1.0",
        "research_id": str(data.get("research_id") or "r05-research"),
        "question": plan.get("question"),
        "fixture": os.path.abspath(fixture_path),
        "generated_at": now_iso(),
        "stage_order": list(STAGE_ORDER),
        "stages": stages,
        "cross_checks": cross_gate,
        "gate": {
            "stage_gates": stage_ok,
            "cross_checks": cross_gate["ok"],
            "ok": stage_ok and cross_gate["ok"],
        },
        "ok": stage_ok and cross_gate["ok"],
        "grade": "A" if stage_ok and cross_gate["ok"] else "F",
    }
    write_json(os.path.join(out_dir, MANIFEST_FILE), manifest)
    return manifest


def audit(out_dir: str) -> Dict[str, Any]:
    """复核一个已落盘的研究链目录：sha256 + 重算门禁 + 跨段一致。"""
    checks: List[Dict[str, Any]] = []
    manifest_path = os.path.join(out_dir, MANIFEST_FILE)
    if not os.path.isfile(manifest_path):
        return {"ok": False, "checks": [ck("audit:manifest_exists", False, manifest_path)]}
    manifest = read_json(manifest_path)
    artifacts: Dict[str, Any] = {}
    for row in manifest.get("stages") or []:
        name = str(row.get("file"))
        path = os.path.join(out_dir, name)
        exists = os.path.isfile(path)
        checks.append(ck("audit:file_exists:%s" % name, exists, path))
        if not exists:
            continue
        digest = file_sha256(path)
        checks.append(ck("audit:sha256:%s" % name, digest == row.get("sha256"),
                         "manifest=%s disk=%s" % (row.get("sha256"), digest)))
        if str(row.get("stage")) in STAGE_FILES:
            artifacts[str(row.get("stage"))] = read_json(path)

    missing = [s for s in STAGE_ORDER if s not in artifacts]
    checks.append(ck("audit:eight_stages", not missing, "缺失阶段：%s" % (missing or "无")))
    if not missing:
        for stage in STAGE_ORDER:
            result = CHECKERS[stage](artifacts[stage])
            checks.append(ck("audit:gate:%s" % stage, result["ok"],
                             "失败：%s" % (result["failed"] or "无")))
        cross = cross_checks(artifacts["scope"], artifacts["source"], artifacts["collect"],
                             artifacts["size"], artifacts["compete"],
                             artifacts["triangulate"], artifacts["report"])
        checks.append(ck("audit:cross_checks", all(c["ok"] for c in cross),
                         "失败：%s" % [c["id"] for c in cross if not c["ok"]]))
    result = gate(checks)
    return {"ok": result["ok"], "verdict": "PASS" if result["ok"] else "FAIL",
            "checks": result["checks"], "failed": result["failed"],
            "research_id": manifest.get("research_id")}

# -*- coding: utf-8 -*-
"""工作流编排：run 一条命令跑指定工作流或全链，产出各包 JSON + workflow_manifest.json。

manifest 记录：每段 sha256、门禁等级/结论、交接回链；任一段 BLOCKER 失败即停止
后续阶段，manifest 置 FAIL（不静默降级）。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from . import acceptance, briefing, common as c, discovery, experience, prd, priority, render

STAGE_ORDER = ("experience", "discovery", "prd", "priority", "acceptance", "briefing")
FILES = {
    "discovery": "discovery_pack.json",
    "prd": "prd_pack.json",
    "priority": "priority_pack.json",
    "acceptance": "acceptance_pack.json",
    "briefing": "briefing_pack.json",
    "experience": "experience_brief.json",
}
_BUILDERS = {
    "discovery": discovery.build,
    "prd": prd.build,
    "priority": priority.build,
    "acceptance": acceptance.build,
    "briefing": briefing.build,
    "experience": experience.build,
}


def _stages_for(flow: str, payload: Dict[str, Any]) -> List[str]:
    flow = (flow or "all").strip()
    if flow in ("all", ""):
        return [s for s in STAGE_ORDER if isinstance(payload.get(s), dict)]
    if flow == "discovery_prd":
        return ["discovery", "prd"]
    if flow == "prd_priority":
        return ["prd", "priority"]
    stages = [s.strip() for s in flow.split(",") if s.strip()]
    for s in stages:
        if s not in _BUILDERS:
            raise ValueError(f"未知工作流：{s}（可用 {list(_BUILDERS)} 或 all）")
    return stages


def _handoffs(artifacts: Dict[str, Dict[str, Any]], paths: Dict[str, str]) -> List[Dict[str, Any]]:
    """交接回链：上游包 → 下游包，携带上游 sha256。"""
    def ref(stage: str) -> Dict[str, str]:
        return {"file": FILES[stage], "sha256": c.sha256_file(paths[stage])}

    out: List[Dict[str, Any]] = []
    if "discovery" in artifacts and "prd" in artifacts:
        out.append({"from": "discovery", "to": "prd", "refs": [ref("discovery")]})
    if "prd" in artifacts and "acceptance" in artifacts:
        out.append({"from": "prd", "to": "acceptance", "refs": [ref("prd")]})
    if "priority" in artifacts and "briefing" in artifacts:
        out.append({"from": "priority", "to": "briefing", "refs": [ref("priority")]})
    if "briefing" in artifacts:
        upstream = [s for s in ("discovery", "prd", "priority", "acceptance")
                    if s in artifacts]
        if upstream:
            out.append({"from": ",".join(upstream), "to": "briefing",
                        "refs": [ref(s) for s in upstream]})
    return out


def run(flow: str, payload: Dict[str, Any], out_dir: str,
        html: Optional[str] = None, html_title: str = "R07 产品工作流") -> Dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    os.makedirs(out_dir, exist_ok=True)
    stages = _stages_for(flow, payload)

    artifacts: Dict[str, Dict[str, Any]] = {}
    paths: Dict[str, str] = {}
    checks: List[Dict[str, Any]] = []

    for stage in stages:
        data = payload.get(stage) if isinstance(payload.get(stage), dict) else payload
        pack = _BUILDERS[stage](data)
        path = os.path.join(out_dir, FILES[stage])
        c.write_json(path, pack)
        artifacts[stage] = pack
        paths[stage] = path
        g = pack.get("gate") or {}
        checks.append(c.ck(bool(g.get("ok")), f"{stage} 门禁={g.get('grade')}",
                           "chain.stage", "BLOCKER" if not g.get("ok") else "OK"))
        if not g.get("ok"):
            break

    handoffs = _handoffs(artifacts, paths)
    checks.append(c.ck(len(handoffs) > 0 or len(artifacts) <= 1,
                       "多段链路缺少交接回链", "chain.handoff", "MAJOR"))
    for item in handoffs:
        for ref in item.get("refs", []):
            p = os.path.join(out_dir, ref["file"])
            checks.append(c.ck(os.path.exists(p) and c.sha256_file(p) == ref["sha256"],
                               f"交接回链哈希不一致：{ref['file']}",
                               "chain.handoff", "BLOCKER"))

    g = c.gate(checks, "chain")
    manifest = {
        "artifact": "workflow_manifest",
        "version": "1.0",
        "flow": flow or "all",
        "stage_order": [s for s in STAGE_ORDER if s in artifacts],
        "stages": [
            {"stage": s, "file": FILES[s], "sha256": c.sha256_file(paths[s]),
             "gate": (artifacts[s].get("gate") or {}).get("grade"),
             "ok": bool((artifacts[s].get("gate") or {}).get("ok"))}
            for s in STAGE_ORDER if s in artifacts
        ],
        "handoffs": handoffs,
        "checks": g["checks"],
        "ok": g["ok"],
        "grade": g["grade"],
        "gate": g,
    }
    c.write_json(os.path.join(out_dir, "workflow_manifest.json"), manifest)

    if html:
        title = html_title
        render.write_html(html, title, "R07 · 5 条产品工作流 + 经验门",
                          [(FILES[s], artifacts[s])
                           for s in STAGE_ORDER if s in artifacts])
    return manifest


def audit(dir_path: str) -> Dict[str, Any]:
    """只读复核：文件齐全、哈希一致、门禁 PASS、交接回链可追。"""
    manifest_path = os.path.join(dir_path, "workflow_manifest.json")
    if not os.path.exists(manifest_path):
        return {"ok": False, "grade": "FAIL", "stage": "audit",
                "checks": [c.ck(False, f"缺少 {manifest_path}", "existence", "BLOCKER")],
                "errors": [f"缺少 {manifest_path}"], "stages": []}
    manifest = c.read_json(manifest_path)
    checks: List[Dict[str, Any]] = []
    for item in manifest.get("stages", []):
        p = os.path.join(dir_path, item.get("file", ""))
        checks.append(c.ck(os.path.exists(p), f"{item.get('stage')} 文件存在",
                           "audit.existence", "BLOCKER" if not os.path.exists(p) else "OK"))
        if os.path.exists(p):
            checks.append(c.ck(c.sha256_file(p) == item.get("sha256"),
                               f"{item.get('stage')} 哈希一致", "audit.integrity",
                               "BLOCKER" if c.sha256_file(p) != item.get("sha256") else "OK"))
    for item in manifest.get("handoffs", []):
        for ref in item.get("refs", []):
            p = os.path.join(dir_path, ref.get("file", ""))
            checks.append(c.ck(os.path.exists(p) and c.sha256_file(p) == ref.get("sha256"),
                               f"回链 {ref.get('file')} 可追", "audit.handoff", "BLOCKER"))
    checks.append(c.ck(bool(manifest.get("ok")), "manifest 判定为 PASS", "audit.gate",
                       "BLOCKER" if not manifest.get("ok") else "OK"))
    g = c.gate(checks, "audit")
    return {"ok": g["ok"], "grade": g["grade"], "stage": "audit",
            "artifact": "workflow_audit", "stages": manifest.get("stages", []),
            "checks": g["checks"], "errors": g["errors"], "gate": g}

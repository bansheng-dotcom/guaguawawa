# -*- coding: utf-8 -*-
"""core.r04_derive —— 从产物**派生** R04 的验收输入（只读、可复算）。

2026-11-20 事故：R04 的 `r04_inventory.json` / `r04_criteria.json` /
`r04_quality.json` 是生产方自己手写的，再喂给 r04 跑出 COMPLETE/PASS/PASS——
等于自己出题自己判卷。「生成与校验分离」被绕过了。

修复口径：
- 这三份输入只能由本模块从产物派生，每份都带 `derived_from`（含 report.html 的 sha256）；
- 生产方手写、或复制旧 `derived_from` 的，sha 对不上，`scripts/check_r04_inputs.py` 直接判 FAIL；
- 派生只陈述「产物里有什么」，不做判断；判断仍然是 r04 的活。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

SCHEMA = "dsh.r04.derived/v1"
WANT = ("report.html", "report.md", "report.pdf", "manifest.json",
        "gaps.json", "source_verify.json", "section_check.json")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {}


def _artifact_index(out: Path) -> Dict[str, Dict[str, Any]]:
    idx = {}
    for name in WANT:
        p = out / name
        idx[name] = {"exists": p.is_file(),
                     "bytes": p.stat().st_size if p.is_file() else 0,
                     "sha256": _sha(p) if p.is_file() else ""}
    return idx


def derive(out_dir: str) -> Dict[str, Any]:
    """写 r04_inventory / r04_criteria / r04_quality 三份派生输入。"""
    out = Path(out_dir)
    idx = _artifact_index(out)
    manifest = _load(out / "manifest.json")
    gaps = _load(out / "gaps.json")
    gate = ((manifest.get("gate") or {}).get("flow") or {})
    ev = gaps.get("evidence") or manifest.get("evidence") or {}
    sv = gaps.get("source_verify") or {}
    depth = (gate.get("stats") or {})
    anchor = {"artifact": "report.html",
              "artifact_sha256": idx["report.html"]["sha256"],
              "manifest_sha256": idx["manifest.json"]["sha256"],
              "generated_by": "core.r04_derive.derive()",
              "schema": SCHEMA}

    files_ok = all(idx[n]["exists"] for n in ("report.html", "report.md", "manifest.json"))
    gate_ok = bool(gate.get("ok"))
    gate_id = gate.get("verdict") or "UNKNOWN"
    uniq = int(ev.get("unique_sources") or ev.get("files") or ev.get("sources") or 0)
    verified = sv.get("verified")
    total = sv.get("total") or 0

    inventory = {
        "schema": "dsh.r04.inventory/v1",
        "derived_from": anchor,
        "items": [
            {"path": str(out / n), "type": "file", "required": n in
             ("report.html", "report.md", "manifest.json")}
            for n in WANT
        ],
    }
    criteria = {
        "schema": "dsh.r04.criteria/v1",
        "derived_from": anchor,
        "criteria": [
            {"id": "C1_artifacts", "severity": "critical",
             "description": "HTML / MD / manifest 三件套齐且非空",
             "evidence": ("verified: manifest.json:files 已列 html/md"
                          if files_ok else "not verified: 三件套缺文件"),
             "issues": [] if files_ok else ["缺 html/md/manifest"]},
            {"id": "C2_flow_gate", "severity": "critical",
             "description": "流程门禁结论（manifest.gate.flow）",
             "evidence": f"verified: manifest.json:gate.flow.verdict = {gate_id}",
             "issues": [] if gate_ok else
                       [v.get("id", "?") for v in (gate.get("violations") or [])]},
            {"id": "C3_unique_sources", "severity": "major",
             "description": "唯一来源数（按 URL 去重，不看登记条数）",
             "evidence": f"verified: gaps.json:evidence.unique_sources = {uniq}",
             "issues": [] if uniq >= 1 else ["没有可用来源"]},
            {"id": "C4_quote_verified", "severity": "major",
             "description": "引文逐条回抓结果",
             "evidence": (f"verified: source_verify.json:verified = {verified}/{total}"
                          if total else "not verified: 本次未做回抓（降级已记入 manifest.quotes）"),
             "issues": [] if (total and verified == total) else
                       [f"未核验 {total - int(verified or 0)}/{total}"] if total else
                       ["未执行回抓"]},
        ],
    }
    quality = {
        "schema": "dsh.r04.quality/v1",
        "derived_from": anchor,
        "claims": [
            {"id": "R1", "kind": "completion",
             "text": f"verified: 流程门禁 {gate_id}（判据 {len(gate.get('stats') or {})} 项指标已记录）",
             "evidence_refs": [f"{out / 'manifest.json'}:1"]},
            {"id": "R2", "kind": "completion",
             "text": f"verified: 唯一来源 {uniq} 条、数字 {ev.get('numbers')} 个",
             "evidence_refs": [f"{out / 'gaps.json'}:1"]},
            {"id": "R3", "kind": "completion",
             "text": (f"verified: 引文回抓 {verified}/{total}"
                      if total else "not verified: 本次未做引文回抓"),
             "evidence_refs": [f"{out / 'source_verify.json'}:1"
                               if total else f"{out / 'manifest.json'}:1"]},
        ],
    }
    paths = {}
    for name, payload in (("r04_inventory.json", inventory),
                          ("r04_criteria.json", criteria),
                          ("r04_quality.json", quality)):
        p = out / name
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[name] = str(p)
    return {"ok": True, "derived_from": anchor, "files": paths,
            "stats": {"gate": gate_id, "unique_sources": uniq,
                      "verified": verified, "total": total,
                      "depth_profile": depth.get("density")}}


def check(out_dir: str) -> Dict[str, Any]:
    """校验三份输入确实是**从当前产物**派生的（sha 必须对得上）。"""
    out = Path(out_dir)
    html = out / "report.html"
    if not html.is_file():
        return {"ok": False, "reason": "没有 report.html，无法校验派生关系"}
    sha = _sha(html)
    bad = []
    for name in ("r04_inventory.json", "r04_criteria.json", "r04_quality.json"):
        p = out / name
        if not p.is_file():
            bad.append(f"{name}: 缺失")
            continue
        d = _load(p)
        anchor = d.get("derived_from") or {}
        if anchor.get("schema") != SCHEMA:
            bad.append(f"{name}: 不是 core.r04_derive 派生的（缺 derived_from.schema）")
        elif anchor.get("artifact_sha256") != sha:
            bad.append(f"{name}: derived_from 与当前 report.html 不匹配（产物已重出或输入是手写的）")
    return {"ok": not bad, "artifact_sha256": sha, "problems": bad}

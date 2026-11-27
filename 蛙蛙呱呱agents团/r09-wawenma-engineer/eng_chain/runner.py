# -*- coding: utf-8 -*-
"""工程链编排：adr → api → feature → testing → debug → release → security →
performance → incident → review。

一条命令产出 10 份 JSON + 10 份 Markdown + eng_manifest.json：
  - 每份工件带自己的门禁与 sha256；
  - 跨段一致：API 错误码 = 安全清单，testing 场景 = feature 验收 ID；
  - 任一段 CRITICAL 失败 → manifest FAIL，CLI 退出码 1；
  - 工作区内不写时间戳，manifest 才留痕，保证同 brief 工件可复现。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

from . import (adr, api, debug, feature, incident, performance, release,
               review, security, testing)
from .common import (STAGE_ORDER, ck, gate, load_brief, now_iso, sha256_file,
                     write_json, write_text)

MODULES = {
    "adr": adr, "api": api, "feature": feature, "testing": testing,
    "debug": debug, "release": release, "security": security,
    "performance": performance, "incident": incident, "review": review,
}


def run(brief_path: str, out_dir: str) -> Dict[str, Any]:
    """跑完 10 段；不提前中断，便于一次看全所有阻断项。"""
    os.makedirs(out_dir, exist_ok=True)
    brief = load_brief(brief_path)
    artifacts: Dict[str, Dict[str, Any]] = {}
    paths: Dict[str, Dict[str, str]] = {}

    for stage in STAGE_ORDER:
        mod = MODULES[stage]
        art = mod.build(brief)
        artifacts[stage] = art
        jp = os.path.join(out_dir, f"{stage}.json")
        mp = os.path.join(out_dir, f"{stage}.md")
        write_json(jp, art)
        write_text(mp, mod.render(art))
        paths[stage] = {"json": jp, "md": mp}

    checks: List[Dict[str, Any]] = []
    for stage in STAGE_ORDER:
        g = artifacts[stage].get("gate") or {}
        checks.append(ck(bool(g.get("ok")), f"{stage} 门禁={g.get('grade')}",
                         f"chain:{stage}", "CRITICAL" if not g.get("ok") else "OK"))

    a, s = artifacts["api"], artifacts["security"]
    code_set = {c.get("code") for c in a.get("error_codes") or []}
    checks.append(ck(code_set == set(s.get("api_error_codes") or []) ==
                     set(s.get("handled_error_codes") or []),
                     "API 错误码 = 安全清单", "consistency:api_security_error_codes",
                     "CRITICAL"))
    t, f = artifacts["testing"], artifacts["feature"]
    checks.append(ck(set(t.get("scenario_ids") or []) ==
                     set(f.get("acceptance_ids") or []) and
                     bool(f.get("acceptance_ids")),
                     "testing 场景 = feature 验收", "consistency:testing_acceptance",
                     "CRITICAL"))
    r, py = artifacts["release"], t.get("pyramid") or {}
    total = sum(int(py.get(k, 0) or 0) for k in ("unit", "integration", "contract", "e2e"))
    passed = int((r.get("tests") or {}).get("passed", 0))
    checks.append(ck(passed >= total > 0 and
                     int((r.get("tests") or {}).get("failed", 0)) == 0,
                     f"发布测试数 ≥ 测试金字塔（{passed}/{total}）",
                     "consistency:release_test_count", "CRITICAL"))

    cg = gate(checks, "chain")
    stages = []
    for stage in STAGE_ORDER:
        art = artifacts[stage]
        st = {"stage": stage,
              "file": f"{stage}.json",
              "md": f"{stage}.md",
              "path": paths[stage]["json"],
              "sha256": sha256_file(paths[stage]["json"]),
              "md_sha256": sha256_file(paths[stage]["md"]),
              "gate": (art.get("gate") or {}).get("grade"),
              "ok": bool((art.get("gate") or {}).get("ok"))}
        stages.append(st)

    blockers: List[str] = []
    warnings: List[str] = []
    for stage in STAGE_ORDER:
        g = artifacts[stage].get("gate") or {}
        blockers.extend(f"{stage}/{b}" for b in g.get("blockers") or [])
        warnings.extend(f"{stage}/{w}" for w in g.get("warnings") or [])
    blockers.extend(f"chain/{b}" for b in cg.get("blockers") or [])

    manifest = {
        "artifact": "eng_manifest",
        "version": "1.0",
        "generated_at": now_iso(),
        "project": brief.get("project", ""),
        "brief": os.path.abspath(brief_path),
        "stage_order": list(STAGE_ORDER),
        "stages": stages,
        "cross_checks": cg["checks"],
        "blockers": blockers,
        "warnings": warnings,
        "ok": bool(cg["ok"]),
        "grade": cg["grade"],
        "gate": cg,
    }
    write_json(os.path.join(out_dir, "eng_manifest.json"), manifest)
    return manifest


def audit(dir_path: str) -> Dict[str, Any]:
    """只读复核：文件齐全、哈希一致、门禁 PASS、跨段检查全绿。"""
    mp = os.path.join(dir_path, "eng_manifest.json")
    if not os.path.exists(mp):
        return {"artifact": "eng_audit", "ok": False, "grade": "FAIL",
                "errors": [f"缺少 {mp}"], "stages": []}
    with open(mp, encoding="utf-8-sig") as f:
        manifest = json.load(f)
    checks = []
    for item in manifest.get("stages", []):
        jp = os.path.join(dir_path, item.get("file", ""))
        mdp = os.path.join(dir_path, item.get("md", ""))
        exists = os.path.exists(jp) and os.path.exists(mdp)
        checks.append(ck(exists, f"{item.get('stage')} 工件齐全", "audit:existence",
                         "CRITICAL" if not exists else "OK"))
        if os.path.exists(jp):
            same = sha256_file(jp) == item.get("sha256")
            checks.append(ck(same, f"{item.get('stage')} JSON 哈希一致", "audit:integrity",
                             "CRITICAL" if not same else "OK"))
    got = {x.get("stage") for x in manifest.get("stages", [])}
    checks.append(ck(got == set(STAGE_ORDER), "10 段齐全", "audit:structure",
                     "CRITICAL" if got != set(STAGE_ORDER) else "OK"))
    checks.append(ck(bool(manifest.get("ok")), "manifest 判定 PASS", "audit:gate",
                     "CRITICAL" if not manifest.get("ok") else "OK"))
    checks.append(ck(all(c.get("ok") for c in manifest.get("cross_checks") or []),
                     "跨段一致检查全绿", "audit:consistency", "CRITICAL"))
    g = gate(checks, "audit")
    return {"artifact": "eng_audit", "ok": g["ok"], "grade": g["grade"],
            "stage": "audit", "gate": g, "errors": g["errors"],
            "stages": manifest.get("stages", [])}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="eng_chain.runner",
                                 description="R09 十段工程链")
    ap.add_argument("--brief", required=True, help="工程 brief JSON")
    ap.add_argument("--out-dir", required=True, help="工件输出目录")
    a = ap.parse_args(argv)
    m = run(a.brief, a.out_dir)
    print(json.dumps(m, ensure_ascii=False, indent=2))
    return 0 if m.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())

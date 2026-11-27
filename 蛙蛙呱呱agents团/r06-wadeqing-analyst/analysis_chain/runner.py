# -*- coding: utf-8 -*-
"""分析链编排：frame → plan → profile → explore → explain → test。

一次运行产出 6 个工件 + chain_manifest.json（含每段门禁、sha256、跨段一致性）。
任一段门禁失败，manifest 置 FAIL，CLI 退出码非 0；不静默降级。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from . import explain as explain_mod
from . import explore as explore_mod
from . import frame as frame_mod
from . import plan as plan_mod
from . import profile as profile_mod
from . import stats_test as stats_mod
from .common import STAGE_ORDER, ck, gate, now_iso, read_json, sha256_file, write_json

FILES = {
    "frame": "frame.json",
    "plan": "analysis_plan.json",
    "profile": "data_profile.json",
    "explore": "findings.json",
    "explain": "explanation.json",
    "test": "stats.json",
}


def run(question: str, data_path: str, out_dir: str, start: str, end: str,
        split: str, decision_use: str = "", metric: str = "",
        dimensions: Optional[List[str]] = None, domain: Optional[str] = None,
        date: str = "date", qty: Optional[str] = None,
        cost: Optional[str] = None, stage: Optional[str] = None,
        stage_order: Optional[str] = None, semantic_path: Optional[str] = None,
        pk: Optional[str] = None, seed: int = 0, min_n: int = 30,
        min_impact_pct: float = 3.0) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    artifacts: Dict[str, Dict[str, Any]] = {}
    paths: Dict[str, str] = {}

    def save(stage: str, artifact: Dict[str, Any]) -> None:
        artifacts[stage] = artifact
        p = os.path.join(out_dir, FILES[stage])
        write_json(p, artifact)
        paths[stage] = p

    frame = frame_mod.build(question, decision_use=decision_use, metric=metric,
                            dimensions=dimensions, domain=domain,
                            min_impact_pct=min_impact_pct)
    save("frame", frame)
    if not (frame.get("gate") or {}).get("ok"):
        return _finish(out_dir, artifacts, paths, question, data_path)

    plan = plan_mod.build(frame, start, end, split, window=frame.get("window", ""))
    save("plan", plan)
    if not (plan.get("gate") or {}).get("ok"):
        return _finish(out_dir, artifacts, paths, question, data_path)

    semantic = read_json(semantic_path) if semantic_path and os.path.exists(semantic_path) else None
    prof = profile_mod.profile(data_path, plan, pk=pk, date=date, semantic=semantic)
    save("profile", prof)
    if not (prof.get("gate") or {}).get("ok"):
        return _finish(out_dir, artifacts, paths, question, data_path)

    findings = explore_mod.build(data_path, plan, date=date, stage=stage,
                                 stage_order=stage_order, qty=qty, cost=cost)
    save("explore", findings)
    if not (findings.get("gate") or {}).get("ok"):
        return _finish(out_dir, artifacts, paths, question, data_path)

    explanation = explain_mod.build(data_path, plan, findings, qty=qty, date=date)
    save("explain", explanation)

    stats = stats_mod.build(data_path, plan, findings, date=date, seed=seed, min_n=min_n)
    save("test", stats)

    return _finish(out_dir, artifacts, paths, question, data_path)


def _finish(out_dir: str, artifacts: Dict[str, Dict[str, Any]], paths: Dict[str, str],
            question: str, data_path: str) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    for stage in STAGE_ORDER:
        art = artifacts.get(stage)
        if art is None:
            checks.append(ck(False, f"{stage} 未产出", "chain", "CRITICAL"))
            continue
        g = art.get("gate") or {}
        checks.append(ck(bool(g.get("ok")), f"{stage} 门禁={g.get('grade')}", "chain",
                         "CRITICAL" if not g.get("ok") else "OK"))

    f, p = artifacts.get("frame"), artifacts.get("plan")
    if f and p:
        fids = sorted(h["id"] for h in f.get("hypotheses", []))
        pids = sorted(r.get("hypothesis_id") for r in p.get("rounds", []))
        checks.append(ck(fids == pids, "假设与计划一一对应", "consistency",
                         "CRITICAL" if fids != pids else "OK"))
    fd, ex = artifacts.get("explore"), artifacts.get("explain")
    if fd and ex:
        overall = next((x for x in fd.get("findings", []) if x.get("type") == "overall"), {})
        delta = (ex.get("root") or {}).get("delta")
        tol = max(0.5, abs(overall.get("delta", 0)) * 0.005)
        checks.append(ck(isinstance(delta, (int, float)) and
                         abs(delta - overall.get("delta", 0)) <= tol,
                         "解释层根变化与发现层一致", "consistency",
                         "CRITICAL" if not (isinstance(delta, (int, float)) and
                                            abs(delta - overall.get("delta", 0)) <= tol) else "OK"))
    st = artifacts.get("test")
    if st and p:
        checks.append(ck(st.get("metric") == p.get("metric"), "统计指标与计划一致",
                         "consistency", "CRITICAL" if st.get("metric") != p.get("metric") else "OK"))
    cg = gate(checks, "chain")
    manifest = {
        "artifact": "chain_manifest",
        "version": "1.0",
        "generated_at": now_iso(),
        "question": question,
        "data": os.path.abspath(data_path),
        "stage_order": list(STAGE_ORDER),
        "stages": [
            {"stage": s,
             "file": FILES[s],
             "path": paths.get(s, ""),
             "sha256": sha256_file(paths[s]) if paths.get(s) and os.path.exists(paths[s]) else "",
             "gate": (artifacts.get(s) or {}).get("gate", {}).get("grade"),
             "ok": bool(((artifacts.get(s) or {}).get("gate") or {}).get("ok"))}
            for s in STAGE_ORDER if s in artifacts
        ],
        "cross_checks": cg["checks"],
        "ok": cg["ok"],
        "grade": cg["grade"],
        "gate": cg,
    }
    write_json(os.path.join(out_dir, "chain_manifest.json"), manifest)
    return manifest

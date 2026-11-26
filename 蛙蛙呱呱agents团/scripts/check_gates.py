# -*- coding: utf-8 -*-
"""scripts/check_gates.py —— 出口闸：G1 口径 + G2 台账 + G3 图表。

用法：
    python scripts/check_gates.py --project <项目目录> [--report <contract.json>]
退出码：0 = 通过或已豁免；1 = 有门未过。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _yaml(path: Path) -> dict:
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else None


def _waiver(cfg: dict, project: Path) -> dict:
    today = date.today().isoformat()
    w = (cfg.get("waivers") or {}).get(project.name) or {}
    if not w:
        return {}
    until = w.get("until", "9999-12-31")
    if until < today:
        return {}  # 过期失效
    return w


def gate_caliber(project: Path, cfg: dict) -> dict:
    from core.claims.cells_claims import audit_cards
    r = audit_cards(project)
    cells = sum(v.get("cells", 0) for v in r.get("roles", {}).values())
    problems = sum(v.get("problems", 0) for v in r.get("roles", {}).values())
    density = round(problems / cells, 3) if cells else 0.0
    thr = cfg.get("gates", {}).get("caliber", {}).get("threshold", 0.2)
    return {"cells": cells, "problems": problems, "density": density,
            "threshold": thr, "pass": density <= thr}


def gate_content(report: Path, cfg: dict) -> dict:
    import importlib.util
    gc = cfg.get("gates", {}).get("content", {}).get("golden_corpus", "")
    base = ROOT / gc
    if not base.exists():
        return {"skip": "no golden corpus"}
    corpus = _json(base)
    cur = _json(report)
    if cur is None:
        return {"skip": "no contract"}
    spec = importlib.util.spec_from_file_location(
        "check_content", ROOT / "scripts" / "check_content.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cur_hash = mod.hash_contract(cur)
    match = None
    rp = report.resolve().as_posix()
    for line in ("claims", "data_line", "flow_line"):
        for e in corpus.get("lines", {}).get(line, []):
            if e.get("content_hash") and Path(e.get("path", "")).as_posix() == rp:
                match = e
    if not match:
        return {"skip": f"corpus 无匹配 {rp}"}
    return {"pass": cur_hash == match.get("content_hash"),
            "current": cur_hash[:12], "golden": match.get("content_hash", "")[:12]}


def gate_chart(report: Path, cfg: dict) -> dict:
    from core.report_theme.charts_pro.spec import RENDERERS, ALIASES
    valid = set(RENDERERS) | set(ALIASES)
    cur = _json(report)
    if cur is None:
        return {"skip": "no contract"}
    bad = [{"index": i, "type": t}
           for i, s in enumerate(cur.get("sections") or [], 1)
           if (t := str((s.get("chart") or {}).get("type") or "")) and t not in valid]
    return {"pass": not bad, "bad": bad}


def gate_fitness(report: Path, cfg: dict) -> dict:
    """G4 图拟合度：S4 在 relation 声明的图上挂了 chart_validation，ok=False 即拦。

    存量卡（未声明 relation）没有 chart_validation，跳过（迁移后再严管）。
    """
    cur = _json(report)
    if cur is None:
        return {"skip": "no contract"}
    bad = []
    for i, s in enumerate(cur.get("sections") or [], 1):
        ch = s.get("chart") or {}
        v = ch.get("chart_validation")
        if isinstance(v, dict) and v.get("ok") is False:
            bad.append({"index": i, "type": ch.get("type"),
                        "reason": v.get("reason"),
                        "suggest": v.get("suggest")})
    return {"pass": not bad, "bad": bad, "checked": len(bad)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--report", default=None)
    ap.add_argument("--config", default=str(ROOT / "configs" / "gates.yaml"))
    args = ap.parse_args(argv)

    cfg = _yaml(Path(args.config))
    project = Path(args.project)
    waiver = _waiver(cfg, project)

    results, fails = {}, []
    # G1
    g1 = gate_caliber(project, cfg)
    results["caliber"] = g1
    if "caliber" in waiver:
        g1["waived"] = waiver["caliber"].get("reason")
        g1["pass"] = True
    elif g1.get("pass") is False:
        fails.append("caliber")
    # G2/G3/G4
    report = Path(args.report) if args.report else None
    if report:
        g2 = gate_content(report, cfg)
        results["content"] = g2
        if g2.get("pass") is False:
            fails.append("content")
        g3 = gate_chart(report, cfg)
        results["chart"] = g3
        if g3.get("pass") is False:
            fails.append("chart")
        g4 = gate_fitness(report, cfg)
        results["fitness"] = g4
        if g4.get("pass") is False:
            fails.append("fitness")

    ok = not fails
    out = {"ok": ok, "mode": cfg.get("mode", "warn"),
           "waiver": {"reason": waiver.get("reason"), "until": waiver.get("until")},
           "failed_gates": fails, "results": results}
    # 只保留摘要，不打印大 detail
    for k, v in results.items():
        if isinstance(v, dict) and "detail" in v:
            v["detail"] = "…(省略)"
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

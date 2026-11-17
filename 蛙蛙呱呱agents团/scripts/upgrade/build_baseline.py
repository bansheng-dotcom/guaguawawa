# -*- coding: utf-8 -*-
"""P0 基线：把升级前的报告状态固化成 baseline.json。

用法：
    python scripts/upgrade/build_baseline.py
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WS = ROOT / "workspace" / "report_upgrade"
PIPE = ROOT.parent / "内蒙古水果三城调研_2026-11-16_pipeline"
DELIV = ROOT.parent / "内蒙古水果三城调研_2026-11-16" / "out"


def load(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def manifest_row(name: str, out_dir: Path) -> dict:
    m = load(out_dir / "manifest.json")
    return {
        "name": name,
        "thesis": m.get("thesis"),
        "label": m.get("thesis_label"),
        "ok": m.get("ok"),
        "branch": m.get("branch"),
        "sections": (m.get("section_check") or {}).get("sections"),
        "quality": (m.get("quality") or {}).get("score"),
        "quality_ok": (m.get("quality") or {}).get("ok"),
        "covered": m.get("covered"),
        "r04": (m.get("r04") or {}).get("verdict"),
        "contract_ok": (m.get("contract") or {}).get("ok"),
        "chart_stats": m.get("chart_stats"),
    }


def gate_row(name: str, path: Path) -> dict:
    d = load(path)
    if isinstance(d, list) and d:
        d = d[0]
    return {
        "name": name,
        "ok": d.get("ok"),
        "violations": d.get("violations"),
        "stats": d.get("stats"),
        "depth": d.get("depth"),
    }


def sh(*args: str) -> str:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def main() -> int:
    reports = []
    for name in ("out_research", "out_ops", "out_chain", "out_remediation"):
        reports.append({
            **manifest_row(name, PIPE / name),
            "gate": gate_row(name, WS / f"gate_{name}.json"),
        })

    delivered = {
        **manifest_row("delivered", DELIV),
        "gate": gate_row("delivered", WS / "gate_delivered.json"),
    }

    dirty = [x for x in sh("git", "status", "--porcelain").splitlines() if x.strip()]
    ci_path = WS / "ci_status.json"
    ci = load(ci_path) if ci_path.exists() else {"status": "pending"}
    baseline = {
        "schema": "dsh.report_upgrade.baseline/v1",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "git": {
            "head": sh("git", "rev-parse", "--short", "HEAD"),
            "tag": "report-line-baseline-2026-11-17",
            "dirty_files": len(dirty),
            "note": "tag 打在 HEAD 上；工作区有未提交改动，baseline.json 记录的是当前工作区状态。",
        },
        "roles_check": {"passed": 20, "total": 20,
                        "source": "python guagua.py check（2026-11-17 实测）"},
        "ci_report_checks": ci,
        "reports": reports,
        "delivered": delivered,
        "summary": {
            "reports_total": len(reports),
            "manifest_ok": sum(1 for r in reports if r.get("ok") is True),
            "gate_pass": sum(1 for r in reports if (r.get("gate") or {}).get("ok") is True),
            "gate_fail": sum(1 for r in reports if (r.get("gate") or {}).get("ok") is False),
            "delivered_gate_ok": (delivered.get("gate") or {}).get("ok"),
            "note": "manifest 说 ok 不等于成品门禁 PASS；out_ops / out_remediation 是反例。",
        },
    }
    WS.mkdir(parents=True, exist_ok=True)
    out = WS / "baseline.json"
    out.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps(baseline["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

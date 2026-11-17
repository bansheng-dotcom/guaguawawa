# -*- coding: utf-8 -*-
"""P4 parity：新旧报告的 finding 覆盖对比。

用法：
    python scripts/upgrade/parity_report_build.py \
      --old out_research out_ops out_chain out_remediation \
      --new p4_build_pipeline3 p4_build_ops --json workspace/report_upgrade/parity.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Set


def findings(d: str | Path) -> Set[str]:
    p = Path(d) / "analysis_trace.json"
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    return {str(f.get("key")) for f in (data.get("findings") or [])}


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="parity_report_build")
    ap.add_argument("--old", nargs="+", required=True)
    ap.add_argument("--new", nargs="+", required=True)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)

    old_sets = {str(p): findings(p) for p in a.old}
    new_sets = {str(p): findings(p) for p in a.new}
    old_union = set().union(*old_sets.values()) if old_sets else set()
    new_union = set().union(*new_sets.values()) if new_sets else set()
    rows = []
    for name, s in new_sets.items():
        rows.append({
            "new": name,
            "findings": sorted(s),
            "missing_from_old": sorted(old_union - s),
            "extra_vs_old": sorted(s - old_union),
            "parity": round(len(old_union & s) / len(old_union), 3) if old_union else 0.0,
        })
    out: Dict[str, Any] = {
        "schema": "dsh.report_parity/v1",
        "old": {k: sorted(v) for k, v in old_sets.items()},
        "old_union": sorted(old_union),
        "new": rows,
        "union_parity": round(len(old_union & new_union) / len(old_union), 3) if old_union else 0.0,
        "ok": len(old_union & new_union) == len(old_union),
    }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if a.json:
        Path(a.json).write_text(text, encoding="utf-8")
    print(text[:8000])
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

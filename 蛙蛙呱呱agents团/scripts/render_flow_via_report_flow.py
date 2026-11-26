# -*- coding: utf-8 -*-
"""scripts/render_flow_via_report_flow.py —— 影子渲染：facts.py → IR → contract → report_flow。

用途：S6 渲染器二选一的对照实验。同一份 facts.py：
  - legacy（kit）：`python guagua.py report flow --project <dir> --out <A>`
  - 新路径（report_renderer）：`python scripts/render_flow_via_report_flow.py --project <dir> --out <B>`
比两份 HTML 的节数/图数/页数，确认等价后再切。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import ir_to_contract
from core.report import report_flow  # noqa: E402
from core.ir_adapters import facts_module_to_ir  # noqa: E402
from core.semantic_pipeline import resolve  # noqa: E402


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="含 facts.py 的项目目录")
    ap.add_argument("--out", required=True, help="输出目录")
    a = ap.parse_args()

    proj = Path(a.project)
    fp = proj / "facts.py"
    if not fp.is_file():
        print(json.dumps({"ok": False, "why": "缺 facts.py"}, ensure_ascii=False))
        return 2

    facts = _load(fp, "flow_facts")
    ir, degraded = facts_module_to_ir(facts)
    model = resolve(ir)
    contract = ir_to_contract.build(model)
    files = report_flow.render(contract, a.out, md_name="report", pdf=False)
    print(json.dumps({
        "ok": True,
        "sections": len(contract.get("sections") or []),
        "figures": len([s for s in contract.get("sections") or [] if s.get("chart")]),
        "html": files.get("html"),
        "chart_stats": files.get("chart_stats"),
        "degraded": len(degraded),
        "degraded_sample": degraded[:3],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

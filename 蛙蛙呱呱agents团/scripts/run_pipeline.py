# -*- coding: utf-8 -*-
"""跑一条 analysis pipeline：python scripts/run_pipeline.py pipelines/example_quality.json"""
import json
import sys
from pathlib import Path

AGENTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENTS))
from core.analysis_pipeline import run  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: run_pipeline.py <pipeline.json>")
        raise SystemExit(2)
    out = run(sys.argv[1])
    print(json.dumps(out, ensure_ascii=False, indent=1))
    raise SystemExit(0 if out.get("ok") else 1)

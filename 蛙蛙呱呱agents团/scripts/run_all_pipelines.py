# -*- coding: utf-8 -*-
"""跑 pipelines/*.json 全部，用于 CI。"""
import json, sys
from pathlib import Path

AGENTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENTS))
from core.analysis_pipeline import run  # noqa: E402

bad = []
for p in sorted((AGENTS / "pipelines").glob("*.json")):
    out = run(str(p))
    print(f"[{'OK' if out.get('ok') else 'FAIL'}] {p.name}")
    if not out.get("ok"):
        bad.append(p.name)
print(f"\n{len(list((AGENTS/'pipelines').glob('*.json'))) - len(bad)} 通过，{len(bad)} 失败")
raise SystemExit(1 if bad else 0)

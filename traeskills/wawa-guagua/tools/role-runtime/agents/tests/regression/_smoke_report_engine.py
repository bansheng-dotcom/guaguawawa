# -*- coding: utf-8 -*-
"""报告引擎冒烟：拿真实技能结果跑一遍报告规格推导（不落盘）。"""
from __future__ import annotations

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from agents.shared.report_engine import build_report_spec  # noqa: E402

demo = {
    "ok": True,
    "checks": [
        {"ok": True, "dim": "wbs.items", "sev": "OK", "msg": "5 项任务均有负责人"},
        {"ok": False, "dim": "capacity.overload", "sev": "BLOCKER",
         "msg": "r09 本周负载 4.5 人日 > 3 人日上限"},
    ],
    "item_count": 5,
    "total_cost": 4.0,
    "max_step": 5,
    "next": "容量超载需先委派再排期",
    "verdict": "FAIL",
}

spec = build_report_spec("r02", demo, "schedule", "wbs", "双 11 渠道冲刺排期")
print(json.dumps({k: v for k, v in spec.items() if k != "analysis_sections"},
                 ensure_ascii=False, indent=1)[:4000])
print("--- sections:", len(spec["analysis_sections"]))
print("--- rca levels:", [r["level"] for r in spec["rca"]])

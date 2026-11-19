# -*- coding: utf-8 -*-
"""R20 SLO 错误预算：允许停机/已用/剩余/燃尽率。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import business  # noqa: E402

DEPTH = "L3"

NAME = "slo"
DESC = "SLO 错误预算：允许停机、已用、剩余、燃尽率"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--slo", type=float, required=True, help="如 99.9")
    p.add_argument("--window-days", type=int, default=30)
    p.add_argument("--requests", type=float, default=0)
    p.add_argument("--downtime-min", type=float, required=True)


def run(args) -> Dict[str, Any]:
    out = business.slo_budget(args.slo, args.window_days, args.requests, args.downtime_min)
    # 错误预算透支 / 燃尽率 >1 是阻断项：不能一边报「超预算」一边 ok=true
    remaining = float(out.get("remaining_min") or 0.0)
    burn = float(out.get("burn_rate") or 0.0)
    over_budget = remaining < 0
    checks = [
        {"ok": not over_budget,
         "msg": f"剩余错误预算 {remaining:.1f} 分钟（<0 即透支）",
         "dim": "slo:budget",
         "sev": "CRITICAL" if over_budget else "OK"},
        {"ok": burn <= 1.0,
         "msg": f"燃尽率 {burn:.3f}（≤1 为健康，>1 会在窗口内耗尽预算）",
         "dim": "slo:burn",
         "sev": "HIGH" if burn > 1.0 else "OK"},
    ]
    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "verdict": "PASS" if ok else "FAIL", "checks": checks, "slo": out,
            "next": ("错误预算健康，可继续观察" if ok
                     else "错误预算已透支：停止发版、按事故流程处理并复核 SLO")}

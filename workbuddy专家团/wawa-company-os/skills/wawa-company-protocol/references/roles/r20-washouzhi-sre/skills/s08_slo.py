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
    return {"ok": True, "checks": [], "slo": out}

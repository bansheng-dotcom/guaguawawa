# -*- coding: utf-8 -*-
"""R12 LTV/CAC 技能（增长扩展）：LTV = ARPU × 毛利率 ÷ 流失率。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import core  # noqa: E402

NAME = "ltv-cac"
DESC = "LTV/CAC：回收月数 + 健康判定"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--arpu", type=float, required=True)
    p.add_argument("--gm", type=float, required=True, help="毛利率 0—1")
    p.add_argument("--churn", type=float, required=True, help="月流失率 0—1")
    p.add_argument("--cac", type=float, required=True)


def run(args) -> Dict[str, Any]:
    return {"ok": True, "checks": [],
            "ltv_cac": core.ltv_cac(args.arpu, args.gm, args.churn, args.cac)}

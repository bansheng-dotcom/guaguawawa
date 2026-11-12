# -*- coding: utf-8 -*-
"""R02 利特尔法则技能（运营扩展）。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import core  # noqa: E402

NAME = "little"
DESC = "利特尔法则：WIP = 到达率 × 周期（瓶颈判断）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--arrival", type=float, required=True, help="件/天")
    p.add_argument("--cycle", type=float, required=True, help="周期（天）")
    p.set_defaults(action=NAME)


def run(args) -> Dict[str, Any]:
    out = core.littles_law(args.arrival, args.cycle)
    return {"ok": True, "checks": [], "little": out, "next": ""}

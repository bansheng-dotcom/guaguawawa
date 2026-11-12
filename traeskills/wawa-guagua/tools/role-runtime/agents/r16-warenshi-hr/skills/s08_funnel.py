# -*- coding: utf-8 -*-
"""R16 招聘漏斗：逐级转化率与瓶颈。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import business  # noqa: E402

DEPTH = "L3"

NAME = "funnel"
DESC = "招聘漏斗：投递→筛选→面试→Offer→入职转化与瓶颈"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--applied", type=float, required=True)
    p.add_argument("--screened", type=float, required=True)
    p.add_argument("--interviewed", type=float, required=True)
    p.add_argument("--offers", type=float, required=True)
    p.add_argument("--hires", type=float, required=True)


def run(args) -> Dict[str, Any]:
    out = business.hiring_funnel(args.applied, args.screened, args.interviewed,
                                 args.offers, args.hires)
    return {"ok": True, "checks": [], "funnel": out}

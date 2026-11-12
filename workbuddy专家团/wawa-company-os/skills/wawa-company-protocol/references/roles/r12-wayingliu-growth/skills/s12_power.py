# -*- coding: utf-8 -*-
"""R12 实验功效：两比例样本量 / MDE。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import business  # noqa: E402

DEPTH = "L3"

NAME = "power"
DESC = "实验功效：两比例样本量（baseline/MDE/alpha/power）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--baseline", type=float, required=True)
    p.add_argument("--mde", type=float, required=True)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--power", type=float, default=0.8)


def run(args) -> Dict[str, Any]:
    out = business.experiment_power(args.baseline, args.mde, args.alpha, args.power)
    return {"ok": True, "checks": [], "power": out}

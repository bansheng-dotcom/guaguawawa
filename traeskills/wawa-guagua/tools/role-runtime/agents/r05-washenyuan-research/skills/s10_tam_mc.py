# -*- coding: utf-8 -*-
"""R05 TAM 蒙特卡洛：渗透率 × ARPU 不确定区间。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import business  # noqa: E402

DEPTH = "L3"

NAME = "tam-mc"
DESC = "TAM 蒙特卡洛：渗透率×ARPU，输出 p10/p50/p90"

# manifest 依赖 ACTIONS（与其它技能一致）；单动作技能用动作名作键
ACTIONS = {NAME: DESC}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--population", type=float, required=True)
    p.add_argument("--pen-low", type=float, required=True)
    p.add_argument("--pen-high", type=float, required=True)
    p.add_argument("--arpu-low", type=float, required=True)
    p.add_argument("--arpu-high", type=float, required=True)
    p.add_argument("--n", type=int, default=10000)
    p.set_defaults(action=NAME)


def run(args) -> Dict[str, Any]:
    out = business.tam_mc(args.population, args.pen_low, args.pen_high,
                          args.arpu_low, args.arpu_high, args.n)
    return {"ok": True, "checks": [], "tam": out}

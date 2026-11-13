# -*- coding: utf-8 -*-
"""R15 履约仿真：基础固定提前期 或 (s,S)+随机提前期+周期服务水平。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import advanced, deep  # noqa: E402

NAME = "fulfill-sim"
DESC = "履约仿真：履约率/缺货/库存；可选 (s,S)+随机提前期"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--demand", type=float, required=True)
    p.add_argument("--sd", type=float, required=True)
    p.add_argument("--lead", type=float, required=True)
    p.add_argument("--capacity", type=float, required=True)
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--sims", type=int, default=1000)
    p.add_argument("--lead-sd", type=float, default=0.0, help="提前期标准差；>0 走深度")
    p.add_argument("--s", type=float, default=None, help="补货点")
    p.add_argument("--S", type=float, default=None, help="补货上限")
    p.add_argument("--warmup", type=float, default=0.1, help="预热比例")


def run(args) -> Dict[str, Any]:
    if args.s is not None and args.S is not None:
        out = deep.fulfillment_deep(args.demand, args.sd, args.lead, args.lead_sd,
                                    args.s, args.S, args.days, args.sims, warmup=args.warmup)
        out["method"] = "sS_random_lead"
    else:
        out = advanced.fulfillment_sim(args.demand, args.sd, args.lead, args.capacity,
                                       args.days, args.sims)
        out["method"] = "fixed_lead"
    return {"ok": True, "checks": [], "fulfillment": out}

# -*- coding: utf-8 -*-
"""R15 安全库存技能（供应链扩展）：SS = z × σ_d × √LT。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import core  # noqa: E402

NAME = "safety-stock"
DESC = "安全库存：z × σ_d × √LT（库存优化）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--sigma", type=float, required=True, help="日需求标准差")
    p.add_argument("--lead", type=float, required=True, help="提前期（天）")
    p.add_argument("--z", type=float, default=1.65, help="服务水平系数，默认 95%")


def run(args) -> Dict[str, Any]:
    return {"ok": True, "checks": [],
            "safety_stock": core.safety_stock(args.sigma, args.lead, args.z)}

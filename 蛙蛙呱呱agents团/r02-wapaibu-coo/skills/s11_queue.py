# -*- coding: utf-8 -*-
"""R02 排队与产能：Kingman 等待时间。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import business  # noqa: E402

DEPTH = "L3"

NAME = "queue"
DESC = "排队等待：Kingman 近似（利用率/等待/在制品）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--arrivals", type=float, required=True, help="日均到达")
    p.add_argument("--service", type=float, required=True, help="日均服务能力")
    p.add_argument("--cv-arrival", type=float, default=1.0)
    p.add_argument("--cv-service", type=float, default=1.0)
    p.set_defaults(action=NAME)


def run(args) -> Dict[str, Any]:
    out = business.queue_wait(args.arrivals, args.service, args.cv_arrival, args.cv_service)
    return {"ok": True, "checks": [], "queue": out, "next": ""}

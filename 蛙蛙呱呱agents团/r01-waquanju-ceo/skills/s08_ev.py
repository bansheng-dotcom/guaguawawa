# -*- coding: utf-8 -*-
"""R01 决策期望值：EV + 盈亏平衡概率 + 敏感性。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from . import _common as c

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import business  # noqa: E402

DEPTH = "L3"

NAME = "ev"
DESC = "决策期望值：EV 排序 + 盈亏平衡 p + 敏感性"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True, help="JSON，含 options[]")


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    options = data.get("options", data if isinstance(data, list) else [])
    if not options:
        return {"ok": False, "checks": [], "error": "缺 options"}
    return {"ok": True, "checks": [], "ev": business.expected_value(options)}

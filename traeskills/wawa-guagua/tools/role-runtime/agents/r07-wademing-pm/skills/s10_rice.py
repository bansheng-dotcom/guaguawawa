# -*- coding: utf-8 -*-
"""R07 RICE 排序：R×I×C/E + confidence 敏感性。"""
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

NAME = "rice"
DESC = "RICE 排序：Reach×Impact×Confidence/Effort + 敏感性"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True, help="JSON，含 items[]")


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    items = data.get("items", data if isinstance(data, list) else [])
    if not items:
        return {"ok": False, "checks": [], "error": "缺 items"}
    return {"ok": True, "checks": [], "rice": business.rice(items)}

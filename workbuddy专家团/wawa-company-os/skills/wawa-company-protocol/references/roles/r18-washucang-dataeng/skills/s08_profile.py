# -*- coding: utf-8 -*-
"""R18 数据画像：缺失/基数/重复/PSI。"""
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

NAME = "profile"
DESC = "数据画像：缺失率/基数/重复 + 时间切分 PSI"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--columns", required=True, help="逗号分隔列")
    p.add_argument("--time", default=None, help="时间列；用于 PSI")


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"ok": False, "checks": [], "error": "空数据"}
    cols = [x.strip() for x in args.columns.split(",") if x.strip()]
    return {"ok": True, "checks": [],
            "profile": business.data_profile(rows, cols, args.time)}

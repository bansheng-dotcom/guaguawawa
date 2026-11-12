# -*- coding: utf-8 -*-
"""R19 评测置信区间：Wilson 95%。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import business  # noqa: E402

DEPTH = "L3"

NAME = "eval-ci"
DESC = "评测成功率 Wilson 置信区间（小样本稳）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--successes", type=float, required=True)
    p.add_argument("--n", type=float, required=True)


def run(args) -> Dict[str, Any]:
    out = business.eval_ci(args.successes, args.n)
    return {"ok": True, "checks": [], "eval_ci": out}

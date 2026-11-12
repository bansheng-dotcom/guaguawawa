# -*- coding: utf-8 -*-
"""R17 重试可靠性：最终成功率 / 期望尝试次数。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import business  # noqa: E402

DEPTH = "L3"

NAME = "retry-model"
DESC = "重试可靠性模型（retry-model）：最终成功率/期望尝试/失败概率"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--success-prob", type=float, required=True)
    p.add_argument("--max-attempts", type=int, required=True)


def run(args) -> Dict[str, Any]:
    out = business.retry_reliability(args.success_prob, args.max_attempts)
    return {"ok": True, "checks": [], "retry_model": out}

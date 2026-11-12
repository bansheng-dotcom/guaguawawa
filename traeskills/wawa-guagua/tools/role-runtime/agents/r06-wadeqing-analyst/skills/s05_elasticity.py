# -*- coding: utf-8 -*-
"""S05i 价格弹性 —— 能力域 5（统计域 · 拆细）。

方法：log-log OLS，ln(q) = a + b·ln(p)，b 即价格弹性；返回 R²。
纯标准库；底层在 shared/methods/core.py。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from . import _common as c

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import core  # noqa: E402

NAME = "elasticity"
DESC = "价格弹性：log-log OLS + R²（能力域5拆细·新增）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--price", required=True, help="价格列")
    p.add_argument("--qty", required=True, help="销量列")


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    price = c.numeric(rows, args.price)
    qty = c.numeric(rows, args.qty)
    n = min(len(price), len(qty))
    return {"elasticity": core.elasticity(price[:n], qty[:n]),
            "price": args.price, "qty": args.qty}

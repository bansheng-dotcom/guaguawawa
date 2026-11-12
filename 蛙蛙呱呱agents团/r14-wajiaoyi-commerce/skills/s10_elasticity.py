# -*- coding: utf-8 -*-
"""R14 价格弹性：OLS / 面板 FE / 2SLS。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from . import _common as c

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import core, deep  # noqa: E402

NAME = "elasticity"
DESC = "价格弹性：log-log OLS / 面板 FE / 2SLS（带 CI 与诊断）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--price", required=True)
    p.add_argument("--qty", required=True)
    p.add_argument("--unit", default=None)
    p.add_argument("--time", default=None)
    p.add_argument("--instrument", default=None)
    p.add_argument("--controls", default=None, help="逗号分隔控制变量")


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    price = c.numeric(rows, args.price)
    qty = c.numeric(rows, args.qty)
    n = min(len(price), len(qty))
    names = [x.strip() for x in (args.controls or "").split(",") if x.strip()]
    ctrl = [[float(r[nm]) for nm in names] for r in rows[:n]] if names else None
    if args.instrument:
        inst = c.numeric(rows, args.instrument)
        n = min(n, len(inst))
        out = deep.elasticity_iv(price[:n], qty[:n], inst[:n], ctrl[:n] if ctrl else None)
        out["method"] = "2sls"
    elif args.unit and args.time:
        u = [r[args.unit] for r in rows[:n]]
        t = [r[args.time] for r in rows[:n]]
        out = deep.elasticity_fe(price[:n], qty[:n], u, t, ctrl)
        out["method"] = "panel_fe"
    else:
        out = core.elasticity(price[:n], qty[:n])
        out["method"] = "ols"
    return {"ok": True, "checks": [], "elasticity": out,
            "price": args.price, "qty": args.qty}

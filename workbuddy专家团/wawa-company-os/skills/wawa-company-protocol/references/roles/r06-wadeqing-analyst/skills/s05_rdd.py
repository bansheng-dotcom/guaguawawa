# -*- coding: utf-8 -*-
"""R06 断点回归：基础 / 敏感性（带宽+安慰剂+密度+二次校正+协变量平衡）。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from . import _common as c

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import advanced, deep  # noqa: E402

NAME = "rdd"
DESC = "断点回归：局部线性 / 敏感性（带宽+安慰剂+密度+二次校正+协变量）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--y", required=True)
    p.add_argument("--running", required=True)
    p.add_argument("--cutoff", type=float, required=True)
    p.add_argument("--bandwidth", type=float, default=None)
    p.add_argument("--sensitivity", action="store_true")
    p.add_argument("--covariates", default=None, help="逗号分隔协变量，用于断点平衡")


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    y = c.numeric(rows, args.y)
    x = c.numeric(rows, args.running)
    n = min(len(y), len(x))
    if args.sensitivity:
        names = [v.strip() for v in (args.covariates or "").split(",") if v.strip()]
        cov = [[float(r[nm]) for nm in names] for r in rows[:n]] if names else None
        out = deep.rdd_sensitivity(y[:n], x[:n], args.cutoff,
                                   [args.bandwidth] if args.bandwidth else None, cov)
        out["method"] = "sensitivity"
    else:
        out = advanced.rdd(y[:n], x[:n], args.cutoff, args.bandwidth)
        out["method"] = "local_linear"
    return {"ok": True, "checks": [], "rdd": out,
            "y": args.y, "running": args.running}

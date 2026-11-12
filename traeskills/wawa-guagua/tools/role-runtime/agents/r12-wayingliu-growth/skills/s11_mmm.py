# -*- coding: utf-8 -*-
"""R12 营销组合模型：OLS / 深度（adstock+饱和+ridge+留出）/ 预算 / 贡献 CI。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from . import _common as c

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import advanced, deep  # noqa: E402

NAME = "mmm"
DESC = "MMM：OLS / 深度（adstock+饱和+ridge+留出）/ 预算分配 / 贡献 CI"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--y", required=True)
    p.add_argument("--channels", required=True)
    p.add_argument("--deep", action="store_true")
    p.add_argument("--budget", type=float, default=0.0, help="总预算；>0 时给分配")
    p.add_argument("--bootstrap", type=int, default=0, help="贡献 CI 的自助次数")


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    names = [x.strip() for x in args.channels.split(",") if x.strip()]
    y = c.numeric(rows, args.y)
    X = [[float(r[nm]) for nm in names] for r in rows]
    n = min(len(y), len(X))
    ch = [[X[i][j] for i in range(n)] for j in range(len(names))]
    if args.deep:
        out = deep.mmm_deep(ch, y[:n], names)
        out["method"] = "adstock_saturation"
        res = {"ok": True, "checks": [], "mmm": out,
               "y": args.y, "channels": names}
        if args.budget > 0:
            res["budget"] = deep.mmm_budget(ch, y[:n], names, args.budget)
        if args.bootstrap > 0:
            res["contribution_ci"] = deep.mmm_contribution_ci(ch, y[:n], names, args.bootstrap)
        return res
    out = advanced.mmm(X[:n], y[:n], names)
    out["method"] = "ols"
    return {"ok": True, "checks": [], "mmm": out,
            "y": args.y, "channels": names}

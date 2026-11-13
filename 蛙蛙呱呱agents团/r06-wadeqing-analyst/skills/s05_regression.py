# -*- coding: utf-8 -*-
"""S05f 回归 —— 一元 OLS（兼容旧路径）+ 多元 OLS / Logit（v2）。

旧路径：`--x a --y b`（单列、无 cluster、model=ols）逐字节兼容。
新路径：`--x a,b,c --cluster city --model ols|logit`，支持类别哑变量与稳健/聚类 SE。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c
from . import _stats

NAME = "regression"
DESC = "回归：一元 OLS（兼容）+ 多元 OLS / Logit + 聚类稳健 SE"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--x", required=True,
                   help="自变量；逗号分隔多列（多列或给 --cluster/--model 时走多元路径）")
    p.add_argument("--y", required=True, help="因变量")
    p.add_argument("--cluster", default=None, help="聚类列（按簇稳健 SE）")
    p.add_argument("--model", choices=["ols", "logit"], default="ols",
                   help="ols=线性；logit=二分类（y 必须 0/1）")
    p.add_argument("--categorical", default=None, help="逗号分隔的类别自变量（自动哑变量）")


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    xs = [x.strip() for x in str(args.x).split(",") if x.strip()]
    cats = [x.strip() for x in str(args.categorical or "").split(",") if x.strip()]

    # 旧路径：单列 + 无 cluster + 无类别 + ols
    if len(xs) == 1 and not args.cluster and not cats and args.model == "ols":
        xv = c.numeric(rows, xs[0])
        yv = c.numeric(rows, args.y)
        n = min(len(xv), len(yv))
        return {"regression": _stats.linear_regression(xv[:n], yv[:n]),
                "x": args.x, "y": args.y}

    from shared.methods import linear  # 延迟导入：旧路径不依赖 numpy

    dm = linear.design_matrix(rows, xs, cats)
    kept = dm["rows"]
    yv = [float(r[args.y]) for r in kept if c.isnum(r.get(args.y))]
    if len(yv) != len(kept):
        # y 有非数值：按行过滤
        filtered = [(r, float(r[args.y])) for r in kept if c.isnum(r.get(args.y))]
        kept = [r for r, _ in filtered]
        yv = [v for _, v in filtered]
        dm = linear.design_matrix(kept, xs, cats)
    cluster = [r.get(args.cluster) for r in kept] if args.cluster else None

    if args.model == "logit":
        y_int = [int(float(v)) for v in yv]
        res = linear.fit_logit(y_int, dm["X"], dm["names"], cluster=cluster)
    else:
        res = linear.fit_ols(yv, dm["X"], dm["names"], cluster=cluster, se="HC1")
    res["x"] = xs
    res["y"] = args.y
    res["categorical"] = cats
    res["rows_used"] = len(kept)
    return {"multivariate": res}

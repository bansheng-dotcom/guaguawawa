# -*- coding: utf-8 -*-
"""R06 匹配：原味差分 / PSM / PSM+反驳。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from . import _common as c

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import core, deep  # noqa: E402

NAME = "matched"
DESC = "匹配差分：原味 / PSM（协变量+平衡+卡尺）/ PSM+反驳"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--treat", required=True)
    p.add_argument("--control", required=True)
    p.add_argument("--col", required=True, help="结果列")
    p.add_argument("--covariates", default=None, help="逗号分隔协变量；给了才走 PSM")
    p.add_argument("--cluster", default=None, help="聚类列（按簇自助）")
    p.add_argument("--refute", action="store_true", help="安慰剂+子集反驳")


def run(args) -> Dict[str, Any]:
    t_rows, c_rows = c.load_csv(args.treat), c.load_csv(args.control)
    if not t_rows or not c_rows:
        return {"error": "空数据或无法读取"}
    ty, cy = c.numeric(t_rows, args.col), c.numeric(c_rows, args.col)
    if args.covariates:
        names = [x.strip() for x in args.covariates.split(",") if x.strip()]
        tx = [[float(r[n]) for n in names] for r in t_rows]
        cx = [[float(r[n]) for n in names] for r in c_rows]
        cl = [r[args.cluster] for r in t_rows] if args.cluster else None
        out = deep.psm_att(ty, cy, tx, cx, cluster=cl)
        out["method"] = "psm"
        res = {"ok": True, "checks": [], "matched": out,
               "treat": args.treat, "control": args.control, "col": args.col}
        if args.refute:
            res["refute"] = deep.psm_refute(ty, cy, tx, cx)
        return res
    out = core.matched_diff(ty, cy)
    out["method"] = "raw_diff"
    return {"ok": True, "checks": [], "matched": out,
            "treat": args.treat, "control": args.control, "col": args.col}

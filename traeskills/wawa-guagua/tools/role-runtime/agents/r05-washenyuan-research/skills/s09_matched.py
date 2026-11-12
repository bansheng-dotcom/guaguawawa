# -*- coding: utf-8 -*-
"""R05 匹配差分技能（研究扩展）：处理组−对照组 + CI + 置换 p。"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import core  # noqa: E402

NAME = "matched"
DESC = "匹配差分：两组均值差 + 自助法 CI + 置换 p"

# manifest 依赖 ACTIONS（与其它技能一致）；单动作技能用动作名作键
ACTIONS = {NAME: DESC}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--treat", required=True)
    p.add_argument("--control", required=True)
    p.add_argument("--col", required=True)
    p.set_defaults(action=NAME)


def _col(path: str, name: str) -> List[float]:
    with open(path, encoding="utf-8-sig") as fh:
        return [float(r[name]) for r in csv.DictReader(fh) if r.get(name) not in (None, "")]


def run(args) -> Dict[str, Any]:
    out = core.matched_diff(_col(args.treat, args.col), _col(args.control, args.col))
    return {"ok": True, "checks": [], "matched": out,
            "treat": args.treat, "control": args.control, "col": args.col}

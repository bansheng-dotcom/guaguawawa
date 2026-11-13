# -*- coding: utf-8 -*-
"""R06 DID：2×2 / TWFE / 事件研究 / 置换安慰剂 / 交错处理。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from . import _common as c

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.methods import core, deep  # noqa: E402

NAME = "did"
DESC = "DID：2×2 / TWFE / 事件研究 / 安慰剂 / 交错处理"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--y", required=True)
    p.add_argument("--treat", required=True)
    p.add_argument("--post", required=True)
    p.add_argument("--unit", default=None)
    p.add_argument("--time", default=None)
    p.add_argument("--event-study", action="store_true")
    p.add_argument("--placebo", action="store_true")
    p.add_argument("--staggered", action="store_true")


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    y = c.numeric(rows, args.y)
    treat = [int(float(r[args.treat])) for r in rows]
    post = [int(float(r[args.post])) for r in rows]
    n = min(len(y), len(treat), len(post))
    res: Dict[str, Any] = {"ok": True, "checks": [], "y": args.y}
    if args.unit and args.time:
        u = [r[args.unit] for r in rows[:n]]
        t = [r[args.time] for r in rows[:n]]
        base = deep.twfe_did(y[:n], treat[:n], post[:n], u, t)
        base["method"] = "twfe"
        res["did"] = base
        if args.event_study:
            import os as _os
            if _os.environ.get("GUAGUA_EVENT_STUDY", "v2").strip().lower() == "legacy":
                res["event_study"] = deep.event_study(y[:n], treat[:n], post[:n], u, t)
                res["event_study_engine"] = "legacy"
            else:
                try:
                    res["event_study"] = deep.event_study_v2(y[:n], treat[:n], post[:n], u, t)
                    res["event_study_engine"] = "v2"
                except Exception:  # noqa: BLE001  失败回退旧实现
                    res["event_study"] = deep.event_study(y[:n], treat[:n], post[:n], u, t)
                    res["event_study_engine"] = "legacy_fallback"
        if args.placebo:
            res["placebo"] = deep.did_placebo(y[:n], treat[:n], post[:n], u, t)
        if args.staggered:
            res["staggered"] = deep.staggered_att(y[:n], treat[:n], post[:n], u, t)
    else:
        base = core.did(y[:n], treat[:n], post[:n])
        base["method"] = "2x2"
        res["did"] = base
    return res

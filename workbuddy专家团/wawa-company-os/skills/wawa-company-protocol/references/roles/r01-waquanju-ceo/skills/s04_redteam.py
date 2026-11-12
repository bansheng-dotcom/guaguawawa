# -*- coding: utf-8 -*-
"""S04 反方质询 (Red Team & Cross Evaluation)。"""
from __future__ import annotations

import json
from typing import Any, Dict

from ._common import make_result

NAME = "redteam"
DESC = "反方质询：devil/crosseval/grove"


def _validate_devil(input_data: Dict[str, Any]) -> Dict[str, Any]:
    res = make_result(True, "redteam", "devil", [])
    ok = True
    for c in input_data.get("concerns", []):
        if c.get("level") == "CRITICAL" and not c.get("mitigation"):
            ok = False
    res["ok"] = ok
    return res


def _validate_crosseval(input_data: Dict[str, Any]) -> Dict[str, Any]:
    res = make_result(True, "redteam", "crosseval", [])
    evals = input_data.get("evaluations", [])
    decisions = [e.get("verdict") for e in evals]
    if decisions.count("REJECT") >= 2:
        res["verdict"] = "STOP"
    elif "DEFER" in decisions:
        res["verdict"] = "PAUSE"
    elif decisions.count("APPROVE") >= 2:
        res["verdict"] = "GO"
    else:
        res["verdict"] = "PAUSE"
    return res


def _validate_grove(input_data: Dict[str, Any]) -> Dict[str, Any]:
    res = make_result(True, "redteam", "grove", [])
    # 兼容 outside_perspective 或 successor_would 外视角字段
    has_ext = bool(input_data.get("outside_perspective") or input_data.get("successor_would"))
    if not has_ext:
        res["ok"] = False
    return res


devil = _validate_devil
crosseval = _validate_crosseval
grove = _validate_grove


def add_parser(subparsers) -> None:
    p = subparsers.add_parser(NAME, help=DESC)
    sp = p.add_subparsers(dest="action", required=True)

    p_devil = sp.add_parser("devil")
    p_devil.add_argument("--input", required=True)

    p_crosseval = sp.add_parser("crosseval")
    p_crosseval.add_argument("--input", required=True)

    p_grove = sp.add_parser("grove")
    p_grove.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    """统一技能入口：按 action 读取输入并执行对应反方质询校验。"""
    with open(args.input, "r", encoding="utf-8-sig") as f:
        input_data = json.load(f)
    fn = {
        "devil": _validate_devil,
        "crosseval": _validate_crosseval,
        "grove": _validate_grove,
    }.get(args.action)
    if fn is None:
        return make_result(
            False, "redteam", str(args.action), [{"ok": False, "msg": "未知 action"}]
        )
    return fn(input_data)

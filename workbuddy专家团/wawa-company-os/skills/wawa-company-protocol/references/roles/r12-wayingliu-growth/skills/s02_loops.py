# -*- coding: utf-8 -*-
"""S02 增长循环与自然获客 —— 能力域 2。

整合自 coreyhaines31__marketingskills（marketing-loops / content-strategy）。
把「增长循环」从口头描述转成确定性校验：飞轮五环闭环、内容获客渠道白名单、
循环九要素（触发/动作条件/目的/自检/停止条件/输出）齐备。

动作：
  flywheel   增长飞轮（五环闭环 + 循环要素）
  content    内容获客方案（渠道白名单 + 与飞轮衔接）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "loops"
DESC = "增长循环与自然获客：flywheel/content"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    b = act.add_parser("flywheel", help="校验增长飞轮")
    b.add_argument("--input", required=True)
    u = act.add_parser("content", help="校验内容获客方案")
    u.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "flywheel":
        return _validate_flywheel(data)
    if args.action == "content":
        return _validate_content(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_flywheel(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    rings = data.get("rings")
    want = th["loops"]["flywheel_rings"]
    ok_rings = isinstance(rings, list) and len(rings) == len(want)
    checks.append(_ck(ok_rings,
                      f"飞轮五环闭环（实际 {len(rings) if isinstance(rings, list) else 0}）",
                      "loops.rings"))
    if ok_rings:
        missing = [r for r in want if r not in rings]
        checks.append(_ck(not missing, f"飞轮无缺环（缺 {missing or '无'}）",
                          "loops.ring_complete"))
    else:
        checks.append(_ck(False, "飞轮缺环", "loops.ring_complete"))

    loop = data.get("loop")
    ok_loop = isinstance(loop, dict)
    checks.append(_ck(ok_loop, "循环定义存在", "loops.loop"))
    if ok_loop:
        parts = th["loops"]["loop_parts"]
        missing_parts = [p for p in parts if not str(loop.get(p, "")).strip()]
        checks.append(_ck(not missing_parts,
                          f"循环要素齐备（缺 {missing_parts or '无'}）", "loops.parts"))
    else:
        checks.append(_ck(False, "循环定义缺失", "loops.parts"))

    ok = ok_rings and ok_loop and (not ok_loop or not any(
        not str(data.get("loop", {}).get(p, "")).strip() for p in th["loops"]["loop_parts"])) \
        and (not ok_rings or not any(r not in rings for r in want))
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    ring_count=len(rings) if isinstance(rings, list) else 0)


# --------------------------------------------------------------------------- #
def _validate_content(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    channels = data.get("channels")
    known = th["loops"]["content_channels"]
    ok_ch = isinstance(channels, list) and len(channels) > 0
    checks.append(_ck(ok_ch,
                      f"内容获客渠道 ≥1（实际 {len(channels) if isinstance(channels, list) else 0}）",
                      "content.channels"))
    if ok_ch:
        bad = [ch for ch in channels if ch not in known]
        checks.append(_ck(not bad, f"渠道在白名单（越界 {bad or '无'}）",
                          "content.channel_enum"))
    else:
        checks.append(_ck(False, "渠道缺失", "content.channel_enum"))

    link = data.get("flywheel_link")
    ok_link = bool(str(link or "").strip())
    checks.append(_ck(ok_link, "内容获客与飞轮衔接声明", "content.link"))

    ok = ok_ch and ok_link and (not ok_ch or not any(
        ch not in known for ch in channels))
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    channel_count=len(channels) if isinstance(channels, list) else 0)

# -*- coding: utf-8 -*-
"""S06 付费投放与 CRO —— 能力域 6。

整合自 coreyhaines31__marketingskills（ads / cro / ab-testing）。
把「付费投放与 CRO」从口头建议转成确定性校验：媒介/受众/创意/预算四要素、
ROI=回报/花费 算术实算、转化实验 hypothesis/metric/significance 三件套 + 显著性门槛。

动作：
  media   付费投放（四要素 + ROI 实算）
  cro     转化实验（三件套 + 显著性门槛）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "paid"
DESC = "付费投放与 CRO：media/cro"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    b = act.add_parser("media", help="校验付费投放计划")
    b.add_argument("--input", required=True)
    u = act.add_parser("cro", help="校验转化实验")
    u.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "media":
        return _validate_media(data)
    if args.action == "cro":
        return _validate_cro(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_media(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    missing = [k for k in th["paid"]["media_required"]
               if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"投放四要素齐备（缺 {missing or '无'}）",
                      "paid.media_fields"))

    channel = data.get("channel")
    ok_ch = channel in th["paid"]["channels"]
    checks.append(_ck(ok_ch, f"channel={channel!r} 在白名单", "paid.channel"))
    if not ok_ch:
        return c.result(checks, ok=False, verdict="FAIL", channel=channel, roi=None)

    def num(k):
        v = data.get(k)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    ret, spend = num("return"), num("spend")
    ok_nums = ret is not None and spend is not None
    checks.append(_ck(ok_nums, "回报/花费数字字段齐备", "paid.nums"))
    roi = None
    if ok_nums:
        ok_spend = spend > 0
        checks.append(_ck(ok_spend, f"花费={spend} 为正", "paid.spend"))
        roi = c.safe_div(ret - spend, spend) if spend else None
        checks.append(_ck(roi is not None and roi >= 0,
                          f"ROI={roi} 非负", "paid.roi"))

    ok = (not missing and ok_ch and ok_nums and
          (not ok_nums or (spend > 0 and roi is not None and roi >= 0)))
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    channel=channel, roi=roi)


# --------------------------------------------------------------------------- #
def _validate_cro(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    missing = [k for k in th["paid"]["cro_required"]
               if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"CRO 实验三件套齐备（缺 {missing or '无'}）",
                      "paid.cro_fields"))

    sig = data.get("significance")
    ok_sig = isinstance(sig, (int, float)) and not isinstance(sig, bool) \
        and sig <= th["paid"]["significance_min"]
    checks.append(_ck(ok_sig,
                      f"显著性要求 significance={sig} ≤ {th['paid']['significance_min']}",
                      "paid.significance"))

    ok = not missing and ok_sig
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    significance=sig)

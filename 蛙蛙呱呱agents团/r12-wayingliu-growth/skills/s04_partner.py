# -*- coding: utf-8 -*-
"""S04 红人与合作增长 —— 能力域 4。

整合自 coreyhaines31__marketingskills（influencer-marketing / co-marketing）。
把「红人合作」从口头建议转成确定性校验：达人分级白名单、披露合规（#ad 必含）、
反刷量检查（粉丝突变/泛评论/机器人/买粉/刷量）、联合营销五要素。

动作：
  influencer   红人合作（达人分级 + 披露合规 + 反刷量）
  comarketing  联合营销（五要素齐备）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "partner"
DESC = "红人与合作增长：influencer/comarketing"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    b = act.add_parser("influencer", help="校验红人合作")
    b.add_argument("--input", required=True)
    u = act.add_parser("comarketing", help="校验联合营销")
    u.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "influencer":
        return _validate_influencer(data)
    if args.action == "comarketing":
        return _validate_comarketing(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_influencer(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    tier = data.get("tier")
    ok_tier = tier in th["partner"]["tiers"]
    checks.append(_ck(ok_tier, f"达人分级 tier={tier!r} 在白名单", "partner.tier"))
    if not ok_tier:
        return c.result(checks, ok=False, verdict="FAIL", tier=tier, partner_count=0)

    disclosure = str(data.get("disclosure", ""))
    ok_disc = c.has_any(disclosure, th["partner"]["disclosure_tokens"])
    checks.append(_ck(ok_disc, "披露合规（#ad/sponsored 必含）", "partner.disclosure"))

    signals = data.get("fraud_signals")
    fraud = th["partner"]["fraud_signals"]
    if isinstance(signals, list):
        bad = [s for s in signals if s in fraud]
        checks.append(_ck(not bad, f"反刷量检查通过（命中 {bad or '无'}）",
                          "partner.fraud"))
    else:
        checks.append(_ck(True, "无刷量信号标注", "partner.fraud"))

    ok = ok_tier and ok_disc
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    tier=tier, partner_count=1)


# --------------------------------------------------------------------------- #
def _validate_comarketing(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    missing = [k for k in th["partner"]["comarketing_required"]
               if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"联合营销五要素齐备（缺 {missing or '无'}）",
                      "partner.comarketing"))

    ok = not missing
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    element_count=len(th["partner"]["comarketing_required"]) - len(missing))

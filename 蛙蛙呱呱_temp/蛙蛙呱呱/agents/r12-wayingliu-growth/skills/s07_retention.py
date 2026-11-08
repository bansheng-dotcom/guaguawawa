# -*- coding: utf-8 -*-
"""S07 激活、留存与推荐 —— 能力域 7。

整合自 coreyhaines31__marketingskills（onboarding / churn-prevention / referrals）。
把「激活留存推荐」从口头建议转成确定性校验：激活定义（aha 时刻）、流失预警阈值、
召回渠道白名单、K 因子=i×转化率 实算、双边激励类型枚举。

动作：
  activation  激活（aha 时刻 + 流失预警 + 召回渠道）
  referral    推荐机制（K 因子实算 + 双边激励）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "retention"
DESC = "激活留存推荐：activation/referral"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    b = act.add_parser("activation", help="校验激活流程")
    b.add_argument("--input", required=True)
    u = act.add_parser("referral", help="校验推荐机制")
    u.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "activation":
        return _validate_activation(data)
    if args.action == "referral":
        return _validate_referral(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_activation(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    missing = [k for k in th["retention"]["activation_required"]
               if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"激活定义三件套齐备（缺 {missing or '无'}）",
                      "retention.activation"))

    warn_days = data.get("churn_warning_days")
    ok_warn = isinstance(warn_days, (int, float)) and not isinstance(warn_days, bool) \
        and warn_days <= th["retention"]["churn_warning_days"]
    checks.append(_ck(ok_warn,
                      f"流失预警天数 {warn_days} ≤ {th['retention']['churn_warning_days']}",
                      "retention.churn"))

    recall = data.get("recall_channels")
    known = th["retention"]["recall_channels"]
    ok_recall = isinstance(recall, list) and len(recall) > 0
    checks.append(_ck(ok_recall,
                      f"召回渠道 ≥1（实际 {len(recall) if isinstance(recall, list) else 0}）",
                      "retention.recall"))
    if ok_recall:
        bad = [r for r in recall if r not in known]
        checks.append(_ck(not bad, f"召回渠道在白名单（越界 {bad or '无'}）",
                          "retention.recall_enum"))

    bad = [r for r in (recall or []) if r not in known]
    ok = not missing and ok_warn and ok_recall and not bad
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    recall_count=len(recall) if isinstance(recall, list) else 0)


# --------------------------------------------------------------------------- #
def _validate_referral(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    def num(k):
        v = data.get(k)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    invites, conv = num("invites_per_customer"), num("conversion_rate")
    ok_nums = invites is not None and conv is not None
    checks.append(_ck(ok_nums, "K 因子数字字段齐备", "referral.nums"))
    kfactor = None
    if ok_nums:
        kfactor = round(invites * conv, 4)
        checks.append(_ck(kfactor >= th["retention"]["kfactor_min"],
                          f"K 因子={kfactor} ≥ {th['retention']['kfactor_min']}（病毒循环成立）",
                          "referral.kfactor"))

    incentive = data.get("incentive_type")
    ok_inc = incentive in th["retention"]["incentive_types"]
    checks.append(_ck(ok_inc, f"激励类型 incentive_type={incentive!r} 在白名单",
                      "referral.incentive"))

    ok = ok_nums and (not ok_nums or kfactor >= th["retention"]["kfactor_min"]) and ok_inc
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    kfactor=kfactor, incentive_type=incentive)

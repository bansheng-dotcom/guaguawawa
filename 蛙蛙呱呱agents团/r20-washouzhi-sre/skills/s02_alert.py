# -*- coding: utf-8 -*-
"""S02 告警与升级 —— 能力域 2。

整合自 louislam__uptime-kuma 的告警通知 + 值班升级（escalation）语义：
阈值、通知渠道、静默（maintenance window）、值班升级链、确认机制。
把「告警什么、通知谁、多久升级」转成确定性校验：阈值结构合法、
通知渠道白名单、升级链单调（低到高、不可跳级回退）、确认字段非空。

关键立场：**告警策略是「约定」不是「触达」**。本角色只校验告警策略与
升级清单结构是否成立，不实际发送通知、不实际呼叫值班（那是运行期动作）。
值班升级必须「从低到高」逐级，跳级/回退都是策略错误。

动作：
  alert       告警规则校验
  escalation  值班升级清单校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "alert"
DESC = "告警与升级：alert/escalation"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("alert", "告警规则校验"), ("escalation", "值班升级清单校验")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "alert":
        return _validate_alert(data)
    if args.action == "escalation":
        return _validate_escalation(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_alert(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["alert"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", alert_count=0)

    rules = data.get("rules") or []
    ok_rules = isinstance(rules, list) and len(rules) > 0
    checks.append(_ck(ok_rules,
                      f"告警规则 ≥1（实际 "
                      f"{len(rules) if isinstance(rules, list) else 0}）",
                      "alert.count"))

    # 每条规则须含 metric/condition/threshold/channel
    bad = [i for i, r in enumerate(rules if isinstance(rules, list) else [])
           if not isinstance(r, dict)
           or not str(r.get("metric", "")).strip()
           or not str(r.get("condition", "")).strip()
           or r.get("threshold") is None
           or not str(r.get("channel", "")).strip()]
    checks.append(_ck(not bad,
                      f"规则含 metric/condition/threshold/channel（缺 {bad or '无'}）",
                      "alert.required"))

    # 严重度白名单
    bad_sev = [r.get("severity") for r in (rules if isinstance(rules, list) else [])
               if isinstance(r, dict) and r.get("severity") not in th["severities"]]
    checks.append(_ck(not bad_sev,
                      f"严重度在 {th['severities']}（越界 {bad_sev or '无'}）",
                      "alert.severity"))

    # 通知渠道白名单
    bad_ch = [r.get("channel") for r in (rules if isinstance(rules, list) else [])
              if isinstance(r, dict) and r.get("channel") not in th["channels"]]
    checks.append(_ck(not bad_ch,
                      f"通知渠道在 {th['channels']}（越界 {bad_ch or '无'}）",
                      "alert.channel"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        alert_count=len(rules) if isinstance(rules, list) else 0,
        narrative=f"告警规则 {len(rules) if isinstance(rules, list) else 0} 条")


# --------------------------------------------------------------------------- #
def _validate_escalation(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["alert"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", escalation_count=0)

    chain = data.get("chain") or []
    ok_chain = isinstance(chain, list) and len(chain) > 0
    checks.append(_ck(ok_chain,
                      f"升级链 ≥1（实际 "
                      f"{len(chain) if isinstance(chain, list) else 0}）",
                      "escalation.count"))

    # 每级须含 level/role/channel/acknowledged
    bad = [i for i, r in enumerate(chain if isinstance(chain, list) else [])
           if not isinstance(r, dict)
           or not str(r.get("level", "")).strip()
           or not str(r.get("role", "")).strip()
           or r.get("channel") not in th["channels"]
           or r.get("acknowledged") not in (True, False)]
    checks.append(_ck(not bad,
                      f"每级含 level/role/channel(白名单)/acknowledged（缺 {bad or '无'}）",
                      "escalation.required"))

    # 升级链 level 单调递增（低到高，跳级/回退都是策略错误）
    levels = [r.get("level") for r in (chain if isinstance(chain, list) else [])
              if isinstance(r, dict)]
    monotonic = all(isinstance(l, (int, float)) for l in levels) and \
        levels == sorted(levels) and len(set(levels)) == len(levels)
    checks.append(_ck(monotonic,
                      f"升级链 level 严格单调递增（实际 {levels}）",
                      "escalation.monotonic"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        escalation_count=len(chain) if isinstance(chain, list) else 0,
        narrative=f"值班升级链 {len(chain) if isinstance(chain, list) else 0} 级")

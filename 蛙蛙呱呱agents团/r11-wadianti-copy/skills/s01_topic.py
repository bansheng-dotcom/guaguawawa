# -*- coding: utf-8 -*-
"""S01 内容策略与选题 —— 能力域 1。

整合自 bzwh321__article-director（topic-architect 的选题规划 → 可执行结构）。
把「选题」从口头判断转成确定性校验：选题卡必填字段、渠道白名单、内容规划
条目齐备。本角色不做统计结论（交 R06），选题卡只要求「差异点」可陈述，
不要求市场数据（那是 R05 的事）。

动作：
  brief  选题卡（受众/痛点/渠道/差异点）
  plan   内容规划（条目：topic/owner/due/status）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "topic"
DESC = "内容策略与选题：brief/plan"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    b = act.add_parser("brief", help="校验选题卡")
    b.add_argument("--input", required=True)
    pl = act.add_parser("plan", help="校验内容规划")
    pl.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "brief":
        return _validate_brief(data)
    if args.action == "plan":
        return _validate_plan(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_brief(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    required = th["topic"]["brief_required"]
    missing = [k for k in required if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"选题卡必填字段齐备（缺 {missing or '无'}）",
                      "topic.brief_fields"))

    channel = data.get("channel")
    ok_ch = channel in th["topic"]["channels"]
    checks.append(_ck(ok_ch, f"channel={channel!r} 在白名单", "topic.channel"))
    if not ok_ch:
        return c.result(checks, ok=False, verdict="FAIL", channel=channel,
                        topic_count=1)

    # 差异点必须可陈述，且不能是空泛措辞
    diff = str(data.get("differentiator", "")).strip()
    vague = ["更好", "更强", "更多", "不一样", "差异化", "有特色", "提升"]
    ok_diff = bool(diff) and not (len(diff) < 4 and c.has_any(diff, vague))
    checks.append(_ck(ok_diff, "差异点具体可陈述（非空泛）", "topic.differentiator"))

    audience = str(data.get("audience", "")).strip()
    checks.append(_ck(bool(audience), "受众明确", "topic.audience"))

    ok = not missing and ok_ch and ok_diff and bool(audience)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    channel=channel, topic_count=1)


# --------------------------------------------------------------------------- #
def _validate_plan(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    items = data.get("items")
    ok_items = isinstance(items, list) and len(items) > 0
    checks.append(_ck(ok_items, f"内容规划条目 ≥1（实际 {len(items) if isinstance(items, list) else 0}）",
                      "topic.plan_items"))
    if not ok_items:
        return c.result(checks, ok=False, verdict="FAIL", item_count=0)

    item_ok = True
    status_enum = th["topic"]["status_enum"]
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            checks.append(_ck(False, f"items[{i}] 非对象", "topic.plan_item"))
            item_ok = False
            continue
        for k in th["topic"]["plan_required"]:
            if not str(it.get(k, "")).strip():
                checks.append(_ck(False, f"items[{i}] 缺 {k}", "topic.plan_item"))
                item_ok = False
        st = it.get("status")
        if st not in status_enum:
            checks.append(_ck(False, f"items[{i}].status={st!r} 不在枚举 {status_enum}",
                              "topic.plan_status"))
            item_ok = False

    ok = ok_items and item_ok
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    item_count=len(items) if isinstance(items, list) else 0)

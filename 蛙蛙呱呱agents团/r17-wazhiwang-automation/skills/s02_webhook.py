# -*- coding: utf-8 -*-
"""S02 Webhook 与事件处理 —— 能力域 2。

整合自 n8n-io__n8n 的 trigger-input-data-shapes / intent-recognition skills：
  - Webhook 触发流程（path/method/inputData 形状匹配 + 校验/路由）
  - 业务事件日志（类型白名单 + 路由完整性 + 时序单调）

关键立场：**接收、校验、路由、重放业务事件，但不替业务角色定义事件语义**。
本门禁只做确定性结构校验：path 合规 + method 白名单 + inputData 形状匹配 +
事件类型白名单 + 路由兜底 + 时序单调。

动作：
  webhook  Webhook 触发流程结构校验
  event    业务事件日志与路由校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "webhook"
DESC = "Webhook 与事件处理：webhook/event"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("webhook", help="校验 Webhook 触发流程（path/method/形状/路由）")
    a.add_argument("--input", required=True)
    b = act.add_parser("event", help="校验业务事件日志与路由完整性")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "webhook":
        return _validate_webhook(data)
    if args.action == "event":
        return _validate_event(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_webhook(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["webhook"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", webhook_count=0)

    path = str(data.get("path", "")).strip()
    checks.append(_ck(len(path) >= th["path_min_len"] and not path.startswith("/"),
                      f"path={path!r} 合规（长度≥{th['path_min_len']} 且不空）",
                      "webhook.path"))

    method = str(data.get("method", "GET")).upper()
    checks.append(_ck(method in th["methods"],
                      f"method={method!r} 在白名单", "webhook.method"))

    # inputData 形状匹配：触发器类型决定输入形状（n8n trigger-input-data-shapes）
    trigger = str(data.get("trigger_type", "webhook"))
    shape_map = th["trigger_input_shapes"]
    expect = shape_map.get(trigger, "body")
    shape = str(data.get("input_shape", expect))
    checks.append(_ck(shape == expect or (expect == "none" and shape in ("none", "body")),
                      f"inputData 形状={shape!r} 匹配 {trigger}（期望 {expect!r}）",
                      "webhook.shape"))

    # 校验/路由：handlers 有匹配规则或默认兜底；重放必须声明幂等
    handlers = data.get("handlers") or []
    if not isinstance(handlers, list) or not handlers:
        checks.append(_ck(False, "handlers 必须非空（含默认兜底）", "webhook.handlers"))
        handlers = []
    else:
        checks.append(_ck(True, f"handlers {len(handlers)} 个", "webhook.handlers"))
    has_default = any(isinstance(h, dict) and h.get("default") is True
                      for h in handlers)
    has_match = any(isinstance(h, dict) and h.get("match") for h in handlers)
    checks.append(_ck(has_default or has_match,
                      f"有匹配规则或默认兜底（default={has_default}）",
                      "webhook.route_fallback"))

    replay = data.get("replay")
    if replay is not None:
        idem = data.get("replay_idempotent", False)
        checks.append(_ck(bool(idem),
                          "重放已声明幂等（idempotency_key/去重）",
                          "webhook.replay_idempotent"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        webhook_count=1, path=path, method=method,
        narrative=f"Webhook {method} {path}：{len(handlers)} 个 handler / "
                  f"inputData 形状 {shape!r}")


# --------------------------------------------------------------------------- #
def _validate_event(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["webhook"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", event_count=0, route_count=0)

    events = data.get("events")
    if not isinstance(events, list) or not events:
        return c.result([_ck(False, "events 必须是非空列表", "event.list")],
                        ok=False, verdict="FAIL", event_count=0, route_count=0)

    checks.append(_ck(True, f"事件 {len(events)} 条", "event.count"))

    # 类型白名单 + entity_id 非空
    bad_type: List[str] = []
    no_entity: List[str] = []
    for e in events:
        if not isinstance(e, dict):
            bad_type.append("(非对象)")
            continue
        if str(e.get("type", "")) not in th["event_types"]:
            bad_type.append(str(e.get("type", "?")))
        if not e.get("entity_id"):
            no_entity.append(str(e.get("type", "?")))
    checks.append(_ck(not bad_type,
                      f"事件类型在白名单（越界 {sorted(set(bad_type)) or '无'}）",
                      "event.type"))
    checks.append(_ck(not no_entity,
                      f"事件 entity_id 非空（缺 {sorted(set(no_entity)) or '无'}）",
                      "event.entity_id"))

    # 时序单调：ts 非递减（同秒合法，用于批次排序，非严格递增）
    ts_list = [e.get("ts") for e in events if isinstance(e, dict)]
    mono = True
    prev = None
    for t in ts_list:
        if t is None:
            continue
        try:
            cur = float(t)
        except (TypeError, ValueError):
            cur = None
        if cur is not None and prev is not None and cur < prev:
            mono = False
            break
        if cur is not None:
            prev = cur
    checks.append(_ck(mono, "事件时序单调非递减（ts 无倒退）", "event.monotonic"))

    # 路由完整性：每个事件类型有对应 handler 或 dead-letter 声明
    routes = data.get("routes") or []
    if not isinstance(routes, list):
        routes = []
    route_types = {str(r.get("type")) for r in routes if isinstance(r, dict)}
    dead_letter = bool(data.get("dead_letter"))
    event_types = {str(e.get("type")) for e in events if isinstance(e, dict)}
    unhandled = event_types - route_types
    checks.append(_ck(not unhandled or dead_letter,
                      f"路由完整（未覆盖 {sorted(unhandled) or '无'}，"
                      f"dead_letter={dead_letter}）", "event.route"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        event_count=len(events), route_count=len(routes),
        narrative=f"事件 {len(events)} 条 / 路由 {len(routes)} 个 / "
                  f"未覆盖 {len(unhandled)}")

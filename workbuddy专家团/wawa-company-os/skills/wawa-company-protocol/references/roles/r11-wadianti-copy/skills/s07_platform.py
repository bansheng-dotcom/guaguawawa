# -*- coding: utf-8 -*-
"""S07 多平台适配 —— 能力域 7。

整合自 bzwh321__article-director 的边界 + R11「多平台改写」能力域。把「针对微信/
小红书/抖音/B站/知乎/X 改写」转成确定性校验：平台白名单 + 平台版本文案差异字段
（长度限制/语气偏移/标签）。发布清单必须逐条 authorized（对外发布需授权）。

动作：
  adapt   平台改写（platform/title/length_limit/tone_shift/hashtags）
  publish 发布清单（platform/url/status/authorized）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "platform"
DESC = "多平台适配：adapt/publish"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("adapt", help="校验平台改写")
    a.add_argument("--input", required=True)
    pu = act.add_parser("publish", help="校验发布清单")
    pu.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "adapt":
        return _validate_adapt(data)
    if args.action == "publish":
        return _validate_publish(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_adapt(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    platform = data.get("platform")
    ok_plat = platform in th["platform"]["platforms"]
    checks.append(_ck(ok_plat, f"platform={platform!r} 在白名单 {th['platform']['platforms']}",
                      "platform.adapt.platform"))
    if not ok_plat:
        return c.result(checks, ok=False, verdict="FAIL", platform=platform)

    for k in th["platform"]["adapt_required"]:
        if k == "hashtags":
            ok = isinstance(data.get(k), list)
        else:
            ok = bool(str(data.get(k, "")).strip())
        checks.append(_ck(ok, f"改写字段 {k} 齐备", f"platform.adapt.{k}"))

    ok = all(ch["ok"] for ch in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    platform=platform)


# --------------------------------------------------------------------------- #
def _validate_publish(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    items = data.get("items")
    ok_items = isinstance(items, list) and len(items) > 0
    checks.append(_ck(ok_items,
                      f"发布清单 ≥1（实际 {len(items) if isinstance(items, list) else 0}）",
                      "platform.publish_items"))
    if not ok_items:
        return c.result(checks, ok=False, verdict="FAIL", item_count=0)

    all_auth = True
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            checks.append(_ck(False, f"items[{i}] 非对象", "platform.publish_item"))
            all_auth = False
            continue
        for k in th["platform"]["publish_required"]:
            checks.append(_ck(bool(str(it.get(k, "")).strip()),
                              f"items[{i}] 缺 {k}", "platform.publish_item"))
        # authorized 必须为 true（对外发布需授权，机器判据）
        auth = it.get("authorized")
        if auth is not True:
            checks.append(_ck(False, f"items[{i}].authorized 非 true（需授权）",
                              "platform.publish_authorized"))
            all_auth = False

    ok = ok_items and all_auth and all(ch["ok"] for ch in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    item_count=len(items) if isinstance(items, list) else 0)

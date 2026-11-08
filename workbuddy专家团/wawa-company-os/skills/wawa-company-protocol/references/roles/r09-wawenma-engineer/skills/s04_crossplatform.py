# -*- coding: utf-8 -*-
"""s04 跨端生产工程（crossplatform）：build / platform 两动作。

- build：构建矩阵——platform 白名单、构建状态、跳过数上限。
- platform：平台差异——state_management 白名单、差异文档化。
阈值：thresholds.json → crossplatform.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "crossplatform"
DESC = "跨端生产工程：构建、测试、平台差异"

ACTIONS = {
    "build": "跨端构建矩阵",
    "platform": "平台差异与状态管理",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #
def build(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["crossplatform"]
    platforms = th["platforms"]
    build_statuses = th["build_statuses"]
    max_skipped = th["max_skipped"]

    targets = data.get("targets") or []
    checks: List[Dict[str, Any]] = []

    if not targets:
        checks.append(c.ck(False, "targets 为空，无构建矩阵可校验", "crossplatform:targets", "CRITICAL"))

    skipped = 0
    for i, t in enumerate(targets):
        platform = str(t.get("platform") or "")
        status = str(t.get("status") or "")
        if platform not in platforms:
            checks.append(c.ck(False, f"targets[{i}] platform={platform!r} 不在白名单 {platforms}", "crossplatform:platform", "HIGH", **{"index": i}))
        else:
            checks.append(c.ck(True, f"平台 {platform} 合规", "crossplatform:platform", **{"platform": platform}))
        if status not in build_statuses:
            checks.append(c.ck(False, f"targets[{i}] status={status!r} 不在枚举 {build_statuses}", "crossplatform:status", "HIGH", **{"index": i}))
        elif status == "skipped":
            skipped += 1
            checks.append(c.ck(False, f"平台 {platform} 构建被跳过", "crossplatform:skipped", "HIGH", **{"platform": platform}))
        elif status == "failed":
            checks.append(c.ck(False, f"平台 {platform} 构建失败", "crossplatform:build_failed", "HIGH", **{"platform": platform}))
        else:
            checks.append(c.ck(True, f"平台 {platform} 构建成功", "crossplatform:build_ok", **{"platform": platform}))

    if skipped > max_skipped:
        checks.append(c.ck(False, f"跳过构建数 {skipped} > 上限 {max_skipped}", "crossplatform:skip_cap", "CRITICAL"))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   target_count=len(targets),
                   skipped=skipped,
                   verdict=verdict,
                   next="跨端构建矩阵全绿" if ok else "修复平台/跳过/失败构建后重新 build",
                   )
    return out


# --------------------------------------------------------------------------- #
# platform
# --------------------------------------------------------------------------- #
def platform(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["crossplatform"]
    platforms = th["platforms"]
    state_management = th["state_management"]

    targets = data.get("targets") or []
    diffs = data.get("diffs") or []
    checks: List[Dict[str, Any]] = []

    if not targets:
        checks.append(c.ck(False, "targets 为空，无平台差异可校验", "crossplatform:targets", "CRITICAL"))

    sm_set: set = set()
    for i, t in enumerate(targets):
        platform = str(t.get("platform") or "")
        sm = str(t.get("state_management") or "")
        if platform not in platforms:
            checks.append(c.ck(False, f"targets[{i}] platform={platform!r} 不在白名单", "crossplatform:platform", "HIGH", **{"index": i}))
        if sm and sm not in state_management:
            checks.append(c.ck(False, f"targets[{i}] state_management={sm!r} 不在白名单 {state_management}", "crossplatform:state_management", "HIGH", **{"index": i}))
        else:
            sm_set.add(sm)

    if len(sm_set) > 1:
        checks.append(c.ck(True, f"多状态管理方案 {sorted(sm_set)} 已声明，需差异文档", "crossplatform:state_management_multi", **{"state_management": sorted(sm_set)}))

    if not diffs:
        checks.append(c.ck(False, "diffs 为空，未文档化平台差异", "crossplatform:diffs", "HIGH"))
    else:
        checks.append(c.ck(True, f"平台差异文档 {len(diffs)} 条", "crossplatform:diffs", **{"diff_count": len(diffs)}))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   target_count=len(targets),
                   state_management=sorted(sm_set),
                   diff_count=len(diffs),
                   verdict=verdict,
                   next="平台差异已文档化" if ok else "补齐平台差异文档/状态管理白名单后重新 platform",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "build":
        result = build(data)
    elif args.action == "platform":
        result = platform(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result

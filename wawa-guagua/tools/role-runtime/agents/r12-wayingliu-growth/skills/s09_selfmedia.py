# -*- coding: utf-8 -*-
"""S09 自媒体运营 —— 能力域 9。

整合自 bzwh321__self-media-data-console-bzwh（self-media-console-workflow /
self-media-attribution）+ 自媒体工作台-trae。把「自媒体运营」转成确定性校验：
多平台数据看板 + 日报确定性结论规则 + 数据接入探测（如实降级）。

动作：
  daily   运营日报（多平台汇总 + 确定性结论）
  probe   数据接入探测（恒 ok=true，缺数据如实降级）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "selfmedia"
DESC = "自媒体运营：daily/probe"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    b = act.add_parser("daily", help="校验运营日报")
    b.add_argument("--input", required=True)
    u = act.add_parser("probe", help="数据接入探测")
    # probe 无输入文件


def run(args) -> Dict[str, Any]:
    if args.action == "daily":
        data = c.load_json(args.input)
        return _validate_daily(data)
    if args.action == "probe":
        return _probe()
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_daily(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    missing = [k for k in th["selfmedia"]["daily_required"]
               if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"日报三件套齐备（缺 {missing or '无'}）",
                      "selfmedia.daily_fields"))

    summary = data.get("platform_summary")
    known = th["selfmedia"]["platforms"]
    ok_summary = isinstance(summary, list) and len(summary) > 0
    checks.append(_ck(ok_summary,
                      f"平台汇总 ≥1（实际 {len(summary) if isinstance(summary, list) else 0}）",
                      "selfmedia.summary"))
    if ok_summary:
        bad_platform = []
        for row in summary:
            if not isinstance(row, dict) or row.get("platform") not in known:
                bad_platform.append(row if isinstance(row, dict) else row)
        checks.append(_ck(not bad_platform, f"平台在白名单（越界 {bad_platform or '无'}）",
                          "selfmedia.platform_enum"))
        # 指标字段白名单
        bad_metric = []
        for row in summary:
            if not isinstance(row, dict):
                continue
            for k in row.keys():
                if k in ("platform", "platform_name"):
                    continue
                if k not in th["selfmedia"]["metric_fields"]:
                    bad_metric.append(k)
        checks.append(_ck(not bad_metric,
                          f"指标字段在白名单（越界 {bad_metric or '无'}）",
                          "selfmedia.metric_enum"))

    metric_fields = th["selfmedia"]["metric_fields"]
    bad_metric = []
    if ok_summary:
        for row in summary:
            if not isinstance(row, dict):
                continue
            for k in row.keys():
                if k in ("platform", "platform_name"):
                    continue
                if k not in metric_fields:
                    bad_metric.append(k)
    ok = not missing and ok_summary and (
        not ok_summary or not any(
            (not isinstance(r, dict) or r.get("platform") not in known) for r in summary)) \
        and not bad_metric
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    platform_count=len(summary) if isinstance(summary, list) else 0)


# --------------------------------------------------------------------------- #
def _probe() -> Dict[str, Any]:
    """数据接入探测：如实降级，恒 ok=true，缺数据只反映在 status 上（探测非门禁）。"""
    import os
    # 探测数据根：仅检查是否存在可选数据目录，缺则 status=blocked，不假装有数据
    here = os.path.dirname(os.path.abspath(__file__))
    data_root = os.path.join(os.path.dirname(os.path.dirname(here)), "..",
                             "补充技能", "自媒体工作台-trae", "data")
    has_demo = os.path.exists(os.path.join(data_root, "demo"))
    status = "ready" if has_demo else "blocked"
    checks = [c.ck(True, "多平台数据接入探测完成（探测非门禁）", "selfmedia.probe",
                   detected=has_demo)]
    return c.result(checks, ok=True, verdict="PASS", status=status,
                    detected=has_demo,
                    next=("数据接入可用，可产出看板与日报"
                          if has_demo else "本机未检测到数据源，日报口径校验仍可用，"
                          "真实数据接入需用户配置"))


def add_parser_probe_help(p) -> None:
    p.add_argument("--skill", required=True)

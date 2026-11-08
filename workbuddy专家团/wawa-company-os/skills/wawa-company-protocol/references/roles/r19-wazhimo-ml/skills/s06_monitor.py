# -*- coding: utf-8 -*-
"""S06 模型监控接口 —— 能力域 6。

整合自 mlflow__mlflow 的 mlflow-trace-metrics（聚合指标查询：latency/token/
count/quality 趋势）+ mlflow-evaluation 的 databricks-online-monitoring
（质量/漂移/延迟/成本交给 R20）。把「监控接口」转成确定性校验：指标视图白名单、
聚合方式白名单、指标名白名单、时间窗、告警阈值声明。

关键立场：**监控接口是「交给 R20 持续观察」的需求规格，不是监控本身**。
本角色定义「该监控哪些质量/漂移/延迟/成本指标、告警阈值设多少」，
实际持续监控与告警由 R20 蛙值守执行。本角色只产出监控需求工件，
**不部署监控、不定义生产告警**（边界：持续监控与备份归 R20）。

动作：
  metrics  指标查询口径校验
  drift    漂移监控需求校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "monitor"
DESC = "模型监控接口：metrics/drift"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("metrics", "校验指标查询口径"), ("drift", "校验漂移监控需求")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "metrics":
        return _validate_metrics(data)
    if args.action == "drift":
        return _validate_drift(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_metrics(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["monitor"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", metric_name="", metric_count=0)

    # 指标名白名单
    mname = data.get("metric_name")
    checks.append(_ck(mname in th["metric_names"],
                      f"指标名={mname!r} 在白名单 {th['metric_names']}",
                      "metrics.name"))

    # 指标视图白名单（TRACES/SPANS/ASSESSMENTS）
    view = data.get("view")
    checks.append(_ck(view in th["metric_views"],
                      f"指标视图={view!r} 在白名单 {th['metric_views']}",
                      "metrics.view"))

    # 聚合方式白名单
    agg = data.get("aggregation")
    checks.append(_ck(agg in th["aggregations"],
                      f"聚合方式={agg!r} 在白名单 {th['aggregations']}",
                      "metrics.aggregation"))

    # 时间窗非空（mlflow-trace-metrics 铁律：显式起止）
    checks.append(_ck(bool(str(data.get("start", "")).strip())
                      and bool(str(data.get("end", "")).strip()),
                      "声明时间窗起止", "metrics.time_window"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        metric_name=mname, view=view, aggregation=agg,
        metric_count=1,
        narrative=f"监控指标 {mname}：{view} / {agg}")


# --------------------------------------------------------------------------- #
def _validate_drift(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", alert_count=0)

    # 漂移监控四要素：指标/阈值/通知渠道/责任方
    checks.append(_ck(bool(str(data.get("metric", "")).strip()),
                      "漂移指标非空", "drift.metric"))
    checks.append(_ck(bool(str(data.get("threshold", "")).strip()),
                      "漂移阈值非空（告警阈值）", "drift.threshold"))
    checks.append(_ck(bool(str(data.get("channel", "")).strip()),
                      "通知渠道非空", "drift.channel"))

    # 责任方非空（交给谁持续观察：R20）
    checks.append(_ck(bool(str(data.get("owner", "")).strip()),
                      "监控责任方非空（R20）", "drift.owner"))

    # 阈值须为数值或可解析（告警阈值须能量化）
    th_raw = data.get("threshold_value")
    checks.append(_ck(isinstance(th_raw, (int, float)) and not isinstance(th_raw, bool),
                      f"阈值可量化（threshold_value={th_raw!r}）",
                      "drift.threshold_numeric"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        metric=data.get("metric"), alert_count=1,
        narrative=f"漂移监控 {data.get('metric')}：阈值 {data.get('threshold')} → {data.get('owner')}")

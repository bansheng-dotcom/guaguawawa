# -*- coding: utf-8 -*-
"""S04 Agent Trace 与调试 —— 能力域 4。

整合自 mlflow__mlflow 的 mlflow-trace-analysis（span 树检查、错误定位、反馈
判读）+ mlflow-trace-retrieval（trace 检索/过滤）+ mlflow-trace-instrumentation
（span 类型）。把「Trace 采集/检索/分析」转成确定性校验：trace 状态白名单、
span 类型白名单、span 结构（parent 引用完整）、错误定位、反馈判读。

关键立场：**Trace 是调试证据，不是结论**。`OK` 状态只说明执行成功，不代表
输出正确（mlflow-trace-analysis 铁律）；`STATUS_CODE_UNSET` 不是错误；HUMAN
反馈描述的是「报告体验」，需用 span 佐证。本角色只产出 Trace 报告与调试证据，
**不修改应用代码**（诊断止于证据与建议，修复交 s05 release 的回归流程）。

动作：
  analyze   Trace 分析校验（span 树 + 错误定位）
  retrieval Trace 检索校验（过滤条件 + 时间窗）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "trace"
DESC = "Agent Trace 与调试：analyze/retrieval"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("analyze", "校验 Trace 分析报告"), ("retrieval", "校验 Trace 检索条件")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "analyze":
        return _validate_analyze(data)
    if args.action == "retrieval":
        return _validate_retrieval(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_analyze(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["trace"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", trace_id="", span_count=0)

    trace_id = str(data.get("trace_id", "")).strip()
    checks.append(_ck(bool(trace_id), "Trace ID 非空", "analyze.trace_id"))

    # trace 状态白名单
    state = data.get("state")
    checks.append(_ck(state in th["trace_states"],
                      f"trace 状态={state!r} 在白名单 {th['trace_states']}",
                      "analyze.state"))

    spans = data.get("spans") or []
    ok_spans = isinstance(spans, list) and len(spans) > 0
    checks.append(_ck(ok_spans,
                      f"span ≥1（实际 {len(spans) if isinstance(spans, list) else 0}）",
                      "analyze.spans"))

    # span 类型白名单（mlflow span type）
    bad_type = [s.get("name") for s in (spans if isinstance(spans, list) else [])
                if isinstance(s, dict) and s.get("type") not in th["span_types"]]
    checks.append(_ck(not bad_type,
                      f"span 类型在白名单（越界 {bad_type or '无'}）",
                      "analyze.span_type"))

    # span 结构：parent 引用完整（除根外，父 span 须存在）
    span_ids = {str(s.get("span_id", "")) for s in (spans if isinstance(spans, list) else [])
                if isinstance(s, dict)}
    dangling = [s.get("span_id") for s in (spans if isinstance(spans, list) else [])
                if isinstance(s, dict) and str(s.get("parent_span_id", "")).strip()
                and str(s.get("parent_span_id", "")).strip() not in span_ids]
    checks.append(_ck(not dangling,
                      f"parent 引用完整（悬空 {dangling or '无'}）",
                      "analyze.parent_integrity"))

    # 若状态为 ERROR，必须定位错误 span（错误定位是调试的核心产出）
    if state == "ERROR":
        err_spans = [s.get("name") for s in (spans if isinstance(spans, list) else [])
                     if isinstance(s, dict) and s.get("status") == "STATUS_CODE_ERROR"]
        checks.append(_ck(bool(err_spans),
                          f"ERROR 状态定位到错误 span（{err_spans or '无'}）",
                          "analyze.error_loc"))
    else:
        checks.append(_ck(True, f"{state} 状态不要求定位错误 span", "analyze.error_loc"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        trace_id=trace_id, state=state,
        span_count=len(spans) if isinstance(spans, list) else 0,
        narrative=f"Trace {trace_id}：{state}，"
                  f"{len(spans) if isinstance(spans, list) else 0} 个 span")


# --------------------------------------------------------------------------- #
def _validate_retrieval(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", trace_count=0)

    # 检索必须有过滤条件（trace ID 或过滤字符串，二选一）
    trace_id = str(data.get("trace_id", "")).strip()
    filter_str = str(data.get("filter_string", "")).strip()
    checks.append(_ck(bool(trace_id) or bool(filter_str),
                      "检索条件非空（trace_id 或 filter_string）",
                      "retrieval.condition"))

    # 时间窗：必须声明起止（mlflow-trace-retrieval 铁律：UC 搜索需时间下界）
    start_ms = str(data.get("start_ms", "")).strip()
    end_ms = str(data.get("end_ms", "")).strip()
    checks.append(_ck(bool(start_ms) and bool(end_ms),
                      f"声明时间窗（start={start_ms or '?'} / end={end_ms or '?'}）",
                      "retrieval.time_window"))
    checks.append(_ck(bool(start_ms) and bool(end_ms) and start_ms <= end_ms,
                      f"时间窗顺序 {start_ms or '?'} ≤ {end_ms or '?'}",
                      "retrieval.window_order"))

    # 上限结果数（max_results）必须声明，防全表扫描
    max_results = data.get("max_results")
    checks.append(_ck(isinstance(max_results, int) and max_results > 0,
                      f"声明 max_results > 0（实际 {max_results!r}）",
                      "retrieval.max_results"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        trace_count=1 if trace_id else 0,
        narrative=f"Trace 检索：{('按 ID ' + trace_id) if trace_id else '按过滤 ' + filter_str}")

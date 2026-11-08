# -*- coding: utf-8 -*-
"""S03 订阅与计量计费 —— 能力域 3。

整合自 getlago__lago 的计费内核：`api/app/models/billable_metric.rb` 的
AGGREGATION_TYPES（count_agg/sum_agg/max_agg/unique_count_agg/weighted_sum_agg/
latest_agg/custom_agg）、`api/app/models/charge.rb` 的 CHARGE_MODELS
（standard/graduated/package/percentage/volume/graduated_percentage）、
`api/app/models/plan.rb` 的 interval（weekly/monthly/yearly/quarterly）、
`api/app/models/invoice.rb` 的 VISIBLE_STATUS（draft/finalized/voided/failed/pending）。

把「计费方案」转成确定性校验：计费方案（计量聚合类型 + 计费模型 + 周期白名单）、
用量记录（metric_code + quantity + 聚合类型）、账单（状态 + 金额复算）。

关键立场：**计量和计费是两个层**——先有 billable_metric 定义「怎么聚合用量」，
再有 charge 定义「怎么计费」；聚合类型与计费模型必须能对上（custom_agg 须显式声明）。

动作：
  plan     计费方案（计量聚合 + 计费模型 + 周期）
  usage    用量记录与聚合校验
  invoice  账单状态与金额复算
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "billing"
DESC = "订阅与计量计费：plan/usage/invoice"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("plan", help="校验计费方案")
    a.add_argument("--input", required=True)
    b = act.add_parser("usage", help="校验用量记录")
    b.add_argument("--input", required=True)
    c_ = act.add_parser("invoice", help="校验账单")
    c_.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "plan":
        return _validate_plan(data)
    if args.action == "usage":
        return _validate_usage(data)
    if args.action == "invoice":
        return _validate_invoice(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_plan(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    bth = c.load_thresholds()["billing"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", plan_count=0)

    plan_code = str(data.get("code", "")).strip()
    checks.append(_ck(bool(plan_code), "方案代码非空", "plan.code"))

    interval = data.get("interval")
    ok_interval = interval in bth["plan_intervals"]
    checks.append(_ck(ok_interval, f"计费周期={interval!r} 在白名单", "plan.interval"))

    charges = data.get("charges") or []
    ok_charges = isinstance(charges, list) and len(charges) > 0
    checks.append(_ck(ok_charges,
                      f"计费规则 ≥1（实际 {len(charges) if isinstance(charges, list) else 0}）",
                      "plan.charges"))

    bad_model = [ch.get("charge_model") for ch in charges if isinstance(ch, dict)
                 and ch.get("charge_model") not in bth["charge_models"]]
    checks.append(_ck(not bad_model,
                      f"计费模型在白名单（越界 {bad_model or '无'}）", "plan.charge_model"))

    bad_agg = [ch.get("aggregation_type") for ch in charges if isinstance(ch, dict)
               and ch.get("aggregation_type") not in bth["aggregation_types"]]
    checks.append(_ck(not bad_agg,
                      f"聚合类型在白名单（越界 {bad_agg or '无'}）", "plan.aggregation"))

    # custom_agg 必须显式声明（不假装有自定义聚合引擎）
    custom_no_decl = [ch.get("charge_model") for ch in charges if isinstance(ch, dict)
                      and ch.get("aggregation_type") == "custom_agg"
                      and not str(ch.get("custom_expression", "")).strip()]
    checks.append(_ck(not custom_no_decl,
                      f"custom_agg 必须声明表达式（缺 {custom_no_decl or '无'}）",
                      "plan.custom_agg"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        plan_count=1, charge_count=len(charges) if isinstance(charges, list) else 0,
        interval=interval,
        narrative=(f"计费方案 {plan_code}（{interval}）{len(charges) if isinstance(charges, list) else 0} 条计费规则"))


# --------------------------------------------------------------------------- #
def _validate_usage(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    bth = c.load_thresholds()["billing"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", usage_count=0)

    events = data.get("usage") or data.get("events")
    if not isinstance(events, list) or not events:
        return c.result([_ck(False, "usage 必须是非空列表", "usage.list")],
                        ok=False, verdict="FAIL", usage_count=0)

    missing = [e.get("metric_code") for e in events if isinstance(e, dict)
               and any(not str(e.get(k, "")).strip() for k in bth["usage_required"])]
    checks.append(_ck(not missing, f"用量必填齐备（缺 {missing or '无'}）",
                      "usage.required"))

    bad_qty = [e.get("metric_code") for e in events if isinstance(e, dict)
               and c._num(e.get("quantity")) <= 0]
    checks.append(_ck(not bad_qty, f"用量均为正（异常 {bad_qty or '无'}）",
                      "usage.quantity"))

    bad_agg = [e.get("metric_code") for e in events if isinstance(e, dict)
               and e.get("aggregation_type") not in bth["aggregation_types"]]
    checks.append(_ck(not bad_agg,
                      f"聚合类型在白名单（越界 {bad_agg or '无'}）", "usage.aggregation"))

    total_qty = round(sum(c._num(e.get("quantity")) for e in events
                          if isinstance(e, dict)), 2)
    checks.append(_ck(True, f"用量合计 {total_qty}（{len(events)} 条事件）",
                      "usage.total"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        usage_count=len(events), total_quantity=total_qty,
        narrative=f"用量 {len(events)} 条、合计 {total_qty}")


# --------------------------------------------------------------------------- #
def _validate_invoice(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    bth = c.load_thresholds()["billing"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", invoice_count=0)

    iid = str(data.get("id", "")).strip()
    checks.append(_ck(bool(iid), "账单号非空", "invoice.id"))

    status = data.get("status")
    ok_status = status in bth["invoice_status"]
    checks.append(_ck(ok_status, f"账单状态={status!r} 在白名单", "invoice.status"))

    total = c.money(data.get("total"))
    checks.append(_ck(total > 0, f"账单总额={total} 为正", "invoice.total"))

    # 金额复算：line items 之和必须等于 total（口径恒等）
    lines = data.get("line_items") or []
    if isinstance(lines, list) and lines:
        sum_lines = round(sum(c.money(li.get("amount")) for li in lines
                              if isinstance(li, dict)), 2)
        ok_identity = abs(sum_lines - total) < 0.01
        checks.append(_ck(ok_identity,
                          f"账单金额恒等：明细合计 {sum_lines} = 总额 {total}",
                          "invoice.identity"))
    else:
        checks.append(_ck(False, "账单缺明细行", "invoice.lines"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        invoice_count=1, status=status, total=total,
        narrative=f"账单 {iid}（{status}）总额 {total}")

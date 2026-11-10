# -*- coding: utf-8 -*-
"""S05 批流与增量边界 —— 能力域 5。

整合自 airbyte sync mode（full_refresh / incremental）+ dbt incremental
materialization + snapshot/CDC 语义。把「全量/增量/快照/迟到数据/重跑策略」
转成确定性校验：模式白名单、分区键、水位字段（watermark）、迟到容忍窗口、
重跑幂等键。

关键立场：**增量边界决定「丢数还是重数」**。水位字段缺失 → 无法定位增量起点；
重跑幂等键缺失 → 重跑会重复入账。本角色只校验增量口径与策略，
**不擅自执行回填**（回填是高风险运维动作，红线 2，交 s07 审批）。

动作：
  strategy  增量策略校验
  backfill  回填方案校验（口径，非执行）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "incremental"
DESC = "批流与增量边界：strategy/backfill"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("strategy", "增量策略校验"), ("backfill", "回填方案校验")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "strategy":
        return _validate_strategy(data)
    if args.action == "backfill":
        return _validate_backfill(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_strategy(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["incremental"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", stream="")

    stream = str(data.get("stream", "")).strip()
    checks.append(_ck(bool(stream), "stream 非空", "strategy.stream"))

    mode = data.get("mode")
    checks.append(_ck(mode in th["modes"],
                      f"增量模式={mode!r} 在白名单 {th['modes']}",
                      "strategy.mode"))

    partition = data.get("partition")
    checks.append(_ck(partition in th["partitions"],
                      f"分区={partition!r} 在白名单 {th['partitions']}",
                      "strategy.partition"))

    # 增量/cdc 必须声明水位字段（定位增量起点）
    if mode in ("incremental", "cdc"):
        checks.append(_ck(bool(str(data.get("watermark_field", "")).strip()),
                          f"{mode} 声明 watermark_field", "strategy.watermark"))
        checks.append(_ck(bool(str(data.get("idempotency_key", "")).strip()),
                          f"{mode} 声明 idempotency_key（重跑幂等）",
                          "strategy.idempotency"))
    else:
        checks.append(_ck(True, f"{mode} 不要求水位", "strategy.watermark"))
        checks.append(_ck(True, f"{mode} 不要求幂等键", "strategy.idempotency"))

    # 迟到容忍窗口非负
    late = c._num(data.get("late_arrival_days"))
    checks.append(_ck(late >= 0, f"迟到容忍 {late:g} 天 ≥ 0", "strategy.late"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        stream=stream, mode=mode,
        narrative=f"增量策略 {stream}：{mode} / 分区 {partition}")


# --------------------------------------------------------------------------- #
def _validate_backfill(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", operation="")

    op = data.get("operation") or "backfill"
    checks.append(_ck(op == "backfill", f"操作={op!r} 为回填", "backfill.operation"))

    # 回填区间起止非空且顺序正确
    start = str(data.get("start", "")).strip()
    end = str(data.get("end", "")).strip()
    checks.append(_ck(bool(start) and bool(end), "回填区间起止非空", "backfill.range"))
    checks.append(_ck(bool(start) and bool(end) and start <= end,
                      f"区间顺序 {start or '?'} ≤ {end or '?'}", "backfill.order"))

    # 回填必须声明幂等键（重跑不重复）
    checks.append(_ck(bool(str(data.get("idempotency_key", "")).strip()),
                      "回填声明 idempotency_key", "backfill.idempotency"))

    # 高风险动作必须声明授权（红线 2：回填须人工审批）
    auth = data.get("authorized")
    checks.append(_ck(auth is True,
                      f"回填已授权（authorized={auth!r}）", "backfill.authorized"))
    checks.append(_ck(bool(str(data.get("approver", "")).strip()),
                      "声明审批人", "backfill.approver"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        operation=op, authorized=auth is True,
        narrative=f"回填方案 {start}~{end}（授权={auth is True}）")

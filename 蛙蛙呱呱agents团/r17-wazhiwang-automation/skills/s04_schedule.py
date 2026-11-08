# -*- coding: utf-8 -*-
"""S04 定时与批处理 —— 能力域 4。

整合自 n8n-io__n8n 的 workflow-builder / one-off-operations skills：
  - 调度工作流（cron/interval + timezone + 日报读回历史行）
  - 批处理记录（batch_id/status + 失败批必须有补偿/人工恢复路径）

关键立场：**日报/提醒类必须读回历史行，不能在单次 run 的内存里编摘要**（n8n
教训：跨 run 状态要靠 Data Table，不能靠上一次执行残留）。本门禁只做确定性
结构校验：调度类型 + 周期参数 + 时区 + 批处理状态 + 失败补偿。

动作：
  schedule  调度工作流校验
  batch     批处理与补偿记录校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "schedule"
DESC = "定时与批处理：schedule/batch"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("schedule", help="校验调度工作流（cron/interval/timezone）")
    a.add_argument("--input", required=True)
    b = act.add_parser("batch", help="校验批处理与补偿记录")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "schedule":
        return _validate_schedule(data)
    if args.action == "batch":
        return _validate_batch(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_schedule(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["schedule"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", schedule_type=None)

    stype = str(data.get("schedule_type", ""))
    checks.append(_ck(stype in th["schedule_types"],
                      f"调度类型={stype!r} 在白名单", "schedule.type"))

    # cron 或 interval 必填其一
    if stype == "cron":
        cron = str(data.get("cron", "")).strip()
        valid = bool(cron) and len(cron.split()) in (5, 6)
        checks.append(_ck(valid, f"cron={cron!r} 合规（5~6 段）", "schedule.cron"))
    elif stype == "interval":
        mins = c._num(data.get("interval_minutes"))
        checks.append(_ck(mins >= th["min_interval_minutes"],
                          f"interval_minutes={mins} ≥ {th['min_interval_minutes']}",
                          "schedule.interval"))
    else:
        # manual：无需周期参数
        checks.append(_ck(True, "manual 调度无需周期参数", "schedule.manual"))

    # timezone 非空
    tz = str(data.get("timezone", "")).strip()
    checks.append(_ck(bool(tz), f"timezone={tz!r} 非空", "schedule.timezone"))

    # 日报/摘要/提醒类必须读回历史行（不能只用当前 run 内存数据）
    kind = str(data.get("kind", ""))
    if kind in th["read_back_required_for"]:
        readback = data.get("read_back") is True
        checks.append(_ck(readback,
                          f"{kind} 类声明读回历史行（read_back=True）",
                          "schedule.read_back"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        schedule_type=stype,
        narrative=f"调度 {stype}（{data.get('kind', '周期任务')}）："
                  f"timezone={tz!r}")


# --------------------------------------------------------------------------- #
def _validate_batch(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["retry"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", batch_count=0)

    batches = data.get("batches")
    if not isinstance(batches, list) or not batches:
        return c.result([_ck(False, "batches 必须是非空列表", "batch.list")],
                        ok=False, verdict="FAIL", batch_count=0)

    checks.append(_ck(True, f"批次 {len(batches)} 个", "batch.count"))

    # batch_id 非空唯一；item_count ≥ 0
    ids: List[str] = []
    bad_id: List[str] = []
    bad_count: List[str] = []
    for b in batches:
        if not isinstance(b, dict):
            bad_id.append("(非对象)")
            continue
        bid = str(b.get("batch_id", ""))
        if not bid:
            bad_id.append("(缺 id)")
        else:
            ids.append(bid)
        if c._num(b.get("item_count")) < 0:
            bad_count.append(bid or "?")
    dup = sorted({x for x in ids if ids.count(x) > 1})
    checks.append(_ck(not bad_id and not dup,
                      f"batch_id 非空唯一（异常 {sorted(set(bad_id)) or '无'} / "
                      f"重复 {dup or '无'}）", "batch.id"))
    checks.append(_ck(not bad_count,
                      f"item_count ≥ 0（异常 {bad_count or '无'}）", "batch.item_count"))

    # status 白名单
    bad_status = [str(b.get("batch_id", "?")) for b in batches
                  if isinstance(b, dict) and str(b.get("status", "")) not in th["statuses"]]
    checks.append(_ck(not bad_status,
                      f"status 白名单（异常 {bad_status or '无'}）", "batch.status"))

    # 失败批必须有补偿声明或人工恢复路径
    failed = [b for b in batches if isinstance(b, dict)
              and str(b.get("status")) in ("failed", "partial", "dead_letter")]
    compensation = data.get("compensation")
    handoff = bool(data.get("handoff"))
    for b in failed:
        has_path = bool(compensation) or handoff
        checks.append(_ck(has_path,
                          f"失败批 {b.get('batch_id')} 有补偿/人工恢复路径",
                          "batch.compensation"))
    if not failed:
        checks.append(_ck(True, "无失败批，无需补偿路径", "batch.compensation"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        batch_count=len(batches), failed_count=len(failed),
        narrative=f"批处理 {len(batches)} 个，失败 {len(failed)} 个")

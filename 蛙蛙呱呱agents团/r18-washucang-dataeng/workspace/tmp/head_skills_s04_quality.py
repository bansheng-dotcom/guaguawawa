# -*- coding: utf-8 -*-
"""S04 数据质量门禁 —— 能力域 4。

整合自 dbt-labs__dbt 通用测试语义 + apache__airflow 数据质量检查点：
在关键节点检查**完整性（not_null）、唯一性（unique）、有效性
（accepted_values/range）、新鲜度（freshness）**四类。把四类检查转成确定性
实算：空值率、重复率、枚举越界数、数据年龄（小时）。

关键立场：**质量门禁是「阻断器」，不是「报告器」**。一条检查不通过，下游所有
消费方都不该拿到这批数据——`ok=false` 即阻断。本角色只判「数据能不能进分析环境」，
**不判「数字说明什么」**（那是 R06 的活，红线 3 的边界）。

动作：
  check   质量检查（完整性/唯一性/有效性/新鲜度四类）
  fresh   R18 新鲜度口径校验（计算数据年龄 → 阈值判读）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "quality"
DESC = "数据质量门禁：check/fresh"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("check", "质量检查"), ("fresh", "新鲜度口径校验")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "check":
        return _validate_check(data)
    if args.action == "fresh":
        return _validate_fresh(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_check(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["quality"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", table="", check_count=0)

    table = str(data.get("table", "")).strip()
    checks.append(_ck(bool(table), "表名非空", "quality.table"))

    row_count = c._num(data.get("row_count"))
    checks.append(_ck(row_count > 0, f"行数 {row_count:g} > 0", "quality.row_count"))

    # 完整性：空值率 ≤ 阈值
    null_ratio = c._num(data.get("null_ratio"))
    max_null = c._num(th["default_max_null_ratio"])
    checks.append(_ck(null_ratio <= max_null,
                      f"空值率 {null_ratio:g} ≤ {max_null:g}",
                      "quality.null_ratio"))

    # 唯一性：重复率 ≤ 阈值
    dup_ratio = c._num(data.get("dup_ratio"))
    max_dup = c._num(th["default_max_dup_ratio"])
    checks.append(_ck(dup_ratio <= max_dup,
                      f"重复率 {dup_ratio:g} ≤ {max_dup:g}",
                      "quality.dup_ratio"))

    # 有效性：枚举越界数 = 0
    invalid = c._num(data.get("invalid_count"))
    checks.append(_ck(invalid == 0, f"无效值 {invalid:g} = 0", "quality.invalid"))

    # 具体检查条目：每条须 pass 且带实测值
    items = data.get("checks") or []
    bad_items = [i.get("name") for i in (items if isinstance(items, list) else [])
                 if isinstance(i, dict)
                 and (i.get("passed") is not True or "value" not in i)]
    checks.append(_ck(not bad_items,
                      f"检查条目全通过且带实测值（未过 {bad_items or '无'}）",
                      "quality.items"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        table=table, check_count=len(items) if isinstance(items, list) else 0,
        row_count=int(row_count),
        narrative=f"质量门禁 {table}：{len(items) if isinstance(items, list) else 0} 项检查")


# --------------------------------------------------------------------------- #
def _validate_fresh(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["quality"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", table="")

    table = str(data.get("table", "")).strip()
    checks.append(_ck(bool(table), "表名非空", "fresh.table"))

    age = c._num(data.get("age_hours"))
    max_age = c._num(th["default_max_age_hours"])
    # 与 dbt freshness 口径一致：age > error_after 即过期（含边界）
    checks.append(_ck(0 <= age <= max_age,
                      f"数据年龄 {age:g}h ≤ {max_age:g}h", "fresh.age"))

    # 声明 loaded_at 与 snapshotted_at 口径（回溯需要）
    checks.append(_ck(bool(str(data.get("loaded_at", "")).strip()),
                      "声明 loaded_at 字段", "fresh.loaded_at"))
    checks.append(_ck(bool(str(data.get("snapshotted_at", "")).strip()),
                      "声明 snapshotted_at 时点", "fresh.snapshotted_at"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        table=table, age_hours=age, max_age_hours=max_age,
        narrative=f"新鲜度 {table}：{age:g}h / 上限 {max_age:g}h")

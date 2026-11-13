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


def _rows_from(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """取真实行集：只要给了 rows/records/sample_rows/data 就不信自报数字。"""
    for key in ("rows", "records", "sample_rows", "data"):
        value = data.get(key)
        if isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
            return value
    return []


# --------------------------------------------------------------------------- #
def _validate_check(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["quality"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", table="", check_count=0)

    table = str(data.get("table", "")).strip()
    checks.append(_ck(bool(table), "表名非空", "quality.table"))

    # L01 主链路接入：有真实行集时，由嵌入式 SQL 引擎重算，禁止信自报数字。
    rows = _rows_from(data)
    measured_by = None
    measured = None
    if rows:
        try:
            from engines import DataEngRuntimeEngine
            engine = DataEngRuntimeEngine()
            prof = engine.profile_table(rows, table=table or "t")
            measured_by = f"runtime_engine({prof['engine']})"
            row_count = float(prof["row_count"])
            null_ratio = max(prof["null_ratio"].values()) if prof["null_ratio"] else 0.0
            dup_ratio = float(prof["dup_ratio"])
            measured = {
                "row_count": int(prof["row_count"]),
                "max_null_ratio": round(null_ratio, 6),
                "dup_ratio": round(dup_ratio, 6),
                "engine": prof["engine"],
            }
            checks.append(_ck(True, f"实测口径 {measured_by}",
                              "quality.measured_by"))
            for key, actual, tol in (("row_count", row_count, 0.0),
                                     ("null_ratio", null_ratio, 0.001),
                                     ("dup_ratio", dup_ratio, 0.001)):
                if key in data and abs(c._num(data.get(key)) - actual) > tol:
                    checks.append(_ck(
                        False,
                        f"自报 {key}={c._num(data.get(key)):g} 与实测 {actual:g} 不符（fail-open 拦截）",
                        "quality.tamper"))
        except Exception as exc:  # noqa: BLE001 - 测量层坏了必须 fail-closed
            checks.append(_ck(False, f"真实测量引擎不可用：{exc}", "quality.measured_by"))
            row_count, null_ratio, dup_ratio = 0.0, 1.0, 1.0
    else:
        row_count = c._num(data.get("row_count"))
        null_ratio = c._num(data.get("null_ratio"))
        dup_ratio = c._num(data.get("dup_ratio"))

    checks.append(_ck(row_count > 0, f"行数 {row_count:g} > 0", "quality.row_count"))

    # 完整性：空值率 ≤ 阈值
    max_null = c._num(th["default_max_null_ratio"])
    checks.append(_ck(null_ratio <= max_null,
                      f"空值率 {null_ratio:g} ≤ {max_null:g}",
                      "quality.null_ratio"))

    # 唯一性：重复率 ≤ 阈值
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
        row_count=int(row_count), measured_by=measured_by, measured=measured,
        narrative=(f"质量门禁 {table}：{len(items) if isinstance(items, list) else 0} 项检查"
                   + (f"（{measured_by} 实测）" if measured_by else "（自报口径）")))


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

# -*- coding: utf-8 -*-
"""S03 字段与身份映射 —— 能力域 3。

整合自 n8n-io__n8n 的 data-table-manager skills：
  - 字段映射表（source_field → target_field + target_type，snake_case 主键引用）
  - Data Table schema（列命名 snake_case + 类型白名单 + 拒收系统保留名）

关键立场：**明确不同系统的数据字段、主键、枚举和负责人，但不替业务角色发明
字段语义**。本门禁只做确定性结构校验：字段名合规 + 类型白名单 + 主键引用完整
+ 拒收系统保留名。

动作：
  mapping  字段映射表与主键规则校验
  table    Data Table 列结构校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "mapping"
DESC = "字段与身份映射：mapping/table"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("mapping", help="校验字段映射表与主键规则")
    a.add_argument("--input", required=True)
    b = act.add_parser("table", help="校验 Data Table 列结构（snake_case/类型/保留名）")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "mapping":
        return _validate_mapping(data)
    if args.action == "table":
        return _validate_table(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_mapping(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["mapping"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", mapping_count=0)

    mappings = data.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        return c.result([_ck(False, "mappings 必须是非空列表", "mapping.list")],
                        ok=False, verdict="FAIL", mapping_count=0)

    checks.append(_ck(True, f"映射 {len(mappings)} 条", "mapping.count"))

    # source/target 非空 + target snake_case + target_type 白名单
    bad_field: List[str] = []
    bad_type: List[str] = []
    for m in mappings:
        if not isinstance(m, dict):
            bad_field.append("(非对象)")
            continue
        src = m.get("source_field")
        tgt = m.get("target_field")
        if not src or not tgt:
            bad_field.append(str(src or tgt or "?"))
            continue
        if not c.is_snake_case(tgt, th["column_pattern"]):
            bad_field.append(str(tgt))
        if m.get("target_type") not in th["column_types"]:
            bad_type.append(str(tgt))
    checks.append(_ck(not bad_field,
                      f"字段名合规 snake_case（异常 {sorted(set(bad_field)) or '无'}）",
                      "mapping.field"))
    checks.append(_ck(not bad_type,
                      f"target_type 白名单（异常 {sorted(set(bad_type)) or '无'}）",
                      "mapping.type"))

    # 无重复 target（去重）
    targets = [str(m.get("target_field")) for m in mappings
               if isinstance(m, dict) and m.get("target_field")]
    dup = sorted({x for x in targets if targets.count(x) > 1})
    checks.append(_ck(not dup, f"target 去重（重复 {dup or '无'}）", "mapping.unique"))

    # 主键规则：主键必须指向真实字段，且不占系统保留名
    pk = data.get("primary_key")
    if pk is not None:
        pk_field = str(pk.get("key_field", "")) if isinstance(pk, dict) else str(pk)
        in_targets = pk_field in targets
        reserved = pk_field in th["reserved_columns"]
        checks.append(_ck(bool(pk_field) and in_targets and not reserved,
                          f"主键 {pk_field!r} 指向真实字段且非保留名",
                          "mapping.primary_key"))
    else:
        checks.append(_ck(False, "必须声明 primary_key 主键规则", "mapping.primary_key"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        mapping_count=len(mappings),
        primary_key=pk_field if pk is not None else None,
        narrative=f"字段映射 {len(mappings)} 条，主键 {pk_field if pk is not None else '?'}")


# --------------------------------------------------------------------------- #
def _validate_table(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["mapping"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", column_count=0)

    table_name = str(data.get("table_name", "")).strip()
    checks.append(_ck(bool(table_name), f"table_name 非空", "table.name"))

    columns = data.get("columns")
    if not isinstance(columns, list) or not columns:
        return c.result([_ck(False, "columns 必须是非空列表", "table.columns")],
                        ok=False, verdict="FAIL", column_count=0, table_name=table_name)

    checks.append(_ck(True, f"列 {len(columns)} 个", "table.count"))

    # snake_case + 类型白名单 + 无系统保留名 + 列名唯一
    bad_name: List[str] = []
    bad_type: List[str] = []
    reserved: List[str] = []
    for col in columns:
        if not isinstance(col, dict):
            bad_name.append("(非对象)")
            continue
        nm = str(col.get("name", ""))
        if not c.is_snake_case(nm, th["column_pattern"]):
            bad_name.append(nm)
        if col.get("type") not in th["column_types"]:
            bad_type.append(nm)
        if nm in th["reserved_columns"]:
            reserved.append(nm)
    checks.append(_ck(not bad_name,
                      f"列名 snake_case（异常 {sorted(set(bad_name)) or '无'}）",
                      "table.name_valid"))
    checks.append(_ck(not bad_type,
                      f"列类型白名单（异常 {sorted(set(bad_type)) or '无'}）",
                      "table.type"))
    checks.append(_ck(not reserved,
                      f"无系统保留名列（命中 {sorted(set(reserved)) or '无'}）",
                      "table.reserved"))

    names = [str(x.get("name")) for x in columns if isinstance(x, dict)]
    dup = sorted({x for x in names if names.count(x) > 1})
    checks.append(_ck(not dup, f"列名唯一（重复 {dup or '无'}）", "table.unique"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        column_count=len(columns), table_name=table_name,
        narrative=f"Data Table {table_name}：{len(columns)} 列")

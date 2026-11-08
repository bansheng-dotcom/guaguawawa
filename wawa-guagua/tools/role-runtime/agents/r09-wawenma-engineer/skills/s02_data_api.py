# -*- coding: utf-8 -*-
"""s02 数据库与 API（data_api）：schema / api 两动作。

- schema：数据库 Schema——表、列类型白名单、主键、索引引用。
- api：API 契约——method/version 枚举、错误码、路径唯一。
阈值：thresholds.json → data_api.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "data_api"
DESC = "数据库与 API：Schema 设计、索引、API 契约与错误码"

ACTIONS = {
    "schema": "数据库 Schema 校验",
    "api": "API 契约校验",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# schema
# --------------------------------------------------------------------------- #
def schema(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["data_api"]
    column_types = th["column_types"]

    tables = data.get("tables") or []
    checks: List[Dict[str, Any]] = []

    if not tables:
        checks.append(c.ck(False, "tables 为空，无 Schema 可校验", "data_api:tables", "CRITICAL"))

    for i, t in enumerate(tables):
        tname = str(t.get("name") or "")
        columns = t.get("columns") or []
        col_names = {str(col.get("name") or "") for col in columns}
        pk = str(t.get("primary_key") or "")
        if not tname:
            checks.append(c.ck(False, f"tables[{i}] 缺 name", "data_api:table_name", "HIGH", **{"index": i}))
        if not columns:
            checks.append(c.ck(False, f"表 {tname!r} 无列", "data_api:columns", "HIGH", **{"table": tname}))
        for j, col in enumerate(columns):
            cname = str(col.get("name") or "")
            ctype = str(col.get("type") or "")
            if ctype not in column_types:
                checks.append(c.ck(False, f"表 {tname!r} 列 {cname!r} type={ctype!r} 不在白名单", "data_api:column_type", "HIGH", **{"table": tname, "column": cname}))
            else:
                checks.append(c.ck(True, f"列 {tname}.{cname} type={ctype} 合规", "data_api:column_type", **{"table": tname, "column": cname}))
        if pk and pk not in col_names:
            checks.append(c.ck(False, f"表 {tname!r} 主键 {pk!r} 不是已有列", "data_api:primary_key", "HIGH", **{"table": tname, "primary_key": pk}))
        elif pk:
            checks.append(c.ck(True, f"表 {tname!r} 主键 {pk} 有效", "data_api:primary_key", **{"table": tname}))
        for idx in (t.get("indexes") or []):
            idx_name = str(idx.get("name") or "")
            cols = [str(x) for x in (idx.get("columns") or [])]
            bad = [x for x in cols if x not in col_names]
            if bad:
                checks.append(c.ck(False, f"索引 {idx_name!r} 引用不存在的列 {bad}", "data_api:index", "HIGH", **{"table": tname, "index": idx_name}))
            else:
                checks.append(c.ck(True, f"索引 {idx_name!r} 列有效", "data_api:index", **{"table": tname, "index": idx_name}))

    column_count = sum(len(t.get("columns") or []) for t in tables)
    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   table_count=len(tables),
                   column_count=column_count,
                   verdict=verdict,
                   next="数据库 Schema 合规" if ok else "修复列类型/主键/索引引用后重新 schema",
                   )
    return out


# --------------------------------------------------------------------------- #
# api
# --------------------------------------------------------------------------- #
def api(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["data_api"]
    http_methods = th["http_methods"]

    endpoints = data.get("endpoints") or []
    checks: List[Dict[str, Any]] = []

    if not endpoints:
        checks.append(c.ck(False, "endpoints 为空，无 API 契约可校验", "data_api:endpoints", "CRITICAL"))

    seen_keys: set = set()
    error_codes_total = 0
    for i, ep in enumerate(endpoints):
        method = str(ep.get("method") or "").upper()
        path = str(ep.get("path") or "")
        error_codes = ep.get("error_codes") or []
        if method not in http_methods:
            checks.append(c.ck(False, f"endpoints[{i}] method={method!r} 不在白名单 {http_methods}", "data_api:method", "HIGH", **{"index": i}))
        else:
            checks.append(c.ck(True, f"{method} {path} method 合规", "data_api:method", **{"method": method, "path": path}))
        if not path or not path.startswith("/"):
            checks.append(c.ck(False, f"endpoints[{i}] path={path!r} 非 / 开头", "data_api:path", "HIGH", **{"index": i}))
        elif (method, path) in seen_keys:
            checks.append(c.ck(False, f"method+path 重复：{method} {path!r}", "data_api:path_dup", "HIGH", **{"path": path, "method": method}))
        else:
            seen_keys.add((method, path))
            checks.append(c.ck(True, f"path {path!r} 唯一", "data_api:path", **{"path": path}))
        if not error_codes:
            checks.append(c.ck(False, f"{method} {path} 未声明错误码", "data_api:error_codes", "HIGH", **{"path": path}))
        else:
            error_codes_total += len(error_codes)
            checks.append(c.ck(True, f"{method} {path} 错误码 {len(error_codes)} 个", "data_api:error_codes", **{"path": path}))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   endpoint_count=len(endpoints),
                   error_codes_total=error_codes_total,
                   verdict=verdict,
                   next="API 契约合规" if ok else "修复 method/path/错误码后重新 api",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "schema":
        result = schema(data)
    elif args.action == "api":
        result = api(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result

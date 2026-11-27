# -*- coding: utf-8 -*-
"""第 2 段 API：数据模型 → JSON Schema + OpenAPI 3.1 + RFC 7807 错误码 + 迁移。

契约必须先可校验，再谈实现：Schema 引用不悬空、错误响应统一 problem+json、
迁移默认可回滚。不可逆迁移只有在显式审批且有备份计划时才放行。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import (ck, gate, md_table, nonempty_list, nonempty_str,
                     render_stage)

_TYPES = {"string": "string", "integer": "integer", "number": "number",
          "boolean": "boolean", "object": "object", "array": "array"}


def _entity_schema(entity: Dict[str, Any]) -> Dict[str, Any]:
    props, required = {}, []
    for f in entity.get("fields") or []:
        name = f.get("name", "")
        if not name:
            continue
        props[name] = {"type": _TYPES.get(f.get("type", "string"), "string")}
        if f.get("required"):
            required.append(name)
    return {"type": "object", "title": entity.get("name", ""),
            "properties": props, "required": required,
            "additionalProperties": False}


def _build_schemas(entities: List[Dict[str, Any]],
                   endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
    schemas: Dict[str, Any] = {e.get("name"): _entity_schema(e) for e in entities}
    by_name = {e.get("name"): e for e in entities}
    for ep in endpoints:
        for key in ("request", "response"):
            ref = ep.get(key)
            if not ref or ref in schemas:
                continue
            if key == "request" and ref.startswith("Create") and ref[6:] in by_name:
                base = by_name[ref[6:]]
                schemas[ref] = _entity_schema({
                    "name": ref,
                    "fields": [f for f in base.get("fields") or []
                               if f.get("name") not in ("id", "created_at")],
                })
            elif key == "response" and ref.endswith("List") and ref[:-4] in by_name:
                schemas[ref] = {"type": "array", "title": ref,
                                "items": {"$ref": f"#/components/schemas/{ref[:-4]}"}}
            else:
                schemas[ref] = {"type": "object", "title": ref,
                                "properties": {}, "additionalProperties": False}
    schemas["Problem"] = {
        "type": "object", "title": "Problem",
        "required": ["type", "title", "status", "detail"],
        "properties": {"type": {"type": "string"}, "title": {"type": "string"},
                       "status": {"type": "integer"}, "detail": {"type": "string"},
                       "code": {"type": "string"}},
        "additionalProperties": False,
    }
    return schemas


def _success_status(method: str) -> int:
    m = method.upper()
    return 201 if m == "POST" else (204 if m == "DELETE" else 200)


def _build_openapi(brief: Dict[str, Any], schemas: Dict[str, Any],
                   error_codes: List[Dict[str, Any]]) -> Dict[str, Any]:
    base = (brief.get("api") or {}).get("base_path", "/api")
    paths: Dict[str, Any] = {}
    by_code = {e.get("code"): e for e in error_codes}
    for ep in (brief.get("api") or {}).get("endpoints") or []:
        method = ep.get("method", "GET").lower()
        status = _success_status(method)
        op: Dict[str, Any] = {"summary": ep.get("summary", ""),
                              "responses": {}}
        if status == 204:
            op["responses"]["204"] = {"description": "无内容"}
        else:
            ref = ep.get("response")
            body = ({"$ref": f"#/components/schemas/{ref}"} if ref
                    else {"type": "object"})
            op["responses"][str(status)] = {
                "description": "成功",
                "content": {"application/json": {"schema": body}},
            }
        if method in ("post", "put", "patch") and ep.get("request"):
            op["requestBody"] = {
                "required": True,
                "content": {"application/json": {
                    "schema": {"$ref": f"#/components/schemas/{ep['request']}"}}},
            }
        for code_name in ep.get("errors") or []:
            meta = by_code.get(code_name) or {}
            code_status = str(meta.get("status", 400))
            op["responses"][code_status] = {
                "description": meta.get("title", code_name),
                "content": {"application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/Problem"}}},
            }
        paths.setdefault(f"{base}{ep.get('path', '')}", {})[method] = op
    return {
        "openapi": "3.1.0",
        "info": {"title": f"{brief.get('project', 'app')} API",
                 "version": (brief.get("release") or {}).get("publish", {}).get("version", "0.0.0")},
        "paths": paths,
        "components": {"schemas": schemas},
    }


def build(brief: Dict[str, Any]) -> Dict[str, Any]:
    api = brief.get("api") or {}
    entities = (brief.get("data_model") or {}).get("entities") or []
    endpoints = api.get("endpoints") or []
    error_codes = [{"code": e.get("code", ""), "title": e.get("title", ""),
                    "status": e.get("status", 400)} for e in api.get("error_codes") or []]
    schemas = _build_schemas(entities, endpoints)
    migration = api.get("migration") or {}
    art: Dict[str, Any] = {
        "artifact": "api",
        "stage": "api",
        "project": brief.get("project", ""),
        "schemas": schemas,
        "openapi": _build_openapi(brief, schemas, error_codes),
        "error_codes": error_codes,
        "endpoints": endpoints,
        "migration": {
            "strategy": migration.get("strategy", ""),
            "reversible": bool(migration.get("reversible")),
            "approved_irreversible": bool(migration.get("approved_irreversible")),
            "steps": migration.get("steps") or [],
            "rollback": migration.get("rollback") or [],
            "backup_plan": migration.get("backup_plan", ""),
        },
    }
    art["gate"] = check(art)
    return art


def check(art: Dict[str, Any]) -> Dict[str, Any]:
    """契约门禁：Schema、OpenAPI 3.1、RFC 7807、迁移可回滚、引用不悬空。"""
    schemas = art.get("schemas") or {}
    spec = art.get("openapi") or {}
    codes = art.get("error_codes") or []
    endpoints = art.get("endpoints") or []
    mig = art.get("migration") or {}
    code_names = [c.get("code") for c in codes]

    schema_ok = bool(schemas) and all(
        isinstance(s, dict) and s.get("type") for s in schemas.values())
    paths = spec.get("paths") or {}
    method_count = sum(len(v) for v in paths.values() if isinstance(v, dict))
    openapi_ok = (str(spec.get("openapi", "")).startswith("3.1") and
                  method_count >= 3 and
                  all("responses" in op for ops in paths.values()
                      for op in ops.values() if isinstance(op, dict)))
    problem_ok = bool(schemas.get("Problem")) and bool(codes) and \
        len(code_names) == len(set(code_names)) and \
        all(400 <= int(c.get("status", 0)) < 600 for c in codes)
    if problem_ok:
        for ep in endpoints:
            problem_ok = problem_ok and set(ep.get("errors") or []) <= set(code_names)
        for ops in paths.values():
            for op in ops.values():
                for st, resp in (op.get("responses") or {}).items():
                    if 400 <= int(st) < 600:
                        problem_ok = problem_ok and \
                            "application/problem+json" in (resp.get("content") or {})
    refs_ok = True
    for ep in endpoints:
        for key in ("request", "response"):
            ref = ep.get(key)
            if ref and ref not in schemas:
                refs_ok = False
    reversible_ok = (mig.get("reversible") and len(mig.get("rollback") or []) >= 2
                     and len(mig.get("steps") or []) >= 2)
    if not mig.get("reversible"):
        reversible_ok = bool(mig.get("approved_irreversible")) and \
            nonempty_str(mig.get("backup_plan"))

    checks = [
        ck(schema_ok, "数据模型已转成可校验 JSON Schema", "api:schemas", "CRITICAL"),
        ck(openapi_ok, "OpenAPI 3.1 片段含 ≥3 个操作与响应", "api:openapi31", "CRITICAL"),
        ck(problem_ok, "4xx/5xx 统一 RFC 7807 problem+json", "api:rfc7807", "CRITICAL"),
        ck(reversible_ok, "迁移默认可回滚；不可逆须审批+备份计划",
           "api:migration_reversible", "CRITICAL"),
        ck(refs_ok, "请求/响应 Schema 引用不悬空", "api:contract_refs", "CRITICAL"),
    ]
    return gate(checks, "api")


def render(art: Dict[str, Any]) -> str:
    code_rows = [[c.get("status"), c.get("code"), c.get("title")]
                 for c in art.get("error_codes") or []]
    ep_rows = [[e.get("method"), e.get("path"), e.get("summary"),
                ", ".join(e.get("errors") or [])]
               for e in art.get("endpoints") or []]
    mig = art.get("migration") or {}
    summary = (f"已生成 {len(art.get('schemas') or {})} 个 Schema、"
               f"{sum(len(v) for v in (art.get('openapi') or {}).get('paths', {}).values())} 个操作；"
               f"错误码 {len(art.get('error_codes') or [])} 个（RFC 7807）。")
    tables = [
        "## 接口清单", "", md_table(["方法", "路径", "说明", "错误码"], ep_rows),
        "", "## 错误码", "", md_table(["HTTP", "code", "标题"], code_rows),
        "", "## 迁移", "",
        f"- 策略：{mig.get('strategy', '')}；可回滚：{mig.get('reversible')}",
        f"- 步骤：{'；'.join(mig.get('steps') or [])}",
        f"- 回滚：{'；'.join(mig.get('rollback') or [])}",
    ]
    return render_stage(art, summary, tables)

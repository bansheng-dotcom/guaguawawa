# -*- coding: utf-8 -*-
"""R09 八个技能模块的共享基础：JSON 读写、轻量 JSON Schema 校验、结果输出。

约束：纯标准库。技能之间不互相 import，只依赖 _common；阈值统一走
experience/thresholds.json（T9 阈值外置，改口径不改代码）。
与 r01/r02/r03/r04/r05/r06/r07/r08 保持同一套 _common 契约。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


def emit(data: Dict[str, Any]) -> None:
    """以单行 JSON 输出结果，供编排器以子进程方式消费。"""
    print("__AGENT_RESULT__ " + json.dumps(data, ensure_ascii=False))


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def load_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_json(path: str, data: Any) -> None:
    _makedirs(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_text(path: str, text: str) -> None:
    _makedirs(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _makedirs(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)


# --------------------------------------------------------------------------- #
# 路径解析：清单/manifest 里的相对路径按「原样 → 输入文件目录 → agent 目录」
# 顺序找第一个存在的位置（确定性，不依赖 CWD）。
# --------------------------------------------------------------------------- #
_AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def agent_dir() -> str:
    return _AGENT_DIR


def resolve_path(path: str, base_dir: Optional[str] = None) -> Optional[str]:
    """返回第一个存在的绝对路径；都不存在返回 None。"""
    if not path:
        return None
    candidates = [path]
    if not os.path.isabs(path):
        if base_dir:
            candidates.append(os.path.join(base_dir, path))
        candidates.append(os.path.join(_AGENT_DIR, path))
    for p in candidates:
        if os.path.isfile(p):
            return os.path.abspath(p)
    return None


# --------------------------------------------------------------------------- #
# 轻量 JSON Schema 校验器（子集，支撑 contracts.py 的确定性契约）。
# --------------------------------------------------------------------------- #
def _typename(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__


def validate_schema(instance: Any, schema: Any, path: str = "$") -> List[str]:
    errs: List[str] = []
    if not isinstance(schema, dict):
        return errs
    if "enum" in schema and instance not in schema["enum"]:
        return [f"{path}: 值 {instance!r} 不在枚举 {schema['enum']}"]
    t = schema.get("type")
    if t == "object":
        if not isinstance(instance, dict):
            return [f"{path}: 应为 object，实际 {_typename(instance)}"]
        for k in schema.get("required", []):
            if k not in instance:
                errs.append(f"{path}.{k}: 缺必填字段")
        props = schema.get("properties") or {}
        for k, sub in props.items():
            if k in instance:
                errs.extend(validate_schema(instance[k], sub, f"{path}.{k}"))
        if schema.get("additionalProperties") is False:
            for k in set(instance) - set(props):
                errs.append(f"{path}.{k}: 未声明字段")
        return errs
    if t == "array":
        if not isinstance(instance, list):
            return [f"{path}: 应为 array，实际 {_typename(instance)}"]
        it = schema.get("items")
        if isinstance(it, dict):
            for i, x in enumerate(instance):
                errs.extend(validate_schema(x, it, f"{path}[{i}]"))
        return errs
    if t == "string":
        if not isinstance(instance, str):
            return [f"{path}: 应为 string，实际 {_typename(instance)}"]
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errs.append(f"{path}: 长度 {len(instance)} < minLength {schema['minLength']}")
        return errs
    if t == "number":
        if isinstance(instance, bool) or not isinstance(instance, (int, float)):
            return [f"{path}: 应为 number，实际 {_typename(instance)}"]
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append(f"{path}: {instance} > maximum {schema['maximum']}")
        return errs
    if t == "integer":
        if isinstance(instance, bool) or not isinstance(instance, int):
            return [f"{path}: 应为 integer，实际 {_typename(instance)}"]
        return errs
    if t == "boolean":
        if not isinstance(instance, bool):
            return [f"{path}: 应为 boolean，实际 {_typename(instance)}"]
        return errs
    if t == "null":
        if instance is not None:
            return [f"{path}: 应为 null，实际 {_typename(instance)}"]
        return errs
    return errs


# --------------------------------------------------------------------------- #
# 通用检查辅助：统一 {ok, msg, dim, sev} 结构（对齐 r01/r02/r03/r04 样板）。
# --------------------------------------------------------------------------- #
def ck(ok: bool, msg: str, dim: str, sev: str = "OK", **ev) -> Dict[str, Any]:
    d: Dict[str, Any] = {"ok": bool(ok), "msg": msg, "dim": dim, "sev": sev}
    d.update(ev)
    return d


def result(checks: List[Dict[str, Any]], **fields) -> Dict[str, Any]:
    """所有检查通过才 ok；CRITICAL/HIGH 失败给 FAIL 语义。"""
    ok = all(x.get("ok", False) for x in checks)
    out: Dict[str, Any] = {"ok": ok, "checks": checks}
    out.update(fields)
    return out


# --------------------------------------------------------------------------- #
# 全局阈值（T9）：优先 experience/thresholds.json > 内置默认。
# --------------------------------------------------------------------------- #
_DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "spec": {
        "topology_types": ["monolith", "modular_monolith", "microservices",
                           "serverless"],
        "module_required": ["name", "inputs", "outputs"],
        "min_modules": 1,
        "verdict_enum": ["PASS", "FAIL"],
    },
    "data_api": {
        "column_types": ["string", "integer", "float", "boolean", "datetime",
                         "text", "json", "uuid", "enum", "bigint"],
        "http_methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
        "api_versions": ["v1", "v2", "v3"],
        "verdict_enum": ["PASS", "FAIL"],
    },
    "fullstack": {
        "auth_methods": ["session", "jwt", "oauth", "passwordless", "api-key",
                         "none"],
        "min_components": 1,
        "min_services": 1,
        "verdict_enum": ["PASS", "FAIL"],
    },
    "crossplatform": {
        "platforms": ["android", "ios", "web", "desktop"],
        "state_management": ["provider", "riverpod", "bloc", "getx", "setstate"],
        "build_statuses": ["success", "failed", "skipped"],
        "max_skipped": 0,
        "verdict_enum": ["PASS", "FAIL"],
    },
    "testing": {
        "suite_types": ["unit", "integration", "contract", "e2e"],
        "flow_results": ["passed", "failed", "flaky"],
        "coverage_min": 0.8,
        "max_skipped": 0,
        "verdict_enum": ["PASS", "FAIL"],
    },
    "debug": {
        "min_repro_steps": 1,
        "verdict_enum": ["PASS", "FAIL"],
    },
    "ops": {
        "irreversible_ops": ["drop", "truncate", "delete", "force_push",
                             "migrate_down", "rm_rf", "destroy", "purge",
                             "reset_hard"],
        "cve_severities": ["low", "medium", "high", "critical"],
        "max_leaked_keys": 0,
        "verdict_enum": ["PASS", "FAIL"],
    },
    "special": {
        "mcp_transports": ["stdio", "sse", "http"],
        "verdict_enum": ["PASS", "FAIL"],
    },
    "review": {
        "vague_words": ["待定", "TODO", "TBD", "占位", "随便", "大概", "稍后补充",
                        "后续完善", "以后再写", "占位符", "lorem", "假数据",
                        "硬编码占位"],
        "irreversible_words": ["drop table", "truncate", "删库", "force push",
                               "强制推送", "生产删除", "rm -rf", "不可恢复",
                               "migrate down", "回滚销毁"],
        "scope_terms": ["监控告警", "灾备", "备份恢复", "uptime", "incident",
                        "on-call", "状态页", "容量规划", "SLO", "主备切换"],
        "concrete_keys": ["ok", "checks", "verdict", "file_path", "files",
                          "modules", "services", "tables", "endpoints",
                          "components", "targets", "suites", "flows",
                          "hypotheses", "hotspots", "steps", "dependencies",
                          "scenes", "servers", "test_report", "test_evidence",
                          "artifacts", "schema", "code", "run_command",
                          "build_artifacts", "frontend", "backend",
                          "rollback_plan", "ci_config", "playwright_trace",
                          "project_config", "manifest", "coverage", "root_cause"],
        "conclusion_keys": ["summary", "conclusion", "next", "description",
                            "note", "symptom", "root_cause", "operation",
                            "reason", "title", "text", "statement", "purpose"],
        "evidence_keys": ["modules", "services", "tables", "endpoints",
                          "components", "targets", "suites", "flows",
                          "hypotheses", "hotspots", "steps", "dependencies",
                          "scenes", "servers", "findings", "test_report",
                          "test_evidence", "artifacts", "coverage", "passed",
                          "failed", "skipped", "total", "rollback_plan",
                          "ci_config", "root_cause", "playwright_trace",
                          "module_count", "boundary_ok", "service_count",
                          "topology", "edge_count", "dangling_edges",
                          "table_count", "column_count", "endpoint_count",
                          "error_codes_total", "component_count",
                          "e2e_coverage", "auth_method", "route_count",
                          "protected_count", "target_count",
                          "state_management", "diff_count", "suite_count",
                          "flow_count", "flaky", "symptom", "repro_step_count",
                          "hotspot_count", "regression_count", "step_count",
                          "irreversible_found", "rollback_steps",
                          "dependency_count", "cve_counts", "leaked_key_count",
                          "transport", "tool_count", "scene_count",
                          "script_count"],
        "handoff_keys": ["handoff", "owner"],
        "verdict_enum": ["PASS", "FAIL", "BLOCKED"],
        "coverage_min": 0.8,
    },
}


def thresholds_path() -> str:
    return os.path.join(_AGENT_DIR, "experience", "thresholds.json")


def load_thresholds() -> Dict[str, Any]:
    p = thresholds_path()
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return dict(_DEFAULT_THRESHOLDS)
    return dict(_DEFAULT_THRESHOLDS)


# --------------------------------------------------------------------------- #
# 通用字符串工具（供措辞/证据校验复用）
# --------------------------------------------------------------------------- #
def has_any(text: str, tokens: List[str]) -> bool:
    return any(t in text for t in tokens if t)

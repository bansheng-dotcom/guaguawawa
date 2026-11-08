# -*- coding: utf-8 -*-
"""R02 七个技能模块的共享基础：JSON 读写、轻量 JSON Schema 校验、结果输出。

约束：纯标准库。技能之间不互相 import，只依赖 _common，保持「可组合、可独立
测试」的单元边界；阈值统一走 experience/thresholds.json（T9 阈值外置）。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List


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
# 通用检查辅助：统一 {ok, msg, dim, sev} 结构（对齐 r01 样板）。
# --------------------------------------------------------------------------- #
def ck(ok: bool, msg: str, dim: str, sev: str = "OK", **ev) -> Dict[str, Any]:
    d: Dict[str, Any] = {"ok": bool(ok), "msg": msg, "dim": dim, "sev": sev}
    d.update(ev)
    return d


def result(checks: List[Dict[str, Any]], **fields) -> Dict[str, Any]:
    """所有检查通过才 ok；CRITICAL/HIGH 失败分别给 FAIL/WARN 语义。"""
    ok = all(x.get("ok", False) for x in checks)
    out: Dict[str, Any] = {"ok": ok, "checks": checks}
    out.update(fields)
    return out


# --------------------------------------------------------------------------- #
# 全局阈值（T9）：优先 experience/thresholds.json > 内置默认。
# --------------------------------------------------------------------------- #
_DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "schedule": {
        "task_kinds": ["analysis", "design", "implementation", "testing",
                       "deployment", "documentation", "management",
                       "maintenance"],
        "step_min": 1, "step_max": 10,
        "cost_min": 0.05, "cost_max": 3.0, "max_items": 20,
        "default_cadence": "daily", "capacity_per_day_default": 2.0,
        "cadences": ["daily", "weekly", "monthly"],
    },
    "capacity": {
        "urgent_weight": 1.2, "overalloc_pct": 100,
        "single_project_cap_pct": 50,
        "lead_time_pcts": {"development": 60, "launch": 15,
                           "maintenance": 10, "innovation": 15},
    },
    "delegate": {
        "max_task_hours": 8, "max_blocked_by": 2, "max_must_read": 3,
        "min_key_results": 1,
    },
    "handoff": {
        "artifact_types": ["document", "code", "data", "config", "report",
                           "dashboard", "design"],
        "required_fields": ["process_doc", "artifact", "owner", "rev",
                           "handoff_to"],
        "min_repro": 1, "min_downstream": 1, "min_acceptance": 1,
        "event_types": ["created", "updated", "handoff", "accepted",
                        "rejected", "reopened", "closed"],
    },
    "retro": {
        "severity_max": 5, "escalation_severity": 4,
        "escalation_within_min": 30, "closure_window_days": 7,
        "dimensions": ["目标", "计划", "执行", "复盘", "团队"],
    },
    "process": {
        "min_steps": 2, "control_point_min_ratio": 0.3,
        "wait_threshold_days": 3, "overprocess_step_threshold": 10,
        "timebox_min": {"daily": 15, "weekly": 60, "monthly": 120},
        "meeting_questions": ["blockers", "yesterday", "today"],
        "min_action_items": 1,
    },
    "knowledge": {
        "supported_types": ["pdf", "epub", "docx", "txt", "md", "markdown",
                            "rst", "adoc", "html", "htm", "rtf", "mobi",
                            "azw3"],
        "slug_min_segments": 2, "min_sections": 3,
        "required_sections": ["Core Idea", "Key Concepts", "Key Takeaways"],
        "skill_md_token_max": 4000, "glossary_token_max": 1500,
        "patterns_token_max": 2000, "cheatsheet_token_max": 1200,
        "chapter_token_max": 3000,
        "staleness_days": 90, "too_large_growth_pct": 150,
        "bm25_k1": 1.5, "bm25_b": 0.75, "rrf_k": 60, "default_top_k": 5,
        "staleness_penalty": 0.5,
    },
    "portfolio": {
        "statuses": ["on_track", "at_risk", "behind", "missed"],
        "rag_map": {"on_track": "G", "at_risk": "A", "behind": "R",
                    "missed": "R"},
        "human_gate_types": ["p0_change", "funding", "redline"],
        "wave_hours_warn": 24,
        "confidence_types": ["EXTRACTED", "INFERRED", "AMBIGUOUS"],
        "confidence_score": {"EXTRACTED": [1.0, 1.0], "INFERRED": [0.4, 0.9],
                             "AMBIGUOUS": [0.1, 0.3]},
        "god_node_pct": 0.2, "god_node_min_nodes": 10,
        "node_warn_threshold": 5000, "bfs_depth_max": 3, "dfs_depth_max": 6,
    },
    "review": {
        "vague_words": ["尽快", "持续关注", "有待进一步", "适当优化",
                        "后续跟进", "推进中"],
        "advice_words": ["建议", "应当", "必须", "务必"],
        "owner_fields": ["owner", "owner_role", "actor", "dri"],
    },
}

_AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
# 通用字符串工具（供句式/模糊措辞校验复用）
# --------------------------------------------------------------------------- #
def has_any(text: str, tokens: List[str]) -> bool:
    return any(t in text for t in tokens if t)

# -*- coding: utf-8 -*-
"""R04 七个技能模块的共享基础：JSON 读写、轻量 JSON Schema 校验、结果输出。

约束：纯标准库。技能之间不互相 import，只依赖 _common；阈值统一走
experience/thresholds.json（T9 阈值外置，改口径不改代码）。
与 r01/r02/r03/r06/r07/r08 保持同一套 _common 契约。
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
# 通用检查辅助：统一 {ok, msg, dim, sev} 结构（对齐 r01/r02/r03 样板）。
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
    "artifact": {
        "stub_markers": ["TODO", "FIXME", "XXX", "HACK", "PLACEHOLDER",
                         "NOT_IMPLEMENTED"],
        "stub_code_patterns": ["pass", "raise NotImplementedError",
                               "return null", "return {}"],
        "test_skip_markers": [".skip", "xit", "xdescribe", "pending"],
        "min_file_bytes": 1,
        "levels": ["L1_EXISTS", "L2_SUBSTANTIVE", "L3_WIRED"],
    },
    "gate": {
        "timeout_s": 120,
        "skipped_command": "NONE",
        "tail_chars": 500,
    },
    "strength": {
        "patterns": {
            "STRENGTH-001": {"severity": "error",
                             "name": "blocking-gate-declared"},
            "STRENGTH-002": {"severity": "error",
                             "name": "baseline-auto-update"},
            "STRENGTH-003": {"severity": "warning",
                             "name": "skip-categories-unjustified"},
            "STRENGTH-004": {"severity": "error",
                             "name": "layers-without-thresholds"},
            "STRENGTH-005": {"severity": "warning",
                             "name": "lowest-default-tier"},
            "STRENGTH-006": {"severity": "error",
                             "name": "baseline-pr-auto-approved"},
            "STRENGTH-007": {"severity": "error",
                             "name": "passed-but-never-run"},
        },
        "solid_min": 85,
        "at_risk_min": 50,
        "error_penalty": 15,
        "warning_penalty": 5,
        "skip_categories_max": 2,
        "never_blocks_markers": ["never blocks", "always exits 0",
                                 "always exit 0", "不阻断", "总是退出 0",
                                 "永不拦截"],
        "baseline_auto_update_markers": ["auto"],
        "lowest_default_tiers": ["theatre", "low", "minimal", "loosest",
                                 "最低"],
    },
    "criteria": {
        "evidence_line_re": ":[0-9]+",
        "evidence_field_re": "[A-Za-z][A-Za-z0-9_]*\\.[A-Za-z][A-Za-z0-9_]*",
        "statuses": ["pass", "warn", "fail"],
    },
    "quality": {
        "hedge_words": ["should", "probably", "seems to", "i believe",
                        "应该", "大概", "似乎", "我认为"],
        "absolutist_words": ["全部", "完美", "生产级", "所有", "绝对",
                             "all tests", "perfect", "production-ready"],
        "severities": ["error", "warning"],
    },
    "facts": {
        "source_type_whitelist": ["primary", "secondary", "unsourced"],
        "severities": {"hallucinated": "critical", "unsourced": "high",
                       "invalid_source_type": "high",
                       "citation_missing": "high",
                       "precision_drift": "high",
                       "coverage_gap": "medium"},
        "blocking_severities": ["critical", "high"],
    },
    "strengths": {
        "keep_required_fields": ["id", "what", "why_keep", "evidence"],
    },
    "human": {
        "comment_kinds": ["selection", "element"],
        "edit_kinds": ["edited", "deleted", "moved"],
        "batch_statuses": ["feedback", "closed", "superseded", "timeout",
                           "feedback-waiting"],
        "package_required_fields": ["artifact", "review_dimensions",
                                    "criteria_ref", "producer", "reviewer",
                                    "deadline"],
    },
    "review": {
        "hedge_words": ["should", "probably", "seems to", "i believe",
                        "应该", "大概", "似乎", "我认为"],
        "fix_keys": ["applied_fixes", "fixes_applied", "modified",
                     "modifications", "files_modified"],
        "evidence_keys": ["evidence", "evidence_refs", "evidences",
                          "level_results", "criteria_results",
                          "claims_checked", "findings", "traces",
                          "trace_results", "dimension_results",
                          "pattern_results", "evaluated_patterns", "keep_list", "applied_plan",
                          "recheck_results", "records", "results",
                          "commands", "items", "delta"],
        "conclusion_keys": ["summary", "conclusion", "overall_note",
                            "executive_summary", "report_text", "opinion",
                            "commentary", "reviewer_note", "verdict_note"],
        "verdict_enum": ["PASS", "FAIL", "BLOCKED"],
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

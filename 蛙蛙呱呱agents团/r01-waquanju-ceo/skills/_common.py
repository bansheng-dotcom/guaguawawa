# -*- coding: utf-8 -*-
"""R01 七个技能模块的共享基础：JSON/MD 读写、轻量 JSON Schema 校验、结果输出。

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
# 全局阈值（T9）：优先 experience/thresholds.json > 内置默认。
# --------------------------------------------------------------------------- #
_DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "intent": {
        "brief_fields": ["problem", "options", "assumptions", "constraints",
                         "impacted_roles", "success_criteria", "kill_criteria"],
        "options_min": 2, "assumptions_min": 3,
        "clarify_questions": ["problem", "customer", "distribution", "moat",
                              "funding", "founder_fit"],
        "levels": ["vision", "objective", "strategy", "milestone", "phase", "task"],
    },
    "decompose": {
        "taskcard_sections": ["goal", "owned_files", "requirements",
                              "interface_contract", "acceptance", "non_goals"],
        "acceptance_min": 1, "requirements_min": 1,
        "max_wave_depth": 6,
    },
    "decide": {
        "levels": ["可逆", "难逆", "不可逆"],
        "irreversible_keywords": ["签约", "扣款", "退款", "发薪", "删库", "上线生产",
                                   "裁员", "不可逆"],
        "hard_keywords": ["发布", "迁移", "改历史账", "解约", "大额"],
        "reversible_keywords": ["文案", "配色", "标题", "定价实验", "小范围"],
        "escalate_cost_months": 6,
        "card_fields": ["topic", "reversibility", "options", "recommendation",
                        "rationale", "rollback_plan", "success_criteria",
                        "kill_criteria", "owner", "deadline"],
    },
    "redteam": {
        "concern_levels": ["CRITICAL", "HIGH", "MEDIUM"],
        "concerns_min": 3,
        "verdicts": ["APPROVE", "REJECT", "DEFER"],
        "go_approve_min": 2, "stop_reject_min": 2,
    },
    "companyos": {
        "components": ["accountability_map", "scorecard", "meeting_cadence",
                       "ids", "rocks", "communication"],
        "scorecard_min": 5, "scorecard_max": 15,
        "rocks_min": 3, "rocks_max": 7, "ids_timebox_min": 15,
        "freeze_days": {"fundraise": 30, "pricing": 60, "market_pivot": 90,
                        "layoffs": 30},
    },
    "decisionlog": {
        "entry_fields": ["date", "title", "decision", "owner", "deadline",
                         "rationale", "rejected", "todos"],
        "retro_grades": ["WIN", "PARTIAL", "LOSS", "MIXED"],
        "retro_triggers": ["90天查点", "杀死标准触发", "决策被推翻", "季度全量"],
        "archive_days": 90,
    },
    "boardroom": {
        "memo_sections": ["wins", "misses", "plan", "asks"],
        "coach_fields": ["sticking_point", "current_approach",
                         "alternative_views", "action_items"],
        "alternative_views_min": 2,
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


def make_result(ok: bool, skill: str, action: str, checks_list: list[str]) -> dict:
    formatted_checks = [{"ok": False, "msg": c} for c in checks_list] if not ok else [{"ok": True, "msg": "Passed"}]
    return {
        "ok": ok,
        "skill": skill,
        "action": action,
        "checks": formatted_checks,
        "grade": 100 if ok else 0
    }

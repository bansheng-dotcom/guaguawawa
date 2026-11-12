# -*- coding: utf-8 -*-
"""R07 八个技能模块的共享基础：JSON/MD 读写、轻量 JSON Schema 校验、结果输出。

约束：纯标准库。技能之间不互相 import，只依赖 _common，保持「可组合、可独立
测试」的单元边界；阈值统一走 experience/thresholds.json（T9 阈值外置）。"""
from __future__ import annotations

import csv
import json
import os
import sys
from typing import Any, Dict, List, Optional


def emit(data: Dict[str, Any]) -> None:
    """以单行 JSON 输出结果，供编排器以子进程方式消费。

    Windows 下 stdout 默认 GBK（cp936），含 U+2212 等非 GBK 字符会抛
    UnicodeEncodeError；这里显式重配为 UTF-8，保证子进程端无论控制台编码
    都能稳定拿到完整 JSON（errors="replace" 只影响终端回显，不影响管道消费）。
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    print("__AGENT_RESULT__ " + json.dumps(data, ensure_ascii=False))


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def load_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_csv(path: str) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


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
# 轻量 JSON Schema 校验器（子集，支contracts.py 的确定性契约）# --------------------------------------------------------------------------- #
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
        return [f"{path}: {instance!r} 不在枚举 {schema['enum']}"]
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
# 全局阈值（T9）：优先 experience/thresholds.json > 内置默认# --------------------------------------------------------------------------- #
_DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "discovery": {"job_story_keys": ["situation", "motivation", "outcome"]},
    "ost": {"opportunities_min": 3, "opportunities_max": 7, "top_focus": 3,
            "solutions_min": 3, "experiments_min": 1,
            "poc_scale_min": 1, "poc_scale_max": 5, "poc_recommend_min": 12},
    "assumption": {"risk_types": ["value", "usability", "viability", "feasibility",
                                   "ethics", "gtm", "strategy", "team"]},
    "prd": {"gates": ["problem", "user", "value", "scope", "metric",
                      "acceptance", "risk", "read"],
            "story_ac_min": 4, "story_ac_max": 6,
            "jobstory_ac_min": 6, "jobstory_ac_max": 8,
            "risk_hypotheses_min": 3},
    "prioritize": {"confidence_max": 100.0, "effort_min": 0.1},
    "roadmap": {"release_categories": ["New Features", "Improvements", "Bug Fixes",
                                       "Breaking Changes", "Deprecations"]},
    "metrics": {"nsm_criteria": 7, "input_metrics_min": 3, "input_metrics_max": 5,
                "okr_sets": 3, "okr_kr_per_set": 3,
                "okr_confidence_min": 60, "okr_confidence_max": 70},
    "techbrief": {"tech_modules": ["user_impact", "frontend", "backend",
                                   "agent", "failure"],
                  "ui_modules": ["page_goal", "ia", "user_actions", "states",
                                 "review_focus"]},
    "decision": {"layers": ["product_judgment", "execution_spec", "decision_gate"]},
    "experience": {"card_fields": ["trigger", "scope", "rule", "boundary",
                                   "source_credibility"]},
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
# 通用字符串工具（供句意/模糊措辞校验复用）
# --------------------------------------------------------------------------- #
def has_any(text: str, tokens: List[str]) -> bool:
    return any(t in text for t in tokens if t)


def is_blank(value: Any) -> bool:
    """统一的「空值」判定：None / 空串 / 空白串 / 空容器。"""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def check(ok: bool, msg: str, dim: str = "", sev: str = "") -> Dict[str, Any]:
    """构造一条确定性门禁判据（dim=维度，sev=BLOCKER/MAJOR/OK）。"""
    return {"ok": bool(ok), "msg": msg, "dim": dim,
            "sev": sev or ("OK" if ok else "BLOCKER")}


def make_result(ok: bool, skill: str, action: str,
                checks_list: Optional[List[Any]] = None, **extra: Any) -> Dict[str, Any]:
    """统一产出结构：{ok, skill, action, checks[], grade, score} + 动作扩展字段。

    checks 的每一条必须是可被 harness / report_contract / SARIF 消费的字典：
    {ok, msg, dim, sev}。历史调用方传入的裸字符串按整体结论归一，避免
    「失败项被记成 ok=True」的假绿回归。
    """
    normalized: List[Dict[str, Any]] = []
    for item in (checks_list or []):
        if isinstance(item, dict):
            entry = dict(item)
            entry["ok"] = bool(entry.get("ok", ok))
            entry["msg"] = str(entry.get("msg", ""))
            entry.setdefault("dim", "")
            entry.setdefault("sev", "OK" if entry["ok"] else "BLOCKER")
            normalized.append(entry)
        else:
            normalized.append(check(ok, str(item)))
    if not normalized:
        normalized = [check(ok, "全部判据通过" if ok else "判据未通过", "summary")]
    result: Dict[str, Any] = {
        "ok": bool(ok),
        "skill": skill,
        "action": action,
        "checks": normalized,
        "grade": "PASS" if ok else "FAIL",
        "score": 100 if ok else 0,
        # 兼容 review.py 的「价值主张可衡量」门禁：任何产物都带可量化口径槽位。
        "metrics": {"gate_score": 100 if ok else 0,
                    "checks_total": len(normalized),
                    "checks_failed": sum(1 for c in normalized if not c["ok"])},
    }
    result.update(extra)
    return result

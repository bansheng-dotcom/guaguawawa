# -*- coding: utf-8 -*-
"""R08 七个技能模块的共享基础：JSON/MD 读写、轻量 JSON Schema 校验、结果输出。

约束：纯标准库。技能之间不互相 import，只依赖 _common，保持「可组合、可独立
测试」的单元边界；阈值统一走 experience/thresholds.json（T9 阈值外置）。"""
from __future__ import annotations

import csv
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
# 轻量 JSON Schema 校验器（子集，支撑 contracts.py 的确定性契约）。# --------------------------------------------------------------------------- #
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
# 全局阈值（T9）：优先 experience/thresholds.json > 内置默认。# --------------------------------------------------------------------------- #
_DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "slice": {"artifact_types": ["cli", "tool", "web", "landing", "saas",
                                 "email", "app"],
              "slices_min": 1},
    "mvp": {"gates": ["assumption", "mvp", "experiment", "criteria", "handoff"],
            "risk_types": ["value", "usability", "viability", "feasibility",
                           "ethics", "gtm", "strategy", "team"],
            "experiment_min": 1},
    "scaffold": {"stack_types": ["nextjs", "rails", "mcp", "python-flask",
                                 "vite-html", "node-express"],
                 "auth_types": ["none", "api-key", "oauth", "session"],
                 "entry_markers": ["main", "index", "app"]},
    "landing": {"keys": ["goal", "headline", "subhead", "proof_points", "form",
                         "button", "faq", "post_submit"],
                "proof_min": 3,
                "tech_constraints": ["single_file_index_html", "no_js_library",
                                     "form_deliverable", "mobile_first",
                                     "button_single_accent"]},
    "saas": {"pages_min": 2,
             "auth_types": ["session", "jwt", "oauth", "email-link", "none"]},
    "prototype": {"structure_keys": ["main", "app", "core", "features",
                                     "shared_widgets", "router"],
                  "feature_layers": ["data", "domain", "presentation", "providers"],
                  "platforms": ["android", "ios", "web", "desktop"]},
    "design": {"token_types": ["color", "typography", "spacing"],
               "scale_types": ["font_size", "spacing", "radius", "shadow"]},
    "qa": {"required_checks": ["build", "typecheck", "screenshot", "design_qa",
                               "a11y"],
           "status_types": ["pass", "fail", "block"],
           "a11y_min": 3},
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
# 通用检查辅助：统一 {ok, msg, dim, sev} 结构（对齐 r01/r02/r03/r04/r05 样板）。# --------------------------------------------------------------------------- #
def ck(ok: bool, msg: str, dim: str, sev: str = "OK", **ev) -> Dict[str, Any]:
    d: Dict[str, Any] = {"ok": bool(ok), "msg": msg, "dim": dim, "sev": sev}
    d.update(ev)
    return d


def result(checks: List[Dict[str, Any]], ok: bool = None, **fields) -> Dict[str, Any]:
    """统一产出：ok/checks 必带，叠加 verdict/next；其余字段透传。

    ok 缺省时由 checks 全绿推导（与 r05 口径一致）；显式传 ok 用于技能内部
    有「非检查项」参与判定的场景。verdict 只允许 PASS/FAIL 两值（实现门禁语义）。
    """
    if ok is None:
        ok = all(x.get("ok", False) for x in checks)
    verdict = fields.pop("verdict", "PASS" if ok else "FAIL")
    next_ = fields.pop("next",
                       "实现工件通过全部门禁，可进入质量验证与交接"
                       if ok else "存在未通过门禁，按 checks 修复后重验")
    out: Dict[str, Any] = {"ok": bool(ok), "checks": checks,
                           "verdict": verdict, "next": next_}
    out.update(fields)
    return out


# --------------------------------------------------------------------------- #
# 通用字符串工具（供句意/模糊措辞校验复用）。# --------------------------------------------------------------------------- #
def has_any(text: str, tokens: List[str]) -> bool:
    return any(t in text for t in tokens if t)

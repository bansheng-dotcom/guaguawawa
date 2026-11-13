# -*- coding: utf-8 -*-
"""数据契约：技能跑前校验列名/类型/日期/枚举/范围，并产出可追溯的 provenance。"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class FieldSpec:
    name: str
    dtype: str = "str"          # str|int|float|date|bool
    required: bool = True
    enum: Optional[List[str]] = None
    range: Optional[List[float]] = None
    date_fmt: str = "%Y-%m-%d"


@dataclass
class DataContract:
    name: str
    fields: List[FieldSpec]
    primary_key: Optional[str] = None
    grain: str = "row"
    calendar: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DataContract":
        return cls(name=d.get("name", "data"),
                   fields=[FieldSpec(**f) for f in d.get("fields", [])],
                   primary_key=d.get("primary_key"),
                   grain=d.get("grain", "row"),
                   calendar=d.get("calendar"))


def _as_float(v: Any) -> Optional[float]:
    try:
        if str(v).strip() == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def validate_rows(rows: Sequence[Dict[str, Any]], contract: DataContract,
                  max_errors: int = 20) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    names = {f.name for f in contract.fields}
    if rows:
        missing_cols = names - set(rows[0].keys())
        if missing_cols:
            return {"ok": False, "errors": [{"field": c, "row": None,
                                             "reason": f"缺列 {c}"} for c in sorted(missing_cols)],
                    "warnings": []}
    for f in contract.fields:
        for i, r in enumerate(rows):
            v = r.get(f.name)
            s = "" if v is None else str(v).strip()
            if s == "":
                if f.required:
                    errors.append({"field": f.name, "row": i, "reason": "必填为空"})
                continue
            if f.dtype in ("int", "float"):
                x = _as_float(s)
                if x is None:
                    errors.append({"field": f.name, "row": i, "reason": "不是数值"})
                    continue
                if f.dtype == "int" and abs(x - round(x)) > 1e-9:
                    errors.append({"field": f.name, "row": i, "reason": "不是整数"})
                if f.range and not (f.range[0] <= x <= f.range[1]):
                    errors.append({"field": f.name, "row": i,
                                   "reason": f"越界 {x} not in {f.range}"})
            elif f.dtype == "date":
                try:
                    date.fromisoformat(s[:10])
                except ValueError:
                    errors.append({"field": f.name, "row": i, "reason": "日期不可解析"})
            elif f.dtype == "bool":
                if s not in ("0", "1", "true", "false", "True", "False"):
                    errors.append({"field": f.name, "row": i, "reason": "不是布尔"})
            if f.enum and s not in [str(x) for x in f.enum]:
                errors.append({"field": f.name, "row": i, "reason": f"枚举外: {s}"})
            if len(errors) >= max_errors:
                break
        if len(errors) >= max_errors:
            break
    return {"ok": not errors, "errors": errors[:max_errors], "warnings": warnings}


def hash_rows(rows: Sequence[Dict[str, Any]]) -> str:
    h = hashlib.sha256()
    for r in rows:
        h.update(json.dumps(r, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8"))
    return "sha256:" + h.hexdigest()[:16]


def provenance(rows: Sequence[Dict[str, Any]], contract: Optional[DataContract],
               skill: str, seed: Optional[int] = None,
               caliber: str = "", version: str = "2.0") -> Dict[str, Any]:
    return {"skill": skill, "skill_version": version,
            "data_hash": hash_rows(rows), "rows": len(rows),
            "seed": seed, "caliber": caliber,
            "contract": contract.name if contract else None,
            "grain": contract.grain if contract else None}


# --------------------------------------------------------------------------- #
# 技能输入契约：schema 放在 core/data_contracts/<skill>.json
# --------------------------------------------------------------------------- #
import csv
from pathlib import Path as _Path

CONTRACT_DIR = _Path(__file__).resolve().parent / "data_contracts"
INPUT_KEYS = {
    "quality": ["input"], "abtest": ["input"], "did": ["input"], "rdd": ["input"],
    "regression": ["input"], "ttest": ["input"], "chi2": ["input"], "anova": ["input"],
    "elasticity": ["input"], "describe": ["input"], "correlate": ["input"],
    "rootcause": ["input"], "explore": ["input"], "matched": ["treat", "control"],
    "causal": ["input"],
}


def load_schema(skill: str) -> Optional[DataContract]:
    p = CONTRACT_DIR / f"{skill}.json"
    if not p.exists():
        return None
    return DataContract.from_dict(json.loads(p.read_text(encoding="utf-8")))


def _read_rows(path: str):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def check_cli(skill: str, args: Dict[str, Any], mode: str = "warn") -> Dict[str, Any]:
    """按技能 schema 校验输入。mode=warn 只返回 errors 不阻断；block 由调用方拦截。"""
    action = str(args.get("action") or "")
    if skill == "power":
        return check_power_args(args)
    j = check_json_skill(skill, action, args)
    if j.get("checked"):
        return j
    key = f"{skill}:{action}" if action else skill
    contract = load_schema(key) or load_schema(skill)
    if contract is None:
        return {"ok": True, "checked": False, "errors": []}
    paths = [args.get(k) for k in INPUT_KEYS.get(skill, ["input"])]
    paths = [x for x in paths if x]
    if not paths:
        return {"ok": True, "checked": False, "errors": []}
    errors = []
    for path in paths:
        try:
            rows = _read_rows(str(path))
        except OSError as e:
            errors.append({"field": None, "row": None, "reason": f"无法读取 {path}: {e}"})
            continue
        res = validate_rows(rows, contract)
        errors.extend(res["errors"])
    summary = {}
    for e in errors:
        key = (e.get("field"), e.get("reason"))
        summary[key] = summary.get(key, 0) + 1
    brief = [{"field": k[0], "reason": k[1], "rows": v} for k, v in
             sorted(summary.items(), key=lambda kv: -kv[1])[:5]]
    return {"ok": not errors, "checked": True, "errors": brief,
            "error_rows": len(errors), "mode": mode, "schema": contract.name}


# --------------------------------------------------------------------------- #
# JSON 输入 / 标量参数校验（semantics / viz / selfmedia / power）
# --------------------------------------------------------------------------- #
JSON_RULES = {
    ("semantics", "validate"): {"required": ["semantic_models"], "types": {"semantic_models": list}},
    ("semantics", "tree"): {"required": ["metrics"], "types": {"metrics": list}},
    ("semantics", "link"): {"required": ["semantic_models"], "types": {"semantic_models": list}},
    ("viz", "spec"): {"required": ["chart_type", "title", "data"], "types": {"data": list}},
    ("selfmedia", "normalize"): {"required": ["platforms"], "types": {"platforms": dict}},
    ("selfmedia", "dashboard"): {"required": ["records"], "types": {"records": list}},
    ("selfmedia", "report"): {"required": ["total_fans", "platform_count"], "types": {"platform_count": int}},
}


def check_json_skill(skill: str, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """JSON 输入或纯标量技能的契约校验。"""
    rule = JSON_RULES.get((skill, action))
    if rule is None:
        return {"ok": True, "checked": False, "errors": []}
    if skill == "power":
        return {"ok": True, "checked": False, "errors": []}
    path = args.get("input")
    if not path:
        return {"ok": False, "checked": True,
                "errors": [{"field": "input", "reason": "缺少 --input"}]}
    try:
        obj = json.loads(_Path(str(path)).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return {"ok": False, "checked": True,
                "errors": [{"field": "input", "reason": f"JSON 不可读: {e}"}]}
    errors = []
    for k in rule.get("required", []):
        if k not in obj:
            errors.append({"field": k, "reason": "缺必填键"})
    for k, typ in (rule.get("types") or {}).items():
        if k in obj and not isinstance(obj[k], typ):
            errors.append({"field": k, "reason": f"类型应为 {typ.__name__}"})
    return {"ok": not errors, "checked": True, "errors": errors, "schema": f"{skill}:{action}"}


def check_power_args(args: Dict[str, Any]) -> Dict[str, Any]:
    errors = []
    try:
        if float(args.get("baseline") or 0) <= 0:
            errors.append({"field": "baseline", "reason": "必须 >0"})
    except (TypeError, ValueError):
        errors.append({"field": "baseline", "reason": "不是数值"})
    if not args.get("mde") and not args.get("n_per_group"):
        errors.append({"field": "mde/n_per_group", "reason": "至少给一个"})
    return {"ok": not errors, "checked": True, "errors": errors, "schema": "power"}

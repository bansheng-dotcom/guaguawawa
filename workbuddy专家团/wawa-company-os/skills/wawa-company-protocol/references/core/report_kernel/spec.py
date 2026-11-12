# -*- coding: utf-8 -*-
"""report_kernel · spec —— 原型 + 差异的声明式报告规格。

约束（写进 schema，不靠纪律）：
1. role 文件只允许 extends + overrides，禁止重定义结构；
2. 未知键直接校验失败（additionalProperties: false）；
3. 只允许一层继承，禁止菱形。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
SPEC_DIR = ROOT / "report_specs"
SCHEMA = json.loads((SPEC_DIR / "schema.json").read_text(encoding="utf-8"))


def _read(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def archetype(name: str) -> Dict[str, Any]:
    p = SPEC_DIR / "archetypes" / f"{name}.yaml"
    if not p.exists():
        raise FileNotFoundError(f"未知原型: {name}")
    return _read(p)


def role_spec_path(role: str) -> Path:
    return SPEC_DIR / "roles" / f"{role}.yaml"


def load(role: str) -> Dict[str, Any]:
    """返回合并后的有效规格；不存在则抛错（禁止静默回落）。"""
    p = role_spec_path(role)
    if not p.exists():
        raise FileNotFoundError(f"missing spec: {p}（禁止回落到 generic）")
    raw = _read(p)
    errs = validate_doc(raw)
    if errs:
        raise ValueError(f"{p.name} 校验失败: {errs}")
    base = archetype(raw["extends"])
    ov = raw.get("overrides") or {}

    sections = [dict(s) for s in base.get("sections", [])]
    for sid, tweak in (ov.get("sections") or {}).items():
        hit = next((s for s in sections if s["id"] == sid), None)
        if hit is None:
            raise ValueError(f"{p.name}: overrides.sections 指向不存在的 section: {sid}")
        hit.update(tweak)

    fid = dict(base.get("fidelity") or {})
    fid.update(ov.get("fidelity") or {})

    dims = ov.get("dimensions") or base.get("dimensions") or []

    return {
        "role": raw["role"],
        "extends": raw["extends"],
        "tier": base.get("tier", "C"),
        "doc_type": raw.get("doc_type") or base.get("doc_type", "角色报告"),
        "title_prefix": raw.get("title_prefix", ""),
        "adapter": raw.get("adapter"),
        "sections": sections,
        "fidelity": fid,
        "dimensions": dims,
    }


def validate_doc(raw: Dict[str, Any]) -> List[str]:
    try:
        jsonschema.validate(raw, SCHEMA)
        return []
    except jsonschema.ValidationError as e:
        return [f"{'/'.join(str(x) for x in e.absolute_path)}: {e.message}"]


def validate(role: str) -> List[str]:
    p = role_spec_path(role)
    if not p.exists():
        return [f"missing spec: {p}"]
    return validate_doc(_read(p))


def all_roles() -> List[str]:
    return sorted(p.stem for p in (SPEC_DIR / "roles").glob("r*.yaml"))

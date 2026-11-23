# -*- coding: utf-8 -*-
"""core.source_profile —— 源画像（SYSTEM-UPGRADE-SOP v3.1 · S0）。

一个「源」声明三件事（都是业务无关的）：
    atomic_grain  这个源能捕获的最低粒度（Kimball：原子粒度优先）
    fields        这个源给哪些字段
    history       snapshot_only（只能采当下）/ historical（有历史序列）

业务词不在这里。同一个源服务所有业务线。

用法：
    from core import source_profile as sp
    src = sp.load("tmall_search")
    errs = sp.validate(src)          # 空 = 合法
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = "dsh.source/v1"
KINDS = ("platform_search", "pdf_report", "csv_manual", "api", "gov_stats")
HISTORY = ("snapshot_only", "historical")
TYPES = ("string", "number", "date", "bool")

ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = ROOT / "configs" / "sources"


def _yaml(p: Path) -> Dict[str, Any]:
    try:
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def load(source_id: str, extra_dirs: Optional[List[str]] = None) -> Dict[str, Any]:
    """按 id 找 configs/sources/<id>.yaml；也支持直接传路径。"""
    p = Path(source_id)
    if p.is_file():
        return _yaml(p)
    for d in ([SOURCES_DIR] + [Path(x) for x in (extra_dirs or [])]):
        cand = Path(d) / (str(source_id) + ".yaml")
        if cand.is_file():
            return _yaml(cand)
    return {}


def validate(src: Dict[str, Any]) -> List[str]:
    """源画像校验，空 = 合法。"""
    errs: List[str] = []
    if not isinstance(src, dict):
        return ["源画像必须是 dict"]
    if src.get("schema") != SCHEMA:
        errs.append("schema 必须是 %s" % SCHEMA)
    if not src.get("id"):
        errs.append("缺 id")
    if str(src.get("kind") or "") not in KINDS:
        errs.append("kind 必须是 %s" % (KINDS,))
    # G-A：原子粒度必须声明——没有它，后面所有 rollup 都无法校验
    grain = [str(x) for x in (src.get("atomic_grain") or []) if str(x).strip()]
    if not grain:
        errs.append("缺 atomic_grain（源能捕获的最低粒度）")
    if str(src.get("history") or "") not in HISTORY:
        errs.append("history 必须是 %s" % (HISTORY,))
    fields = src.get("fields") or []
    if not fields:
        errs.append("fields 为空")
    names = set()
    for i, f in enumerate(fields):
        n = str(f.get("name") or "")
        if not n:
            errs.append("fields[%d] 缺 name" % i)
            continue
        if n in names:
            errs.append("fields 重名: %s" % n)
        names.add(n)
        if str(f.get("type") or "") not in TYPES:
            errs.append("fields[%s].type 非法: %r" % (n, f.get("type")))
    # 原子粒度的每个维度都必须是字段之一
    for g in grain:
        if names and g not in names:
            errs.append("atomic_grain 的 %r 不在 fields 里" % g)
    return errs


def field_names(src: Dict[str, Any]) -> List[str]:
    return [str(f.get("name")) for f in src.get("fields") or []]


def numeric_fields(src: Dict[str, Any]) -> List[str]:
    return [str(f.get("name")) for f in src.get("fields") or []
            if str(f.get("type")) == "number"]


def covers(src: Dict[str, Any], columns: List[str]) -> List[str]:
    """这些列里，哪些是源没有的（空 = 全都有）。"""
    have = set(field_names(src))
    return [c for c in columns if c not in have]

# -*- coding: utf-8 -*-
"""报告结构 profile：内容模型不变，按任务类型组装模块。

不是“多套模板”：模块集合和页序由 profile 决定，正文/图表/表格仍走同一套
claim → slice → encoding → blocks。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "configs" / "report_structures.yaml"
_DEFAULT = {
    "default": "research",
    "profiles": {
        "research": {"modules": ["cover", "decision", "toc", "body", "actions",
                                 "sources", "support", "caliber", "back"],
                     "table_policy": "ref_full", "chart_policy": "relation"},
    },
}


def load() -> Dict[str, Any]:
    if not PATH.is_file():
        return dict(_DEFAULT)
    try:
        data = yaml.safe_load(PATH.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return dict(_DEFAULT)
    if not isinstance(data, dict) or not data.get("profiles"):
        return dict(_DEFAULT)
    return data


def profile_for(doc_type: str = "", intent: str = "", explicit: str = "") -> str:
    data = load()
    names = data.get("profiles") or {}
    if explicit and explicit in names:
        return explicit
    text = f"{doc_type} {intent}"
    if any(k in text for k in ("一页", "brief")):
        return "brief" if "brief" in names else data.get("default", "research")
    if any(k in text for k in ("诊断", "经营分析", "复盘")):
        return "diagnostic" if "diagnostic" in names else data.get("default", "research")
    if any(k in text for k in ("决策", "拍板", "要不要做")):
        return "decision" if "decision" in names else data.get("default", "research")
    if "简报" in text:
        return "decision" if "decision" in names else data.get("default", "research")
    return data.get("default", "research")


def modules(contract: Dict[str, Any]) -> List[str]:
    data = load()
    name = str(contract.get("structure_profile") or "")
    if not name:
        name = profile_for(str(contract.get("doc_type") or ""),
                           str(contract.get("intent") or contract.get("standfirst") or ""))
    prof = (data.get("profiles") or {}).get(name) or {}
    mods = prof.get("modules") or ["cover", "decision", "toc", "body",
                                   "actions", "sources", "caliber", "back"]
    return [str(x) for x in mods]


def has(contract: Dict[str, Any], module: str) -> bool:
    return module in modules(contract)


def table_policy(contract: Dict[str, Any]) -> str:
    data = load()
    name = str(contract.get("structure_profile") or "")
    prof = (data.get("profiles") or {}).get(name) or {}
    return str(prof.get("table_policy") or "ref_full")

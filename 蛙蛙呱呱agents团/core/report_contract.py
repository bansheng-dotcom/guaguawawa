# -*- coding: utf-8 -*-
"""core.report_contract —— 报告契约的单一读取入口。

所有产线模块（卡片、收卡、文笔、版式、门禁、claims_v4）只从这里读阈值，
禁止在代码里再写第二套「每节多少字 / 最多几条判断 / 图几点」。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs" / "report_contract.yaml"

DEFAULTS: Dict[str, Any] = {
    "paragraph_max_chars": 300,
    "paragraph_hard_max_chars": 330,
    "section_max_chars": None,
    "main_claims_max": 7,
    "decision_items_max": 5,
    "decision_fields_required": True,
    "title_max_chars": 20,
    "chart_per_main": 1,
    "table_per_main": 1,
    "decision_page": True,
    "gap_page": True,
    "appendix": True,
    "source_grades": ["S", "A", "B"],
    "chart_unit_strict": True,
    "chart_entity_strict": True,
    "chart_min_points": 3,
    "chart_max_points": 12,
    "chart_baseline_required": True,
    "chart_annotate_required": True,
    "auto_derive_charts": True,
    "prose_length_score": False,
    "prose_numbers_per_1000_min": 15,
}


def load() -> Dict[str, Any]:
    data = dict(DEFAULTS)
    if not CONFIG.exists():
        return data
    try:
        import yaml
        raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return data
    for k, v in (raw.get("report") or {}).items():
        if v is not None or k == "section_max_chars":
            data[k] = v
    return data


def get(key: str, default: Any = None) -> Any:
    return load().get(key, default)


def paragraph_max() -> int:
    return int(load().get("paragraph_max_chars") or 300)


def paragraph_hard_max() -> int:
    return int(load().get("paragraph_hard_max_chars") or 330)


def main_claims_max() -> int:
    return int(load().get("main_claims_max") or 7)

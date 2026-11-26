# -*- coding: utf-8 -*-
"""core.report.report_contract —— 报告契约的单一读取入口。

所有产线模块（卡片、收卡、文笔、版式、门禁、claims_v4）只从这里读阈值，
禁止在代码里再写第二套「每节多少字 / 最多几条判断 / 图几点」。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "report_contract.yaml"

DEFAULTS: Dict[str, Any] = {
    "paragraph_max_chars": 300,
    "paragraph_hard_max_chars": 330,
    "section_max_chars": None,
    "main_claims_max": 0,
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
    """0 = 自适应，不设上限；只有显式正整数才截断正文。"""
    raw = load().get("main_claims_max")
    if raw in (None, "", 0, "0"):
        return 0
    return int(raw)


#: 文笔门禁兜底值：与 configs/report_prose.yaml 逐键对齐（P5-2 单一出处）。
#: 配置文件缺失时按**严格值** fail-closed，不用宽松默认值放行薄稿。
PROSE_DEFAULTS: Dict[str, Any] = {
    "chars_per_section": [1000, 1600],
    "chars_table_section": [800, 1300],
    "chars_hard_min": 800,
    "numbers_per_1000_chars_min": 15,
    "required_blocks": ["结论", "事实", "机理", "反例", "所以"],
    "markers": ["判别", "证伪", "如果", "若", "下一期", "信号"],
    "contrast_markers": ["不是", "而是", "一种解释", "另一种解释"],
    "banned_phrases": [],
    "rubric": {"pass": 70, "usable": 55},
}


def prose_defaults() -> Dict[str, Any]:
    """返回文笔门禁兜底值的深拷贝（调用方可安全修改）。"""
    import copy
    return copy.deepcopy(PROSE_DEFAULTS)

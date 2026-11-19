# -*- coding: utf-8 -*-
"""core.coverage_policy —— 覆盖门禁阈值（唯一出处：configs/report_coverage.yaml）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "configs" / "report_coverage.yaml"

DEFAULTS: Dict[str, Any] = {
    "coverage": {
        "cited_sources_min": 50,
        "saturation_no_new": 15,
        "page_floor": 21,
        "maps_required": ["national", "regional"],
        "core_units_min": 3,
        "core_units_max": 5,
        "long_tail_ratio_max": 0.40,
        "core_estimated_ratio_max": 0.30,
        "core_missing": "block",
        "long_tail_missing": "context_red",
        "quick_tier": False,
    },
    "audit": {"hard": ["coverage", "evidence", "charts", "layout"], "soft": ["prose"]},
    "research": {
        "meta_prompts": ["规模与增长", "链路与节点", "竞争与集中度", "渠道与价格",
                         "成本与损耗", "合规与标准", "地理与产区", "风险与情景"],
        "source_grades": {"A": "官方统计/标准/法规", "B": "行业报告/协会/券商/咨询",
                          "C": "公司披露/年报/招股书", "D": "学术研究",
                          "E": "专业社区/从业者", "F": "媒体（只做线索）"},
        "core_source_grades": ["A", "B", "C", "D"],
    },
}


def load(path: str | Path | None = None) -> Dict[str, Any]:
    p = Path(path) if path else DEFAULT_PATH
    data = dict(DEFAULTS)
    if p.exists():
        try:
            import yaml
            raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            for k, v in raw.items():
                if isinstance(v, dict) and isinstance(data.get(k), dict):
                    data[k] = {**data[k], **v}
                else:
                    data[k] = v
        except Exception:
            pass
    return data

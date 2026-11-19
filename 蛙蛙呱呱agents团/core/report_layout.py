# -*- coding: utf-8 -*-
"""报告版式默认值：从 configs/report_flow.yaml 读，缺省 flow。

单一出处：默认版式不在 CLI 里写死，改配置即改默认。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs" / "report_flow.yaml"

_FALLBACK = {"default_layout": "flow", "section_chars": [1000, 1600],
             "appendix_max_pages": 1}


def load() -> Dict[str, Any]:
    data = dict(_FALLBACK)
    if not CONFIG.exists():
        return data
    try:
        import yaml
        raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return data
    flow = raw.get("flow") or {}
    for k in ("default_layout", "section_chars", "appendix_max_pages"):
        if k in flow:
            data[k] = flow[k]
    return data


def default_layout() -> str:
    v = str(load().get("default_layout") or "flow")
    return v if v in ("flow", "paper") else "flow"

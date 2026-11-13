# -*- coding: utf-8 -*-
"""R03 领域财务账本解析器 (L04 领域账本层)。

对标高星标杆: awesome-design-md (126k+)
统一持久化规范文件 FINANCIAL_SPEC.md，集中管理阈值、红线与业务口径，防止多轮跨任务口径漂移。
"""
from __future__ import annotations
import os
import re
from typing import Any, Dict

class FinancialLedgerParser:
    """持久化财务合规规范账本解析器。"""

    _SPEC_CACHE: Dict[str, Any] = {}

    @classmethod
    def get_spec_path(cls) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "FINANCIAL_SPEC.md")

    @classmethod
    def load_spec(cls, force_reload: bool = False) -> Dict[str, Any]:
        """读取并解析根目录 FINANCIAL_SPEC.md。"""
        if cls._SPEC_CACHE and not force_reload:
            return cls._SPEC_CACHE

        spec_file = cls.get_spec_path()
        if not os.path.exists(spec_file):
            return {
                "BALANCE_DIFF_TOLERANCE": 0.0,
                "RUNWAY_ALERT_MONTHS": 6.0,
                "BURN_MULTIPLE_CEILING": 2.5,
                "DSR_RESPONSE_SLA_DAYS": 30,
                "FINANCIAL_RECORD_RETENTION_YEARS": 7,
                "AML_CTR_THRESHOLD": 10000.0,
                "LICENSED_GUARANTEE_WORDS": ["保本", "稳赚", "零风险"]
            }

        with open(spec_file, "r", encoding="utf-8") as f:
            content = f.read()

        parsed: Dict[str, Any] = {}

        # 匹配配置项 KEY = VALUE
        for match in re.finditer(r"([A-Z0-9_]+)\s*=\s*(.+)", content):
            key = match.group(1).strip()
            val_raw = match.group(2).strip()

            if val_raw.startswith("[") and val_raw.endswith("]"):
                # 简单列表解析
                items = [item.strip(" '\"") for item in val_raw[1:-1].split(",") if item.strip()]
                parsed[key] = items
            else:
                try:
                    if "." in val_raw:
                        parsed[key] = float(val_raw)
                    else:
                        parsed[key] = int(val_raw)
                except ValueError:
                    parsed[key] = val_raw

        cls._SPEC_CACHE = parsed
        return parsed

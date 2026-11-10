# -*- coding: utf-8 -*-
"""R02 持久化运营领域规范账本体系 (轮次 4 落地)。

对标高星标杆: awesome-design-md / google-labs-code/design.md
统一解析与管理全局运营约束规范，防止跨任务指标漂移。
"""
from __future__ import annotations
import os
import re
from typing import Any, Dict

class OperationsLedgerParser:
    """运营规范账本解析器。"""

    def __init__(self, ledger_path: str = "OPERATIONS_SPEC.md"):
        self.ledger_path = ledger_path

    def load_rules(self) -> Dict[str, Any]:
        if not os.path.exists(self.ledger_path):
            # 返回内置基准法则
            return {
                "max_task_hours": 8.0,
                "urgent_load_multiplier": 1.2,
                "project_concentration_threshold": 0.50,
                "escalation_minutes": 30,
                "closure_window_days": 7,
                "meeting_timeboxes": {"daily": 15, "weekly": 60, "retro": 120}
            }
        
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            content = f.read()

        rules: Dict[str, Any] = {}
        # 简单提取键值与阈值
        m = re.search(r"MAX_TASK_HOURS\s*=\s*(\d+)", content)
        if m:
            rules["max_task_hours"] = float(m.group(1))
        m = re.search(r"URGENT_WEIGHT\s*=\s*([\d\.]+)", content)
        if m:
            rules["urgent_load_multiplier"] = float(m.group(1))

        return rules

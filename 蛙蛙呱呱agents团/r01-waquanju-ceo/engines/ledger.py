# -*- coding: utf-8 -*-
"""R01 蛙全局 CEO 持久化规范账本解析器 (Executive Ledger Parser)。

对标 GitHub 开源标杆:
- awesome-design-md (126k+ stars) / google-labs-code/design.md
- 解析 EXECUTIVE_GOVERNANCE_SPEC.md，提取全局决策阈值、红线规则与治理模式。
"""
from __future__ import annotations
import json
import os
import re
from typing import Any, Dict

class ExecutiveLedgerParser:
    """CEO 规范账本解析引擎。"""
    
    DEFAULT_SPEC_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "EXECUTIVE_GOVERNANCE_SPEC.md"
    )

    @classmethod
    def load_spec(cls, spec_path: str = DEFAULT_SPEC_PATH) -> Dict[str, Any]:
        """读取并解析规范账本。"""
        if not os.path.exists(spec_path):
            # 返回默认兜底账本
            return {
                "constants": {
                    "FREEZE_DAYS_PRICING": 60,
                    "FREEZE_DAYS_FUNDING": 30,
                    "FREEZE_DAYS_PIVOT": 90,
                    "FREEZE_DAYS_LAYOFFS": 30,
                    "SCORECARD_METRICS_MIN": 5,
                    "SCORECARD_METRICS_MAX": 15,
                    "ESCALATION_COST_THRESHOLD_MONTHS": 6
                },
                "prohibited_phrases": ["逐步推进", "尽快落实", "进一步优化", "加强各部门协同"]
            }

        with open(spec_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 提取 JSON 常量块
        constants = {}
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            try:
                constants = json.loads(json_match.group(1))
            except Exception:
                pass

        # 提取禁止词列表
        prohibited = []
        for line in content.splitlines():
            if "❌" in line:
                m = re.findall(r"“([^”]+)”|\"([^\"]+)\"", line)
                for g1, g2 in m:
                    phrase = g1 or g2
                    if phrase:
                        prohibited.append(phrase)

        return {
            "constants": constants,
            "prohibited_phrases": prohibited,
            "version": "1.0",
            "file": spec_path
        }

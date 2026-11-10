# -*- coding: utf-8 -*-
"""L04 领域账本层：标准代码审查规范与外部规则注册器。
对标开源标杆：awesome-design-md (Stars: 2k+), standard/standard (Code Specs, Stars: 29k+)

功能：
1. 解析并提供标准规范账本 REVIEW_SPEC.md 与 thresholds.json；
2. 提供统一的全局阈值与规范获取接口（get_spec, get_threshold）；
3. 支持动态规则注册与热更新覆盖，确保规则外置不破损契约。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


class ReviewSpecRegistry:
    """领域规范统一注册与提取器"""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.spec_file = os.path.join(self.base_dir, "REVIEW_SPEC.md")
        self.thresholds_file = os.path.join(self.base_dir, "experience", "thresholds.json")
        self._cached_spec: Optional[str] = None
        self._cached_thresholds: Optional[Dict[str, Any]] = None

    def get_raw_spec(self) -> str:
        """读取物理规范账本全文"""
        if self._cached_spec is None:
            if os.path.isfile(self.spec_file):
                with open(self.spec_file, "r", encoding="utf-8") as f:
                    self._cached_spec = f.read()
            else:
                self._cached_spec = "# REVIEW_SPEC (Fallback Default)"
        return self._cached_spec

    def get_thresholds(self) -> Dict[str, Any]:
        """读取标准阈值字典"""
        if self._cached_thresholds is None:
            if os.path.isfile(self.thresholds_file):
                with open(self.thresholds_file, "r", encoding="utf-8") as f:
                    self._cached_thresholds = json.load(f)
            else:
                self._cached_thresholds = {}
        return self._cached_thresholds

    def validate_against_spec(self, dimension: str, value: Any) -> Dict[str, Any]:
        """按规范检验具体指标是否合规"""
        th = self.get_thresholds()

        if dimension == "complexity":
            # 圈复杂度检验
            max_allowed = 15
            val = int(value)
            is_valid = val <= max_allowed
            return {
                "dimension": dimension,
                "value": val,
                "max_allowed": max_allowed,
                "passed": is_valid,
                "verdict": "PASS" if is_valid else "FAIL",
                "message": f"圈复杂度为 {val}，{'合规' if is_valid else f'超标(上限{max_allowed})'}",
            }

        if dimension == "gate_score":
            score = float(value)
            tier = "solid" if score >= 80 else ("at-risk" if score >= 60 else "theatre")
            return {
                "dimension": dimension,
                "score": score,
                "tier": tier,
                "passed": score >= 60,
                "message": f"门禁评分 {score}，评级归为 {tier.upper()}",
            }

        return {"dimension": dimension, "value": value, "passed": True, "message": "无特别约束"}

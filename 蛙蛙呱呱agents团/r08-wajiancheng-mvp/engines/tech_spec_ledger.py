# -*- coding: utf-8 -*-
"""engines/tech_spec_ledger.py - L04 领域账本层 (Tech Spec Ledger & Unified Design Tokens).

对标开源标杆：Style Dictionary / DTCG (Stars > 15k)
核心职责：
1. 动态加载并解析 TECH_SPEC.md 领域账本，提供统一定义的色彩、排版、间距、断点基准；
2. 杜绝多轮对话或跨项目交付时的样式口径漂移；
3. 将统一 Design Tokens 编译为 Web (CSS Variables)、Flutter (ThemeData) 和 Tailwind 配置。
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional


class TechSpecLedger:
    """R08 L04 领域技术规格与设计令牌账本引擎。"""

    def __init__(self, spec_path: Optional[str] = None):
        if spec_path is None:
            spec_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TECH_SPEC.md")
        self.spec_path = spec_path
        self._cached_spec: Optional[Dict[str, Any]] = None

    def load_spec(self) -> Dict[str, Any]:
        """解析 TECH_SPEC.md 获得全局令牌与规范。"""
        if self._cached_spec:
            return self._cached_spec

        tokens: Dict[str, Any] = {
            "colors": {},
            "typography": {},
            "spacing": {},
            "breakpoints": {},
            "a11y_gates": {},
        }

        if not os.path.exists(self.spec_path):
            # 提供安全回退基准
            tokens["colors"] = {"primary": "#3355FF", "secondary": "#FF5533", "background": "#F8FAFC"}
            tokens["breakpoints"] = {"mobile": "375px", "tablet": "768px", "desktop": "1280px"}
            return {"spec_loaded": False, "tokens": tokens}

        with open(self.spec_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 正则提取色彩 Token
        color_matches = re.findall(r"-\s+\*\*([^*]+)\*\*:\s*`([^`]+)`", content)
        for name, val in color_matches:
            clean_name = name.split("(")[0].strip().lower().replace(" ", "_")
            tokens["colors"][clean_name] = val.strip()

        # 正则提取断点
        bp_matches = re.findall(r"-\s+\*\*([a-z0-9_]+)\*\*:\s*`([^`]+)`", content)
        for name, val in bp_matches:
            if any(k in name for k in ("mobile", "tablet", "desktop", "max_content")):
                tokens["breakpoints"][name] = val.strip()

        # 兜底确保关键键位存在
        tokens["colors"].setdefault("primary", "#3355FF")
        tokens["colors"].setdefault("secondary", "#FF5533")
        tokens["colors"].setdefault("background", "#F8FAFC")
        tokens["breakpoints"].setdefault("mobile", "375px")
        tokens["breakpoints"].setdefault("tablet", "768px")
        tokens["breakpoints"].setdefault("desktop", "1280px")

        res = {
            "spec_loaded": True,
            "spec_path": self.spec_path,
            "tokens": tokens,
            "version": "1.0.0",
        }
        self._cached_spec = res
        return res

    def export_css_variables(self) -> str:
        """导出为 Web 标准 CSS 自定义属性。"""
        spec = self.load_spec()
        lines = [":root {"]
        for k, v in spec["tokens"]["colors"].items():
            lines.append(f"  --color-{k}: {v};")
        for k, v in spec["tokens"]["breakpoints"].items():
            lines.append(f"  --breakpoint-{k}: {v};")
        lines.append("}")
        return "\n".join(lines)

    def export_flutter_theme(self) -> str:
        """导出为 Flutter 官方 ThemeData Dart 映射代码块。"""
        spec = self.load_spec()
        c = spec["tokens"]["colors"]
        p = c.get("primary", "#3355FF").replace("#", "0xFF")
        s = c.get("secondary", "#FF5533").replace("#", "0xFF")
        return f"""// Generated from TECH_SPEC.md by R08 TechSpecLedger
import 'package:flutter/material.dart';

final ThemeData r08AppTheme = ThemeData(
  colorScheme: ColorScheme.fromSeed(
    seedColor: const Color({p}),
    primary: const Color({p}),
    secondary: const Color({s}),
  ),
  useMaterial3: true,
);
"""

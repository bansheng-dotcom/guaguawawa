# -*- coding: utf-8 -*-
"""engines/spec_ledger.py - R10 视觉设计官 · L04 领域设计账本层 (Design Spec Ledger).

对标 VoltAgent/awesome-design-md 与 google-labs-code/design.md (Stars > 15k)：
1. 加载并解析设计规范唯一可信源 (SSOT) `DESIGN.md`；
2. 提取并管理语义化 Design Tokens（色彩、网格排版、安全留白、字阶规范）；
3. 提供向跨端生态（CSS Variables、Flutter Theme、JSON Tokens）的确定性一键导出。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.dirname(HERE)
DEFAULT_SPEC_PATH = os.path.join(AGENT_DIR, "DESIGN.md")


class DesignSpecLedger:
    """L04 设计系统规范账本。"""

    def __init__(self, spec_path: str = DEFAULT_SPEC_PATH):
        self.spec_path = spec_path
        self._cached_spec: Optional[Dict[str, Any]] = None

    def load_spec(self) -> Dict[str, Any]:
        """解析并返回结构化领域规范账本。"""
        if self._cached_spec:
            return self._cached_spec

        if not os.path.exists(self.spec_path):
            # 优雅降级默认规格
            spec = self._fallback_spec()
            self._cached_spec = spec
            return spec

        with open(self.spec_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 正则提取色彩 Token
        colors = {
            "primary": "#0F172A",
            "accent": "#22D3EE",
            "secondary": "#F43F5E",
            "text_light": "#F8FAFC",
            "text_muted": "#94A3B8",
            "card": "#1E293B",
        }
        hex_pattern = r"(#[0-9a-fA-F]{6})"
        for key in ["primary", "accent", "secondary"]:
            m = re.search(rf"color\.{key}.*?`{hex_pattern}`", content)
            if m:
                colors[key] = m.group(1)

        m_light = re.search(rf"color\.text\.light.*?`{hex_pattern}`", content)
        if m_light:
            colors["text_light"] = m_light.group(1)
        m_muted = re.search(rf"color\.text\.muted.*?`{hex_pattern}`", content)
        if m_muted:
            colors["text_muted"] = m_muted.group(1)
        m_card = re.search(rf"color\.surface\.card.*?`{hex_pattern}`", content)
        if m_card:
            colors["card"] = m_card.group(1)

        # 纵横比提取
        aspect_ratios = ["1:1", "3:4", "9:16", "16:9"]
        # 反模式硬门禁提取
        anti_patterns = []
        for line in content.splitlines():
            if line.strip().startswith("* ❌") or line.strip().startswith("- ❌"):
                anti_patterns.append(line.replace("* ❌", "").replace("- ❌", "").strip())

        spec = {
            "version": "1.0.0",
            "role": "r10-wachengmei-design",
            "spec_file": self.spec_path,
            "tokens": {
                "colors": colors,
                "breakpoints": {"mobile": 375, "tablet": 768, "desktop": 1200},
                "aspect_ratios": aspect_ratios,
                "typography_scale": {
                    "display": ">=64px",
                    "heading": "32px-48px",
                    "body": "18px-24px",
                    "caption": "14px-16px"
                },
                "safe_margin": {
                    "top_empty_ratio": 0.25,
                    "bottom_empty_ratio": 0.20,
                    "subject_anchor": "center_or_golden_ratio"
                }
            },
            "anti_patterns": anti_patterns,
        }
        self._cached_spec = spec
        return spec

    def export_css_variables(self) -> str:
        """导出 CSS 变量代码。"""
        spec = self.load_spec()
        colors = spec["tokens"]["colors"]
        lines = [":root {"]
        for k, v in colors.items():
            lines.append(f"  --color-{k}: {v};")
        lines.append("  --safe-margin-top: 25%;")
        lines.append("  --safe-margin-bottom: 20%;")
        lines.append("}")
        return "\n".join(lines)

    def export_flutter_theme(self) -> str:
        """导出 Flutter ThemeData Dart 代码。"""
        spec = self.load_spec()
        colors = spec["tokens"]["colors"]
        p = colors["primary"].replace("#", "0xFF")
        a = colors["accent"].replace("#", "0xFF")
        return (
            "import 'package:flutter/material.dart';\n\n"
            "final r10Theme = ThemeData(\n"
            f"  primaryColor: const Color({p}),\n"
            f"  colorScheme: ColorScheme.dark(primary: const Color({p}), secondary: const Color({a})),\n"
            "  scaffoldBackgroundColor: const Color(0xFF0F172A),\n"
            ");"
        )

    def export_tokens_json(self) -> str:
        """导出标准 JSON Token 格式。"""
        return json.dumps(self.load_spec()["tokens"], ensure_ascii=False, indent=2)

    def _fallback_spec(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "role": "r10-wachengmei-design",
            "tokens": {
                "colors": {
                    "primary": "#0F172A", "accent": "#22D3EE", "secondary": "#F43F5E",
                    "text_light": "#F8FAFC", "text_muted": "#94A3B8", "card": "#1E293B"
                },
                "breakpoints": {"mobile": 375, "tablet": 768, "desktop": 1200},
                "aspect_ratios": ["1:1", "3:4", "9:16", "16:9"],
                "typography_scale": {"display": ">=64px", "heading": "32px-48px", "body": "18px-24px", "caption": "14px-16px"},
                "safe_margin": {"top_empty_ratio": 0.25, "bottom_empty_ratio": 0.20}
            },
            "anti_patterns": ["色彩失控", "过度高光", "AI假字", "主体融化"]
        }

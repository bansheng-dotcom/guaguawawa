# -*- coding: utf-8 -*-
"""DESIGN.md 设计账本解析与令牌约束引擎。

对标 VoltAgent/awesome-design-md 与 google-labs-code/design.md 规范标准：
将团队项目中的 DESIGN.md 解析为结构化的 Design System Tokens，供 LLM 扩写和排版渲染引擎使用。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DesignLedger:
    """结构化设计账本。"""
    raw_markdown: str = ""
    primary_color: str = "#0F172A"
    accent_color: str = "#22D3EE"
    secondary_color: str = "#F43F5E"
    text_light: str = "#F8FAFC"
    text_muted: str = "#94A3B8"
    card_color: str = "#1E293B"
    aspect_ratios: List[str] = field(default_factory=lambda: ["1:1", "3:4", "9:16", "16:9"])
    anti_patterns: List[str] = field(default_factory=list)
    safe_margin_rules: str = "top-25-percent-empty, bottom-20-percent-empty"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "colors": {
                "primary": self.primary_color,
                "accent": self.accent_color,
                "secondary": self.secondary_color,
                "text_light": self.text_light,
                "text_muted": self.text_muted,
                "card": self.card_color,
            },
            "aspect_ratios": self.aspect_ratios,
            "anti_patterns": self.anti_patterns,
            "safe_margin_rules": self.safe_margin_rules,
        }


class DesignLedgerParser:
    """DESIGN.md 提取器。"""

    @classmethod
    def load_ledger(cls, custom_path: Optional[str] = None) -> DesignLedger:
        search_paths = [
            custom_path,
            os.path.join(os.path.dirname(__file__), "..", "DESIGN.md"),
            os.path.join(os.path.dirname(__file__), "..", "..", "DESIGN.md"),
        ]
        target_path = None
        for p in search_paths:
            if p and os.path.exists(p):
                target_path = p
                break

        if not target_path:
            return DesignLedger()

        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()

        ledger = DesignLedger(raw_markdown=content)

        # 提取 Hex 颜色
        hex_pattern = r"(#[0-9a-fA-F]{6})"
        if "color.primary" in content:
            m = re.search(r"color\.primary.*?`" + hex_pattern, content)
            if m: ledger.primary_color = m.group(1)
        if "color.accent" in content:
            m = re.search(r"color\.accent.*?`" + hex_pattern, content)
            if m: ledger.accent_color = m.group(1)
        if "color.secondary" in content:
            m = re.search(r"color\.secondary.*?`" + hex_pattern, content)
            if m: ledger.secondary_color = m.group(1)

        # 提取 Anti-patterns 列表
        anti_lines = re.findall(r"❌\s*\*\*(.*?)\*\*", content)
        if anti_lines:
            ledger.anti_patterns = anti_lines

        return ledger


_cached_ledger: Optional[DesignLedger] = None


def get_design_ledger(reload: bool = False) -> DesignLedger:
    global _cached_ledger
    if _cached_ledger is None or reload:
        _cached_ledger = DesignLedgerParser.load_ledger()
    return _cached_ledger

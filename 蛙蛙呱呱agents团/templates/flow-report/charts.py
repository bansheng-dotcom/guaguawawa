# -*- coding: utf-8 -*-
"""flow 报告模板：图表层。通用图型来自 core.report_theme.chartkit。"""
from __future__ import annotations

from core.report_theme import chartkit as c


def hbar_demo() -> str:
    return c.hbar([("2016 年", 1358.4, "峰值"), ("2024 年", 414.5, ""),
                   ("2025 年", 354.9, "只剩 26.13%")],
                  unit="万千升", accent=2, note="来源：S01。")

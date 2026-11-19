# -*- coding: utf-8 -*-
"""report_kernel · 报告质量内核。

2026-11-15 产线收敛后，内核只做「结构与写作门禁」；
2026-11-16 增加四件默认动作，解决「能力有、交付不用」的最后一公里：
  - contract：开工前的验收契约（读者/决策/问题/截止/档位/签字）
  - specs：表/图规格推断（单位、对齐、涨跌色、合计行、参考线）
  - consistency：跨报告数字登记与冲突检查
  - series：趋势 ≥12 期、跨时点必须对齐
  - gate：交付门禁（契约/档位/深度/图卡/单位/manifest/来源/一致性）
"""
from . import structure  # noqa: F401
from . import contract, specs, consistency, series  # noqa: F401

__all__ = ["structure", "contract", "specs", "consistency", "series"]

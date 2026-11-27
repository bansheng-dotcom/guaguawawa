# -*- coding: utf-8 -*-
"""R07 产品工作流包：5 条工作流（discovery/prd/priority/acceptance/briefing）
+ 1 个经验门（experience），由 runner 统一编排。

设计约束（对齐升级方案 §10 / §17.2）：
  - 每条工作流只做一件事，产出一个可独立审计的 JSON 包；
  - 每个包自带 `gate`（`{ok, grade, checks, errors}`），未过门禁不得交接；
  - 纯标准库、确定性、不联网；时间只用于经验卡时效判断，且由输入 `as_of` 提供。
"""
from __future__ import annotations

from . import acceptance, briefing, discovery, experience, prd, priority, render, runner

WORKFLOWS = {
    "discovery": discovery,
    "prd": prd,
    "priority": priority,
    "acceptance": acceptance,
    "briefing": briefing,
    "experience": experience,
}

__all__ = ["WORKFLOWS", "acceptance", "briefing", "discovery", "experience",
           "prd", "priority", "render", "runner"]

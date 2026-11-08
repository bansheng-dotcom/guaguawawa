# -*- coding: utf-8 -*-
"""R02 七个能力域技能模块注册表。

能力全景 R02 七能力域 → 七个可独立执行、可确定性校验的技能：
  s01 schedule   工作拆解与排期（wbs/sprint/critpath）
  s02 capacity   容量与委派（check/delegate/split）
  s03 handoff    交接与验收追踪（package/accept/trace）
  s04 retro      复盘与事故分析（postmortem/grade/action）
  s05 process    流程与 SOP（sop/waste/meeting）
  s06 knowledge  知识运营（digest/entry/search）
  s07 portfolio  项目群与 Agent 编排（status/plan/graph）
"""
from __future__ import annotations

from . import (s01_schedule, s02_capacity, s03_handoff, s04_retro,
               s05_process, s06_knowledge, s07_portfolio)

SKILLS = [
    s01_schedule,
    s02_capacity,
    s03_handoff,
    s04_retro,
    s05_process,
    s06_knowledge,
    s07_portfolio,
]

# -*- coding: utf-8 -*-
"""R01 七个能力域技能模块注册表。

能力全景 R01 七能力域 + 编排器本体 → 七个可独立执行、可确定性校验的技能：
  s01 intent       意图识别与任务分级
  s02 decompose    跨部门拆解
  s03 decide       经营与硬决策
  s04 redteam      反方质询
  s05 companyos    公司 OS 与治理
  s06 decisionlog  决策留痕与复盘
  s07 boardroom    高层汇报与创始人陪练

（编排器本体 plan/status/run-all 保留在 agent.py，不属技能域。）
"""
from __future__ import annotations

from . import (s01_intent, s02_decompose, s03_decide, s04_redteam,
               s05_companyos, s06_decisionlog, s07_boardroom)

from . import s08_ev

SKILLS = [
    s01_intent,
    s02_decompose,
    s03_decide,
    s04_redteam,
    s05_companyos,
    s06_decisionlog,
    s07_boardroom,
    s08_ev,
]

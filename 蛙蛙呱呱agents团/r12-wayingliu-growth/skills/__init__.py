# -*- coding: utf-8 -*-
"""R12 九个能力域技能模块注册表。

能力全景 R12 九能力域 → 九个可独立执行、可确定性校验的技能：
  s01 diagnose   增长诊断与基线
  s02 loops      增长循环与自然获客
  s03 outreach   冷启动与外联
  s04 partner    红人与合作增长
  s05 launch     ASO 与发布
  s06 paid       付费投放与 CRO
  s07 retention  激活、留存与推荐
  s08 revops     归因与 RevOps
  s09 selfmedia  自媒体运营
"""
from __future__ import annotations

from . import (s01_diagnose, s02_loops, s03_outreach, s04_partner,
               s05_launch, s06_paid, s07_retention, s08_revops,
               s09_selfmedia)

from . import s10_ltv_cac

from . import s11_mmm

from . import s12_power

SKILLS = [
    s01_diagnose,
    s02_loops,
    s03_outreach,
    s04_partner,
    s05_launch,
    s06_paid,
    s07_retention,
    s08_revops,
    s09_selfmedia,
    s10_ltv_cac,
    s11_mmm,
    s12_power,
]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

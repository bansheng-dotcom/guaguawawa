# -*- coding: utf-8 -*-
"""R16 七个能力域技能模块注册表。

能力全景 R16 七能力域 → 七个可独立执行、可确定性校验的技能：
  s01 recruit      招聘与入职
  s02 people       人员与合同档案
  s03 attendance   考勤与休假
  s04 performance  绩效与目标
  s05 payroll      薪酬准备
  s06 expense      费用与福利业务
  s07 report       组织运营报表
"""
from __future__ import annotations

from . import (s01_recruit, s02_people, s03_attendance, s04_performance,
               s05_payroll, s06_expense, s07_report)

from . import s08_funnel

SKILLS = [
    s01_recruit,
    s02_people,
    s03_attendance,
    s04_performance,
    s05_payroll,
    s06_expense,
    s07_report,
    s08_funnel,
]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

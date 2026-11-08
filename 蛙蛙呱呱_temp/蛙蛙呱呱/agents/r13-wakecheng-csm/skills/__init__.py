# -*- coding: utf-8 -*-
"""R13 八个能力域技能模块注册表。

能力全景 R13 八能力域 → 八个可独立执行、可确定性校验的技能：
  s01 crm         客户与联系人管理
  s02 pipeline    销售管道
  s03 activity    销售活动与跟进
  s04 support     全渠道客服
  s05 voc         客户反馈与 VOC
  s06 health      客户健康与续约输入
  s07 knowledge   服务知识与升级
  s08 automation  客户运营自动化接口
"""
from __future__ import annotations

from . import (s01_crm, s02_pipeline, s03_activity, s04_support,
               s05_voc, s06_health, s07_knowledge, s08_automation)

SKILLS = [
    s01_crm,
    s02_pipeline,
    s03_activity,
    s04_support,
    s05_voc,
    s06_health,
    s07_knowledge,
    s08_automation,
]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

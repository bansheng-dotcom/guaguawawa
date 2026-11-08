# -*- coding: utf-8 -*-
"""R17 八个能力域技能模块注册表。

能力全景 R17 八能力域 → 八个可独立执行、可确定性校验的技能：
  s01 integration  SaaS/API 集成
  s02 webhook      Webhook 与事件处理
  s03 mapping      字段与身份映射
  s04 schedule     定时与批处理
  s05 approval     人工审批节点
  s06 retry        失败处理与重试
  s07 aiworkflow   AI 工作流接入
  s08 audit        自动化审计
"""
from __future__ import annotations

from . import (s01_integration, s02_webhook, s03_mapping, s04_schedule,
               s05_approval, s06_retry, s07_aiworkflow, s08_audit)

SKILLS = [
    s01_integration,
    s02_webhook,
    s03_mapping,
    s04_schedule,
    s05_approval,
    s06_retry,
    s07_aiworkflow,
    s08_audit,
]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

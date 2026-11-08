# -*- coding: utf-8 -*-
"""R20 七个能力域技能模块注册表。

能力全景 R20 七能力域 → 七个可独立执行、可确定性校验的技能：
  s01 monitor     可用性监控
  s02 alert       告警与升级
  s03 statuspage  状态页与事件沟通
  s04 backup      加密增量备份
  s05 restore     恢复演练
  s06 dr          灾难恢复与回滚接口
  s07 postmortem  运行复盘
"""
from __future__ import annotations

from . import (s01_monitor, s02_alert, s03_statuspage, s04_backup,
               s05_restore, s06_dr, s07_postmortem)

SKILLS = [
    s01_monitor,
    s02_alert,
    s03_statuspage,
    s04_backup,
    s05_restore,
    s06_dr,
    s07_postmortem,
]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

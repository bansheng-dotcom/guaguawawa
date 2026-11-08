# -*- coding: utf-8 -*-
"""R19 七个能力域技能模块注册表。

能力全景 R19 七能力域 → 七个可独立执行、可确定性校验的技能：
  s01 tracking     实验追踪
  s02 registry     模型注册与版本
  s03 evaluation   评估数据集与评分器
  s04 trace        Agent Trace 与调试
  s05 release      回归与发布候选
  s06 monitor      模型监控接口
  s07 modelcard    模型卡与资产说明
"""
from __future__ import annotations

from . import (s01_tracking, s02_registry, s03_evaluation, s04_trace,
               s05_release, s06_monitor, s07_modelcard)

SKILLS = [
    s01_tracking,
    s02_registry,
    s03_evaluation,
    s04_trace,
    s05_release,
    s06_monitor,
    s07_modelcard,
]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

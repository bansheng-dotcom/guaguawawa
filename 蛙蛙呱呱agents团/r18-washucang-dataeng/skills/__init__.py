# -*- coding: utf-8 -*-
"""R18 七个能力域技能模块注册表。

能力全景 R18 七能力域 → 七个可独立执行、可确定性校验的技能：
  s01 elt          数据连接与 ELT
  s02 transform    数仓转换
  s03 pipeline     管道调度与编排
  s04 quality      数据质量门禁
  s05 incremental  批流与增量边界
  s06 catalog      数据目录与口径接口
  s07 ops          人工审批与运维接口
"""
from __future__ import annotations

from . import (s01_elt, s02_transform, s03_pipeline, s04_quality,
               s05_incremental, s06_catalog, s07_ops)

SKILLS = [
    s01_elt,
    s02_transform,
    s03_pipeline,
    s04_quality,
    s05_incremental,
    s06_catalog,
    s07_ops,
]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

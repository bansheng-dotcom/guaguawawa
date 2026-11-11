# -*- coding: utf-8 -*-
"""R08 七个能力域技能模块注册表。

能力全景 R08 七能力域 → 七个可独立执行、可确定性校验的技能：
  s01 slice      产品切片与 MVP
  s02 scaffold   Spec 转仓库
  s03 landing    落地页与 H5
  s04 saas       SaaS 与邮件脚手架
  s05 prototype  跨平台原型
  s06 design     组件与设计实现
  s07 qa         质量验证与交接
"""
from __future__ import annotations

from . import (s01_slice, s02_scaffold, s03_landing, s04_saas,
               s05_prototype, s06_design, s07_qa, s08_deck)

SKILLS = [
    s01_slice,
    s02_scaffold,
    s03_landing,
    s04_saas,
    s05_prototype,
    s06_design,
    s07_qa,
    s08_deck,
]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}
# -*- coding: utf-8 -*-
"""R09 蛙稳码（代码工程官）技能清单。"""
from . import (s01_spec, s02_data_api, s03_fullstack, s04_crossplatform,
               s05_testing, s06_debug, s07_ops, s08_special, s09_eng_chain)

SKILLS = [s01_spec, s02_data_api, s03_fullstack, s04_crossplatform,
          s05_testing, s06_debug, s07_ops, s08_special, s09_eng_chain]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

# T7 工程链：与 8 个既有技能并列注册，动作面（10 段 + run/audit）进目录与提示词系统。
CHAIN = s09_eng_chain
CHAIN_ACTIONS = s09_eng_chain.ACTIONS

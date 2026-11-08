# -*- coding: utf-8 -*-
"""R09 蛙稳码（代码工程官）技能清单。"""
from . import (s01_spec, s02_data_api, s03_fullstack, s04_crossplatform,
               s05_testing, s06_debug, s07_ops, s08_special)

SKILLS = [s01_spec, s02_data_api, s03_fullstack, s04_crossplatform,
          s05_testing, s06_debug, s07_ops, s08_special]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

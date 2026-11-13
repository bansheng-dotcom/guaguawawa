# -*- coding: utf-8 -*-
"""R05 蛙深远（战略研究官）技能清单。"""
from . import (s01_research, s02_industry, s03_competitor, s04_business,
               s05_sizing, s06_scenario, s07_auto)

from . import s09_matched

from . import s10_tam_mc

SKILLS = [s01_research, s02_industry, s03_competitor, s04_business,
          s05_sizing, s06_scenario, s07_auto, s09_matched,
    s10_tam_mc,
]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

# -*- coding: utf-8 -*-
"""R04 蛙挑刺（独立评审官）技能清单。"""
from . import s01_artifact
from . import s02_gate
from . import s03_criteria
from . import s04_quality
from . import s05_facts
from . import s06_strengths
from . import s07_human

SKILLS = [s01_artifact, s02_gate, s03_criteria, s04_quality,
          s05_facts, s06_strengths, s07_human]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

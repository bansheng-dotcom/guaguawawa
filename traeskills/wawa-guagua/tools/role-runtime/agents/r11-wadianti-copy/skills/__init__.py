# -*- coding: utf-8 -*-
"""R11 八个能力域技能模块注册表。

能力全景 R11 八能力域 → 八个可独立执行、可确定性校验的技能：
  s01 topic      内容策略与选题
  s02 seo        SEO/AEO 与搜索发现
  s03 hook       钩子、提纲与立场
  s04 copy       文案与长文
  s05 voice      品牌语调与编辑
  s06 pr         广告、公关与新闻稿
  s07 platform   多平台适配
  s08 localize   持续本地化
"""
from __future__ import annotations

from . import (s01_topic, s02_seo, s03_hook, s04_copy,
               s05_voice, s06_pr, s07_platform, s08_localize, s11_xhs)

SKILLS = [
    s01_topic,
    s02_seo,
    s03_hook,
    s04_copy,
    s05_voice,
    s06_pr,
    s07_platform,
    s08_localize,
    s11_xhs,
]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

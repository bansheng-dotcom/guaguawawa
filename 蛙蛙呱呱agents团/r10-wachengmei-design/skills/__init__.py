# -*- coding: utf-8 -*-
"""R10 八个能力域技能模块注册表。

能力全景 R10 八能力域 → 八个可独立执行、可确定性校验的技能：
  s01 imagegen     AI 生图与插画
  s02 logo         Logo、图标与品牌 VI
  s03 uiux         产品与 UI/UX
  s04 brand        品牌 VI 与设计令牌
  s05 motion       交互原型与动效
  s06 imaging      修图与图像工程
  s07 media        视频与音频处理
  s08 transcribe   转写与字幕素材
"""
from __future__ import annotations

from . import (s01_imagegen, s02_logo, s03_uiux, s04_brand,
               s05_motion, s06_imaging, s07_media, s08_transcribe,
               s09_render, s11_designsys, s12_aihive, s13_h3prompt)

SKILLS = [
    s01_imagegen,
    s02_logo,
    s03_uiux,
    s04_brand,
    s05_motion,
    s06_imaging,
    s07_media,
    s08_transcribe,
    s09_render,
    s11_designsys,
    s12_aihive,
    s13_h3prompt,
]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

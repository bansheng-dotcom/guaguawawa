# -*- coding: utf-8 -*-
"""R07 八个能力域技能模块注册表。"""
from __future__ import annotations

from . import (s01_discover, s02_ost, s03_prd, s04_priority,
               s05_roadmap, s06_metrics, s07_techbrief, s08_decision)

SKILLS = [s01_discover, s02_ost, s03_prd, s04_priority,
          s05_roadmap, s06_metrics, s07_techbrief, s08_decision]

# 兼容历史技能模块：统一补齐注册元数据。
_MODULE_META = {
    s01_discover: ("discover", "产品发现与 JTBD"),
    s02_ost: ("ost", "机会树与用户研究"),
    s03_prd: ("prd", "用户故事与 PRD"),
    s04_priority: ("priority", "优先级与 Backlog"),
    s05_roadmap: ("roadmap", "路线图与发布"),
    s06_metrics: ("metrics", "产品愿景与指标"),
    s07_techbrief: ("techbrief", "技术翻译与代码反推需求"),
    s08_decision: ("decision", "经验检索与决策汇报"),
}
for _module, (_name, _desc) in _MODULE_META.items():
    _module.NAME = getattr(_module, "NAME", _name)
    _module.DESC = getattr(_module, "DESC", _desc)

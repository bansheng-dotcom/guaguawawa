# -*- coding: utf-8 -*-
"""R06 蛙得清 · 九个独立技能模块的注册表。

每个技能模块暴露统一接口：
    NAME(str)                    子命令名
    HEAP / DESC(str)             一句话说明
    add_parser(subparsers)       向 CLI 注册子命令
    run(args) -> dict            执行，返回可 JSON 化的结果

调度器 agent.py 只 import 这一份 SKILLS 清单，不关心内部实现；
新增/删除技能只需改这里，dispatcher 与协作入口自动跟随。
"""
from __future__ import annotations

from . import s01_semantics
from . import s02_quality
from . import s03_explore
from . import s04_rootcause
from . import s05_describe
from . import s05_correlate
from . import s05_ttest
from . import s05_chi2
from . import s05_anova
from . import s05_regression
from . import s05_abtest
from . import s05_power
from . import s05_causal
from . import s05_matched
from . import s05_did
from . import s05_elasticity
from . import s06_scinlp
from . import s07_domain
from . import s08_viz
from . import s09_selfmedia

# 顺序即「能力域顺序」，与能力全景 R06 的九能力域一致；
# 能力域 5（统计）按来源技能粒度拆成 7 个单功能模块。
from . import s05_rdd

SKILLS = [
    s01_semantics,
    s02_quality,
    s03_explore,
    s04_rootcause,
    s05_describe,
    s05_correlate,
    s05_ttest,
    s05_chi2,
    s05_anova,
    s05_regression,
    s05_abtest,
    s05_power,
    s05_causal,
    s05_matched,
    s05_did,
    s05_elasticity,
    s06_scinlp,
    s07_domain,
    s08_viz,
    s09_selfmedia,
    s05_rdd,
]
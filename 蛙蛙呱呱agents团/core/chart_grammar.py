# -*- coding: utf-8 -*-
"""兼容层（P4 第三阶段）：实现已迁至 core.charts.chart_grammar。

用 sys.modules 别名保持模块身份一致。
迁移全部完成后统一删除本文件。
"""
import sys as _sys

from core.charts import chart_grammar as _impl

_sys.modules[__name__] = _impl

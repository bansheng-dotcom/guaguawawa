"""core.charts —— 图表层（P4 第三阶段：已物理归位）。

原有 3 个渲染器 + 13 个 `chart_*.py` 现在都在本包内；旧路径 `core/chart_*.py`
保留一版兼容 shim。对外仍可按需访问：

    from core.charts import chart_grammar
    from core.charts import chart_lib

不 import 任何子模块直到被访问（懒加载），避免循环依赖。
"""
from __future__ import annotations

import importlib

__all__ = [
    "chart_lib", "chart_renderers_ext", "consulting",
    "chart_grammar", "chart_chooser", "chart_relation", "chart_candidates",
    "chart_payload", "chart_query", "chart_shapes", "chart_spec",
    "chart_contract", "chart_plan", "chart_units", "chart_capabilities",
    "chart_field_contract",
]


def __getattr__(name):
    if name in __all__:
        return importlib.import_module("core.charts." + name)
    raise AttributeError(
        "core.charts 没有 %r；可用：%s" % (name, ", ".join(__all__)))


def __dir__():
    return sorted(__all__)

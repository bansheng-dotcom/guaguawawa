"""core.charts —— 图表层（逻辑分组入口，物理不动）。

`core/charts/` 本来只有 3 个渲染器；图表相关的 12 个 `chart_*.py` 仍平铺在
`core/` 下。本文件把它们**按层聚合**，对外提供统一入口：

    from core.charts import chart_grammar      # == core.chart_grammar
    from core.charts import chart_query        # == core.chart_query
    from core.charts import chart_lib          # == core.charts.chart_lib

不 import 任何模块直到被访问（懒加载）。完整分层见 docs/CORE-MAP.md。
"""
from __future__ import annotations

import importlib
import sys

# 本包内的真子模块
_LOCAL = ("chart_lib", "chart_renderers_ext", "consulting")

# 平铺在 core/ 下、逻辑上属于图表层的 12 个模块
_ROOT = (
    "chart_grammar", "chart_chooser", "chart_relation", "chart_candidates",
    "chart_payload", "chart_query", "chart_shapes", "chart_spec",
    "chart_contract", "chart_plan", "chart_units", "chart_capabilities",
)

__all__ = list(_LOCAL) + list(_ROOT)


def __getattr__(name):
    if name in _LOCAL:
        return importlib.import_module("core.charts." + name)
    if name in _ROOT:
        mod = importlib.import_module("core." + name)
        # 登记别名：让 `import core.charts.chart_grammar` 在首次访问后也可用
        sys.modules.setdefault("core.charts." + name, mod)
        return mod
    raise AttributeError(
        "core.charts 没有 %r；可用：%s" % (name, ", ".join(__all__)))


def __dir__():
    return sorted(__all__)

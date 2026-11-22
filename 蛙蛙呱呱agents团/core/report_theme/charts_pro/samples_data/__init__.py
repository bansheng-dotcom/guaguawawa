# -*- coding: utf-8 -*-
"""samples_data —— 图表示例数据（内蒙古口径）的隔离区。

2026-11-22 迁移：`core/charts/dataset.py` 与 `charts_pro/geo.py` 原来是散在
渲染器目录里的历史项目样例数据。现在统一收进本子包，渲染器逻辑与样例数据分开。

**注意**：这不是"迁出 core"的终态——pk_b1..b4 / prokit2 / spec_space 仍是
样例渲染器，要彻底迁出需要把它们一起搬到 `examples/`，并让渲染器把样例数据
当参数传入。本次先做"隔离"，把那一步留给专项。
"""

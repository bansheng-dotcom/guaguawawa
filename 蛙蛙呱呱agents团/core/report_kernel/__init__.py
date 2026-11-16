# -*- coding: utf-8 -*-
"""report_kernel · 版式与写作门禁（唯一实现）。

2026-11-15 产线收敛后，内核只剩「结构门禁」这一件事：
  - 四条版式硬规则 R1—R4（首屏无分数 / 末节口径与分数 / 附录折叠 / 无重复章节）
  - 四条写作判据（指标带业务化 / 每节带数字 / 结论带数字 / 字段回显）

spec / layers / aggregate / guard 已随 20 角色报告产线一并删除；
报告只剩一条产线（core/report_flow.py），由 R01 出具。
"""
from . import structure  # noqa: F401

__all__ = ["structure"]

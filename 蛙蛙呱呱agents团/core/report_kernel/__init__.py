# -*- coding: utf-8 -*-
"""report_kernel · 统一报告内核（20 角色共用）。

对外暴露五件事：
  spec.load(role)            → 合并后的有效规格
  layers.build_contract(...) → 三层 contract（兼容 report_renderer）
  guard.ContractCache        → contract 级缓存
  aggregate.build_l2/l3      → 跨域汇总与评审
  structure.guard(...)       → 六条结构门禁；结构 → contract；四条版式规则
"""
from . import aggregate, guard, layers, spec, structure  # noqa: F401

__all__ = ["spec", "layers", "guard", "aggregate", "structure"]

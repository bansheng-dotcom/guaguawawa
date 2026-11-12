# -*- coding: utf-8 -*-
"""report_kernel · 统一报告内核（20 角色共用）。

对外只暴露四件事：
  spec.load(role)            → 合并后的有效规格
  layers.build_contract(...) → 三层 contract（兼容 report_renderer）
  guard.ContractCache        → contract 级缓存
  aggregate.build_l2/l3      → 跨域汇总与评审
"""
from . import aggregate, guard, layers, spec  # noqa: F401

__all__ = ["spec", "layers", "guard", "aggregate"]

# -*- coding: utf-8 -*-
"""兼容层（P4 第一阶段）：实现已迁至 core.base.workspace。

保留旧路径供现有 import 使用；迁移验证后统一删除。
"""
from core.base import workspace as _impl  # noqa: F401

for _k, _v in vars(_impl).items():
    if not _k.startswith("__"):
        globals()[_k] = _v

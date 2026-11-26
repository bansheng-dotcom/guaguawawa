# -*- coding: utf-8 -*-
"""兼容层（P4 第四阶段）：实现已迁至 core.claims.cells_unified。

用 sys.modules 别名保持模块身份一致。
迁移全部完成后统一删除本文件。
"""
import sys as _sys

from core.claims import cells_unified as _impl

_sys.modules[__name__] = _impl

# -*- coding: utf-8 -*-
"""兼容层（P4）：实现已迁至 core.sources.supply_plan。

用 sys.modules 别名保持模块身份一致：monkeypatch / 模块级状态仍然作用在实现模块上。
迁移全部完成后统一删除本文件。
"""
import sys as _sys

from core.sources import supply_plan as _impl

_sys.modules[__name__] = _impl

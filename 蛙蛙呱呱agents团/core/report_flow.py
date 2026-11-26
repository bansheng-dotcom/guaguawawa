# -*- coding: utf-8 -*-
"""兼容层（P4 第六阶段）：实现已迁至 core.report.report_flow。

用 sys.modules 别名保持模块身份一致；`python -m core.report_flow` 转发 main()。
迁移全部完成后统一删除本文件。
"""
import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from core.report import report_flow as _impl

_sys.modules[__name__] = _impl

if __name__ == "__main__":
    raise SystemExit(_impl.main())

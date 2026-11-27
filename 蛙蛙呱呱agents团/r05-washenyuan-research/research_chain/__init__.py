# -*- coding: utf-8 -*-
"""R05 研究链：scope → source → collect → verify → triangulate → size → compete → report。

对外只暴露两个入口：
- `run_fixture(fixture, out_dir)`：一条命令跑完 8 段并写 manifest；
- `audit(out_dir)`：复核已落盘产物的 sha256 与全部门禁。
"""
from .runner import audit, cross_checks, run_fixture

__all__ = ["run_fixture", "audit", "cross_checks"]

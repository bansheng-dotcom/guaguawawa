# -*- coding: utf-8 -*-
"""全角色共享引擎实现（T0 收敛层）。

现状（2026-11-27 实测）：
  - 9 类“通用引擎”在 20 个角色间共有 143 个副本；
  - 只有 telemetry_watchdog 存在近似副本（r11/r12 相似度 0.974），已收敛到这里；
  - 其余 7 类同名文件相似度 0.33–0.90，含角色专属语义，合并需单独评审，
    因此先登记为 domain_variant，并由 `scripts/check_engine_variants.py` 冻结哈希，
    禁止再新增未登记副本。

新代码接入规则：
  1. 能复用 → `from shared.engines.<name> import <Class>`；
  2. 确需角色差异 → 在角色 engines/ 下写薄适配器（继承/别名），不要复制整份实现；
  3. 新增或修改角色引擎后，运行 `python scripts/check_engine_variants.py --write`
     更新台账，再提交。
"""
from .telemetry_watchdog import (  # noqa: F401
    ContentTelemetryWatchdog,
    GrowthTelemetryWatchdog,
    TelemetryWatchdog,
)

__all__ = ["TelemetryWatchdog", "ContentTelemetryWatchdog", "GrowthTelemetryWatchdog"]

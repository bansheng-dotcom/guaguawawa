# -*- coding: utf-8 -*-
"""r11 适配器：L10 遥测看门狗实现已收敛到 shared.engines.telemetry_watchdog。

保留类名 ContentTelemetryWatchdog 供角色内 import 使用，不再复制整份实现。
"""
from __future__ import annotations

from shared.engines.telemetry_watchdog import (  # noqa: F401
    ContentTelemetryWatchdog,
    TelemetryWatchdog,
)

__all__ = ["ContentTelemetryWatchdog", "TelemetryWatchdog"]

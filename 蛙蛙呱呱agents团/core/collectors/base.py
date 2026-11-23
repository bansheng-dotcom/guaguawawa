# -*- coding: utf-8 -*-
"""core.collectors —— 采集器（SYSTEM-UPGRADE-SOP v3.1 · S2）。

每个源一个采集器；采集器**不认识业务词**，只认 `spec.query` 里的参数。

约定：
    fetch(spec) -> list[dict]     返回原子行
    每行必须包含 source.atomic_grain 的全部列
"""
from __future__ import annotations

from typing import Any, Dict, List, Protocol


class Collector(Protocol):
    name: str

    def fetch(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        ...


_REGISTRY: Dict[str, Any] = {}


def register(cls):
    _REGISTRY[getattr(cls, "name", cls.__name__)] = cls
    return cls


def get(name: str):
    return _REGISTRY.get(str(name))


def names() -> List[str]:
    return sorted(_REGISTRY)

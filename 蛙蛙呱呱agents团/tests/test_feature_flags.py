# -*- coding: utf-8 -*-
"""P9：feature flags 的最基本行为。"""
from __future__ import annotations

import pytest

from core import report_build


def test_engine_v8_is_rejected(monkeypatch):
    monkeypatch.setenv("REPORT_ENGINE", "v8")
    with pytest.raises(ValueError):
        report_build.build("x", "x", "x")

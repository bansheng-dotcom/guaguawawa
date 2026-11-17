# -*- coding: utf-8 -*-
"""Quote 正/负样本 fixture：strict 必须放行/拦截。"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from core import report_flow, research_intake as ri

FIX = Path(__file__).resolve().parent / "fixtures"


def _copy(tmp_path, name):
    dst = tmp_path / name
    shutil.copytree(FIX / name, dst)
    return dst


def test_quote_ok_fixture_strict_passes(tmp_path):
    p = _copy(tmp_path, "quote_ok_project")
    out = ri.quote_gate(str(p), refs=["S01", "S02"], mode="strict")
    assert out["ok"] is True
    assert out["used_unverified"] == []
    assert out["ok_count"] == 2


def test_quote_gap_fixture_strict_blocks(tmp_path):
    p = _copy(tmp_path, "quote_gap_project")
    with pytest.raises(report_flow.FlowError):
        ri.quote_gate(str(p), refs=["S01", "S02"], mode="strict")

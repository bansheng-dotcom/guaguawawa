# -*- coding: utf-8 -*-
"""P13：正文可比切片节。"""
from __future__ import annotations

from core import report_compose


def test_add_slice_section_inserts_comparable_section():
    secs = [{"title": "宽口径：3 个", "refs": ["E1", "E2", "E3"],
             "reading": [{"text": "a", "refs": ["E1"]},
                         {"text": "b", "refs": ["E2"]}]}]
    pack = {"numbers": [
        {"id": "E1", "period": "2026-11-01", "unit": "元"},
        {"id": "E2", "period": "2026-11-01", "unit": "元"},
        {"id": "E3", "period": "2026-10-01", "unit": "%"},
    ]}
    assert report_compose._add_slice_section(secs, pack) is True
    assert len(secs) == 2
    assert secs[1]["slice"]["n"] == 2
    assert secs[1]["slice"]["period"] == "2026-11-01"
    assert secs[1]["refs"] == ["E1", "E2"]

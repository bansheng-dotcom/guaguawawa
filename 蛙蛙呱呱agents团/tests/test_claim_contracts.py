# -*- coding: utf-8 -*-
"""P8b 数据契约：计数 / 假设 / 公式。"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
SKILLS = TEAM / "r01-waquanju-ceo" / "skills"
_pkg = types.ModuleType("skills")
_pkg.__path__ = [str(SKILLS)]  # type: ignore[attr-defined]
sys.modules.setdefault("skills", _pkg)
_SPEC = importlib.util.spec_from_file_location(
    "skills.s09_interpret", SKILLS / "s09_interpret.py")
s09 = importlib.util.module_from_spec(_SPEC)
sys.modules["skills.s09_interpret"] = s09
_SPEC.loader.exec_module(s09)  # type: ignore[union-attr]

PACK = {"numbers": [{"id": "A1", "name": "数值", "value": 1, "unit": "元",
                     "period": "2025", "source_file": "x.json"}]}


def _draft(reading: str, assumptions=None, records=None):
    return {"standfirst": "测试 1 元",
            "sections": [{"title": "测试：1 元", "question": "q", "refs": ["A1"],
                          "reading": [{"text": reading, "refs": ["A1"]},
                                      {"text": "口径说明", "refs": ["A1"]}],
                          "assumptions": assumptions or []}],
            "counts": {"n": 2},
            "assumption_records": records or []}


def _sections_check(draft):
    return next(x for x in s09._check_sections(draft, PACK)
                if x["id"] == "sections_valid")


def test_count_registry_allows_registered_only():
    ok = _sections_check(_draft("2 个"))
    assert ok["ok"] is True, ok
    bad = _sections_check(_draft("29 个"))
    assert bad["ok"] is False
    assert "29" in str(bad)


def test_assumption_requires_source():
    bad = _sections_check(_draft("7.7 元", assumptions=[7.7]))
    assert bad["ok"] is False
    good = _sections_check(
        _draft("7.7 元", assumptions=[7.7],
               records=[{"value": 7.7, "source": "method:economics"}]))
    assert good["ok"] is True, good


def test_no_arbitrary_ratio():
    refs = [{"value": 1}, {"value": 2}]
    assert s09._explainable(1.0, refs) is True
    assert s09._explainable(0.5, refs) is False       # 1/2 不再放行
    assert s09._explainable(3.0, refs) is True        # 1+2 仍允许

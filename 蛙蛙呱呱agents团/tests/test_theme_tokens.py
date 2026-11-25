# -*- coding: utf-8 -*-
"""P5：设计 token 默认值 = 现状；表格降级可访问。"""
from __future__ import annotations

import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core import data_standard as ds  # noqa: E402
from core.report_theme import table_backend, tokens  # noqa: E402


def _dataset():
    obs = [ds.Observation(metric_id="m", entity=e, period="2025", value=v, unit="元")
           for e, v in (("甲", 1.0), ("乙", 2.0))]
    d = ds.Dataset(name="示例", grain=["entity", "period"], observations=obs)
    d.profile = ds.profile_observations(obs)
    return d


def test_default_tokens_match_renderer():
    assert tokens.verify_defaults_match_renderer() == []


def test_load_theme_overrides_color(tmp_path):
    p = tmp_path / "theme.yaml"
    p.write_text("color:\n  accent: '#0055AA'\n", encoding="utf-8")
    tk = tokens.load(p)
    assert tk["color"]["accent"] == "#0055AA"
    assert tk["color"]["ink"] == tokens.DEFAULT_TOKENS["color"]["ink"]


def test_css_vars_contains_tokens():
    css = tokens.css_vars()
    assert "--chart-ink:" in css and css.startswith(":root{")


def test_table_backend_is_accessible():
    html = table_backend.render_table(_dataset())
    assert "<table" in html and "<caption>" in html
    assert 'scope="col"' in html and "甲" in html


def test_fallback_note_explains_missing_precondition():
    fit = {"candidates": [{"type": "heatmap", "fallback": "table",
                           "preconditions": {"ok": False,
                                             "missing": ["交叉维度超过 12 档"]}}]}
    note = table_backend.fallback_note(fit, "heatmap")
    assert "交叉维度超过 12 档" in note and "table" in note

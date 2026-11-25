# -*- coding: utf-8 -*-
"""P4-3：Layout 层在 70 型渲染前统一接管空态/值域/刻度/精度。"""
from __future__ import annotations

import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core.report_theme.charts_pro import layout, spec  # noqa: E402

try:
    from samples import samples  # noqa: PLC0415
except Exception:  # noqa: BLE001
    samples = None

KINDS = spec.kinds()
NUMERIC_REQ = {"start", "low", "high", "value", "target"}


def test_every_kind_gets_layout():
    if samples is None:
        return
    for t in KINDS:
        prepared = layout.prepare(dict(samples.SAMPLE[t], type=t))
        lay = prepared[layout.LAYOUT_KEY]
        assert lay["type"] == t
        assert isinstance(lay["decimals"], int)
        assert lay["domain"][0] <= 0 <= lay["domain"][1]
        assert lay["tick"] > 0
        assert prepared["decimals"] == lay["decimals"]
        assert "required" in lay and lay["required"] == list(spec.REQUIRED[t])


def test_every_kind_renders_through_layout():
    if samples is None:
        return
    for t in KINDS:
        svg = spec.render(dict(samples.SAMPLE[t], type=t))
        assert "<svg" in svg and "</svg>" in svg, t


def test_empty_state_is_uniform_across_kinds():
    checked = 0
    for t in KINDS:
        req = list(spec.REQUIRED[t])
        if any(k in NUMERIC_REQ for k in req):
            continue          # 数值必填型（gauge 等）不适用「空列表」语义
        empty = {k: ([] if req else None) for k in req}
        out = spec.render({"type": t, **empty})
        assert "<svg" in out and "无数据" in out, t
        checked += 1
    assert checked >= 60      # 绝大多数图型都应走统一空态


def test_negative_domain_is_injected():
    p = layout.prepare({"type": "hbar",
                        "items": [{"label": "a", "value": -5},
                                  {"label": "b", "value": 3}]})
    lay = p[layout.LAYOUT_KEY]
    assert lay["negative"] is True
    assert lay["domain"][0] < 0 <= lay["domain"][1]
    assert p["domain"] == tuple(lay["domain"])


def test_flat_values_flagged():
    p = layout.prepare({"type": "line",
                        "points": [{"label": "a", "value": 2},
                                   {"label": "b", "value": 2}]})
    assert p[layout.LAYOUT_KEY]["flat"] is True


def test_alias_gets_layout_for_real_type():
    p = layout.prepare({"type": "share", "items": [{"label": "a", "value": 1}]})
    assert p["type"] == "share_bar"
    assert p[layout.LAYOUT_KEY]["type"] == "share_bar"

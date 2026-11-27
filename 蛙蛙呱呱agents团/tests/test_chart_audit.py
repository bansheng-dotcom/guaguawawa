# -*- coding: utf-8 -*-
"""T10：48 型图表六维审计 + 黄金 SVG 回归。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from chart_audit_cases import cases  # noqa: E402
from core.charts.audit import audit, audit_many, level_of  # noqa: E402
from core.charts.chart_capabilities import CATALOG  # noqa: E402
from core.report_theme.charts_pro import spec  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "charts"


def _render(key: str, payload: dict) -> str:
    title = next((c["title"] for c in CATALOG if c["key"] == key), key)
    return spec.render({**payload, "type": key, "title": title})


def test_catalog_has_48_levels():
    assert len(CATALOG) == 48
    levels = {c["key"]: c.get("level") for c in CATALOG}
    assert all(v in ("quick", "guided") for v in levels.values())
    assert any(v == "quick" for v in levels.values())
    assert any(v == "guided" for v in levels.values())
    assert level_of("line") == "quick"
    assert level_of("candlestick") == "guided"


def test_all_48_types_pass_audit():
    rows = []
    for key, payload in cases().items():
        svg = _render(key, payload)
        rows.append((key, payload, svg))
    assert len(rows) == 48
    report = audit_many(rows)
    assert report["ok"], report["failed"]


def test_golden_svgs_exist_and_pass():
    missing = [c["key"] for c in CATALOG if not (FIXTURES / f"{c['key']}.svg").is_file()]
    assert not missing, f"缺黄金 SVG：{missing}"
    cs = cases()
    for c in CATALOG:
        key = c["key"]
        svg = (FIXTURES / f"{key}.svg").read_text(encoding="utf-8")
        r = audit(key, cs[key], svg)
        assert r["ok"], (key, [x["msg"] for x in r["checks"] if not x["ok"]])


@pytest.mark.parametrize("key,payload,check_id", [
    ("pie", {"items": [{"label": str(i), "value": 1} for i in range(7)]}, "chart_fit"),
    ("waterfall", {"start": 10, "deltas": [{"label": "a", "value": 3}], "end": 20},
     "calc_correct"),
    ("funnel", {"stages": [{"label": "a", "value": 10},
                           {"label": "b", "value": 12}]}, "calc_correct"),
    ("candlestick", {"ohlc": [{"label": "D1", "o": 10, "h": 9, "l": 8, "c": 11}]},
     "calc_correct"),
])
def test_misuse_is_blocked(key, payload, check_id):
    r = audit(key, payload, _render(key, payload))
    failed = {c["id"] for c in r["checks"] if not c["ok"]}
    assert check_id in failed
    assert not r["ok"]


def test_empty_and_gradient_blocked():
    r = audit("line", {}, "")
    assert not r["ok"]
    svg = '<svg viewBox="0 0 10 10"><style>.x{background:linear-gradient(#fff,#000)}</style>' \
          '<text x="1" y="2">a</text></svg>'
    r2 = audit("line", {"points": [{"label": "a", "value": 1},
                                   {"label": "b", "value": 2},
                                   {"label": "c", "value": 3}]}, svg)
    assert not r2["ok"]

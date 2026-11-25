# -*- coding: utf-8 -*-
"""数据 intake（quote 门禁）的回归测试（升级 P3）。"""
from __future__ import annotations

import json

import pytest

from core import report_flow, research_intake as ri


def _project(tmp_path, quote: str = ""):
    d = tmp_path / "data"
    d.mkdir()
    (d / "sources.json").write_text(json.dumps({
        "sources": [{"id": "S01", "title": "测试来源", "type": "government",
                     "grade": "A", "url": "http://example.invalid",
                     "date": "2025-01-15", "quote": quote}]
    }, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_collect_refs_nested():
    draft = {"sections": [{"refs": ["S01#a", "S02"]}],
             "chart": {"refs": ["S03"]}}
    assert ri.collect_refs(draft) == ["S01", "S02", "S03"]


def test_collect_refs_resolves_derived_to_source():
    draft = {"sections": [{"refs": ["D_common6_hohhot_mean", "S03"]}]}
    pack = {"numbers": [{"id": "D_common6_hohhot_mean", "source_ref": "S01"}]}
    assert ri.collect_refs(draft, pack) == ["S01", "S03"]


def test_gate_off_skips():
    out = ri.quote_gate("/nonexistent", refs=["S01"], mode="off")
    assert out["ok"] is True
    assert out["verdict"] == "SKIP"


def test_gate_no_sources_skips(tmp_path):
    out = ri.quote_gate(str(tmp_path), refs=["S01"], mode="warn")
    assert out["ok"] is True
    assert out["status"] == "no_sources"


def test_gate_warn_marks_unverified_without_quote(tmp_path):
    p = _project(tmp_path, quote="")
    out = ri.quote_gate(str(p), refs=["S01"], mode="warn")
    assert out["ok"] is False
    assert out["used_unverified"] == ["S01"]
    assert out["unverified"] == 1
    assert out["checked"] == 0


def test_gate_strict_raises_on_unverified(tmp_path):
    p = _project(tmp_path, quote="")
    with pytest.raises(report_flow.FlowError):
        ri.quote_gate(str(p), refs=["S01"], mode="strict")


def test_verify_skips_unused_sources(tmp_path):
    p = _project(tmp_path, quote="")
    q = ri.verify(str(p), only_ids=["S99"])
    assert q["schema"] == "dsh.reachability/v1"
    assert q["skipped"] == 1
    assert q["reachable"] == 0

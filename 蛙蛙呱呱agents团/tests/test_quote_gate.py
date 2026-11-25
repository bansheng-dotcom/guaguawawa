# -*- coding: utf-8 -*-
"""P3-4：可达性预检（research_intake）与 quote 判据（source_verify）分离。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core import research_intake  # noqa: E402

PAGE = "本报告显示 2025 年样本规模同比增长 12.3%，其中头部主体占比 48%。"
SOURCES = {"sources": [
    {"id": "S1", "file": "s1.html", "url": "https://example.invalid/a",
     "date": "2025-11-20", "quote": "样本规模同比增长 12.3%", "grade": "A"},
    {"id": "S2", "file": "s2.html", "url": "https://example.invalid/b",
     "date": "2025-11-20", "quote": "这句话在页面里根本不存在", "grade": "B"},
]}


def _proj(tmp_path: Path) -> Path:
    d = tmp_path / "proj"
    (d / "data").mkdir(parents=True)
    (d / "data" / "sources.json").write_text(
        json.dumps(SOURCES, ensure_ascii=False), encoding="utf-8")
    return d


def test_verify_only_checks_reachability(tmp_path, monkeypatch):
    p = _proj(tmp_path)
    monkeypatch.setattr(research_intake, "_fetch", lambda url: (PAGE, ""))
    out = research_intake.verify(str(p))
    assert out["schema"] == "dsh.reachability/v1"
    assert out["reachable"] == 2 and out["unreachable"] == 0
    assert "ok" not in out and "mismatch" not in out   # 不再给 quote 结论
    assert (p / "data" / "reachability.json").is_file()


def test_quote_gate_delegates_to_source_verify(tmp_path, monkeypatch):
    p = _proj(tmp_path)
    monkeypatch.setattr(research_intake, "_fetch", lambda url: (PAGE, ""))
    g = research_intake.quote_gate(str(p), mode="warn", fetch=lambda url: PAGE)
    assert g["ok"] is False
    assert g["ok_count"] == 1 and g["mismatch"] == 1
    assert set(g["used_unverified"]) == {"S2"}
    items = {r["id"]: r for r in g["items"]}
    assert items["S1"]["status"] == "verified"
    assert items["S2"]["status"] == "quote_not_found"
    saved = json.loads((p / "data" / "quote_check.json").read_text(encoding="utf-8"))
    assert saved["schema"] == "dsh.quote_check/v1"


def test_quote_gate_marks_unreachable(tmp_path, monkeypatch):
    p = _proj(tmp_path)
    monkeypatch.setattr(research_intake, "_fetch", lambda url: (PAGE, ""))

    def boom(url):
        raise TimeoutError("timed out")

    g = research_intake.quote_gate(str(p), mode="warn", fetch=boom)
    assert g["ok"] is False and g["unreachable"] == 2


def test_quote_gate_skip_when_no_sources(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    g = research_intake.quote_gate(str(d), mode="warn")
    assert g["ok"] is True and g["status"] == "no_sources"

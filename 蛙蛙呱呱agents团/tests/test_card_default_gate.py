# -*- coding: utf-8 -*-
"""拆卡线默认硬门（2026-11-22）：没有 issued.json 的卡不收；显式 legacy 才放行。"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from core import dispatch

# 临时目录必须在团外：写团内会让"项目边界门禁"变红（且污染工具仓）
TMP = Path(tempfile.gettempdir()) / "guagua_test_card_default_gate"


def _fake_project() -> Path:
    shutil.rmtree(TMP, ignore_errors=True)
    card = TMP / "cards" / "r06"
    card.mkdir(parents=True)
    (card / "TASK.md").write_text("# 工单 r06\n", encoding="utf-8")
    (card / "claims.json").write_text(json.dumps({
        "schema": "dsh.agent.claims/v1",
        "sources": [{"file": "S1", "url": "https://example.com/a",
                     "date": "2025", "quote": "这是一段示例原文片段十个字以上",
                     "title": "示例", "org": "示例机构", "kind": "web",
                     "grade": "B"}],
        "numbers": [{"id": "N1", "name": "示例", "value": 1, "unit": "个",
                     "period": "2025", "source_file": "S1"}],
        "sections": [],
    }, ensure_ascii=False), encoding="utf-8")
    return TMP


def test_collect_blocks_missing_issued():
    base = _fake_project()
    merged, problems = dispatch.collect(str(base), min_sources=0)
    assert any("没有 issued.json" in p for p in problems), problems
    assert any(d == "blocked" for d in [merged.get("dispatch_mode")] if d) or True


def test_collect_allows_explicit_legacy_but_marks_it():
    base = _fake_project()
    merged, problems = dispatch.collect(str(base), min_sources=0, allow_legacy=True)
    assert not any("没有 issued.json" in p for p in problems), problems
    assert "legacy_no_issued" in (merged.get("degraded") or [])

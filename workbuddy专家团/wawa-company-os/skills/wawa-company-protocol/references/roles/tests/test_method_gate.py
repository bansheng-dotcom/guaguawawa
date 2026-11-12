# -*- coding: utf-8 -*-
"""方法门禁测试：未匹配价差/无基线趋势应 FAIL，匹配后应 PASS。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.method_gate import check  # noqa: E402


def test_unmatched_spread_fails(tmp_path: Path) -> None:
    p = tmp_path / "bad.html"
    p.write_text("<p>省内价差 2.33 倍，呼市最高。</p><p>价格窄幅震荡，振幅 4.79%，属正常。</p>", encoding="utf-8")
    issues = check(p)
    assert any(i["type"] == "价差未匹配" for i in issues)
    assert any(i["type"] == "趋势无基线" for i in issues)


def test_matched_spread_passes(tmp_path: Path) -> None:
    p = tmp_path / "good.md"
    p.write_text("同规格同日分规格对照后，价差 3.09 元；同比 -5.11%，低于同期基线。", encoding="utf-8")
    assert check(p) == []

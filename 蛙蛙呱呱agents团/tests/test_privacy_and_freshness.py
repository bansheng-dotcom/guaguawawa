# -*- coding: utf-8 -*-
"""隐私扫描（scripts/check_report_privacy.py）与来源时效（core.sources.source_freshness）回归。"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core.sources import source_freshness  # noqa: E402
from scripts import check_report_privacy as privacy  # noqa: E402


def test_privacy_hits_secret_and_pii():
    text = "\n".join([
        "api_key = sk-abcdefghijklmnop123456",
        'password="hunter2pass"',
        "联系电话 13812345678",
        "身份证 110101199001011234",
    ])
    names = {h[0] for h in privacy.scan_text(text)}
    assert {"密钥前缀", "键值对", "手机号", "身份证"} <= names


def test_privacy_allows_placeholders():
    text = 'api_key = "${API_KEY}"\npassword=<your_password>\ntoken=***'
    assert privacy.scan_text(text) == []


def test_privacy_cli_blocks_and_passes(tmp_path, capsys):
    bad = tmp_path / "claims.json"
    bad.write_text('{"note":"secret=abcdef123456"}', encoding="utf-8")
    assert privacy.main([str(bad)]) == 1
    bad.write_text('{"note":"secret=***"}', encoding="utf-8")
    assert privacy.main([str(bad), "--quiet"]) == 0


def test_freshness_ratio_and_year_midpoint():
    today = dt.date(2026, 11, 26)
    src = [
        {"date": "2026"},           # 年份按 7 月 1 日 → 约 4 个月
        {"date": "2025-11"},        # 12 个月
        {"date": "2023-01"},        # 46 个月 → 旧
        {"date": "不详"},            # 解析不了
    ]
    r = source_freshness.summarize(src, window_months=18, today=today)
    assert r["dated"] == 3 and r["undated"] == 1
    assert r["stale_ratio"] == round(1 / 3, 3)
    assert r["newest"] == "2026-07-01"


def test_freshness_empty():
    r = source_freshness.summarize([], today=dt.date(2026, 11, 26))
    assert r["dated"] == 0 and r["stale_ratio"] is None

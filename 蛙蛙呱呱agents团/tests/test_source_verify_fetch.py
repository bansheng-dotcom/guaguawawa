# -*- coding: utf-8 -*-
"""来源回抓硬化（core.source_verify）回归。

守三条：
1. 连接级失败会退避重试，第三次成功就返回正文；
2. 未开启兜底时不调用 Playwright，异常照常抛出（不能假装已核）；
3. 开启 GUAGUA_FETCH_FALLBACK=1 时才走无头浏览器。
"""
from __future__ import annotations

import sys
import urllib.error
from pathlib import Path

import pytest

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core import source_verify  # noqa: E402


class _Resp:
    headers = {"Content-Type": "text/html; charset=utf-8"}

    def read(self, n: int = -1) -> bytes:
        return "<html><body>内蒙古蔬菜 655 万吨</body></html>".encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_retry_then_success(monkeypatch):
    calls = {"n": 0}

    def fake(url, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.URLError("connection reset")
        return _Resp()

    monkeypatch.setattr(source_verify.urllib.request, "urlopen", fake)
    monkeypatch.setattr(source_verify.time, "sleep", lambda s: None)
    out = source_verify.default_fetch("https://example.gov.cn/a")
    assert calls["n"] == 3
    assert "655" in out


def test_no_fallback_by_default(monkeypatch):
    called = {"pw": 0}

    def always_fail(url, timeout=None):
        raise urllib.error.URLError("blocked")

    monkeypatch.setattr(source_verify.urllib.request, "urlopen", always_fail)
    monkeypatch.setattr(source_verify.time, "sleep", lambda s: None)
    monkeypatch.setattr(source_verify, "_playwright_fetch",
                        lambda *a, **k: called.__setitem__("pw", called["pw"] + 1) or "")
    monkeypatch.delenv("GUAGUA_FETCH_FALLBACK", raising=False)
    with pytest.raises(urllib.error.URLError):
        source_verify.default_fetch("https://example.gov.cn/a")
    assert called["pw"] == 0


def test_fallback_when_enabled(monkeypatch):
    def always_fail(url, timeout=None):
        raise urllib.error.URLError("blocked")

    monkeypatch.setattr(source_verify.urllib.request, "urlopen", always_fail)
    monkeypatch.setattr(source_verify.time, "sleep", lambda s: None)
    monkeypatch.setattr(source_verify, "_playwright_fetch", lambda *a, **k: "兜底正文")
    monkeypatch.setenv("GUAGUA_FETCH_FALLBACK", "1")
    assert source_verify.default_fetch("https://example.gov.cn/a") == "兜底正文"


def test_pdf_returns_empty(monkeypatch):
    class PdfResp(_Resp):
        headers = {"Content-Type": "application/pdf"}

    monkeypatch.setattr(source_verify.urllib.request, "urlopen",
                        lambda url, timeout=None: PdfResp())
    assert source_verify.default_fetch("https://example.gov.cn/a.pdf") == ""

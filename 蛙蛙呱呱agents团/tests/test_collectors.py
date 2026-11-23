# -*- coding: utf-8 -*-
"""test_collectors —— 采集器（离线夹具，不依赖网络）。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.collectors import base  # noqa: E402
import core.collectors  # noqa: F401,E402  触发注册
from core.collectors import web_search as ws  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "html" / "search_demo.html"

SEL = {
    "item": "//li[@class='item']",
    "title": ".//h2/a/text()",
    "url": ".//h2/a/@href",
    "price": ".//span[@class='price']/text()",
    "sales": ".//span[@class='sales']/text()",
}


def test_registry_has_three_collectors():
    assert set(base.names()) >= {"csv_manual", "web_search", "platform_search"}


def test_parse_items_offline():
    html = FIX.read_text(encoding="utf-8")
    rows = ws.parse_items(html, SEL)
    assert len(rows) == 3
    assert rows[0]["title"] == "AAA 汽车脚垫 全包围"
    assert rows[0]["url"] == "https://demo.invalid/1"
    assert rows[0]["price"] == "128.0"


def test_parse_requires_item_selector():
    try:
        ws.parse_items("<ul></ul>", {"title": ".//a"})
    except ValueError as exc:
        assert "item" in str(exc)
    else:
        raise AssertionError("缺 item 选择器应当报错")


def test_zero_rows_must_raise():
    # 反爬拦截页会得到 0 行；必须报错，不能静默当成「今天没数据」
    try:
        ws.check_rows([], html_len=2696)
    except ValueError as exc:
        assert "0 行" in str(exc)
    else:
        raise AssertionError("0 行必须报错")


def test_check_rows_passes_through():
    assert ws.check_rows([{"a": 1}], 100) == [{"a": 1}]


def test_fetch_requires_url():
    try:
        base.get("web_search")().fetch({"query": {}})
    except ValueError as exc:
        assert "url" in str(exc)
    else:
        raise AssertionError("缺 url 应当报错")

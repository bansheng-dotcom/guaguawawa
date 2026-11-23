# -*- coding: utf-8 -*-
"""网页搜索页采集器（S2 / 选项 B：真采集）。

**业务无关**：它只知道三件事——
    去哪抓（query.url）
    怎么找条目（query.selectors.item，XPath）
    每条抽哪些字段（query.selectors.<field>，相对条目的 XPath）

业务词（品类/品牌名）只出现在 url 里。

诚实边界（必须写在前面）：
- 天猫/京东/百度搜索页有反爬，常只返回 2–3KB 的拦截页 → 抓到 0 行就报错，**不静默返回空**。
- 真正稳定的产品级采集要么用浏览器（Playwright），要么买第三方数据，要么手工 CSV。
- 本采集器对「能返回正常 HTML 的页面」有效（如必应结果页、公开报告页）。
"""
from __future__ import annotations

import urllib.parse
import urllib.request
from typing import Any, Dict, List

from core.collectors import base

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def fetch_html(url: str, timeout: int = 20) -> str:
    """抓一个页面；失败抛异常（不返回空串掩盖问题）。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    for enc in ("utf-8", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_items(html: str, selectors: Dict[str, str]) -> List[Dict[str, str]]:
    """按 XPath 抽条目。selectors 里必须有 item，其余是「相对条目的 XPath」。"""
    try:
        from lxml import html as LH
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("需要 lxml 才能解析 HTML: %s" % exc)
    tree = LH.fromstring(html)
    item_xp = str(selectors.get("item") or "")
    if not item_xp:
        raise ValueError("selectors 缺 item（条目 XPath）")
    nodes = tree.xpath(item_xp)
    out: List[Dict[str, str]] = []
    for nd in nodes:
        row: Dict[str, str] = {}
        for k, xp in selectors.items():
            if k == "item":
                continue
            try:
                vals = nd.xpath(str(xp))
            except Exception:  # noqa: BLE001
                vals = []
            txt = " ".join(str(v).strip() for v in vals
                           if isinstance(v, str) and str(v).strip())
            row[str(k)] = txt
        out.append(row)
    return out


def check_rows(rows: List[Dict[str, Any]], html_len: int = 0) -> List[Dict[str, Any]]:
    """0 行必须报错——反爬拦截页不能静默变成「今天没数据」。"""
    if not rows:
        raise ValueError(
            "抓到 0 行（页面 %d 字节，可能被反爬拦截或选择器失效）" % html_len)
    return rows


@base.register
class WebSearchCollector:
    name = "web_search"

    def fetch(self, spec: Dict[str, Any],
              project_dir: str = "") -> List[Dict[str, Any]]:
        q = (spec or {}).get("query") or {}
        url = str(q.get("url") or "")
        if not url:
            raise ValueError("web_search 需要 query.url")
        sel = dict(q.get("selectors") or {})
        html = fetch_html(url)
        rows = parse_items(html, sel)
        return check_rows(rows, len(html))


@base.register
class PlatformSearchCollector(WebSearchCollector):
    """平台搜索页：同一套抓取/解析，只是源类型叫 platform_search。"""
    name = "platform_search"

# -*- coding: utf-8 -*-
"""core.sources.source_verify —— 来源逐条回抓：字段齐、URL 可取、quote 能在原文里找到。

分两级，不混为一谈：

    字段级（永远跑）：每条 source 必须有 file / url(http|https) / date / quote。
    回抓级（--verify-quotes 才跑）：打开 URL，把 quote 去掉空白后做子串匹配。

回抓结果只有三种：verified / quote_not_found / fetch_failed。
被反爬、需要登录、正文在图片里的，一律记 fetch_failed，不假装已核。
"""
from __future__ import annotations

import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List
from urllib.parse import urlsplit

QUOTE_MIN = 12
DATE_RE = re.compile(r"^\d{4}(-\d{1,2}(-\d{1,2})?)?$")
URL_RE = re.compile(r"^https?://")

# 2026-11-26：回抓失败的主因不是「引文不对」，而是 gov 站点对默认 UA / 无 Referer
# 的请求直接断连。补请求头 + 退避重试，把「取不到」和「取到了但引文不匹配」分开。
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
_ACCEPT = ("text/html,application/xhtml+xml,application/xml;q=0.9,"
           "image/avif,image/webp,*/*;q=0.8")
_MAX_TRIES = 3
_BACKOFF = 0.6

Fetch = Callable[[str], str]

# URL 归一化：去协议、去 www、去 fragment 与追踪参数，再比是不是同一个来源。
# 2026-11-20：去重键原来是 `角色:文件编号`，同一篇报道被 4 个角色各登记一次，
# 就能把 `--min-sources 50` 刷成 140。去重必须落在 URL 上。
_TRACKING = re.compile(r"^(utm_[a-z]+|spm|from|share_token|ref|source)$", re.I)


def normalize_url(url: Any) -> str:
    """同一篇文章的不同写法 → 同一个键；解析不了就退回原文小写。"""
    raw = str(url or "").strip()
    if not raw:
        return ""
    try:
        from urllib.parse import parse_qsl, urlencode, urlsplit
        p = urlsplit(raw if "://" in raw else "http://" + raw)
        host = (p.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        path = re.sub(r"/+$", "", p.path or "/")
        query = urlencode([(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
                           if not _TRACKING.match(k)])
        return host + path + ("?" + query if query else "")
    except Exception:  # noqa: BLE001
        return raw.lower()


def _norm(text: Any) -> str:
    return re.sub(r"\s+", "", str(text or ""))


def check_fields(src: Dict[str, Any]) -> List[str]:
    """一条来源最少要有什么。缺什么回什么，顺序固定。"""
    miss: List[str] = []
    if not str(src.get("file") or "").strip():
        miss.append("file")
    if not URL_RE.match(str(src.get("url") or "")):
        miss.append("url(http/https)")
    if not DATE_RE.match(str(src.get("date") or "").strip()):
        miss.append("date(YYYY[-MM[-DD]])")
    if len(_norm(src.get("quote"))) < QUOTE_MIN:
        miss.append(f"quote(原文≥{QUOTE_MIN}字)")
    return miss


def _headers(url: str) -> Dict[str, str]:
    try:
        p = urlsplit(url)
        referer = f"{p.scheme}://{p.hostname}/" if p.hostname else ""
    except Exception:  # noqa: BLE001
        referer = ""
    h = {"User-Agent": _UA, "Accept": _ACCEPT,
         "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
         "Connection": "close"}
    if referer:
        h["Referer"] = referer
    return h


def _urllib_get(url: str, timeout: int) -> str:
    """带退避重试的 GET：仅对「可重试」错误重试（429/5xx/连接中断）。"""
    last: Exception | None = None
    for i in range(_MAX_TRIES):
        try:
            req = urllib.request.Request(url, headers=_headers(url))
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                raw = resp.read(2_000_000)
                ctype = (resp.headers.get("Content-Type") or "").lower()
            if "pdf" in ctype:
                # PDF 不在此处解析：记为取到但无法逐字匹配，交给人工。
                return ""
            text = raw.decode("utf-8", errors="ignore")
            text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text,
                          flags=re.S | re.I)
            return re.sub(r"<[^>]+>", " ", text)
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in (429, 500, 502, 503, 504) or i == _MAX_TRIES - 1:
                raise
        except Exception as exc:  # noqa: BLE001  连接重置/超时都值得再试一次
            last = exc
            if i == _MAX_TRIES - 1:
                raise
        time.sleep(_BACKOFF * (2 ** i))
    if last:
        raise last
    return ""


def _playwright_fetch(url: str, timeout: int = 25) -> str:
    """无头浏览器兜底：只在 GUAGUA_FETCH_FALLBACK=1 时启用。

    为什么默认关闭：Playwright 是可选依赖，失败会拖慢整批回抓；
    显式开关让「本地能跑」和「CI 只跑确定性部分」两种场景都不被破坏。
    """
    from playwright.sync_api import sync_playwright  # noqa: PLC0415
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            return page.inner_text("body")
        finally:
            browser.close()


def default_fetch(url: str, timeout: int = 20) -> str:
    """抓 HTML → 纯文本。urllib 失败且显式开启兜底时，改用无头浏览器。"""
    try:
        return _urllib_get(url, timeout)
    except Exception:  # noqa: BLE001
        if os.environ.get("GUAGUA_FETCH_FALLBACK") != "1":
            raise
        return _playwright_fetch(url, timeout=max(timeout, 25))


def verify_source(src: Dict[str, Any], fetch: Fetch | None = None) -> Dict[str, Any]:
    fields = check_fields(src)
    row: Dict[str, Any] = {
        "id": str(src.get("file") or ""),
        "url": str(src.get("url") or ""),
        "quote_len": len(_norm(src.get("quote"))),
        "fields": fields,
        "status": "unverified",
    }
    if fields:
        row["status"] = "fields_missing"
        return row
    if fetch is None:
        return row
    try:
        page = fetch(str(src["url"]))
    except Exception as exc:  # noqa: BLE001  网络失败只记录，不抛
        row["status"] = "fetch_failed"
        row["error"] = f"{type(exc).__name__}: {exc}"[:200]
        return row
    if page and _norm(src["quote"]) in _norm(page):
        row["status"] = "verified"
        row["ok"] = True
        return row
    row["status"] = "quote_not_found"
    row["page_chars"] = len(_norm(page))
    return row


def _memo_fetch(fetch: Fetch) -> Fetch:
    """按归一化 URL 记忆抓取结果：同一页被 4 个角色各登记一次，只抓一次。"""
    cache: Dict[str, tuple] = {}

    def call(url: str) -> str:
        key = normalize_url(url) or url
        if key not in cache:
            try:
                cache[key] = ("ok", fetch(url))
            except Exception as exc:  # noqa: BLE001
                cache[key] = ("err", exc)
        kind, val = cache[key]
        if kind == "err":
            raise val
        return val

    call.cache = cache  # type: ignore[attr-defined]
    return call


def verify_sources(sources: List[Dict[str, Any]], fetch: Fetch | None = None) -> Dict[str, Any]:
    memo = _memo_fetch(fetch or default_fetch)
    rows = [verify_source(s, memo) for s in sources]
    verified = sum(1 for r in rows if r["status"] == "verified")
    counts: Dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"ok": bool(rows) and verified == len(rows),
            "total": len(rows), "verified": verified, "counts": counts,
            "unique_fetches": len(memo.cache),  # type: ignore[attr-defined]
            "fetch": fetch is not None, "rows": rows}

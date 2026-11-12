# -*- coding: utf-8 -*-
"""探源 6：全国富士苹果分市场行情表 + 内蒙古价格监测平台水果条目。"""
from __future__ import annotations

import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"}


def get(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=timeout).read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def table(html: str) -> list[list[str]]:
    out = []
    for tr in re.findall(r"<tr[\s\S]*?</tr>", html, flags=re.I):
        cells = [re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ").strip()
                 for c in re.findall(r"<t[dh][\s\S]*?</t[dh]>", tr, flags=re.I)]
        cells = [c for c in cells if c]
        if cells:
            out.append(cells)
    return out


if __name__ == "__main__":
    print("=== 全国富士苹果 ===")
    h = get("http://futures.stockstar.com/IG2026111100024473.shtml")
    for r in table(h)[:30]:
        print(" | ".join(r)[:120])

    print("\n=== nmgjgjc 列表 ===")
    for url in ("http://www.nmgjgjc.com.cn/jgjcwz/pricedyna/", "http://www.nmgjgjc.com.cn/"):
        try:
            t = get(url)
            print(url, len(t))
            for m in re.findall(r'href="([^"]+)"[^>]*>([^<]{6,40})<', t)[:20]:
                print("  ", m)
            if "水果" in t:
                print("  含'水果'")
            break
        except Exception as exc:  # noqa: BLE001
            print(url, "ERR", type(exc).__name__, str(exc)[:80])

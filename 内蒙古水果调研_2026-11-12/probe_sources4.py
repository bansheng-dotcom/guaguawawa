# -*- coding: utf-8 -*-
"""探源 4：把一页批发行情表按行 dump 出来，确认可解析结构。"""
from __future__ import annotations

import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"}


def get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=timeout).read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def rows(html: str) -> list[list[str]]:
    out = []
    for tr in re.findall(r"<tr[\s\S]*?</tr>", html, flags=re.I):
        cells = [re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ").strip()
                 for c in re.findall(r"<t[dh][\s\S]*?</t[dh]>", tr, flags=re.I)]
        cells = [c for c in cells if c]
        if cells:
            out.append(cells)
    return out


def main() -> None:
    for name, url in {
        "stockstar_baoquanzhuang": "https://futures.stockstar.com/IG2026111000019922.shtml",
        "21food": "https://wap.21food.cn/price/market/1327-p7.html",
    }.items():
        print("=" * 15, name)
        html = get(url)
        rs = rows(html)
        print("tables rows:", len(rs))
        for r in rs[:40]:
            print(" | ".join(r)[:160])
        print()


if __name__ == "__main__":
    main()

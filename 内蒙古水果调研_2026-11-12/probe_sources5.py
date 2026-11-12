# -*- coding: utf-8 -*-
"""探源 5：21food 分页能覆盖多少天；商务局周报列表页能否枚举。"""
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
        if len(cells) >= 3:
            out.append(cells)
    return out


if __name__ == "__main__":
    print("=== 21food 保全庄 1327 分页 ===")
    for p in range(1, 16):
        url = f"https://wap.21food.cn/price/market/1327-p{p}.html"
        try:
            rs = table(get(url))
            dates = sorted({r[3] for r in rs if len(r) >= 4 and re.match(r"\d{4}-\d{2}-\d{2}", r[3])})
            fruits = [r[0] for r in rs if len(r) >= 4 and r[3].startswith("2026")]
            print(p, "rows", len(rs), "dates", dates[:4], "sample", fruits[:4])
        except Exception as exc:  # noqa: BLE001
            print(p, "ERR", type(exc).__name__, str(exc)[:60])

    print("\n=== 商务局列表页 ===")
    for url in ("http://swj.huhhot.gov.cn/tjxx/", "http://swj.huhhot.gov.cn/tjxx/index.html"):
        try:
            t = get(url)
            links = re.findall(r'href="([^"]*t\d{8}_\d+\.html)"[^>]*>([^<]{4,60})<', t)
            print(url, "links", len(links))
            for a, b in links[:12]:
                print("  ", a, b.strip())
            break
        except Exception as exc:  # noqa: BLE001
            print(url, "ERR", type(exc).__name__, str(exc)[:80])

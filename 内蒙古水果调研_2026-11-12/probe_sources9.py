# -*- coding: utf-8 -*-
"""探源 9：解析 Nuxt 数据 + gotohui 表格。"""
from __future__ import annotations

import gzip
import json
import re
import urllib.request
import zlib

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={**UA, "Accept-Encoding": "gzip"})
    r = urllib.request.urlopen(req, timeout=30)
    raw = r.read()
    if r.headers.get("Content-Encoding") == "gzip":
        raw = gzip.decompress(raw)
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


h = get("http://m.cnhnkj.cn/hangqing/cd-2001636-1069-0-1441/")
m = re.search(r"window\.__NUXT__=(.*?);?</script>", h, re.S)
print("NUXT found:", bool(m))
if m:
    blob = m.group(1)
    print(blob[:1500])

print("\n--- gotohui tables ---")
g = get("https://www.gotohui.com/ndata/show-1712206")
for tbl in re.findall(r"<table[\s\S]*?</table>", g, flags=re.I)[:2]:
    txt = re.sub(r"<[^>]+>", "|", tbl)
    txt = re.sub(r"\s+", " ", txt.replace("&nbsp;", " "))
    print(txt[:1200])

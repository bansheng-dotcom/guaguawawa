# -*- coding: utf-8 -*-
"""探源 10：统计公报中的水果产量。"""
from __future__ import annotations

import gzip
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={**UA, "Accept-Encoding": "gzip"})
    r = urllib.request.urlopen(req, timeout=40)
    raw = r.read()
    if r.headers.get("Content-Encoding") == "gzip":
        raw = gzip.decompress(raw)
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def strip(html: str) -> str:
    body = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    body = re.sub(r"<style[\s\S]*?</style>", " ", body, flags=re.I)
    text = re.sub(r"<[^>]+>", "\n", body)
    text = text.replace("&nbsp;", " ").replace("&#160;", " ")
    return "\n".join(l.strip() for l in text.split("\n") if l.strip())


url = "https://www.nmg.gov.cn/tjsj/tjsj/tjgb/202604/t20260409_2886936.html"
t = strip(get(url))
print("len", len(t))
for line in t.split("\n"):
    if re.search(r"水果|园林|苹果|葡萄|梨|瓜果|经济林", line):
        print(line[:300])

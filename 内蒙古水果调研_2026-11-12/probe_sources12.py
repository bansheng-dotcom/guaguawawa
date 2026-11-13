# -*- coding: utf-8 -*-
"""探源 12：公报关键基础数（人口/农牧业）+ 澎湃全国水果产区文。"""
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


t = strip(get("https://www.nmg.gov.cn/tjsj/tjsj/tjgb/202604/t20260409_2886936.html"))
for line in t.split("\n"):
    if re.search(r"常住人口|城镇化率|社会消费品零售|居民人均|农牧业|粮食产量|牲畜|瓜果", line):
        print(line[:260])

print("\n=== 澎湃 ===")
try:
    p = strip(get("https://m.thepaper.cn/newsDetail_forward_33753707"))
    for line in p.split("\n"):
        if re.search(r"内蒙古|水果产量|万吨|苹果|葡萄", line):
            print(line[:220])
except Exception as exc:  # noqa: BLE001
    print("ERR", type(exc).__name__, str(exc)[:120])

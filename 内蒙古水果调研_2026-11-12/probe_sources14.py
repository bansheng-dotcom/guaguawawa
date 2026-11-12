# -*- coding: utf-8 -*-
"""探源 14：人均消费/零售规模/内蒙古冷链基础数据。"""
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


URLS = {
    "qianzhan": "https://www.qianzhan.com/analyst/detail/220/260520-0065a0b3.html",
    "huaon": "https://www.huaon.com/channel/trend/1166031.html",
    "nmg_jtyst": "https://jtyst.nmg.gov.cn/zwgk/zfxxgk/fdzdgknr/labl/202512/t20251219_2836948.html",
}

for name, url in URLS.items():
    print("=" * 20, name)
    try:
        t = strip(get(url))
        hits = [l for l in t.split("\n")
                if re.search(r"人均|公斤|万亿|亿元|冷链|库容|损耗|流通率|万吨|冷藏|预冷", l)]
        print(f"lines={len(t.splitlines())} hits={len(hits)}")
        for h in hits[:14]:
            print("  ", h[:260])
    except Exception as exc:  # noqa: BLE001
        print("ERR", type(exc).__name__, str(exc)[:120])
    print()

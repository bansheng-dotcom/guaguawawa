# -*- coding: utf-8 -*-
"""探源 13：内蒙古水果产量/面积、宁城与通辽果业、冷链损耗。"""
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
    "ningcheng": "http://lcj.nmg.gov.cn/xxgk/zxzx/202509/t20250930_2798125.html",
    "tongliao": "https://www.tongliao.gov.cn/zjtl/fztl/tltf/nmy/202512/t20251216_1021786.html",
    "ceic": "https://www.ceicdata.com/zh-hans/china/yield-of-farm-crops-fruits-by-region/cn-farm-crops-fruits-yield-inner-mongolia",
}

for name, url in URLS.items():
    print("=" * 20, name)
    try:
        t = strip(get(url))
        hits = [l for l in t.split("\n") if re.search(r"万吨|万亩|亩|产量|面积|苹果|沙果|产值|损耗", l)]
        print(f"lines={len(t.splitlines())} hits={len(hits)}")
        print("\n".join(hits[:18]))
    except Exception as exc:  # noqa: BLE001
        print("ERR", type(exc).__name__, str(exc)[:120])
    print()

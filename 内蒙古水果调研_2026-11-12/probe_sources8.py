# -*- coding: utf-8 -*-
"""探源 8：看这些页面里数据到底在哪个结构（JSON/表格/接口）。"""
from __future__ import annotations

import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=30).read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


for name, url in {
    "cnhnkj_apple": "http://m.cnhnkj.cn/hangqing/cd-2001636-1069-0-1441/",
    "ymt_wuyuan": "https://www.ymt.com/hangqing/chandi_detail-7599-488621-807",
    "gotohui": "https://www.gotohui.com/ndata/show-1712206",
}.items():
    print("=" * 18, name)
    h = get(url)
    print("len", len(h))
    for pat in (r"__NUXT__", r"__NEXT_DATA__", r"window\.__INITIAL", r"application/ld\+json", r"<table", r"<!--"):
        print(f"  {pat}: {len(re.findall(pat, h))}")
    # 数值片段
    for m in re.finditer(r".{60}(元/斤|元/公斤|万吨).{60}", h):
        print("   ...", re.sub(r"\s+", " ", m.group(0))[:200])
        break
    idx = h.find("苹果")
    print("  ctx:", re.sub(r"\s+", " ", h[max(0, idx - 100): idx + 300])[:400])

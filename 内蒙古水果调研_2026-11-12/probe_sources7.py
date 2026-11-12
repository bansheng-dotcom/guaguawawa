# -*- coding: utf-8 -*-
"""探源 7：产量/面积/产地价页面取数（打印正文关键段，供落台账）。"""
from __future__ import annotations

import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"}

URLS = {
    "gotohui_fruit": "https://www.gotohui.com/ndata/show-1712206",
    "cnhnkj_apple": "http://m.cnhnkj.cn/hangqing/cd-2001636-1069-0-1441/",
    "cnhnb_melon": "https://www.cnhnb.com/p/tiangua-0-0-9723-0-1/",
    "ymt_wuyuan": "https://www.ymt.com/hangqing/chandi_detail-7599-488621-807",
}


def get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=timeout).read()
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
    text = text.replace("&nbsp;", " ").replace("&#160;", " ").replace("&amp;", "&")
    return "\n".join(l.strip() for l in text.split("\n") if l.strip())


if __name__ == "__main__":
    for name, url in URLS.items():
        print("=" * 18, name, url)
        try:
            t = strip(get(url))
            lines = t.split("\n")
            keep = [l for l in lines if re.search(r"万吨|万亩|公顷|元/斤|元/公斤|产量|面积|苹果|蜜瓜|葡萄", l)]
            print(f"lines={len(lines)} keep={len(keep)}")
            print("\n".join(keep[:25]))
        except Exception as exc:  # noqa: BLE001
            print("ERR", type(exc).__name__, str(exc)[:100])
        print()

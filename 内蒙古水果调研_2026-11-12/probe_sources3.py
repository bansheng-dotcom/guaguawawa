# -*- coding: utf-8 -*-
"""探源 3：本地批发/零售页面的数据结构（保全庄、东瓦窑、商务局周报、全国富士苹果行情）。"""
from __future__ import annotations

import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
      "Accept-Language": "zh-CN,zh;q=0.9"}

URLS = {
    "baoquanzhuang_1110": "https://futures.stockstar.com/IG2026111000019922.shtml",
    "dongwayao_1105": "http://futures.stockstar.com/IG2026110500018250.shtml",
    "apple_national_1111": "http://futures.stockstar.com/IG2026111100024473.shtml",
    "hh_swj_1102_1108": "http://swj.huhhot.gov.cn/tjxx/202611/t20261110_2049154.html",
    "hh_swj_1026_1101": "http://swj.huhhot.gov.cn/tjxx/202611/t20261103_2047305.html",
    "21food_baoquanzhuang": "https://wap.21food.cn/price/market/1327-p7.html",
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


def main() -> None:
    for name, url in URLS.items():
        print("=" * 20, name, url)
        try:
            html = get(url)
            t = strip(html)
            keep = [l for l in t.split("\n") if re.search(r"苹果|香蕉|梨|葡萄|西瓜|橘|橙|火龙果|猕猴桃|水果|元/", l)]
            print(f"len={len(html)} lines={len(t.splitlines())} keep={len(keep)}")
            print("\n".join(keep[:30]))
        except Exception as exc:  # noqa: BLE001
            print("ERR", type(exc).__name__, exc)
        print()


if __name__ == "__main__":
    main()

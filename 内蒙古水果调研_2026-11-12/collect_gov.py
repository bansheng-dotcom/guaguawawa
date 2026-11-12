# -*- coding: utf-8 -*-
"""采集层 3：自治区级价格监测（内蒙古价格监测平台）+ 商务预报，抽水果条目。"""
from __future__ import annotations

import gzip
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
RAW.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"}

PAGES = {
    "nmg_202611_10": "http://www.nmgjgjc.com.cn/jgjcwz/pricedyna/202611/10/qba034230aha5p0brf5y.shtml",
    "nmg_202611_09": "http://www.nmgjgjc.com.cn/jgjcwz/pricedyna/202611/09/qb9045419h14smsjcjr0.shtml",
    "nmg_202610_21": "http://www.nmgjgjc.com.cn/jgjcwz/pricedyna/202610/21/qal03001975nrpddn3b9.shtml",
    "nmg_202610_28": "http://www.nmgjgjc.com.cn/jgjcwz/pricedyna/202610/28/qas033252m8iuyeawsrh.shtml",
    "mofcom_1030": "https://cif.mofcom.gov.cn/newsite/html/neimenggu/html/1349859/2026/11/3/1793695175802.html",
}
FRUIT = re.compile(r"苹果|香蕉|梨|葡萄|西瓜|柑橘|橘|桃|哈密瓜|猕猴桃|火龙果|水果")


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


def sentences(html: str) -> list[str]:
    body = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    body = re.sub(r"<style[\s\S]*?</style>", " ", body, flags=re.I)
    text = re.sub(r"<[^>]+>", "\n", body).replace("&nbsp;", " ")
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    out = []
    for line in lines:
        for s in re.split(r"(?<=[。；])", line):
            s = s.strip()
            if len(s) >= 8 and FRUIT.search(s) and re.search(r"元/", s):
                out.append(s)
    return out


if __name__ == "__main__":
    digest = []
    for name, url in PAGES.items():
        try:
            html = get(url)
        except Exception as exc:  # noqa: BLE001
            digest.append(f"### {name} [FAIL {type(exc).__name__}] {url}")
            continue
        (RAW / f"{name}.html").write_text(html, encoding="utf-8", errors="replace")
        ss = sentences(html)
        digest.append(f"### {name} ({len(ss)} 句) {url}")
        digest.extend(ss[:8])
        digest.append("")
    text = "\n".join(digest)
    (ROOT / "digest_gov.txt").write_text(text, encoding="utf-8")
    print(text)

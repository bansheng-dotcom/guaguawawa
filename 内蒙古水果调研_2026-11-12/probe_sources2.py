# -*- coding: utf-8 -*-
"""探源 2：水果可用数据面（周度水果表 / 苹果红枣期货 / 本地价格监测列表页 / 惠农网）。"""
from __future__ import annotations

import json
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
      "Accept-Language": "zh-CN,zh;q=0.9"}


def post(url: str, data: dict, referer: str = "https://pfsc.agri.cn/") -> dict:
    h = dict(UA)
    h["Content-Type"] = "application/json;charset=UTF-8"
    h["Referer"] = referer
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=h, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace"))


def get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=timeout).read()
    for enc in ("utf-8", "gbk"):
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
    print("=== A. 周度接口候选 ===")
    for ep in ("/api/fruitWeekly/pageList", "/api/farmWeekly/pageList"):
        try:
            d = post(ep, {"pageNum": 1, "pageSize": 2})
            lst = d["content"]["list"]
            s = (lst[0].get("contentstr") or "")
            print(f"{ep}: ok, n={len(lst)}, date={lst[0].get('weeklyDate')}, 含'水果'={'水果' in s}")
            idx = s.find("水果")
            if idx >= 0:
                print("   ...", s[max(0, idx - 200): idx + 700].replace("\u3000", " "))
        except Exception as exc:  # noqa: BLE001
            print(f"{ep}: ERR {type(exc).__name__} {exc}")

    print("\n=== B. 期货：苹果 / 红枣 / 鲜苹果 ===")
    for sym in ("AP0", "CJ0"):
        url = ("https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_"
               f"{sym}=/InnerFuturesNewService.getDailyKLine?symbol={sym}")
        try:
            t = get(url)
            m = re.search(r"=\s*\((\[.*\])\)", t, re.S)
            arr = json.loads(m.group(1)) if m else []
            print(sym, "n=", len(arr), "last=", arr[-1] if arr else None)
            if arr:
                print("   first=", arr[0])
        except Exception as exc:  # noqa: BLE001
            print(sym, "ERR", type(exc).__name__, exc)

    print("\n=== C. 呼市发改委价格监测列表 ===")
    for url in ("http://fgw.huhhot.gov.cn/ywgz/jggz/", "http://fgw.huhhot.gov.cn/ywgz/jggz/index.html"):
        try:
            t = strip(get(url))
            print(url, "len", len(t))
            print("\n".join(t.split("\n")[:25]))
            break
        except Exception as exc:  # noqa: BLE001
            print(url, "ERR", type(exc).__name__, exc)


if __name__ == "__main__":
    main()

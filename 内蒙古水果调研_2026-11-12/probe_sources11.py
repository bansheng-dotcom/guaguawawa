# -*- coding: utf-8 -*-
"""探源 11：国家统计局分省年度数据（水果产量）。"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
      "Referer": "https://data.stats.gov.cn/easyquery.htm?cn=E0103"}


def q(params: dict) -> dict:
    url = "https://data.stats.gov.cn/easyquery.htm?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=40).read()
    return json.loads(raw.decode("utf-8", "replace"))


# 先看内蒙古有哪些农业指标
try:
    tree = q({"m": "getTree", "dbcode": "fsnd", "wdcode": "zb", "id": "A0D"})
    def walk(nodes, depth=0):
        for n in nodes:
            print("  " * depth, n.get("id"), n.get("name"), n.get("isParent"))
            if n.get("isParent") and depth < 1:
                walk(q({"m": "getTree", "dbcode": "fsnd", "wdcode": "zb", "id": n["id"]}), depth + 1)
    walk(tree[:40])
except Exception as exc:  # noqa: BLE001
    print("ERR", type(exc).__name__, str(exc)[:200])

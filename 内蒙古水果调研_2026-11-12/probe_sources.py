# -*- coding: utf-8 -*-
"""探源：确认水果品类的可用数据接口（不落成品，只验证）。"""
from __future__ import annotations

import json
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"}


def post(url: str, data: dict, referer: str = "https://pfsc.agri.cn/") -> dict:
    h = dict(UA)
    h["Content-Type"] = "application/json;charset=UTF-8"
    h["Referer"] = referer
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=h, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace"))


def get(url: str, timeout: int = 30, enc: str = "utf-8") -> str:
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=timeout).read()
    try:
        return raw.decode(enc)
    except UnicodeDecodeError:
        return raw.decode("utf-8", "replace")


if __name__ == "__main__":
    print("=== 1. FarmDaily ===")
    try:
        d = post("https://pfsc.agri.cn/api/FarmDaily/list", {"pageNum": 1, "pageSize": 1})
        rec = d["content"]["list"][0]
        print("date:", rec.get("daylyDate"))
        for k, v in rec.items():
            if isinstance(v, str) and len(v) > 30:
                print(f"  [{k}] {v[:600]}")
            else:
                print(f"  [{k}] {v}")
    except Exception as exc:  # noqa: BLE001
        print("ERR", type(exc).__name__, exc)

    print("\n=== 2. farmWeekly ===")
    try:
        d = post("https://pfsc.agri.cn/api/farmWeekly/pageList", {"pageNum": 1, "pageSize": 1})
        rec = d["content"]["list"][0]
        print("week:", rec.get("weeklyDate"))
        print((rec.get("contentstr") or "")[:1200])
    except Exception as exc:  # noqa: BLE001
        print("ERR", type(exc).__name__, exc)

    print("\n=== 3. cnhnb 内蒙古水果 ===")
    try:
        t = get("https://www.cnhnb.com/hangqing/cdlist-2010102-0-0-0-0-1/", enc="utf-8")
        print("len", len(t), "水果" in t, "苹果" in t)
        print(t[:300])
    except Exception as exc:  # noqa: BLE001
        print("ERR", type(exc).__name__, exc)

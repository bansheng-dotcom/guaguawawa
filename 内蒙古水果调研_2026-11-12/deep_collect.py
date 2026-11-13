# -*- coding: utf-8 -*-
"""深度补数：季节性基线（2023—2025 同期）+ 新发地分规格日度价。

目的：回答两个原报告回答不了的问题
  Q1 2026 年 10—11 月到底是「正常波动」还是「异常」？—— 需要多年同期基线。
  Q2 「同省价差 133%」里，多少是规格差、多少是区域差？—— 需要同市场同日的分规格报价。
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
DATA = ROOT / "data"
RAW.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

AGRI_UA = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json;charset=UTF-8",
           "Referer": "https://pfsc.agri.cn/"}
XFD_UA = {"User-Agent": "Mozilla/5.0",
          "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
          "Referer": "http://www.xinfadi.com.cn/priceDetail.html"}


def agri_post(path: str, data: dict) -> dict:
    req = urllib.request.Request("https://pfsc.agri.cn" + path, data=json.dumps(data).encode(),
                                 headers=AGRI_UA, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace"))


def xfd_post(**kw) -> dict:
    body = {"limit": "100", "current": "1", "pubDateStartTime": "", "pubDateEndTime": "",
            "prodPcatid": "", "prodCatid": "", "prodName": ""}
    body.update(kw)
    req = urllib.request.Request("http://www.xinfadi.com.cn/getPriceData.html",
                                 data=urllib.parse.urlencode(body).encode(), headers=XFD_UA, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace"))


def collect_national_history() -> list[dict]:
    """农业农村部日度：把全部历史翻一遍，保留 9—11 月（做季节基线）。"""
    rows, page = [], 1
    while True:
        d = agri_post("/api/FarmDaily/list", {"pageNum": page, "pageSize": 100})
        lst = d["content"]["list"]
        if not lst:
            break
        for rec in lst:
            date = (rec.get("daylyDate") or "")[:10]
            text = rec.get("fruitsConclusion") or ""
            import re
            m = re.search(r"6种水果平均价格为([0-9.]+)元/公斤", text)
            if m and date[5:7] in ("09", "10", "11"):
                rows.append({"date": date, "value": float(m.group(1)), "raw": text})
        if page >= d["content"]["totalPage"]:
            break
        page += 1
    rows.sort(key=lambda r: r["date"])
    (RAW / "farm_daily_seasonal.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("national seasonal rows:", len(rows), rows[0]["date"], "→", rows[-1]["date"])
    return rows


def collect_xfd(prod: str, start: str, end: str) -> list[dict]:
    rows, page = [], 1
    while True:
        d = xfd_post(prodName=prod, pubDateStartTime=start, pubDateEndTime=end,
                     limit="100", current=str(page))
        lst = d.get("list") or []
        if not lst:
            break
        for x in lst:
            rows.append({"date": x["pubDate"][:10], "prod": x["prodName"], "spec": x.get("specInfo") or "",
                         "place": x.get("place") or "", "low": float(x["lowPrice"]),
                         "high": float(x["highPrice"]), "avg": float(x["avgPrice"]),
                         "unit": x.get("unitInfo") or "斤", "cat": x.get("prodPcat") or ""})
        if page * 100 >= d.get("count", 0):
            break
        page += 1
    print(f"xinfadi {prod} {start}~{end}: {len(rows)} 行")
    return rows


if __name__ == "__main__":
    hist = collect_national_history()
    series = {}
    for prod, s, e in [("富士", "2025-09-01", "2025-11-15"),
                       ("富士", "2026-09-01", "2026-11-13"),
                       ("丑苹果", "2026-11-01", "2026-11-13"),
                       ("青苹果", "2026-11-01", "2026-11-13"),
                       ("辽宁寒富苹果", "2026-11-01", "2026-11-13")]:
        series[f"{prod}_{s[:7]}"] = collect_xfd(prod, s, e)
    (RAW / "xinfadi_apple.json").write_text(json.dumps(series, ensure_ascii=False, indent=1), encoding="utf-8")
    print("total xfd rows:", sum(len(v) for v in series.values()))

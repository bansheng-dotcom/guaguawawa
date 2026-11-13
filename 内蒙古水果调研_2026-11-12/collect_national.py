# -*- coding: utf-8 -*-
"""采集层 1：国家级日度 / 周度水果行情 + 苹果红枣期货日线。

来源
  A. 农业农村部 pfsc.agri.cn /api/FarmDaily/list      全国日度「6 种水果均价」
  B. 农业农村部 pfsc.agri.cn /api/farmWeekly/pageList  全国周度「表 5 重点监测水果」
  C. 新浪财经期货日 K                                  苹果 AP0 / 红枣 CJ0
输出
  raw/farm_daily.json / farm_weekly.json / futures_daily.json
  data/全国日度_6种水果.csv / 全国周度_6种水果.csv / 期货_苹果红枣.csv
"""
from __future__ import annotations

import csv
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
DATA = ROOT / "data"
RAW.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
      "Content-Type": "application/json;charset=UTF-8",
      "Referer": "https://pfsc.agri.cn/"}
BASE = "https://pfsc.agri.cn"

START, END = "2026-09-15", "2026-11-13"
FRUITS6 = ["富士苹果", "巨峰葡萄", "香蕉", "菠萝", "西瓜", "鸭梨"]


def post(path: str, data: dict, timeout: int = 40) -> dict:
    req = urllib.request.Request(BASE + path, data=json.dumps(data).encode(), headers=UA, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace"))


def get_text(url: str, timeout: int = 40) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


# ---------------------------------------------------------------- L1 日度
DAILY_RE = re.compile(r"6种水果平均价格为([0-9.]+)元/公斤，[^0-9]{0,8}?(上升|下降|持平)([0-9.]+)?")


def parse_daily(rec: dict) -> dict:
    out = {"date": (rec.get("daylyDate") or rec.get("createDate") or "")[:10]}
    text = rec.get("fruitsConclusion") or ""
    m = DAILY_RE.search(text)
    if m:
        out["水果6种均价"] = float(m.group(1))
        pct = float(m.group(3)) if m.group(3) else 0.0
        out["水果6种环比"] = pct * (1 if m.group(2) == "上升" else -1 if m.group(2) == "下降" else 0)
    # 涨跌榜里出现的水果（只做方向，不做水平）
    up = down = ""
    m2 = re.search(r"涨幅居前的是([^。]*?)，?价格跌幅", rec.get("incOrReduRange") or "")
    if not m2:
        m2 = re.search(r"涨幅居前的是([^。]*)。", rec.get("incOrReduRange") or "")
    if m2:
        up = m2.group(1)
    m3 = re.search(r"价格跌幅居前的是([^。]*)", rec.get("incOrReduRange") or "")
    if m3:
        down = m3.group(1)
    for name in FRUITS6:
        for label, seg in (("涨", up), ("跌", down)):
            mm = re.search(name + r"[^0-9]{0,6}([0-9.]+)%", seg)
            if mm:
                out[f"{name}_{label}榜"] = float(mm.group(1))
    out["_raw_fruits"] = text
    return out


def collect_daily() -> list[dict]:
    rows, page = [], 1
    while page <= 40:
        d = post("/api/FarmDaily/list", {"pageNum": page, "pageSize": 100})
        lst = d["content"]["list"]
        if not lst:
            break
        stop = False
        for rec in lst:
            row = parse_daily(rec)
            dt = row.get("date") or ""
            if START <= dt <= END:
                rows.append(row)
            if dt and dt < START:
                stop = True
        if stop or page >= d["content"]["totalPage"]:
            break
        page += 1
    rows = [r for r in rows if r.get("date", "") >= START]
    rows.sort(key=lambda r: r["date"])
    (RAW / "farm_daily.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows


# ---------------------------------------------------------------- L2 周度
WEEK_CELL = re.compile(r"([0-9]{1,3}\.[0-9]{2})([0-9]{1,3}\.[0-9]{2})([0-9]{1,3}\.[0-9]{2})"
                       r"(-?[0-9]{1,2}\.[0-9]%)?(-?[0-9]{1,2}\.[0-9]%)?")


def parse_weekly(rec: dict) -> list[dict]:
    """表 5 重点监测的水果价格及变化幅度：本周 / 上周 / 去年同期 / 环比 / 同比。"""
    text = (rec.get("contentstr") or "").replace("\u3000", " ")
    week = rec.get("weeklyDate") or ""
    seg = ""
    i = text.find("表5 重点监测的水果价格")
    if i >= 0:
        seg = text[i:]
        j = seg.find("注：")
        if j > 0:
            seg = seg[:j]
    out = []
    for name in FRUITS6:
        idx = seg.find(name)
        if idx < 0:
            continue
        chunk = seg[idx + len(name): idx + len(name) + 60]
        m = WEEK_CELL.search(chunk)
        if not m:
            continue
        out.append({"week": week, "item": name,
                    "this": float(m.group(1)), "last": float(m.group(2)), "yoy_base": float(m.group(3)),
                    "mom_pct": m.group(4) or "", "yoy_pct": m.group(5) or ""})
    return out


def collect_weekly() -> list[dict]:
    d = post("/api/farmWeekly/pageList", {"pageNum": 1, "pageSize": 60})
    rows = []
    for rec in d["content"]["list"]:
        wd = rec.get("weeklyDate") or ""
        if wd and wd >= "20260815":
            rows.extend(parse_weekly(rec))
    rows.sort(key=lambda r: (r["week"], r["item"]))
    (RAW / "farm_weekly.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows


# ---------------------------------------------------------------- L5 期货
FUT = {"AP0": "苹果", "CJ0": "红枣"}


def collect_futures() -> list[dict]:
    rows = []
    for sym, label in FUT.items():
        url = (f"https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_{sym}=/"
               f"InnerFuturesNewService.getDailyKLine?symbol={sym}")
        txt = get_text(url)
        m = re.search(r"=\s*\((\[.*\])\)", txt, re.S)
        if not m:
            print("  [warn] futures parse fail", sym)
            continue
        arr = json.loads(m.group(1))
        n = 0
        for k in arr:
            if START <= k["d"] <= END:
                rows.append({"date": k["d"], "symbol": sym, "name": label,
                             "open": float(k["o"]), "high": float(k["h"]), "low": float(k["l"]),
                             "close": float(k["c"]), "volume": int(float(k["v"]))})
                n += 1
        print(f"  {sym} {label}: {n} 天")
    rows.sort(key=lambda r: (r["date"], r["symbol"]))
    (RAW / "futures_daily.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows


# ---------------------------------------------------------------- 落盘
def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow([r.get(h, "") for h in header])


if __name__ == "__main__":
    daily = collect_daily()
    print("日度:", len(daily), daily[0]["date"] if daily else "-", "→", daily[-1]["date"] if daily else "-")
    write_csv(DATA / "全国日度_6种水果.csv", ["date", "水果6种均价", "水果6种环比"], daily)

    weekly = collect_weekly()
    print("周度:", len(weekly), "周数:", len({r["week"] for r in weekly}))
    write_csv(DATA / "全国周度_6种水果.csv", ["week", "item", "last", "this", "yoy_base", "mom_pct", "yoy_pct"], weekly)

    fut = collect_futures()
    print("期货:", len(fut))
    write_csv(DATA / "期货_苹果红枣.csv", ["date", "symbol", "name", "open", "high", "low", "close", "volume"], fut)

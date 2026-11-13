# -*- coding: utf-8 -*-
"""采集层 1：国家级日度/周度行情 + 期货日线。

来源
  A. 农业农村部 pfsc.agri.cn  /api/FarmDaily/list      全国日度批发价（9 品类）
  B. 农业农村部 pfsc.agri.cn  /api/farmWeekly/pageList 全国周度行情（含表 1/表 2）
  C. 新浪财经期货日 K                                  豆粕/玉米/鸡蛋/生猪
输出
  raw/*.json  原始响应
  data_daily.csv / data_weekly.csv / data_futures.csv
"""
from __future__ import annotations

import csv
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(r"D:\蛙蛙呱呱\内蒙古七类蛋白调研_2026-11-12\底稿版")
RAW = ROOT / "raw"
RAW.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
      "Content-Type": "application/json;charset=UTF-8",
      "Referer": "https://pfsc.agri.cn/"}
BASE = "https://pfsc.agri.cn"

START, END = "2026-09-20", "2026-11-13"


def post(path: str, data: dict, timeout: int = 40):
    req = urllib.request.Request(BASE + path, data=json.dumps(data).encode(), headers=UA, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace"))


def get_text(url: str, timeout: int = 40) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("gbk", "replace")


# ---------------------------------------------------------------- 日度
ANIMAL = ["猪肉", "牛肉", "羊肉", "鸡蛋", "白条鸡"]
AQUATIC = ["鲫鱼", "鲤鱼", "白鲢鱼", "大带鱼", "草鱼", "花鲢鱼", "大黄花鱼"]


def parse_daily(rec: dict) -> dict:
    out = {"date": rec.get("daylyDate") or (rec.get("createDate") or "")[:10]}
    for field in ("animalConclusion", "aquaticConclusion"):
        text = rec.get(field) or ""
        for name in ANIMAL + AQUATIC:
            m = re.search(name + r"[^0-9]{0,12}?([0-9]+\.?[0-9]*)元/公斤", text)
            if m:
                out[name] = float(m.group(1))
    return out


def collect_daily() -> list[dict]:
    rows, page = [], 1
    while True:
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
    rows = [r for r in rows if r.get("date", "")[:10] >= START]
    rows.sort(key=lambda r: r["date"])
    (RAW / "farm_daily.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows


# ---------------------------------------------------------------- 周度
ROW = re.compile(r"(\d{1,3}\.\d{2})(\d{1,3}\.\d{2})(\d{1,3}\.\d{2})(-?\d{1,2}\.\d%)?(-?\d{1,2}\.\d%)?")

def parse_weekly(rec: dict) -> list[dict]:
    """从 contentstr 解析表 1（畜禽）与表 2（水产）：上周 / 本周 / 去年同期 / 环比 / 同比。"""
    text = (rec.get("contentstr") or "").replace("\u3000", " ")
    date = rec.get("weeklyDate") or ""
    out = []
    for name in ANIMAL + ["草鱼", "鲫鱼", "鲤鱼", "白鲢鱼", "花鲢鱼", "大带鱼", "大黄花鱼"]:
        idx = text.find(name + "  ")
        if idx < 0:
            idx = text.find(name)
        if idx < 0:
            continue
        seg = text[idx + len(name): idx + len(name) + 60]
        m = ROW.search(seg)
        if not m:
            continue
        out.append({"week": date, "item": name, "last": float(m.group(1)), "this": float(m.group(2)),
                    "yoy_base": float(m.group(3)), "mom_pct": m.group(4) or "", "yoy_pct": m.group(5) or ""})
    return out


def collect_weekly() -> list[dict]:
    d = post("/api/farmWeekly/pageList", {"pageNum": 1, "pageSize": 60})
    rows = []
    for rec in d["content"]["list"]:
        wd = rec.get("weeklyDate") or ""
        if wd and "2026" in wd and wd >= "20260920":
            rows.extend(parse_weekly(rec))
    (RAW / "farm_weekly.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows


# ---------------------------------------------------------------- 期货
FUT = {"M0": "豆粕主连", "C0": "玉米主连", "JD0": "鸡蛋主连", "LH0": "生猪主连"}


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
        for k in arr:
            if START <= k["d"] <= END:
                rows.append({"date": k["d"], "symbol": sym, "name": label,
                             "open": float(k["o"]), "high": float(k["h"]), "low": float(k["l"]), "close": float(k["c"])})
        print(f"  {sym} {label}: {sum(1 for r in rows if r['symbol']==sym)} 天")
    (RAW / "futures_daily.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows


def write_csv(path: Path, header: list[str], rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow([r.get(h, "") for h in header])


if __name__ == "__main__":
    daily = collect_daily()
    print("日度记录:", len(daily), daily[0]["date"] if daily else "-", "→", daily[-1]["date"] if daily else "-")
    cols = ["date"] + ANIMAL + [a for a in AQUATIC if any(a in r for r in daily)]
    write_csv(ROOT / "data_daily.csv", cols, daily)

    weekly = collect_weekly()
    print("周度记录:", len(weekly))
    write_csv(ROOT / "data_weekly.csv", ["week", "item", "last", "this", "yoy_base", "mom_pct", "yoy_pct"], weekly)

    fut = collect_futures()
    print("期货记录:", len(fut))
    write_csv(ROOT / "data_futures.csv", ["date", "symbol", "name", "open", "high", "low", "close"], fut)

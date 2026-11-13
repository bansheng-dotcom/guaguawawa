# -*- coding: utf-8 -*-
"""采集层 4：产地/销地价差（全国富士苹果分市场）+ 产地经营面（宁城/通辽）+ 人口基数。

来源
  A. 证券之星转载农业农村部「全国主要批发市场富士苹果价格行情」2026-10-28 / 2026-11-11
  B. 一亩田「10月28日苹果全国价格行情分析」（产地 vs 销地价差）
  C. 内蒙古林草局·宁城县林果产业（面积/产量/产值）
  D. 通辽市林草局·塞外红苹果（面积/产地价）
  E. 内蒙古 2025 年统计公报（人口/收入/社零）
输出
  data/全国苹果分市场_两期.csv / data/产地_内蒙古.csv / data/基础数.json
"""
from __future__ import annotations

import csv
import gzip
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
DATA = ROOT / "data"
RAW.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"}

APPLE_PAGES = {
    "2026-10-28": "https://futures.stockstar.com/IG2026102800025651.shtml",
    "2026-11-11": "http://futures.stockstar.com/IG2026111100024473.shtml",
}
YMT = "https://www.ymt.com/hangqing/hqfx-pingguo-3-0-1417291-20261028"
NINGCHENG = "http://lcj.nmg.gov.cn/xxgk/zxzx/202509/t20250930_2798125.html"
TONGLIAO = "https://www.tongliao.gov.cn/zjtl/fztl/tltf/nmy/202512/t20251216_1021786.html"
BULLETIN = "https://www.nmg.gov.cn/tjsj/tjsj/tjgb/202604/t20260409_2886936.html"


def get(url: str, timeout: int = 40) -> str:
    req = urllib.request.Request(url, headers={**UA, "Accept-Encoding": "gzip"})
    r = urllib.request.urlopen(req, timeout=timeout)
    raw = r.read()
    if r.headers.get("Content-Encoding") == "gzip":
        raw = gzip.decompress(raw)
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def tables(html: str) -> list[list[str]]:
    out = []
    for tr in re.findall(r"<tr[\s\S]*?</tr>", html, flags=re.I):
        cells = [re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ").strip()
                 for c in re.findall(r"<t[dh][\s\S]*?</t[dh]>", tr, flags=re.I)]
        cells = [c for c in cells if c]
        if len(cells) >= 2:
            out.append(cells)
    return out


def text_of(html: str) -> str:
    body = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    body = re.sub(r"<style[\s\S]*?</style>", " ", body, flags=re.I)
    t = re.sub(r"<[^>]+>", "\n", body).replace("&nbsp;", " ")
    return "\n".join(l.strip() for l in t.split("\n") if l.strip())


def collect_apple() -> list[dict]:
    rows = []
    for date, url in APPLE_PAGES.items():
        html = get(url)
        (RAW / f"apple_market_{date}.html").write_text(html, encoding="utf-8", errors="replace")
        for r in tables(html):
            if len(r) < 2:
                continue
            name, price = r[0].strip(), r[1].strip()
            if not re.search(r"市场|交易中心|物流|农贸", name):
                continue
            m = re.search(r"([0-9]+\.?[0-9]*)", price)
            if not m:
                continue
            rows.append({"date": date, "market": name, "price": float(m.group(1)), "unit": "元/公斤",
                         "region": "内蒙古" if re.search(r"内蒙|呼和浩特|赤峰|包头|鄂尔多斯|通辽", name) else "外省"})
    print("苹果分市场:", len(rows), "行，市场数", len({r['market'] for r in rows}))
    return rows


def collect_origin_text() -> dict:
    facts = {}
    ymt = text_of(get(YMT))
    (RAW / "ymt_apple_1028.html").write_text(ymt, encoding="utf-8")
    for line in ymt.split("\n"):
        if re.search(r"产地|销地|元/斤|元/公斤|价差", line) and len(line) < 400:
            facts.setdefault("ymt", []).append(line)
    nc = text_of(get(NINGCHENG))
    (RAW / "ningcheng.html").write_text(nc, encoding="utf-8")
    for line in nc.split("\n"):
        if re.search(r"万亩|万吨|产值|销售", line):
            facts.setdefault("ningcheng", []).append(line[:300])
    tl = text_of(get(TONGLIAO))
    (RAW / "tongliao.html").write_text(tl, encoding="utf-8")
    for line in tl.split("\n"):
        if re.search(r"塞外红|万亩|万吨|元/", line):
            facts.setdefault("tongliao", []).append(line[:300])
    bl = text_of(get(BULLETIN))
    (RAW / "bulletin_2025.html").write_text(bl, encoding="utf-8")
    for line in bl.split("\n"):
        if re.search(r"常住人口|万人|社会消费品零售总额", line):
            facts.setdefault("bulletin", []).append(line[:200])
    return facts


if __name__ == "__main__":
    rows = collect_apple()
    with (DATA / "全国苹果分市场_两期.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "market", "region", "price", "unit"])
        for r in rows:
            w.writerow([r["date"], r["market"], r["region"], r["price"], r["unit"]])

    facts = collect_origin_text()
    (DATA / "产地_原文摘要.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in facts.items():
        print(f"\n--- {k} ({len(v)}) ---")
        for line in v[:6]:
            print(" ", line[:200])

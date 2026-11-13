# -*- coding: utf-8 -*-
"""采集层 2：内蒙古本地批发市场日度水果报价 + 盟市零售周报。

来源
  A. 食品商务网 21food 批发市场行情（呼和浩特保全庄 1327 / 东瓦窑 268 / 包头友谊 2299），
     按日期分页，逐页抽取「品名 / 价格 / 报价日期」。
  B. 呼和浩特市商务局「生活必需品市场运行分析」周报（水果零售均价与分品种）。
  C. 乌兰察布市发改委「粮油副食品价格分析」周报（含水果）。
输出
  raw/21food_*.html、raw/hh_swj_*.html、raw/wlcb_*.html
  data/批发_保全庄_日度.csv / 批发_东瓦窑_日度.csv / 批发_包头_日度.csv / 零售_呼市周度.csv
"""
from __future__ import annotations

import csv
import gzip
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
DATA = ROOT / "data"
RAW.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
      "Accept-Language": "zh-CN,zh;q=0.9"}

FRUIT_WORDS = ["苹果", "香蕉", "梨", "葡萄", "西瓜", "蜜瓜", "哈密瓜", "香瓜", "甜瓜", "橘", "橙", "柑",
               "柚", "猕猴桃", "火龙果", "石榴", "草莓", "枣", "桃", "李", "杏", "樱桃", "蓝莓", "芒果",
               "菠萝", "凤梨", "榴莲", "荔枝", "龙眼", "柿", "山楂", "沙果", "海棠", "人参果", "百香果"]
NOT_FRUIT = {"苹果醋", "苹果汁", "枣糕", "桃酥", "梨膏"}


def get(url: str, timeout: int = 30) -> str:
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
        cells = [re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ").replace("&#160;", " ").strip()
                 for c in re.findall(r"<t[dh][\s\S]*?</t[dh]>", tr, flags=re.I)]
        cells = [c for c in cells if c]
        if cells:
            out.append(cells)
    return out


def is_fruit(name: str) -> bool:
    if any(bad in name for bad in NOT_FRUIT):
        return False
    return any(w in name for w in FRUIT_WORDS)


# ------------------------------------------------- A. 21food 批发市场
def crawl_21food(market_id: int, label: str, stop: str = "2026-09-20", max_pages: int = 240) -> list[dict]:
    rows, page, seen = [], 1, set()
    last_date = ""
    while page <= max_pages:
        url = f"https://wap.21food.cn/price/market/{market_id}-p{page}.html"
        cache = RAW / f"21food_{market_id}_p{page}.html"
        try:
            html = cache.read_text(encoding="utf-8", errors="replace") if cache.exists() else get(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{label}] p{page} ERR {type(exc).__name__}")
            page += 1
            continue
        if not cache.exists():
            cache.write_text(html, encoding="utf-8", errors="replace")
        rs = tables(html)
        dates = sorted({r[3] for r in rs if len(r) >= 4 and re.match(r"\d{4}-\d{2}-\d{2}", r[3])})
        if not dates:
            dates = sorted({d for d in re.findall(r"2026-\d{2}-\d{2}", html)})
        if dates:
            last_date = dates[-1]
        for r in rs:
            if len(r) < 4 or not re.match(r"\d{4}-\d{2}-\d{2}", r[3]):
                continue
            name, price = r[0].strip(), r[2].strip()
            m = re.search(r"([0-9]+\.?[0-9]*)", price)
            if not m or not is_fruit(name):
                continue
            key = (r[3], name)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"date": r[3], "market": label, "item": name,
                         "price_raw": price, "price": float(m.group(1)), "unit": "元/公斤"})
        if last_date and last_date < stop:
            break
        page += 1
        time.sleep(0.15)
    rows.sort(key=lambda r: (r["date"], r["item"]))
    print(f"  {label}: {len(rows)} 条，{rows[0]['date'] if rows else '-'} → {rows[-1]['date'] if rows else '-'}，{page} 页")
    return rows


# ------------------------------------------------- B. 呼市商务局周报
SWJ = [
    ("2026-11-02~11-08", "http://swj.huhhot.gov.cn/tjxx/202611/t20261110_2049154.html"),
    ("2026-10-26~11-01", "http://swj.huhhot.gov.cn/tjxx/202611/t20261103_2047305.html"),
    ("2026-10-19~10-25", "http://swj.huhhot.gov.cn/tjxx/202610/t20261028_2045770.html"),
    ("2026-10-12~10-18", "http://swj.huhhot.gov.cn/tjxx/202610/t20261028_2045768.html"),
    ("2026-10-05~10-11", "http://swj.huhhot.gov.cn/tjxx/202610/t20261013_2042482.html"),
    ("2026-09-28~10-04", "http://swj.huhhot.gov.cn/tjxx/202610/t20261008_2041345.html"),
    ("2026-09-21~09-27", "http://swj.huhhot.gov.cn/tjxx/202609/t20260928_2040314.html"),
    ("2026-09-14~09-20", "http://swj.huhhot.gov.cn/tjxx/202609/t20260921_2038498.html"),
    ("2026-09-07~09-13", "http://swj.huhhot.gov.cn/tjxx/202609/t20260914_2036284.html"),
]


def parse_swj(html: str, week: str) -> list[dict]:
    body = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<[^>]+>", "", body)
    text = text.replace("&nbsp;", " ").replace("&#160;", " ")
    text = re.sub(r"\s+", " ", text)
    out = []
    m = re.search(r"水果[^。]{0,40}?平均零售价格(\d+\.?\d*)元[／/]公斤，环比(上涨|下降|持平)(\d+\.?\d*)?[％%]", text)
    if not m:
        m = re.search(r"(\d+)种水果[^。]{0,60}?平均零售价格(\d+\.?\d*)元[／/]公斤，环比(上涨|下降|持平)(\d+\.?\d*)?[％%]", text)
    if m:
        g = m.groups()
        if len(g) == 3 and m.re.pattern.startswith("水果"):
            out.append({"week": week, "item": "8种水果均价", "price": float(m.group(1)),
                        "mom_pct": float(m.group(3) or 0) * (1 if m.group(2) == "上涨" else -1 if m.group(2) == "下降" else 0),
                        "kind": "retail_avg"})
        else:
            out.append({"week": week, "item": "8种水果均价", "price": float(m.group(2)),
                        "mom_pct": float(m.group(4) or 0) * (1 if m.group(3) == "上涨" else -1 if m.group(3) == "下降" else 0),
                        "kind": "retail_avg"})
    # 分品种：苹果13.88元／公斤，环比上涨2.8％
    for name, price, direction, pct in re.findall(
            r"(苹果|香蕉|梨|西瓜|柑橘|芒果|葡萄|桃|哈密瓜|火龙果|猕猴桃)(\d+\.?\d*)元[／/]公斤，环比(上涨|下降|持平)(\d+\.?\d*)?[％%]", text):
        out.append({"week": week, "item": name, "price": float(price),
                    "mom_pct": float(pct or 0) * (1 if direction == "上涨" else -1 if direction == "下降" else 0),
                    "kind": "retail_item"})
    return out


def collect_swj() -> list[dict]:
    rows = []
    for week, url in SWJ:
        try:
            html = get(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  [swj] {week} ERR {type(exc).__name__}")
            continue
        (RAW / f"hh_swj_{week[:10].replace('-', '')}.html").write_text(html, encoding="utf-8", errors="replace")
        rows.extend(parse_swj(html, week))
    print(f"  呼市商务局：{len(rows)} 条，{len({r['week'] for r in rows})} 周")
    return rows


# ------------------------------------------------- C. 乌兰察布发改委周报
WLCB = [
    ("2026-11-05", "https://fgw.wulanchabu.gov.cn/jgsf/2035331.html"),
    ("2026-10-29", "https://fgw.wulanchabu.gov.cn/jgsf/2032221.html"),
    ("2026-10-22", "https://fgw.wulanchabu.gov.cn/jgsf/2029969.html"),
    ("2026-10-15", "https://fgw.wulanchabu.gov.cn/jgsf/2027461.html"),
]


def collect_wlcb() -> list[dict]:
    rows = []
    for date, url in WLCB:
        try:
            html = get(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  [wlcb] {date} ERR {type(exc).__name__}")
            continue
        (RAW / f"wlcb_{date.replace('-', '')}.html").write_text(html, encoding="utf-8", errors="replace")
        body = re.sub(r"<[^>]+>", " ", html)
        body = re.sub(r"\s+", " ", body)
        for name, price in re.findall(r"(苹果|香蕉|梨|葡萄|西瓜|柑橘)[^0-9]{0,8}([0-9]+\.[0-9]{1,2})元/500克", body):
            rows.append({"date": date, "market": "乌兰察布发改委", "item": name,
                         "price_raw": price, "price": float(price), "unit": "元/斤"})
    print(f"  乌兰察布：{len(rows)} 条")
    return rows


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow([r.get(h, "") for h in header])


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == "market":
        # python collect_local.py market <id> <label> <stop_date> <max_pages>
        mid, label, stop, pages = int(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5])
        rows = crawl_21food(mid, label, stop=stop, max_pages=pages)
        write_csv(DATA / f"批发_{label}_日度.csv", ["date", "market", "item", "price", "unit"], rows)
        raise SystemExit(0)

    print("[1] 21food 批发市场")
    bqz = crawl_21food(1327, "呼和浩特保全庄", max_pages=200)
    dwy = crawl_21food(268, "呼和浩特东瓦窑")
    bt = crawl_21food(2299, "包头友谊")
    for rows, fn in ((bqz, "批发_保全庄_日度.csv"), (dwy, "批发_东瓦窑_日度.csv"), (bt, "批发_包头_日度.csv")):
        write_csv(DATA / fn, ["date", "market", "item", "price", "unit"], rows)
    (RAW / "21food_all.json").write_text(json.dumps(bqz + dwy + bt, ensure_ascii=False, indent=1), encoding="utf-8")

    print("[2] 呼市商务局周报")
    swj = collect_swj()
    write_csv(DATA / "零售_呼市周度.csv", ["week", "item", "price", "mom_pct", "kind"], swj)

    print("[3] 乌兰察布发改委")
    wl = collect_wlcb()
    write_csv(DATA / "零售_乌兰察布周度.csv", ["date", "market", "item", "price", "unit"], wl)

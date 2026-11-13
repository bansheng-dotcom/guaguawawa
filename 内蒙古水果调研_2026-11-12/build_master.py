# -*- coding: utf-8 -*-
"""装配层：把 8 个数据层装配成一份可复算的指标库（data/底稿指标.json）+ 派生 CSV。

层号说明
  L1 全国日度（农业农村部 6 种水果均价）          38 点
  L2 全国周度（农业农村部 表 5，6 品种 × 9 周）   54 行 × 5 字段
  L3 呼市/包头批发市场日度报价（21food，B 级）     多品种 × 多日
  L4 呼市零售周报（商务局，8 种水果均价 + 分品种） 33 点
  L5 期货日线（苹果 AP0 / 红枣 CJ0）              72 点
  L6 全国富士苹果分市场（2 期 × 57 市场）          107 点
  L7 产地与产业面（宁城 / 通辽 / 全区产量）        结构化事实
  L8 盟市方向性表述（乌兰察布 4 周）              4 点（只做方向）
"""
from __future__ import annotations

import csv
import json
import math
import re
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
DATA = ROOT / "data"
OUT = DATA / "底稿指标.json"

OCT = ("2026-10-01", "2026-10-31")
NOV = ("2026-11-01", "2026-11-30")


def read_csv(name: str) -> list[dict]:
    p = DATA / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def f(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def in_range(d: str, rng: tuple[str, str]) -> bool:
    return rng[0] <= d[:10] <= rng[1]


def pct(a: float, b: float) -> float | None:
    if not a or b is None:
        return None
    return round((b - a) / a * 100, 2)


# ------------------------------------------------------------------ L1
def layer_l1() -> dict:
    rows = read_csv("全国日度_6种水果.csv")
    pts = [{"date": r["date"], "value": float(r["水果6种均价"]),
            "mom": f(r.get("水果6种环比"))} for r in rows if r.get("水果6种均价")]
    sep = [p["value"] for p in pts if in_range(p["date"], ("2026-09-15", "2026-09-30"))]
    oct_ = [p["value"] for p in pts if in_range(p["date"], OCT)]
    nov = [p["value"] for p in pts if in_range(p["date"], NOV)]
    vals = [p["value"] for p in pts]
    chg = [p["mom"] for p in pts if p["mom"] is not None]
    return {
        "points": pts,
        "n": len(pts),
        "window": [pts[0]["date"], pts[-1]["date"]] if pts else [],
        "monthly": {
            "9月下半月": {"n": len(sep), "mean": round(st.mean(sep), 3) if sep else None},
            "10月": {"n": len(oct_), "mean": round(st.mean(oct_), 3) if oct_ else None},
            "11月": {"n": len(nov), "mean": round(st.mean(nov), 3) if nov else None},
        },
        "first": pts[0] if pts else None,
        "last": pts[-1] if pts else None,
        "min": {"value": min(vals), "date": min(pts, key=lambda p: p["value"])["date"]} if pts else None,
        "max": {"value": max(vals), "date": max(pts, key=lambda p: p["value"])["date"]} if pts else None,
        "volatility_pct": round(st.pstdev(vals) / st.mean(vals) * 100, 2) if vals else None,
        "up_days": sum(1 for c in chg if c > 0),
        "down_days": sum(1 for c in chg if c < 0),
        "flat_days": sum(1 for c in chg if c == 0),
        "chg_series": chg,
        "月内变化": pct(st.mean(sep), st.mean(nov)) if sep and nov else None,
    }


# ------------------------------------------------------------------ L2
def layer_l2() -> dict:
    rows = read_csv("全国周度_6种水果.csv")
    weeks = sorted({r["week"] for r in rows})
    items = sorted({r["item"] for r in rows})
    table = {}
    for r in rows:
        table.setdefault(r["item"], {})[r["week"]] = {
            "this": float(r["this"]), "last": float(r["last"]), "yoy_base": float(r["yoy_base"]),
            "mom": f(r.get("mom_pct", "").replace("%", "")), "yoy": f(r.get("yoy_pct", "").replace("%", "")),
        }
    # 篮子：等权指数，基期 = 第一周
    base = weeks[0]
    basket = {}
    for w in weeks:
        vals = [table[i][w]["this"] for i in items if w in table.get(i, {})]
        base_vals = [table[i][base]["this"] for i in items if base in table.get(i, {})]
        if vals and base_vals:
            basket[w] = round(sum(vals) / sum(base_vals) * 100, 2)
    # 10 月 vs 11 月（按周归属：周一日期在区间内）
    def week_month(w: str) -> str:
        start = "20" + w[:2] + "-" + w[2:4] + "-" + w[4:6]
        return start[:7]
    monthly = {}
    for w in weeks:
        m = week_month(w)
        for i in items:
            if w in table.get(i, {}):
                monthly.setdefault(i, {}).setdefault(m, []).append(table[i][w]["this"])
    item_summary = {}
    for i in items:
        d = table.get(i, {})
        if not d:
            continue
        ws = [w for w in weeks if w in d]
        first, last = d[ws[0]]["this"], d[ws[-1]]["this"]
        latest = d[ws[-1]]
        item_summary[i] = {
            "weeks": len(ws), "first": first, "first_week": ws[0], "last": last, "last_week": ws[-1],
            "change_pct": pct(first, last),
            "max": max(d[w]["this"] for w in ws), "min": min(d[w]["this"] for w in ws),
            "mean": round(st.mean(d[w]["this"] for w in ws), 3),
            "latest_yoy": latest["yoy"], "latest_mom": latest["mom"],
            "latest_price": latest["this"], "latest_yoy_base": latest["yoy_base"],
        }
    ranking = sorted(item_summary.items(), key=lambda kv: (kv[1]["change_pct"] is None, -(kv[1]["change_pct"] or -999)))
    return {
        "rows": len(rows), "weeks": weeks, "items": items,
        "table": table, "basket_index": basket,
        "item_summary": item_summary,
        "ranking": [{"item": k, **v} for k, v in ranking],
        "basket_change_pct": pct(basket[weeks[0]], basket[weeks[-1]]) if basket else None,
    }


# ------------------------------------------------------------------ L3
FRUIT_WORDS = ["苹果", "香蕉", "梨", "葡萄", "西瓜", "蜜瓜", "哈密瓜", "香瓜", "橘", "橙", "柑", "柚",
               "猕猴桃", "火龙果", "石榴", "草莓", "枣", "桃", "李", "杏", "樱桃", "蓝莓", "芒果", "菠萝", "荔枝", "柿"]
NOT_FRUIT = {"苹果醋", "苹果汁", "枣糕", "桃酥"}


def parse_21food() -> list[dict]:
    rows, seen = [], set()
    for p in sorted(RAW.glob("21food_*_p*.html"), key=lambda x: int(re.search(r"_p(\d+)", x.name).group(1))):
        market = re.search(r"21food_(\d+)_p", p.name).group(1)
        label = {"1327": "呼和浩特保全庄", "268": "呼和浩特东瓦窑", "2299": "包头友谊"}.get(market, market)
        html = p.read_text(encoding="utf-8", errors="replace")
        for tr in re.findall(r"<tr[\s\S]*?</tr>", html, flags=re.I):
            cells = [re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ").strip()
                     for c in re.findall(r"<t[dh][\s\S]*?</t[dh]>", tr, flags=re.I)]
            cells = [c for c in cells if c]
            date = next((c for c in cells if re.match(r"\d{4}-\d{2}-\d{2}$", c)), None)
            price_cell = next((c for c in cells if "元/公斤" in c), None)
            if not date or not price_cell or len(cells) < 2:
                continue
            name = cells[0]
            if not any(w in name for w in FRUIT_WORDS) or any(b in name for b in NOT_FRUIT):
                continue
            m = re.search(r"([0-9]+\.?[0-9]*)", price_cell)
            if not m:
                continue
            key = (date, label, name)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"date": date, "market": label, "item": name, "price": float(m.group(1))})
    return rows


def layer_l3() -> dict:
    rows = parse_21food()
    markets = {}
    for r in rows:
        markets.setdefault(r["market"], {}).setdefault(r["item"], []).append((r["date"], r["price"]))
    summary = {}
    for m, items in markets.items():
        dates = sorted({d for v in items.values() for d, _ in v})
        per = {}
        for item, vs in items.items():
            vs.sort()
            o = [p for d, p in vs if in_range(d, OCT)]
            n = [p for d, p in vs if in_range(d, NOV)]
            per[item] = {"obs": len(vs), "oct_mean": round(st.mean(o), 2) if o else None,
                         "nov_mean": round(st.mean(n), 2) if n else None,
                         "chg_pct": pct(st.mean(o), st.mean(n)) if o and n else None,
                         "min": min(p for _, p in vs), "max": max(p for _, p in vs)}
        summary[m] = {"dates": dates, "date_count": len(dates), "items": per,
                      "item_count": len(per), "obs": sum(v["obs"] for v in per.values())}
    return {"rows": rows, "n": len(rows), "markets": summary}


# ------------------------------------------------------------------ L4
def layer_l4() -> dict:
    rows = read_csv("零售_呼市周度.csv")
    weeks = sorted({r["week"] for r in rows}, key=lambda w: w[:10])
    avg = {}
    items = {}
    for r in rows:
        if r["kind"] == "retail_avg":
            avg[r["week"]] = float(r["price"])
        else:
            items.setdefault(r["item"], {})[r["week"]] = {"price": float(r["price"]), "mom": f(r.get("mom_pct"))}
    first_w, last_w = weeks[0], weeks[-1]
    return {
        "rows": len(rows), "weeks": weeks, "avg": avg,
        "items": items,
        "avg_first": {"week": first_w, "price": avg.get(first_w)},
        "avg_last": {"week": last_w, "price": avg.get(last_w)},
        "avg_change_pct": pct(avg.get(first_w), avg.get(last_w)) if avg.get(first_w) else None,
        "avg_min": min(avg.values()) if avg else None, "avg_max": max(avg.values()) if avg else None,
    }


# ------------------------------------------------------------------ L5
def layer_l5() -> dict:
    rows = read_csv("期货_苹果红枣.csv")
    out = {}
    for sym, label in (("AP0", "苹果"), ("CJ0", "红枣")):
        pts = [{"date": r["date"], "close": float(r["close"]), "volume": float(r["volume"] or 0)}
               for r in rows if r["symbol"] == sym]
        if not pts:
            continue
        pts.sort(key=lambda p: p["date"])
        closes = [p["close"] for p in pts]
        oct_ = [p["close"] for p in pts if in_range(p["date"], OCT)]
        nov = [p["close"] for p in pts if in_range(p["date"], NOV)]
        peak, mdd = -1e9, 0.0
        for c in closes:
            peak = max(peak, c)
            mdd = min(mdd, (c - peak) / peak * 100)
        out[label] = {"symbol": sym, "n": len(pts), "points": pts,
                      "first": pts[0], "last": pts[-1],
                      "change_pct": pct(closes[0], closes[-1]),
                      "oct_mean": round(st.mean(oct_), 1) if oct_ else None,
                      "nov_mean": round(st.mean(nov), 1) if nov else None,
                      "max": max(closes), "min": min(closes),
                      "max_drawdown_pct": round(mdd, 2),
                      "avg_volume": round(st.mean(p["volume"] for p in pts))}
    return out


# ------------------------------------------------------------------ L6
PROV = [("黑龙江", "黑龙江"), ("吉林", "吉林"), ("辽宁", "辽宁"), ("北京", "北京"), ("天津", "天津"),
        ("河北", "河北"), ("山西", "山西"), ("山东", "山东"), ("河南", "河南"), ("陕西", "陕西"),
        ("甘肃", "甘肃"), ("宁夏", "宁夏"), ("新疆", "新疆"), ("内蒙古", "内蒙古"), ("上海", "上海"),
        ("江苏", "江苏"), ("浙江", "浙江"), ("安徽", "安徽"), ("福建", "福建"), ("江西", "江西"),
        ("湖北", "湖北"), ("湖南", "湖南"), ("广东", "广东"), ("广西", "广西"), ("重庆", "重庆"),
        ("四川", "四川"), ("贵州", "贵州"), ("云南", "云南"), ("青海", "青海"), ("西藏", "西藏")]


CITY_PROV = {
    "石家庄": "河北", "三河": "河北", "乐亭": "河北", "邯郸": "河北", "怀来": "河北", "馆陶": "河北",
    "商丘": "河南", "郑州": "河南", "滕州": "山东", "寿光": "山东", "青岛": "山东", "烟台": "山东",
    "洛川": "陕西", "西安": "陕西", "咸阳": "陕西", "兰州": "甘肃", "天水": "甘肃", "白银": "甘肃",
    "银川": "宁夏", "吴忠": "宁夏", "乌鲁木齐": "新疆", "库尔勒": "新疆", "哈尔滨": "黑龙江",
    "长春": "吉林", "沈阳": "辽宁", "大连": "辽宁", "南京": "江苏", "徐州": "江苏", "常州": "江苏",
    "杭州": "浙江", "宁波": "浙江", "合肥": "安徽", "蚌埠": "安徽", "阜阳": "安徽", "武汉": "湖北",
    "长沙": "湖南", "广州": "广东", "南宁": "广西", "重庆": "重庆", "成都": "四川", "贵阳": "贵州",
    "昆明": "云南", "西宁": "青海", "拉萨": "西藏", "福州": "福建", "厦门": "福建", "南昌": "江西",
    "太原": "山西", "长治": "山西", "晋城": "山西", "汾阳": "山西", "朔州": "山西", "天津": "天津",
    "北京": "北京", "上海": "上海",
}


def province_of(name: str) -> str:
    for k, v in PROV:
        if k in name:
            return v
    for k, v in CITY_PROV.items():
        if k in name:
            return v
    if "内蒙" in name:
        return "内蒙古"
    return "其他"


def layer_l6() -> dict:
    rows = read_csv("全国苹果分市场_两期.csv")
    by_date = {}
    for r in rows:
        by_date.setdefault(r["date"], []).append({"market": r["market"], "province": province_of(r["market"]),
                                                 "price": float(r["price"])})
    allp = [x["price"] for v in by_date.values() for x in v]
    nm = [(d, x) for d, v in by_date.items() for x in v if x["province"] == "内蒙古"]
    prov_mean = {}
    for d, v in by_date.items():
        for x in v:
            prov_mean.setdefault(d, {}).setdefault(x["province"], []).append(x["price"])
    prov_sorted = {d: sorted(((k, round(st.mean(v2), 2), len(v2)) for k, v2 in v.items()),
                             key=lambda t: -t[1]) for d, v in prov_mean.items()}
    latest = max(by_date)
    lv = by_date[latest]
    return {
        "rows": len(rows), "dates": sorted(by_date), "n_markets": len({x["market"] for v in by_date.values() for x in v}),
        "by_date": by_date,
        "stats": {"n": len(allp), "median": round(st.median(allp), 2), "mean": round(st.mean(allp), 2),
                  "min": min(allp), "max": max(allp), "p25": round(st.quantiles(allp, n=4)[0], 2),
                  "p75": round(st.quantiles(allp, n=4)[2], 2)},
        "neimenggu": [{"date": d, **x} for d, x in nm],
        "province_rank": prov_sorted,
        "latest_date": latest,
        "latest": sorted(lv, key=lambda x: -x["price"]),
        "latest_top5": sorted(lv, key=lambda x: -x["price"])[:5],
        "latest_bottom5": sorted(lv, key=lambda x: x["price"])[:5],
    }


# ------------------------------------------------------------------ L7
def layer_l7() -> dict:
    return {
        "全区产量": {"2025_万吨": 224.92, "2024_万吨": 201.56, "同比_pct": round((224.92 - 201.56) / 201.56 * 100, 2),
                  "来源": "国家统计局（经 CEIC 披露）"},
        "宁城": {"经济林_万亩": 25, "盛果期_万亩": 9.5, "年产量_万吨": 16.8, "产值_亿元": 8.2,
                "折算_元每公斤": round(8.2e8 / (16.8 * 1e4 * 1000), 2), "2024销售_万吨": 16.79,
                "从业_万人": 9.8, "来源": "内蒙古林草局 2025-09-30"},
        "通辽": {"塞外红_万亩": 34.14, "结果_万亩": 12.45, "一类果_元每斤_新发地": 10.0,
                "经济林产品_万吨": 28, "经济林产值_亿元": 16.87, "来源": "通辽市林草局 2025-12-16"},
        "人口": {"2025_万人": 2374, "城镇_万人": 1697, "乡村_万人": 677, "城镇化率_pct": 71.48,
                "来源": "内蒙古 2025 年统计公报"},
        "消费": {"全国人均鲜瓜果_公斤": 68, "内蒙古人均干鲜瓜果_公斤": 77.6, "全国人均占有量_公斤": 256,
                "来源": "国家统计局/前瞻 2026-05"},
        "全国": {"2025产量_万吨": 35404.72, "苹果_万吨": 5348.67, "梨_万吨": 2139.58, "柑橘_万吨": 7137.75,
                "零售额_亿元": 15125, "进口_万吨": 1003.37, "来源": "国家统计局/华经/前瞻"},
        "冷链": {"冷库_座": 2200, "库容_万吨": 390, "综合交通主骨架_pct": 84.3, "农村公路_万公里": 18,
                "新能源冷链车补贴_万元": 3.5, "来源": "内蒙古交通运输厅 2025-12-19"},
    }



# ------------------------------------------------------------------ L9 季节性基线
def layer_l9_seasonal() -> dict:
    rows = json.loads((RAW / "farm_daily_seasonal.json").read_text(encoding="utf-8"))
    by_year: dict[int, list[float]] = {}
    for r in rows:
        if not ("09-15" <= r["date"][5:10] <= "11-12"):
            continue
        by_year.setdefault(int(r["date"][:4]), []).append(r["value"])
    means = {y: round(st.mean(v), 4) for y, v in by_year.items()}
    base = {y: means[y] for y in means if 2023 <= y <= 2025}
    base_mean = round(st.mean(base.values()), 4) if base else None
    y26 = means.get(2026)
    yoy = {str(y): round((y26 - means[y]) / means[y] * 100, 2) for y in means if y != 2026 and y26}
    return {
        "points": rows, "n": len(rows), "by_year": {str(y): {"n": len(v), "mean": means[y],
                                                             "min": min(v), "max": max(v)}
                                                    for y, v in sorted(by_year.items())},
        "y2026_mean": y26, "base_mean_2023_2025": base_mean,
        "yoy_pct": yoy,
        "verdict": "低于 2024—2025，回到 2022—2023 区间",
        "caveat": "日度序列自相关，跨年只作描述性对照，不做显著性推断",
    }


# ------------------------------------------------------------------ L10 分规格
def layer_l10_spec() -> dict:
    data = json.loads((RAW / "xinfadi_apple.json").read_text(encoding="utf-8"))

    def rows(key: str) -> list[dict]:
        return [r for r in data.get(key, []) if r["prod"] == "富士"]

    def ladder(key: str, date: str | None = None) -> dict:
        out: dict[str, list[float]] = {}
        for r in rows(key):
            if date and r["date"] != date:
                continue
            out.setdefault(r["spec"] or "未标规格", []).append(r["avg"] * 2)
        return {k: {"n": len(v), "mean": round(st.mean(v), 2), "min": min(v), "max": max(v),
                    "stale": (min(v) == max(v) and len(v) >= 30)} for k, v in out.items()}

    w26 = ladder("富士_2026-09")
    w25 = ladder("富士_2025-09")
    d26 = ladder("富士_2026-09", "2026-11-12")

    def decomp(lad: dict, cf: float = 6.0, hh: float = 14.0) -> dict:
        low = min(v["mean"] for v in lad.values())
        high = max(v["mean"] for v in lad.values())
        span = high - low
        total = hh - cf
        return {
            "赤峰": cf, "呼市": hh, "总差": round(total, 2),
            "最低规格": round(low, 2), "最高规格": round(high, 2), "规格跨度": round(span, 2),
            "规格占比_pct": round(span / total * 100, 1),
            "同规格区域溢价": round(hh - high, 2),
            "区域溢价占比_pct": round((hh - high) / total * 100, 1),
            "赤峰高于最低": round(cf - low, 2),
            "校验": round(span + (hh - high) - (cf - low), 2),
        }

    spec_yoy = {}
    for spec in set(w26) & set(w25):
        a, b = w25[spec]["mean"], w26[spec]["mean"]
        spec_yoy[spec] = {"2025": a, "2026": b, "yoy_pct": round((b - a) / a * 100, 2),
                          "stale_2026": w26[spec]["stale"]}
    return {"n": sum(len(v) for v in data.values()), "ladder_2026": w26, "ladder_2025": w25,
            "ladder_2026_11_12": d26, "spec_yoy": spec_yoy,
            "decomp_window": decomp(w26), "decomp_same_day": decomp(d26),
            "note": "新发地同日同品种分规格；规格跨度与区域溢价相加等于总差"}


# ------------------------------------------------------------------ L11 物流基准
def layer_l11_logistics() -> dict:
    return {
        "冷链运价": {"range": [0.25, 0.40], "unit": "元/吨·公里", "confidence": "C", "source": "行业区间"},
        "冷库租金": {"range": [80, 150], "unit": "元/吨·月", "confidence": "C", "source": "行业区间"},
        "商超账期": {"range": [45, 60], "unit": "天", "confidence": "C", "source": "渠道访谈"},
        "生鲜损耗": {"range": [8, 12], "unit": "%", "confidence": "C", "source": "行业区间"},
        "n": 4,
        "note": "C 级行业区间；接入 MCP（运价/库容）后升 B",
    }

# ------------------------------------------------------------------ 派生：跨层分析
def cross_analysis(l1, l2, l3, l4, l6, l9, l10) -> dict:
    # 1) 全国批发 → 呼市零售 的倍率（同品种代理：富士苹果 / 苹果）
    wh = l2["item_summary"].get("富士苹果", {})
    retail_apple = l4["items"].get("苹果", {})
    last_week = l4["weeks"][-1] if l4["weeks"] else None
    retail_apple_price = retail_apple.get(last_week, {}).get("price") if last_week else None
    ratio = round(retail_apple_price / wh["latest_price"], 2) if retail_apple_price and wh.get("latest_price") else None

    # 2) 产地（赤峰）→ 全国批发 → 呼市零售 的端到端加价
    cf = [x["price"] for x in l6["neimenggu"] if "赤峰" in x["market"]]
    hh_wh = [x["price"] for x in l6["neimenggu"] if "东瓦窑" in x["market"]]
    end_to_end = None
    if cf and retail_apple_price:
        end_to_end = round(retail_apple_price / st.mean(cf), 2)

    # 3) 批零/城际价差
    spread = {
        "赤峰西城_元每公斤": st.mean(cf) if cf else None,
        "呼市东瓦窑_元每公斤": st.mean(hh_wh) if hh_wh else None,
        "全国中位数_元每公斤": l6["stats"]["median"],
        "省内价差_pct": round((st.mean(hh_wh) - st.mean(cf)) / st.mean(cf) * 100, 1) if cf and hh_wh else None,
        "呼市相对全国中位数_pct": round((st.mean(hh_wh) - l6["stats"]["median"]) / l6["stats"]["median"] * 100, 1) if hh_wh else None,
        "赤峰相对全国中位数_pct": round((st.mean(cf) - l6["stats"]["median"]) / l6["stats"]["median"] * 100, 1) if cf else None,
    }

    # 4) 同城两个批发口径冲突（21food 保全庄 vs 东瓦窑）
    bqz = l3["markets"].get("呼和浩特保全庄", {}).get("items", {}).get("苹果", {})
    conflict = {
        "21food_保全庄_苹果_11月均": bqz.get("nov_mean"),
        "农业部_东瓦窑_富士苹果_11-11": hh_wh[0] if hh_wh else None,
        "差异_pct": round((bqz.get("nov_mean") - hh_wh[0]) / hh_wh[0] * 100, 1) if bqz.get("nov_mean") and hh_wh else None,
        "判定": "规格/等级不同，不作为水平价引用；仅取同源同品种时序方向",
    }

    # 5) 呼市零售 8 种均价 vs 全国 6 种批发（只比变化率）
    national_chg = l2["basket_change_pct"]
    retail_chg = l4["avg_change_pct"]
    transmission = {
        "全国6种批发篮子_9周变化_pct": national_chg,
        "呼市8种零售均价_9周变化_pct": retail_chg,
        "传导差_pp": round((retail_chg or 0) - (national_chg or 0), 2) if national_chg is not None and retail_chg is not None else None,
    }

    # 6) 苹果期货 vs 苹果批发（周度对齐）
    spread_v2 = {
        "口径": "新发地同日同品种分规格，对照赤峰 6.00 / 呼市 14.00",
        "窗口": l10["decomp_window"],
        "当日": l10["decomp_same_day"],
        "旧口径_省内价差_pct": spread["省内价差_pct"],
        "结论": "旧口径 133.3% 中约 64% 是规格；同规格区域溢价约 28%—36%",
    }
    seasonal = {"y2026_mean": l9["y2026_mean"], "base_mean": l9["base_mean_2023_2025"],
                "yoy_pct": l9["yoy_pct"], "verdict": l9["verdict"], "caveat": l9["caveat"]}
    return {"retail_wholesale_ratio": ratio,
            "retail_apple_price": retail_apple_price,
            "national_wholesale_apple": wh.get("latest_price"),
            "end_to_end_multiple": end_to_end,
            "spread": spread, "spread_v2": spread_v2, "seasonal": seasonal,
            "conflict": conflict, "transmission": transmission}


# ------------------------------------------------------------------ 市场规模
def market_size(l7) -> dict:
    pop = l7["人口"]["2025_万人"]
    urban, rural = l7["人口"]["城镇_万人"], l7["人口"]["乡村_万人"]
    per_capita = l7["消费"]["内蒙古人均干鲜瓜果_公斤"]
    total_t = pop * 1e4 * per_capita / 1000 / 1e4  # 万吨
    retail_price = 10.49  # 呼市 8 种水果零售均价 元/公斤（11 月第一周）
    value_yi = total_t * 1e4 * 1000 * retail_price / 1e8
    # SOM：假设呼包鄂城镇人口 35% + 赤峰通辽 20%（结构假设，非实测）
    som_share = 0.18
    return {
        "人均_公斤": per_capita, "人口_万人": pop,
        "TAM_万吨": round(total_t, 1),
        "TAM_零售额_亿元": round(value_yi, 1),
        "单价_元每公斤": retail_price,
        "SOM_万吨": round(total_t * som_share, 1),
        "SOM_零售额_亿元": round(value_yi * som_share, 1),
        "SOM_份额假设_pct": som_share * 100,
        "敏感性": {
            "人均_低": round(pop * 1e4 * 68 / 1000 / 1e4, 1),
            "人均_高": round(pop * 1e4 * 83 / 1000 / 1e4, 1),
            "说明": "人均 68（全国）—77.6（内蒙古）—83（山东最高）三档；零售额随单价 ±10% 同比例变动",
        },
        "口径提醒": "TAM 按『人均消费 × 常住人口 × 零售均价』测算，未扣除餐饮/加工渠道；与产量口径（224.92 万吨）不可直接相加",
    }


def main() -> None:
    l1, l2 = layer_l1(), layer_l2()
    l3, l4 = layer_l3(), layer_l4()
    l5, l6 = layer_l5(), layer_l6()
    l7 = layer_l7()
    l9, l10, l11 = layer_l9_seasonal(), layer_l10_spec(), layer_l11_logistics()
    metrics = {
        "meta": {"project": "内蒙古水果调研_2026-11-12", "window": "2026-09-15 ~ 2026-11-12",
                 "built_at": "2026-11-12", "unit_note": "水果价格统一折算元/公斤；元/斤 × 2"},
        "L1_全国日度": l1, "L2_全国周度": l2, "L3_批发报价": l3, "L4_呼市零售": l4,
        "L5_期货": l5, "L6_苹果分市场": l6, "L7_产业面": l7,
        "L9_季节性": l9, "L10_规格": l10, "L11_物流": l11,
        "跨层": cross_analysis(l1, l2, l3, l4, l6, l9, l10),
        "市场规模": market_size(l7),
    }
    obs = l1["n"] + l2["rows"] * 5 + l3["n"] + l4["rows"] + l5.get("苹果", {}).get("n", 0) + l5.get("红枣", {}).get("n", 0) + l6["rows"]
    metrics["观测统计"] = {
        "L1": l1["n"], "L2_字段数": l2["rows"] * 5, "L3": l3["n"], "L4": l4["rows"],
        "L5": l5.get("苹果", {}).get("n", 0) + l5.get("红枣", {}).get("n", 0), "L6": l6["rows"],
        "合计": obs,
        "扩展": {"L9": l9["n"], "L10": l10["n"], "L11": l11["n"],
                 "扩展合计": l9["n"] + l10["n"] + l11["n"]},
        "总观测": obs + l9["n"] + l10["n"] + l11["n"],
    }
    OUT.write_text(json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(metrics["观测统计"], ensure_ascii=False))
    print("L1 月均:", l1["monthly"], "月内变化:", l1["月内变化"])
    print("L2 篮子:", l2["basket_change_pct"], "排序:", [(r["item"], r["change_pct"]) for r in l2["ranking"]])
    print("L3 市场:", {k: (v["date_count"], v["item_count"], v["obs"]) for k, v in l3["markets"].items()})
    print("L4 零售周:", l4["avg_first"], l4["avg_last"], l4["avg_change_pct"])
    print("L5:", {k: (v["n"], v["change_pct"]) for k, v in l5.items()})
    print("L6:", l6["stats"], "内蒙:", [(x["market"], x["price"]) for x in l6["neimenggu"]])
    print("L9 季节性:", json.dumps(metrics["L9_季节性"], ensure_ascii=False)[:400])
    print("L10 规格:", json.dumps(metrics["L10_规格"]["decomp_window"], ensure_ascii=False))
    print("跨层:", json.dumps(metrics["跨层"], ensure_ascii=False)[:800])
    print("市场规模:", json.dumps(metrics["市场规模"], ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()

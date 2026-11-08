# -*- coding: utf-8 -*-
"""S03 探索与产品分析 —— 能力域 3。

整合自 data-analytics-skills 的 `funnel-analysis` / `cohort-analysis` /
`segmentation-analysis` / `time-series-analysis` / `business-metrics-calculator`。

主张：**先定分母与分段，再谈数字**。本技能覆盖趋势 / 分组 / 漏斗 / 留存
cohort / RFM 分群 / SaaS 运营指标，以及时间序列（趋势+季节+异常）、
k-means 聚类分群、业务指标（SaaS 订阅 / 电商 GMV）。
"""
from __future__ import annotations

import math
import random
import statistics
from collections import Counter, defaultdict
from typing import Any, Dict, List

from . import _common as c

NAME = "explore"
DESC = ("探索与产品分析：trend / groupby / funnel / cohort / rfm / saas "
        "/ time_series / segment / metrics")


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)

    t = act.add_parser("trend", help="时间序列趋势（按日期聚合求和）")
    t.add_argument("--input", required=True)
    t.add_argument("--date", default="date")
    t.add_argument("--value", default="amount")

    g = act.add_parser("groupby", help="分组汇总（sum/mean/n）")
    g.add_argument("--input", required=True)
    g.add_argument("--group", default="channel")
    g.add_argument("--value", default="amount")

    f = act.add_parser("funnel", help="漏斗：逐步/整体转化率")
    f.add_argument("--input", required=True)
    f.add_argument("--stage", default="status")
    f.add_argument("--order", default=None, help="逗号分隔的阶段顺序，缺省按出现频次")

    co = act.add_parser("cohort", help="留存 cohort 矩阵（按 cohort 期 + 活跃期）")
    co.add_argument("--input", required=True)
    co.add_argument("--user", default="user_id")
    co.add_argument("--period", default="date")

    rfm = act.add_parser("rfm", help="RFM 分群（R/F/M 各四分位打分）")
    rfm.add_argument("--input", required=True)
    rfm.add_argument("--user", default="user_id")
    rfm.add_argument("--date", default="date")
    rfm.add_argument("--value", default="amount")

    sa = act.add_parser("saas", help="SaaS 运营指标（MRR/churn/LTV/ARPU，标量输入）")
    sa.add_argument("--mrr", type=float, required=True)
    sa.add_argument("--active_users", type=float, required=True)
    sa.add_argument("--churn_rate", type=float, required=True, help="月流失率，如 0.05")

    ts = act.add_parser("time_series", help="时间序列：趋势/季节强度/移动平均/异常检测")
    ts.add_argument("--input", required=True)
    ts.add_argument("--date", default="date")
    ts.add_argument("--value", default="amount")
    ts.add_argument("--window", type=int, default=3, help="滚动窗口（移动平均/中位数）")

    seg = act.add_parser("segment", help="k-means 聚类分群 + 画像 + 策略映射")
    seg.add_argument("--input", required=True)
    seg.add_argument("--features", required=True, help="逗号分隔的数值特征列")
    seg.add_argument("--k", type=int, default=3)
    seg.add_argument("--user", default="user_id")
    seg.add_argument("--seed", type=int, default=0)

    me = act.add_parser("metrics", help="业务指标：SaaS 订阅 / 电商 GMV/AOV")
    me.add_argument("--input", required=True)
    me.add_argument("--model", default="saas", choices=["saas", "ecommerce"])
    me.add_argument("--value", default="amount")
    me.add_argument("--customer", default="customer_id")
    me.add_argument("--month", default="month")
    me.add_argument("--cac_spend", type=float, default=None, help="营销费用（算 LTV:CAC）")


def run(args) -> Dict[str, Any]:
    if args.action == "saas":
        return _saas(args.mrr, args.active_users, args.churn_rate)
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    return {
        "trend": lambda: _trend(rows, args.date, args.value),
        "groupby": lambda: _groupby(rows, args.group, args.value),
        "funnel": lambda: _funnel(rows, args.stage, args.order),
        "cohort": lambda: _cohort(rows, args.user, args.period),
        "rfm": lambda: _rfm(rows, args.user, args.date, args.value),
        "time_series": lambda: _time_series(rows, args.date, args.value, args.window),
        "segment": lambda: _segment(rows, args.features, args.k, args.user, args.seed),
        "metrics": lambda: _metrics(rows, args.model, args.value, args.customer,
                                    args.month, args.cac_spend),
    }[args.action]()


# --------------------------------------------------------------------------- #
def _trend(rows, date_col, value_col):
    b: Dict[str, float] = defaultdict(float)
    for r in rows:
        try:
            b[str(r[date_col])] += float(r.get(value_col, 0) or 0)
        except (KeyError, ValueError):
            continue
    series = [{"date": k, "value": round(v, 2)} for k, v in sorted(b.items())]
    return {"type": "trend", "series": series,
            "total": round(sum(x["value"] for x in series), 2)}


def _groupby(rows, group_col, value_col):
    b: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        try:
            b[str(r[group_col])].append(float(r.get(value_col, 0) or 0))
        except (KeyError, ValueError):
            continue
    groups = [{"group": k, "sum": round(sum(v), 2),
               "mean": round(sum(v) / len(v), 2), "n": len(v)}
              for k, v in sorted(b.items(), key=lambda kv: -sum(kv[1]))]
    return {"type": "groupby", "groups": groups}


def _funnel(rows, stage_col, order):
    drop_warn = c.load_thresholds().get("funnel", {}).get("drop_warn_pct", 20.0)
    counts = Counter(str(r[stage_col]) for r in rows if r.get(stage_col))
    if order:
        order_list = [x.strip() for x in order.split(",")]
    else:
        order_list = [k for k, _ in counts.most_common()]
    stages = [{"stage": s, "count": counts.get(s, 0)} for s in order_list]
    base = stages[0]["count"] if stages else 1
    prev = base
    for s in stages:
        s["conversion_overall"] = round(s["count"] / base, 4) if base else 0
        s["conversion_step"] = round(s["count"] / prev, 4) if prev else 0
        step_drop = round((1 - s["conversion_step"]) * 100, 2) if s["count"] else 0.0
        s["step_drop_pct"] = step_drop
        s["drop_alert"] = step_drop >= drop_warn
        prev = s["count"] or 1
    return {"type": "funnel", "stages": stages,
            "drop_warn_pct": drop_warn,
            "note": f"相邻步骤转化率骤降≥{drop_warn}% 时 drop_alert=true，提示漏斗漏损"}


def _cohort(rows, user_col, period_col):
    """按首个 period 入组，逐期统计仍活跃的去重用户数。"""
    first = {}
    for r in rows:
        u, p = str(r.get(user_col, "")), str(r.get(period_col, ""))
        if u and p and u not in first:
            first[u] = p
    periods = sorted({p for p in first.values()})
    active_by_coh: Dict[str, Dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for r in rows:
        u = str(r.get(user_col, ""))
        p = str(r.get(period_col, ""))
        if not u or u not in first:
            continue
        active_by_coh[first[u]][p].add(u)
    matrix = []
    for coh in periods:
        row = {"cohort": coh, "cohort_size": len({u for u, f in first.items() if f == coh})}
        for i, pp in enumerate(periods):
            if pp < coh:
                continue
            row[f"p{periods.index(pp) - periods.index(coh)}"] = len(
                active_by_coh[coh].get(pp, set()))
        matrix.append(row)
    return {"type": "cohort", "periods": periods, "matrix": matrix}


def _rfm(rows, user_col, date_col, value_col):
    import datetime as _dt
    today = _dt.date.today()
    recency, frequency, monetary = {}, Counter(), defaultdict(float)
    for r in rows:
        u = str(r.get(user_col, ""))
        if not u:
            continue
        frequency[u] += 1
        try:
            monetary[u] += float(r.get(value_col, 0) or 0)
        except (KeyError, ValueError):
            pass
        try:
            d = _dt.date.fromisoformat(str(r[date_col])[:10])
            recency[u] = min(recency.get(u, 99999), (today - d).days)
        except (KeyError, ValueError):
            pass
    users = set(recency) | set(frequency) | set(monetary)
    if not users:
        return {"type": "rfm", "segments": []}
    # 百分位打分（1–5，ties 不塌陷）：reverse=True 时值越小分越高
    def score(vals: Dict[str, float], reverse: bool) -> Dict[str, int]:
        ranked = sorted(vals.values())
        n = len(ranked)
        out = {}
        for u, v in vals.items():
            below = sum(1 for x in ranked if x < v)
            bucket = int(below / n * 5) + 1 if n else 1
            out[u] = 6 - bucket if reverse else bucket
        return out

    r_score = score(recency, reverse=True)   # 越小(越近)分越高
    f_score = score(dict(frequency), reverse=False)
    m_score = score(dict(monetary), reverse=False)
    segments = []
    for u in users:
        rr, ff, mm = r_score.get(u, 1), f_score.get(u, 1), m_score.get(u, 1)
        segments.append({"user": u, "r": rr, "f": ff, "m": mm,
                         "rfm": f"{rr}{ff}{mm}"})
    return {"type": "rfm", "user_count": len(users), "segments": segments}


def _saas(mrr, active_users, churn_rate):
    arpu = mrr / active_users if active_users else 0.0
    ltv = arpu / churn_rate if churn_rate else 0.0
    return {
        "mrr": round(mrr, 2), "active_users": active_users,
        "churn_rate": churn_rate, "arpu": round(arpu, 2),
        "ltv": round(ltv, 2), "ltv_requires_gross_margin": True,
        "expected_lifetime_months": round(1 / churn_rate, 1) if churn_rate else None,
    }


# --------------------------------------------------------------------------- #
# 统计小工具（纯标准库）
# --------------------------------------------------------------------------- #
def _var(vals: List[float]) -> float:
    if not vals:
        return 0.0
    m = sum(vals) / len(vals)
    return sum((x - m) ** 2 for x in vals) / len(vals)


def _slope(xs: List[float], ys: List[float]):
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return 0.0, my
    b = sxy / sxx
    return b, my - b * mx


def _rolling_median(vals: List[float], w: int) -> List[float]:
    out = []
    for i in range(len(vals)):
        seg = vals[max(0, i - w + 1):i + 1]
        out.append(statistics.median(seg))
    return out


def _time_series(rows, date_col, value_col, window):
    th = c.load_thresholds().get("timeseries", {})
    sigma = th.get("anomaly_sigma", 3.0)
    strong = th.get("seasonality_strong", 0.6)
    min_pts = int(th.get("min_points", 6))

    b: Dict[str, float] = defaultdict(float)
    for r in rows:
        try:
            b[str(r[date_col])] += float(r.get(value_col, 0) or 0)
        except (KeyError, ValueError):
            continue
    keys = sorted(b)
    vals = [b[k] for k in keys]
    if len(vals) < min_pts:
        return {"type": "time_series", "error":
                f"样本点 {len(vals)} 少于要求 {min_pts}，无法可靠检验/分解"}

    w = max(2, int(window))
    ma = []
    for i in range(len(vals)):
        lo = max(0, i - w + 1)
        ma.append(round(sum(vals[lo:i + 1]) / (i - lo + 1), 2))

    slope, intercept = _slope([float(i) for i in range(len(vals))], vals)
    head = sum(vals[:len(vals) // 3]) / max(1, len(vals) // 3)
    tail = sum(vals[-(len(vals) // 3):]) / max(1, len(vals) // 3)
    if head:
        head_tail_change = round((tail - head) / head * 100, 2)
    else:
        head_tail_change = 0.0
    direction = "up" if slope > 0 else ("down" if slope < 0 else "flat")

    season_strength = _seasonality_strength(keys, vals)
    anomalies, band = _detect_anomalies(vals, w, sigma)

    series = [{"date": keys[i], "value": round(vals[i], 2),
               "moving_avg": ma[i], "anomaly": i in {a["index"] for a in anomalies}}
              for i in range(len(vals))]

    return {"type": "time_series", "series": series,
            "n": len(vals), "window": w,
            "trend": {"slope_per_step": round(slope, 4), "direction": direction,
                      "head_tail_change_pct": head_tail_change},
            "seasonality_strength": season_strength,
            "seasonality_strong": season_strength >= strong,
            "anomalies": {"count": len(anomalies), "band": round(band, 4),
                          "top": sorted(anomalies, key=lambda a: -a["deviation"])[:5]},
            "note": f"季节强度≥{strong} 视为强季节；异常=|值−滚动中位数|>{sigma}×1.4826×全局MAD"}


def _seasonality_strength(keys: List[str], vals: List[float]) -> float:
    """周期均值法：strength = 1 − var(残差)/var(总量)，周期键取前 7 字符（YYYY-MM）。"""
    groups: Dict[str, List[float]] = defaultdict(list)
    for k, v in zip(keys, vals):
        groups[str(k)[:7]].append(v)
    if len(groups) < 2:
        return 0.0
    means = {k: sum(v) / len(v) for k, v in groups.items()}
    residuals = [v - means[str(k)[:7]] for k, v in zip(keys, vals)]
    var_tot = _var(vals)
    var_res = _var(residuals)
    if var_tot == 0:
        return 0.0
    return round(max(0.0, min(1.0, 1 - var_res / var_tot)), 4)


def _detect_anomalies(vals: List[float], w: int, sigma: float):
    meds = _rolling_median(vals, w)
    global_med = statistics.median(vals)
    mad = statistics.median([abs(v - global_med) for v in vals])
    band = 1.4826 * mad
    anomalies = []
    for i, (v, m) in enumerate(zip(vals, meds)):
        dev = abs(v - m)
        if band > 0 and dev > sigma * band:
            anomalies.append({"index": i, "value": round(v, 2),
                              "rolling_median": round(m, 2),
                              "deviation": round(dev, 2)})
    return anomalies, band


# --------------------------------------------------------------------------- #
# k-means 聚类分群（纯标准库 Lloyd）
# --------------------------------------------------------------------------- #
def _sqdist(a: List[float], b: List[float]) -> float:
    return sum((a[i] - b[i]) ** 2 for i in range(len(a)))


def _zscore_col(colv: List[float]):
    m = sum(colv) / len(colv)
    sd = (sum((x - m) ** 2 for x in colv) / len(colv)) ** 0.5
    return [(x - m) / sd if sd > 0 else 0.0 for x in colv], m, sd


def _segment(rows, features, k, user_col, seed):
    th = c.load_thresholds().get("segmentation", {})
    sil_ok = th.get("silhouette_ok", 0.3)
    max_k = int(th.get("max_k", 8))
    feats = [f.strip() for f in features.split(",") if f.strip()]
    if not feats:
        return {"type": "segment", "error": "未提供数值特征列"}

    data: List[List[float]] = []
    ids: List[str] = []
    for r in rows:
        try:
            v = [float(r[f]) for f in feats]
        except (KeyError, ValueError, TypeError):
            continue
        data.append(v)
        u = str(r.get(user_col, "")).strip()
        ids.append(u if u else f"u{len(data)}")
    n = len(data)
    if n < 3:
        return {"type": "segment", "error": f"可聚类样本仅 {n} 个，不足以分群"}

    cols = [[row[i] for row in data] for i in range(len(feats))]
    std_cols, means, sds = [], [], []
    for colv in cols:
        zs, m, sd = _zscore_col(colv)
        std_cols.append(zs); means.append(m); sds.append(sd)
    pts = [[std_cols[j][i] for j in range(len(feats))] for i in range(n)]

    k = max(1, min(int(k), max_k, n))
    rng = random.Random(int(seed))
    order = list(range(n))
    rng.shuffle(order)
    cents = [pts[order[i]][:] for i in range(k)]
    labels = [0] * n
    for _ in range(100):
        changed = False
        for i, p_ in enumerate(pts):
            best = min(range(k), key=lambda ci: _sqdist(p_, cents[ci]))
            if labels[i] != best:
                labels[i] = best
                changed = True
        if not changed:
            break
        sums = [[0.0] * len(feats) for _ in range(k)]
        cnt = [0] * k
        for i, p_ in enumerate(pts):
            for j in range(len(feats)):
                sums[labels[i]][j] += p_[j]
            cnt[labels[i]] += 1
        for ci in range(k):
            if cnt[ci]:
                cents[ci] = [sums[ci][j] / cnt[ci] for j in range(len(feats))]

    inertia = sum(_sqdist(p_, cents[labels[i]]) for i, p_ in enumerate(pts))
    sil = _silhouette(pts, labels, k)
    composite = {ci: sum(cents[ci]) for ci in range(k)}
    strategies = ["Retain & Expand", "Monetise", "Activate", "Win-Back", "Sunset"]
    seg_sorted = sorted(range(k), key=lambda ci: -composite[ci])

    clusters = []
    for rank, ci in enumerate(seg_sorted):
        idxs = [i for i in range(n) if labels[i] == ci]
        prof = {}
        for j, f in enumerate(feats):
            m = sum(data[i][j] for i in idxs) / len(idxs)
            pct = round((m - means[j]) / means[j] * 100, 2) if means[j] else 0.0
            prof[f] = {"mean": round(m, 2), "vs_overall_pct": pct}
        defining = sorted(feats, key=lambda f: abs(prof[f]["vs_overall_pct"]),
                          reverse=True)[:2]
        clusters.append({"segment": f"seg_{ci}", "size": len(idxs),
                         "size_pct": round(len(idxs) / n * 100, 2),
                         "strategy": strategies[min(rank, len(strategies) - 1)],
                         "profile": prof, "defining_features": defining,
                         "centroid_composite": round(composite[ci], 4)})

    return {"type": "segment", "k": k, "n": n, "features": feats,
            "inertia": round(inertia, 4), "silhouette": round(sil, 4),
            "silhouette_ok": sil >= sil_ok,
            "clusters": clusters,
            "note": f"silhouette≥{sil_ok} 视为结构有效；策略映射为一阶启发式，须业务复核"}


def _silhouette(pts: List[List[float]], labels: List[int], k: int) -> float:
    """平均轮廓系数（n>600 时抽样 600 点，O(n²) 近似）。"""
    n = len(pts)
    idxs = list(range(n))
    if n > 600:
        idxs = random.Random(0).sample(idxs, 600)
    scores = []
    for i in idxs:
        same = [j for j in range(n) if labels[j] == labels[i]]
        other = [j for j in range(n) if labels[j] != labels[i]]
        if len(same) <= 1:
            continue
        a = sum(_sqdist(pts[i], pts[j]) for j in same) / (len(same) - 1)
        b = 0.0
        for ci in set(labels) - {labels[i]}:
            cj = [j for j in other if labels[j] == ci]
            if cj:
                b_ci = sum(_sqdist(pts[i], pts[j]) for j in cj) / len(cj)
                b = b_ci if (b == 0.0 or b_ci < b) else b
        scores.append((b - a) / max(a, b) if max(a, b) > 0 else 0.0)
    return sum(scores) / len(scores) if scores else 0.0


# --------------------------------------------------------------------------- #
# 业务指标（business-metrics-calculator）
# --------------------------------------------------------------------------- #
def _metrics(rows, model, value_col, customer_col, month_col, cac_spend):
    if model == "ecommerce":
        return _ecommerce_metrics(rows, value_col, customer_col)
    return _saas_metrics(rows, value_col, customer_col, month_col, cac_spend)


def _band_gte(v, good, warn):
    if v >= good:
        return "good"
    return "warn" if v >= warn else "poor"


def _band_lte(v, good, warn):
    if v <= good:
        return "good"
    return "warn" if v <= warn else "poor"


def _saas_metrics(rows, value_col, customer_col, month_col, cac_spend):
    th = c.load_thresholds().get("saas", {})
    active: Dict[str, set] = defaultdict(set)
    mrr: Dict[str, Dict[str, float]] = defaultdict(dict)
    for r in rows:
        cid = str(r.get(customer_col, "")).strip()
        m = str(r.get(month_col, "")).strip()
        if not cid or not m:
            continue
        try:
            v = float(r.get(value_col, 0) or 0)
        except (KeyError, ValueError, TypeError):
            v = 0.0
        status = str(r.get("status", "active")).strip().lower()
        mrr[m][cid] = v
        if status != "canceled":
            active[m].add(cid)

    months = sorted(m for m in active if active[m])
    if len(months) < 2:
        return {"type": "metrics", "model": "saas",
                "error": "需要至少两个有活跃客户的月份"}
    first, last = months[0], months[-1]

    def total(m, cids):
        return sum(mrr[m].get(cid, 0.0) for cid in cids)

    start_cust, end_cust = active[first], active[last]
    retained = start_cust & end_cust
    new_cust = end_cust - start_cust
    churned_cust = start_cust - end_cust

    starting_mrr = total(first, start_cust)
    ending_mrr = total(last, end_cust)
    new_mrr = total(last, new_cust)
    churned_mrr = total(first, churned_cust)
    expansion = contraction = 0.0
    for cid in retained:
        d = mrr[last].get(cid, 0.0) - mrr[first].get(cid, 0.0)
        if d > 0:
            expansion += d
        elif d < 0:
            contraction += -d
    start_retained = total(first, retained)
    end_retained = total(last, retained)
    nrr = round(end_retained / start_retained * 100, 2) if start_retained else 0.0
    grr = round(max(0.0, start_retained - churned_mrr - contraction) /
                start_retained * 100, 2) if start_retained else 0.0
    logo_churn = round(len(churned_cust) / len(start_cust) * 100, 2) if start_cust else 0.0
    arpu = ending_mrr / len(end_cust) if end_cust else 0.0
    ltv = arpu / (logo_churn / 100) if logo_churn > 0 else 0.0

    out = {"type": "metrics", "model": "saas", "first_month": first, "last_month": last,
           "starting_mrr": round(starting_mrr, 2), "ending_mrr": round(ending_mrr, 2),
           "net_new_mrr": round(ending_mrr - starting_mrr, 2),
           "new_mrr": round(new_mrr, 2), "churned_mrr": round(churned_mrr, 2),
           "expansion_mrr": round(expansion, 2), "contraction_mrr": round(contraction, 2),
           "net_revenue_retention_pct": nrr, "gross_revenue_retention_pct": grr,
           "logo_churn_rate_pct": logo_churn, "arpu": round(arpu, 2),
           "ltv": round(ltv, 2), "arr": round(ending_mrr * 12, 2)}
    out["benchmarks"] = {
        "nrr": _band_gte(nrr, th.get("nrr_good_pct", 100.0),
                         th.get("nrr_warn_pct", 90.0)),
        "logo_churn": _band_lte(logo_churn, th.get("churn_rate_good_pct", 5.0),
                                th.get("churn_rate_warn_pct", 10.0))}
    if cac_spend and new_cust:
        cac = cac_spend / len(new_cust)
        ratio = ltv / cac if cac else 0.0
        out["cac"] = round(cac, 2)
        out["ltv_cac_ratio"] = round(ratio, 2)
        out["benchmarks"]["ltv_cac"] = _band_gte(ratio, th.get("ltv_cac_good", 3.0),
                                                 th.get("ltv_cac_warn", 1.0))
    return out


def _ecommerce_metrics(rows, value_col, customer_col):
    gmv = 0.0
    orders = 0
    cust = set()
    amounts: List[float] = []
    for r in rows:
        try:
            a = float(r.get(value_col, 0) or 0)
        except (KeyError, ValueError, TypeError):
            continue
        gmv += a
        orders += 1
        amounts.append(a)
        cid = str(r.get(customer_col, "")).strip()
        if cid:
            cust.add(cid)
    aov = gmv / orders if orders else 0.0
    # 订单级复购占比 = (订单数 − 独立客户数) / 订单数
    repeat_share = round((orders - len(cust)) / orders, 4) if orders else 0.0
    return {"type": "metrics", "model": "ecommerce", "gmv": round(gmv, 2),
            "orders": orders, "customer_count": len(cust), "aov": round(aov, 2),
            "repeat_purchase_share": repeat_share,
            "note": "conversion/ROAS 需独立访客与投放数据，不在该输入契约内"}
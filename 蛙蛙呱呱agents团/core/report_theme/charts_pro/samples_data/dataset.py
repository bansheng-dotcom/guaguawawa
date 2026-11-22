# -*- coding: utf-8 -*-
"""core.charts.v2.dataset —— 48 型图表的完整演示数据源。

来源：`workspace/图鉴-满血_2026-11-15/data.py`（内蒙古家居百货口径）逐项迁入，
保持同样的密度与确定性（种子 20261115）：

    36 个月 × 6 品类、10 门店 × 6 品类动销矩阵、45 个 SKU、12 盟市 × 5 维度、
    365 天日销、30 天履约序列、30 日 OHLC、转化漏斗、桑基流量、树形结构。

用途：
- 图鉴 / 门禁 / 报告接入验收共用同一套数据，避免“每处一套示例”；
- 报告真实数据仍由 result / fact_table 注入，这里只用于能力演示与回归。

**这些数字只演示图形能力，不能当结论引用。**
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

RNG = np.random.default_rng(20261115)

YEARS = ["2020", "2021", "2022", "2023", "2024", "2025"]
RETAIL = [286.0, 305.4, 298.2, 322.7, 352.1, 376.3]

CATS = ["家纺布艺", "清洁日用", "小家电", "餐厨用品", "收纳整理", "家居饰品"]
CAT_2025 = [96.4, 88.2, 74.1, 61.3, 38.6, 17.7]
CAT_GROWTH = [4.2, 9.8, 12.4, 1.9, 6.1, -2.3]
CAT_2024 = [round(v / (1 + g / 100), 1) for v, g in zip(CAT_2025, CAT_GROWTH)]

CITIES = ["呼和浩特", "包头", "鄂尔多斯", "赤峰", "通辽", "呼伦贝尔",
          "巴彦淖尔", "乌兰察布", "锡林郭勒", "兴安盟", "乌海", "阿拉善"]
CITY_2025 = [62.4, 48.1, 46.9, 36.2, 27.4, 21.8, 17.6, 16.2, 11.4, 9.8, 7.2, 3.6]
CITY_POP = [360, 274, 222, 400, 285, 219, 152, 168, 112, 141, 56, 27]
CITY_2024 = [round(v / (1 + g / 100), 1) for v, g in zip(
    CITY_2025, [6.4, 3.1, 8.2, 4.6, 2.2, 1.4, 5.1, 3.8, 0.9, 4.2, -1.6, 2.4])]
CITY_TICKET = [186, 172, 214, 149, 141, 155, 132, 128, 163, 126, 178, 158]

TILES = {
    "阿拉善": (0, 1), "乌海": (1, 2), "巴彦淖尔": (1, 1), "鄂尔多斯": (2, 2),
    "包头": (2, 1), "呼和浩特": (3, 1), "乌兰察布": (3, 0), "锡林郭勒": (4, 1),
    "赤峰": (5, 1), "通辽": (6, 1), "兴安盟": (6, 0), "呼伦贝尔": (7, 0),
}

MONTHS = [f"{y}-{m:02d}" for y in (2023, 2024, 2025) for m in range(1, 13)]
SEASON = np.array([1.18, 1.12, 0.94, 0.92, 0.96, 0.98,
                   0.93, 0.95, 1.02, 1.05, 1.24, 1.09])

_MONTH_BASE = {c: v / 12.0 for c, v in zip(CATS, CAT_2025)}
MONTHLY: Dict[str, List[float]] = {}
for _i, _c in enumerate(CATS):
    _mult = 1.0 - 0.05 * (2 - _i)
    _vals: List[float] = []
    for _k in range(36):
        _trend = 1.0 + (_mult - 1.0) * (_k / 35.0) + 0.004 * _k
        _v = _MONTH_BASE[_c] * _trend * SEASON[_k % 12] * (1 + RNG.normal(0, 0.035))
        _vals.append(float(_v))
    _scale = CAT_2025[_i] / sum(_vals[-12:])
    MONTHLY[_c] = [round(v * _scale, 2) for v in _vals]

MONTH_TOTAL = [round(sum(MONTHLY[c][k] for c in CATS), 2) for k in range(36)]

STORES = ["呼市·万象城", "呼市·民族商场", "包头·昆都仑", "鄂尔多斯·康巴什", "赤峰·红山",
          "通辽·科尔沁", "海拉尔·河东", "临河·胜利路", "集宁·新区", "乌海·海勃湾"]
STORE_SIZE = [1.35, 0.92, 1.08, 0.86, 0.74, 0.61, 0.48, 0.44, 0.40, 0.31]
STORE_CAT = np.array([[1.0, 1.1, 0.9, 0.8, 0.7, 0.5],
                      [0.9, 1.0, 1.0, 1.2, 0.8, 0.7],
                      [1.1, 0.9, 1.1, 0.9, 0.9, 0.6],
                      [0.8, 0.9, 1.3, 0.8, 1.1, 0.9],
                      [1.0, 1.0, 0.8, 1.1, 0.9, 0.8],
                      [1.2, 1.1, 0.7, 1.0, 0.7, 0.6],
                      [0.9, 0.8, 0.9, 1.3, 1.0, 0.7],
                      [1.0, 0.9, 0.8, 1.2, 0.9, 0.6],
                      [1.1, 1.0, 0.9, 1.0, 0.8, 0.7],
                      [0.9, 0.9, 1.0, 1.1, 0.8, 0.6]])
STORE_MATRIX = np.round(
    np.outer(STORE_SIZE, [26.0, 24.0, 20.0, 16.0, 10.0, 5.0]) * STORE_CAT
    * (1 + RNG.normal(0, 0.05, (10, 6))), 1)

_SKU_PRICE = np.array([19, 29, 35, 39, 45, 49, 55, 59, 65, 69, 75, 79, 85, 89, 95,
                       99, 109, 119, 129, 139, 149, 159, 169, 179, 189, 199, 219,
                       239, 259, 279, 299, 329, 359, 399, 449, 499, 559, 619, 699,
                       799, 899, 999, 1099, 1199, 1299], dtype=float)
SKU_PRICE = _SKU_PRICE
SKU_SALES = np.round(24000 * _SKU_PRICE ** -0.72 * (1 + RNG.normal(0, 0.22, len(_SKU_PRICE))))
SKU_SALES = np.maximum(SKU_SALES, 3)
SKU_OUTLIER = {8: "39 元爆款：单位陈列翻倍，偏离弹性线 2.6 倍",
               37: "619 元新品：铺货 3 周，销量还没起",
               41: "999 元礼盒：企业团购一次性大单"}

TICKETS = {c: np.round(RNG.lognormal(mean=np.log(v), sigma=0.42, size=260), 0)
           for c, v in zip(CITIES[:6], CITY_TICKET[:6])}

RETURN_REASONS = [("尺寸不符", 42.0), ("色差", 27.0), ("物流破损", 18.0),
                  ("安装复杂", 9.0), ("其他", 4.0)]
FUNNEL = [("曝光", 1_860_000), ("点击", 214_000), ("加购", 61_400),
          ("下单", 28_900), ("支付", 24_600)]
EFFECTS = [("详情页加尺寸表", 3.4, 1.1, 5.7, 8), ("次日达覆盖", 2.6, 0.4, 4.8, 11),
           ("客服 30 秒响应", 1.9, -0.3, 4.1, 9), ("满减改阶梯", 0.8, -2.1, 3.7, 12),
           ("短视频种草", -0.4, -2.9, 2.1, 7)]
CONTROL = np.round(96.0 + RNG.normal(0, 0.55, 30), 2)
CONTROL[9] = 92.9
CONTROL[22] = 93.2
OHLC: List[tuple] = []
_p = 100.0
for _ in range(30):
    _o = _p
    _c = _o * (1 + RNG.normal(0.0012, 0.011))
    _h = max(_o, _c) * (1 + abs(RNG.normal(0, 0.006)))
    _l = min(_o, _c) * (1 - abs(RNG.normal(0, 0.006)))
    OHLC.append((round(_o, 2), round(_h, 2), round(_l, 2), round(_c, 2)))
    _p = _c
OHLC = np.array(OHLC)

DAYS = [f"{m:02d}-{d:02d}" for m in range(1, 13) for d in range(1, 31)
        if not (m == 2 and d > 28)]
_DAILY = 1.0 + 0.10 * np.sin(np.arange(len(DAYS)) / 58.0) + RNG.normal(0, 0.07, len(DAYS))
_NOV11 = DAYS.index("11-11")
_DAILY[_NOV11] = 1.86
for _k in range(1, 11):
    _DAILY[_NOV11 + _k] = 1.42 + RNG.normal(0, 0.05)
for _k in range(1, 7):
    _DAILY[_NOV11 - _k] = 1.30 + RNG.normal(0, 0.05)
DAILY = np.round(np.clip(_DAILY, 0.55, 1.9), 2)

GANTT = [("选品定档", 0, 18), ("供应商比价", 10, 26), ("首批备货", 22, 44),
         ("门店陈列改造", 40, 62), ("本地达人投放", 55, 78), ("复盘与二次补货", 74, 90)]
MILESTONES = [(18, "定档会"), (44, "首仓到货"), (62, "全店上线"), (90, "复盘")]

SANKEY = {
    "nodes": ["曝光 186 万", "点击 21.4 万", "加购 6.14 万", "下单 2.89 万", "支付 2.46 万",
              "流失 164.6 万", "流失 15.3 万", "流失 3.25 万", "流失 0.43 万"],
    "links": [(0, 1, 21.4), (0, 5, 164.6), (1, 2, 6.14), (1, 6, 15.3),
              (2, 3, 2.89), (2, 7, 3.25), (3, 4, 2.46), (3, 8, 0.43)],
}

NETWORK = {
    "nodes": ["家纺布艺", "收纳整理", "清洁日用", "餐厨用品", "小家电", "家居饰品"],
    "edges": [("家纺布艺", "收纳整理", 0.62), ("家纺布艺", "家居饰品", 0.48),
              ("清洁日用", "收纳整理", 0.57), ("清洁日用", "餐厨用品", 0.44),
              ("小家电", "餐厨用品", 0.51), ("小家电", "清洁日用", 0.39),
              ("家居饰品", "餐厨用品", 0.21), ("家纺布艺", "清洁日用", 0.26)],
}

TREEMAP = {
    "家纺布艺": [("四件套", 38.2), ("被芯", 26.4), ("枕芯", 14.8), ("毯类", 9.6), ("帘类", 7.4)],
    "清洁日用": [("纸品", 31.6), ("洗衣液", 24.2), ("清洁工具", 18.4), ("除菌", 8.9), ("香氛", 5.1)],
    "小家电": [("电饭煲", 22.4), ("空气炸锅", 19.8), ("养生壶", 13.2), ("吸尘器", 11.6), ("其他", 7.1)],
    "餐厨用品": [("锅具", 24.1), ("餐具", 16.8), ("水具", 12.4), ("储物", 8.0)],
    "收纳整理": [("衣柜收纳", 16.2), ("桌面收纳", 11.4), ("箱包", 7.6), ("挂钩", 3.4)],
    "家居饰品": [("装饰画", 7.2), ("摆件", 5.8), ("香薰", 4.7)],
}

SUNBURST = TREEMAP


# --------------------------------------------------------------------------- #
# 由完整数据源直接生成的 48 型样本（唯一出处；画廊与门禁共用）
# --------------------------------------------------------------------------- #
def _round(v: float, d: int = 1) -> float:
    return round(float(v), d)


def pct_change(a: float, b: float) -> float:
    return (b - a) / a * 100 if a else 0.0


def month_labels() -> List[str]:
    return list(MONTHS)


def sample_line() -> Dict[str, Any]:
    vals = MONTH_TOTAL
    yoy = pct_change(sum(vals[-24:-12]), sum(vals[-12:]))
    return {
        "type": "line",
        "title": f"月度规模回到 {vals[-1]:,.0f} 万元，近 12 个月同比 {yoy:+.1f}%",
        "subtitle": "2023-01 至 2025-12 月度规模 · 万元 · 36 个月",
        "unit_meta": "万元", "source": "S1 月度台账", "note": "虚线为 36 个月均值",
        "ref": {"value": _round(sum(vals) / len(vals), 1),
                "label": f"均值 {sum(vals) / len(vals):,.0f}"},
        "xlabels": month_labels(),
        "series": [{"name": "月度规模", "values": vals, "accent": True}],
    }


def sample_area() -> Dict[str, Any]:
    vals = MONTH_TOTAL[-12:]
    prev = MONTH_TOTAL[-24:-12]
    delta = sum(vals) - sum(prev)
    return {
        "type": "area",
        "title": f"2025 年把全年增量做到 {delta:+,.0f} 万元，四季度贡献最大",
        "subtitle": "2025-01 至 2025-12 月度规模 · 万元",
        "unit_meta": "万元", "source": "S1 月度台账", "note": "纵轴自 0 起，面积强调量级",
        "ref": {"value": _round(sum(vals) / 12, 1), "label": f"月均 {sum(vals) / 12:,.0f}"},
        "xlabels": month_labels()[-12:],
        "series": [{"name": "月度规模", "values": vals, "accent": True}],
    }


def sample_streamgraph() -> Dict[str, Any]:
    vals = {c: MONTHLY[c] for c in CATS}
    first = {c: sum(vals[c][:12]) for c in CATS}
    last = {c: sum(vals[c][-12:]) for c in CATS}
    fastest = max(CATS, key=lambda c: pct_change(first[c], last[c]))
    return {
        "type": "streamgraph",
        "title": f"{fastest} 三年增 {pct_change(first[fastest], last[fastest]):+.1f}%，结构变化最快",
        "subtitle": "2023–2025 六品类月度规模构成 · 万元",
        "unit_meta": "万元", "source": "S1 月度台账", "note": "非负中心堆叠，厚度∝当期规模",
        "xlabels": month_labels(),
        "series": [{"name": c, "values": vals[c],
                    "accent": c == fastest} for c in CATS],
    }


def sample_histogram() -> Dict[str, Any]:
    vals = [float(v) for c in CITIES[:6] for v in TICKETS[c]]
    med = float(np.median(vals))
    p90 = float(np.percentile(vals, 90))
    return {
        "type": "histogram",
        "title": f"六城 {len(vals):,} 笔客单价中位 {med:.0f} 元，P90 到 {p90:.0f} 元",
        "subtitle": "2025 年六城订单客单价 · 等宽 12 箱",
        "unit_meta": "元", "source": "订单明细（示例构造）", "note": "虚线为均值/中位参考",
        "values": vals,
    }


def _ticket_groups(labels: List[str], accent: str = "") -> List[Dict[str, Any]]:
    out = []
    for c in labels:
        out.append({"label": c, "values": [float(v) for v in TICKETS[c]],
                    "accent": c == accent})
    return out


def _spread(vals: List[float]) -> float:
    v = np.array(vals)
    return float(np.percentile(v, 75) - np.percentile(v, 25))


def sample_box() -> Dict[str, Any]:
    groups = _ticket_groups(CITIES[:6])
    widest = max(groups, key=lambda g: _spread(g["values"]))
    return {
        "type": "box",
        "title": f"{widest['label']} 四分位跨度 {_spread(widest['values']):.0f} 元，离散最大",
        "subtitle": "六城客单价分布 · 箱体 P25–P75 · n=260/城",
        "unit_meta": "元", "source": "订单明细（示例构造）", "note": "须线 1.5 IQR，点为离群值",
        "groups": groups,
    }


def sample_violin() -> Dict[str, Any]:
    groups = _ticket_groups(CITIES[:6])
    thick = max(groups, key=lambda g: float(np.percentile(g["values"], 90) -
                                           np.median(g["values"])))
    gap = float(np.percentile(thick["values"], 90) - np.median(thick["values"]))
    return {
        "type": "violin",
        "title": f"{thick['label']} P90 比中位高 {gap:.0f} 元，尾部最厚",
        "subtitle": "六城客单价密度 · 14 箱平滑 · n=260/城",
        "unit_meta": "元", "source": "订单明细（示例构造）", "note": "竖线为中位数",
        "groups": groups,
    }


def sample_ridgeline() -> Dict[str, Any]:
    groups = _ticket_groups(CITIES[:6])
    return {
        "type": "ridgeline",
        "title": f"{CITIES[0]} 峰位 {TICKETS[CITIES[0]].mean():.0f} 元，六城共享横轴",
        "subtitle": "六城客单价分布 · 峰位按分箱中值",
        "unit_meta": "元", "source": "订单明细（示例构造）", "note": "组序即给定顺序",
        "groups": groups,
    }


def sample_scatter() -> Dict[str, Any]:
    pts = [{"x": _round(SKU_PRICE[i], 0), "y": _round(SKU_SALES[i], 0)} for i in range(len(SKU_PRICE))]
    for idx, note in SKU_OUTLIER.items():
        if idx < len(pts):
            pts[idx].update({"label": note.split("：")[0], "accent": True})
    return {
        "type": "scatter",
        "title": f"{len(pts)} 个 SKU：价格每升 10%，月销降约 7.2%（弹性 −0.72）",
        "subtitle": "同品类 SKU 到手价 vs 月销 · OLS 拟合",
        "unit_meta": "件/月", "source": "商品台账（示例构造）", "note": "灰色为常规 SKU，强调为离群点",
        "points": pts, "xlabel": "到手价（元）",
    }


def sample_bubble() -> Dict[str, Any]:
    per_cap = [CITY_2025[i] * 10000 / CITY_POP[i] for i in range(len(CITIES))]
    pts = [{"x": CITY_TICKET[i], "y": _round(per_cap[i], 0),
            "size": CITY_POP[i], "name": CITIES[i],
            "label": CITIES[i] if CITY_POP[i] >= 274 else "",
            "accent": CITIES[i] in ("呼和浩特", "鄂尔多斯")}
           for i in range(len(CITIES))]
    return {
        "type": "bubble",
        "title": f"呼和浩特人均 {per_cap[0]:,.0f} 元、鄂尔多斯 {per_cap[2]:,.0f} 元，人口与客单双高",
        "subtitle": "12 盟市 · 横轴客单价、纵轴人均消费 · 面积=常住人口",
        "unit_meta": "元", "source": "分盟市台账（示例构造）", "note": "虚线为两轴均值",
        "points": pts,
    }


def sample_heatmap() -> Dict[str, Any]:
    return {
        "type": "heatmap",
        "title": f"呼市万象城 × 家纺布艺 {STORE_MATRIX[0][0]:.1f} 万元，是矩阵最大格",
        "subtitle": "10 门店 × 6 品类月动销 · 万元",
        "unit_meta": "万元", "source": "门店经营台账（示例构造）", "note": "单色阶，深=高",
        "rows": [s.split("·")[-1] for s in STORES],
        "cols": CATS,
        "cells": [[_round(v) for v in row] for row in STORE_MATRIX],
    }


def sample_cal_heatmap() -> Dict[str, Any]:
    return {
        "type": "cal_heatmap",
        "title": f"11-11 单日峰值 {DAILY.max():.2f}，是平日均值的 1.9 倍",
        "subtitle": "2025 全年日销指数 · 365 天 · 缺失日斜纹",
        "unit_meta": "指数", "source": "订单流水（示例构造）", "note": "周一至周日自上而下",
        "days": [{"date": f"2025-{d}", "value": _round(DAILY[i], 2)}
                 for i, d in enumerate(DAYS)],
    }


def sample_candlestick() -> Dict[str, Any]:
    rows = [{"label": f"T{i + 1}", "open": _round(r[0], 2), "high": _round(r[1], 2),
             "low": _round(r[2], 2), "close": _round(r[3], 2),
             "accent": i == int(np.argmax(OHLC[:, 1]))}
            for i, r in enumerate(OHLC)]
    ups = int(sum(1 for r in OHLC if r[3] >= r[0]))
    return {
        "type": "candlestick",
        "title": f"{len(rows)} 个交易日：最高 {OHLC[:, 1].max():.2f} 元，{ups} 根阳线",
        "subtitle": "示例标的日 K · 开高低收 · 30 个交易日",
        "unit_meta": "元", "source": "行情快照（示例构造）", "note": "红涨绿跌，虚线为收盘均值",
        "candles": rows,
    }


def sample_control() -> Dict[str, Any]:
    return {
        "type": "control",
        "title": f"30 期里越限 {int(sum(1 for v in CONTROL if abs(v - 96) > 3))} 次，均为单点异常",
        "subtitle": "日履约达标率 · 均值 96、控制带 ±3",
        "unit_meta": "%", "source": "履约台账（示例构造）", "note": "越限点单独标注",
        "series": [{"name": "达标率", "values": [float(v) for v in CONTROL]}],
        "xlabels": [f"D{i + 1}" for i in range(len(CONTROL))],
        "center": 96, "band": 3,
    }


def sample_sankey() -> Dict[str, Any]:
    nodes = [{"id": str(i), "label": n} for i, n in enumerate(SANKEY["nodes"])]
    links = [{"from": str(a), "to": str(b), "value": v} for a, b, v in SANKEY["links"]]
    return {
        "type": "sankey",
        "title": "曝光 186 万里，支付 2.46 万：总转化 1.3%",
        "subtitle": "一次大促流量漏斗 · 人数（万）",
        "unit_meta": "万人", "source": "站内埋点（示例构造）", "note": "流带宽∝流量，主路径标值",
        "nodes": nodes, "links": links,
    }


def sample_treemap() -> Dict[str, Any]:
    items = [{"label": c, "value": _round(sum(v for _, v in TREEMAP[c]))} for c in CATS]
    return {
        "type": "treemap",
        "title": f"{items[0]['label']} {items[0]['value']:.1f} 万元，是六类里最大的一块",
        "subtitle": "2025 年品类结构 · 面积∝规模 · 万元",
        "unit_meta": "万元", "source": "S1 品类台账", "note": "squarify 确定性切分",
        "items": items,
    }


def sample_sunburst() -> Dict[str, Any]:
    children = [{"label": c, "value": _round(sum(v for _, v in TREEMAP[c])),
                 "accent": c == CATS[0],
                 "children": [{"label": n, "value": v} for n, v in TREEMAP[c]]}
                for c in CATS]
    return {
        "type": "sunburst",
        "title": f"家纺布艺里四件套 {TREEMAP['家纺布艺'][0][1]:.1f} 万元，是最大二级项",
        "subtitle": "2025 年两层级结构 · 内环一级、外环二级",
        "unit_meta": "万元", "source": "S1 品类台账", "note": "小扇区标签外置",
        "root": {"label": "全品类", "children": children},
    }


def sample_gantt() -> Dict[str, Any]:
    from datetime import date, timedelta

    d0 = date(2026, 3, 2)
    tasks = [{"label": n, "start": (d0 + timedelta(days=s)).isoformat(),
              "end": (d0 + timedelta(days=e)).isoformat(),
              "accent": n in ("首批备货", "门店陈列改造")}
             for n, s, e in GANTT]
    return {
        "type": "gantt",
        "title": f"六项任务 {GANTT[-1][2]} 天总工期，备货与陈列是关键路径",
        "subtitle": "2026 年上新计划 · 2026-03-02 起",
        "unit_meta": "天", "source": "项目排期表", "note": "菱形为里程碑，虚线为今日",
        "today": "2026-04-01", "tasks": tasks,
    }


def sample_funnel() -> Dict[str, Any]:
    stages = [{"label": n, "value": v} for n, v in FUNNEL]
    drop = (FUNNEL[2][1] - FUNNEL[3][1]) / FUNNEL[2][1] * 100
    return {
        "type": "funnel",
        "title": f"加购到下单流失 {drop:.1f}%，是五级里最大漏点",
        "subtitle": "一次大促转化漏斗 · 人数",
        "unit_meta": "人", "source": "站内埋点（示例构造）", "note": "逐级流失直接标注",
        "stages": stages,
    }


def sample_error_bar() -> Dict[str, Any]:
    items = []
    for i, c in enumerate(CITIES[:6]):
        vals = TICKETS[c]
        items.append({"label": c, "value": _round(float(np.mean(vals)), 1),
                      "err": _round(float(np.std(vals) / np.sqrt(len(vals))), 1),
                      "accent": c == "鄂尔多斯"})
    hi = max(items, key=lambda x: x["value"])
    return {
        "type": "error_bar",
        "title": f"{hi['label']} 客单价 {hi['value']:.1f} 元最高，与末位相差 {hi['value'] - min(i['value'] for i in items):.1f} 元",
        "subtitle": "六城客单价均值 ± 标准误（SE）· n=260/城",
        "unit_meta": "元", "source": "订单明细（示例构造）", "note": "区间重叠≠不显著",
        "err_type": "SE", "items": items,
    }


def sample_parallel() -> Dict[str, Any]:
    size = np.array(STORE_SIZE)
    axes = ["规模", "家纺", "清洁", "小家电"]
    rows = []
    for i, s in enumerate(STORES):
        v = [size[i] * 100, STORE_MATRIX[i][0], STORE_MATRIX[i][1], STORE_MATRIX[i][2]]
        rows.append({"name": s.split("·")[-1], "values": [_round(x, 1) for x in v],
                     "accent": i == 0})
    return {
        "type": "parallel",
        "title": f"{rows[0]['name']} 四项全部最高，末位门店规模只有它的 {size[-1] / size[0] * 100:.0f}%",
        "subtitle": "十门店四维经营指标 · 各轴独立标准化",
        "unit_meta": "指数", "source": "门店经营台账（示例构造）", "note": "灰色为常规门店",
        "axes": axes, "items": rows,
    }


def sample_radar() -> Dict[str, Any]:
    aria = [82, 76, 71, 68, 64]
    axes = ["客单价", "复购", "上新", "毛利", "履约"]
    return {
        "type": "radar",
        "title": "头部门店复购 76 分、毛利 68 分，履约只有 64 分",
        "subtitle": "两店五维能力画像 · 统一 0–100 尺度",
        "unit_meta": "分", "source": "门店经营台账（示例构造）", "note": "多边形面积不是总分",
        "axes": axes,
        "series": [{"name": "万象城", "values": [82, 76, 71, 68, 64], "accent": True},
                   {"name": "海勃湾", "values": [58, 52, 46, 61, 49]}],
    }


def rail_transit() -> List[Dict[str, Any]]:
    """36 个月的品类状分布（供 small_mult / streamgraph 复用）。"""
    return [{"label": c, "values": MONTHLY[c]} for c in CATS]


def sample_small_mult() -> Dict[str, Any]:
    panels = [{"label": c, "values": MONTHLY[c][-12:]} for c in CATS[:4]]
    best = max(panels, key=lambda p: p["values"][-1] - p["values"][0])
    d = best["values"][-1] - best["values"][0]
    return {
        "type": "small_mult",
        "title": f"{best['label']} 12 个月增 {d:+.0f} 万元，四品类里最快",
        "subtitle": "2025 年四品类月度规模 · 共享尺度 · 万元",
        "unit_meta": "万元", "source": "S1 月度台账", "note": "仅比较维度在变",
        "panels": panels,
    }

# -*- coding: utf-8 -*-
"""图表引擎 v2 画廊（仓库内版本）：48 型各一张，渲成单页 HTML。

用法：
    python scripts/chart_gallery_v2.py [theme]
输出：
    workspace/chart_gallery.html
"""
from __future__ import annotations

import math
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.charts.v2 import dataset as DS  # noqa: E402
from core.charts.v2 import render  # noqa: E402

OUT = ROOT.parent / "workspace" / "chart_gallery.html"


def _wave(center: float, spread: float, n: int = 25, phase: float = 0.0) -> list:
    return [round(center + spread * math.sin(i * 0.9 + phase) + (i - n / 2) * 0.32, 1)
            for i in range(n)]


def _days(start: str, n: int, base: float, amp: float) -> list:
    d0 = date.fromisoformat(start)
    return [{"date": (d0 + timedelta(days=i)).isoformat(),
             "value": round(base + amp * abs(math.sin(i * 0.7)), 1)} for i in range(n)]


def _scatter_pts(n: int = 28) -> list:
    pts = []
    for i in range(n):
        x = 20 + i * 3.4
        y = 9000 / (x ** 0.9) + 40 * math.sin(i * 1.7)
        pts.append({"x": round(x, 1), "y": round(max(y, 6), 1)})
    pts[8].update({"label": "39 元爆款", "accent": True})
    return pts


def _candles(n: int = 12) -> list:
    out, price = [], 100.0
    for i in range(n):
        o = price
        c = o + 3.2 * math.sin(i * 1.1 + 0.4)
        h = max(o, c) + 1.4 + 0.6 * abs(math.sin(i))
        low = min(o, c) - 1.2 - 0.5 * abs(math.cos(i))
        out.append({"label": f"T{i + 1}", "open": round(o, 1), "high": round(h, 1),
                    "low": round(low, 1), "close": round(c, 1), "accent": i == 9})
        price = c
    return out


SAMPLES = {
    # ---- 基础比较 ----
    "hbar": {"type": "hbar", "title": "猫砂 40 亿元，是唯一上规模的细分",
             "subtitle": "2024 年三大电商口径 · 六类细分销售额",
             "unit_meta": "亿元", "source": "S3；2024 年三大电商口径",
             "note": "猫砂占细分合计 43%",
             "ref": {"value": 18.4, "label": "细分均值 18.4"},
             "bars": [{"label": "猫砂", "value": 40, "weight": "accent"},
                      {"label": "智能用品", "value": 22},
                      {"label": "清洁除臭", "value": 15},
                      {"label": "出行箱包", "value": 9},
                      {"label": "玩具", "value": 6}]},
    "vbar": {"type": "vbar", "title": "规模四年翻一倍，但增速掉到 4%",
             "subtitle": "2022–2025 年宠物行业零售规模",
             "unit_meta": "亿元", "source": "S1/S2", "note": "CAGR 4.9%",
             "ref": {"value": 2906.8, "label": "四年均值 2,907"},
             "bars": [{"label": "2022", "value": 2706}, {"label": "2023", "value": 2793},
                      {"label": "2024", "value": 3002, "weight": "accent"},
                      {"label": "2025", "value": 3126}]},
    "dot": {"type": "dot", "title": "用品赛道最分散：龙头也只占 26%",
            "subtitle": "2024 年各赛道 CR5",
            "unit_meta": "CR5，%", "source": "S3", "note": "食品集中度最高",
            "ref": {"value": 23.5, "label": "赛道均值 23.5"},
            "items": [{"label": "用品", "value": 26, "weight": "accent"},
                      {"label": "食品", "value": 38}, {"label": "医疗", "value": 12},
                      {"label": "服务", "value": 18}]},
    "lollipop": {"type": "lollipop", "title": "客单价排名：鄂尔多斯 268 元，高出末位一倍",
                 "subtitle": "12 盟市客单价 · 茎线仅作连接",
                 "unit_meta": "元", "source": "示例数据；剔除 1,000 元以上团购单",
                 "note": "前三位均为高收入盟市",
                 "ref": {"value": 188, "label": "盟市均值 188"},
                 "items": [{"label": "鄂尔多斯", "value": 268, "accent": True},
                           {"label": "呼和浩特", "value": 212}, {"label": "乌海", "value": 196},
                           {"label": "包头", "value": 188}, {"label": "赤峰", "value": 164},
                           {"label": "通辽", "value": 152}, {"label": "乌兰察布", "value": 138}]},
    "pareto": {"type": "pareto", "title": "前三项吃掉 80% 的缺口",
               "subtitle": "退款原因分类 · 288 条工单",
               "unit_meta": "条", "source": "内部复盘", "note": "累计 80% 参考线",
               "items": [{"label": "退款慢", "value": 42}, {"label": "描述不符", "value": 28},
                         {"label": "物流慢", "value": 18}, {"label": "客服", "value": 8},
                         {"label": "其他", "value": 4}]},
    "waterfall": {"type": "waterfall", "title": "从 3,002 到 3,126：增量只有 124 亿",
                  "subtitle": "2024→2025 规模桥接 · 亿元",
                  "unit_meta": "亿元", "source": "S1/S2", "note": "贡献项已闭合",
                  "steps": [{"label": "2024 合计", "value": 3002, "type": "total"},
                            {"label": "食品", "value": 78}, {"label": "医疗", "value": 35},
                            {"label": "用品", "value": 12}, {"label": "服务", "value": -1},
                            {"label": "2025 合计", "value": 3126, "type": "total"}]},
    "bridge": {"type": "bridge", "title": "毛利变化 128 万，其中渠道结构贡献 61 万",
               "subtitle": "2025 年毛利桥接 · 万元",
               "unit_meta": "万元", "source": "财务口径", "note": "贡献项闭合校验通过",
               "steps": [{"label": "期初毛利", "value": 820, "type": "total"},
                         {"label": "渠道结构", "value": 61}, {"label": "客单价", "value": 38},
                         {"label": "采购成本", "value": -52}, {"label": "履约", "value": 81},
                         {"label": "期末毛利", "value": 948, "type": "total"}]},
    "dumbbell": {"type": "dumbbell", "title": "猫一年涨 140 亿，犬只涨 68 亿",
                 "subtitle": "2024 vs 2025 分品类规模",
                 "unit_meta": "亿元", "source": "S1", "note": "差值直接标注",
                 "a_label": "2024", "b_label": "2025",
                 "items": [{"label": "猫", "a": 1305, "b": 1445},
                           {"label": "犬", "a": 1489, "b": 1557}]},
    "grouped_bar": {"type": "grouped_bar", "title": "猫增速 +2.5%、+4.9%，数量与单价同时领先",
                    "subtitle": "2025 年猫犬核心指标增速",
                    "unit_meta": "%", "source": "S1", "note": "同单位并列",
                    "categories": ["数量增速", "单宠消费增速"],
                    "series": [{"name": "犬", "values": [1.6, 3.0]},
                               {"name": "猫", "values": [2.5, 4.9]}]},
    "stacked_bar": {"type": "stacked_bar", "title": "食品占 52.8%，医疗占 28.0%",
                    "subtitle": "2024–2025 结构 · 亿元",
                    "unit_meta": "亿元", "source": "S1", "note": "柱顶为总量",
                    "categories": ["2024", "2025"],
                    "segments": [{"name": "食品", "values": [1585, 1650]},
                                 {"name": "医疗", "values": [841, 890]},
                                 {"name": "用品", "values": [372, 380]},
                                 {"name": "服务", "values": [204, 206]}]},
    "pct_stacked": {"type": "pct_stacked", "title": "三年里医疗占比从 28% 升到 29.4%",
                    "subtitle": "2023–2025 结构占比 · 各条合计 100%",
                    "unit_meta": "%", "source": "S1",
                    "note": "标注小于 8% 的段已省略",
                    "categories": ["2023", "2024", "2025"],
                    "segments": [{"name": "食品", "values": [1585, 1650, 1700], "accent": True},
                                 {"name": "医疗", "values": [841, 890, 940]},
                                 {"name": "用品", "values": [372, 380, 395]},
                                 {"name": "服务", "values": [204, 206, 210]}]},
    # ---- 趋势 ----
    "line": {"type": "line", "title": "增速从 7.5% 掉到 4.1%，2027 的 13.7% 是预测",
             "subtitle": "2022–2027E 规模 · 2027 为预测",
             "unit_meta": "亿元", "source": "S1/S2；2027 为预测", "note": "阴影为预测区间",
             "ref": {"value": 3002, "label": "2024 基准 3,002"},
             "xlabels": ["2022", "2023", "2024", "2025", "2027E"],
             "series": [{"name": "规模", "values": [2706, 2793, 3002, 3126, 4042], "accent": True}]},
    "area": {"type": "area", "title": "增量从 209 亿收窄到 124 亿",
             "subtitle": "2022–2025 规模 · 纵轴自 0 起",
             "unit_meta": "亿元", "source": "S1", "note": "面积强调量级",
             "ref": {"value": 2906.8, "label": "四年均值 2,907"},
             "xlabels": ["2022", "2023", "2024", "2025"],
             "series": [{"name": "规模", "values": [2706, 2793, 3002, 3126], "accent": True}]},
    "slope": {"type": "slope", "title": "医疗一年增 49 亿，用品只增 8 亿",
              "subtitle": "2024 vs 2025 规模 · 亿元",
              "unit_meta": "亿元", "source": "S1", "note": "斜率表达变化方向",
              "a_label": "2024", "b_label": "2025",
              "items": [{"label": "医疗", "a": 841, "b": 890},
                        {"label": "用品", "a": 372, "b": 380}]},
    "small_mult": {"type": "small_mult", "title": "食品 5 个月增 25 亿，服务只增 2 亿",
                   "subtitle": "2025 年 1–5 月 · 共享尺度",
                   "unit_meta": "亿元", "source": "内部数据", "note": "仅比较维度在变",
                   "panels": [{"label": "食品", "values": [120, 126, 131, 138, 145]},
                              {"label": "医疗", "values": [64, 66, 70, 71, 74]},
                              {"label": "用品", "values": [28, 29, 30, 31, 31]},
                              {"label": "服务", "values": [16, 17, 16, 17, 18]}]},
    # ---- 构成 ----
    "pie": {"type": "pie", "title": "食品 52.8% 过半，医疗 28.0% 次之",
            "subtitle": "2024 年结构占比",
            "unit_meta": "%", "source": "S1", "note": "从大到小顺时针",
            "items": [{"label": "食品", "value": 52.8}, {"label": "医疗", "value": 28.0},
                      {"label": "用品", "value": 12.4}, {"label": "服务", "value": 6.8}]},
    "donut": {"type": "donut", "title": "2024 结构：食品 52.8%、医疗 28.0%",
              "subtitle": "2024 年结构 · 中心为合计",
              "unit_meta": "亿元", "source": "S1", "note": "≤5 类，不合并",
              "items": [{"label": "食品", "value": 1585.1}, {"label": "医疗", "value": 840.6},
                        {"label": "用品", "value": 372.2}, {"label": "服务", "value": 204.1}],
              "center": {"label": "2024 合计", "value": 3002}},
    "treemap": {"type": "treemap", "title": "食品 1,585 亿，等于其余三块之和",
                "subtitle": "2024 年结构 · 面积∝规模",
                "unit_meta": "亿元", "source": "S1", "note": "squarify 确定性切分",
                "items": [{"label": "食品", "value": 1585}, {"label": "医疗", "value": 841},
                          {"label": "用品", "value": 372}, {"label": "服务", "value": 204}]},
    "sunburst": {"type": "sunburst", "title": "食品二级里主粮占 68%，是最大的单一层级",
                  "subtitle": "2024 年两层级结构 · 内环一级、外环二级",
                  "unit_meta": "亿元", "source": "S1", "note": "小扇区标签外置",
                  "root": {"label": "全渠道", "children": [
                      {"label": "食品", "value": 1585, "accent": True, "children": [
                          {"label": "主粮", "value": 1080}, {"label": "零食", "value": 505}]},
                      {"label": "医疗", "value": 841, "children": [
                          {"label": "药品", "value": 520}, {"label": "服务", "value": 321}]},
                      {"label": "用品", "value": 372, "children": [
                          {"label": "猫砂", "value": 210}, {"label": "玩具", "value": 162}]},
                      {"label": "服务", "value": 204, "children": [
                          {"label": "洗护", "value": 120}, {"label": "寄养", "value": 84}]},
                  ]}},
    "waffle": {"type": "waffle", "title": "每 100 户有 34 户买过，剩下 66 格才是空间",
               "subtitle": "城镇家庭年渗透率 · 每格 1%",
               "unit_meta": "%", "source": "样本 n=3,200 户", "note": "斜纹为未覆盖",
               "items": [{"label": "已购买", "value": 34, "accent": True},
                         {"label": "观望", "value": 26}, {"label": "未触达", "value": 18},
                         {"label": "流失", "value": 12}, {"label": "其他", "value": 10}]},
    "heatmap": {"type": "heatmap", "title": "风险矩阵：高概率 × 高影响 9 项",
                "subtitle": "概率 × 影响交叉计数",
                "unit_meta": "项", "source": "内部复盘", "note": "单色阶，深=高",
                "rows": ["高概率", "中概率", "低概率"],
                "cols": ["低影响", "中影响", "高影响"],
                "cells": [[3, 6, 9], [2, 4, 6], [1, 2, 2]]},
    # ---- 分布 ----
    "histogram": {"type": "histogram", "title": "客单价集中在 55–70 元，长尾拖到 120 元",
                  "subtitle": "2,400 笔订单客单价 · 等宽 8 箱",
                  "unit_meta": "元", "source": "订单明细", "note": "均值/中位参考线",
                  "values": _wave(62, 16, 40, 0.3)},
    "box": {"type": "box", "title": "呼和浩特离散最大：四分位跨 74 元",
            "subtitle": "六城客单价分布 · 箱体 P25–P75",
            "unit_meta": "元", "source": "示例数据；n=25/城", "note": "须线 1.5 IQR",
            "groups": [{"label": "呼和浩特", "values": _wave(212, 42, 25, 0.2), "accent": True},
                       {"label": "鄂尔多斯", "values": _wave(268, 30, 25, 1.1)},
                       {"label": "包头", "values": _wave(188, 24, 25, 2.0)},
                       {"label": "赤峰", "values": _wave(164, 20, 25, 2.8)}]},
    "violin": {"type": "violin", "title": "鄂尔多斯 P90 比中位高 42 元，尾部最厚",
              "subtitle": "四城客单价分布 · 14 箱平滑",
              "unit_meta": "元", "source": "示例数据；n=25/城", "note": "竖线为中位数",
              "groups": [{"label": "呼和浩特", "values": _wave(212, 42, 25, 0.2), "accent": True},
                         {"label": "鄂尔多斯", "values": _wave(268, 30, 25, 1.1)},
                         {"label": "包头", "values": _wave(188, 24, 25, 2.0)},
                         {"label": "赤峰", "values": _wave(164, 20, 25, 2.8)}]},
    "ridgeline": {"type": "ridgeline", "title": "收入越高，客单价分布整体右移 60 元",
                  "subtitle": "五档收入家庭客单价分布",
                  "unit_meta": "元", "source": "样本 n=1,250 户", "note": "共享横轴",
                  "groups": [{"label": "5 万以上", "values": _wave(248, 34, 24, 1.4), "accent": True},
                             {"label": "3–5 万", "values": _wave(212, 30, 24, 1.0)},
                             {"label": "2–3 万", "values": _wave(186, 26, 24, 0.6)},
                             {"label": "1–2 万", "values": _wave(160, 22, 24, 0.2)},
                             {"label": "1 万以下", "values": _wave(136, 20, 24, -0.2)}]},
    "scatter": {"type": "scatter", "title": "价格每降 10%，销量涨 12.6%：弹性 −1.26",
                "subtitle": "28 个 SKU 月销与到手价 · OLS 拟合",
                "unit_meta": "件/月", "source": "示例数据；同品类",
                "note": "灰色点为常规 SKU",
                "points": _scatter_pts(), "xlabel": "到手价（元）"},
    "bubble": {"type": "bubble", "title": "呼和浩特人均 1,180 元，鄂尔多斯 1,320 元",
               "subtitle": "12 盟市 · 气泡面积=常住人口",
               "unit_meta": "元/人", "source": "示例数据", "note": "虚线为均值",
               "points": [{"x": 1180, "y": 7.2, "size": 355, "label": "呼和浩特", "accent": True},
                          {"x": 1320, "y": 6.4, "size": 268, "label": "鄂尔多斯", "accent": True},
                          {"x": 980, "y": 5.1, "size": 221},
                          {"x": 760, "y": 4.2, "size": 403},
                          {"x": 690, "y": 3.4, "size": 330},
                          {"x": 640, "y": 2.9, "size": 287},
                          {"x": 610, "y": 2.2, "size": 245},
                          {"x": 580, "y": 1.8, "size": 198},
                          {"x": 540, "y": 1.1, "size": 152},
                          {"x": 510, "y": 0.6, "size": 118}]},
    "parallel": {"type": "parallel", "title": "门店 A 四维均在前 25%，门店 F 全部后 25%",
                 "subtitle": "六家门店 · 四维标准化 0–1",
                 "unit_meta": "指数", "source": "门店经营数据", "note": "各轴独立标准化",
                 "axes": ["客单", "复购", "上新", "毛利"],
                 "items": [{"name": "门店 A", "values": [82, 76, 71, 68], "accent": True},
                           {"name": "门店 B", "values": [64, 58, 62, 55]},
                           {"name": "门店 C", "values": [55, 48, 52, 50]},
                           {"name": "门店 D", "values": [46, 52, 44, 47]},
                           {"name": "门店 E", "values": [38, 34, 41, 36]},
                           {"name": "门店 F", "values": [28, 26, 30, 29]}]},
    # ---- 不确定性 / 监控 ----
    "error_bar": {"type": "error_bar", "title": "六城复购率最高 41.2%，区间大面积重叠",
                  "subtitle": "复购率均值 ± 标准误（SE）",
                  "unit_meta": "%", "source": "样本 n=260/城", "note": "区间重叠≠不显著",
                  "err_type": "SE",
                  "items": [{"label": "呼和浩特", "value": 34.6, "err": 2.1},
                            {"label": "鄂尔多斯", "value": 41.2, "err": 3.4, "accent": True},
                            {"label": "包头", "value": 33.6, "err": 2.6},
                            {"label": "赤峰", "value": 31.2, "err": 2.2},
                            {"label": "通辽", "value": 30.4, "err": 1.9},
                            {"label": "乌海", "value": 28.8, "err": 3.8}]},
    "forest": {"type": "forest", "title": "高价值会员效应 +0.62，显著高于基线",
                  "subtitle": "效应量及 95% 置信区间",
                  "unit_meta": "效应量", "source": "回归结果", "note": "关联非因果",
                  "baseline": 0.0, "ci_level": "95% CI",
                  "items": [{"label": "高价值会员", "est": 0.62, "lo": 0.41, "hi": 0.83,
                             "accent": True},
                            {"label": "中价值会员", "est": 0.28, "lo": 0.11, "hi": 0.45},
                            {"label": "价格敏感", "est": -0.06, "lo": -0.24, "hi": 0.12},
                            {"label": "新客", "est": -0.31, "lo": -0.52, "hi": -0.10},
                            {"label": "沉睡客", "est": -0.48, "lo": -0.71, "hi": -0.25}]},
    "control": {"type": "control", "title": "第 14 周越限一次：单点异常，未出现连续漂移",
                 "subtitle": "周均客单价 · 均值 100、控制带 ±12",
                 "unit_meta": "元", "source": "20 周直营数据", "note": "3σ 控制限",
                 "series": [{"name": "客单价", "values":
                             [98, 102, 97, 101, 99, 103, 96, 100, 101, 99,
                              104, 98, 102, 126, 101, 97, 99, 103, 100, 101]}],
                 "xlabels": [f"W{i + 1}" for i in range(20)],
                 "center": 100, "band": 12},
    "funnel": {"type": "funnel", "title": "加购到下单流失 60%，是最大漏点",
               "subtitle": "一次大促转化漏斗 · 人数",
               "unit_meta": "人", "source": "站内埋点", "note": "逐级流失直接标注",
               "stages": [{"label": "曝光", "value": 12000}, {"label": "点击", "value": 4800},
                          {"label": "加购", "value": 1900}, {"label": "下单", "value": 760},
                          {"label": "支付", "value": 610}]},
    "bullet": {"type": "bullet", "title": "动销率 82%，距目标差 18 个百分点",
               "subtitle": "实际 vs 目标 vs 绩效区间",
               "unit_meta": "%", "source": "月度经营台账", "note": "目标线在柱之上",
               "label": "动销率", "value": 82, "target": 100, "unit": "%",
               "target_source": "年度经营目标",
               "bands": [{"to": 60, "label": "差"}, {"to": 85, "label": "中"},
                         {"to": 100, "label": "优"}]},
    "gauge": {"type": "gauge", "title": "月度达成 78%，距 100% 目标还差 22 个百分点",
              "subtitle": "年度目标完成度 · 0–120%",
              "unit_meta": "%", "source": "经营看板", "note": "文字状态同步给出",
              "value": 78, "min": 0, "max": 120, "target": 100, "unit": "%"},
    "target_band": {"type": "target_band", "title": "六个月里 3 个月落在目标带内",
                    "subtitle": "月度毛利率 vs 目标带 18%–22%",
                    "unit_meta": "%", "source": "财务月报", "note": "带外强调色",
                    "xlabels": ["1 月", "2 月", "3 月", "4 月", "5 月", "6 月"],
                    "series": [{"name": "毛利率", "values": [17.2, 19.8, 21.4, 23.1, 20.6, 18.4]}],
                    "band": {"lo": 18, "hi": 22, "label": "目标带"}},
    "dual_axis": {"type": "dual_axis", "title": "规模在涨，毛利率却从 22% 掉到 18%",
                  "subtitle": "规模（柱）与毛利率（线）· 双单位",
                  "unit_meta": "亿元 / %", "source": "财务口径",
                  "note": "左轴自 0 起，右轴只读趋势",
                  "xlabels": ["2021", "2022", "2023", "2024", "2025", "2026E"],
                  "bars": {"name": "规模", "values": [2100, 2450, 2706, 3002, 3126, 3350],
                           "unit": "亿元"},
                  "line": {"name": "毛利率", "values": [22.1, 21.4, 20.2, 19.8, 18.4, 18.0],
                           "unit": "%"}},
    "radar": {"type": "radar", "title": "头部品牌复购 86 分，价格力仅 58 分",
              "subtitle": "五维能力画像 · 统一 0–100 尺度",
              "unit_meta": "分", "source": "品牌调研 n=1,200",
              "note": "多边形面积不是总分",
              "axes": ["价格力", "复购", "上新", "服务", "毛利"],
              "series": [{"name": "头部品牌", "values": [58, 86, 74, 88, 71], "accent": True},
                         {"name": "区域品牌", "values": [82, 61, 66, 52, 63]}]},
    # ---- 时间 / 流程 ----
    "cal_heatmap": {"type": "cal_heatmap", "title": "大促周单日峰值 128 单，是平日的 3.4 倍",
                    "subtitle": "2026-03-01 起 35 天日订单量",
                    "unit_meta": "单", "source": "订单流水", "note": "斜纹为缺失日期",
                    "days": _days("2026-03-01", 35, 32, 96)},
    "gantt": {"type": "gantt", "title": "六项任务里采购前置期占了 32 天，是总工期瓶颈",
             "subtitle": "2026 年上新计划 · 起止日期",
             "unit_meta": "天", "source": "项目排期表", "note": "菱形为里程碑",
             "today": "2026-03-20",
             "tasks": [{"label": "需求确认", "start": "2026-03-02", "end": "2026-03-08"},
                       {"label": "选品打样", "start": "2026-03-06", "end": "2026-03-18", "accent": True},
                       {"label": "采购备货", "start": "2026-03-15", "end": "2026-04-16", "accent": True},
                       {"label": "内容制作", "start": "2026-04-01", "end": "2026-04-10"},
                       {"label": "首发上线", "start": "2026-04-18", "end": "2026-04-18", "milestone": True},
                       {"label": "复盘迭代", "start": "2026-04-20", "end": "2026-04-28"}]},
    "candlestick": {"type": "candlestick", "title": "12 个交易日：收盘 95–106 元，5 根阳线",
                    "subtitle": "示例标的日 K · 开高低收",
                    "unit_meta": "元", "source": "行情快照", "note": "红涨绿跌",
                    "candles": _candles()},
    "sankey": {"type": "sankey", "title": "原料 100 单位里，只有 61 流向终端",
                  "subtitle": "供应链流量拆解 · 同一单位",
                  "unit_meta": "单位", "source": "供应链台账", "note": "流带宽∝流量",
                  "nodes": [{"id": "raw", "label": "原料"}, {"id": "prod", "label": "生产"},
                            {"id": "dist", "label": "分销"}, {"id": "direct", "label": "直营"},
                            {"id": "dealer", "label": "经销"}, {"id": "online", "label": "线上"},
                            {"id": "offline", "label": "线下"}],
                  "links": [{"from": "raw", "to": "prod", "value": 100},
                            {"from": "prod", "to": "dist", "value": 60},
                            {"from": "prod", "to": "direct", "value": 25},
                            {"from": "prod", "to": "dealer", "value": 15},
                            {"from": "dist", "to": "online", "value": 35},
                            {"from": "dist", "to": "offline", "value": 25},
                            {"from": "direct", "to": "online", "value": 15},
                            {"from": "direct", "to": "offline", "value": 10},
                            {"from": "dealer", "to": "offline", "value": 15}]},
    "streamgraph": {"type": "streamgraph", "title": "即食辅食占比从 12% 升到 21%，是最快的结构变化",
                    "subtitle": "2020–2026 各品类规模构成",
                    "unit_meta": "亿元", "source": "行业年报", "note": "非负中心堆叠",
                    "xlabels": ["2020", "2021", "2022", "2023", "2024", "2025", "2026E"],
                    "series": [{"name": "主粮", "values": [420, 455, 492, 528, 566, 602, 640]},
                               {"name": "零食", "values": [180, 205, 232, 258, 288, 315, 344]},
                               {"name": "即食辅食", "values": [58, 76, 96, 121, 148, 176, 208],
                                "accent": True}]},
    "kpi_break": {"type": "kpi_break", "title": "GMV 3,126 亿，增量 124 亿里食品贡献 78 亿",
                  "subtitle": "核心指标 + 趋势 + 驱动拆解",
                  "unit_meta": "亿元", "source": "经营月报", "note": "三模块同口径",
                  "kpi": {"label": "年度 GMV", "value": 3126, "unit": "亿元",
                          "delta_label": "+4.1% 同比"},
                  "trend": {"xlabels": ["2021", "2022", "2023", "2024", "2025", "2026E"],
                            "values": [2100, 2450, 2706, 3002, 3126, 3350]},
                  "breakdown": {"items": [{"label": "食品", "value": 78, "accent": True},
                                          {"label": "医疗", "value": 35},
                                          {"label": "用品", "value": 12},
                                          {"label": "服务", "value": -1}]}},
    "rose": {"type": "rose", "title": "八月是全年峰值，二月最低，相差 2.1 倍",
             "subtitle": "1–8 月订单量 · 面积∝数值",
             "unit_meta": "单", "source": "订单流水", "note": "半径 √ 映射",
             "sectors": [{"label": "1 月", "value": 860}, {"label": "2 月", "value": 610},
                         {"label": "3 月", "value": 940}, {"label": "4 月", "value": 1020},
                         {"label": "5 月", "value": 880}, {"label": "6 月", "value": 790},
                         {"label": "7 月", "value": 1160}, {"label": "8 月", "value": 1280, "accent": True}]},
    # ---- 地理 / 关系 ----
    "choropleth": {"type": "choropleth", "title": "广东、上海、北京三地贡献全国 43% 的销售额",
                   "subtitle": "省域销售额 · 离线示意格网",
                   "unit_meta": "亿元", "source": "分省台账", "note": "虚线框为未提供数据",
                   "regions": [{"name": "北京", "value": 120}, {"name": "天津", "value": 80},
                               {"name": "河北", "value": 65}, {"name": "山西", "value": 42},
                               {"name": "内蒙古", "value": 38}, {"name": "辽宁", "value": 55},
                               {"name": "吉林", "value": 30}, {"name": "黑龙江", "value": 28},
                               {"name": "上海", "value": 150}, {"name": "江苏", "value": 110},
                               {"name": "浙江", "value": 105}, {"name": "安徽", "value": 70},
                               {"name": "福建", "value": 60}, {"name": "江西", "value": 45},
                               {"name": "山东", "value": 95}, {"name": "河南", "value": 75},
                               {"name": "湖北", "value": 68}, {"name": "湖南", "value": 62},
                               {"name": "广东", "value": 135}, {"name": "四川", "value": 72},
                               {"name": "陕西", "value": 50}, {"name": "甘肃", "value": 22},
                               {"name": "宁夏", "value": 15}, {"name": "新疆", "value": 20},
                               {"name": "云南", "value": 40}, {"name": "贵州", "value": 35},
                               {"name": "广西", "value": 48}, {"name": "海南", "value": 18},
                               {"name": "重庆", "value": 58}, {"name": "西藏", "value": 0}]},
    "symbol_map": {"type": "symbol_map", "title": "呼和浩特单城贡献 320 万，是包头的 1.5 倍",
                   "subtitle": "八盟市销售额 · 气泡面积∝数值",
                   "unit_meta": "万元", "source": "分盟市台账", "note": "等距圆柱近似投影",
                   "points": [{"name": "呼和浩特", "lon": 111.7, "lat": 40.8, "value": 320, "accent": True},
                              {"name": "包头", "lon": 109.8, "lat": 40.7, "value": 210},
                              {"name": "鄂尔多斯", "lon": 109.8, "lat": 39.6, "value": 280, "accent": True},
                              {"name": "赤峰", "lon": 118.9, "lat": 42.3, "value": 150},
                              {"name": "通辽", "lon": 122.2, "lat": 43.6, "value": 120},
                              {"name": "呼伦贝尔", "lon": 119.8, "lat": 49.2, "value": 90},
                              {"name": "巴彦淖尔", "lon": 107.4, "lat": 40.7, "value": 110},
                              {"name": "乌兰察布", "lon": 113.1, "lat": 41.0, "value": 95}]},
    "geo_flow": {"type": "geo_flow", "title": "呼和浩特→北京是主通道，占跨省流量 46%",
                 "subtitle": "跨区域调拨流向 · 线宽∝流量",
                 "unit_meta": "吨", "source": "物流台账", "note": "等距圆柱近似投影",
                 "points": [{"id": "hhht", "name": "呼和浩特", "lon": 111.7, "lat": 40.8},
                            {"id": "bt", "name": "包头", "lon": 109.8, "lat": 40.7},
                            {"id": "eeds", "name": "鄂尔多斯", "lon": 109.8, "lat": 39.6},
                            {"id": "bj", "name": "北京", "lon": 116.4, "lat": 39.9},
                            {"id": "tj", "name": "天津", "lon": 117.2, "lat": 39.1},
                            {"id": "sjz", "name": "石家庄", "lon": 114.5, "lat": 38.0}],
                 "flows": [{"from": "hhht", "to": "bj", "value": 460},
                           {"from": "bt", "to": "bj", "value": 210},
                           {"from": "eeds", "to": "bj", "value": 180},
                           {"from": "hhht", "to": "tj", "value": 120},
                           {"from": "bt", "to": "sjz", "value": 90},
                           {"from": "eeds", "to": "sjz", "value": 70}]},
    "network": {"type": "network", "title": "原料供应商 A 连接 5 个节点，是最关键的单一风险点",
                 "subtitle": "供应链关系网 · 节点大小=度数",
                 "unit_meta": "条", "source": "采购台账", "note": "环形布局，无地理含义",
                 "nodes": [{"id": "A", "label": "供应商 A", "size": 5, "accent": True},
                           {"id": "B", "label": "供应商 B", "size": 3},
                           {"id": "C", "label": "供应商 C", "size": 2},
                           {"id": "D", "label": "工厂 D", "size": 3},
                           {"id": "E", "label": "工厂 E", "size": 3},
                           {"id": "F", "label": "仓配 F", "size": 2},
                           {"id": "G", "label": "渠道 G", "size": 2},
                           {"id": "H", "label": "渠道 H", "size": 1}],
                 "edges": [{"a": "A", "b": "D", "weight": 4}, {"a": "A", "b": "E", "weight": 3},
                           {"a": "A", "b": "F", "weight": 2}, {"a": "A", "b": "G", "weight": 1},
                           {"a": "B", "b": "D", "weight": 3}, {"a": "B", "b": "E", "weight": 2},
                           {"a": "C", "b": "E", "weight": 2}, {"a": "C", "b": "F", "weight": 1},
                           {"a": "D", "b": "G", "weight": 2}, {"a": "E", "b": "H", "weight": 1},
                           {"a": "F", "b": "G", "weight": 2}, {"a": "F", "b": "H", "weight": 1}]},
}

# 密度型图表统一改由 dataset.py（完整数据源，唯一出处）生成：
# 36 个月 × 6 品类、10 门店 × 6 品类、45 SKU、六城 1,560 笔客单价、365 天日销、30 日 OHLC。
SAMPLES.update({
    "line": DS.sample_line(),
    "area": DS.sample_area(),
    "small_mult": DS.sample_small_mult(),
    "streamgraph": DS.sample_streamgraph(),
    "histogram": DS.sample_histogram(),
    "box": DS.sample_box(),
    "violin": DS.sample_violin(),
    "ridgeline": DS.sample_ridgeline(),
    "scatter": DS.sample_scatter(),
    "bubble": DS.sample_bubble(),
    "heatmap": DS.sample_heatmap(),
    "cal_heatmap": DS.sample_cal_heatmap(),
    "candlestick": DS.sample_candlestick(),
    "control": DS.sample_control(),
    "sankey": DS.sample_sankey(),
    "treemap": DS.sample_treemap(),
    "sunburst": DS.sample_sunburst(),
    "gantt": DS.sample_gantt(),
    "funnel": DS.sample_funnel(),
    "error_bar": DS.sample_error_bar(),
    "parallel": DS.sample_parallel(),
    "radar": DS.sample_radar(),
})


def main() -> int:
    theme = sys.argv[1] if len(sys.argv) > 1 else "paper"
    parts = [f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>图表引擎 v2 画廊 · {theme}</title>
<style>
body{{margin:0;background:#F8FAFC;font-family:"Microsoft YaHei","PingFang SC",sans-serif;color:#0F172A}}
.wrap{{max-width:1080px;margin:0 auto;padding:28px 40px 60px;background:#fff}}
h1{{font-size:22px;margin:8px 0 4px}} .sub{{color:#64748B;font-size:13px;margin-bottom:22px}}
.grid{{display:grid;grid-template-columns:1fr;gap:26px}}
.card{{border:1px solid #E2E8F0;border-radius:6px;padding:10px 14px 4px;background:#fff}}
.k{{font:600 11px/1.6 ui-monospace,monospace;color:#B45309;letter-spacing:.06em;text-transform:uppercase}}
svg{{display:block;width:100%;height:auto}}
</style></head><body><div class="wrap">
<h1>图表引擎 v2 · 画廊</h1><div class="sub">主题 {theme} · {len(SAMPLES)} 型 · 内联 SVG，无外部依赖</div><div class="grid">"""]
    ok, fail = [], []
    for key, spec in SAMPLES.items():
        svg = render(spec, theme)
        if svg:
            ok.append(key)
            parts.append(f'<div class="card"><div class="k">{key}</div>{svg}</div>')
        else:
            fail.append(key)
            parts.append(f'<div class="card"><div class="k">{key}</div><p>渲染失败</p></div>')
    parts.append("</div></div></body></html>")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print("ok:", ok)
    print("fail:", fail)
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

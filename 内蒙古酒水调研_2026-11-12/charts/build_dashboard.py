#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内蒙古酒水数据可视化 · 数据刷新脚本

作用：
    读取 ../data/图表序列.csv，把最新数据写回
    ../内蒙古酒水数据可视化.html 的 <script id="chart-data"> JSON 块。

用法：
    python build_dashboard.py

依赖：
    仅 Python 标准库（csv / json / os / re / sys），无需 pandas。
"""

import csv
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE, "..", "data", "图表序列.csv")
HTML_PATH = os.path.join(BASE, "..", "内蒙古酒水数据可视化.html")

REQUIRED_CHARTS = [
    "market",
    "brand",
    "price_band",
    "region",
    "unit_margin",
    "value_chain",
    "cost_structure",
    "capacity",
    "logistics",
    "saving",
]


def load_rows(path):
    """读取长表 CSV，返回统一结构的行列表。"""
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_no, raw in enumerate(reader, start=2):
            chart = (raw.get("chart") or "").strip()
            item = (raw.get("item") or "").strip()
            if not chart or not item:
                continue
            value_text = (raw.get("value") or "").strip()
            try:
                value = float(value_text)
            except ValueError:
                raise ValueError(
                    "第 %d 行 value 不是数字：%r" % (line_no, value_text)
                )
            rows.append(
                {
                    "chart": chart,
                    "item": item,
                    "series": (raw.get("series") or "").strip(),
                    "value": value,
                    "unit": (raw.get("unit") or "").strip(),
                    "note": (raw.get("note") or "").strip(),
                }
            )
    return rows


def group_by_chart(rows):
    """按 chart 分组，输出前端直接消费的 JSON 结构。"""
    data = {key: [] for key in REQUIRED_CHARTS}
    for row in rows:
        data.setdefault(row["chart"], []).append(
            {
                "item": row["item"],
                "value": row["value"],
                "unit": row["unit"],
                "note": row["note"],
            }
        )
    missing = [key for key in REQUIRED_CHARTS if not data.get(key)]
    if missing:
        raise ValueError("缺少图表序列：" + ", ".join(missing))
    return data


def main():
    rows = load_rows(CSV_PATH)
    data = group_by_chart(rows)
    payload = json.dumps(data, ensure_ascii=False, indent=2)

    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    pattern = re.compile(
        r'(<script id="chart-data" type="application/json">)(.*?)(</script>)',
        re.S,
    )
    if not pattern.search(html):
        raise RuntimeError("未找到 chart-data 数据块，请检查 HTML 是否被改动")

    new_html = pattern.sub(
        lambda m: m.group(1) + "\n" + payload + "\n" + m.group(3),
        html,
        count=1,
    )

    with open(HTML_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_html)

    counts = {key: len(value) for key, value in data.items()}
    print("OK ->", os.path.abspath(HTML_PATH))
    print("图表序列：" + ", ".join("%s=%d" % (k, v) for k, v in counts.items()))
    print("总数据点：%d" % sum(counts.values()))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - 脚本入口需要把错误打印给使用者
        print("FAILED:", exc, file=sys.stderr)
        sys.exit(1)

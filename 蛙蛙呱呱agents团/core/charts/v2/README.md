# 图表引擎 v2（core/charts/v2）

研报级图表引擎：**matplotlib → 确定性内联 SVG**，无外部依赖、可离线打开、可打印。
基准工艺来自 `workspace/图鉴-满血_2026-11-15`（kit.py + charts_a–d.py），
现已全量并入本目录，48 型全部由 v2 出图，**不再有 v1 素图兜底**（回退通道保留，仅作保险）。

与 v1（`core/charts/chart_lib.py`）的关系是**分层**：

| | v1 chart_lib | v2（本目录） |
|---|---|---|
| 目标 | 48 型「能画出来」 | 48 型「画到能直接进报告」 |
| 实现 | 手写 SVG 字符串 | matplotlib Figure → SVG |
| 刻度 | 由数据极值直接均分（2,815 / 3,168 …） | MaxNLocator 取整（3,000 / 3,500 / 4,000） |
| 装饰 | 卡片描边、阴影 | 无框、无纵网格、一条基线 |
| 标注 | 图例 + 轴 | 直接标注（线末端「系列 末值」、参考线、异常归因） |
| 失败 | 画不出来就抛错 | 数据不够返回 None，**自动回退 v1** |

48/48 能力不退化：`python -m core.chart_capabilities --check` 仍是 48/48。

## 用法

```python
from core.charts.v2 import render
svg = render({"type": "hbar", "title": "…结论句…", "subtitle": "口径…",
              "unit_meta": "亿元", "source": "S1", "note": "图注",
              "ref": {"value": 18.4, "label": "均值 18.4"},
              "bars": [{"label": "猫砂", "value": 40, "weight": "accent"}]},
             theme="paper")
```

## 与报告系统的分工（EMBED 契约）

报告里不手写图表，也不让图里再画一遍标题。分工是硬约定：

| 元素 | 由谁画 | 说明 |
|---|---|---|
| 结论式标题 | 报告图卡 `<figcaption>` | SVG 内清空，避免双标题 |
| 单位 | 图卡右上 `fig-unit` | 同上 |
| 口径副标题 | 图卡 `.fig-sub` | 由 contract 的 `chart.subtitle` 提供 |
| 来源 + 图注 | 图卡 `.fig-src` | `chart.source` 与 `chart.note` 用「　·　」拼一行 |
| 数据、参考线、归因 | SVG 绘图区 | 唯一允许出现在图内的文字层 |
| 图底通用说明（如「区间重叠不等于显著」） | 独立画廊图 | 嵌入时自动隐藏（`_base.EMBED`） |

引擎侧实现：`report_renderer.render_chart()` 调 `render({**chart, "_embed": True})`，
`base.canvas()` 在 EMBED 下清空四个文本位、收紧上下留白；各 `_footer()` 直接返回。

引擎默认开：契约顶层不写 `chart_engine` 也走 v2；要回滚设
`GUAGUA_CHART_ENGINE=v1`（环境变量优先），或契约里显式写 `"chart_engine": "v1"`。

## 支持的 48 型

比较：`hbar` `vbar` `dot` `lollipop` `pareto` `waterfall` `bridge` `dumbbell`
`grouped_bar` `stacked_bar` `pct_stacked`
趋势：`line` `area` `slope` `small_mult` `streamgraph` `dual_axis` `kpi_break`
构成：`pie` `donut` `treemap` `sunburst` `waffle` `rose`
分布与关系：`histogram` `box` `violin` `ridgeline` `scatter` `bubble` `parallel` `network`
统计与目标：`error_bar` `forest` `control` `funnel` `bullet` `gauge` `target_band` `radar`
时间与流程：`cal_heatmap` `gantt` `candlestick` `sankey`
空间：`choropleth` `symbol_map` `geo_flow`
矩阵：`heatmap`

## 数据源

`core/charts/v2/dataset.py` 是演示与回归的唯一数据源（内蒙古家居百货口径，
种子 20261115，36 个月 × 6 品类、10 门店 × 6 品类、45 SKU、六城 1,560 笔客单价、
365 天日销、30 日 OHLC）。画廊、门禁、交付物共用它，避免「每处一套示例」。
**这些数字只演示图形能力，不能当结论引用。**

## 六条设计规则（改图之前先读）

1. **标题即结论**：`title` 必须是一句带数字的判断，读者不看轴也能拿到结论；
2. **固定几何**：宽 980px、标题 13px、右上单位、左下来源；多张图上下对齐；
3. **一个强调色**：其余灰阶；红/绿只表达「好/坏」，不表达类别；
4. **直接标注**：≤3 系列不用图例，线末端标「系列名 + 末值」，条末端标数值；
5. **去装饰**：无外框、无纵网格、刻度取整；瀑布图遇到「总量 >> 增量」用断轴；
6. **数据不够不画**：schema 不合就回退 v1，绝不出空白图（这条是踩过坑加的）。

## 自查

```bash
python scripts/chart_gallery_v2.py                 # 48 型画廊（单页 HTML）
python scripts/check_chart_v2_coverage.py --strict  # v1/v2 覆盖对齐
python scripts/check_chart_fallback.py             # 48 型样本零回退
python scripts/check_chart_fullness.py             # 六要素 ≥4/6（现全 6/6）
python scripts/check_chart_report_embed.py         # 经报告管线嵌入的 48 型门禁
python -m core.chart_capabilities --check          # 48/48 不退化
```

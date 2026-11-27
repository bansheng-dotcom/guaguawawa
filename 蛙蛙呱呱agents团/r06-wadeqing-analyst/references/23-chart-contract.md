# 23 · 图表契约（chart）：claim-bound 与 fail_if_missing

> R06 报告链第 8 段的领域依据。每张图只回答一条断言，缺数据就不画。

## 1. 六件套

| 字段 | 含义 | 失败后果 |
|---|---|---|
| `claim_id` | 绑定哪条已验证断言 | 未绑定 → 不画 |
| `required_series` | 必须出现的系列/分段 | 缺一个 → 图表失败 |
| `series_completeness` | required / present / ratio / missing | ratio <1 → 回流 analysis |
| `focus_metric` | 这张图聚焦的唯一指标 | 缺失 → 不画 |
| `annotation_plan` | 起止值、差值、最小间距、避让 | 缺标注/会重叠 → 不画 |
| `fail_if_missing` | 缺什么就拒绝渲染 | 为空 → 契约失败 |

视觉自检另记：坐标轴从 0、单位写进标注、标签不重叠、标题与断言一致。

## 2. 为什么“缺数据不画”比“画个大概”重要

图会放大可信度。缺一条系列仍然画出来，读者会把“没画”当成“没有”。
因此本仓把缺数据做成**硬失败**：宁可少一张图，也不让图替证据撒谎。

## 3. 标注的最小要求

- 起点、终点、差值必须标；
- 标注之间最小间距 12px，且声明 `avoid_overlap=true`；
- 单位写在标注里，不依赖图例；
- 聚焦指标只能有一个，避免“双轴图各说各话”。

## 4. 渲染取舍

- 报告用静态 SVG，适配 A4 打印；
- 不引入 ECharts 交互（交互只用于教学画廊）；
- 渲染走 `core.report.report_renderer.render_chart`，不另起渲染器。

## 5. 本仓落点

| 能力 | 代码 | 门禁 |
|---|---|---|
| 规格包 | `analysis_chain/chart_pack.py` | 六件套 + claim 已验证 |
| 渲染 | `deliver._render_chart` | 3/3 渲染成功，否则 deliver FAIL |
| 必绘 | `scripts/check_chart_fail_if_missing.py` | ratio=1、标注齐、fail_if_missing 全 |
| 文注 | deliver | 每个 chart_id 必须进正文图注 |

## 6. 误用反例

| 反例 | 为什么错 | 本仓如何拦 |
|---|---|---|
| 只画两条系列却声称覆盖五个渠道 | 视觉误导 | required_series 缺失 → FAIL |
| 没有起止标注的趋势线 | 读者无法定位变化 | annotation_plan 缺项 → FAIL |
| 双轴图同时讲两个指标 | 相关性错觉 | focus_metric 只能一个 |
| 图注不写来源与单位 | 不可复核 | 图注必含来源/单位/标注 |
| 用交互图替代打印图 | A4 打印丢失信息 | 只走静态 SVG |

## 7. 来源

- Tufte, E. R. *The Visual Display of Quantitative Information* (1983)：数据墨水比与误导性图表。
- Few, S. *Show Me the Numbers* (2012)：图表标注与比较基准。
- WCAG 2.2（W3C）：非文本内容的可访问替代（本仓用 `aria-label`）。
- 本仓 `_refs/dar/references/chart_spec_pack_contract.md`：required_series / completeness / annotation 的工程契约。
- 本仓 `_refs/viz/prompts/*.md`：48 型图的“怎么检查”六维清单。

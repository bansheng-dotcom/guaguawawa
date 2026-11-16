# 图表与报告写法研究（Chart Craft Study）

> 补充输入：`渭河数据分析报告agent.zip`（chart spec / 文字控制 / 对抗审查）与 `数据分析可视化图片提示词.zip`（48 图施工规范）。  
> 详见 [WEIHE_AGENT_LEARNING.md](WEIHE_AGENT_LEARNING.md)。

> 目的：不是列参考，而是把“人家的图为什么这样画”变成可执行的规则。  
> 结论先行：**图不是把数字画出来，图是回答一个具体问题。**

## 1. 我实际看了什么

### 图表语法与选择

| 来源 | 我学到的 | 用在哪 |
|---|---|---|
| [FT Visual Vocabulary](https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary) | 先分问题：变化/比较/分布/关系/构成/ deviation；再选图 | 角色报告的图先按问题选，不按“有数据”选 |
| [Datawrapper Academy](https://www.datawrapper.de/academy/) | 标题写结论、直接标注、参考线、来源、样本量 | 图题改结论；加 source；少用图例 |
| [Storytelling with Data](https://www.storytellingwithdata.com/blog) | 一图一信息；去掉与结论无关的装饰 | 删掉通用“当前 vs 目标”图 |
| [Observable Plot](https://observablehq.com/plot/) | 用 grammar 组合 mark/scale/annotation | 图应有 mark + annotation，不只是 bar |
| [Vega-Lite](https://vega.github.io/vega-lite/) | 图表 spec 化：data/transform/mark/encoding | 代码里把图规格化，不手写 SVG |
| [IBM Carbon Charts](https://carbondesignsystem.com/data-visualization/chart-types/) | 企业图表的可读性/一致性 | 统一颜色/字号/来源位置 |
| [Material Charts](https://m3.material.io/components/charts/overview) | 组件化图表规范 | 图组/卡片布局 |
| [D3 Gallery](https://observablehq.com/@d3/gallery) | 复杂图（Sankey/heatmap）的交互与标注 | 只在必要时用复杂图 |

### 报告写法

| 来源 | 我学到的 | 用在哪 |
|---|---|---|
| [Consulting Slide Standards](https://deckary.com/blog/consulting-slide-standards) | 动作标题、一页一信息、金字塔、每数据带来源 | 章节标题写结论；每节只讲一个判断 |
| [Amazon 2025 Shareholder Letter](https://www.aboutamazon.com/news/company-news/amazon-ceo-andy-jassy-2025-letter-to-shareholders) | 业务链、分部、FCF、长期投入 | 报告先讲链，再讲数字 |
| [MercadoLibre Annual Reports](https://investor.mercadolibre.com/financial-information/annual-reports) | GMV/支付/物流分开讲 | 电商类角色分链 |
| [Microsoft Annual Report](https://www.microsoft.com/investor/reports/ar26/index.html) | 分部收入/利润/现金流 | 财务角色用桥/分部 |
| [SEC 10-K](https://www.sec.gov/edgar/browse/?CIK=0001018724) | 风险因素/管理层讨论 | 报告要有边界/反证 |

## 2. 十张图，十种问题

| 问题 | 正确图 | 错误图 | 关键标注 |
|---|---|---|---|
| 时间怎么变 | line / area | 饼图 | 最后一点、拐点、目标线 |
| 谁大谁小 | hbar（排序） | 3D 柱 | 数值、份额、排序 |
| 构成怎么拆 | waterfall / stacked | 饼图 | 起点/终点、delta |
| 两期对比 | slope / dumbbell | 双轴 | before/after、变化量 |
| 分布 | histogram / box | 平均值柱 | n、分位数 |
| 关系 | scatter | 双轴折线 | 拟合线、异常点 |
| 不确定性 | error bar / forest | 单点柱 | CI、n、基线 |
| 目标达成 | bullet / target band | 仪表盘 | 目标线、区间 |
| 流程/时间线 | gantt（天级） | 分钟级 gantt | 起止、里程碑 |
| 贡献/集中度 | pareto | 普通柱 | 80% 线、前 N 项 |

## 3. 我犯过的三个具体错误

### 错误 1：分钟级事件用 Gantt

R20 事故 09:00→09:42，只有 42 分钟。Gantt 的坐标是天，画出来只有两条细线，读者看不出 15/27 的分解。

正确：**waterfall** 拆 0→15→42，直接显示“发现 15 + 定位/恢复 27”。

### 错误 2：TCO 用“当前 vs 目标”

TCO 的差异在分项：货值/物流/关税/资金占用/质量。用一根“当前 102 万 vs 目标 95 万”的条，读者不知道从哪省。

正确：**dumbbell** 看 A/B 分项差，**waterfall** 看 B 从货值到 TCO 的桥。

### 错误 3：所有角色都画“当前 vs 目标”

R19 的核心是“v2 显著、v3 不显著、旧绿集是否牺牲”；画当前 vs 目标没有回答这个问题。

正确：**grouped bar + p 值/失败样本**，或 **slope** 看 baseline→v2/v3；有 CI 时用 **forest/error bar**。

## 4. 报告写法：一段话只做一件事

正确结构：

```text
结论句（带数字）
→ 证据（图/表/来源）
→ 机制（为什么会这样）
→ 影响（所以呢）
→ 反证/边界（什么会推翻）
→ 动作（谁/何时/停止线）
```

错误结构：

```text
背景 → 背景 → 背景 → 一图 → 一段“这一层要回答” → 结论
```

## 5. 代码规则（要落进生成器）

1. 每个 section 先声明 `question`，再选 `chart_type`；
2. 没有 `question` 不许画图；
3. 图必须有 `source`、`n`、`unit`；
4. 图题必须是结论句，不是“XX 趋势”；
5. 能直接标注就不放图例；
6. 有目标/阈值就画 reference line；
7. 有不确定性就画 CI，不画单点；
8. 分钟级流程不用 Gantt，用 waterfall/step；
9. 两期对比用 slope/dumbbell，不用双轴；
10. 构成用 waterfall/stacked，不用饼；
11. 贡献用 pareto，不用普通柱；
12. 没有数据支持的分层，不画图，写“缺数据”。

## 6. 现在的差距

| 项 | 现状 | 目标 |
|---|---|---|
| 图类型 | 大量 hbar/line | 按问题选：waterfall/dumbbell/slope/forest/pareto |
| 图题 | 主题/当前 vs 目标 | 结论句 |
| 标注 | 少 | 目标线/异常点/来源/n |
| 文字 | 模板句多 | 一段一 claim，无模板句 |
| 数据 | 角色 frame/示例 | 有数据才写，没数据写缺口 |
| 长度 | 先凑 8K | 证据决定长度 |

## 7. 已落地的样板

- [R15 TCO 证据优先](<workspace/r15_tco_evidence/report.html>)：dumbbell + waterfall
- [R19 评测证据优先](<workspace/r19_evidence_first/report.html>)：grouped bar + p 值/失败样本
- [R20 事故证据优先](<workspace/r20_incident_evidence/report.html>)：waterfall 拆 MTTR

这三份都不长，但每个结论都能回到数据；比 20 份 8K 模板更接近“分析”。

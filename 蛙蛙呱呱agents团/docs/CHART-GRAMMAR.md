# 图表语法（CHART-GRAMMAR）

> 由 `core/charts/chart_grammar.py` 导出，不要手改。
> 依据：Financial Times《Visual Vocabulary》九类意图 + From Data to Viz 数据格式决策树。
> 来源：https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary ｜ https://www.data-to-viz.com/

共 **100** 条语法；本仓库可渲染 **47** 种，缺口 **48** 种（= 角色该补什么数据）。

## 偏差 deviation

| 图型 | 数据形状 | 什么时候用 | 常见误用 | 可渲染 |
|---|---|---|---|---|
| `diverging` | signed | 相对 0 或目标的正负偏离 | 不标基准线 | ✅ |
| `diverging_stacked` | composition | 问卷式赞同/中立/反对 | 中性段挤掉两侧 | — |
| `spine` | signed | 一个值拆成两个对立分量 | 两段比例失真 | — |
| `surplus_line` | series | 盈余/赤字随时间的填充面积 | 基线漂移 | — |
| `baseline_dot` | category | 每个点相对基准的偏移 | 基准不一致 | — |
| `change_column` | signed | 相对上期的增减柱 | 正负配色反直觉 | — |

## 相关 correlation

| 图型 | 数据形状 | 什么时候用 | 常见误用 | 可渲染 |
|---|---|---|---|---|
| `scatter` | category | 两个连续变量找关系 | 把相关讲成因果 | ✅ |
| `bubble` | category | 第三维用面积编码 | 面积按半径画（应平方） | ✅ |
| `connected_scatter` | series | 两变量的关系随时间移动 | 路径交叉看不懂 | — |
| `line_column` | series | 量（柱）与率（线）同图 | 双轴刻度误导 | — |
| `heatmap` | matrix | 两类目交叉的强弱 | 色阶不归一 | ✅ |
| `correlogram` | matrix | 多变量两两相关 | 只给系数不给样本量 | — |
| `density_2d` | distribution | 点太多时的二维密度 | 把密度当概率 | — |
| `hexbin` | distribution | 超大数据量的分箱 | 分箱尺寸掩盖结构 | — |
| `pca` | matrix | 多维降维后的聚类 | 主成分不可解释 | — |
| `dendrogram` | matrix | 层次聚类结构 | 距离度量不写清 | — |

## 排序 ranking

| 图型 | 数据形状 | 什么时候用 | 常见误用 | 可渲染 |
|---|---|---|---|---|
| `dot` | category | 名次比数值重要，3–8 项 | 点太密 | ✅ |
| `lollipop` | category | 要名次也要数值 | 杆太长 | ✅ |
| `pareto` | category | 头部集中度，含其他 | 把其他排第一 | ✅ |
| `hbar` | category | 类目名长、条目多 | 轴不从 0 起 | ✅ |
| `ordered_column` | category | 名次且标签短 | 列太多变栅栏 | — |
| `slope` | series | 名次随时间变化 | 只两点也画斜率 | ✅ |
| `bump` | series | 多主体名次交替 | 名次线交叉成毛线 | ✅ |
| `proportional_symbol` | category | 差距极大、只比量级 | 面积难精读 | — |
| `dot_strip` | distribution | 多类目下摊开个体值 | 重复值重叠 | — |

## 分布 distribution

| 图型 | 数据形状 | 什么时候用 | 常见误用 | 可渲染 |
|---|---|---|---|---|
| `histogram` | distribution | 看形状与偏态 | 分箱拍脑袋 | ✅ |
| `box` | distribution | 多组分布比较 | 样本太少也画 | ✅ |
| `violin` | distribution | 复杂分布、多峰 | 小样本形状假 | ✅ |
| `strip` | distribution | 个体值直接摊开 | 点重叠 | ✅ |
| `beeswarm` | distribution | 避免重叠的散点分布 | 点数过多 | ✅ |
| `ridge` | distribution | 多组分布叠成山脊 | 层数太多糊成一片 | ✅ |
| `density` | distribution | 连续变量的密度曲线 | 带宽选择影响结论 | — |
| `cumulative_curve` | distribution | 看集中度（洛伦兹） | 不标对角线 | — |
| `barcode` | distribution | 逐条列出所有值 | 密集处看不清 | — |
| `population_pyramid` | matrix | 年龄×性别的背靠背分布 | 分组粒度不一致 | — |
| `raincloud` | distribution | 分布 + 个体点 + 箱线三合一 | 元素过多 | — |
| `qq` | distribution | 检验分布是否正态 | 样本太少 | — |
| `lorenz` | distribution | 不平等程度 | 不标基尼系数 | — |

## 时序 change over time

| 图型 | 数据形状 | 什么时候用 | 常见误用 | 可渲染 |
|---|---|---|---|---|
| `line` | series | 连续时间看趋势 | 时间轴不等距 | ✅ |
| `area` | series | 总量变化、单系列 | 多系列堆叠看不出个体 | ✅ |
| `step` | series | 阶梯式变化 | 平滑掩盖跳变 | ✅ |
| `column` | series | 少数时点的量 | 时点太多 | — |
| `line_column` | series | 量与率同时看 | 双轴 | — |
| `slope` | series | 两三个时点的变化 | 点多就不适用 | ✅ |
| `fan` | series | 预测区间随时间变宽 | 把区间当中值 | — |
| `calendar_heatmap` | matrix | 日/周/月的周期规律 | 精确值读不出 | — |
| `priestley` | flow | 起止时间与时长 | 时间轴拥挤 | — |
| `circle_timeline` | flow | 离散事件的大小与时间 | 圆面积难比较 | — |
| `seismogram` | series | 波动极大的序列 | 基线被噪声吃掉 | — |
| `streamgraph` | series | 多系列总量与结构 | 读数困难 | — |
| `stock` | series | 开高低收 | 没有量纲说明 | — |
| `connected_scatter` | series | 两变量随时间移动 | 路径交叉 | — |
| `spiral` | series | 长周期节律（年/季） | 读不出绝对时间 | — |
| `small_mult` | matrix | 多主体同一时间轴对比 | 小图太多看不清 | ✅ |
| `multi_line` | series | 多系列同时看 | 系列超过 4 条 | ✅ |
| `area_range` | range | 区间随时间的带状 | 上下限来源不明 | ✅ |
| `spark_table` | matrix | 表格里嵌迷你趋势 | 迷你图没有刻度 | ✅ |

## 构成 part-to-whole

| 图型 | 数据形状 | 什么时候用 | 常见误用 | 可渲染 |
|---|---|---|---|---|
| `share_bar` | composition | 占比且强调结构 | 分段 <5% | ✅ |
| `treemap` | composition | 层级构成、面积即份额 | 小块点不出 | ✅ |
| `waffle` | composition | 数格子的占比直觉 | 格子不能整除 | ✅ |
| `donut` | composition | 2–3 个大块 | 超过 5 块 | ✅ |
| `pie` | composition | 最常见但不精确 | 多块难比较 | ✅ |
| `stacked_bar` | composition | 构成随时间/类目变化 | 中间段不可比 | — |
| `pct_stacked` | composition | 只比结构不比总量 | 总量差异被抹掉 | ✅ |
| `marimekko` | composition | 宽度=总量、高度=结构 | 格子太多 | ✅ |
| `sunburst` | composition | 两层以上层级构成 | 内圈小到看不见 | ✅ |
| `gridplot` | composition | 百分比用格子铺 | 格子数不整除 | — |
| `arc` | composition | 议会式席位构成 | 只适合整数席位 | — |
| `voronoi` | composition | 点转面积 | 面积难精读 | — |
| `waterfall` | flow | 有增有减的构成 | 起终点不闭合 | ✅ |
| `fluid` | composition | 构成随时间的流动 | 标签拥挤 | — |
| `venn` | composition | 两个集合的交叠 | 面积不按比例 | — |
| `dot_matrix` | matrix | 类目×类目的点阵 | 点大小无说明 | ✅ |

## 量级 magnitude

| 图型 | 数据形状 | 什么时候用 | 常见误用 | 可渲染 |
|---|---|---|---|---|
| `hbar` | category | 比大小、标签长 | 轴不从 0 | ✅ |
| `vbar` | category | 比大小、项少 | 项多就挤 | ✅ |
| `kpi` | single | 3–5 个关键数字 | 无关数字拼一起 | ✅ |
| `range` | range | 给的是区间不是单值 | 只画中点 | ✅ |
| `dumbbell` | category | 两组值在同一行对比 | 差值方向不标 | ✅ |
| `bullet` | category | 实际值 vs 目标 vs 区间 | 目标线不标数值 | ✅ |
| `gauge` | single | 单指标完成度 | 表盘过度装饰 | ✅ |
| `paired_bar` | category | 两个系列并排 | 系列超过 2 个 | — |
| `radar` | category | 多维度画像 | 轴顺序随意 | ✅ |
| `parallel` | matrix | 多维比较 | 维度过多 | ✅ |
| `isotype` | category | 整数计数、直觉化 | 用小数切图 | — |
| `dual_axis` | series | 量 + 率双轴 | 两轴不标单位 | — |
| `timeline` | flow | 里程碑与时长 | 时间轴不等距 | ✅ |

## 空间 spatial

| 图型 | 数据形状 | 什么时候用 | 常见误用 | 可渲染 |
|---|---|---|---|---|
| `choropleth` | matrix | 按行政区着色 | 用总量而非比率 | ✅ |
| `symbol_map` | matrix | 按点位大小编码 | 小差异看不出 | — |
| `flow_map` | flow | 明确的空间移动 | 线条交叉 | — |
| `contour` | matrix | 等值线 | 插值过度 | — |
| `cartogram` | matrix | 面积按值缩放 | 地理失真 | — |
| `dot_density` | distribution | 事件点位密度 | 不标注模式 | — |
| `hexbin_map` | distribution | 网格化密度 | 网格尺寸影响结论 | — |
| `locator` | matrix | 先定位再看数据 | 地图喧宾夺主 | — |

## 流向 flow

| 图型 | 数据形状 | 什么时候用 | 常见误用 | 可渲染 |
|---|---|---|---|---|
| `sankey` | flow | 多对多流转 | 流量不加总核对 | ✅ |
| `funnel` | flow | 阶段转化 | 阶段口径不一致 | ✅ |
| `chord` | matrix | 两两流向 | 读不出净流向 | — |
| `network` | matrix | 关系强度 | 节点太多成毛球 | ✅ |
| `waterfall` | flow | 过程账（有增有减） | 起终点不闭合 | ✅ |
| `gantt` | flow | 任务与时长 | 时间粒度不一致 | ✅ |

## 缺口清单（有图型、没数据或没渲染器）

`arc`、`barcode`、`baseline_dot`、`calendar_heatmap`、`cartogram`、`change_column`、`chord`、`circle_timeline`、`column`、`connected_scatter`、`contour`、`correlogram`、`cumulative_curve`、`dendrogram`、`density`、`density_2d`、`diverging_stacked`、`dot_density`、`dot_strip`、`dual_axis`、`fan`、`flow_map`、`fluid`、`gridplot`、`hexbin`、`hexbin_map`、`isotype`、`line_column`、`locator`、`lorenz`、`ordered_column`、`paired_bar`、`pca`、`population_pyramid`、`priestley`、`proportional_symbol`、`qq`、`raincloud`、`seismogram`、`spine`、`spiral`、`stacked_bar`、`stock`、`streamgraph`、`surplus_line`、`symbol_map`、`venn`、`voronoi`

## 选型算法

```
1. intent = 从本节标题/问题/图题里判意图（九类，关键词计分）
2. shape  = 从数字里判形状（series/signed/composition/range/category/…）
3. cands  = GRAMMAR 中 intent+shape 都对上、且渲染器存在的图型
4. 按『本报告已用次数』升序，且不与前两节同型 → 选中
5. 一个都选不出 → 回退 hbar/vbar（并在 manifest 记 fallback）
```

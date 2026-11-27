# 18 · 数据质量剖析（profile）：六维与偏差，先于任何结论

> R06 分析链第 3 段的领域依据。目的不是“打个质量分”，而是**明确哪些结论现在不能下**。

## 1. 六维的定义与阈值

| 维度 | 计算 | 本仓阈值（`experience/thresholds.json`） | 失败含义 |
|---|---|---|---|
| 完整性 completeness | 各列缺失率 | WARN ≥5%，FAIL ≥30% | 缺失严重，任何总量结论都不可靠 |
| 唯一性 uniqueness | 主键或整行重复率 | FAIL ≥1% | 重复计数会放大指标 |
| 有效性 validity | IQR 离群比例、非数值率 | 离群 ≥10% WARN，≥20% FAIL | 极端值/脏值扭曲均值 |
| 泄漏 leakage | 与目标相关性 ≥0.999，或列名含 future/after/result/target | 出现即 FAIL | 用了未来信息，结论不可复现 |
| 选择偏差 selection_bias | 计划维度的最大分段占比、分段数 | 单段 ≥80% WARN，分段 <2 FAIL | 只看到一个群体，不能外推 |
| 覆盖 coverage | 日期覆盖天数 / 应有天数、分段覆盖 | <80% WARN | 时间/分段有空洞，趋势不可信 |

六维之外还输出 `overall_score`（加权 30/20/15/15/10/10）与 A–D 等级；分数只用于排序，真正阻断的是各维 FAIL。

## 2. 为什么先做 profile 再 explore

explore 的分母是“期内同口径总量”。如果数据本身有 40% 缺失，分母就不是业务事实，而是采集事实。
先 profile 的好处是：把“数据不可用”与“业务真的变化”分开，避免把采集问题写成经营结论。

本仓顺序是硬约束：`plan → profile → explore`，profile 门禁不过，explore 不启动。

## 3. 泄漏为什么是一票否决

泄漏（target leakage）指特征里包含了预测目标时才有的信息，例如：

- 列名 `profit_after_adjust`、`final_result`、`is_churn_next_month`；
- 某列与目标相关系数 0.999，几乎等于目标的副本。

泄漏会让“归因”变成“复述答案”。本仓同时用**列名规则**与**相关系数**两条路检测，任一命中即 FAIL。

## 4. 选择偏差的两种常见形态

1. **单段占比过高**：90% 订单来自一个渠道。此时“整体下滑”本质是“这个渠道下滑”，不能外推到其它渠道；
2. **分段不足**：计划要按城市拆，但数据只有一个城市。此时城市维度不可分析，必须降级。

profile 会在 `selection_bias.dimensions` 中逐维记录 `distinct`、`max_share`、`top_value`，供后续解释层引用。

## 5. 本仓落点

| 能力 | 代码 | 门禁 |
|---|---|---|
| 六维计算 | `analysis_chain/profile.py` | `check()`：六维齐全、completeness/leakage/selection_bias 不得 FAIL、综合分 ≥50 |
| 语义防幻觉 | 复用 `skills/s01_semantics._link` | 语义模型每个 expr 必须落到真实列 |
| 阈值单一出处 | `experience/thresholds.json` | 代码不写第二份阈值 |
| 覆盖 | `coverage.day_coverage` | <80% 记 HIGH（不阻断，但下游必须声明） |

## 6. 误用反例

| 反例 | 为什么错 | 本仓如何拦 |
|---|---|---|
| 缺失 40% 仍照常算总量 | 分母是采集事实，不是业务事实 | completeness FAIL → 阻断 |
| 用 `status=已流失` 预测流失 | 泄漏 | 列名含 result/target 或相关性 ≥0.999 → FAIL |
| 只看一个渠道就下“整体”结论 | 选择偏差 | 单段 ≥80% → WARN；分段 <2 → FAIL |
| 用均值填缺失后当成真实值 | 制造虚假确定性 | 缺失率门禁 + 清洗必须留痕（quality 段） |
| 日期缺 30% 仍画趋势 | 趋势由采集节奏决定 | day_coverage <80% → HIGH |

## 7. 来源

- Rahm, E., & Do, H. H. (2000). Data Cleaning: Problems and Current Approaches. *IEEE Data Engineering Bulletin*, 23(4).
- DAMA International. *DAMA-DMBOK: Data Management Body of Knowledge*（数据质量维度）。
- ISO 8000 系列：数据质量与主数据质量（公开标准）。
- Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in Data Mining: Formulation, Detection, and Avoidance. *ACM TKDD*, 6(4).
- Hernán, M. A., & Robins, J. M. *Causal Inference: What If* (2020)：选择偏差与目标人群。

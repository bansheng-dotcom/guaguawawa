# 17 · 预注册分析计划（plan）：先写计划，再看数

> R06 分析链第 2 段的领域依据。核心不是“计划文档”，而是**把分析自由度锁死**：指标、粒度、窗口、维度、检验、停止条件必须在看数之前确定。

## 1. 解决什么问题

同一份数据，换分母、换窗口、换分组、换检验，几乎可以得到任意想要的结论。
plan 段把“怎么算”提前固化，后续 explore/test 只能按计划执行；想改，就要显式改计划并留下原因。

本仓的硬判据：

- `preregistered = true`
- `data_read_before_plan = false`
- 每个假设恰好对应一轮计划
- 指标/维度/窗口/检验/停止条件缺一项即失败

## 2. 最小契约（`analysis_chain/plan.py` + `experience/plan_schema.json`）

每轮计划必须含：

| 字段 | 示例 | 作用 |
|---|---|---|
| `round` | 1 | 轮次，必须连续 |
| `hypothesis_id` | H1 | 与 frame 一一对应 |
| `analytical_step` | decomposition | 只允许 trend_analysis / decomposition / attribution / risk_mining |
| `question` | 折扣变化是否解释利润变化 | 本轮要回答的问题 |
| `query_spec.metrics` | ["profit"] | 指标口径 |
| `query_spec.group_by` | ["channel","category"] | 分段维度，不得越界 |
| `query_spec.date_range` | start/end/split | 窗口与前后期切分点 |
| `query_spec.grain` | day | 粒度 |
| `expected_output` | table + 必须字段 | 产物形状 |
| `acceptance_criteria` | min_rows=30 | 最少样本 |
| `stop_condition.if_impact_below_pct` | 3.0 | 贡献低于阈值即停止下钻 |
| `tests` | welch_t / bootstrap_ci / cohen_d / holm | 检验清单 |
| `multiple_testing` | holm | 多重检验校正方法 |
| `denominator_definition` | 期内同口径总量 | 分母唯一出处 |

## 3. “计划先于看数”如何被证明

仅有 `data_read_before_plan=false` 这个自报字段不够。本仓再做两件事：

1. plan 工件的输入只有 frame，不接收 CSV；`plan.build` 的签名里没有数据参数；
2. 门禁扫描计划里是否出现数据证据字段（`rows` / `observed` / `actual_values` / `data_profile`），出现即 CRITICAL。

这让“先看数再补计划”在结构上做不到，而不是靠自觉。

## 4. 停止条件为什么必须写

没有停止条件，归因会无限下钻：渠道 → 城市 → 门店 → SKU，总能找到一个“显著”的小格子。
本仓用 `if_impact_below_pct`（默认 3%）作为停止线：贡献低于阈值的分支标记为 minor，不再下钻。
阈值来自 `experience/thresholds.json`，不在代码里写第二份。

## 5. 适用边界

- 计划是“最小充分”，不是“完整项目计划”：只锁会影响结论的选项；
- 探索性分析可以先跑，但一旦要下判断，必须回到 plan 重新预注册；
- 计划变更必须留痕（改 `round` 或新增版本），不能静默改分母；
- 单窗口数据无法支持季节性结论，计划里应显式写“不可验证”，而不是硬做。

## 6. 误用反例

| 反例 | 为什么错 | 本仓如何拦 |
|---|---|---|
| 先跑完 groupby，再补计划 | 计划被结果反向塑造 | plan 不接收数据；出现观测字段即 CRITICAL |
| 同一假设跑多个分母，挑显著的报 | 多重比较 + 口径漂移 | 每轮只允许一个 `denominator_definition`，explore 校验分母一致 |
| `date_range` 只写“近 90 天”不写起止 | 无法复算 | start/end 必填 |
| 没有停止条件 | 无限下钻、噪声当信号 | `if_impact_below_pct` 必填且为数值 |
| 计划里出现 5 个检验但不写校正 | 假阳性膨胀 | `multiple_testing` 必填；test 段执行 Holm |

## 7. 来源

- Nosek et al. (2018). The preregistration revolution. *PNAS*.
- Center for Open Science. *Pre-Registration* 与 *Registered Reports* 指南（公开方法标准）。
- Simmons, J. P., Nelson, L. D., & Simonsohn, U. (2011). False-Positive Psychology. *Psychological Science*, 22(11).
- Tukey, J. W. (1977). *Exploratory Data Analysis*：探索与确证必须分开。
- 本仓 `experience/plan_schema.json`：字段级契约；`analysis_chain/plan.py`：确定性门禁。

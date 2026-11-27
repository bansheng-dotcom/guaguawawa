# 20 · 驱动树与贡献拆解（explain）：把“某渠道下滑”拆到量价

> R06 分析链第 5 段的领域依据。核心要求：**点名一个驱动，就必须给出它的贡献与量价拆解**；同时列出替代解释并说明是否被数据排除。

## 1. 贡献拆解的基本公式

对可加总指标（收入、利润、播放量）：

```
总变化 Δ = Σ 分段变化 Δi
贡献率 = Δi / Δ
```

本仓强制校验 `Σ Δi` 与整体 Δ 的误差 ≤5%，否则判为口径错误。
这条校验能拦住三类常见问题：分段遗漏、重复计数、整体与分段用了不同过滤条件。

## 2. 量价拆解（volume / price / mix）

收入的变化可以拆成：

```
ΔRevenue = ΔQty × P_before  +  ΔP × Qty_after  +  交互项
           \____ 量效应 ____/    \____ 价效应 ___/
```

本仓实现：

- 每个分段先算 `qty_before/after`、`value_before/after`；
- 净价 `P = value / qty`；
- 量效应 = `(qty_after − qty_before) × P_before`；
- 价效应 = `(P_after − P_before) × qty_after`；
- 残差 = `Δ − 量效应 − 价效应`（用于吸收四舍五入与结构交互）。

没有数量列时不允许硬拆：输出 `decomposition_unavailable_reason`，门禁记 WARN，而不是编一个量价。

## 3. 驱动树的三层结构

```
指标（root）
├── level_1 驱动：渠道/品类/套餐…（来自 plan.dimensions[0]）
│   ├── 贡献额 Δ
│   ├── 贡献率 Δi/Δ
│   └── 量效应 / 价效应 / 残差
└── additivity：ΣΔi 与 root Δ 的误差
```

只做一层是刻意的：再往下钻需要新的计划轮次（plan 的 round），不能在 explain 里临时加维度。
这保证“下钻”也有预注册，而不是看完数后追着显著性跑。

## 4. 替代解释：至少两个，且要表态

只给一个原因，等于把相关性包装成结论。本仓要求至少两个替代解释，每个都要有：

- `statement`：替代解释是什么；
- `test`：用什么数据/方法检验；
- `status`：`not_supported` / `partially_supported` / `possible` / `unverifiable`；
- `evidence`：检验依据（样本量变化、份额变化、需要的外部数据）。

内置三类：

1. 口径/采集变化：比较前后期记录数与字段集合；
2. 其他维度结构变化（mix）：比较其他计划维度的份额变化；
3. 季节性/外部因素：单窗口数据只能标 `unverifiable`，不允许假装排除。

## 5. 反事实与因果边界

本段输出反事实参照：

> 若头号驱动维持前期水平，整体将是 X（而非实际的 Y）。

这是**描述性反事实**，不是因果效应。因此：

- `causal_claim=false`，除非有实验（`experiment=true`）；
- 时间为驱动、或把“趋势”当原因，一律 CRITICAL；
- 相关不等于因果：没有随机化/准实验设计时，只能写“与……一致”，不能写“由……导致”。

## 6. 本仓落点

| 能力 | 代码 | 门禁 |
|---|---|---|
| 贡献拆解 | `analysis_chain/explain.py` | 头号驱动必须有贡献率 |
| 量价拆解 | 同上 | 有数量列则给效应；没有则必须写原因 |
| 加总一致 | `driver_tree.additivity` | 误差 >5% → CRITICAL |
| 替代解释 | `alternatives[]` | 少于 2 条 → CRITICAL；每条必须有 test/status |
| 因果边界 | `causal_claim` / `experiment` | 无实验却声称因果 → CRITICAL |
| 与发现一致 | `root.delta` vs findings | 误差 >0.5% → CRITICAL |

## 7. 适用边界

- 适合：可加总指标、分段可比、有数量的场景；
- 不适合：比率指标直接做量价拆解（需先拆分子分母）；
- 不适合：分段之间不可比（如不同口径的门店）；
- 不适合：把残差解释成“结构效应”——残差只说明还有未拆部分。

## 8. 误用反例

| 反例 | 为什么错 | 本仓如何拦 |
|---|---|---|
| “抖音下滑导致整体下滑”，不给贡献与量价 | 只是复述现象 | 头号驱动缺拆解 → CRITICAL/WARN |
| 把时间当原因 | 同义反复 | driver 含时间/date → CRITICAL |
| 只列一个原因 | 确认偏误 | alternatives <2 → CRITICAL |
| 加总对不上还继续写结论 | 口径错误 | 误差 >5% → CRITICAL |
| 把描述性反事实写成“如果我们降价就会……” | 越权因果 | causal_claim 默认 false |

## 9. 来源

- Horngren, C. T. et al. *Cost Accounting*：价差/量差（price/volume variance）的标准拆法。
- DuPont 分析（杜邦恒等式）：把 ROE 拆成利润率 × 周转率 × 杠杆，是驱动树的经典形态。
- Dhuliawala, S. et al. (2023). Chain-of-Verification Reduces Hallucination in Large Language Models. *arXiv:2309.11495*：先给结论、再逐条验证的结构。
- Pearl, J. *Causality* (2009)：反事实与干预的区别。
- 本仓 `skills/s04_rootcause.py`（贡献分解/帕累托）与 `analysis_chain/explain.py`（量价拆解/替代解释门禁）。

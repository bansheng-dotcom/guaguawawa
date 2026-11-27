# 归因与增量：首触/末触/多触，以及为什么相关不是因果

## 来源

- Google Analytics 归因模型说明（first / last / linear / position-based）。
- Shao & Li, *Data-driven Multi-touch Attribution Models*（KDD 2011）。
- Vaver & Koehler, *Measuring Ad Effectiveness Using Geo Experiments*（2011）。
- 两比例样本量：Fleiss, *Statistical Methods for Rates and Proportions*。
- 本角色实现：`growth_chain/attribution.py`、`growth_chain/experiment.py`。

## 核心口径

分母固定为「转化用户数」，每个转化用户贡献 1 个转化，四种模型只是分配方式不同：

| 模型 | 分配规则 |
|---|---|
| first_touch | 100% 给路径第一个渠道 |
| last_touch | 100% 给路径最后一个渠道 |
| linear | 均分给路径所有渠道 |
| position_based | 首 40% / 末 40% / 中间 20% 均分 |

因此恒有：`Σ 各渠道转化 = 转化用户数`，任何模型都不允许改变分母。
收入按同一权重分配，保证 `Σ 渠道收入 = 转化收入`。

增量（incrementality）只能来自实验：A/B、地理实验、PSA/暂停实验。
没有实验证据时，`incrementality.method = not_run`，只能写「相关」，
`causal_claim` 必须为 false；强行写因果会被门禁拦下。

实验设计用两比例公式复算每臂样本量：

```
n = (z_{1-α/2}·√(2p̄(1-p̄)) + z_power·√(p1q1+p2q2))² / (p2-p1)²
```

预注册必须在看数据前固定：假设、主指标、MDE、α、power、停止条件、分析窗口。

## 适用边界

- 归因模型只解释「已发生路径的分配」，不能替代增量实验。
- 多设备、跨端、线下触点缺失时，归因结果只能作为方向参考。
- 末触会高估临近转化的渠道（如品牌词、再营销），首触会高估拉新渠道。
- 样本量不足时，任何「显著」结论都不成立，应继续收集或改设计。

## 误用反例

1. **把相关当因果**：投放涨、收入也涨，就写「投放贡献 100% 增量」。
   门禁：`禁止把相关当因果`，`causal_claim=true` 且无实验证据直接 FAIL。
2. **分母漂移**：首触用「全部访客」做分母，末触用「转化用户」做分母，模型之间不可比。
   门禁：`归因分母与模型一致`，四个模型转化合计必须等于同一分母。
3. **样本不足就下结论**：每臂 800 人宣布显著并全量上线。
   门禁：`样本量不足不得下结论`，观测样本必须达到预注册要求。

# R06L 多场景实验参数模板：使用说明与依据

## 先说结论：没有一组适用于所有业务的固定最佳参数

可以建立**通用默认值 + 场景模板 + 每次实验覆盖**，但 baseline、MDE、业务门槛不能由行业模板替代真实业务数据。模板里的 fallback 只是方案演算默认值；生产实验应使用同一随机化人群、同一事件定义的历史指标或预实验数据。

本仓库参数模板见 `experiment_profiles.json`。当前包含：

- 电商下单转化（商品详情、主图、CTA、购物链路）
- 电商每用户营收（价格、优惠券、套餐）
- 线索/表单提交
- 内容互动/播放（视频素材、标题、封面、投流创意）
- 留存/复购
- 性能/错误率

每个 profile 指定 primary metric、统计类型、baseline 来源、MDE 默认和允许范围、alpha、power、impact_min、护栏指标和建议观察周期。数字是**可编辑的起始模板**，不是行业基准或保证最佳的值。

## 参数应该如何定

### baseline

优先用和实验完全同口径的人群、入口、归因窗口和分母的历史数据。Statsig 的 power analysis 也强调用代表目标实验人群的历史流量和指标统计；如果目标是 checkout 用户，不能拿全站平均代替。没有匹配历史值时，fallback 只能用于模拟规划，不能支撑生产 ship 决策。

### MDE

MDE 是实验希望有足够概率检出的最小变化，不是预测效果。建议先问“这个改动至少改善多少，才能覆盖开发/运营成本并值得上线？”，再转为绝对差异或相对差异。越小的 MDE 通常需要越多曝光。

### alpha 与 power

模板常规取双侧 alpha=0.05、power=0.80；高风险支付、稳定性/安全性场景可考虑更严格 alpha=0.01 和 power=0.90，但样本量会更大。重要结论应给置信区间，不只给 p 值。

### impact_min 与护栏

impact_min 是经济性门槛，不是显著性门槛，应该由毛利、流量、履约能力、折扣成本等换算。主指标有提升但退款、毛利、差评等护栏恶化时，不应仅凭主指标显著就放量。

### 观察周期和反复查看

周期应结合达到样本量的时间、周内/活动周期、转化归因窗口和业务风险设定。不能在每天反复查看普通 p 值、第一次过 0.05 就提前停；若需要提前停止，应使用预先设定的序贯检验方法。

## 本次落地的技术边界

现有 R06L 计算实现支持 **binary_rate（二值比例指标）** 的配置化 profile，计算双比例 z 检验和近似样本量；遇到 continuous_mean 等暂未实现的 profile 会明确报错，不会错误地把金额指标当比例检验。多场景 profile 已建好，但非二值 profile 需要后续补齐均值/Welch 或稳健 bootstrap 样本量计算后才能端到端运行。

命令示例：

```powershell
python stitch_result.py --input orders.csv --profile ecommerce_conversion --output abtest_result.json
python stitch_result.py --input orders.csv --profile ecommerce_conversion --baseline 0.05 --mde 0.10 --alpha 0.05 --power 0.80 --impact-min-pct 3 --output abtest_result.json
```

其中 `--mde` 按 profile 的 `mde.mode` 解释：`relative` 表示相对比例（0.10 = 10% 相对提升），`absolute` 表示绝对比例差（0.01 = 1 个百分点）。

## 来源与设计依据

1. [Statsig — Power Analysis](https://docs.statsig.com/experiments/power-analysis)：MDE 定义为"实验能可靠检出的最小变化"，在 80% 功效下等于 MDE 的效果有 80% 概率产生显著结果；计算基于历史人群的指标均值与方差、每组曝光量、分流比例、α（典型 5%）、功效（典型 80%）、单/双侧检验与多重比较校正（Bonferroni）。文档明确要求历史人群应与实验目标人群一致（可用 targeting gate / qualifying event / previous experiment 逼近），否则曝光与方差估计会失真；并指出 "target MDE is a planning threshold, not a predicted effect"，以及可把观察到的效果与 sizing 时的 MDE 直接对比。Scenario Matrix 表格给出"目标 MDE → 所需各组曝光量/周数"。
2. [Statsig — Experiment Process Overview](https://docs.statsig.com/experiments/process-overview)：流程先做 power analysis，再建实验、配置主次指标、流量分配和分析设置，并在发布前后检查。
3. [Statsig — Monitor an Experiment](https://docs.statsig.com/experiments/monitor)：关注随机分流健康、SRM、交叉曝光及护栏告警，而不是只看最终 lift。
4. [Statsig — How to Read Experiment Results](https://docs.statsig.com/experiments/interpreting-results/read-results)：结果包含相对 lift、置信区间和显著性；建议等到目标周期/功效再决策，并指出序贯测试用于处理提前反复查看的假阳性风险。
5. [Microsoft Research — Experimentation Platform](https://www.microsoft.com/en-us/research/group/experimentation-platform-exp/)：大规模产品实验平台研究与实践资源。

这些资料支持方法和流程原则，不会替你的店铺给出唯一正确的业务阈值；模板中的场景化数值仍需按自家成本、基线、流量和风险校准。

## 本次实现与 Statsig 做法的差异（需注意）

- 样本量公式为双比例 z 检验的近似解析解（Statsig 用历史均值/方差 + 曝光量反推 MDE），只对 `binary_rate` 指标成立，误差来自正态近似。
- 多重比较校正（Bonferroni）、CUPED 方差削减、序贯检验/群序贯 alpha spending 均未实现；多指标或多变体同时看时，应手动把 alpha 调严（例如 0.05/m）。
- 功效门采用"规划样本量达成 **或** 观测 lift ≥ 预设 MDE 即通过"。后者对应 Statsig 的"把观察效果与 sizing MDE 对比"的做法：当实际效果已大于最小有意义效果时，功效不足不会掩盖这个量级的效应。该判定是工程化取舍，不等同于严格的样本量达标。

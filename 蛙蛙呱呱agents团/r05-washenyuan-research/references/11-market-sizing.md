# 市场测算：TAM / SAM / SOM、自下而上与蒙特卡洛

> 用途：R05 研究链第 6 段 `size` 的方法依据。目标是让“市场有多大”变成双口径可对拍、假设可追证据、区间可解释的测算，而不是一个拍脑袋的大数。

## 方法要点

1. **先分清三层市场：**
   - TAM（Total Addressable Market）：在给定产品与地理范围内，全部潜在需求的总盘子；
   - SAM（Serviceable Available Market）：受渠道、合规、产品形态限制后，实际可服务的部分；
   - SOM（Serviceable Obtainable Market）：在竞争与执行约束下，一段时间内可获得的份额。
   报告必须写清每层用了什么过滤条件，不能只给一个“万亿市场”。
2. **双口径对拍：**
   - top-down：自上游品类规模逐层乘过滤系数（或分品类加总）；
   - bottom-up：客户数 × 可服务比例 × 年购买量 × 单价。
   两口径差异 >50% 时，先怀疑口径（是否含线下、是否含耗材），而不是直接取平均。
3. **假设清单是产物的一部分。** 每条假设写：名称、取值、low/high、单位、证据 id、口径说明。没有证据 id 的假设不能进入测算。
4. **敏感性用区间而非点估计。** 对各假设在 [low, high] 内做确定性抽样（固定 LCG 种子），输出 p10/p50/p90；同一输入必须得到同一结果。
5. **SOM 不是“市占率拍脑袋”。** 应回到竞争段：份额上限受前五集中度、渠道容量与自身产能约束。

## 来源

- Metropolis N, Ulam S. “The Monte Carlo Method.” *Journal of the American Statistical Association*, 1949;44(247):335–341（蒙特卡洛抽样的原始方法）。
- Saltelli A, Ratto M, Andres T, et al. *Global Sensitivity Analysis: The Primer*. Wiley, 2008（不确定性分析与分位输出）。
- Blank S, Dorf B. *The Startup Owner's Manual*. K&S Ranch, 2012（TAM/SAM/SOM 与自下而上客户验证的实践来源）。
- Damodaran A. *Investment Valuation*, 3rd ed. Wiley, 2012（市场规模假设对估值与增长的影响，强调口径一致）。
- 国家统计局《统计上大中小微型企业划分办法（2017）》与行业分类 GB/T 4754—2017：客户数/企业数的口径边界，避免把“所有企业”当可服务客户。

## 适用边界

- TAM 只回答“天花板”，不能直接当收入预测；SAM/SOM 必须叠加渠道、合规与竞争约束。
- 蒙特卡洛的输出质量取决于假设区间；区间本身没有证据时，p10–p90 只是“精致的猜测”。
- 假设之间若强相关（如价格与销量），独立均匀抽样会低估尾部风险；本仓只做一阶敏感性，不声称覆盖相关性。
- bottom-up 的客户数若来自“户数”而单价来自“台”，需先统一到“件/户/年”，否则量纲错误。
- 分位口径（最近秩）与插值口径会有小数差异；跨报告比较时必须注明。

## 误用反例

| 反例 | 为什么错 | 本仓拦截 |
|---|---|---|
| 只给 top-down 一个数，没有 bottom-up | 无法判断“客户行为能否花到这么多” | `size:bottom_up_fields` |
| 假设清单没有 low/high，直接给点值 | 无法做敏感性，区间是假的 | `size:assumption_bounds`、`size:order` |
| 假设不挂证据 id | 假设来源不可追，等于拍脑袋 | `size:assumption_evidence` |
| 双口径差 3 倍仍取平均 | 口径不自洽，平均会把错误藏起来 | `size:variance`（>50% 失败） |
| 用随机数但不固定种子，每次结果不同 | 无法复现与审计 | 固定 LCG（`MC_SEED`），测试 `test_determinism` |
| 把 TAM 当 SOM 写进经营目标 | 忽略竞争与执行约束，目标必然落空 | `cross:shares_sum` + 竞争段份额约束 |

## 与本仓落点

- 生产代码：`research_chain/size.py`（top-down、bottom-up、假设清单、LCG 蒙特卡洛、p10/p50/p90）。
- 门禁：`size:top_down`、`size:bottom_up_fields`、`size:assumptions`、`size:assumption_evidence`、`size:assumption_bounds`、`size:variance`、`size:order`、`size:mc_samples`、`size:bottom_up_in_range`。
- 黄金成品：`golden/market-sizing.html`（top-down 87.00 亿元、bottom-up 87.05 亿元、p10 70.08 / p50 88.17 / p90 110.55）。

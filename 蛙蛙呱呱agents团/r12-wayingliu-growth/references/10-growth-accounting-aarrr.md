# 增长会计与 AARRR：指标树、漏斗、异常定位

## 来源

- Dave McClure, *The AARRR Metrics Framework*（2007）：Acquisition / Activation /
  Retention / Referral / Revenue 五段口径。
- Sean Ellis & Morgan Brown, *Hacking Growth*（2017）：北极星指标与增长会计。
- 本角色实现：`growth_chain/diagnose.py`（指标树 + 漏斗 + z/环比异常）。

## 核心口径

增长会计把北极星指标拆成可干预的驱动，直到每个驱动都能落到一个动作：

```
revenue = orders × aov
orders  = visits × order_cvr
signups = visits × signup_cvr
activations = signups × activation_cvr
```

漏斗逐级必须单调（后一级 ≤ 前一级），每一级都记录 `step_cvr` 与 `of_top`。
分母固定：比率一律用「同一窗口、同一批用户」的分子/分母，不做跨窗口拼接。

异常检测两条规则同时保留：
- 统计异常：`|z| ≥ 2.5`（基于窗口内均值/样本标准差）；
- 结构异常：末段均值 vs 中段均值变化 `|Δ| ≥ 20%`。

每条异常都必须带 `rule` 字段，说明它由哪条规则命中，避免「拍脑袋说异常」。

## 适用边界

- 适合日/周粒度的经营诊断，指标口径已经稳定、可逐日取数。
- 不适合把不同渠道、不同口径的指标直接相加；要先把渠道粒度对齐。
- 分母过小（如单日订单 < 30）时，比率波动天然大，只能看趋势不能下结论。
- 异常检测只负责「指路」，根因仍需结合投放、产品、供给侧证据。

## 误用反例

1. **缺数据补零**：某天播放量为空，脚本写成 0，漏斗直接断裂并被误判为「转化暴跌」。
   门禁：`diagnose` 的分母为正 + 缺失不参与求和；自媒体段单独有「缺数据不补零」。
2. **漏斗不单调**：signups 大于 visits，说明口径不一致（访客去重 vs 注册不去重）。
   门禁：`漏斗单调`，直接 FAIL。
3. **把环比当异常**：只看 Δ 不看 z，促销日正常放量被报成故障。
   门禁：异常必须带规则，且规则同时覆盖 z 与周期变化。

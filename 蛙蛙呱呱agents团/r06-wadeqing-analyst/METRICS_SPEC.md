# METRICS_SPEC: R06 蛙得清 · 数据分析统一业务基准账本 (L04)

> 版本：v1.0.0  
> 统一定义 R06 分析师全局指标口径、方差上限、显著性门槛、质检扣分项与异常报警容差。杜绝在代码中硬编码或多轮对话口径漂移。

---

## 1. 核心业务指标口径 (Standard Metric Definitions)
- **GMV (Gross Merchandise Volume)**: 订单总交易金额，包含优惠前金额，口径为 `sum(amount)`，排除已全额退款及测试刷单（`status != 'refunded'`）。
- **UV (Unique Visitors)**: 独立访客数，按自然日/分析周期去重计数 `count(distinct user_id)`。
- **CVR (Conversion Rate)**: 转化率，定义为 `完成目标转化人数 / 访问人数`，取值范围 `[0.0, 1.0]`。
- **LTV (Life Time Value)**: 用户生命周期价值，计算窗口默认为 30天/90天/180天。
- **MRR (Monthly Recurring Revenue)**: SaaS 订阅场景月经常性收入，仅统计状态为 `active` 的订阅。

## 2. 统计检验与报警阈值 (Statistical Gates & Thresholds)
- **显著性水平 (alpha)**: 默认 `0.05`，严格模式下为 `0.01`。
- **统计功效 (Statistical Power)**: 默认 `0.80`，低于 `0.70` 视为低功效样本不足。
- **SRM (Sample Ratio Mismatch) 容差**: 卡方检验 p_value < `0.001` 判定为 SRM 严重失配，实验数据不可信。
- **TAM 估算方差上限 (tam_variance_max)**: 默认 `0.30`，自上而下与自下而上估算方差必须 <= 30%。
- **对账容差 (reconciliation_tolerance)**: 跨源数据对账差异率必须 `<= 0.01` (1%)。

## 3. 集中度与结构判定 (Concentration & Structure)
- **HHI (赫芬达尔指数)**:
  - `HHI < 1500`: 低集中度，健康竞争型
  - `1500 <= HHI <= 2500`: 中度集中
  - `HHI > 2500`: 高度集中，具备单一依赖风险

## 4. 数据质量六维评分基准 (Data Quality Dimensions)
- 完整性 (Completeness): 缺失率 > 20% 扣 20 分；缺失率 > 50% 扣 40 分。
- 唯一性 (Uniqueness): 重复主键存在即扣 30 分。
- 及时性 (Timeliness): 自媒体/业务数据延迟 > 1天标 stale，> 7天标 missing。
- 一致性 (Consistency): 跨表外键孤立行每处扣 10 分。
- 合规性 (Compliance): 出现未脱敏 PII (手机/身份证) 扣 50 分。
- 准确性 (Accuracy): IQR 3倍以外极端离群值超过 5% 触发警告。

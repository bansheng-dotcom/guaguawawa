# 蛙蛙呱呱 · 蛙守线 (R03) 全局财务与合规底线规范账本 (FINANCIAL_SPEC.md)

> 版本: v1.0.0
> 约束标准：全生命周期财务精算、税务合规、数据合规与风控审计硬约束红线

## 1. 财务精算与预算硬红线 (Financial Actuarial Guardrails)
- BALANCE_DIFF_TOLERANCE = 0.00
- 资产负债表与预算滚动校验容差为 0.00，任何单边差额必须阻断结账。
- RUNWAY_ALERT_MONTHS = 6.0
- 现金跑道安全底线：预测跑道低于 6.0 个月时必须强制触发董事会/管理层黄色预警；低于 3.0 个月触发红色紧急状态。
- BURN_MULTIPLE_CEILING = 2.5
- 烧钱倍数警戒上限：净消耗资金 / 净新增 ARR 超过 2.5x 时强制启动控费缩减。

## 2. 税务与股权激励合规基准 (Tax Compliance Benchmarks)
- ISO_HOLDING_PERIOD_YEARS = 2.0
- ISO 期权合规处置：自授予日起至少满 2 年且自行权日起至少满 1 年，否则自动降级为非限定性期权 (NQSO) 处理。
- AMT_EXEMPTION_THRESHOLD = 85700.0
- AMT 替代性最低税基础豁免额度基准，防范行权引发突发流动性税负穿透。

## 3. 隐私与数据留存硬基准 (Privacy & Retention SLA)
- DSR_RESPONSE_SLA_DAYS = 30
- GDPR / CCPA 数据主体权利请求 (DSR) 法定响应上限：严禁超过 30 天，超时直接列为合规违规 (Overdue)。
- FINANCIAL_RECORD_RETENTION_YEARS = 7
- 财务会计及税务凭证法定保存年限：最低 7 年；必须存放于防篡改 WORM (Write Once Read Many) 存储介质。

## 4. 反洗钱与广告合规禁区 (AML & Marketing Anti-Slop)
- AML_CTR_THRESHOLD = 10000.0
- 大额现金交易报告 (CTR) 法定申报阈值：单笔或单日累计超过 $10,000 / ¥50,000 必须触发申报流程。
- STRUCTURING_SMURF_WINDOW_DAYS = 7
- 疑似分拆交易 (Structuring/Smurfing) 监控时间窗口：7 天内连续发生 3 笔以上贴近阈值的交易自动触发黄色警报。
- LICENSED_GUARANTEE_WORDS = ["保本", "稳赚", "零风险", "绝对收益", "保证合规", "保底", "无风险", "100%收益"]
- 广告与对外披露绝对禁区：严禁使用任何形式的保本保收益用语与绝对化合规保证。

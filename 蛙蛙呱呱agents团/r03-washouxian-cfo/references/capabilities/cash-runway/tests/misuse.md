# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/cash-runway/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 2/2`（含 1 个反例）。版本：v2.0.0

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 模塑期内现金转负（第 5 个月） | `cash_out` CRITICAL | ✅ exit=1（`examples/cfo_runway.json`） |
| MU-02 | burn multiple 5.03（> 2.0） | `burn_multiple` HIGH | ✅ exit=1（同上） |
| MU-03 | 触发器命中 4 条（融资/降本/执行/紧急） | `triggers` HIGH | ✅ exit=1（同上） |

## 二、门禁抓不到，靠 §6 自检

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-04 | 用平均净烧钱算 runway | 低估前期烧钱速度 | §6 逐月检查 |
| MU-05 | 现金口径含应收未收 | 跑道虚长 | §6 口径声明 |
| MU-06 | 人力不算社保年终 | 净烧钱偏低 | §6 口径声明 |
| MU-07 | MRR 增长率用最好情况 | 跑道虚长 | §6 保守值 |
| MU-08 | 触发器命中但不给决策 | 没人对开关负责 | §6 |
| MU-09 | 改短 model_months 掩盖耗尽 | 自欺 | §7 EX-08 |
| MU-10 | 把未到账融资算进现金 | 跑道虚长 | §7 EX-12 |
| MU-11 | 跑道结论直接当资金决策 | 越界 | §7 EX-10 |

> **纪律**：runway 是唯一能提前三个月发现问题的指标。逐月表比一句话结论重要得多。

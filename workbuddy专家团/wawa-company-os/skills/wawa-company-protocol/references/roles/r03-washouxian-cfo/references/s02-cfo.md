# S02 CFO 经营诊断
> 蒸馏自: 补充技能/01-当前能力域/alirezarezvani__claude-skills/cfo-advisor/SKILL.md
>


## 方法论（来源 cfo-advisor：burn_rate_calculator / unit_economics_analyzer
+ financial-statements 三表勾稽）

### 现金模拟与跑道

月度模拟：MRR×(1+增速) → 毛利 → 人力 + 运营 → 净烧 → 现金 → runway。
决策触发器（runway 跌破即触发）：

| runway | 触发 |
|---|---|
| ≤ 9 个月 | START FUNDRAISE（开始融资） |
| ≤ 6 个月 | COST REDUCTION PLAN（降本方案） |
| ≤ 4 个月 | EXECUTE CUTS（执行削减） |
| ≤ 3 个月 | EMERGENCY（紧急状态） |

burn multiple = 累计净烧钱 / 净新增 ARR，> 2x 为低效烧钱。

### 单位经济

- churn 由队列收入反推：月流失 = 1 − (M12/M1)^(1/11)（6 个月用 1/5 次方），
  夹紧 [0.001, 0.30]
- LTV = ARPA × 毛利率 / 月流失
- CAC 回本 = CAC / (ARPA × 毛利率)，≤ 12 个月达标
- LTV:CAC ≥ 3 达标

### 三表勾稽（financial-statements）

- 资产 = 负债 + 权益
- 期末现金 = 期初 + 经营 + 投资 + 融资
- 毛利 = 收入 − COGS
- 净利润 → 留存收益（期末留存 = 期初 + 净利 − 分红）

## 现金战术（cash_management）

早收晚付：AR aging 收紧、预付折扣（如 2/10 net 30 的年化 ~36%）、
AP terms 延长；Tier 1 快速现金（hiring freeze / 软件/云成本审计）优先于
Tier 2 结构性降本。

## 已验证算例（run_tests.py T05/T06，已对拍）

- **runway**：`examples/cfo_runway.json` → `cash_out_month=5`
  （按 runway 阈值 ≤6 个月命中「COST REDUCTION PLAN」档）。
- **unitecon**：`examples/cfo_unitecon.json` 两个队列 →
  `cohort_count=2`，队列 a `monthly_churn≈0.019`（由 M12/M1 反推，夹紧
  [0.001, 0.30]）。
- **healthcheck**：`examples/cfo_healthcheck.json` →
  `balance_sheet.ok=true`（资产=负债+权益成立）、
  `income_statement.ok=true`（毛利=收入−COGS 成立）、
  `cash_flow.ok=false`（期末现金 ≠ 期初+经营+投资+融资）→ 整体 `ok=false`。

## 实战踩坑

- churn 反推的次方：6 个月数据用 `1/5` 而非 `1/11`——用错指数会让月流失
  系统性偏大，LTV 偏低，误触发花钱收缩。夹紧区间 [0.001, 0.30] 防队列
  只有 1 个月时除零/负值。
- runway 用**净烧**不是毛利：误把毛利当净烧会高估跑道，错过融资窗口。
- 三表勾稽必须三张表都跑：只查资产负债恒等式会漏掉现金流失衡——后者往往
  才是真 bug（见算例 cash_flow.ok=false）。

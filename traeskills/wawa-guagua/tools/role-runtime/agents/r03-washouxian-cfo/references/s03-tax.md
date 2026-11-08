# S03 税务边界
> 蒸馏自: 补充技能/01-当前能力域/JoelLewis__finance_skills/equity-compensation/SKILL.md
>


## 方法论（来源 equity-compensation / retirement-decumulation / tax-efficiency）

> 所有法定数字在 `experience/thresholds.json`（逐年核实，不改代码）。

### ISO（激励股票期权）

- **合格处置**：授予日 → 出售日 > 2 年 **且** 行权日 → 出售日 > 1 年；
  否则不合格处置，价差按普通收入计税
- 首次可行权 ISO（按授予日 FMV）每年限 $100,000，超出按 NSO
- 离职后 3 个月内须行权，否则 ISO 身份失效
- **AMT 交叉计算**：TMT = 26% × 断点内 + 28% × 超出（断点 220k，
  免税额 137k）；AMT = max(0, TMT − 常规税)。AMT 是预付非永久成本，
  可结转抵免；行权前先算交叉点

### RMD（退休账户最低分配）

- 年龄门槛：73 岁（2033 起 75 岁）；首年可延至次年 4 月 1 日
- RMD = 上年 12/31 余额 ÷ Uniform Lifetime Table 除数
  （73→26.5 / 75→24.6 / 80→20.2 / 85→16.0 / 90→12.2）
- 漏缴消费税 25%，更正窗口内 10%
- Roth IRA 免 RMD

### 预估税安全港

免罚目标 = min(90% × 当年税, 上年税 × 100%)；上年 AGI > 150k 用 110%。
RSU 归属按补充预扣 22%（超 $1M 部分 37%），边际税率更高时形成预扣缺口，
须季度预估缴款补齐。

### 其他边界（tax-efficiency 摘要）

- 洗售规则：回购窗口 61 天（售前 30 + 售后 31）
- 资本亏损抵扣普通收入上限 $3,000/年，余额结转
- NIIT 3.8%（MAGI > $250k，已婚合并）
- 83(b) 选举：授予后 30 天内

## 已验证算例（run_tests.py T07，已对拍）

- **ISO 交叉计算**：`examples/tax_iso.json` → 行权 1 合格、行权 2 不合格；
  `amt_adjustment_total=51000.0`（AMT 调整项合计）。
  交叉校验：`tmt≈42640.0`、`amt_due≈0.0`（常规税 ≥ AMT 临界值，
  无 AMT 应缴，但调整项仍影响抵免基数）。
- **RMD**：`examples/tax_rmd.json` 三个账户 →
  账户 1 `rmd=32075.47`、账户 2 `rmd=10000.0` 且漏缴
  `excise_penalty=2500.0`（10000×25%）、账户 3（Roth）`rmd=0.0` 豁免；
  `total_required=42075.47`。
- **安全港**：`examples/tax_safeharbor.json` →
  `safe_harbor_target=40000.0`、RSU 预扣缺口
  `rsu_shortfall_total=52000.0` → `ok=false`（须季度补缴）。

## 实战踩坑

- ISO 的「合格处置」是**双时钟**（授予→售 >2 年 且 行权→售 >1 年），
  只查一个条件会把不合格处置误判为合格，价差性质算错。
- AMT 断点/免税额逐年可能变，**一律读 thresholds.json 真源**，不手抄
  （220k/137k 是写作时口径）。
- RSU 预扣 22% 是补充预扣率：员工边际税率 35% 时必然缺口，
  「预扣了」≠「缴够了」，安全港算的才是真正免罚目标。

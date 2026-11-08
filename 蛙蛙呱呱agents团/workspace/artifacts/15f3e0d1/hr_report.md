# 蛙人事 · payroll/calc
> 帮我核算这个月工资，净额对不对 

**结论**：next=人事工件通过全部门禁，可进入授权与交接

## 关键指标

| 指标 | 值 | 说明 |
|---|---|---|
| 门禁 | **PASS** | 4/4 项 |
| next | **人事工件通过全部门禁，可进入授权与交接** | 输出字段 |
| payroll_input_count | **1** | 输出字段 |
| gross_pay | **20,000.00** | 输出字段 |

## 1. payroll_input_count
> payroll_input_count 的判定与证据是什么？

- **payroll_input_count：**1

## 2. gross_pay
> gross_pay 的判定与证据是什么？

- **gross_pay：**20,000.00

## 3. net_pay
> net_pay 的判定与证据是什么？

- **net_pay：**18,000.00

## 4. total_deduction
> total_deduction 的判定与证据是什么？

- **total_deduction：**2,000.00

## 5. employer_contribution
> employer_contribution 的判定与证据是什么？

- **employer_contribution：**0

## 6. narrative
> narrative 的判定与证据是什么？

- **narrative：**核算：毛额 20000 扣除 2000 净额 18000（待 R03/外部复核，非发放）

## 口径与边界

- **来源：**技能 payroll/calc 的确定性输出（无 LLM）。
- **边界：**结论仅基于本次输入的产出；未纳入的输入不参与判断。

# 05 · 薪酬准备口径（payroll）—— L4 制度性幻觉防护主战场
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/human-resources/comp-analysis/SKILL.md
>


> 技能：`payroll` ｜ 动作：`input`（薪酬输入表）、`calc`（核算记录）
> 来源：frappe__hrms（SalaryStructure.payroll_frequency / SalaryComponent.type / SalarySlip 勾稽）

## 第一层：方法论

薪酬是**「准备」，不是「发放」**。这是本角色风险最高、也最需要"反幻觉"设计的技能。

三条方法论：

1. **净额恒等是硬门禁**。`net_pay = ΣEarning − ΣDeduction`，容差 0.01（分位误差）。
   数字对不上，后面所有报表都是错的。恒等先于一切业务讨论。
2. **制度性字段必须可溯源（L4 制度性幻觉防护）**。Lance/免税额度/税率/社保基数/
   起征点/速算扣除等"看起来专业"的字段，必须能在输入表找到 `source`。
   找不到源头 = **制度性幻觉** → BLOCKER。这比数字错更危险：数字错是算错，字段凭空
   是**编造制度**——LLM 幻觉在薪酬领域最典型的形态。
3. **考勤勾稽**。`payment_days ≤ total_working_days`。计薪天数不得超过计薪基数。

**本角色绝对不做的事**：不擅自发薪、不代发工资、不打款、不做税务/社保复核结论。
核算草稿必须移交 R03 + 外部专业人士复核。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| input.payroll_frequency | ∈ `{Monthly, Fortnightly, Bimonthly, Weekly, Daily}` | hrms SalaryStructure.payroll_frequency |
| input.employee | 非空 | 关联人员 |
| input.components | `≥ 1` | 组成项非空 |
| input.component.type | ∈ `{Earning, Deduction, Employer Contribution}` | hrms SalaryComponent.type |
| input.component.source | 每项必须有 `source` | 防凭空组成项 |
| calc.gross_pay | `== ΣEarning`（容差 0.01） | hrms SalarySlip.gross_pay |
| calc.net_pay | `== gross_pay − ΣDeduction`（容差 0.01） | hrms SalarySlip.net_pay |
| calc.payment_days | `≤ total_working_days`（若提供） | 考勤勾稽 |
| calc.system_fields | 每个制度性字段的 `source` 非空 | **L4 幻觉防护** |

**净额恒等式速查**：
```
gross_pay = Σ(Earning)
net_pay   = gross_pay − Σ(Deduction)
```
注意：`Employer Contribution`（雇主承担）**不进入净额扣除**——它是雇主成本，不是
员工到手金额的扣项。把它算进 net_pay 是常见错误。

## 第三层：已验证的算例

**算例 A（干净核算）**：`examples/payroll_calc.json`
```
gross=20000 / net=18000 / [Earning 20000, Deduction 2000]
payment_days=20 ≤ 22 / system_fields[社保基数(source), 起征点(source)]
```
毛额 20000 == ΣEarning；净额 18000 == 20000 − 2000；制度字段均有来源 → `ok=true`。

**算例 B（脏核算）**：`examples/payroll_calc_dirty.json`
```
gross=20000 / net=99999 / [Earning 20000]
payment_days=25 > 22 / system_fields[免税额度(无 source)]
```
BLOCKER ×3：净额不恒等（实算 20000 ≠ 声明 99999）、计薪天数 25 > 22、
制度字段「免税额度」凭空（L4 幻觉）。

**算例 C（干净输入）**：`examples/payroll_input.json`
```
EMP-0001 / Monthly / [基本工资(Earning,20000,source), 社保个人(Deduction,2000,source),
公积金雇主(Employer Contribution,1000,source)]
```
频率合法、组成项类型白名单、均有 source → `ok=true`。

**算例 D（脏输入）**：`examples/payroll_input_dirty.json`
```
EMP-0001 / Yearly / [基本工资(type=Bonus，无 source)]
```
BLOCKER ×3：频率 `Yearly` 越界、类型 `Bonus` 越界、组成项无 source。

## 第四层：实战踩坑

1. **L4 制度性幻觉是头号陷阱**。LLM 很容易"顺手"写上"按 3% 税率""免税额度 5000"，
   这些数字**看起来完全合理**，但如果没有输入表来源，就是编造制度。
   口径：任何制度性字段必须有 `source`，无来源一律 BLOCKER。**宁可拦错，不可放过**。

2. **Employer Contribution 不进净额**。公金金雇主承担是雇主成本，员工净额不扣它。
   把它算进 deduction 会让 net_pay 偏小。

3. **元/分混淆**。金额单位必须统一。20000.00 元 vs 20000 分（=200 元）差 100 倍。
   本仓库统一用**元**（两位小数）。

4. **payment_days 的基数**。`total_working_days` 是该薪酬周期的工作日数，
   `payment_days` 是实际计薪天数。请假会减少 payment_days（勾稽 s03）。

5. **组成项的 source 口径**。`source` 可以是 `salary_structure`（薪酬结构）、
   `tax_table`（税表）、`expense_claim`（报销）等。核心是**可追溯**，不是具体取值。

6. **不要在结论里写"我已给员工发薪"**。这是越权（`unauthorized_hr_action`）。
   正确写法："产出核算草稿 payroll_calc.json（毛额 20000、扣除 2000、净额 18000），
   标注需 R03 + 外部专业人士复核，由人工授权后发放。"

7. **不要在结论里写"个税按 X% 算，社保合规"**。这是越界到 R03（`scope_overlap`）。
   R16 只做数量勾稽，不做税务/社保结论。

8. **tolerance 的作用**。浮点计算会有分位误差（如 0.1+0.2=0.30000000000000004）。
   容差 0.01 让"分位级"误差不误报，但绝不放过"元级"差异。

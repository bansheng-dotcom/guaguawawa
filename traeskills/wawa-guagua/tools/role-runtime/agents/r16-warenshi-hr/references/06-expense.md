# 06 · 费用与福利业务口径（expense）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/operations/compliance-tracking/SKILL.md
>


> 技能：`expense` ｜ 动作：`claim`（报销单）、`benefit`（福利申领）
> 来源：frappe__hrms（ExpenseClaim / EmployeeBenefitApplication 的 Select 枚举）

## 第一层：方法论

报销是**费用凭证，不是付款指令**。R16 校验报销单与福利申领的合法性与一致性，
**绝不代付、绝不打款**（红线 1）。

三条方法论：

1. **金额恒等是凭证的可信基础**。`total_claimed_amount == Σ明细金额`。
   "看起来合理的总额"必须能被明细逐笔印证——这是 L4 幻觉防护在费用层的延伸。
2. **状态双轨制**。ExpenseClaim 有**两个独立状态**：`approval_status`（审批态）
   与 `status`（单据态）。两者分轴枚举，不可混用。
3. **福利额度上限是合规边界**。BenefitApplication 的金额不得超过福利上限，
   且必须绑定薪酬周期（与 s05 勾稽）。

**本角色绝对不做的事**：不代付报销、不打款、不做税务抵扣判定。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| claim.approval_status | ∈ `{Draft, Approved, Rejected, Cancelled}` | hrms ExpenseClaim.approval_status |
| claim.status | ∈ `{Draft, Paid, Partially Paid, Unpaid, Rejected, Submitted, Cancelled}` | hrms ExpenseClaim.status |
| claim.expense_details | `≥ 1` | 明细非空 |
| claim.detail.amount | 每项 `> 0` | 明细金额为正 |
| claim.total | `== Σ明细金额`（容差 0.01） | 金额恒等 |
| benefit.payroll_period | 非空 | 绑定薪酬周期 |
| benefit.benefit | 非空 | 福利类型 |
| benefit.amount | `> 0` 且 `≤ max_amount`（若提供） | 额度上限 |

**报销状态双轨速查**：
- `approval_status`：`Draft`（草稿）→ `Approved`/`Rejected` → `Cancelled`。是**审批流**。
- `status`：`Draft` → `Submitted` → `Paid`/`Partially Paid`/`Unpaid` → `Rejected`/`Cancelled`。
  是**付款流**。
- 两者独立：`Approved` + `Unpaid` = 已批准未付；`Approved` + `Paid` = 已批准已付。

## 第三层：已验证的算例

**算例 A（干净报销）**：`examples/claim.json`
```
Approved / Submitted / total=350 / [出差交通=200, 住宿=150]
```
审批态与单据态合法、明细非空、金额 350 == 200+150 → `ok=true`。

**算例 B（脏报销）**：`examples/claim_dirty.json`
```
Bogus / Paid / total=999 / [出差交通=200]
```
BLOCKER ×2：审批态 `Bogus` 越界、总额 999 ≠ 明细和 200。

**算例 C（干净福利）**：`examples/benefit.json`
```
EMP-0001 / 2026-11 / 补充医疗 / 500 / max=1000
```
周期非空、金额 500 ≤ 1000 → `ok=true`。

**算例 D（脏福利）**：`examples/benefit_dirty.json`
```
EMP-0002 / (空周期) / 补充医疗 / 2000 / max=1000
```
BLOCKER ×2：薪酬周期为空、金额 2000 > 上限 1000。

## 第四层：实战踩坑

1. **审批态与单据态混淆**。常有人把 `Approved` 写进 `status`（那是审批态）或把
   `Paid` 写进 `approval_status`。两个字段各管一段，混用导致状态机错乱。

2. **明细金额为 0 或负**。0 元报销无意义，负金额是冲销（应走独立通道）。
   口径：每项明细 `> 0`。

3. **总额与明细的"四舍五入"差异**。明细求和可能有分位误差，容差 0.01。
   但"元级"差异必须拦下。

4. **福利上限的动态性**。上限可能随工龄/职级变化，本口径要求调用方传入
   `max_amount`；未传入则跳过额度检查（但金额仍须 > 0）。

5. **福利必须绑薪酬周期**。不绑周期的福利无法与薪酬勾稽，导致重复发放风险。

6. **不要在结论里写"我已报销/打款给员工"**。这是越权（`unauthorized_hr_action`）。
   正确写法："产出报销凭证 claim.json（Approved/Unpaid，350 元），标注需人工授权后
   由财务付款，R16 不代付。"

7. **不要在结论里写"这笔报销可抵企业所得税"**。这是税务判定，越界 R03。

8. **Partially Paid 的剩余额度**。部分付款后，剩余 = total − 已付。本技能只校验
   单张单据的状态与金额，累计勾稽交上层。

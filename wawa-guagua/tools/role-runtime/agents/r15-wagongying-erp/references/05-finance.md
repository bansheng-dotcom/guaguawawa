# 05 · ERP 财务业务接口口径（finance）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/small-business/ap-processor/SKILL.md
>


> 技能：`finance` ｜ 动作：`invoice` / `payment`
> 来源：frappe__erpnext（Sales Invoice / Purchase Invoice / Payment Entry）

## 第一层：方法论

本技能只做**业务凭证的确定性门禁**，不做财务结论。立场是：

> R15 登记「已发生的应收应付」，不代替 R03 做财报、税务与资金决策。

财务业务接口有两类事实源：
- **发票（Invoice）**：销售发票 = 应收，采购发票 = 应付。发票必须能复算
  （total == Σ 数量×单价），它是「收入/成本确认」的业务凭据。
- **付款单（Payment Entry）**：登记「钱已付出/收到」，是资金流动的凭据。

本技能坚持两条原则：
1. **凭证必须可复算**——发票总额 = Σ 行项目金额，容差 0.01（对账口径）。
2. **不代付款**——付款单必须显式声明授权（handoff/authorized/approved_by），
   这是 R15 红线的可执行化：涉及资金流动的动作一律产出请求工件 + 授权声明。

**关键区分**：`Submitted`（已提交入账）与 `Paid`（已付款）是两回事。发票 Submitted
只表示已确认应收应付，Paid 才表示资金已结清。把 Submitted 当 Paid 会让「未收款」
被误判为「已收款」。`Overdue`（逾期）是 Unpaid 的超期状态，催收依据。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| invoice_kind | ∈ `{sales, purchase}` | 业务分类 |
| invoice_status | 九态 `{Draft, Return, Credit Note Issued, Submitted, Paid, Partly Paid, Unpaid, Overdue, Cancelled}` | erpnext Sales/Purchase Invoice |
| invoice_required | `party` + `total` + `line_items` | erpnext Invoice |
| invoice_line_required | `item_code` + `qty` + `rate` | erpnext Invoice Item |
| 发票恒等式 | total == Σ(qty×rate)（容差 0.01） | 对账口径 |
| payment_status | ∈ `{Draft, Submitted, Cancelled}` | erpnext Payment Entry |
| payment_required | `party` + `paid_amount` + `paid_to` | erpnext Payment Entry |
| 金额下限 | paid_amount ≥ 0 | 货币公理 |
| 授权 | 必须声明 handoff/authorized/approved_by | R15 红线 |

**关键区分**：`party` 在销售发票是客户、在采购发票是供应商；门禁按 kind 区分语义但不
强制绑定具体主数据（主数据校验归 `masterdata`）。`paid_to`（收款/付款账户）是必需字段，
缺了就无法追溯资金流向。

## 第三层：已验证的算例

**算例 A（干净·销售发票）**：`examples/invoice.json`
```
INV-001 / sales / 客户A / Unpaid
line_items: FG-001 ×10 @88 → Σ=880 == total → PASS
```

**算例 B（脏·恒等式不闭合）**：`examples/invoice_dirty.json`
```
line_items Σ=880，但 total 声明 999 → 恒等式不闭合 → FAIL
```
发票总额手抄错误是应收应付对不上的高发原因，恒等式门禁把它变成确定性拦截。

**算例 C（干净·付款单带授权）**：`examples/payment.json`
```
PAY-001 / 华东原料供应商 / paid_amount=550 / paid_to=银行-基本户 / Submitted / approved_by=CEO
→ 必填齐备 + 金额非负 + 已声明授权 → PASS
```

**算例 D（脏·付款无授权）**：`examples/payment_dirty.json`
```
同上有付款单但缺 approved_by/handoff/authorized → 未授权 → FAIL
```
这是红线门禁：R15 不代付款，缺授权凭证一律拦。

## 第四层：实战踩坑

- **Submitted ≠ Paid**：把已提交入账的发票当成已收款，会让现金流预测整体乐观。
  `Partly Paid`（部分收款）与 `Paid`（全额收款）也必须区分。
- **红冲/退货走 Return/Credit Note**：发票退货用 `Return` 或 `Credit Note Issued` 状态，
  不要用负数 total 表示，否则恒等式与账务口径都会乱。
- **付款授权是硬门禁**：`approved_by`/`handoff` 缺失即 FAIL，不能因为「金额小」就放行——
  红线不因金额大小而变。
- **币种与精度**：金额容差 0.01 是「一元以下忽略」的对账口径，跨币种场景需要财务
  （R03）另行给汇率口径，本技能不擅自换算。

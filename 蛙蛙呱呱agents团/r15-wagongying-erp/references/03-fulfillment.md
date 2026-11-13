# 03 · 销售与履约记录口径（fulfillment）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/small-business/ticket-deflector/SKILL.md
>


> 技能：`fulfillment` ｜ 动作：`sales_order` / `delivery`
> 来源：frappe__erpnext（Sales Order / Delivery Note）

## 第一层：方法论

销售订单是**「已确认承诺」，发货单是「已实际交付」**，二者必须严格区分。订单的
`delivery_status`（发货轴）与 `billing_status`（开票轴）是**两条独立轴**：

```
Sales Order.status  ×  delivery_status（交付）  ×  billing_status（开票/收款）
```

绝大多数销售类纠纷源于把三者压成一个「状态」。典型症状：「订单已完成，但没开发票」——
Completed 是主状态，Not Billed 是开票轴，两轴各自合法，组合起来才是问题。
因此本技能的第一原则：**先分轴校验，再校验跨轴一致性**。

`Completed` 是一个**终态承诺**：它必须同时满足「已全部交付」且「已全部开票」，
否则就是把「部分完成」谎报为「全部完成」。

履约的另一条硬边界是**超发**：发货数量 > 订单数量 = 白送 / 账实不符，默认容差 0。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| so_status | 九态 `{Draft, On Hold, To Pay, To Deliver and Bill, To Bill, To Deliver, Completed, Cancelled, Closed}` | erpnext Sales Order |
| delivery_status | ∈ `{Not Delivered, Fully Delivered, Partly Delivered, Closed}` | erpnext Sales Order |
| billing_status | ∈ `{Not Billed, Fully Billed, Partly Billed, Closed}` | erpnext Sales Order |
| so 必填 | `customer` + `items` | erpnext Sales Order |
| so_item 必填 | `item_code` + `qty` + `rate` | erpnext Sales Order Item |
| 金额恒等式 | grand_total == Σ(qty×rate)（容差 0.01） | 交易语义公理 |
| 跨轴一致性 | status=Completed → delivery=Fully Delivered 且 billing=Fully Billed | 语义公理 |
| 发货状态 | ∈ `{Draft, To Bill, Partially Billed, Completed, Return}` | erpnext Delivery Note |
| delivery 必填 | `customer` + `items` | erpnext Delivery Note |
| 超发 | qty ≤ against_qty × (1 + tolerance)，默认 tolerance=0 | thresholds.fulfillment |

**关键区分**：`To Deliver`（待发货）与 `To Bill`（待开票）是两条不同的待办。
`To Deliver and Bill` 表示两者都待办。`Closed` 是**人工终止**（不再继续），
不同于 `Completed`（已全部完成）——把 Closed 当 Completed 会让「未完成」的订单
被当成历史已结案。

## 第三层：已验证的算例

**算例 A（干净）**：`examples/sales_order.json`
```
SO-2026-001 / 客户A / To Deliver / Not Delivered / Not Billed
items: FG-001 ×10 @88 → Σ=880 == grand_total → 分轴合法、非 Completed 无需跨轴校验 → PASS
```

**算例 B（脏·恒等式不闭合）**：`examples/sales_order_dirty.json`
```
items Σ = 880，但 grand_total 声明 999 → 恒等式不闭合 → FAIL
```

**算例 C（脏·超发）**：`examples/delivery_dirty.json`
```
qty=15 / against_qty=10，tolerance=0 → 超发 5 → FAIL
```
超发是「白送」或「账实不符」，必须走让步交付或补录订单，不能直接放行。

**算例 D（跨轴矛盾·应拦）**：
```
status=Completed 但 delivery_status=Partly Delivered → 谎报全交付 → FAIL
```
即使枚举各自合法，跨轴组合也必须自洽。

## 第四层：实战踩坑

- **三轴压一轴**：把 delivery_status/billing_status 合并进 status 是 ERP 二次开发的高发错误，
  门禁坚持三轴分列 + 跨轴一致性检查。
- **Closed ≠ Completed**：Closed 是人工终止（可能只交付了一半就协商结束），Completed 是
  全部完成；用 Closed 替代 Completed 会让未结订单静默消失。
- **against_qty 必填**：超发门禁依赖「对照订单数量」，若发货单不记录 against_qty，
  门禁无法判定，必须强制该字段。
- **退货走 Return 而非负数**：Delivery Note 的 Return 状态表示退货，不要用负数 qty 表示，
  否则恒等式与账实都会被污染。

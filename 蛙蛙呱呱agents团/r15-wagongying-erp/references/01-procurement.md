# 01 · 采购与供应商口径（procurement）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/operations/vendor-review/SKILL.md
>


> 技能：`procurement` ｜ 动作：`supplier` / `rfq` / `quotation` / `purchase_order` / `receipt`
> 来源：frappe__erpnext（Supplier / Request for Quotation / Supplier Quotation / Purchase Order / Purchase Receipt）

## 第一层：方法论

采购链是**「先比价 → 再下单 → 后收货」的三段门禁**，不是一张采购单从头到尾。把三段压成一段，
是采购类事故的最大来源：要么「没比价直接下单」（供应商坐地起价），要么「下了单不核收货」
（账实脱节）。

因此本技能坚持三条原则：
1. **比价不是走过场**——RFQ 至少询两家（阈值 `rfq_min_suppliers=2`），否则报价单失去意义。
2. **金额必须可复算**——PO/报价单的总额必须等于 Σ(数量×单价)，不能「声明什么信什么」。
3. **收货以订单为上限**——收 > 订 是账实不符的源头，默认容差 0，让步接收需显式授权。

供应商主数据是采购链的事实源：供应商类型（Company/Individual/Partnership）决定税务与合同
口径，冻结供应商（status=Frozen）不得下单。账期过长（> 180 天）是供应商风险的信号，
必须显式复核而非默认通过。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| supplier_type | ∈ `{Company, Individual, Partnership}` | erpnext Supplier |
| supplier_required | `supplier_name` 非空 | thresholds.procurement |
| payment_terms_days | ≤ 180 天 | thresholds.procurement |
| rfq_status | ∈ `{Draft, Submitted, Cancelled}` | erpnext RFQ |
| rfq 家数 | ≥ 2 家 | thresholds.procurement |
| sq_status | ∈ `{Draft, Submitted, Partially Ordered, Ordered, Stopped, Cancelled, Expired}` | erpnext Supplier Quotation |
| po_status | 十态 `{Draft, On Hold, To Pay, To Receive and Bill, To Bill, To Receive, Completed, Cancelled, Closed, Delivered}` | erpnext Purchase Order |
| po 必填 | `supplier` + `transaction_date` + `schedule_date` + `items` | erpnext Purchase Order |
| po_item 必填 | `item_code` + `qty` + `rate` | erpnext Purchase Order Item |
| 金额恒等式 | grand_total == Σ(qty×rate)（容差 0.01） | 交易语义公理 |
| 时序 | schedule_date ≥ transaction_date | 计划可执行性 |
| receipt_status | 六态 `{Draft, Partly Billed, To Bill, Completed, Return, Return Issued}` | erpnext Purchase Receipt |
| 超收 | received_qty ≤ ordered_qty × (1 + tolerance)，默认 tolerance=0 | thresholds.procurement |

**关键区分**：`To Receive`（待收货）与 `To Bill`（待开票）是 PO 生命周期两个阶段，
`To Receive and Bill` 是二者重叠。把「待收货」当「已完成」是采购链最常见的静默错误。
收货单 `To Bill` 表示已收未开票，超收部分在对账前不得进入应付。

## 第三层：已验证的算例

**算例 A（干净）**：`examples/purchase_order.json`
```
PO-2026-001 / 华东原料供应商 / 2026-11-05 下单 / 2026-12-05 交货 / To Receive
items: RM-001 ×100 @5.5 + RM-002 ×50 @3.0 → Σ = 700.0 == grand_total  → PASS
```

**算例 B（脏·时序倒退）**：`examples/purchase_order_dirty.json`
```
schedule_date=2026-11-01 < transaction_date=2026-11-05 → 交货早于下单 → FAIL
```
计划不可执行：交货日期倒退意味着「先收货后下单」，账实必然错位。

**算例 C（脏·超收）**：`examples/receipt_dirty.json`
```
received_qty=120 / ordered_qty=100，tolerance=0 → 超收 20 → FAIL
```
超收必须走让步接收（声明 handoff），不能直接入库。

**算例 D（脏·恒等式不闭合）**：`examples/quotation_dirty.json`
```
items 总额 = 100×5.5 = 550，但 total 声明 999 → 恒等式不闭合 → FAIL
```

## 第四层：实战踩坑

- **动作错配**：意图路由里「报价」必须排在「询价」之前（报价是 quotation，询价是 rfq），
  否则「供应商报价」会被当成 rfq 校验，门禁选错（R14 踩坑同理：退款状态 vs 退款）。
- **超收 ≠ 白送**：即使供应商免费多送，账上「收 > 订」也会破坏 MRP 与应付对账，必须拦。
- **金额用手抄**：采购员手输总额是抄错高发区，恒等式门禁把它变成确定性拦截，而非人工核对。
- **冻结供应商**：status=Frozen 是「禁止下单」开关，但很多系统里它只是备注字段，
  门禁必须显式读它，否则冻结形同虚设。

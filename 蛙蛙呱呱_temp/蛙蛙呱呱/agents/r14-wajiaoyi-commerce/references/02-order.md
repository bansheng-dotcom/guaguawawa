# 02 · 购物车与订单三态口径（order）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/sales/deal-review/SKILL.md
>


> 技能：`order` ｜ 动作：`cart`（购物车校验）、`order`（订单三态校验）
> 来源：medusajs__medusa（OrderStatus、PaymentStatus、FulfillmentStatus）

## 第一层：方法论

订单是**三个独立状态轴的组合**，不是单一状态：

```
OrderStatus（订单生命周期）  ×  PaymentStatus（资金）  ×  FulfillmentStatus（履约）
```

绝大多数订单类事故都源于把三轴压成一个轴。典型症状："订单已完成，但钱没收"——
"已完成"是 OrderStatus，"钱没收"是 PaymentStatus，两个轴各自合法，组合起来才是问题。
因此本技能的第一个原则是：**永远分轴校验，再校验跨轴一致性**。

第二个原则是**恒等式优先**。购物车小计必须等于行项目金额之和；订单总额必须可与行项目对上。
恒等式不成立时，一切后续讨论（折扣、税费、运费）都失去基准。

第三个原则是**跨轴矛盾必须显式报错**。最危险的不是明显非法状态，而是"看起来都对"的组合：
`status=completed` + `payment_status=refunded` + `fulfillment_status=delivered`：
货已交付、钱已退还、订单却标为完成——这在语义上要求"已退款完成的订单仍算完成"，
属于业务规则变更级别的事情，校验层必须拦下让人确认。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| cart_required | `line_items` 必须存在且非空 | thresholds.cart |
| line_item_required | `title`、`unit_price`、`quantity` | thresholds.cart |
| max_line_items | ≤ 50 | thresholds.cart.max_line_items |
| subtotal 恒等式 | `subtotal == Σ(unit_price × quantity)`（容差 0.01） | 交易语义公理 |
| 行项目单价 | `unit_price > 0` | 交易语义公理 |
| 行项目数量 | `quantity > 0` | 交易语义公理 |
| 订单总额 | `total > 0` | 交易语义公理 |
| order_status | ∈ `{pending, completed, draft, archived, canceled, requires_action}` | medusa OrderStatus |
| payment_status | ∈ `{not_paid, awaiting, authorized, partially_authorized, captured, partially_captured, partially_refunded, refunded, canceled, requires_action}` | medusa PaymentStatus |
| fulfillment_status | ∈ `{not_fulfilled, partially_fulfilled, fulfilled, partially_shipped, shipped, partially_delivered, delivered, canceled}` | medusa FulfillmentStatus |
| paid_statuses | `{captured, partially_refunded, refunded}` | thresholds.order.paid_statuses |
| cancelable_statuses | `{pending, draft, requires_action}` | thresholds.order.cancelable_statuses |

**跨轴规则（本技能的核心价值，实现见 `s02_order._validate_order`）**：
- `payment_status == refunded` 且 `status == completed` → FAIL
  （已完成却全额退款，自相矛盾；判据 `order.consistency`）
- `total ≤ 0` → FAIL（判据 `order.total`，`> 0` 严格为正）
- 三个状态轴**各自独立**校验白名单（`order.status` / `order.payment_status` /
  `order.fulfillment_status`）——单轴全过不代表组合合法

判据表（代码为准）：

| dim | 判据 |
|---|---|
| `order.id` | 订单号非空（事件表与回调的对账锚点） |
| `order.status` | ∈ order_status 白名单 |
| `order.payment_status` | ∈ payment_status 白名单 |
| `order.fulfillment_status` | ∈ fulfillment_status 白名单 |
| `order.consistency` | 非（`refunded` + `completed`） |
| `order.total` | `total > 0` |

## 第三层：已验证的算例

**算例 A（干净）**：`examples/cart.json`
```
CRM 3 席位订阅 × 3 @299.0 = 897.0
数据看板加装   × 1 @149.0 = 149.0
Σ = 1046.0 == subtotal 1046.0   → PASS
```
`line_item_count=2 ≤ 50`，恒等式成立 → `ok=true`。

**算例 B（脏数据）**：`examples/cart_dirty.json`
```
CRM 3 席位订阅 × 0 @-299.0
Σ = 0.0 ≠ subtotal 9999.0
```
三条失败判据：`单价均为正（异常 ['CRM 3 席位订阅']）`、`数量均为正（异常 ['CRM 3 席位订阅']）`、
`小计口径恒等：声明 9999.0 = 实算 0.0`。
注意：**恒等式错误与行项目错误同时报出**，不要只报第一条就退出——一次性把所有问题列全，
使用者才能一次修完。

**算例 C（干净订单）**：`examples/order.json`
```
ord_20261105_001 / completed / captured / delivered / 1046.0  → PASS
```
三轴各自合法，跨轴组合：completed + captured + delivered 是**标准完成态**，无矛盾 → `ok=true`。

**算例 D（脏订单）**：`examples/order_dirty.json`
```
"" / completed / refunded / delivered / 0
```
三条失败判据：`订单号非空`、`已全额退款却状态 completed，自相矛盾`（跨轴矛盾专用判据）、
`订单总额=0.0 为正`。注意三个状态**各自都在白名单内**——单轴校验全过，
问题只在跨轴组合与金额上，这正是"分轴校验 + 跨轴一致性"两层设计的价值。

## 第四层：实战踩坑

1. **quantity=0 的行项目**：业务上"加进购物车又改成 0"很常见，但 0 数量行项目进入订单会产生
   "幽灵行"——金额为 0 却占一个行位。口径：`quantity ≤ 0` 一律 BLOCKER，结算前清理。

2. **partially_* 家族被当成"错误"**：`partially_captured`、`partially_refunded` 等是**合法业务态**，
   不是数据错误。新手常把它们当异常拦下，导致合法的部分履约流程无法登记。校验层只做枚举合法性，
   不做"是否等于标准值"的判断。

3. **subtotal 与 total 的混淆**：全量数据里 total 可能含运费/税，subtotal 不含。
   本技能的恒等式针对 **subtotal vs 行项目**；若输入给的是 total，必须先确认是否含附加项，
   否则会把正确的数据判成恒等式不成立。

4. **浮点求和**：897.0 + 149.0 在浮点下可能得 1045.9999999。恒等式比对必须允许
   极小容差（本仓库统一用 `abs(a-b) < 1e-6`）。禁止用 `==` 直接比浮点。

5. **订单 ID 为空**：看似无关紧要，实际上 id 是事件表与回调对账的唯一锚点。
   `id` 为空 → BLOCKER，理由不是"格式要求"而是"对账锚点缺失"。

6. **不要替 R15 判库存**：订单里出现 `fulfillment_status=not_fulfilled` 不代表"缺货"。
   缺货判断需要库存数据，属 R15。本技能只看状态枚举与跨轴一致性。

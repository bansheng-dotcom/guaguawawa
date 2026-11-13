# 07 · 交易状态机与迁移口径（workflow）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/operations/process-optimization/SKILL.md
>


> 技能：`workflow` ｜ 动作：`state`（状态快照校验）、`transition`（状态迁移校验）
> 来源：综合 medusa（Order/Payment）与 documenso（Document）、easyappointments（Appointment）

## 第一层：方法论

交易链上有四个实体各自跑着状态机：**订单、支付、签署、预约**。
它们之间是**编排关系**而非包含关系——一个订单可以聚合多次支付、
一份合同可以对应多个订单。因此状态机校验必须**按实体分别做**，再检查编排一致性。

三条方法论：

1. **状态必须来自白名单**。每个实体的合法状态集合是封闭的。自造状态
   （如 `order: "已发货"`）意味着"系统不知道这笔交易现在是什么"，一律 BLOCKER。

2. **迁移只走声明的边**。状态机是一张有向图，只有声明的边允许走。
   `refunded → captured` 这类"回滚"在资金语义上不可能（钱退出去不会自动回来），
   必须拦截。

3. **终态不可逆**。`completed`、`refunded`、`canceled`（订单侧）、`COMPLETED`（签署侧）
   是终态，不存在"从终态再走一步"的合法迁移。若业务需要复开，那是**新实体**
   （新订单/新合同），不是原实体的迁移。

**待处理动作（pending_action）的语义**：`pending_action` 在**非终态**实体上是正常的
（流程尚未走完）；但一旦实体处于**终态**（在迁移表中无出边，如 `completed`、`refunded`、
`COMPLETED`、`no_show`），还挂 `pending_action` 就是自相矛盾的 BLOCKER——
终态意味着没有下一步，有下一步说明状态标错了。

## 第二层：可执行口径

| 实体 | 状态白名单 |
|---|---|
| order | `pending, completed, draft, archived, canceled, requires_action` |
| payment | `not_paid, awaiting, authorized, partially_authorized, captured, partially_captured, partially_refunded, refunded, canceled, requires_action` |
| signature | `DRAFT, PENDING, COMPLETED` |
| appointment | `booked, pending, approved, rejected, canceled, no_show` |

**声明式迁移表（`skills/s07_workflow._VALID_TRANSITIONS`，代码为准）**：

| 实体 | 合法边（`from → [to...]`） |
|---|---|
| order | `pending → [completed, canceled, requires_action]`；`draft → [pending, archived]`；`requires_action → [completed, canceled]`；`completed / canceled / archived → []`（终态） |
| payment | `requires_payment_method → [requires_confirmation, canceled]`；`requires_confirmation → [requires_action, processing, canceled]`；`requires_action → [processing, succeeded, canceled]`；`processing → [succeeded, canceled]`；`requires_capture → [succeeded, canceled]`；`succeeded → [partially_refunded]`；`partially_refunded → [refunded]`；`refunded / canceled → []`（终态） |
| signature | `DRAFT → [PENDING]`；`PENDING → [COMPLETED]`；`COMPLETED → []`（终态） |
| appointment | `pending → [booked, rejected, canceled]`；`booked → [canceled, no_show]`；`approved → [booked, canceled]`；`rejected / canceled / no_show → []`（终态） |

**明确禁止的边（回滚类，均不在上表）**：
- `refunded → captured`（资金不可能自动回来）
- `canceled → completed`（取消不是完成）
- `COMPLETED → PENDING`（已签合同不能退回待签）
- `no_show → booked`（历史事实不可改写）
- `processing → requires_payment_method`（处理中不能退回待支付）

## 第三层：已验证的算例

**算例 A（干净快照）**：`examples/state.json`
```
order: completed      payment: succeeded → 归一化 captured 族
signature: COMPLETED  appointment: booked
```
四个实体的状态各自在白名单内、无 pending_action → `ok=true`，`entity_count=4`。

**算例 B（脏快照）**：`examples/state_dirty.json`
```
order: completed, pending_action="ship"       → 终态却有后续动作
payment: refunded, pending_action="recapture" → 终态却有后续动作
```
判据：`终态实体不得有后续动作（异常 ['order:completed', 'payment:refunded']）` → FAIL。
`payment:refunded + recapture` 是经典错误：`refunded` 是付款侧终态，`recapture`（重新捕获）
意味着"钱退出去再收回来"——只能通过**新建支付意图**实现，不能作为原支付意图的迁移。
注意 `order:completed + ship` 同样被拦（`completed` 在迁移表中是终态，无出边）——
本仓库口径下，"已完成"就是流程走完，若仍需发货说明状态标早了。

**算例 C（干净迁移）**：`examples/transition.json`
```
kind=payment, from=processing, to=succeeded
```
`processing → succeeded` 属支付正常推进（银行侧处理完成）→ `ok=true`。

**算例 D（脏迁移）**：`examples/transition_dirty.json`
```
kind=payment, from=refunded, to=captured
```
实际 2 条失败判据：`迁移 refunded → captured 合法（允许 无）`（`refunded` 在迁移表中无出边）、
`终态 refunded 不可再迁移`。正确处置：如需重新收款，新建支付意图
（`requires_payment_method` 起步），而不是对已退款意图做迁移。

## 第四层：实战踩坑

1. **把"状态 + 待办"当成"状态错误"**：`completed` + `pending_action=ship` 是合法的中间态，
   判 BLOCKER 会误伤正常流程。口径：状态在白名单内即通过，`pending_action`
   只做合法性提示（WARN），并检查该动作是否与终态矛盾。

2. **不同实体的同名状态混用**：订单有 `canceled`、支付也有 `canceled`、预约还有 `canceled`，
   语义完全不同（订单取消 ≠ 资金取消）。校验必须**按 kind 分别取白名单**，
   不能合并成一个全局集合。

3. **签名状态的大小写**：documenso 用全大写（`COMPLETED`），medusa 用小写（`completed`）。
   跨实体比较时若不归一化，会把正确的数据判错。口径：校验时按实体原文比对，
   跨实体引用时显式转换并说明。

4. **`requires_action` 被当成失败**：它表示"需要额外动作"（3DS 验证、补充材料），
   是可恢复态，不是失败。常见误判是把它归入"异常"直接拒绝交易。

5. **终态复开的需求**：客户要求"把已取消的订单恢复"时，正确做法是**新建订单**，
   保留原订单的取消记录。直接改状态会破坏审计链（事件表里会有两条互相矛盾的记录）。
   这也是编排原则：**历史不可改，未来可新建**。

6. **状态机与事件表的一致**：每次状态迁移都应在事件表留下记录（`order.completed`、
   `refund.created` 等）。若状态变了但事件表没记录，收入口径与业务事实不一致——
   这属 R08 revenue 技能的检查范围，两者需交叉验证。

7. **不要把 workflow 做成工作流引擎**：本技能只判"这个迁移合法吗"，
   不负责"如何自动化执行这套迁移"（那属 R17）。越界即 `scope_overlap`。

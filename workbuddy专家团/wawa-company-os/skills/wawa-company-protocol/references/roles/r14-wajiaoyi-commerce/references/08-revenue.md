# 08 · 收入数据接口与交易自动化接口（revenue）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/finance/close-management/SKILL.md
>


> 技能：`revenue` ｜ 动作：`events`（交易事件表）、`webhook`（回调需求）
> 来源：stripe__stripe-node（Webhook 事件与幂等）、medusa/lago（事件命名口径）

## 第一层：方法论

事件表与回调是交易系统的**神经系统**：状态变化通过事件传播给下游（财务、BI、通知）。
两个核心属性决定其可靠性：

1. **单调时间戳**——事件按发生顺序单调递增。时间倒退意味着乱序到达或时钟漂移，
   会让下游按时间窗口聚合的指标出错（例如"本月收入"算错）。
2. **三要素完整**——每个事件必须能回答"发生了什么（type）、对谁（entity_id）、
   涉及多少钱（amount）"。缺 amount 的事件无法用于收入口径。

**回调（webhook）的特殊性**：它是**外部系统主动推给我们**的，因此天然存在
重试、乱序、重复。三条方法论：

1. **回调必须声明对账方式（reconciliation）**。没有对账口径的回调需求，
   等于把"可能重复入账"的风险留给未来。
2. **重试次数有上限**（0–5）。无限重试会造成回调风暴，拖垮接收端。
3. **高风险回调需要审批声明**。涉及资金（refund、payment 相关）的回调端点，
   必须声明 `approval` 字段（谁批准接入），否则视为未授权接入。

**本角色绝对不做的事**：不配置真实回调端点、不注册真实密钥、不在回调处理器里
执行资金动作。R14 输出的是**回调需求工件**（event 类型、端点、对账方式、重试次数、
审批要求），由人工/工程师按此实现。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| event_types | ∈ `{order.created, order.completed, payment.succeeded, payment.failed, refund.created, invoice.finalized, document.completed, appointment.booked, order.canceled}` | 交易链事件口径 |
| event_required | `type`、`entity_id`、`amount` 三字段 | thresholds.event.event_required |
| amount_min | `amount ≥ 0`（最小货币单位） | thresholds.event.amount_min |
| 单调时间戳 | 事件序列的 `ts` 非递减 | 顺序可靠性 |
| 金额汇总 | `total_amount == Σ(event.amount)` | 可对账性 |
| retries | `0 ≤ retries ≤ 5` | 防回调风暴 |
| 对账声明 | `reconciliation` 非空 | 防重复入账 |
| 审批声明 | 高风险事件（refund/payment 类）→ `approval` 非空 | 未授权接入防护 |

**事件类型语义速查**：
- `order.created` / `order.completed` / `order.canceled`：订单生命周期
- `payment.succeeded` / `payment.failed`：资金结果
- `refund.created`：退款发生
- `invoice.finalized`：账单定稿（收入确认的**业务**信号，非会计确认）
- `document.completed`：签署完成（可触发交付）
- `appointment.booked`：预约确认

**高风险事件**（要求 `approval` 非空）：回调 `event` 名含 `refund` 或 `cancel` 者
（即 `refund.created`、`order.canceled`）。判定口径是**子串匹配**（`"refund" in event.lower()`），
所以 `payment.succeeded` / `payment.failed` **不在**强制审批集合内。
理由：退款与取消是对**既有资金/权益的撤销**，一旦被滥用会造成实际损失；
而"支付成功"本身只是通知，风险等级较低。

## 第三层：已验证的算例

**算例 A（干净事件表）**：`examples/events.json`
```
order.completed   / ord_001 / 104600 / 2026-11-05T09:00:00
payment.succeeded / pi_3abc / 104600 / 2026-11-05T09:01:00
invoice.finalized / inv_001 / 104600 / 2026-11-05T09:02:00
```
三个事件类型均合法、三要素齐备、时间戳单调递增（09:00 → 09:01 → 09:02）、
`total_amount = 104600 × 3 = 313800` → `ok=true`，`event_count=3`。

**算例 D（脏回调）**：`examples/webhook_dirty.json`
```
event=refund.created / endpoint="" / reconciliation="" / retries=9 / approval=""
```
实际 4 条失败判据：`回调端点非空`、`对账规则非空`、`重试次数=9 在 0-5 区间`
（应为"重试次数=9 在 0-5 区间"失败）、`高危回调「refund.created」必须声明人工审批`。
（`回调事件类型非空` 通过——`event` 字段本身有值。）

**算例 B（脏数据）**：`examples/events_dirty.json`
```
bogus.event      / x      / 1     / 09:05:00
order.completed  / ""     / -5    / 09:00:00
```
实际 4 条失败判据：`事件类型在白名单（越界 ['x']）`、`事件三要素齐备（缺 ['']）`、
`事件金额非负（异常 ['']）`、`事件时序单调（2 条）`。
其中**时间戳倒退**（09:05 之后出现 09:00）只有按序列看才能发现——
这正是"事件表是一门序列校验"的体现。

**算例 C（干净回调）**：`examples/webhook.json`
```
event=payment.succeeded / endpoint=https://example.com/hooks/stripe
reconciliation="按 payment_intent 幂等键对账" / retries=3 / approval=""
```
`retries=3 ≤ 5`、对账方式已声明、端点非空 → `ok=true`。
（本样例的事件类型不在高风险集合内，`approval` 空合法。）

**算例 D（脏回调）**：`examples/webhook_dirty.json`
```
event=refund.created / endpoint="" / reconciliation="" / retries=9 / approval=""
```
BLOCKER ×4：`refund.created` 属高风险但无 `approval`、端点为空、
无对账声明（重复入账风险）、`retries=9 > 5`（回调风暴风险）。

## 第四层：实战踩坑

1. **时间戳格式混用**：ISO 8601（`2026-11-05T09:00:00`）与本地格式（`2026-11-05 09:00`）
   混在一张表里，字符串比较会得出错误顺序。必须解析为时间对象比对，
   并显式要求统一格式。

2. **同一秒内多个事件**：`09:00:00` 出现两次是合法的（同秒不同实体）。
   "单调非递减"允许多个相等值，**不是**严格递增。写成严格递增会误杀正常数据。

3. **amount 的单位**：与支付层一致，统一用**最小货币单位**。
   事件表里混用元与分，会让汇总金额错 100 倍。这是收入口径事故的头号来源。

4. **重放导致的虚假事件**：上游重发同一事件（无幂等键）→ 事件表里出现两条相同记录
   → `total_amount` 翻倍。口径：对账时按 `entity_id` + `type` 去重再汇总，
   并检查是否存在幂等键。

5. **"对账方式"不能写成空话**：`reconciliation="对账"` 等于没写。
   合格的对账声明必须给出**键**（如 payment_intent / 幂等键 / 订单 ID）
   和**判定规则**（如"按键去重，以首次为准"）。

6. **回调端点不能用内网地址**：`http://localhost:3000/hooks` 在部署后不可达。
   端点校验应检查协议与可解析性；本技能只校验非空，实际可达性属部署验证（R17）。

7. **不要在结论里写"我已配置好回调"**：属 `unauthorized_exec`。
   正确写法："产出回调需求工件（event=refund.created，端点待人工确认，
   对账按幂等键去重，retries=3，需业务负责人审批接入）。"

8. **事件的口径 ≠ 财务口径**：`invoice.finalized` 是业务事件（账单定稿），
   不等于会计上的收入确认。涉及收入确认时点、递延、摊销，一律移交 R03，
   并在结论中显式写出移交声明。

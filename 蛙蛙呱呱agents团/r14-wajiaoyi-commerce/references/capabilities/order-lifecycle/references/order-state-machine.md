# 订单状态机与退款规则（order-state-machine）

> 被 §3、§5、§7 按需引用。版本：v2.0.0（项目自建，v1）

---

## 一、三态模型（正交，不是层级）

| 维度 | 白名单 | 语义 |
|---|---|---|
| `status` | `pending` / `paid` / `completed` / `canceled` | 订单整体生命周期 |
| `payment_status` | `pending` / `authorized` / `captured` / `refunded` / `failed` | 钱到了哪一步 |
| `fulfillment_status` | `unfulfilled` / `partial` / `fulfilled` / `delivered` | 货到了哪一步 |

**为什么必须分开**：退款只需回滚支付，不该动履约（货已发出）；
部分发货不该把订单整体置为完成。用一个字段表达三件事，必然出现"要么错要么丢信息"。

---

## 二、合法迁移白名单

### 订单 `status`
```
pending → paid        （仅当 payment_status ∈ {authorized, captured}）
pending → canceled
paid    → completed   （仅当 fulfillment_status = delivered）
paid    → canceled    （需先退款）
completed / canceled  → 终态，不可迁移
```

### 支付 `payment_status`
```
pending    → authorized → captured
pending    → failed
authorized → captured
captured   → refunded
failed / refunded → 终态，不可迁移
```

### 履约 `fulfillment_status`
```
unfulfilled → partial → fulfilled → delivered
unfulfilled → fulfilled
delivered → 终态，不可迁移
```

> 未列出的路径**一律非法**。想加新路径，先改这份文档，再改门禁，最后改代码——顺序不能反。

---

## 三、终态保护

| 终态 | 为什么不能回头 | 想"撤销"时的正确做法 |
|---|---|---|
| `completed` | 已结算，回头会让收入与库存永久失真 | 新建退货单 / 换货单，原单不动 |
| `canceled` | 已退款或未成交，重开会产生重复账 | 新建重购单 |
| `refunded` | 钱已退出，重进需新交易 | 新建重购单 |
| `delivered` | 货已到用户手里 | 新建退货流程 |

**铁律**：撤销业务动作 ≠ 修改状态。改终态是不可审计的，新建关联单是可审计的。

---

## 四、退款规则（四条一起看）

| 检查 | 规则 | 常见违反 |
|---|---|---|
| `refund.required` | 必填：金额、原因、`payment_intent` | 只填金额就提交 |
| `refund.amount` | > 0 | 0 元退款（走补偿而非退款） |
| `refund.ratio` | **累计比例 ≤ 1.0** | 多次部分退款累计超总额 |
| `refund.prior` | 前置状态必须可退款 | 从 `canceled` 发起退款（钱可能根本没收到） |

### 部分退款

正确姿势：
```
退款单 R1：金额 300（订单 1000）→ 累计比例 0.3
退款单 R2：金额 200            → 累计比例 0.5
```
每笔**独立记录**，累计比例由系统汇总。不要把 R1 的金额改成 500 来表达"又退了一点"——
那会覆盖历史，且审计时无法还原"先后退了多少"。

### 不可退款的典型前置状态

| 前置 | 为什么不可退 |
|---|---|
| `canceled` | 订单已取消，可能从未收款 |
| `pending`（支付未成功） | 没有钱可退 |
| `failed` | 支付失败，无资金流入 |
| `refunded`（已全额） | 已退完，再退即超比例 |

---

## 五、幂等（不是优化，是正确性）

| 场景 | 无幂等的后果 | 幂等键建议 |
|---|---|---|
| 支付回调重试 | 重复记账 / 重复发货 | `order_id + event_type + event_id` |
| 退款重试 | 同一笔退两次 | `order_id + refund_seq` |
| 状态迁移重试 | 从终态再迁移一次 | `order_id + transition + seq` |
| webhook 重放 | 伪造"已支付" | 验签 + 时间窗 + 事件去重表 |

**幂等键三要素**：足够唯一、可由重试方原样重建、不含随机量。
用 UUID 做幂等键是常见错误——重试时生成新 UUID，等于没有幂等。

---

## 六、事件与回调校验

| 检查 | 内容 |
|---|---|
| `events` | 事件结构（类型/时间/实体/序号）+ 顺序单调 + 无空洞 |
| `webhook` | 签名有效 + 时间戳在重放窗口内 + 事件 ID 未处理过 |

**顺序为什么重要**：`refunded` 事件先于 `captured` 到达，说明上游乱序或存在补偿交易。
不校验顺序，就会把乱序当正常，最后对账时才发现钱对不上。

---

## 七、与门禁的对应关系

| 门禁 | 覆盖本文件的哪一节 | 判不了什么 |
|---|---|---|
| `harness.py order` | §一 白名单、§二 三态一致性 | 判不了迁移路径全貌 |
| `harness.py state` | §三 终态保护 | 判不了迁移合法性 |
| `harness.py transition` | §二 迁移白名单 + 终态 | 判不了跨实体顺序 |
| `harness.py refund` | §四 四项退款约束 | 判不了真实资金流 |
| `harness.py cart` | 行项目与金额一致 | — |
| `harness.py events` | §六 事件结构 | 判不了业务语义 |
| `harness.py webhook` | §六 回调校验 | 判不了上游是否可信 |

> 七道门禁合起来能保证"状态机自洽"，**保证不了"这笔钱真的到账了"**。
> 资金真实性只能靠渠道对账单，归 `r03`。

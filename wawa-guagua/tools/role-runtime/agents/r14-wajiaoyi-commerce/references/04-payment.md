# 04 · 支付意图与退款口径（payment）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/finance/variance-analysis/SKILL.md
>


> 技能：`payment` ｜ 动作：`payment_intent`（支付意图）、`refund`（退款请求）
> 来源：stripe__stripe-node（PaymentIntent.status、Refund、Webhook 幂等）

## 第一层：方法论

支付层是**不可逆动作聚集区**。订单错了可以改、账单错了可以重开，
但一旦钱到了错误的地方，挽回成本极高。因此本技能的设计哲学与其它技能完全相反：

> **其它技能追求"帮用户把事做成"；支付技能追求"让不该发生的事发生不了"。**

三条方法论：

1. **状态枚举即安全边界**。Stripe 的 PaymentIntent.status 是一台严格的状态机，
   任何不在枚举内的状态都意味着"我们不知道这笔钱在哪里"——未知即危险，一律 BLOCKER。

2. **金额有下限**。`amount_min = 50`（最小货币单位，即 0.50 元）。低于此的支付意图
   通常是上游把"元"和"分"搞混了（1046 元写成 1046 分）。这个下限不是为了限制小额支付，
   而是**单位混淆的探测器**。

3. **成功状态必须幂等**。`succeeded` 的支付意图若再收到同一 webhook，
   幂等处理是唯一正确响应。没有幂等键的重复 `payment.succeeded` = 重复入账风险。

**本角色绝对不做的事**：不开通支付账户、不配置真实密钥、不发起扣款、不发起退款。
所有涉及资金真实流动的动作都产出**请求工件**，由人工授权后在网关侧执行。
这不是保守，是分工——R14 的价值在于"把该退多少算对"，不在于"按下那个按钮"。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| pi_status | ∈ `{requires_payment_method, requires_confirmation, requires_action, processing, requires_capture, canceled, succeeded}` | stripe PaymentIntent.status |
| intent_types | ∈ `{payment_intent, setup_intent, subscription}` | stripe 支付意图族 |
| amount_min | `amount ≥ 50`（最小货币单位） | thresholds.payment.amount_min |
| succeeded_status | `"succeeded"` | stripe |
| 成功幂等性 | `status == succeeded` → 必须声明 `idempotency_key` | 防重复入账 |
| cancelable_statuses | ∈ `{requires_payment_method, requires_capture, requires_confirmation, requires_action, processing}` | stripe 可取消集合 |
| refund_required | `payment_intent`、`amount`（+ 本仓库扩展 `original_amount`、`prior_status`） | thresholds.payment.refund_required |
| refund_ratio_max | `amount / original_amount ≤ 1.0` | 禁止超额退款 |
| 退款前置状态 | `prior_status ∈ {succeeded, partially_refunded, captured}`；缺省视为可退 | stripe 可退族 + medusa captured |
| 凭据零出现 | 输出文本中不得出现 api_key/secret/token/password/私钥/密钥 | R14 红线 |

**Pay 状态家族速查**：
- `requires_*` 族：**钱未动**，可以安全取消或重试。
- `processing`：银行侧处理中，**不可判定成败**，只能等待。
- `requires_capture`：已授权未捕获，可以取消（释放冻结）或捕获。
- `succeeded`：**钱已入账**，此后只能走退款通道。
- `canceled`：已取消，不构成退款前提（钱没进来）。

## 第三层：已验证的算例

**算例 A（干净支付意图）**：`examples/payment_intent.json`
```
pi_3abc / succeeded / amount=104600 / payment_intent / payment.succeeded / idem_001
```
状态合法、金额 104600 ≥ 50、成功状态带幂等键 → `ok=true`。

**算例 B（脏数据）**：`examples/payment_intent_dirty.json`
```
id="" / status="bogus" / amount=10 / payment_intent
```
BLOCKER ×3：id 为空、状态不在枚举、`amount=10 < 50`（典型的"元/分"混淆信号）。

**算例 D（脏退款）**：`examples/refund_dirty.json`
```
payment_intent="" / amount=200000 / original_amount=104600 / prior_status="canceled"
```
实际 3 条失败判据：`退款必填齐备（缺 ['payment_intent']）`、
`退款比例=1.912 ≤ 1.0`（1.912 > 1.0，超额 91.2%）、`前置状态='canceled' 不可退款`。
**关键**：超额与不可退是两类独立错误，必须分别指明——只报"退款失败"无法指导修复。

**算例 C（干净退款）**：`examples/refund.json`
```
payment_intent=pi_3abc / amount=29900 / original_amount=104600 / prior_status=succeeded
refund_ratio = 29900 / 104600 = 0.2859 ≤ 1.0  → PASS
prior_status=succeeded ∈ 可退集合             → PASS
```
部分退款，额度合法 → `ok=true`。

## 第四层：实战踩坑

1. **"退款"其实该做"取消"**：对 `requires_capture` 的支付，"退款"是把授权释放掉，
   走 cancel 而非 refund。走错通道会导致退款失败并留下冻结资金。先看状态再选通道。

2. **元/分混淆是头号事故源**：1046 元写成 `amount=1046`（分）等于退 10.46 元。
   本仓库统一用**最小货币单位**（分），并在 `references` 与样例中显式标注。
   接入真实数据时，任何 `amount < 50` 都要先怀疑单位。

3. **重复 webhook = 重复退款**：退款成功后网关会重发 `charge.refunded`。
   没有幂等键时，第二次处理会再退一次。口径：所有资金相关回调必须带幂等键，
   处理前先查 `idempotency_key` 是否已消费。

4. **partially_refunded 之后还能退**：剩余可退额度 = `original_amount - Σ已退金额`。
   `refund_ratio` 应对**累计**退款计算，不是对单次。只按单次计算会导致总额超额。

5. **凭据的"隐性"泄露**：不只是明文 key。形如 `sk_live_xxx`、`whsec_xxx` 的前缀片段、
   完整 webhook 签名串、后台登录链接带 token，都算泄露。评审层按关键词扫描，
   命中即 `credential_leak` 退回。

6. **不要在结论里写"我已为客户退款"**：这是越权（`unauthorized_exec`）。
   正确写法："产出退款请求工件 refund.json（amount=29900，prior_status=succeeded），
   标注需人工授权，由人工在网关侧执行。"

7. **金额为零的退款**：`amount=0` 的退款请求无意义，且会污染退款流水。
   口径：`amount > 0` 是退款的隐含前提（尽管 schema 只约束 ratio ≤ 1.0）。

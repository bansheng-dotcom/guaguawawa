# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/order-lifecycle/scripts/gate_selftest.py` → 必须 `PASS 11/11`（含 5 个反例）。
> 版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | `payment_status=refunded` 且 `status=completed` | `order.consistency` 三态矛盾 | ✅ exit=1（`order_dirty.json`） |
| MU-02 | `total = 0` | `order.total` 必须 > 0 | ✅ exit=1（同上） |
| MU-03 | 订单号为空 | `order.id` BLOCKER | ✅ exit=1（同上） |
| MU-04 | `status` 填白名单外的自创值 | `order.status` 白名单 | ✅ 由 `order.status` 覆盖 |
| MU-05 | 购物车行项目金额与总额不一致 | `cart.*` 一致性命中 | ✅ exit=1（`cart_dirty.json`） |
| MU-06 | 终态实体仍有后续动作 | `workflow.terminal` | ✅ exit=1（`state_dirty.json`） |
| MU-07 | 从终态 `refunded` 迁向 `captured` | `transition.to` / `transition.terminal` | ✅ exit=1（`transition_dirty.json`） |
| MU-08 | 退款缺 `payment_intent` | `refund.required` | ✅ exit=1（`refund_dirty.json`） |
| MU-09 | 退款比例 1.912（超 100%） | `refund.ratio ≤ 1.0` | ✅ exit=1（同上） |
| MU-10 | 退款前置状态为 `canceled` | `refund.prior` 不可退款 | ✅ exit=1（同上） |

## 二、门禁抓不到，必须靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-11 | 在代码里临时加一条 `if status=='x': status='y'` | 迁移未进白名单 | §6 + 代码评审（`r09`） |
| MU-12 | 部分退款在同一记录里反复改金额 | 历史不可还原 | §6 自检 |
| MU-13 | 幂等键用随机 UUID | 重试生成新键＝没有幂等 | §6 + 压测 |
| MU-14 | webhook 不验签、不限重放窗口 | 可被伪造"已支付" | `harness webhook` 部分覆盖 + §6 |
| MU-15 | 事件乱序（refunded 先于 captured） | 上游乱序或补偿交易 | `harness events` 部分覆盖 + §6 |
| MU-16 | 用 `status` 一个字段承担三态语义 | 必然丢信息 | §6 + 架构评审 |
| MU-17 | 门禁报错就改状态字段让它变绿 | 改绿了就会被结算 | §7 EX-10 + 治理 |
| MU-18 | 状态机只存在某人的记忆里 | 接口改动即失效 | §6 要求落盘 |

---

## 三、诚实说明：门禁的边界

| 门禁能判 | 门禁判不了 |
|---|---|
| 三态是否自洽 | 这笔钱**真的**到账了吗（需渠道对账单，归 `r03`） |
| 迁移是否在白名单 | 业务上**该不该**走这条迁移（需业务规则） |
| 退款比例是否 ≤ 1.0 | 退款是否**应该**批（需财务判断） |
| 事件结构是否合法 | 上游系统是否可信 |

> **纪律**：门禁过 ≠ 钱对了。状态机自洽只是必要条件。
> 任何涉及真实资金的结论，必须叠加 `r03` 的渠道对账，否则不得出"账实相符"的说法。

---

## 四、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 新增状态或迁移路径时，先改 `references/order-state-machine.md`，再改 `harness.py`，最后改代码
- [ ] 每次改 `harness.py` 的 `order/cart/refund/state/transition` 检查项后重跑 `gate_selftest.py`
- [ ] 涉及真实资金的结论都已叠加 `r03` 对账
- [ ] 七道门禁中本次涉及的都已跑，未跑的已标注"未验"

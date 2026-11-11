# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/webhook-retry/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 6/6`（含 3 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 缺 path | `webhook.path` | ✅ exit=1（`examples/webhook_dirty.json`） |
| MU-02 | 缺 method | `webhook.method` | ✅ exit=1（同上） |
| MU-03 | 缺 handlers（收了不处理） | `webhook.handlers` | ✅ exit=1（同上） |
| MU-04 | 无幂等键 | `retry.idempotency` | ✅ exit=1（`examples/retry_dirty.json`） |
| MU-05 | 无死信队列 | `retry.dead_letter` | ✅ exit=1（同上） |
| MU-06 | 错误流未发布 | `errorflow.published` | ✅ exit=1（`examples/errorflow_dirty.json`） |
| MU-07 | 无恢复路径 | `errorflow.recovery` | ✅ exit=1（同上） |

## 二、门禁抓不到，靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-08 | 幂等键用 UUID | 重试生成新键 = 没幂等 | §6 三要素检查 |
| MU-09 | 无限重试 | 打爆下游 | §6 次数检查 |
| MU-10 | 固定间隔重试 | 重试风暴 | §6 退避检查 |
| MU-11 | 外部回调不验签 | 可伪造"已支付" | §6 + `r14` 对账 |
| MU-12 | 所有事件同一 path | 无法独立重试 | §6 路由检查 |
| MU-13 | 凭据写进代码 | 泄露 | §6 + 治理 |
| MU-14 | 只做传输层去重 | 业务重复执行 | §7 EX-11 |
| MU-15 | 把"重试 99 次"当死信 | 死信是独立去处 | §7 EX-12 |

---

## 三、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 每次改 `harness.py webhook/retry/errorflow` 后重跑 `--self-test`
- [ ] 死信队列写明了谁看、多久看一次
- [ ] 恢复路径演练过一次（不只是设计）
- [ ] 业务侧也做了幂等（不只在传输层）

> **纪律**：丢事件不会报错，只会让数据慢慢对不上。
> 死信队列是唯一能让"丢了"变成"看见了"的东西。

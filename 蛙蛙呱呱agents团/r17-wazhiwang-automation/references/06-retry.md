# 参考层 06 —— 失败处理与重试（debugging-executions / error-workflows）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/skills/incident-response/SKILL.md
>


> 来源：n8n-io__n8n `packages/@n8n/instance-ai/skills/debugging-executions` +
> `error-workflows`
> 角色：R17 蛙织网 · S06 retry 的确定性口径来源。

## 第一层 · 方法论

自动化在真实世界必然遇到失败：网络超时、API 限流、数据脏、下游系统宕机。n8n
的失败处理围绕三个概念：

1. **重试（retry）**：对可恢复错误（超时、限流）自动重试，但要有上限。
2. **幂等（idempotency）**：**写操作**重试时必须幂等——否则一次「创建订单」重试
   三次就变成三张订单。幂等靠 `idempotency_key` 或**轮询游标去重**（poll cursor
   dedupe：记录已处理的 id，重跑时跳过）。
3. **死信与告警（dead letter / notify）**：重试耗尽后，失败项进死信队列或发
   告警，绝不能静默丢弃。

错误处理在 n8n 里是**独立的工作流**（error workflow）：一个带 **Error Trigger**
的工作流，被挂到目标工作流上。关键约束：

- **必须是已发布的 Error Trigger**：draft 的错误流运行时不会生效。
- **按目标挂载**：`settings.errorWorkflow` 是**每个工作流**的设置，不是全局兜底。

## 第二层 · 可执行口径（判据 | 口径 | 取值来源）

| 判据 | 口径 | 取值来源 |
|---|---|---|
| 重试上限 | 0 ≤ max_retries ≤ 10 | n8n retry 设置 |
| 超时 | timeout_s ≥ 1 | n8n 节点超时 |
| 写操作幂等 | operation ∈ 写集合 → 必须声明 idempotency_key 或 poll_cursor_dedupe | n8n idempotency |
| 死信/告警 | dead_letter 或 notify 至少其一 | n8n 恢复路径 |
| 错误流目标 | target_workflow_id 非空 | error-workflows |
| 错误流发布 | published 且 error_trigger_active | 发布铁律 |
| 按目标挂载 | per_target=True（非 global） | settings.errorWorkflow |

## 第三层 · 已验证算例

**干净重试**：
```
policy={max_retries: 3, timeout_s: 5, operation: create,
        idempotency_key: idem_abc, dead_letter: true}
```
门禁：重试有界 + 写操作 create 有幂等 key + 有死信 → PASS，`idempotency_declared=True`。

**脏重试**：
```
policy={max_retries: 3, timeout_s: 5, operation: create}   # 无幂等、无死信
```
门禁：`写操作 create 未声明幂等` + `无死信/告警路径` → FAIL。

**脏错误流**：
```
error_workflow_id=wf_err_123, published=False, error_trigger_active=True
```
门禁：`错误工作流已发布且 Error Trigger 激活（published=False）` → FAIL。

## 第四层 · 实战踩坑

1. **「写操作」集合要列全**：`create/update/insert/upsert/send/delete/post/put/
   patch/charge/refund/publish`——漏掉 `upsert` 或 `charge` 会放过真实的风险操作。
2. **轮询去重也算幂等**：有的集成没有 idempotency_key，靠 poll cursor 记录已处理
   id 去重，同样是合法幂等，别只认 key。
3. **错误流「发布」与「触发激活」是两件事**：published 是工作流状态，active 是
   触发器是否在监听。两者都为真才算生效。
4. **`max_retries` 上限不是任意值**：设成 100 会让失败任务反复烧资源，R17 封顶 10。

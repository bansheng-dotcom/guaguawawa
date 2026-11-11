---
name: webhook-retry
description: Webhook 与失败重试技能包。把"接了这条回调"变成可校验的集成契约：Webhook 必须有明确 path/method/handlers，重试必须定义幂等键与死信队列，错误流必须有恢复路径且发布前验证过，配套凭据与审计留痕齐备。当需要设计 webhook 接收端、配重试与死信、排查回调丢事件、或判断一条集成能不能上生产时使用。不负责业务逻辑实现、不做第三方账号授权、不替代数据管道建模。
license: MIT
compatibility: 通用。门禁在角色根目录 harness.py（webhook / retry / errorflow 三道，Python 3.10+、零第三方依赖）；无 Python 环境时按 §8 转人工八项核对，此时不得上生产。
metadata:
  owner: r17
  version: "2.0.0"
  kind: skill
  triggers: "webhook,回调,重试,幂等,死信,错误流,集成"
  verify: python harness.py webhook --input <webhook定义.json>
  entry: "python agent.py webhook webhook"
  consumers: "r14,r18,r20"
  supersedes: README.md
---

<!-- 本文件由 scripts/sync_dsh_skills.py 生成，请勿手改；改源包后重跑同步 -->

# Webhook 与失败重试（Webhook Retry）

> 一句话定位：**这个技能存在的意义，是防止"回调接了，但丢事件没人知道"**。
> 集成最贵的失败不是接口报错，而是**静默丢事件**：
> 重试没有幂等键导致重复扣款、失败进不了死信队列于是永久丢失、
> 错误流没验证过就上线于是故障时才发现走不通。
> 这些都不会让服务挂掉，只会让数据慢慢对不上。

## §1 何时用 / 何时不用

**该用（用户真实会这么说）**
- 「接一下支付回调」「webhook 怎么配」
- 「失败了怎么重试」「为什么有的事件丢了」
- 「这条集成能上生产吗」

**不该用，转给谁**

| 用户其实想要 | 转给 | 理由 |
|---|---|---|
| 订单状态与退款逻辑 | `r14` 交易 | 本技能只管回调传输与重试 |
| 数据同步与管道 | `r18` 数仓 | 那是 ETL 侧 |
| 告警与值班 | `r20` 值守 | 本技能只定义审计与错误流 |
| 第三方账号授权操作 | 人工 | 本技能不做 OAuth 实操 |

**最小可开工输入**：**事件来源 + 接收端行为**（要做什么）。

---

## §2 前置输入与最省追问

| 输入 | 是否必需 | 缺失时怎么办 |
|---|---|---|
| 事件来源（哪个服务推什么） | 必需 | 无来源无法定 path/method |
| 接收端 path 与 method | 必需 | 门禁会拦（`webhook.path` / `webhook.method`） |
| 处理动作（handlers） | 必需 | 无 handler 等于收了不处理（`webhook.handlers`） |
| 幂等键定义 | 重试时必需 | 缺则重试会重复执行（`retry.idempotency`） |
| 死信去处 | 重试时必需 | 缺则失败事件永久丢失（`retry.dead_letter`） |

**追问纪律**：最多一轮，只问**谁推、推什么、失败了怎么办**。

---

## §3 执行流水线（Workflow）

### Step 1 · Webhook 契约（path / method / handlers）
```bash
python harness.py webhook --input <webhook定义.json>
```
- `path`：唯一路由，不同事件分开；
- `method`：通常 POST，改了要有理由；
- `handlers`：至少 1 个，且写明"做什么、失败怎么办"。

门禁实测：缺 path/method/handlers 任一即 FAIL。

**验签必做**：外部回调必须校验签名与时间戳，否则任何人都能伪造"已支付"。

- **产出**：webhook 定义
- **过关条件**：`harness.py webhook` 退出码 0

### Step 2 · 幂等键（重试的正确性前提）
```bash
python harness.py retry --input <重试策略.json>
```
幂等键三要素：**足够唯一 / 重试方能原样重建 / 不含随机量**。

| 反例 | 为什么错 |
|---|---|
| 用 UUID | 重试时生成新 UUID，等于没有幂等 |
| 用时间戳 | 重试时间不同 |
| 只用来事件类型 | 同类型多个事件会互相覆盖 |
| ✅ `event_id` 或 `order_id + event_type` | 可重建、唯一、稳定 |

门禁实测：缺 `idempotency` 即 FAIL。

- **产出**：幂等键定义
- **过关条件**：`harness.py retry` 退出码 0

### Step 3 · 重试策略与死信（失败要有去处）
| 参数 | 建议 | 说明 |
|---|---|---|
| 最大重试次数 | 3–5 次 | 无限重试会打爆下游 |
| 退避 | 指数退避 + 抖动 | 固定间隔会形成重试风暴 |
| 超时 | 单次 ≤ 10s | 过长会拖住队列 |
| 死信队列 | **必需** | 超过次数进 DLQ，人工介入 |

门禁实测：缺 `dead_letter` 即 FAIL。

**没有死信的"无限重试"是最坏设计**：既丢不了也处理不了。

### Step 4 · 错误流与恢复（上线前必须验证）
```bash
python harness.py errorflow --input <错误流.json>
```
必须满足：`published`（错误流已发布生效）+ `recovery`（恢复路径可执行）。
门禁实测：任一缺失即 FAIL。

**"错误流设计了但没发布"是最常见的坑**：配置存在于草稿里，故障时根本没跑。

- **产出**：错误流定义 + 恢复验证记录
- **过关条件**：`harness.py errorflow` 退出码 0

### Step 5 · 凭据与审计
- 凭据（API Key / 签名密钥）走环境变量或密钥管理，**不进代码库**；
- 每次回调与重试都写审计日志（事件 ID / 结果 / 耗时 / 重试次数）。

---

## §4 交付物清单

| # | 交付物 | 载体 | 骨架出处 |
|---|---|---|---|
| 1 | Webhook 定义（path/method/handlers + 验签） | `.json` | `examples/webhook.json` |
| 2 | 重试策略（幂等键/退避/最大次数/死信） | `.json` | `examples/retry.json` |
| 3 | 错误流与恢复验证 | `.json` | `examples/errorflow.json` |
| 4 | 审计日志字段定义 | `.md` | 本文 §3 Step 5 |

- 命名：`integration_<系统>_<YYYYMMDD>.json`
- **死信去处必须落盘**；口头"失败会有人看"不算。

---

## §5 质量门（一票否决，不过不给交付）

1. **webhook 有 path / method / handlers**（`webhook.*`）；
2. **外部回调有验签与时间戳校验**；
3. **幂等键可重建且唯一**（`retry.idempotency`）；
4. **有最大重试次数与指数退避**；
5. **有死信队列**（`retry.dead_letter`）；
6. **错误流已发布**（`errorflow.published`）且**恢复路径已验证**（`errorflow.recovery`）；
7. **凭据不进代码库**，审计日志字段齐全。

> 验收命令：`python harness.py webhook|retry|errorflow --input <json>`
> 命中任一项不过 → 回 §3 对应 Step，**不允许把"重试 99 次"当死信**。

---

## §6 交付前自检清单

- [ ] 我写清了谁在什么时候推什么事件
- [ ] path 与 method 明确，不同事件分开路由
- [ ] 至少一个 handler，且写了"失败怎么办"
- [ ] 外部回调做了验签 + 时间戳窗口校验
- [ ] 幂等键是 `event_id` 或业务键组合，不是 UUID
- [ ] 重试次数有限（3–5 次），退避是指数 + 抖动
- [ ] 死信队列存在，并写明谁看、多久看一次
- [ ] 错误流**已经发布**，不只是画在文档里
- [ ] 恢复路径演练过一次（不只是设计）
- [ ] 凭据走环境变量，没写进代码
- [ ] 审计日志记了事件 ID / 结果 / 耗时 / 重试次数
- [ ] 三道门禁均退出码 0

---

## §7 易犯错误对照表

| # | 易犯错法 | 正确做法 |
|---|---|---|
| EX-01 | 幂等键用 UUID | 用 `event_id` 或 `order_id + event_type`，重试能原样重建 |
| EX-02 | 无限重试 | 3–5 次后进死信队列；无限重试会打爆下游 |
| EX-03 | 固定间隔重试 | 指数退避 + 抖动，避免重试风暴 |
| EX-04 | 没有死信队列 | 必须有 DLQ，并写明谁负责看 |
| EX-05 | 错误流只在文档里 | 必须发布生效并验证过 |
| EX-06 | 外部回调不验签 | 验签 + 时间戳窗口；否则可伪造"已支付" |
| EX-07 | 所有事件塞同一个 path | 按事件类型分开路由，便于独立重试 |
| EX-08 | handler 写"处理一下" | 写清做什么、失败怎么办、是否可重入 |
| EX-09 | 凭据写进代码/配置库 | 走环境变量或密钥管理 |
| EX-10 | 不记审计日志 | 记事件 ID / 结果 / 耗时 / 重试次数 |
| EX-11 | 重试成功但业务重复执行 | 幂等键必须在**业务侧**也去重，不只在传输层 |
| EX-12 | 把"重试 99 次"当死信 | 死信是独立去处，不是"再试一次" |

---

## §8 降级与边界

| 触发情况 | 处置 |
|---|---|
| `harness.py` 跑不了 | 按 §6 人工逐项核对，标注「未跑门禁」；**不得上生产** |
| 第三方不支持验签 | 用共享密钥 + IP 白名单，标注"无签名校验"，风险已知 |
| 无法建死信队列 | 至少落本地失败表 + 每日巡检，标注"临时方案" |
| 事件量极大 | 先做幂等与死信，再谈吞吐；不许为吞吐砍掉幂等 |
| 回调乱序到达 | 用事件时间戳排序，不依赖到达顺序 |
| 需要人工审批的步骤 | 审批节点出队列，不进重试（重试人不会点） |
| 涉及真实支付回调 | 额外加 `r14` 对账 + `r03` 复核，本技能不出资金结论 |

**明确不做**
- 不实现业务逻辑（归 `r09`）；
- 不做第三方账号授权实操（人工）；
- 不做数据管道建模（归 `r18`）；
- 不收告警配置（归 `r20`）。

---

## §9 资源地图（按需读取，禁止全量加载）

> 本包不单独设 `references/`：契约与判据写在正文 §3，判定复用角色根目录 `harness.py`。
> 调研说明：全网**未找到**高质量的 n8n/webhook 技能包（最接近的是 `studiomeyer-io/n8n-workflows`
> 的模板 + 独立 `PRODUCTION_CHECKLIST.md`），本包为自建。

| 什么时候需要 | 读哪个文件 |
|---|---|
| webhook 定义骨架 | `D:/蛙蛙呱呱/蛙蛙呱呱agents团/r17-wazhiwang-automation/examples/webhook.json` |
| 重试策略骨架 | `D:/蛙蛙呱呱/蛙蛙呱呱agents团/r17-wazhiwang-automation/examples/retry.json` |
| 错误流骨架 | `D:/蛙蛙呱呱/蛙蛙呱呱agents团/r17-wazhiwang-automation/examples/errorflow.json` |
| 事件 / 映射 / 定时 | `D:/蛙蛙呱呱/蛙蛙呱呱agents团/r17-wazhiwang-automation/examples/event.json` / `mapping.json` / `schedule.json` |
| 凭据定义 | `D:/蛙蛙呱呱/蛙蛙呱呱agents团/r17-wazhiwang-automation/examples/credential.json` |
| 审计日志 | `D:/蛙蛙呱呱/蛙蛙呱呱agents团/r17-wazhiwang-automation/examples/audit.json` |
| 门禁是否还有效（正/反例 fixture） | `scripts/gate_selftest.py --self-test` |
| 负向用例 | `tests/misuse.md` |

**脚本清单**

| 脚本 | 用途 | 入口 |
|---|---|---|
| `scripts/gate_selftest.py` | 断言三道门禁对正/反例的退出码 | `--self-test` / `--verbose` |

---

## §10 变更记录

- **v2.0.0（2026-11-11）**：按 `docs/SKILL-LAYER-SPEC.md` v1.0 新增技能包。
  含 §1–§10 十节骨架、`scripts/gate_selftest.py`、`tests/misuse.md`。
  门禁复用 `harness.py` 三道（webhook / retry / errorflow）。
- **调研结论**：n8n / Zapier / Make 生态**没有**可对标的技能包，本包内容为自建（幂等三要素、
  死信必填、"错误流必须已发布并验证"三条为原创约束）。

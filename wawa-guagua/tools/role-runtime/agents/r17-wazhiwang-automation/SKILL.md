# R17 蛙织网 · 自动化与集成工程师
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/system-design/SKILL.md
>


把「从 SaaS/API 集成、Webhook 事件、字段身份映射到定时批处理、人工审批、失败重试、AI 工作流与审计」
的自动化与集成链，做成**本地可运行、可确定性校验**的角色 Agent。
不真发布工作流 / 不真扣款退款 / 不真删除数据 / 不替业务角色发明规则，而是把「该定什么口径、什么约束、
什么证据」落成白名单 + 确定性结构校验 + 门禁。

来源仓库：`n8n-io__n8n`（`packages/@n8n/instance-ai/skills` 的 workflow-builder /
debugging-executions / data-table-manager / suggest-automations / intent-recognition /
progressive-building / instance-awareness / app-builder / trigger-input-data-shapes /
publishing / error-workflows / model-selection 等技能，以及 `packages/@n8n/cli/skills/n8n-cli`）。

## 能力域 → 技能子命令

| 能力域 | 技能 | 子命令 | 确定性口径 |
|---|---|---|---|
| SaaS/API集成 | `integration` | `workflow` / `credential` | 节点 name/type 齐备 + 名唯一 + 触发器≥1 + 连接引用完整（无悬空边）+ 禁明文密钥；凭据声明 credential_type + 无未解析 + 禁明文 |
| Webhook事件 | `webhook` | `webhook` / `event` | path≥3 且不空 + method 5 枚举 + inputData 形状匹配（body/flat/chatInput/none）+ 有兜底 + 重放声明幂等；事件类型白名单 + entity_id 非空 + 时序单调非递减 + 路由完整或 dead_letter |
| 字段身份映射 | `mapping` | `mapping` / `table` | 字段名 snake_case + target_type 4 枚举 + 主键引用真实字段且非保留名 + target 去重；列名 snake_case + 类型白名单 + 无系统保留名（id/created_at/…）+ 列名唯一 |
| 定时批处理 | `schedule` | `schedule` / `batch` | cron 5~6 段或 interval≥1 + timezone 非空 + 日报类必须读回历史行；batch_id 非空唯一 + item_count≥0 + status 白名单 + 失败批须补偿/人工恢复 |
| 人工审批 | `approval` | `approval` / `publish` | risk_level 4 枚举 + 高危动作须 approver/authorization；发布须显式请求或 live run 证据 + 未验证节点须披露 + 错误流 publish-before-assign |
| 失败重试 | `retry` | `retry` / `errorflow` | max_retries∈[0,10] + timeout≥1 + 写操作须幂等（key/轮询去重）+ 死信或告警；target 非空 + published 且 Error Trigger 激活 + 按目标挂载 + 有恢复路径 |
| AI工作流 | `aiworkflow` | `aiagent` / `model` | AI 节点类型白名单 + 显式 model + purpose + io_record/evaluation + 高危须 permission；锚点 agent/workflow + 显式模型 + agent 锚点须 tools 与 guardrails |
| 审计 | `audit` | `audit` / `runlog` | 证据字段齐备（trigger/input/execution/output/operator）+ 状态白名单 + 失败可追溯；执行状态白名单 + 证据齐备 + 成功率实算 |

共 **8 技能 / 16 动作**（16 个门禁）。

## 协作契约

- **inputs**：`rules` + `fields`
- **outputs**：`workflow` + `audit_log`
- 意图路由（`agent.py run --task`）：集成/连接/节点 → integration/workflow；凭据/密钥 → integration/credential；
  webhook/事件/回调 → webhook/webhook；事件路由/重放 → webhook/event；字段/映射/主键 → mapping/mapping；
  数据表/列/schema → mapping/table；定时/调度/cron → schedule/schedule；批处理/批次/补偿 → schedule/batch；
  审批/授权/HITL → approval/approval；发布/上线/部署 → approval/publish；重试/幂等/死信 → retry/retry；
  错误工作流/恢复手册 → retry/errorflow；AI 节点/模型 → aiworkflow/aiagent；锚点/anchor → aiworkflow/model；
  审计/轨迹 → audit/audit；执行统计/成功率 → audit/runlog；兜底 → `integration/workflow`。

## 运行

```bash
python agent.py manifest                                   # 契约 + 8 技能清单
python agent.py demo                                       # 生成示例自动化工件
python agent.py integration workflow --input examples/workflow.json
python agent.py webhook event --input examples/event.json
python agent.py mapping table --input examples/table.json
python agent.py schedule schedule --input examples/schedule.json
python agent.py approval publish --input examples/publish.json
python agent.py retry retry --input examples/retry.json
python agent.py aiworkflow model --input examples/model.json
python agent.py audit audit --input examples/audit.json
python agent.py harness publish --input examples/publish.json   # 确定性门禁
python agent.py contract list
python agent.py case list
python verify_loop.py                                       # 32 行闭环矩阵
python run_tests.py                                         # 一键验收，期望 ALL GREEN
```

## 边界（角色分工与红线）

- **业务规则 / 财务结论 / 税务结论 / 合同效力 / 法律意见**归业务角色与 R03；
  **产品设计**归 R07；**数据分析结论**归 R06；**供应商/库存/履约口径**归 R15。
- 本角色只产出**自动化工件**（工作流结构、凭据选择、Webhook/Hook 流程、事件路由、字段映射表、
  Data Table、调度/批处理、审批节点、发布门禁、重试/错误流、AI 节点/模型选择、审计轨迹、执行日志），
  不替业务角色发明规则、不下业务结论、不实现业务逻辑本身。
- **红线（不可越）**：
  1. **不替业务角色发明规则**——业务字段、枚举、边界由业务角色的已确认输入（`rules` / `fields`）决定，
     本角色只做组装与校验。
  2. **不在无审批情况下自动执行高风险动作**——发布 / 退款 / 扣款 / 删除 / 合同签署 / 发送 PII 等
     必须有 approver / authorization，一律产出**请求工件 + handoff 声明**。
  3. **不把凭据写入技能文档或公开工作流**——`api_key` / `secret` / `token` / `password` / `bearer` /
     `private_key` 等绝不能以明文出现在工作流 source、参数或任何输出中。

## Honest capability status and safe local execution

`manifest` labels workflow validation as `simulated` and actual n8n invocation as `blocked`. `python agent.py local --input <workflow.json>` checks schema/mapping/retry policy in dry-run mode, reports zero external calls, and never calls n8n. Missing credentials or unreachable systems are blocked.


- 干净数据 → `ok=true` / exit 0；脏数据（悬空引用 / 明文密钥 / 形状错配 / 字段名不合规 /
  保留名占用 / 调度越界 / 失败无补偿 / 高危无授权 / 未验证未披露 / 写操作无幂等 / 错误流未发布 /
  缺模型 / agent 无护栏 / 证据缺字段 / 状态越界）→ `ok=false` / exit 1。
- 对抗评审五检查：`contract` / `unauthorized_exec` / `credential_leak` / `scope_invent` /
  `concrete_artifact`；失败按类别 route 回 writer（擅自执行 / 凭据泄露 / 越界发明规则）或
  controller（无工件 / 无价值），类别为 `unauthorized_exec` / `credential_leak` /
  `scope_invent` / `artifact_not_concrete` / `no_report_value`。
- 阈值全部外置在 `experience/thresholds.json`，改口径不改代码；案例可再覆盖
  （如 `unapproved-publish` 补充审批等级收紧、`credential-leak` 补充密钥禁词子集）。
- Windows GBK 控制台：所有输出经 UTF-8 重配置，verify_loop 使用 `[OK]` / `[XX]` ASCII 标记。

## 踩坑记录（形态平移）

1. **harness 子命令名冲突**：审计技能的动作名 `runlog`（执行日志统计）与 harness 的可观测性子命令
   `runlog --n` 同名，argparse 会抛 `conflicting subparser`。解决办法：harness 里该门禁改名为
   `exec_log`，`runlog` 只保留为可观测性入口。
2. **红线词误伤自身结论**：`credential` 动作的 narrative 若写「明文密钥 N 个」，会被对抗评审的
   `credential_words` 命中而误报 `credential_leak`。改为「明文命中 N 个」。
3. **concrete_keys 必须覆盖全部输出键**：`runlog` 的 `execution_count` / `success_rate` 若不在
   `concrete_keys`，干净产出会被判 `artifact_not_concrete`。新增输出键时必须同步登记到
   `thresholds.json` 与 `_common` 默认值两处。
4. **审计证据判空要小心**：`input` / `output` 为空对象 `{}` 是 falsy，会被判「证据缺失」。fixtures
   里的审计记录必须给真实内容，否则干净数据也会 FAIL。

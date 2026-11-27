# R17 蛙智网 · 厚度自述（T11 / L2）

> 按升级方案 §5「五层可验收」与 §16「厚度包」逐项自述。只写可被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | `references/` 11 篇 / 约 40.5KB（`check_role_thickness --report` 可复核） |
| 来源 | n8n（workflow/debugging/error workflows）等公开仓口径 |
| 适用边界 | 每篇单列「适用边界」 |
| 误用说明 | 每篇单列误用反例，并对应本仓门禁 |

## 2. 生产层

`skills/` 9 个模块，覆盖集成、Webhook、字段映射、调度、审批、失败处理、
AI 工作流、审计与重试可靠性模型：

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `integration` | 工作流源码/凭据 | 节点/连接/触发器、明文密钥门禁 |
| 2 | `webhook` | 事件与路由 | 事件路由与死信声明 |
| 3 | `mapping` | 字段映射 | 类型与必填 |
| 4 | `schedule` | 调度配置 | 频率与窗口 |
| 5 | `approval` | 审批动作 | 审批点与发布门禁 |
| 6 | `retry` | 重试/错误流 | 上限/超时/幂等/死信/恢复 |
| 7 | `aiworkflow` | AI 节点 | 提示与工具约束 |
| 8 | `audit` | 执行轨迹/日志 | 六要素证据与失败可追溯 |
| 9 | `retry-model` | 成功率/尝试次数 | 最终成功率与期望尝试 |

黄金链：`integration.workflow → retry.retry → audit.runlog`；
`retry.errorflow → audit.audit → audit.runlog`。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 干净/脏夹具 | `examples/*.json`（32 个） | 每动作配对，脏件断言被拦 |
| 案例包 | `cases/`（18 个文件） | SOP 与经验 |
| 黄金成品 | `golden/automation-success.html`、`golden/automation-replay.html` | 含夹具 sha256 与 25 条门禁 |
| 阈值 | `experience/`、`AUTOMATION_SPEC.md` | 重试/审计口径外置 |

## 4. 门禁层

| 门禁 | 落点 | 失败后果 |
|---|---|---|
| 节点/连接/触发器完整 | `integration.workflow` → `workflow.*` | BLOCKER |
| 无明文密钥 | `integration.workflow/credential` → `no_secret` | BLOCKER |
| 重试上限 | `retry.retry` → `retry.max_retries` | BLOCKER |
| 写操作幂等 | `retry.retry` → `retry.idempotency` | BLOCKER |
| 死信/告警路径 | `retry.retry` → `retry.dead_letter` | BLOCKER |
| Error Trigger 已发布且按目标挂载 | `retry.errorflow` → `errorflow.published/per_target` | BLOCKER |
| 审计六要素 | `audit.audit` → `audit.*` | BLOCKER |
| 失败可追溯 | `audit.runlog` → `runlog.*` | BLOCKER |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 技能与契约 | `tests/test_skills.py`、`tests/test_contracts.py` | 覆盖全部动作 |
| 黄金成品 | `tests/test_thickness_samples.py::ThicknessSamples` | 2 份 |
| 误用反例 | `misuse/*.json` + 同测试 | 2 个（无界重试、死信丢失） |
| 端到端 | `run_tests.py` T01–T16 | 全绿 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r17-wazhiwang-automation/golden/build_golden.py`
- 产物：`automation-success.html`（13 条门禁，0 未过）、
  `automation-replay.html`（12 条门禁，0 未过）
- 命令：`python r17-wazhiwang-automation/run_tests.py`
- 结果：全绿（含厚度样本 T16）

## 7. 已知边界

- 只装配管道与校验结构，不发明业务规则、不硬编码凭据；
- 重放/发布生产流属高风险动作，必须人工决策；
- 死信与恢复路径必须显式声明，否则失败会静默丢失。

# R02 蛙排布 · 厚度自述（T12 Tier C：补机制）

> 按升级方案 §16「厚度包」与 §17.1 T12 逐项自述。只写能被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | 10 篇 / 35.8KB（排期 WBS、容量与委派、交接验收、复盘事故、流程 SOP、知识运营、项目群编排等） |
| 来源 | 每篇列公开方法来源（关键路径、Little 定律、SRE postmortem、SOP/控制点等）与适用边界 |
| 误用说明 | 每篇有「误用反例」表；对应门禁在 `harness.py` 与 `skills/s04_retro.py` |
| 能力卡 | `references/capabilities/`：handoff-acceptance、business-ops-analysis、lark |

## 2. 生产层

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1–7 | `skills/s01..s07` | WBS / 容量 / 交接包 / 事故 / SOP / 知识条目 / 项目群 | 21 个确定性动作 |
| 8 | `skills/s10_little.py`、`s11_queue.py` | 排队与负载 | Little 定律 / 队列 |
| 9 | `verify_loop.py` | 21 动作 | 契约 + 评审闭环矩阵 |
| 10 | **`workflow_engine.py`（T12 新增）** | policy + tasks | `workflow-run.json` + 2 份 HTML |

`workflow_engine.py` 实现工作流状态机：`pending → running → succeeded / failed → dead_letter`，
指数退避 `base·2^(n-1)` 封顶、幂等键去重、死信重放、依赖阻塞恢复。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 真实实测数字 | `golden/coo-process-retro.html` | 143 份副本 / 28,278 行 / 85.8% 重复（升级方案 §6.1） |
| 运行产物 | `golden/workflow-run.json` | 首轮 6 任务 + 重放，确定性可复算 |
| 两份黄金报告 | `golden/*.html` | 重试死信报告、流程复盘 |

## 4. 门禁层

| 错误码 | 判据 | 失败后果 |
|---|---|---|
| `W01_UNBOUNDED_RETRY` | `max_retries∈[1,10]` 且无 `retry_forever` | 拒绝执行工作流 |
| `W02_DEAD_LETTER_LOST` | 每个 failed/dead_letter 任务都在死信队列 | 拒绝执行 + 审计失败 |
| `W03_IDEMPOTENCY` | 幂等键非空且唯一 | 拒绝执行 |
| `W04_BACKOFF` | `backoff=exponential`、`base>0`、`max≥base` | 拒绝执行 |
| `W05_BLOCKED_DEPENDENCY` | 依赖已成功的任务不得停在 blocked | 审计失败（要求恢复） |

既有门禁：`harness.py` 21 项 + `review.py` 对抗评审。

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 机制单测（pytest） | `tests/test_mechanism.py` | 7 条（退避/策略/三态/幂等/阻塞/误用/HTML） |
| 角色端到端 | `run_tests.py` §16 | 8 条 |
| 黄金成品 | `golden/*.html` | 2 份 |
| 误用反例 | `misuse/*.json` | 2 份（无限重试 / 死信丢失） |
| 全量 | `python run_tests.py` | 115 项全过 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r02-wapaibu-coo/run_tests.py`
- 结果：通过 115 / 失败 0
- 机制：`python workflow_engine.py goldens` → 首轮 `failed`（1 条死信），重放 `replayed`（死信清零 + 阻塞恢复）
- 呈现：`python scripts/check_report_presentation.py r02-wapaibu-coo/golden/*.html` → 2/2 PASS

## 7. 已知边界

- 执行是确定性模拟：用 `attempts_fail` 表示「前 N 次失败」，不接真实下游；
- 退避只计算等待值，不做真实 sleep；封顶值来自 policy；
- 死信重放一次只跑死信任务及其下游阻塞，不重跑已成功任务；
- 幂等键唯一性只在单次 `run_workflow` 内校验，跨运行去重依赖外部存储。

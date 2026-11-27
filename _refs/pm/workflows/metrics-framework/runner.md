# 指标与数据验证 Runner

## 1. Runner 定位

这是人工可执行 runner，不是自动取数脚本。它规定产品管理 person 如何为需求、PRD 或 MVP 生成指标框架。

当前版本不调用数据库、不运行模型、不渲染图表，也不自动触发其他 agent。

## 1.1 重任务门禁

指标框架报告属于重任务。先读 `workflows/HEAVY_TASK_RAG_RULES.md`，执行 `workflows/experience-rag/workflow.yaml` 的 `heavy-task` 模式；如果决策问题、数据状态或目标用户不清，先复用入口 `experience_brief`，关键维度变化才执行 `pre-question` L1。

## 2. 启动信号

- “这个需求怎么衡量成功”
- “PRD 里指标怎么写”
- “怎么用数据验证”
- “Go/No-Go 怎么定”
- “没有数据怎么判断”

## 3. 执行步骤

| 步骤 | 动作 | 输入 | 输出 | 门禁 |
| --- | --- | --- | --- | --- |
| 1 | 读取 workflow 配置 | `workflow.yaml` | 运行边界 | 明确不做真实取数 |
| 2 | 读取 prompt 和质量指南 | `prompts/current.md`、`references/metrics-framework-guide.md` | 写作规则 | 版本号记录到工作日志 |
| 3 | 明确决策问题 | 需求/PRD/MVP | 决策问题 | 通过 decision_gate |
| 4 | 定义指标树 | 决策问题 | 北极星、输入、护栏指标 | 通过 balance_gate |
| 5 | 写指标口径 | 指标树 | 指标字典 | 通过 definition_gate |
| 6 | 判断数据可得性 | 指标字典、上下文 | 数据源与缺口 | 通过 data_gate |
| 7 | 写 Go/No-Go | 指标和数据状态 | 判断标准 | 通过 go_no_go_gate |
| 8 | 生成可选审查提醒 | `review_hints.yaml` | 下一步提醒 | 不写成本地路径 |
| 9 | 输出确认版 | 框架报告 | 人话报告 | 先讲怎么决策 |

## 4. 文件管理

| 文件 | 作用 |
| --- | --- |
| `workflow.yaml` | 工作流元信息、输入输出、门禁 |
| `topology.md` | 拓扑图、节点备注、输出包 |
| `references/metrics-framework-guide.md` | 指标框架质量规则 |
| `review_hints.yaml` | 可选审查提醒 |
| `prompts/current.md` | 当前稳定 prompt |
| `prompts/CHANGELOG.md` | prompt 版本变更 |
| `runner.md` | 本执行手册 |

## 5. 回退方式

| 失败点 | 回退 |
| --- | --- |
| 决策不清 | 回 requirement-report 或只问 1 个关键问题 |
| 需求不成立 | 不写指标，先回需求分析 |
| 数据源不清 | 标为待补，不伪造口径 |
| 目标值没有基线 | 先写基线待补和相对判断 |
| 用户要真实分析 | 输出 PM 本地分析 brief，给可选数据分析能力提醒 |

## 6. 完成标准

- 有一句话结论。
- 有指标树。
- 每个关键指标有口径、数据源和缺口。
- 有 Go/No-Go 标准。
- 有数据误判风险和护栏指标。
- 有下一步建议。

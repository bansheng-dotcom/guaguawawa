# PM 总控与轻量反应 Runner

## 1. Runner 定位

这是产品管理 person 的入口 runner，不直接生产重报告。它负责把用户输入路由到正确 workflow。

## 2. 执行步骤

| 步骤 | 动作 | 输出 |
| --- | --- | --- |
| 1 | 读用户输入、约束和当前项目上下文 | 任务理解 |
| 2 | 判断缺口是否影响方向 | 追问候选或默认假设 |
| 3 | 如果准备追问，先走 `workflows/experience-rag/workflow.yaml` 的 `pre-question` L1 Gate | 发问依据 |
| 4 | 合并问题：能默认推进就不问；必须问时最多问 1 个关键问题 | 关键追问/默认假设 |
| 5 | 判断任务重量：提问/质问不算重，报告/文档/需求包算重 | 强度判断 |
| 6 | 重任务先读 `workflows/HEAVY_TASK_RAG_RULES.md`，并走 `experience-rag` 的 `heavy-task` L2，生成 `experience_brief` | 重思考中间包 |
| 7 | 非重但涉及产品判断、纠错、用户偏好或持续项目时，走 `experience-rag` 的 `normal` L1；强命中才升级 L2 | applied_rules |
| 8 | 选择 workflow | workflow id |
| 9 | 给出最小产物或进入下游 | 下一步动作 |

## 3. 文件管理

| 文件 | 用途 |
| --- | --- |
| `references/light-reaction-guide.md` | 轻量反应和少问规则 |
| `references/pm-routing-guide.md` | 路由表和工作流选择 |
| `../experience-rag/workflow.yaml` | RAG Gate、经验检索与沉淀入口 |
| `../HEAVY_TASK_RAG_RULES.md` | 报告/文档类重任务的 RAG 与重思考门禁 |
| `prompts/current.md` | 当前执行提示词 |

## 4. 回退方式

- 如果路由冲突，回到用户真正问题和最小产物。
- 如果连续追问仍不清楚，先写默认假设和风险，不继续问长问题。
- 如果用户要求正式开发输入，转 `workflows/demand-management/workflow.yaml`。

## 5. 完成标准

- 用户知道当前理解是否正确。
- 已选择一个 workflow 或直接给出短答。
- 未确认假设没有写成事实。

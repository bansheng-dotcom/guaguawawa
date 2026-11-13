# 需求管理与协作复核 Runner

## 1. Runner 定位

这是正式开发输入 runner。它不负责早期想法澄清，也不替专业能力做最终实现判断。

## 1.1 重任务门禁

正式需求包和开发输入属于重任务。先读 `workflows/HEAVY_TASK_RAG_RULES.md`，执行 `workflows/experience-rag/workflow.yaml` 的 `heavy-task` 模式；如果需求确认状态、范围或下游责任不清，先复用入口 `experience_brief`，关键维度变化才执行 `pre-question` L1。

## 2. 执行步骤

| 步骤 | 动作 | 输出 |
| --- | --- | --- |
| 1 | 确认用户已要求进入正式执行 | 启动条件 |
| 2 | 创建或更新需求编号和需求卡 | 需求卡 |
| 3 | 回链 PRD、来源和范围 | 可追溯需求 |
| 4 | 拆下游文件和验收引用 | 执行包 |
| 5 | 记录协作能力复核状态 | 复核表 |
| 6 | 写工作日志和给用户的确认版 | 汇报 |

## 3. 文件管理

| 文件 | 用途 |
| --- | --- |
| `references/demand-management-guide.md` | 需求编号、下游文件、复核规则 |
| `references/prd-to-execution-guide.md` | PRD 转执行需求的拆解规则 |
| `templates/product-requirement-submit-template.md` | 需求卡模板 |
| `templates/collaboration-capability-review-template.md` | 协作能力复核记录模板 |

## 4. 回退方式

- 如果方向未确认，回到 `workflows/pm-thinking/workflow.yaml` 或 `workflows/requirement-report/workflow.yaml`。
- 如果 PRD 不够清楚，回到 `workflows/prd-report/workflow.yaml`。
- 如果下游复核不通过，先改需求卡，再改下游文件。

## 5. 完成标准

- 每个正式文件都能回链需求编号。
- 需求范围、不在范围和验收标准明确。
- 复核状态清楚，未复核内容只标草稿。

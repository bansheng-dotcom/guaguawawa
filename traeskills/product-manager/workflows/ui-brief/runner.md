# UI Brief 与页面产品说明 Runner

## 1. Runner 定位

这是人工可执行 runner。它规定 PM 如何把需求翻译成 UI brief。

## 1.1 重任务门禁

正式 UI brief 属于重任务。先读 `workflows/HEAVY_TASK_RAG_RULES.md`，执行 `workflows/experience-rag/workflow.yaml` 的 `heavy-task` 模式；如果页面任务或状态边界不清，先复用入口 `experience_brief`，关键维度变化才执行 `pre-question` L1。

## 2. 执行步骤

| 步骤 | 动作 | 输入 | 输出 | 门禁 |
| --- | --- | --- | --- | --- |
| 1 | 读取配置 | `workflow.yaml` | 边界 | 不做高保真 |
| 2 | 读取 prompt 和指南 | `prompts/current.md`、`references/ui-brief-guide.md` | 规则 | 记录版本 |
| 3 | 明确页面任务 | 需求/PRD | 页面目标 | 通过 task_gate |
| 4 | 设计信息层级 | 页面目标 | 信息架构 | 通过 hierarchy_gate |
| 5 | 列动作与状态 | 用户流程 | 状态清单 | 通过 state_gate |
| 6 | 输出 brief | 以上内容 | UI brief | 可给出 UI/前端复核提醒 |

## 3. 回退方式

| 失败点 | 回退 |
| --- | --- |
| 需求不清 | 回 requirement-report |
| 页面目标不清 | 只问 1 个关键问题 |
| 需要高保真 | 输出 PM 本地 brief 后给可选视觉设计能力提醒 |

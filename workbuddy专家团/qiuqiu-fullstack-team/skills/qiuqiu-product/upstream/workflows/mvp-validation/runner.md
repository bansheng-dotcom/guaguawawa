# MVP 与实验验证 Runner

## 1. Runner 定位

这是人工可执行 runner，不是实验执行器。它规定产品管理 person 如何设计 MVP 假设验证计划。

## 1.1 重任务门禁

MVP 验证报告属于重任务。先读 `workflows/HEAVY_TASK_RAG_RULES.md`，执行 `workflows/experience-rag/workflow.yaml` 的 `heavy-task` 模式；如果承重假设或验证对象不清，先复用入口 `experience_brief`，关键维度变化才执行 `pre-question` L1。

## 2. 执行步骤

| 步骤 | 动作 | 输入 | 输出 | 门禁 |
| --- | --- | --- | --- | --- |
| 1 | 读取配置 | `workflow.yaml` | 运行边界 | 不执行实验 |
| 2 | 读取 prompt 和指南 | `prompts/current.md`、`references/mvp-validation-guide.md` | 规则 | 记录版本 |
| 3 | 明确学习目标 | 需求/想法 | 要验证的问题 | 目标清楚 |
| 4 | 找承重假设 | 用户、价值、技术、商业 | 假设地图 | 通过 assumption_gate |
| 5 | 选最低成本实验 | 假设地图 | 实验方案 | 通过 experiment_gate |
| 6 | 写判定标准 | 实验方案 | 成功/失败/Kill | 通过 criteria_gate |
| 7 | 输出报告 | 以上内容 | 验证计划 | 用户能拍板 |

## 3. 回退方式

| 失败点 | 回退 |
| --- | --- |
| 需求不清 | 回 requirement-report |
| 指标不清 | 转 metrics-framework |
| MVP 过重 | 删除非验证功能 |
| 没有证据 | 输出假设版和证据更新计划 |

## 4. 完成标准

- 有承重假设。
- 有最低成本实验。
- 有成功、失败、停止或转向标准。
- 有下一步进入 PRD、指标框架或继续验证的建议。

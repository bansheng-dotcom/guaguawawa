# 产品战略与机会树 Runner

## 1. Runner 定位

这是人工可执行 runner。它规定 PM 如何把阶段目标和多个机会整理成战略判断。

## 1.1 重任务门禁

产品战略报告属于重任务。先读 `workflows/HEAVY_TASK_RAG_RULES.md`，执行 `workflows/experience-rag/workflow.yaml` 的 `heavy-task` 模式；如果阶段目标、用户分群或取舍边界不清，先复用入口 `experience_brief`，关键维度变化才执行 `pre-question` L1。

## 2. 执行步骤

| 步骤 | 动作 | 输入 | 输出 | 门禁 |
| --- | --- | --- | --- | --- |
| 1 | 读取配置 | `workflow.yaml` | 边界 | 明确不替代公司战略 |
| 2 | 读取 prompt 和指南 | `prompts/current.md`、`references/product-strategy-guide.md` | 规则 | 记录版本 |
| 3 | 明确阶段目标 | 业务/产品目标 | 阶段任务 | 通过 stage_gate |
| 4 | 定义用户分群 | 用户、场景、任务 | 分群 | 通过 user_gate |
| 5 | 建机会树 | 需求/反馈/机会 | Opportunity Solution Tree | 通过 opportunity_gate |
| 6 | 做取舍 | 机会树、约束 | 做/不做 | 通过 tradeoff_gate |
| 7 | 输出报告 | 以上内容 | 战略报告 | 用户能拍板 |

## 3. 回退方式

| 失败点 | 回退 |
| --- | --- |
| 单个需求问题 | 转 requirement-report |
| 方案已确认要写文档 | 转 prd-report |
| 指标缺失 | 转 metrics-framework |
| 取舍依据不足 | 输出待补证据 |

# 竞品分析报告 Runner

## 1. Runner 定位

这是人工可执行 runner。它规定 PM 如何做决策导向的竞品分析。

## 1.1 重任务门禁

竞品分析报告属于重任务。先读 `workflows/HEAVY_TASK_RAG_RULES.md`，执行 `workflows/experience-rag/workflow.yaml` 的 `heavy-task` 模式；如果决策问题、竞品范围或维度不清，先复用入口 `experience_brief`，关键维度变化才执行 `pre-question` L1。

## 2. 执行步骤

| 步骤 | 动作 | 输入 | 输出 | 门禁 |
| --- | --- | --- | --- | --- |
| 1 | 读取配置 | `workflow.yaml` | 边界 | 不做泛泛资料收集 |
| 2 | 读取 prompt 和指南 | `prompts/current.md`、`references/competitive-analysis-guide.md` | 规则 | 记录版本 |
| 3 | 明确决策问题 | 用户目标 | 比较目的 | 通过 decision_gate |
| 4 | 定义竞品和维度 | 产品上下文 | 对照框架 | 维度一致 |
| 5 | 收集事实 | 来源材料/现查 | 事实表 | 通过 source_gate |
| 6 | 提炼洞察 | 对照矩阵 | 启发、风险、取舍 | 通过 implication_gate |
| 7 | 输出报告 | 以上内容 | 竞品报告 | 用户能拍板 |

## 3. 回退方式

| 失败点 | 回退 |
| --- | --- |
| 决策问题不清 | 只问 1 个关键问题 |
| 资料时效不稳 | 现查并标日期 |
| 来源不足 | 标为假设或待补来源 |
| 用户要转需求 | 转 requirement-report 或 prd-report |

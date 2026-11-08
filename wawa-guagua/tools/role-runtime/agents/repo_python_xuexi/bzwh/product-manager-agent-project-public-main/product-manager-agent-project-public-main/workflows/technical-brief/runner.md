# 技术翻译报告 Runner

## 1. Runner 定位

这是人工可执行 runner。它规定 PM 如何把技术内容翻译成用户和技术角色都能理解的 brief。

## 1.1 重任务门禁

技术翻译报告属于重任务。先读 `workflows/HEAVY_TASK_RAG_RULES.md`，执行 `workflows/experience-rag/workflow.yaml` 的 `heavy-task` 模式；如果读者、决策点或技术对象不清，先复用入口 `experience_brief`，关键维度变化才执行 `pre-question` L1。

## 2. 执行步骤

| 步骤 | 动作 | 输入 | 输出 | 门禁 |
| --- | --- | --- | --- | --- |
| 1 | 读取配置 | `workflow.yaml` | 边界 | 不直接实现 |
| 2 | 读取 prompt 和指南 | `prompts/current.md`、`references/technical-brief-guide.md` | 规则 | 记录版本 |
| 3 | 明确读者和决策 | 用户目标 | 报告目的 | 通过 reader_gate |
| 4 | 写用户影响 | 需求/方案 | 用户影响摘要 | 人话优先 |
| 5 | 拆技术影响 | 文件/方案 | 影响矩阵 | 通过 impact_gate |
| 6 | 写数据权限失败 | 技术上下文 | 数据与兜底 | 通过 data_gate/fallback_gate |
| 7 | 输出报告 | 以上内容 | 技术 brief | 可拍板或接手 |

## 3. 回退方式

| 失败点 | 回退 |
| --- | --- |
| 需求不清 | 回 prd-report 或 requirement-report |
| 架构争议 | 输出 PM 本地 brief 后给可选架构能力提醒 |
| 缺技术事实 | 标为待技术确认，不编造 |
| 用户听不懂 | 改成人话影响版 |

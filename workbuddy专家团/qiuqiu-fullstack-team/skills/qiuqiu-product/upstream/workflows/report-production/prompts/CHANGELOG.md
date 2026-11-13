# PM 报告生产 Prompt Changelog

## 0.4 - 2026-07-01

- 将报告生产边界改为本地轻量写作、UI、数据分析能力优先；超出部分只给可选专业能力提醒。

## 0.3 - 2026-07-01

- 将重任务入口调整为 `heavy-task` L2 生成 `experience_brief`。
- 内部追问默认复用入口 `experience_brief`，只有项目、workflow、产物或决策点变化才执行 `pre-question` L1。

## 0.2 - 2026-07-01

- 报告生产默认按重任务处理。
- 写作前接入 `HEAVY_TASK_RAG_RULES.md` 与 `experience-rag: heavy-task`；报告前追问先走 `pre-question`。

## 0.1 - 2026-07-01

- 将原 PM 报告生产流程目录化。
- 明确报告目标、证据、视觉和外部能力边界。

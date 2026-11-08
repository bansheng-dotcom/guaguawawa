# MVP 与实验验证 Prompt Changelog

## 0.3 - 2026-07-01

- 将重任务入口调整为 `heavy-task` L2 生成 `experience_brief`。
- 内部追问默认复用入口 `experience_brief`，只有项目、workflow、产物或决策点变化才执行 `pre-question` L1。

## 0.2 - 2026-07-01

- MVP 验证报告按重任务处理。
- 写作前接入 `HEAVY_TASK_RAG_RULES.md` 与 `experience-rag: heavy-task`；承重假设或验证对象追问前先走 `pre-question`。

## 0.1 - 2026-06-30

- 建立 `mvp-validation` 首版 workflow。
- 明确 MVP 是验证核心假设，不是缩小版完整产品。
- 增加承重假设、最低成本实验、成功/失败/Kill 标准。

# 产品战略与机会树 Prompt Changelog

## 0.3 - 2026-07-01

- 将重任务入口调整为 `heavy-task` L2 生成 `experience_brief`。
- 内部追问默认复用入口 `experience_brief`，只有项目、workflow、产物或决策点变化才执行 `pre-question` L1。

## 0.2 - 2026-07-01

- 产品战略报告按重任务处理。
- 写作前接入 `HEAVY_TASK_RAG_RULES.md` 与 `experience-rag: heavy-task`；阶段目标、用户分群或取舍边界追问前先走 `pre-question`。

## 0.1 - 2026-06-30

- 建立 `product-strategy` 首版 workflow。
- 定义阶段目标、用户分群、机会树、战略画布和取舍门禁。

# 需求管理与协作审核 Prompt Changelog

## 0.3 - 2026-07-01

- 将重任务入口调整为 `heavy-task` L2 生成 `experience_brief`。
- 内部追问默认复用入口 `experience_brief`，只有项目、workflow、产物或决策点变化才执行 `pre-question` L1。

## 0.2 - 2026-07-01

- 正式需求包和开发输入按重任务处理。
- 写作前接入 `HEAVY_TASK_RAG_RULES.md` 与 `experience-rag: heavy-task`；需求确认、范围或下游责任追问前先走 `pre-question`。

## 0.1 - 2026-07-01

- 合并原需求管理与协作审核流程、PRD 到执行需求融合流程。
- 将需求卡和协作复核模板纳入本 workflow。

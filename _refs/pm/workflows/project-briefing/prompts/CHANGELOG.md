# 项目理解与汇报 Prompt Changelog

## 0.3 - 2026-07-01

- 将重任务入口调整为 `heavy-task` L2 生成 `experience_brief`。
- 内部追问默认复用入口 `experience_brief`，只有项目、workflow、产物或决策点变化才执行 `pre-question` L1。

## 0.2 - 2026-07-01

- 项目汇报按重任务处理。
- 写作前接入 `HEAVY_TASK_RAG_RULES.md` 与 `experience-rag: heavy-task`；补事实或拍板追问前先走 `pre-question`。

## 0.1 - 2026-07-01

- 将原项目理解与汇报流程目录化。
- 接入 `user/`、人感汇报、选项利弊和归档规则。

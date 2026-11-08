# 技术翻译报告 Prompt Changelog

## 0.4 - 2026-07-01

- 将架构和实现边界改为“PM 本地 brief + 可选专业能力提醒”，不再写成固定角色依赖。

## 0.3 - 2026-07-01

- 将重任务入口调整为 `heavy-task` L2 生成 `experience_brief`。
- 内部追问默认复用入口 `experience_brief`，只有项目、workflow、产物或决策点变化才执行 `pre-question` L1。

## 0.2 - 2026-07-01

- 技术翻译报告按重任务处理。
- 写作前接入 `HEAVY_TASK_RAG_RULES.md` 与 `experience-rag: heavy-task`；读者、决策点或技术对象追问前先走 `pre-question`。

## 0.1 - 2026-06-30

- 建立 `technical-brief` 首版 workflow。
- 定义用户影响、前端影响、后端影响、Agent 影响、数据权限和失败兜底。

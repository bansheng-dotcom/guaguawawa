# UI Brief Prompt Changelog

## 0.4 - 2026-07-01

- 将高保真边界改为“PM 本地 brief + 可选视觉设计能力提醒”，不再写成固定 UI 角色依赖。

## 0.3 - 2026-07-01

- 将重任务入口调整为 `heavy-task` L2 生成 `experience_brief`。
- 内部追问默认复用入口 `experience_brief`，只有项目、workflow、产物或决策点变化才执行 `pre-question` L1。

## 0.2 - 2026-07-01

- 正式 UI brief 按重任务处理。
- 写作前接入 `HEAVY_TASK_RAG_RULES.md` 与 `experience-rag: heavy-task`；页面任务或状态边界追问前先走 `pre-question`。

## 0.1 - 2026-06-30

- 建立 `ui-brief` 首版 workflow。
- 定义页面目标、信息架构、用户动作、状态清单和 UI/前端审查重点。

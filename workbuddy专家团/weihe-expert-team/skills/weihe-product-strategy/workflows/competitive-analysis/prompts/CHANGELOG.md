# 竞品分析报告 Prompt Changelog

## 0.3 - 2026-07-01

- 将重任务入口调整为 `heavy-task` L2 生成 `experience_brief`。
- 内部追问默认复用入口 `experience_brief`，只有项目、workflow、产物或决策点变化才执行 `pre-question` L1。

## 0.2 - 2026-07-01

- 竞品分析报告按重任务处理。
- 写作前接入 `HEAVY_TASK_RAG_RULES.md` 与 `experience-rag: heavy-task`；追问决策、范围或维度前先走 `pre-question`。

## 0.1 - 2026-06-30

- 建立 `competitive-analysis` 首版 workflow。
- 明确竞品分析服务产品决策，不做泛泛资料收集。
- 增加来源、日期、对照矩阵、差异化和取舍门禁。

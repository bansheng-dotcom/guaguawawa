# 指标与数据验证 Prompt Changelog

## 0.4 - 2026-07-01

- 将真实取数和数据分析边界改为“PM 本地分析 brief + 可选数据分析能力提醒”，不再写成固定 agent 依赖。

## 0.3 - 2026-07-01

- 将重任务入口调整为 `heavy-task` L2 生成 `experience_brief`。
- 内部追问默认复用入口 `experience_brief`，只有项目、workflow、产物或决策点变化才执行 `pre-question` L1。

## 0.2 - 2026-07-01

- 指标框架报告按重任务处理。
- 写作前接入 `HEAVY_TASK_RAG_RULES.md` 与 `experience-rag: heavy-task`；关键追问前先走 `pre-question`。

## 0.1 - 2026-06-30

- 建立 `metrics-framework` 首版 workflow。
- 明确它是 P0 开发前指标门禁，不负责真实取数。
- 定义北极星指标、输入指标、护栏指标、指标字典、数据缺口和 Go/No-Go 标准。
- 保持可选审查提醒，不自动触发其他 agent。

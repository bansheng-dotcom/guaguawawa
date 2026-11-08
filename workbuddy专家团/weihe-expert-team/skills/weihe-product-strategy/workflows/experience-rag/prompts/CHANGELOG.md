# 经验 RAG 与沉淀 Prompt Changelog

## 0.3 - 2026-07-01

- 将“必须调用 RAG”改成“必须经过 RAG Gate”，先判断再决定是否打开经验卡。
- 明确 `pre-question` 默认 L1，不读取大量经验卡；`heavy-task` 才允许 L2 读取 3-5 条经验卡。
- 增加 `experience_brief` 复用规则：同一重任务内部追问默认复用，只有项目、workflow、产物或决策点变化才重新 Gate。

## 0.2 - 2026-07-01

- 增加 `pre-question`、`heavy-task`、`normal` 三种模式。
- 明确发问前输出 0-1 个问题建议，重任务入口输出重思考约束。

## 0.1 - 2026-07-01

- 新增 experience RAG 检索、适用判断和经验写入流程。

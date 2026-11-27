# 验收与测试场景 Prompt Changelog

## 0.3 - 2026-07-01

- 将重任务入口调整为 `heavy-task` L2 生成 `experience_brief`。
- 内部追问默认复用入口 `experience_brief`，只有项目、workflow、产物或决策点变化才执行 `pre-question` L1。

## 0.2 - 2026-07-01

- 正式验收文档按重任务处理。
- 写作前接入 `HEAVY_TASK_RAG_RULES.md` 与 `experience-rag: heavy-task`；范围、主路径或失败态追问前先走 `pre-question`。

## 0.1 - 2026-06-30

- 建立 `acceptance-test` 首版 workflow。
- 明确它是 P0 开发前验收门禁，不负责测试执行。
- 定义 Given/When/Then、测试场景表、边界状态、失败态和回归提示。
- 保持可选审查提醒，不自动触发其他 agent。

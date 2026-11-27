# 需求分析报告 Prompt Changelog

## 0.4 - 2026-07-01

- 将重任务入口调整为 `heavy-task` L2 生成 `experience_brief`。
- 内部追问默认复用入口 `experience_brief`，只有项目、workflow、产物或决策点变化才执行 `pre-question` L1。

## 0.3 - 2026-07-01

- 完整需求分析报告和需求文档按重任务处理。
- 写报告前接入 `HEAVY_TASK_RAG_RULES.md` 与 `experience-rag: heavy-task`；内部追问先走 `pre-question`。

## 0.2 - 2026-06-30

- 在需求分析报告入口增加轻量 intake 与数据门禁。
- 明确先判断数据状态、需求细节状态和本轮报告深度，再进入完整分析。
- 增加无数据可行性规则：低风险探索可输出假设版，高风险决策先补证据。
- 增加轻量 grill 规则：只在方向性缺口存在时问 1 个关键问题。

## 0.1 - 2026-06-30

- 建立 `requirement-report` 首版 workflow。
- 明确报告目的：判断需求是否成立、强度如何、优先级如何、下一步是否进入 PRD。
- 融合腾讯产品法：真正问题、需求成立、产品强度、用户场景、MVP 最小验证、战略取舍。
- 融合 pm-skills：feature request triage、analyze-feature-requests、discover、identify assumptions、prioritize-features。
- 保持和 `prd-report` 一致的边界：不自动触发其他 agent，只给可选审查提醒。

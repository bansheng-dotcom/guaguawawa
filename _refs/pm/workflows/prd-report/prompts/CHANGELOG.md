# PRD 报告工作流 Prompt Changelog

## 0.5 - 2026-07-01

- 将重任务入口调整为 `heavy-task` L2 生成 `experience_brief`。
- 内部追问默认复用入口 `experience_brief`，只有项目、workflow、产物或决策点变化才执行 `pre-question` L1。

## 0.4 - 2026-07-01

- PRD 写作前接入报告/文档类重任务门禁。
- 要求先执行 `experience-rag: heavy-task`，内部追问先执行 `pre-question`。

## 0.3 - 2026-06-30

- 新增 `references/prd-writing-guide.md`，融合腾讯产品法、pm-skills 和 `CP-PRD-OmniReport.md` 样例的 PRD 写作规则。
- 在 prompt 中加入产品判断摘要：真正问题、用户/JTBD、场景、产品强度、MVP 假设、指标和阶段取舍。
- 增加轻量/标准/重型 PRD 的裁剪规则，避免所有需求都写成超长文档。
- 增加承重假设红队要求：Fails if、本周证据、Kill criterion、Cheapest test。
- 强化指标规则：缺少基线或数据源时必须标“待补”，不能伪造成已验证结论。

## 0.2 - 2026-06-30

- 将 `prd-report` 收缩为 PRD 报告写作流程，不再把下游 agent 审核放进主链路。
- 将 `subagents.yaml` 改为 `review_hints.yaml`，只保留可选审查提醒，不写死本地 agent 路径。
- 输出结构改为 PRD 报告骨架、PRD 草稿、验收标准、风险与未决点、可选审查提醒、用户确认问题。
- 正式开发提交改为后续进入 `workflows/demand-management/workflow.yaml`，不在本 prompt 内自动触发。

## 0.1 - 2026-06-30

- 建立 PRD 报告工作流首版 prompt。
- 明确 PM 是总控，不替代前端、后端、UI、Agent、测试和架构。
- 固定输出结构：能否进入 PRD、需求卡草稿、PRD 草稿、下游 brief、协作复核计划、用户确认问题。
- 增加 AI/自动化/权限/后台任务的人工兜底和审计要求。

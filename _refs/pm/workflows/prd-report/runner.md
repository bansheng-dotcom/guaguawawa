# PRD 报告工作流 Runner

## 1. Runner 定位

这是人工可执行 runner，不是自动脚本。它规定产品管理 person 每次运行 `prd-report` 时的报告写作顺序、门禁、文件和回退方式。

若未来需要确定性校验器，再新增 `harness/` 或脚本；当前版本不调用 API、不运行模型、不写隐藏状态，也不自动触发其他 agent。

## 2. 启动命令

自然语言触发：

- “整理需求 / 写 PRD”
- “把这个想法变成开发输入”
- “生成 PRD 报告”
- “这个功能怎么做，整理成文档”

前置要求：

1. 先走 `workflows/controller/workflow.yaml`。
2. 先读 `workflows/HEAVY_TASK_RAG_RULES.md`，并执行 `workflows/experience-rag/workflow.yaml` 的 `heavy-task` 模式。
3. 若缺口影响方向，先复用入口 `experience_brief`；关键维度变化才执行 `experience-rag` 的 `pre-question` L1，再走 `workflows/pm-thinking/workflow.yaml`。
4. 确认进入 `prd-report` 后，再执行本 runner。

## 3. 执行步骤

| 步骤 | 动作 | 输入 | 输出 | 门禁 |
| --- | --- | --- | --- | --- |
| 1 | 读取 workflow 配置 | `workflow.yaml` | 运行边界 | 明确状态为 draft/active |
| 2 | 读取 prompt 和写作指南 | `prompts/current.md`、`references/prd-writing-guide.md` | 本次写作规则 | 版本号记录到工作日志 |
| 3 | 建上下文 | 用户原话、项目文件 | 上下文摘要 | 不靠聊天记忆猜事实 |
| 4 | 判断能否进入 PRD | 上下文摘要 | 通过/回质问 | 通过 G1 |
| 5 | 写产品判断摘要 | 上下文、写作指南 | 真实问题、用户/JTBD、价值、指标、MVP 假设 | 通过问题/价值/指标门禁 |
| 6 | 写 PRD 报告骨架 | 产品判断摘要、模板 | 报告目录 | 按轻量/标准/重型裁剪 |
| 7 | 写 PRD 草稿 | 报告骨架、PRD 模板 | PRD 报告草稿 | 人话 + 机器说明 |
| 8 | 补验收、风险和承重假设 | PRD 草稿 | 验收标准、风险、最低成本验证 | 动作、结果、状态变化清楚 |
| 9 | 生成可选审查提醒 | `review_hints.yaml` | 下一步提醒 | 只提醒角色类型，不写死本地路径 |
| 10 | 给用户确认版 | PRD 和提醒 | 人话报告 | 先讲结论和影响 |
| 11 | 建议后续 workflow | 用户确认状态 | 下一步 | 需要开发时转需求管理与协作复核 |

## 4. 文件管理

| 文件 | 作用 |
| --- | --- |
| `workflow.yaml` | 工作流元信息、输入输出、门禁 |
| `topology.md` | 拓扑图、节点备注、门禁说明 |
| `references/prd-writing-guide.md` | 腾讯产品法、pm-skills 和样例 PRD 融合后的写作门禁 |
| `review_hints.yaml` | 可选审查提醒，不是触发图 |
| `prompts/current.md` | 当前稳定 prompt |
| `prompts/CHANGELOG.md` | prompt 版本变更 |
| `runner.md` | 本执行手册 |

## 5. 回退方式

| 失败点 | 回退 |
| --- | --- |
| 真正问题不清 | 回 `workflows/pm-thinking/workflow.yaml` |
| 范围不清 | 只输出确认问题，不写 PRD |
| 价值主张不清 | 回产品判断摘要，补 Before/How/After/Alternatives |
| 指标不可验证 | 标“待补基线/数据源”，不能写成已验证目标 |
| PRD 报告不可读 | 回 PRD 草稿补问题、范围、验收、风险 |
| 用户要求进入开发 | 转 `workflows/demand-management/workflow.yaml`，不在本 runner 内自动触发 |
| 用户不认可方向 | 回到 `workflows/controller/workflow.yaml` 重新理解目标 |

## 6. 完成标准

`prd-report` 完成不等于开发可开始。完成标准是：

- 有 PRD 报告草稿。
- 需要时有需求卡草稿。
- 有产品判断摘要。
- 有验收标准、风险、承重假设和未决点。
- 有可选审查提醒。
- 有给用户确认的问题和下一步。

只有用户确认后，才判断是否进入 `workflows/demand-management/workflow.yaml`。正式开发提交仍然需要需求卡、下游文件和协作复核；那是后续 workflow，不是 PRD 报告写作的一部分。

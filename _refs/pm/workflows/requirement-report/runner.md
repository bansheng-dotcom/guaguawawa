# 需求分析报告 Runner

## 1. Runner 定位

这是人工可执行 runner，不是自动脚本。它规定产品管理 person 每次运行 `requirement-report` 时的顺序、门禁、文件和回退方式。

当前版本不调用 API、不运行模型、不写隐藏状态，也不自动触发其他 agent。

## 1.1 重任务门禁

如果本轮要产出完整需求分析报告或需求文档，先读 `workflows/HEAVY_TASK_RAG_RULES.md`，执行 `workflows/experience-rag/workflow.yaml` 的 `heavy-task` 模式；内部追问默认复用入口 `experience_brief`，关键维度变化才执行 `pre-question` L1。仅做提问、质问或轻量判断时不算重任务。

## 2. 启动信号

- “帮我分析这个需求”
- “这个想法值不值得做”
- “用户反馈怎么整理”
- “这些 feature requests 怎么排优先级”
- “这个需求强不强”
- “先别写 PRD，先判断需求”

## 3. 执行步骤

| 步骤 | 动作 | 输入 | 输出 | 门禁 |
| --- | --- | --- | --- | --- |
| 1 | 读取 workflow 配置 | `workflow.yaml` | 运行边界 | 明确不是 PRD |
| 2 | 读取 prompt、质量指南和入口门禁 | `prompts/current.md`、`references/requirement-report-guide.md`、`references/light-intake-and-data-gate.md` | 写作规则 | 版本号记录到工作日志 |
| 3 | 执行轻量 react | 用户原话、已知上下文 | 初始理解 | 用一句话说明“我先按这个理解推进” |
| 4 | 执行数据与细节门禁 | 初始理解、可用证据 | 数据状态、细节状态、路由结果 | 通过 intake_gate/data_gate/detail_gate |
| 5 | 判断本轮路径 | 路由结果 | 完整报告/假设版/补数据/只问 1 个问题 | 高风险无数据时不写确定结论 |
| 6 | 建立来源上下文 | 用户原话、反馈、项目文件 | 来源摘要 | 缺来源要标待补 |
| 7 | 拆表层诉求与真实问题 | 来源摘要 | 问题定义 | 不直接接受功能名 |
| 8 | 判断需求成立 | 问题定义 | 需要/行动/成本判断 | 通过 demand_gate |
| 9 | 评估产品强度 | 需求成立判断 | 体验、成本、新增成本 | 通过 strength_gate |
| 10 | 聚类机会或主题 | 单个想法/批量请求 | 机会树或主题表 | 优先问题，不优先功能 |
| 11 | 排优先级 | 机会/主题 | Act Now / Plan Next / Collect More Signal / Defer | 通过 priority_gate |
| 12 | 设计最低成本验证或证据更新计划 | 优先级结果、数据状态 | 验证计划/证据更新计划 | 通过 validation_gate |
| 13 | 生成可选审查提醒 | `review_hints.yaml` | 下一步提醒 | 不写成本地路径 |
| 14 | 输出给用户确认版 | 报告草稿 | 人话报告 | 先讲结论和下一步 |

## 4. 文件管理

| 文件 | 作用 |
| --- | --- |
| `workflow.yaml` | 工作流元信息、输入输出、门禁 |
| `topology.md` | 拓扑图、节点备注、输出包 |
| `references/requirement-report-guide.md` | 腾讯产品法与 pm-skills 融合后的需求分析规则 |
| `references/light-intake-and-data-gate.md` | 轻量 react、数据状态、细节缺口和无数据可行性判断 |
| `review_hints.yaml` | 可选审查提醒，不是触发图 |
| `prompts/current.md` | 当前稳定 prompt |
| `prompts/CHANGELOG.md` | prompt 版本变更 |
| `runner.md` | 本执行手册 |

## 5. 回退方式

| 失败点 | 回退 |
| --- | --- |
| 无数据但决策高风险 | 输出证据更新计划，不写确定需求结论 |
| 细节缺一个方向性事实 | 只问 1 个关键问题，并说明默认假设 |
| 没有来源 | 输出“待补来源”的轻量判断，不写确定结论 |
| 真正问题不清 | 只问 1 个关键问题 |
| 需求不成立 | 输出暂缓/拒绝理由，不进入 PRD |
| 优先级证据不足 | 转 Collect More Signal，给最低成本验证 |
| 用户确认要写 PRD | 转 `workflows/prd-report/workflow.yaml` |

## 6. 完成标准

- 有一句话结论。
- 有入口判断：初始理解、数据状态、细节状态、本轮路径。
- 有来源摘要和证据等级。
- 有表层诉求 vs 真实问题。
- 有需求成立和产品强度判断。
- 有优先级建议。
- 有最低成本验证或下一步 workflow。

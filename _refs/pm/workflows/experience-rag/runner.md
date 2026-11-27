# 经验 RAG 与沉淀 Runner

## 1. Runner 定位

这是经验门禁、检索和沉淀 runner，不是向量数据库脚本。当前默认使用本地索引 + `rg` 检索；多数场景只过 Gate，不打开经验卡。

## 2. 启动信号

- 准备向用户提问、质问、grill 或确认方向。
- 产品判断、项目汇报、PRD、需求分析、需求管理。
- 汇报、需求文档、PRD、竞品分析、技术翻译报告、指标/验收文档等报告或文档类重任务。
- 用户纠错、偏好、听不懂、不理解。
- 任务会影响项目文件、下游角色或长期决策。

## 3. 运行模式

| 模式 | 什么时候用 | 输出重点 |
| --- | --- | --- |
| `pre-question` | 准备向用户追问或质问前 | L1 索引级 Gate、发问约束、0-1 个问题建议 |
| `heavy-task` | 准备产出报告、需求文档、PRD、竞品分析等重任务前 | L2 经验卡检索、`experience_brief`、重思考约束 |
| `normal` | 普通产品判断、纠错或经验沉淀 | applied_rules 和新经验候选 |

## 3.1 RAG 层级

| 层级 | 默认读取 | 允许打开经验卡 | 输出 |
| --- | --- | --- | --- |
| L0 | 不读经验库 | 否 | 无 |
| L1 | `EXPERIENCE_INDEX.md`、项目经验索引、用户偏好/纠错摘要 | 否 | `rag_gate_decision` |
| L2 | L1 + 经验卡 | 是，3-5 条 | `experience_brief` |

`pre-question` 默认停在 L1。`heavy-task` 默认进入 L2。`normal` 先做 L1，命中强纠错、关键偏好或高风险决策时才升级 L2。

## 4. 执行步骤

| 步骤 | 动作 | 输出 |
| --- | --- | --- |
| 1 | 判断运行模式：`pre-question`、`heavy-task` 或 `normal` | rag_mode |
| 2 | 判断 RAG 层级：L0/L1/L2 | rag_level |
| 3 | 抽取项目、workflow、产物、信号、产品区域、决策维度 | gate query |
| 4 | L1：读取 `experience/EXPERIENCE_INDEX.md` 和项目索引/偏好/纠错摘要 | rag_gate_decision |
| 5 | 判断是否升级 L2 | upgrade_decision |
| 6 | L2：使用关键词打开 3-5 条经验卡 | 经验片段 |
| 7 | 判断范围、可信度、时效、边界 | 适用/不适用 |
| 8 | 按模式输出：发问依据、`experience_brief`、重思考约束或本次规则 | mode_output |
| 9 | 任务结束后判断是否写入新经验 | 经验卡或不写 |

## 5. 检索命令

L1 项目内 Gate：

```powershell
rg -n "关键词1|关键词2|workflow-id|产物名" "experience/<项目名>/经验索引.md" "experience/<项目名>/*偏好*" "experience/<项目名>/纠错经验库.md" user
```

L2 经验卡检索：

```powershell
rg -n "关键词1|关键词2|workflow-id|产物名" experience user
```

## 6. 文件管理

| 文件 | 用途 |
| --- | --- |
| `experience/RAG_MODEL.md` | 经验卡字段和维度 |
| `experience/RAG_RULES.md` | 检索、阅读、应用、写入规则 |
| `experience/EXPERIENCE_INDEX.md` | 全局经验索引 |
| `experience/templates/experience-card-template.md` | 新经验卡模板 |
| `experience/<项目名>/经验索引.md` | 项目经验索引 |
| `workflows/HEAVY_TASK_RAG_RULES.md` | 重任务入口与内部追问门禁 |

## 7. 回退方式

- 如果 `pre-question` 的 L1 Gate 没有命中，继续基于当前事实发问，不升级 L2。
- 如果 `heavy-task` 的 L2 没有命中经验卡，仍要输出轻量 `experience_brief` 和重思考中间包，不能直接套模板。
- 如果重任务内部追问的项目、workflow、产物、决策点没变，复用入口 `experience_brief`。
- 如果召回经验冲突，以当前用户明确要求和当前项目事实为准。
- 如果经验可信度低，只作为风险提醒。
- 如果无法判断是否写入，先写 `experience/inbox/`，状态 `candidate`。

## 8. 完成标准

- Gate 或检索过的经验能回到文件路径。
- 使用的经验有适用范围判断。
- 输出没有把旧经验当当前事实。
- `pre-question` 默认 L1，不打开经验卡，输出的问题少且指向决策差异。
- `heavy-task` 输出可复用的 `experience_brief` 和重思考中间包，再进入报告/文档 workflow。
- 需要沉淀的新经验有模板、关键词、可信度和触发条件。

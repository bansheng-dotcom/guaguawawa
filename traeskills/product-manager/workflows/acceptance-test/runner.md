# 验收与测试场景 Runner

## 1. Runner 定位

这是人工可执行 runner，不是测试执行脚本。它规定产品管理 person 如何把 PRD 或需求卡转换成验收标准和测试场景。

当前版本不运行自动化测试、不提交 bug、不修复代码，也不自动触发其他 agent。

## 1.1 重任务门禁

正式验收文档属于重任务。先读 `workflows/HEAVY_TASK_RAG_RULES.md`，执行 `workflows/experience-rag/workflow.yaml` 的 `heavy-task` 模式；如果范围、主路径或失败态不清，先复用入口 `experience_brief`，关键维度变化才执行 `pre-question` L1。

## 2. 启动信号

- “帮我写验收标准”
- “这个 PRD 怎么验收”
- “拆测试场景”
- “补边界情况”
- “Given/When/Then 怎么写”

## 3. 执行步骤

| 步骤 | 动作 | 输入 | 输出 | 门禁 |
| --- | --- | --- | --- | --- |
| 1 | 读取 workflow 配置 | `workflow.yaml` | 运行边界 | 明确不执行测试 |
| 2 | 读取 prompt 和质量指南 | `prompts/current.md`、`references/acceptance-test-guide.md` | 写作规则 | 版本号记录到工作日志 |
| 3 | 提取范围 | PRD/需求卡 | 范围和不在范围 | 通过 scope_gate |
| 4 | 提取主路径 | 用户流程、系统行为 | 主路径清单 | 用户动作清楚 |
| 5 | 写验收标准 | 主路径 | Given/When/Then | 通过 gwt_gate |
| 6 | 补状态和失败态 | 验收标准 | 边界场景 | 通过 state_gate |
| 7 | 写测试场景表 | 验收标准、边界 | 场景表 | 通过 testability_gate |
| 8 | 生成可选审查提醒 | `review_hints.yaml` | 下一步提醒 | 不写成本地路径 |
| 9 | 输出确认版 | 场景表 | 人话报告 | 先讲覆盖范围 |

## 4. 文件管理

| 文件 | 作用 |
| --- | --- |
| `workflow.yaml` | 工作流元信息、输入输出、门禁 |
| `topology.md` | 拓扑图、节点备注、输出包 |
| `references/acceptance-test-guide.md` | 验收与测试场景质量规则 |
| `review_hints.yaml` | 可选审查提醒 |
| `prompts/current.md` | 当前稳定 prompt |
| `prompts/CHANGELOG.md` | prompt 版本变更 |
| `runner.md` | 本执行手册 |

## 5. 回退方式

| 失败点 | 回退 |
| --- | --- |
| PRD 范围不清 | 回 prd-report 补范围 |
| 验收不可观察 | 改成动作、结果、状态变化 |
| 缺失败态 | 补错误、权限、超时、空数据 |
| 用户要执行测试 | 输出测试 brief，提醒转测试能力 |

## 6. 完成标准

- 有范围和不在范围。
- 有主路径验收标准。
- 有边界、失败态和权限状态。
- 有测试场景表。
- 每条验收都能被观察或复现。
- 有可选审查提醒和下一步。

# PM Workflow Registry

> 用途：登记产品管理 person 的目录化 workflow。工作流以目录为主体，根目录只保留注册表和迁移说明；具体方法、模板、prompt 和 runner 放回所属 workflow。

| Workflow | 优先级 | 状态 | 入口 | 说明 |
| --- | --- | --- | --- | --- |
| `controller` | P0 | draft | `workflows/controller/workflow.yaml` | 总控入口：轻量反应、缺口判断、workflow 路由和最小产物选择 |
| `experience-rag` | P0 | draft | `workflows/experience-rag/workflow.yaml` | 先过 RAG Gate，再决定是否打开经验卡；重任务生成可复用 experience_brief |
| `pm-thinking` | P0 | draft | `workflows/pm-thinking/workflow.yaml` | 轻量 grill-me：基于用户输入推演关键缺口，少问但能推进 |
| `requirement-report` | 基础 | draft | `workflows/requirement-report/workflow.yaml` | 将想法、反馈或功能请求整理成需求成立判断、优先级和最低成本验证计划 |
| `prd-report` | P0 | draft | `workflows/prd-report/workflow.yaml` | 将已澄清需求整理成 PRD 报告；后续审查只作为可选提醒 |
| `metrics-framework` | P0 | draft | `workflows/metrics-framework/workflow.yaml` | 为需求、PRD 或 MVP 定义指标树、数据口径、数据缺口和 Go/No-Go 标准 |
| `acceptance-test` | P0 | draft | `workflows/acceptance-test/workflow.yaml` | 将 PRD 或需求卡翻译成验收标准、测试场景、边界和失败态 |
| `demand-management` | P0 | draft | `workflows/demand-management/workflow.yaml` | 正式开发输入：需求编号、需求卡、下游文件、协作复核和工作日志 |
| `project-briefing` | P0 | draft | `workflows/project-briefing/workflow.yaml` | 项目理解、人感汇报、决策选项、推荐但不代决策、归档 |
| `report-production` | P1 | draft | `workflows/report-production/workflow.yaml` | 报告类型、证据层、视觉层和可选专业能力边界 |
| `mvp-validation` | P1 | draft | `workflows/mvp-validation/workflow.yaml` | 将需求或想法收敛成 MVP 假设、最低成本实验和 Kill 标准 |
| `competitive-analysis` | P1 | draft | `workflows/competitive-analysis/workflow.yaml` | 围绕产品决策做竞品对照、启发、差异化和风险分析 |
| `product-strategy` | P1 | draft | `workflows/product-strategy/workflow.yaml` | 将阶段目标、用户分群、机会树、战略画布和取舍整理成战略判断 |
| `ui-brief` | P1 | draft | `workflows/ui-brief/workflow.yaml` | 将需求翻译成页面目标、信息架构、用户动作和状态清单 |
| `technical-brief` | P1 | draft | `workflows/technical-brief/workflow.yaml` | 将需求或技术方案翻译成用户影响、前后端/Agent 影响、数据权限和失败兜底 |

## 重任务门禁

重任务指要产出正式报告、文档或需求包的工作，不包括仅提问、质问或轻量判断。

| 类型 | 适用 workflow | 入口规则 |
| --- | --- | --- |
| 汇报/报告 | `project-briefing`、`report-production` | 先读 `workflows/HEAVY_TASK_RAG_RULES.md`，通过 `heavy-task` L2 生成 `experience_brief`，再进入具体 workflow |
| 需求/PRD | `requirement-report`、`prd-report`、`demand-management` | 入口走 `experience-rag` 的 `heavy-task` L2；内部追问默认复用 `experience_brief`，关键维度变化才走 `pre-question` L1 |
| 分析/翻译/验收 | `competitive-analysis`、`product-strategy`、`metrics-framework`、`mvp-validation`、`technical-brief`、`acceptance-test`、`ui-brief` | 先形成 `experience_brief` 和重思考中间包，再写报告或 brief |

## 目录化 workflow 规范

每个新 workflow 默认包含：

```text
workflows/<workflow-id>/
├── workflow.yaml
├── topology.md
├── review_hints.yaml
├── runner.md
├── references/
│   └── <workflow-id>-guide.md
├── templates/
│   └── <optional-template>.md
└── prompts/
    ├── current.md
    └── CHANGELOG.md
```

## 分层规则

| 文件 | 放什么 | 不放什么 |
| --- | --- | --- |
| `workflow.yaml` | 元信息、触发、输入输出、门禁、版本 | 长篇 prompt |
| `topology.md` | Mermaid 拓扑、节点备注、门禁说明 | 子 agent 长提示词 |
| `review_hints.yaml` | 可选审查角色、提醒条件、审查重点 | 自动触发、写死本地路径 |
| `runner.md` | 执行顺序、回退、完成标准 | 隐藏运行时、API key |
| `references/` | 任务需要时才读取的方法参考、质量门禁、样例提炼 | 主入口长篇说明 |
| `templates/` | 该 workflow 直接使用的输出模板 | 无归属模板、跨 workflow 模板堆叠 |
| `prompts/current.md` | 当前稳定提示词 | 历史说明 |
| `prompts/CHANGELOG.md` | prompt 版本变化 | 当前执行规则 |

## 迁移说明

| 原散文件 | 当前归属 | 处理结果 |
| --- | --- | --- |
| `PM轻量反应与工作流选择.md`、`PM总控路由流程.md` | `workflows/controller/` | 已融合为总控 workflow，原文进入 `references/` |
| `PM质问与思考流程.md` | `workflows/pm-thinking/` | 已目录化，原文进入 `references/` |
| `PM报告生产流程.md` | `workflows/report-production/` | 已目录化，原文进入 `references/` |
| `项目理解与汇报流程.md` | `workflows/project-briefing/` | 已目录化，原文进入 `references/` |
| `需求管理与协作审核流程.md`、`PRD到执行需求融合流程.md` | `workflows/demand-management/` | 已融合为正式开发输入 workflow |
| `外部PM框架融合流程.md` | `workflows/prd-report/references/external-framework-fusion-guide.md` | 不再作为独立 workflow，成为 PRD 报告参考 |
| `腾讯产品法产品决策流程.md` | `workflows/product-strategy/references/tencent-product-decision-flow.md` | 不再作为根 workflow，成为产品战略/判断参考 |

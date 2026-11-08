# PM Skills 融合参考

## 来源

- 参考仓库：`phuryn/pm-skills`
- 参考时间：2026-06-30
- 参考范围：README、CLAUDE/AGENTS 指南、各插件 README、commands、skills。
- 当前状态：原始仓库只作归档，不作为运行时 reference。运行时只读取本地 `library/`、`workflows/*/references/` 和 `experience/`。

## 总体判断

`pm-skills` 的价值是把产品管理拆成可触发的框架和端到端 workflow。它适合补强本 person 的方法库，但不能替代本地产品管理 agent 的身份、需求编号、需求卡、腾讯产品法审查和本地协作审核制度。

## 可吸收的方法块

| 方法块 | 适合吸收什么 | 本地落点 |
| --- | --- | --- |
| PRD 八段结构 | 摘要、背景、目标、用户分群、价值主张、方案、发布、开放问题 | `workflows/prd-report/templates/prd-human-machine-template.md` |
| write-prd workflow | 从模糊想法到 PRD，再到 scope tightening、pre-mortem、stories | `workflows/demand-management/references/prd-to-execution-guide.md` |
| User Stories | 角色、动作、收益、验收条件 | `workflows/acceptance-test/templates/user-story-test-scenario-template.md` |
| Job Stories | 情境、动机、结果 | `workflows/acceptance-test/templates/user-story-test-scenario-template.md` |
| WWA | Why、What、Acceptance | `workflows/acceptance-test/templates/user-story-test-scenario-template.md` |
| Test Scenarios | 测试目标、前置条件、动作、预期结果 | `workflows/acceptance-test/templates/user-story-test-scenario-template.md` |
| Red-team | 承重假设、失败条件、证据、停止标准、最小实验 | `workflows/prd-report/templates/prd-red-team-premortem-template.md` |
| Pre-mortem | 预演失败、风险分级、行动计划 | `workflows/prd-report/templates/prd-red-team-premortem-template.md` |
| Outcome Roadmap | 功能清单改写成用户结果和业务结果 | PRD / 工作报告 |
| Metrics Dashboard | 北极星、输入、健康、商业指标 | PRD / 需求卡 |
| Opportunity Solution Tree | 目标、机会、方案、实验 | `workflows/prd-report/templates/product-discovery-to-prd-template.md` |
| Value Proposition | 用户、问题、现状、方案、结果、替代品 | PRD / 腾讯产品法审查 |

## 全包内化状态

| pm-skills 包 | 原始能力 | 本地化状态 | 本地落点 | 说明 |
| --- | --- | --- | --- | --- |
| `pm-execution` | PRD、用户故事、Job Story、WWA、测试场景、优先级、红队、预演失败、roadmap、OKR、sprint、retro、会议纪要、stakeholder map、release notes | 已内化核心，团队仪式类轻量保留 | `prd-report`、`demand-management`、`acceptance-test`、`mvp-validation`、`product-strategy`、`project-briefing` | 本地重点是需求卡、PRD、验收、风险和汇报；sprint/retro/meeting 不做独立 workflow |
| `pm-product-discovery` | 需求分析、假设识别、假设排序、实验设计、OST、访谈、指标 dashboard、功能优先级 | 已内化 | `requirement-report`、`pm-thinking`、`mvp-validation`、`metrics-framework`、`product-strategy` | 入口加了轻量 intake、RAG Gate 和数据状态判断 |
| `pm-product-strategy` | Product Strategy Canvas、Value Proposition、Business/Lean/Startup Canvas、SWOT、PESTLE、Five Forces、Ansoff、pricing、monetization | 已内化为战略判断框架，商业/定价细节保留为可选分析 | `product-strategy/references/product-strategy-guide.md`、`prd-report/references/prd-writing-guide.md` | 不把每个框架做成独立 agent，按决策问题选择 |
| `pm-market-research` | 竞品、用户画像、用户分群、旅程地图、市场规模、情绪分析 | 已内化核心，数据密集部分只给可选数据能力提醒 | `competitive-analysis`、`requirement-report`、`product-strategy`、`metrics-framework` | 竞品/分群/旅程可由 PM 初稿闭环；市场规模和情绪分析需要证据或数据 |
| `pm-marketing-growth` | 北极星指标、价值主张、定位、命名、营销想法 | 部分内化 | `metrics-framework`、`product-strategy`、`competitive-analysis`、`report-production` | PM 可定义指标和定位判断；命名/营销创意不是本 agent P0/P1 |
| `pm-go-to-market` | ICP、beachhead、GTM motion、growth loop、battlecard、launch plan | 部分内化 | `product-strategy`、`competitive-analysis`、`report-production` | 可做战略/竞品/汇报初稿；正式 GTM 执行不是当前 PM agent 核心 |
| `pm-data-analytics` | SQL、cohort、A/B test | 只内化问题定义和指标门禁 | `metrics-framework`、`requirement-report`、`report-production` | 真实查询、统计检验、归因计算只给可选数据分析能力提醒 |
| `pm-ai-shipping` | shipping artifacts、intended-vs-implemented、安全/性能审计、测试覆盖地图 | 内化为可审阅交付物和技术翻译门禁 | `demand-management`、`technical-brief`、`acceptance-test`、`ui-brief` | PM 写意图、权限、流程、测试地图；安全/性能审计交给工程/测试 |
| `pm-toolkit` | NDA、隐私政策、简历、语法检查 | 不作为 PM agent 核心内化 | 无默认 workflow | 法务、简历和通用校对不进入产品管理总控 |

## 已内化的核心能力覆盖

| 原始能力簇 | 本地能力 | 覆盖判断 |
| --- | --- | --- |
| 模糊想法澄清 / grill | `pm-thinking` + `experience-rag: pre-question L1` | 已内化 |
| 需求与反馈分析 | `requirement-report` | 已内化 |
| PRD 写作 | `prd-report` | 已内化 |
| PRD 到执行 | `demand-management` + `acceptance-test` | 已内化 |
| 用户故事 / Job Story / WWA | `acceptance-test/templates/user-story-test-scenario-template.md` | 已内化 |
| 指标体系 / North Star / Go-No-Go | `metrics-framework` | 已内化 |
| MVP / 假设 / 实验 | `mvp-validation` | 已内化 |
| 机会树 / 战略画布 / 取舍 | `product-strategy` | 已内化 |
| 竞品 / battlecard / 市场对照 | `competitive-analysis` | 已内化为决策型竞品报告 |
| 红队 / Pre-mortem | `prd-report/templates/prd-red-team-premortem-template.md` + `demand-management` | 已内化 |
| 可审阅交付物 / Intent vs implementation | `technical-brief` + `demand-management` + `acceptance-test` | 已内化为 PM 侧意图和验收门禁 |
| SQL / cohort / A/B test | `metrics-framework` 定义问题，真实数据分析只做可选能力提醒 | 有意不内化执行 |
| GTM / marketing / legal / resume | 非当前 P0/P1 | 有意不内化或仅轻量参考 |

## 不直接照搬的部分

| 不照搬项 | 原因 | 本地处理 |
| --- | --- | --- |
| Slash command | Codex 当前不把外部命令当本地 slash command 运行 | 转成 workflow 或模板 |
| 外部插件注册结构 | 本 person 是本地自定义 agent，不是外部插件市场 | 只保留方法映射 |
| 英文原模板 | 不符合“给用户的人话汇报”要求 | 改写成中文、人机两层表达 |
| 只写 PRD 不建需求卡 | 和本地强制需求管理规范冲突 | 先建需求卡，再生成 PRD |
| 只给风险清单 | 容易空转 | 必须给证据、停止标准和下一步动作 |

## 融合后的默认链路

```mermaid
flowchart LR
  A["用户想法/外部 PRD"] --> B["真正问题"]
  B --> C["用户/JTBD/价值主张"]
  C --> D["指标与核心假设"]
  D --> E["需求卡"]
  E --> F["PRD"]
  F --> G["User Story / WWA"]
  G --> H["Test Scenarios"]
  H --> I["Red-team / Pre-mortem"]
  I --> J["可选协作审核"]
```

## 使用边界

- 轻量任务只用 PRD 和验收标准，不强制跑完整链路。
- 高风险或跨角色任务必须跑 Red-team 或 Pre-mortem。
- 需求方向未确认前，不拆开发任务。
- 缺少数据时，指标可以标为待补，但不能伪造基线或目标。

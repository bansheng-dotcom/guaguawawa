---
name: qiuqiu-product
description: "产品管理总控（内置产品经理 Agent 完整方法包）：需求澄清、产品判断、PRD、需求卡、指标框架、验收标准、MVP 验证、竞品分析、产品战略、UI brief、技术翻译、项目汇报，以及基于 RAG Gate 的经验沉淀。当用户要判断需求成立性、写或评审 PRD、定义指标与验收、做 MVP 实验设计、做竞品/战略分析、把技术方案讲成人话、或需要产品决策汇报时使用。Product manager controller: clarify intent, judge requirement validity, write PRD, define metrics and acceptance, run MVP validation, competitive analysis and product strategy."
---

# 产品策略工作流（高雅人士天团 · 产品管理总控）

本技能 **不是摘要**，而是内置了完整的上游方法包：`upstream/` 下是产品经理 Agent 项目的全部 workflow、模板、经验库和能力地图，原样保留。遇到具体任务时，按本文件的「路由表」进入对应 `upstream/workflows/<workflow-id>/`，读该 workflow 的 `runner.md` 与 `references/`，而不是凭记忆作答。

核心信条：**先判断问题是否成立，再决定方案；不把「用户想要」当作「需求成立」。**

---

## 一、什么时候启用

- 需求/想法/反馈需要判断「该不该做」「做成什么」「怎么验收」
- 要写 PRD、需求卡、指标树、验收标准、MVP 实验方案
- 要做竞品对照、产品战略取舍、机会树、差异化定位
- 要把技术方案、接口、权限、兜底翻译成用户能拍板的人话
- 要做产品决策汇报、项目理解汇报、汇报归档
- 需要复用历史经验（偏好、纠错、同类判断）避免重复踩坑

**不启用**：纯取数与归因（走 qiuqiu-data-analysis）、图表选型与美化（走 qiuqiu-data-viz）、长文写作（走 qiuqiu-content）、多平台运营看板（走 qiuqiu-media-ops）。

---

## 二、启动必读（按顺序，最多 3 个文件）

| 顺序 | 文件 | 读到什么程度 |
|---|---|---|
| 1 | `upstream/SKILL.md` | 触发边界、能力边界、禁止事项（全文） |
| 2 | `upstream/AGENTS.md` | 总控规则：角色认知、任务轻重分级、路由、RAG Gate、输出边界（全文） |
| 3 | `upstream/workflows/WORKFLOW_REGISTRY.md` | 15 个 workflow 的优先级与入口（全文） |

重任务（正式报告/文档/需求包）**额外必读** `upstream/workflows/HEAVY_TASK_RAG_RULES.md`，先过 `heavy-task` L2 门禁生成 `experience_brief` 再动笔。

---

## 三、主流程（六步，不许跳）

1. **轻量反应**：一句话复述「我理解为……」，判断信息缺口是否影响方向。参考 `upstream/workflows/controller/references/light-reaction-guide.md`。
2. **任务轻重分级**：轻（解释/判断/追问）→ 直接短答；中（草稿/审阅/局部框架）→ 对应 workflow 轻量版；重（PRD/报告/需求包）→ 先过门禁。
3. **RAG Gate**：轻任务走 `pre-question` L1，重任务走 `heavy-task` L2，产出 `experience_brief`。规则见 `upstream/experience/RAG_RULES.md`，模型见 `upstream/experience/RAG_MODEL.md`。
4. **选 workflow 并执行**：按下方路由表进入 `upstream/workflows/<id>/runner.md`，按其执行顺序推进；模板取同目录 `templates/`，方法参考取 `references/`。
5. **结果结构化**：默认顺序为「一句话结论 → 真正问题 → 该走的能力 → 用户/前端/后端/Agent 影响 → 风险与未决点 → 下一步最小动作」。
6. **沉淀**：用户纠错、偏好、可复用判断写入经验卡（`upstream/experience/templates/experience-card-template.md`），不靠聊天记忆。

---

## 四、能力路由表（用户意图 → workflow）

| 用户意图 | workflow 目录 | 主要产物 |
|---|---|---|
| 帮我想清楚 / 被质问 | `workflows/pm-thinking/` | 已确认事实、隐含假设、关键问题、下一步 |
| 这个需求成立吗 / 分析反馈 | `workflows/requirement-report/` | 需求成立判断、优先级、最低成本验证 |
| 写 PRD / 改 PRD | `workflows/prd-report/` | PRD 报告、范围与不在范围、验收标准、风险 |
| 准备进开发 | `workflows/demand-management/` | 需求卡、需求编号、下游文件、协作复核状态 |
| 指标怎么定 / 怎么验证 | `workflows/metrics-framework/` | 指标树、口径、数据源、数据缺口、Go/No-Go |
| 怎么验收 | `workflows/acceptance-test/` | Given/When/Then、边界、失败态、测试场景 |
| MVP 怎么验证 | `workflows/mvp-validation/` | 承重假设、最低成本实验、Kill 标准 |
| 竞品对比 | `workflows/competitive-analysis/` | 对照矩阵、启发、差异化、风险 |
| 产品战略 / 阶段取舍 | `workflows/product-strategy/` | 用户分群、机会树、战略画布、取舍 |
| 页面怎么设计 | `workflows/ui-brief/` | 页面目标、信息架构、状态清单、交互 brief |
| 技术讲成人话 | `workflows/technical-brief/` | 用户影响、系统影响、权限、失败兜底 |
| 汇报 / 项目理解 | `workflows/project-briefing/`、`workflows/report-production/` | 人话汇报、决策选项、推荐、归档 |
| 总控 / 不确定走哪个 | `workflows/controller/` | 路由决策 + 最小可验证产物 |
| 经验检索与沉淀 | `workflows/experience-rag/` | experience_brief、经验卡 |

> 每个 workflow 的标准结构：`workflow.yaml`（元信息/触发/门禁）、`topology.md`（拓扑）、`runner.md`（执行顺序与完成标准）、`references/`（方法参考）、`templates/`（输出模板）、`prompts/current.md`（当前稳定提示词）。

---

## 五、内化能力包（轻量调用，不依赖外部 agent）

| 需要什么 | 读哪个文件 | 能力边界 |
|---|---|---|
| PM 角色认知与工作切分 | `upstream/library/PM角色认知.md`、`upstream/library/PM工作切分与能力地图.md` | — |
| 腾讯产品法决策纲领 | `upstream/library/腾讯产品法产品纲领.md` | 作战略/判断参考，不作流程 |
| PM Skills 融合参考 | `upstream/library/PM Skills融合参考.md` | — |
| 轻量写作 | `upstream/library/PM轻量写作能力.md` | 可到决策报告/PRD 草稿；不可声称做正式长文与强风格内容 |
| 轻量 UI | `upstream/library/PM轻量UI设计能力.md` | 可到页面目标/信息架构/低保真；不可声称做高保真视觉与设计系统 |
| 轻量数据分析 | `upstream/library/PM轻量数据分析能力.md` | 可到分析问题/口径/图表计划；不可声称出真实 SQL、清洗、统计检验、复杂归因 |
| 协作边界与术语 | `upstream/library/PM内化能力与协作边界.md`、`upstream/library/术语翻译表.md` | 对外表达统一口径 |

---

## 六、硬性规则

- 问题没定义清楚前不直接给方案。
- 不用长文掩盖判断不清；不把未确认内容写成已确认需求。
- 不跳过需求卡与验收标准进入开发。
- 不把外部能力写死成触发契约（保持「能力内化 + 显式边界」）。
- 正式开发输入必须齐：需求编号、需求卡、范围/不在范围、验收标准、协作审核状态。
- 缺数据支撑的判断必须标注为**待验证假设**，并给出最低成本验证动作。
- 经验卡只写可复用规则，不抄任务过程。

## 七、输出模板与归档

- 模板注册表：`upstream/templates/TEMPLATE_REGISTRY.md`（模板归属到具体 workflow / user / experience，不堆叠）
- 用户偏好与纠错：`upstream/user/README.md`、`upstream/user/templates/user-preference-record-template.md`
- 汇报归档：`upstream/reports/README.md`

**交付前自检**：结论是否先行？事实/假设/建议是否分离？是否给了下一步最小动作？是否需要用户拍板的选项与代价？

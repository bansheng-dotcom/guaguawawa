# docs 索引（现行 / 历史）

> 2026-11-24 重新校准。**文件仍存在于 docs/ 不等于它是现行规则。** 规则冲突时，先读唯一总纲，再读对应现行分册；历史文档只用于追溯设计背景，不得直接作为施工依据。

## 现行（读这些）

| 文档 | 回答什么 |
|---|---|
| **`MASTER-UPGRADE-SOP.md`** | **唯一系统升级总纲**：当前决策、优先级、显式降级边界、D1/D2/D3 与 DoD |
| **`UPGRADE-PLAN.md`** | **2026-11-24 本轮唯一执行分册**：静态源码审查、主链接线、问题矩阵、外部依据、二阶三阶影响与未来同步文件 |
| `COLLECTION-COMPLIANCE.md` | 采集合规现行分册：逐源审核、默认拒绝、preview/quality/run 同门、单快照与撤销 |
| `COLLECTION-SOP.md` | 采集流程专项分册；合规与门禁以 `COLLECTION-COMPLIANCE.md` 和总纲为准 |
| `COORDINATION-SOP.md` | 协同与能力级别分册；实际级别必须来自已验证资产，并与双覆盖率口径一致 |
| `../REPORT-STANDARD.md` | 报告写什么、怎么判合格、怎么验（唯一报告标准） |
| `PROJECT-RULES.md` | 项目规则（13 条，每条绑定一个自动检查；违反即返工） |
| `../REPORT-BRIDGE-GUIDE.md` | 新角色/新能力怎么接入唯一产线 |
| `REPORT-LINES.md` | 报告产线地图（一条线、四种输入、保留零件、项目根与 brief） |
| `../使用指南.md` §2.7 | 工具 vs 项目资产：项目根、写入守卫、CardBundle 与 expert_brief 契约 |
| `../CHANGELOG.md` | 专家团（智能体）更新日志：按日期记录能力、门禁、迁移与不兼容 |
| `REPORT-COVERAGE-UPGRADE-SOP.md` | 覆盖升级 SOP：50 源/饱和/矩阵/确认/双门禁/R04 全审 |
| `REPORT-PROSE-STYLE.md` | 文笔与深度 Style Guide：三问/三动作/PART I–III/论证五段/rubric |
| `REPORT-FLOW.md` | Flow 报告：HTML 一条流、PDF 自动分页、摘要必填、小页脚 |
| `REPORT-LAYOUTS.md` | consulting 主题：A/B 两种页式 + 13 型图表（core 可选出口） |
| `REPORT-DECISION-GRADE.md` | 决策级报告的目标形态（问题→断言→证据→图） |
| `REPORT-CLAIM-GATE.md` | 断言门禁（头条资格、可比较性） |
| `REPORT-DATA-INTAKE.md` | 数据 intake：来源、quote 回抓、缺口 |
| `REPORT-SOURCE-GAP-POLICY.md` | 缺口政策（缺就是缺，不许补形容词） |
| `REPORT-OUTCOME-LEDGER.md` · `REPORT-OUTCOME-CALIBRATION.md` | 结果台账与校准 |
| `REPORT-CAPABILITY-GRAPH.md` · `REPORT-CAPABILITY-DECISIONS.md` | 角色×问题×能力图 |
| `REPORT-FEATURE-FLAGS.md` | 降级开关（哪些还生效、哪些已随 P1 删除） |
| `SKILL-LAYER-SPEC.md` | 一份合格 `SKILL.md` 的硬标准（六字段 + 十节 + 100 分口径） |
| `SKILL-MD-UPGRADE-PLAN.md` | 技能层升级路线 |
| `SOP_AGENT_META_UPGRADE.md` | 智能体能力升级方法论（体检→对标→硬化→注入→闭环→沉淀） |
| `CHART_CRAFT_STUDY.md` | 图表工艺沉淀（48 型图纪律） |
| `DOMAIN-EXPERT-LAYER.md` | 业务线 → 领域编队 |
| `REPORT_REFERENCE_LIBRARY.md` | 报告参考库（案例与写法） |

## 历史 / 限定使用（文件可能仍在 docs/）

| 文档或类别 | 当前使用方式 |
|---|---|
| `docs/archive/DATA-LAYER-SOP.md`、`DATA-LAYER-SOP-v3.md` | 历史方案/专项背景。`actual_rows=null`、collect 收尾调 `fulfil` 等旧表述不得当作当前源码事实或既定实施路线。 |
| `docs/archive/SYSTEM-UPGRADE-SOP-v3.md` | 历史方案/专项背景。staging→mart、Expand-Contract 等设计可参考；`GUAGUA_PIPELINE=v2` 未核实到当前消费者，不得当作现存回滚开关。 |
| 未在上方列为现行的 `REPORT-*-UPGRADE-SOP.md`、早期升级 SOP 与过程稿 | 按各自主题参考；状态、优先级和验收与总纲冲突时，以总纲和 `UPGRADE-PLAN.md` 为准。 |
| 其他未列入“现行”的学习笔记、复盘和版本稿 | 只作历史证据，不直接施工；需要追溯时同时查 git 历史与当前源码。 |

本轮仅校准权威关系，没有批量删除历史文件。任何“已接线”“已通过”“开关存在”的描述，都必须以当前源码和运行时证据重新验证。

## 数据文件

`actions_catalog.json`（由 `scripts/export_actions_catalog.py` 生成）、
`semantic_field_map.json`（由 `scripts/build_semantic_field_map.py` 生成）——
需要最新口径时重新生成，不要手改。

## 重构文档（在包内 `交付/`）

| 文档 | 内容 | 状态 |
|---|---|---|
| `拆卡升级-SOP-2026-11-21.md` | 拆卡五轴、S1–S11 门禁、卡片契约 | 历史原始定义，仍被 `REPORT-LINES.md` 引用；冲突以 MASTER 为准 |
| `协作层-SOP-2026-11-21.md` | 卡间协商、R02 交接包与波次 | 专项参考，被拆卡 SOP 引用；冲突以 MASTER / COORDINATION 为准 |
| `报告系统升级SOP-2026-11-21.md` | 报告产线结构、呈现与数据层修复 | 过程记录，与两份设计稿互引 |
| `50材料核验-2026-11-21.md` | 50 份外部材料的 URL/许可核验明细 | 证据附件 |
| `专家团系统升级-SOP-v5-2026-11-22.md` | 2026-11-22 系统升级方案 | 历史版本链；不是当前唯一总纲 |
| `generic_semantics_v1.yaml` | 跨业务线通用语义（度量类型/质量六维/因果阶） | **代码依赖**（`core/cards/card_upgrade.py`） |
| `semantic_layer.template.yaml` | 语义层模板 | 模板（`card_issue.py` 会生成同名文件） |
| `agent_card.template.yaml` · `handoff_contract.template.yaml` | 角色卡 / 交接包模板 | 模板，暂无代码引用 |
| `perspectives.template.yaml` | 视角模板 | 被拆卡 SOP 引用 |

> 2026-11-22 核查结论：除 `generic_semantics_v1.yaml` 外，`交付/` 下文件均不被运行时读取。

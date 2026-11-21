# docs 索引（现行 / 历史）

> 2026-11-18（v11 · P1）重整，2026-11-22 清理历史过程稿。**现行文档只有下面列出的几份**；
> 历史副本不再保留，只在 git 历史里可追溯。

## 现行（读这些）

| 文档 | 回答什么 |
|---|---|
| `../REPORT-STANDARD.md` | 报告写什么、怎么判合格、怎么验（唯一报告标准） |
| `PROJECT-RULES.md` | 项目规则（13 条，每条绑定一个自动检查；违反即返工） |
| `../REPORT-BRIDGE-GUIDE.md` | 新角色/新能力怎么接入唯一产线 |
| `REPORT-LINES.md` | 报告产线地图（一条线、四种输入、保留零件） |
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

## 历史（已移出 docs/）

历史过程稿（`REPORT-LINE-V4..V8.md`、`UPGRADE-PLAN-V3.md`、各类 SOP 与学习笔记）已在 2026-11-22 的
仓库清理中删除，不再保留本地副本；需要追溯时看 git 历史，不要当现行口径引用。

## 数据文件

`actions_catalog.json`（由 `scripts/export_actions_catalog.py` 生成）、
`semantic_field_map.json`（由 `scripts/build_semantic_field_map.py` 生成）——
需要最新口径时重新生成，不要手改。

## 重构文档（在包内 `交付/`）

| 文档 | 内容 | 状态 |
|---|---|---|
| `拆卡升级-SOP-2026-11-21.md` | 拆卡五轴、S1–S11 门禁、卡片契约 | 现行，被 `REPORT-LINES.md` 引用 |
| `协作层-SOP-2026-11-21.md` | 卡间协商、R02 交接包与波次 | 现行，被拆卡 SOP 引用 |
| `报告系统升级SOP-2026-11-21.md` | 报告产线结构、呈现与数据层修复 | 过程记录，与两份设计稿互引 |
| `50材料核验-2026-11-21.md` | 50 份外部材料的 URL/许可核验明细 | 证据附件 |
| `专家团系统升级-SOP-v5-2026-11-22.md` | 最新一版系统升级 SOP | 版本链最新 |
| `generic_semantics_v1.yaml` | 跨业务线通用语义（度量类型/质量六维/因果阶） | **代码依赖**（`core/card_upgrade.py`） |
| `semantic_layer.template.yaml` | 语义层模板 | 模板（`card_issue.py` 会生成同名文件） |
| `agent_card.template.yaml` · `handoff_contract.template.yaml` | 角色卡 / 交接包模板 | 模板，暂无代码引用 |
| `perspectives.template.yaml` | 视角模板 | 被拆卡 SOP 引用 |

> 2026-11-22 核查结论：除 `generic_semantics_v1.yaml` 外，`交付/` 下文件均不被运行时读取。

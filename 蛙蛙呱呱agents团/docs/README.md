# docs 索引（现行 / 历史）

> 2026-11-18（v11 · P1）重整。**现行文档只有下面列出的几份**；历史过程稿已移出 `docs/`，
> 放在仓库的 `_attic/docs/`（不入库），只作追溯，不作为口径。

## 现行（读这些）

| 文档 | 回答什么 |
|---|---|
| `../REPORT-STANDARD.md` | 报告写什么、怎么判合格、怎么验（唯一报告标准） |
| `../REPORT-BRIDGE-GUIDE.md` | 新角色/新能力怎么接入唯一产线 |
| `REPORT-LINES.md` | 报告产线地图（一条线、四种输入、保留零件） |
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

## 历史（已移出 docs/，在 `_attic/docs/`）

`REPORT-LINE-V4..V8.md`、`UPGRADE-PLAN-V3.md`、`SOP_ANALYTIC_LEARNING.md`、
`SOP_AUTONOMOUS_GOVERNANCE_OS.md`、`SOP_CHART_ENGINE_V2_UPGRADE.md`、
`WEIHE_AGENT_LEARNING.md`、`ROLE_CAPABILITY_MATRIX.md`。

恢复某一份：`cp _attic/docs/<文件> docs/`（`_attic` 在 `.gitignore` 里，需要时手动取回）。

## 数据文件

`actions_catalog.json`（由 `scripts/export_actions_catalog.py` 生成）、
`semantic_field_map.json`（由 `scripts/build_semantic_field_map.py` 生成）——
需要最新口径时重新生成，不要手改。

## 重构文档（在仓根 `交付/`）

| 文档 | 内容 |
|---|---|
| `报告产线-实际结构与问题-2026-11-18.md` | 改造前的实测诊断（12 环节 / 线路清点 / 24 条问题） |
| `报告产线重构-SOP-2026-11-18.md` | P1–P5 可执行 SOP |
| `SOP-P1-验收-2026-11-18.md` | P1 验收记录（删了什么、哈希证据、遗留项） |

# docs 索引（现行 10 份 / 其余归档）

> 2026-11-27 收口：docs/ 顶层只保留 10 份现行文档；其余（含旧 SOP、方案、记录、学习笔记）
> 全部移入 `docs/archive/`，文件头标 `status: ARCHIVED`，只作历史证据，不得直接作为施工依据。

## 现行（读这些）

| 文档 | 回答什么 |
|---|---|
| **`ARCHITECTURE-LEDGER.md`** | 分层账本：每个旧模块现在在哪、哪条叙事已废、守卫在哪 |
| `CORE-MAP.md` | `core/` 全图：每个文件干什么、在 flow 线哪一步 |
| `REPORT-LINES.md` | 报告产线地图（一条线、四种输入、项目根与 brief） |
| `GLOSSARY.md` | 术语口径：任务卡 / ClaimCard / 格子 / 门禁编号 / 职责键 |
| `ENTRYPOINTS.md` | 入口清单：对外只承诺 `guagua.py report`，其余为内部或诊断 |
| `GATES.md` | 门禁索引：每个 `check_*.py` 的消费者与触发方式（由 `gates_index.py` 生成） |
| **`MASTER-UPGRADE-SOP.md`** | 唯一系统升级总纲：当前决策、优先级、降级边界与 DoD |
| **`UPGRADE-PLAN.md`** | 本轮唯一执行分册：静态审查、主链接线、问题矩阵与未来同步文件 |
| `SKILL-LAYER-SPEC.md` | 一份合格 `SKILL.md` 的硬标准（六字段 + 十节 + 100 分口径） |
| `README.md` | 本索引 |

## 根目录入口文档（5 份）

`AGENTS.md`（跨宿主入口，生成物）· `README.md` · `SKILL.md` ·
`REPORT-STANDARD.md`（唯一报告标准）· `使用指南.md`

组织/协议/变更/许可等辅助文档仍在生效，收在 `docs/_entry/`：
`ORG.md` · `PROTOCOL.md` · `CHANGELOG.md` · `TEAM.md` ·
`REPORT-BRIDGE-GUIDE.md` · `THIRD_PARTY_NOTICES.md` · `蛙蛙呱呱人设设定.md`。

## 归档（`docs/archive/`）

`docs/archive/` 下全部文件只作历史证据。按主题大致分：

| 类别 | 代表文件 |
|---|---|
| 采集 / 供给 / 数据层 | `COLLECTION-COMPLIANCE.md`、`COLLECTION-SOP.md`、`SUPPLY-SOP.md`、`DATA-LAYER-SOP*.md`、`DATA-SHAPE-SOP.md`、`DERIVATION-SOP.md` |
| 协同 / 可行性 / 拆卡 | `COORDINATION-SOP.md`、`FEASIBILITY-SOP.md`、`AUTHORING-CONTRACT-*.md`、`PROJECT-RULES.md` |
| 报告子专题 | `REPORT-FLOW.md`、`REPORT-LAYOUTS.md`、`REPORT-PROSE-STYLE.md`、`REPORT-DATA-INTAKE.md`、`REPORT-OUTCOME-*.md`、`REPORT-SOURCE-GAP-POLICY.md`、`REPORT-GATE-CONTRACT.md`、`REPORT-FEATURE-FLAGS.md`、`REPORT-CAPABILITY-DECISIONS.md`、`REPORT-CONTENT-MODEL.md`、`REPORT-DISPATCH.md`、`REPORT_REFERENCE_LIBRARY.md`、`报告产线现状.md` |
| 图表 / 渲染 | `CHART-GRAMMAR.md`、`CHART_CRAFT_STUDY.md`、`RENDERER-DECISION.md` |
| 升级 / 技能 / 元方法 | `SKILL-MD-UPGRADE-PLAN.md`、`SOP_AGENT_META_UPGRADE.md` |

归档文件若与现行规则冲突，一律以 `MASTER-UPGRADE-SOP.md`、`UPGRADE-PLAN.md` 与当前源码为准。

## 数据文件

`actions_catalog.json`（由 `scripts/export_actions_catalog.py` 生成）、
`semantic_field_map.json`（由 `scripts/build_semantic_field_map.py` 生成）——
需要最新口径时重新生成，不要手改。

## 交付附件（`docs/archive/交付/`）

拆卡 SOP、协作层 SOP、报告系统升级 SOP、50 材料核验、专家团升级 v5 等原始设计与证据；
除 `generic_semantics_v1.yaml` 外，运行时不读取。

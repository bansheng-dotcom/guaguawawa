# 架构世代台账（ARCHITECTURE-LEDGER）

> 每个关注点只允许一个 CURRENT；其余必须标 LEGACY 并写清删除条件。
> 新增一层时，PR 必须在这里补一行：替代谁、何时删、删之前保留什么读路径。
> 生成口径见 `docs/_migration/wiring-truth.md`（机器可核）。

| 关注点 | CURRENT（唯一在跑） | LEGACY / 已删除 | 删除条件 / 备注 |
|---|---|---|---|
| 地基模块 | `core/base/`：paths / workspace / project / registry / protocol | 旧平铺 `core/<name>.py`（2026-11-26 已删除） | 包名不用 `platform`（遮蔽标准库） |
| 数据层 | `core/data/`：analysis_desk / unit / pipeline、data_*、dataset*、fact_table、evidence_pack | 旧平铺 `core/<name>.py`（2026-11-26 已删除） | 包名 `data` 已在 boundary_allowlist 登记 |
| 来源层 | `core/sources/`：source_*、collection_*、coverage_*、supply_plan、research_* | 旧平铺 `core/<name>.py`（2026-11-26 已删除） | 同上 |
| 图表层 | `core/charts/`：16 个模块（13 个原平铺 chart_* + 3 个渲染器） | 旧平铺 `core/chart_*.py`（2026-11-26 已删除） | `python -m core.charts.chart_capabilities` 是唯一 CLI 入口 |
| 断言层 | `core/claims/`：claims（含映射层）/ claim_consistency / cell_claim / cells_claims / cells_unified | 旧平铺 `core/<name>.py`（2026-11-26 已删除）；`claims_v4`（2026-11-27 并入 claims） | `python -m core.claims.claim_consistency` 是唯一 CLI 入口 |
| 卡片层 | `core/cards/`：card_plan / card_issue / card_probe / card_bundle / card_upgrade / dispatch / report_dispatch | 旧平铺 `core/<name>.py`（2026-11-26 已删除） | `core.cards` 是真子包，另映射 7 个已归位成员（cells_claims / collection_contract / research_* 等） |
| 报告层 | `core/report/`：19 个 `report_*` + flow_report | 旧平铺 `core/report_*.py`（2026-11-26 已删除） | `report_kernel/`、`report_theme/` 已是真包，保持原地（迁入会产生双重模块身份） |
| 报告入口 | `report run-line` → `report_line` → `decision_report` → `report_flow` | `report_cli` 的 v10/v11 说法、`flow_report` 模板线 | `report_line` 目前是转发层；统一门面后合并 |
| 拆卡 / 收卡 | 外部只走 `core/cards/pipeline.py`（P5-3，2026-11-27）；实现仍在 `report_dispatch`（发/验）+ `card_issue`（拆/探）+ `dispatch.collect`（收） | `dispatch` v12.2 的旧叙事 | 合并为 `cards/pipeline` 单一实现后，三个模块退场 |
| 断言模型 | `core/claims/claims.py`（论证层 + 映射层，P5-4 合并）；字段与契约版本见 `core/claims/contract.py`（P5-1） | `claims_v4.py`（2026-11-27 并入 claims）；`claim_card` / `claim_gate`（2026-11-26 已删除） | 统一 schema 为 ClaimCard 后动；在此之前字段只许从 contract 读 |
| 格子读数 | `cells_unified.observations()` | `cells_claims` 的 v1/v2/v3 三入口 | 单一读数稳定后下线旧入口 |
| 报告正文 | `core/prose/`：prose_spec / prose_candidates / prose_style；`report_prose_gen` 随报告线在 `core/report/`；阈值兜底见 `report_contract.PROSE_DEFAULTS`（P5-2，2026-11-27） | 旧平铺 `core/prose_*.py`（2026-11-26 已删除）；`prose_critic`（已删除） | 合并为 `prose_contract` + `prose_render` 时动；阈值只许配置 + 一处兜底 |
| 图表 | 14 个 `chart_*` + `core/charts` + `report_theme` | `chart_fit`（2026-11-26 已删除） | 选型只保留 `report_flow.chart_fitness_errors` 一份 |
| 覆盖矩阵 | `coverage_plan` / `coverage_confirm` / `coverage_policy` / `coverage_wire` | `coverage_cli` / `task_frame` / `task_research`（2026-11-26 已删除） | `dispatch` 内联产出 `task_frame.json`，不再有独立 CLI |
| 门禁 | `check_report_flow` F1–F12 + `check_gates` + `ci_report_checks` | `gate_chain`（2026-11-26 已删除） | 以 F 编号为唯一索引；新增门禁先登记 |
| 知识注入 | `experience_cards` + `knowledge_base` + `expert_brief` | `core/__init__` 的 10 个懒加载分组（零实际 import） | 决定删除或改成真实包结构后再动 |
| 文档入口 | `AGENTS.md` / `REPORT-LINES.md` / `CORE-MAP.md` | 6 份 `status: ARCHIVED` 的历史 SOP | 归档保留，不再作为接入依据 |
| 包导出 | `core/__init__`：8 个真子包 + 8 个懒加载分组 + runner | 旧的 100+ 平铺导出（2026-11-26 随 shim 删除） | 保持 ≤20 个常用入口 |

## 使用规则

1. 新层合并前，先在表里把旧层改成 LEGACY，并写删除条件；空着不许合并。
2. 旧层删除后，同步删 `docs/_migration/wiring-debt.json` 对应项与本文对应行。
3. `wiring_truth --check` 与 `check_dead_code --check` 是这张表的机器版本；两者冲突时以机器为准。

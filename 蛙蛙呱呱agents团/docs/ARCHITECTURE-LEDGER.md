# 架构世代台账（ARCHITECTURE-LEDGER）

> 每个关注点只允许一个 CURRENT；其余必须标 LEGACY 并写清删除条件。
> 新增一层时，PR 必须在这里补一行：替代谁、何时删、删之前保留什么读路径。
> 生成口径见 `docs/_migration/wiring-truth.md`（机器可核）。

| 关注点 | CURRENT（唯一在跑） | LEGACY / 已删除 | 删除条件 / 备注 |
|---|---|---|---|
| 地基模块 | `core/base/`：paths / workspace / project / registry / protocol | 旧 `core/<name>.py` shim（模块别名） | P4 全部包迁完后统一删 shim；包名不用 `platform`（遮蔽标准库） |
| 数据层 | `core/data/`：analysis_desk / unit / pipeline、data_*、dataset*、fact_table、evidence_pack | 旧 `core/<name>.py` shim | 同上；包名 `data` 已在 boundary_allowlist 登记 |
| 来源层 | `core/sources/`：source_*、collection_*、coverage_*、supply_plan、research_* | 旧 `core/<name>.py` shim | 同上 |
| 报告入口 | `report run-line` → `report_line` → `decision_report` → `report_flow` | `report_cli` 的 v10/v11 说法、`flow_report` 模板线 | `report_line` 目前是转发层；统一门面后合并 |
| 拆卡 / 收卡 | `report_dispatch`（发卡）+ `card_issue`（拆卡）+ `dispatch.collect`（收卡） | `dispatch` v12.2 的旧叙事 | 合并为 `cards/pipeline` 时删旧描述 |
| 断言模型 | `claims.py` + `claims_v4.py` | `claim_card` / `claim_gate`（2026-11-26 已删除） | 收敛为新 ClaimCard 后删 `claims_v4` |
| 格子读数 | `cells_unified.observations()` | `cells_claims` 的 v1/v2/v3 三入口 | 单一读数稳定后下线旧入口 |
| 报告正文 | `prose_spec`（11 字段）+ `report_prose_gen` + `prose_candidates` + `prose_style` | `prose_critic`（2026-11-26 已删除） | 合并为 `prose_contract` + `prose_render` |
| 图表 | 14 个 `chart_*` + `core/charts` + `report_theme` | `chart_fit`（2026-11-26 已删除） | 选型只保留 `report_flow.chart_fitness_errors` 一份 |
| 覆盖矩阵 | `coverage_plan` / `coverage_confirm` / `coverage_policy` / `coverage_wire` | `coverage_cli` / `task_frame` / `task_research`（2026-11-26 已删除） | `dispatch` 内联产出 `task_frame.json`，不再有独立 CLI |
| 门禁 | `check_report_flow` F1–F12 + `check_gates` + `ci_report_checks` | `gate_chain`（2026-11-26 已删除） | 以 F 编号为唯一索引；新增门禁先登记 |
| 知识注入 | `experience_cards` + `knowledge_base` + `expert_brief` | `core/__init__` 的 10 个懒加载分组（零实际 import） | 决定删除或改成真实包结构后再动 |
| 文档入口 | `AGENTS.md` / `REPORT-LINES.md` / `CORE-MAP.md` | 6 份 `status: ARCHIVED` 的历史 SOP | 归档保留，不再作为接入依据 |
| 包导出 | `core/__init__` 分组（当前 100+ 名字） | 114 个导出、15 个重复 | 缩到 ≤20 个常用入口 |

## 使用规则

1. 新层合并前，先在表里把旧层改成 LEGACY，并写删除条件；空着不许合并。
2. 旧层删除后，同步删 `docs/_migration/wiring-debt.json` 对应项与本文对应行。
3. `wiring_truth --check` 与 `check_dead_code --check` 是这张表的机器版本；两者冲突时以机器为准。

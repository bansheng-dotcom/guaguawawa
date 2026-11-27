# core/ 内部耦合审计（couplings）

> 由 `python scripts/audit_core_paths.py --write` 生成，禁止手改。
> 口径：静态 import 分析；只统计 core 内部模块之间的边，不含 tests/scripts。

## 汇总

| 指标 | 数量 |
|---|---:|
| core 模块 | 166 |
| 内部 import 边 | 423 |
| 跨包边 | 289 |
| 循环（SCC>1） | 4 |

## 包间耦合

| 从 | 到 | 边数 | 代表 |
|---|---|---:|---|
| `core.cards` | `core.sources` | 16 | core.cards.card_issue → core.sources |
| `core.report` | `core.charts` | 11 | core.report.report_cli → core.charts.chart_capabilities |
| `core.report` | `core.report_theme` | 11 | core.report.flow_report → core.report_theme |
| `core.report` | `core.sources` | 9 | core.report.report_cli → core.sources |
| `core.cards` | `core.data` | 8 | core.cards.card_issue → core.data |
| `core.cards` | `core.report` | 8 | core.cards.card_issue → core.report |
| `core.report` | `core` | 6 | core.report.flow_report → core |
| `core.cards` | `core.claims` | 5 | core.cards.dispatch → core.claims |
| `core.report` | `core.prose` | 5 | core.report.flow_report → core.prose |
| `core.cards` | `core` | 4 | core.cards.card_issue → core |
| `core.cards` | `core.base` | 4 | core.cards.card_bundle → core.base |
| `core.charts` | `core.report_theme` | 4 | core.charts.chart_candidates → core.report_theme.charts_pro.spec |
| `core.claims` | `core.data` | 4 | core.claims.cell_claim → core.data |
| `core.decision_report` | `core.report` | 4 | core.decision_report → core.report |
| `core.ingest` | `core.base` | 4 | core.ingest.runner → core.base |
| `core.quality_gate` | `core.report` | 4 | core.quality_gate → core.report |
| `core.report` | `core.base` | 4 | core.report.report_cli → core.base |
| `core.report` | `core.claims` | 4 | core.report.report_assembly → core.claims |
| `core.report` | `core.data` | 4 | core.report.report_cli → core.data |
| `core.report_theme` | `core.report` | 4 | core.report_theme.kit → core.report.report_marks |
| `core.cards` | `core.roster` | 3 | core.cards.card_issue → core.roster |
| `core.charts` | `core.data` | 3 | core.charts.chart_field_contract → core.data |
| `core.collect_schema` | `core.ingest` | 3 | core.collect_schema → core.ingest |
| `core.decision` | `core.charts` | 3 | core.decision → core.charts |
| `core.decision_report` | `core.data` | 3 | core.decision_report → core.data |
| `core.methods` | `core.analysis_methods` | 3 | core.methods → core.analysis_methods |
| `core.report` | `core.cards` | 3 | core.report.report_cli → core.cards |
| `core.report` | `core.report_kernel` | 3 | core.report.report_flow → core.report_kernel |
| `core.report_theme` | `core.charts` | 3 | core.report_theme.pages → core.charts |
| `core.cards` | `core.charts` | 2 | core.cards.card_upgrade → core.charts |
| `core.cards` | `core.panel` | 2 | core.cards.card_issue → core.panel |
| `core.claims` | `core.report` | 2 | core.claims.claims → core.report |
| `core.claims` | `core.sources` | 2 | core.claims.cells_claims → core.sources |
| `core.collect_schema` | `core.base` | 2 | core.collect_schema → core.base |
| `core.collect_schema` | `core.sources` | 2 | core.collect_schema → core.sources |
| `core.collectors` | `core.sources` | 2 | core.collectors.csv_manual → core.sources |
| `core.data` | `core.base` | 2 | core.data.data_model → core.base |
| `core.data` | `core.charts` | 2 | core.data.data_shape → core.charts |
| `core.data` | `core.claims` | 2 | core.data.dataset_gates → core.claims |
| `core.decision` | `core.data` | 2 | core.decision → core.data |
| `core.decision_report` | `core.sources` | 2 | core.decision_report → core.sources |
| `core.drill` | `core.claims` | 2 | core.drill → core.claims |
| `core.drill` | `core.data` | 2 | core.drill → core.data |
| `core.drill` | `core.sources` | 2 | core.drill → core.sources |
| `core.grain` | `core.sources` | 2 | core.grain → core.sources |
| `core.grid_attach` | `core.cards` | 2 | core.grid_attach → core.cards |
| `core.ingest` | `core.data` | 2 | core.ingest.runner → core.data |
| `core.ingest` | `core.sources` | 2 | core.ingest.runner → core.sources |
| `core.ir_adapters` | `core.report` | 2 | core.ir_adapters → core.report |
| `core.methods` | `core` | 2 | core.methods → core |
| `core.methods` | `core.report` | 2 | core.methods → core.report |
| `core.orchestrator` | `core.data` | 2 | core.orchestrator → core.data |
| `core.r04_audit` | `core.prose` | 2 | core.r04_audit → core.prose |
| `core.r04_audit` | `core.sources` | 2 | core.r04_audit → core.sources |
| `core.report_kernel` | `core` | 2 | core.report_kernel → core |
| `core.runner` | `core.base` | 2 | core.runner → core.base |
| `core.semantic_pipeline` | `core.charts` | 2 | core.semantic_pipeline → core.charts |
| `core.semantic_pipeline` | `core.report` | 2 | core.semantic_pipeline → core.report |
| `core.sources` | `core.base` | 2 | core.sources.collection_spec → core.base |
| `core.sources` | `core.ingest` | 2 | core.sources.collection_spec → core.ingest |
| `core.synthesis` | `core.charts` | 2 | core.synthesis → core.charts |
| `core` | `core.base` | 1 | core → core.base |
| `core` | `core.cards` | 1 | core → core.cards |
| `core` | `core.charts` | 1 | core → core.charts |
| `core` | `core.claims` | 1 | core → core.claims |
| `core` | `core.data` | 1 | core → core.data |
| `core` | `core.prose` | 1 | core → core.prose |
| `core` | `core.report` | 1 | core → core.report |
| `core` | `core.sources` | 1 | core → core.sources |
| `core.analysis_methods` | `core` | 1 | core.analysis_methods → core |
| `core.analysis_methods` | `core.method_params` | 1 | core.analysis_methods → core.method_params |
| `core.analysis_methods` | `core.runner` | 1 | core.analysis_methods → core.runner |
| `core.cards` | `core.collab` | 1 | core.cards.card_issue → core.collab |
| `core.cards` | `core.demand` | 1 | core.cards.card_probe → core.demand |
| `core.cards` | `core.dor` | 1 | core.cards.card_issue → core.dor |
| `core.cards` | `core.drill` | 1 | core.cards.card_issue → core.drill |
| `core.cards` | `core.intake` | 1 | core.cards.card_issue → core.intake |
| `core.cards` | `core.synthesis` | 1 | core.cards.dispatch → core.synthesis |
| `core.claims` | `core` | 1 | core.claims.cells_claims → core |
| `core.claims` | `core.drill` | 1 | core.claims.cells_claims → core.drill |
| `core.collect_schema` | `core` | 1 | core.collect_schema → core |
| `core.collectors` | `core` | 1 | core.collectors.csv_manual → core |
| `core.collectors` | `core.grain` | 1 | core.collectors.csv_manual → core.grain |
| `core.data` | `core` | 1 | core.data.analysis_desk → core |
| `core.data` | `core.method_params` | 1 | core.data.analysis_desk → core.method_params |
| `core.decision` | `core` | 1 | core.decision → core |
| `core.decision` | `core.analysis_methods` | 1 | core.decision → core.analysis_methods |
| `core.decision` | `core.methods` | 1 | core.decision → core.methods |
| `core.decision_report` | `core` | 1 | core.decision_report → core |
| `core.decision_report` | `core.analysis_methods` | 1 | core.decision_report → core.analysis_methods |
| `core.decision_report` | `core.decision` | 1 | core.decision_report → core.decision |
| `core.decision_report` | `core.methods` | 1 | core.decision_report → core.methods |
| `core.decision_report` | `core.orchestrator` | 1 | core.decision_report → core.orchestrator |
| `core.decision_report` | `core.quality_gate` | 1 | core.decision_report → core.quality_gate |
| `core.decision_report` | `core.shape_gate` | 1 | core.decision_report → core.shape_gate |
| `core.domain_pack` | `core` | 1 | core.domain_pack → core |
| `core.domain_pack` | `core.skill_bridge` | 1 | core.domain_pack → core.skill_bridge |
| `core.drill` | `core` | 1 | core.drill → core |
| `core.drill` | `core.grain` | 1 | core.drill → core.grain |
| `core.grid_attach` | `core` | 1 | core.grid_attach → core |
| `core.grid_attach` | `core.roster` | 1 | core.grid_attach → core.roster |
| `core.ingest` | `core` | 1 | core.ingest → core |
| `core.ingest` | `core.runner` | 1 | core.ingest → core.runner |
| `core.ir_to_contract` | `core.charts` | 1 | core.ir_to_contract → core.charts.chart_payload |
| `core.methods` | `core.method_params` | 1 | core.methods.research → core.method_params |
| `core.orchestrator` | `core` | 1 | core.orchestrator → core |
| `core.orchestrator` | `core.analysis_methods` | 1 | core.orchestrator → core.analysis_methods |
| `core.orchestrator` | `core.methods` | 1 | core.orchestrator → core.methods |
| `core.prose` | `core.report` | 1 | core.prose.prose_contract → core.report.report_contract |
| `core.quality_gate` | `core` | 1 | core.quality_gate → core |
| `core.quality_gate` | `core.r04_audit` | 1 | core.quality_gate → core.r04_audit |
| `core.r04_audit` | `core.data` | 1 | core.r04_audit → core.data.data_shape |
| `core.report` | `core.analysis_methods` | 1 | core.report.report_cli → core.analysis_methods |
| `core.report` | `core.decision_report` | 1 | core.report.report_line → core.decision_report |
| `core.report` | `core.grid_attach` | 1 | core.report.report_cli → core.grid_attach |
| `core.report` | `core.intake` | 1 | core.report.report_cli → core.intake |
| `core.report` | `core.ir_adapters` | 1 | core.report.report_flow → core.ir_adapters |
| `core.report` | `core.method_params` | 1 | core.report.report_assembly → core.method_params |
| `core.report` | `core.methods` | 1 | core.report.report_cli → core.methods |
| `core.report` | `core.parallel_research` | 1 | core.report.report_cli → core.parallel_research |
| `core.report` | `core.quality_gate` | 1 | core.report.report_flow → core.quality_gate |
| `core.report` | `core.r04_audit` | 1 | core.report.flow_report → core.r04_audit |
| `core.report` | `core.r04_derive` | 1 | core.report.report_flow → core.r04_derive |
| `core.report` | `core.runner` | 1 | core.report.report_flow → core.runner |
| `core.report` | `core.semantic_pipeline` | 1 | core.report.report_flow → core.semantic_pipeline |
| `core.report` | `core.skill_graph` | 1 | core.report.report_roles → core.skill_graph |
| `core.report_kernel` | `core.report` | 1 | core.report_kernel.gate → core.report.report_quality |
| `core.report_theme` | `core` | 1 | core.report_theme → core |
| `core.report_theme` | `core.data` | 1 | core.report_theme.pages → core.data.data_shape |
| `core.roster` | `core.base` | 1 | core.roster → core.base.registry |
| `core.skill_bridge` | `core` | 1 | core.skill_bridge → core |
| `core.skill_bridge` | `core.runner` | 1 | core.skill_bridge → core.runner |
| `core.sources` | `core` | 1 | core.sources.collection_spec → core |
| `core.sources` | `core.collectors` | 1 | core.sources.collection_spec → core.collectors |
| `core.sources` | `core.data` | 1 | core.sources.coverage_plan → core.data.data_shape |
| `core.sources` | `core.grain` | 1 | core.sources.collection_spec → core.grain |

## 扇出 Top 20（这个模块 import 了多少 core 模块）

| 模块 | 扇出 |
|---|---:|
| `core.report.report_flow` | 37 |
| `core.report.report_cli` | 26 |
| `core.cards.dispatch` | 25 |
| `core.cards.card_issue` | 18 |
| `core.decision_report` | 16 |
| `core.ingest.runner` | 11 |
| `core.report.flow_report` | 11 |
| `core.cards.card_probe` | 10 |
| `core.cards.report_dispatch` | 10 |
| `core.report_theme.pages` | 10 |
| `core.claims.cells_claims` | 9 |
| `core.report_theme.charts_pro.spec` | 9 |
| `core.sources.collection_spec` | 9 |
| `core` | 8 |
| `core.collect_schema` | 8 |
| `core.decision` | 8 |
| `core.drill` | 8 |
| `core.methods` | 7 |
| `core.cards.card_upgrade` | 6 |
| `core.collectors.csv_manual` | 6 |

## 扇入 Top 20（有多少模块依赖它）

| 模块 | 扇入 |
|---|---:|
| `core` | 30 |
| `core.sources` | 21 |
| `core.data` | 18 |
| `core.report` | 14 |
| `core.base` | 12 |
| `core.claims` | 10 |
| `core.base.paths` | 9 |
| `core.charts` | 9 |
| `core.report_theme.charts_pro` | 9 |
| `core.report_theme.charts_pro.prokit_helpers` | 9 |
| `core.cards` | 8 |
| `core.analysis_methods` | 7 |
| `core.report_theme.charts_pro.spec` | 7 |
| `core.sources.source_profile` | 7 |
| `core.claims.contract` | 5 |
| `core.cards.card_upgrade` | 4 |
| `core.collectors` | 4 |
| `core.collectors.base` | 4 |
| `core.data.analysis_desk` | 4 |
| `core.data.data_model` | 4 |

## 循环依赖（SCC > 1）

- `core.cards.card_issue` ↔ `core.cards.report_dispatch`
- `core.collectors` ↔ `core.collectors.csv_manual` ↔ `core.collectors.openfoodfacts` ↔ `core.collectors.web_search`
- `core.quality_gate` ↔ `core.report.report_flow`
- `core.report_theme.charts_pro.layout` ↔ `core.report_theme.charts_pro.spec`

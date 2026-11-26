# core/ 全图：每个文件干什么 + 在 flow 线哪一步

> 生成依据：`core/` 下 139 个 .py 的模块 docstring（2026-11-23 实抽，不是回忆）。
> 主线定义见 `docs/REPORT-LINES.md` 的 S0–S7。

---

## 0.1 怎么用（逻辑分组入口，物理不动）

139 个文件**仍在 `core/` 平铺**（零迁移风险），但对外多了一层按层访问的入口：

```python
from core import gates, pipeline, cards, semantic, narrative, charts, render

gates.quality_gate          # == core.quality_gate
pipeline.report_flow        # == core.report_flow
cards.card_issue            # == core.card_issue
semantic.report_ir          # == core.report_ir
narrative.claims_v4         # == core.claims_v4
charts.chart_grammar        # == core.chart_grammar
render.report_theme         # == core.report_theme
```

- 全部**懒加载**：`import core` 只多加载 1 个模块，访问到谁才导入谁。
- 分组名与 `docs/CORE-MAP.md` 的 13 层一一对应（`collab` 因与 `core/collab.py`
  同名，协作组改叫 `coordination`）。
- 没有 import 语义变化：`from core.report_flow import run` 照旧可用。

---

## 0. 一分钟看懂主线

```
S0 输入识别   report_line.detect_mode()          → input_mode.json
S1 意图→域    orchestrator.plan()                → decisions.json
S2 专家编排   roster / report_roles / skill_graph
S3 专家作答   methods/* + analysis_methods       → findings
S4 叙事装配   report_assembly / report_editorial → 节
S5 排版出图   report_flow → report_bridge → report_renderer → charts_pro
S6 三层质检   quality_gate / report_quality / report_kernel
S7 交付       report.html + report.md + report.pdf + manifest.json
```

**真正被主线调用的文件只有约 30 个**；其余是拆卡线、数据层、图表库、门禁、辅助工具。
下面按"层"分组，每行标 `【Sx】` 或 `【拆卡】/【图表】/【数据】/【门禁】/【辅助】/【空】`。

---

## 1. 入口与编排（主线骨架）

| 文件 | 行 | 干什么 | flow 线角色 |
|---|---|---|---|
| `report_cli.py` | 904 | CLI 唯一入口：clarify/brief/collect/run-line/check/flow… | 【S0】所有命令的入口 |
| `report_line.py` | 183 | 唯一报告生产线：`detect_mode` + `build` | 【S0】判输入模式，转发到 decision_report 或 claims |
| `report_dispatch.py` | 616 | 三段可审文件：brief → collect → report | 【S2/S3】拆卡线的调度 |
| `report_flow.py` | 1484 | **唯一报告产线**：契约装配 + 渲染 + 门禁 | 【S4/S5】核心，`build_sections_contract` 在这 |
| `report_bridge.py` | 243 | 共享渲染桥：contract → HTML/MD/PDF | 【S5/S7】产物出口 |
| `report_renderer.py` | 1599 | 确定性 HTML 渲染器（70 型 + 8 主题） | 【S5】`validate_contract` + `render` |
| `decision_report.py` | 431 | 决策优先的报告装配（report decide） | 【S4】数据分支的装配器 |
| `flow_report.py` | 245 | **项目代码宿主**：从项目目录加载 facts/charts/prose_specs | 【S5 旁路】项目自带代码时用 |
| `report_layout.py` | 36 | 版式默认值（flow/paper） | 【S5】读 configs |
| `report_contract.py` | 73 | 所有阈值只从这里读 | 【S6】阈值单一出处 |

## 2. 意图与决策（S1）

| 文件 | 行 | 干什么 | 角色 |
|---|---|---|---|
| `orchestrator.py` | 359 | 专家编排：谁出场由"你的问题"决定 | 【S1】意图→域→角色 |
| `decision.py` | 702 | 决策契约：报告的上游唯一对象 | 【S1】3–5 问 + 对照 + 图型 |
| `report_clarify.py` | 317 | 澄清卡：把模糊需求逼成可回答的问题 | 【S1】先对齐再动手 |
| `intake.py` | 145 | 输入归一（SOP v5） | 【S0/S1】 |
| `report_thesis.py` | 137 | 纲领（只保留 analysis 一条） | 【S1】 |
| `report_structure.py` | 75 | 结构 profile（decision/brief 模块裁剪） | 【S1/S4】 |
| `domain_pack.py` | 407 | 业务线 → 领域编队（**允许的文件，行业关键词包**） | 【S1】 |
| `dor.py` | 57 | 就绪定义（Definition of Ready） | 【S1】门禁 |

## 3. 专家与技能（S2/S3）

| 文件 | 行 | 干什么 | 角色 |
|---|---|---|---|
| `roster.py` | 141 | 完整专家名册（从角色目录生成，不手写） | 【S2】 |
| `registry.py` | 246 | 20 角色注册表：能力唯一事实来源 | 【S2】 |
| `report_roles.py` | 325 | 角色适配层：哪些技能能进报告 | 【S2/S3】 |
| `skill_graph.py` | 126 | 角色→技能→动作 的可调度注册表 | 【S2】 |
| `skill_bridge.py` | 130 | 领域方法 ↔ 现有技能的接入层 | 【S3】 |
| `methods/__init__.py` | 118 | 方法注册表装配 | 【S3】 |
| `methods/spec.py` | 165 | 方法注册表：能力声明 + 自动挂载 | 【S3】 |
| `methods/generic.py` | 913 | 通用方法：订单/评价/履约/投放/优先级/容量/故障/商品 | 【S3】 |
| `methods/research.py` | 319 | 研究类方法：规模多路径/集中度/增长/单位经济/进入闸门 | 【S3】 |
| `analysis_methods.py` | 1545 | 分析方法库：每个方法产出一条带数字的判断 | 【S3】 |
| `analysis_desk.py` | 496 | 数据台：把项目目录归一成可算的观测 | 【S3】前置 |
| `analysis_pipeline.py` | 100 | 最小编排：data → skill → assert → report | 【S3】 |
| `domain_pack.py` | — | 见 S1 | |

## 4. 数据与证据（S3 前置）

| 文件 | 行 | 干什么 | 角色 |
|---|---|---|---|
| `fact_table.py` | 396 | 把带来源观测归一成可查事实表 | 【S3】 |
| `evidence_pack.py` | 282 | 把全部输入收成"可寻址的数字索引" | 【S3/S4】 |
| `data_model.py` | 309 | 数据模型：切片/维度/度量 | 【S3】 |
| `data_profile.py` | 96 | 先看数据长什么样，再决定能问什么 | 【S0/S3】 |
| `data_shape.py` | 88 | 数据形状 → 图型适配 | 【S3/S5】 |
| `data_contract.py` | 223 | 数据契约：列名/类型/日期/枚举/范围校验 | 【S3】 |
| `source_verify.py` | 143 | 来源两级核验 | 【S6】 |
| `coverage_plan.py` | 123 | 覆盖计划 + 出稿前门禁 | 【S1/S6】 |
| `coverage_confirm.py` | 81 | 覆盖确认 | 【S1】 |
| `coverage_policy.py` | 51 | 覆盖阈值策略 | 【S6】 |
| `panel.py` | 89 | 分析 = 面板上的运算 | 【S3】 |

## 4.1 采集层（v3 粒度 / v4 推导 / v5 降级）

> 业务无关：代码只认 grain 与目录，业务词只活在项目目录的 YAML 里。

| 文件 | 干什么 | 角色 |
|---|---|---|
| `source_profile.py` | 源画像：原子粒度 / 字段 / 历史可得性 | 【S3】采集 |
| `grain.py` | 粒度运算与校验（G-A~G-E）+ 安全算术 + derive DSL（field/substr/token/split/bucket/calc） | 【S3】采集 |
| `collection_spec.py` | 采集规格（源+rollup+claim）+ `preview`/`quality` 样本验证 | 【S3】采集 |
| `collection_gen.py` | 从「需求+匹配」生成候选规格（`generated` 标记，手改不覆盖） | 【S3】采集 |
| `demand.py` | 网格 → 采集需求（度量 × 粒度 × 维度） | 【拆卡→S3】 |
| `source_match.py` | 需求 × 源 匹配（DERIVE/MEASURE 目录，三态 full/partial/none） | 【拆卡→S3】 |
| `supply_plan.py` | **拆卡前**数据供给方案（A/B/C 源 + 计划 L1/L2 + 补采条件） | 【S0】 |
| `card_probe.py` | **拆卡后**可行性测试 + 降级（三态 + tried/why） | 【拆卡→S3】 |
| `collectors/base.py` | 采集器协议与注册表 | 【S3】采集 |
| `collectors/csv_manual.py` | 手工 CSV 采集器 | 【S3】采集 |
| `collectors/web_search.py` | 网页采集器（urllib + XPath，0 行必报错） | 【S3】采集 |
| `collectors/openfoodfacts.py` | Open Food Facts API 采集器 | 【S3】采集 |
| `dataset.py` | 数据集 schema（`dsh.dataset/v1`） | 【S3】 |
| `cell_claim.py` | 判断格 schema（`dsh.cell_claim/v1`） | 【S3】 |
| `drill.py` | 纵向钻取（v2）+ 从 rollup 推导（v3） | 【拆卡→S3】 |
| `dataset_gates.py` | G1'/G3'/G4'/G5' + 派生 G-ROLLUP / G-PREVIEW（软） | 【S6】 |
| `dataset_query.py` | 数据集查询 + 出图（hbar/line/stacked_bar） | 【S5】 |

## 5. 拆卡与发卡（brief → collect）

| 文件 | 行 | 干什么 | 角色 |
|---|---|---|---|
| `card_plan.py` | 86 | 发卡计划规则 | 【拆卡】 |
| `card_issue.py` | 422 | 拆卡五轴 + S1–S12 发卡前门禁 | 【拆卡】发卡 |
| `card_upgrade.py` | 1118 | 五轴 builders + G1–G25 收卡后门禁 + `post_collect` | 【拆卡】收卡 |
| `grid_attach.py` | 135 | 把六维网格追加到每张 TASK.md | 【拆卡】 |
| `cells_claims.py` | 304 | 拆卡格子 → 报告 claims 的桥 | 【拆卡→S4】 |
| `collection_contract.py` | 128 | 采集契约（dsh.collection/v1） | 【拆卡】 |
| `dispatch.py` | 624 | 按 brief 发卡、收 claims、合并（v12.2） | 【拆卡】 |
| `report_exchange.py` | 120 | 卡间协商（needs → INBOX） | 【拆卡】 |
| `collab.py` | 138 | 真的调用 R02 的 agent | 【拆卡】 |
| `protocol.py` | 89 | 交接协议：端口/任务卡/事件 | 【拆卡/协作】 |
| `parallel_research.py` | 109 | 并行调研编排 | 【拆卡】旁路 |
| `research_protocol.py` | 139 | 调研交付契约（不含行业清单） | 【拆卡】 |
| `research_intake.py` | 354 | 新业务研究入口：采集 → 校验 → 台账 → 成稿 | 【拆卡→S4】 |

## 6. 语义 / IR（S3→S4 之间）

| 文件 | 行 | 干什么 | 角色 |
|---|---|---|---|
| `report_ir.py` | 137 | 富 IR（dsh.report_ir/v1）+ validate + infer_relation | 【S3/S4】 |
| `ir_adapters.py` | 377 | 三前端：claims/decision/facts → IR | 【S3/S4】 |
| `semantic_pipeline.py` | 111 | IR → 已解析模型（纯函数） | 【S3/S4】 |
| `ir_to_contract.py` | 131 | 已解析模型 → 渲染契约 | 【S4/S5】 |
| `report_model.py` | 141 | 报告系统单一模型（问题→维度→方法→图型）+ 引用完整性审计 | 【S1/S6】 |

## 7. 论证与叙事（S4）

| 文件 | 行 | 干什么 | 角色 |
|---|---|---|---|
| `claims.py` | 471 | 论证层：数字 → 可检验判断 | 【S4】 |
| `claims_v4.py` | 240 | claim → slice → encoding → findings → 五块 | 【S4】 |
| `claim_consistency.py` | 156 | 交叉质询：同一个数两个说法 | 【S6】 |
| `report_assembly.py` | 397 | finding → 节/指标/计数 | 【S4】 |
| `report_editorial.py` | 342 | 编辑层：verdict/kicker 等契约 | 【S4】 |
| `synthesis.py` | 136 | 论点 → 节（SOP v5） | 【S4】 |

## 8. 图表（S5）

| 文件 | 行 | 干什么 | 角色 |
|---|---|---|---|
| `chart_grammar.py` | 294 | 图形语法（47 型 + 编码约束） | 【S5】选型 |
| `chart_chooser.py` | 94 | 按关系选图 | 【S5】选型 |
| `chart_relation.py` | 93 | 关系 → 图型适配器 | 【S5】 |
| `chart_candidates.py` | 99 | 合法下限（不决定图型） | 【S5】校验 |
| `chart_payload.py` | 72 | facts → 某图型 payload | 【S5】适配 |
| `chart_query.py` | 113 | 面板 → 热力图/线/份额条 | 【S5】矩阵出图 |
| `chart_shapes.py` | 128 | 数据形状 → 图型 | 【S5】 |
| `chart_spec.py` | 25 | 图表规格契约（先声明证明什么） | 【S5】 |
| `chart_contract.py` | 112 | 图合同（三条线现状） | 【S5】 |
| `chart_plan.py` | 120 | 自动选图 + 规格（v12.4） | 【S5】 |
| `chart_units.py` | 102 | 一张图只能一个单位 | 【S5】 |
| `chart_capabilities.py` | 77 | 48 型能力注册表 | 【S5】 |
| `charts/chart_lib.py` | 684 | 48 个可视化提示词接成规格库 | 【S5】 |
| `charts/chart_renderers_ext.py` | 1936 | 48 图谱确定性 SVG（含地图坐标） | 【S5】 |
| `charts/consulting.py` | 569 | consulting 主题 14 型 SVG | 【S5】 |

## 9. 渲染底座（S5）

| 文件 | 行 | 干什么 | 角色 |
|---|---|---|---|
| `report_theme/__init__.py` | 5 | consulting 主题入口 | 【S5】 |
| `report_theme/pages.py` | 730 | 页面构造：cover/summary/toc/page | 【S5】 |
| `report_theme/flow.py` | 161 | flow 版式：flowify / render_flow | 【S5】 |
| `report_theme/blocks.py` | 42 | 可复用 flow 区块 | 【S5】 |
| `report_theme/kit.py` | 648 | 杂志式页面构造（action/appendix/back） | 【S5 旁路】项目代码路径用 |
| `report_theme/chartkit.py` | 195 | 自包含 SVG 基元 + 通用图型 | 【S5】 |
| `report_theme/charts_pro/__init__.py` | 31 | 生产图型库（70 型，懒加载样例） | 【S5】 |
| `report_theme/charts_pro/spec.py` | 405 | 参数化图表层：{type,data} → SVG | 【S5】 |
| `report_theme/charts_pro/spec_families.py` | 420 | 条形族 + 折线族 | 【S5】 |
| `report_theme/charts_pro/spec_more.py` | 140 | slope/dumbbell/small_mult/box/scatter | 【S5】 |
| `report_theme/charts_pro/spec_points.py` | 435 | 点位族 + 构成族（18 型） | 【S5】 |
| `report_theme/charts_pro/spec_space.py` | 186 | 空间/流程/派生 | 【S5】 |
| `report_theme/charts_pro/spec_stats.py` | 289 | 统计族 + 时间族 | 【S5】 |
| `report_theme/charts_pro/spec_time.py` | 119 | gantt/timeline/cal_heatmap/candle | 【S5】 |
| `report_theme/charts_pro/compat.py` | 140 | 旧 chart dict → spec（report_renderer 用） | 【S5】 |
| `report_theme/charts_pro/prokit_helpers.py` | 83 | 图型基元（无样例数据） | 【S5】 |
| `report_theme/charts_pro/samples_data/*` | 10 个 | **样例数据隔离区**（生产不加载） | 【样例】 |

## 10. 门禁与质检（S6）

| 文件 | 行 | 干什么 | 角色 |
|---|---|---|---|
| `quality_gate.py` | 214 | 三层质检：证据/编辑/呈现 | 【S6】 |
| `report_quality.py` | 372 | "像不像咨询稿"可判定门禁 Q1–Q9 | 【S6】 |
| `prose_style.py` | 132 | 只量页内正文 | 【S6】 |
| `prose_spec.py` | 48 | 固定 11 字段 | 【S6】 |
| `report_prose_gen.py` | 90 | 受约束生成正文 | 【S4/S6】 |
| `report_marks.py` | 44 | 标记字面量单一出处 | 【S6】 |
| `r04_audit.py` | 175 | R04 审计 | 【S6】 |
| `r04_derive.py` | 158 | R04 派生（事故后修复） | 【S6】 |
| `report_kernel/__init__.py` | 15 | 报告质量内核 | 【S6】 |
| `report_kernel/contract.py` | 131 | 开工前验收契约 | 【S6】 |
| `report_kernel/gate.py` | 218 | 交付门禁（ship gate） | 【S6】 |
| `report_kernel/consistency.py` | 116 | 跨报告数字冲突 | 【S6】 |
| `report_kernel/specs.py` | 236 | 表/图规格推断 | 【S6】 |
| `report_kernel/structure.py` | 200 | 结构门禁 + 版式规则 | 【S6】 |
| `report_kernel/series.py` | 45 | 序列与时间口径门禁 | 【S6】 |
| `report_kernel/__main__.py` | 220 | init/spec/registry/ship/self-test | 【CLI】 |

## 11. 协作与工作区

| 文件 | 行 | 干什么 | 角色 |
|---|---|---|---|
| `workspace.py` | 246 | 共享工作区（文件系统读写同一状态） | 【协作】 |
| `outcome_ledger.py` | 227 | 结果台账（P6） | 【协作】 |
| `memory_guard.py` | 293 | 记忆池体积护栏 | 【辅助】 |
| `runner.py` | 73 | 子进程方式调用另一个 Agent | 【协作】 |
| `prompt_kernel/__init__.py` | 304 | 共享 L02 提示词编译内核 | 【辅助】 |

## 12. 需注意（不是空的，之前误标）

| 文件 | 行 | 说明 |
|---|---|---|
| `report_model.py` | 141 | 报告系统**单一模型**（问题→维度→方法→图型）+ 引用完整性审计（找孤儿） |
| `research_intake.py` | 354 | 新业务研究入口：采集 → 校验 → 台账 → 成稿（quote 必须能在原文找到） |
| `report_theme/charts_pro/samples_data/*` | 10 个 | 样例数据（历史项目口径），生产不加载，已隔离 |

---

## 13. 一句话总结

- **主线只用到约 30 个文件**：`report_cli → report_line → decision_report/report_flow → report_bridge → report_renderer → charts_pro`。
- **拆卡线**是另一组：`card_issue / card_upgrade / dispatch / report_dispatch / grid_attach / cells_claims`。
- **图表库**最大：`charts/`(3) + `charts_pro/`(10) + `samples_data/`(10) = **23 个图表文件**，S5 专用；另有 `report_theme/`(6) 页面/基元。
- **`flow_report.py` 是项目代码宿主**，不在主线里，但它是"项目代码不进 core/"的关键。
- **139 个文件全部有内容**（之前我说"两个空文件"是抽取脚本的 bug，已更正）。

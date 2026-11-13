---
name: qiuqiu-data-analysis
description: "可审计数据分析报告（内置数据分析报告 Agent 完整方法包）：语义层锚定、分析计划、归因、证据链、图表 spec、报告文本治理与确定性校验器。当用户要求分析数据、诊断指标异动、解释异常、产出经营分析报告、把表字段与业务规则变成结构化分析、或需要可追溯证据的报告时使用。Auditable data analysis reports with semantic-layer grounding, deterministic validators, chart specs, report text governance, and source-traceable findings."
---

# 数据分析报告工作流（高雅人士天团 · 可审计分析）

本技能内置 `data-analysis-report-agent` 完整方法包，落在 `upstream/`：主契约 `SKILL.md`（31KB）、6 个专职子 Agent、7 个确定性校验器、报告文本包契约、图表 spec 契约、两套页面风格与配色系统、零售盈利案例包与通用经验包。

**铁律：结论必须能回溯到证据。** 没有证据链的结论只能写成假设，并给出补齐动作。

---

## 一、什么时候启用

- 「为什么掉了/涨了」「这个指标异常怎么解释」——指标异动归因
- 要出经营分析报告、诊断报告、复盘报告、汇报材料
- 要把一张表/一个数据集 + 业务规则，变成结构化、可审计的分析报告
- 需要图表规格（claim → 图）与页面设计规范（高密度证据型 HTML）
- 需要跑确定性校验（计划、数据、图表 spec、文本、装配、输出）

**不启用**：只做图表选型与美化（走 qiuqiu-data-viz）、产品需求判断（走 qiuqiu-product）、多平台运营看板与日报（走 qiuqiu-media-ops）。

---

## 二、启动必读（按顺序）

| 顺序 | 文件 | 读到什么 |
|---|---|---|
| 1 | `upstream/SKILL.md` | 全流程契约、分层规则、成本纪律、禁止事项（**全文必读**） |
| 2 | `upstream/references/analysis_material_pack_contract.md` | 分析材料包字段契约（下游复用依据） |
| 3 | 若出 HTML/React 报告：`upstream/references/human_authored_html_design_system.md` + `upstream/styles/color-system/color_system.yaml` | 高密度证据型页面规范 + 红黄绿语义信号层 |

有具体案例包时，再加读 `upstream/cases/<case-id>/semantic_layer.yaml` 与该 case 的 `experience/`（阈值、优先级规则、好报告样例）。

---

## 三、主流程（七阶段）

1. **语义层确认**：字段名、业务含义、单位、粒度、别名、分析边界。没有语义层就先用 `cases/retail-profitability/semantic_layer.yaml` 作模板现场补一版。
2. **分析计划**：把问题拆成假设树 + 验证方式 + 所需数据 + 判定规则，按 `upstream/experience/plan_schema.json` 落结构，过 `harness/plan_validator.py`。
3. **取数与画像**：源数据只 profile 一次，落 canonical 证据提取物并复用；批量用 SQL/Python 一次算完，禁止每发现一条就重读原表。过 `harness/data_validator.py`。
4. **归因与证据链**：每条发现必须挂「证据 → 推理 → 结论」，区分相关与因果；证据不足写入待补清单。
5. **图表 spec**：先定「这张图要证明什么 claim」，再按 `upstream/references/chart_spec_pack_contract.md` 出 spec（必填序列、标注点、图表侧观点）；选型参考 `upstream/references/chart_prompt_resource_index.md` 与 `qiuqiu-data-viz` 技能。过 `harness/chart_spec_validator.py`。
6. **报告文本治理**：Report Text Controller 切分有界单元包 → Editor 逐单元写（温度 0，证据到结论） → Adversarial Reviewer 对抗审查 → 装配。契约见 `upstream/references/report_text_pack_contract.md`、`report_assembly_pack_contract.md`、`report_writing_micro_prompt.md`。过 `harness/report_text_validator.py`、`report_assembly_validator.py`。
7. **渲染与交付**：按 `upstream/styles/manifest.yaml` 选风格（`editorial-evidence-report` 或 `internet-reporting`），交 html-report-renderer 出页面；过 `harness/output_validator.py`。产出放**技能包外**的输出目录，不要在技能目录里堆 outputs/。

---

## 四、六个专职子 Agent（按需加载，不要一次全开）

| 子 Agent | 目录 | 只负责 | 明确不做 |
|---|---|---|---|
| report-text-controller | `upstream/agents/report-text-controller/` | 问题拆解、有界上下文路由、补证控制、答案状态判断、渐进式总结 | 算数、写正文、HTML、给建议 |
| chart-spec-agent | `upstream/agents/chart-spec-agent/` | claim 绑定的图表规格、必备序列与标注、图表侧观点、补证请求 | 报告正文、重算数据、渲染 |
| report-text-editor | `upstream/agents/report-text-editor/` | 温度 0 的单元级措辞、证据到结论逻辑、标题推导 | 全报告遍历、查数、重算、新发现 |
| report-text-adversarial-reviewer | `upstream/agents/report-text-adversarial-reviewer/` | 独立挑战证据、验证完整性、逻辑、有用性、语气 | 看全量材料包、看作者隐藏推理、直接改写 |
| report-assembler | `upstream/agents/report-assembler/` | 文图关系仲裁、章节装配、回退判定、交接渲染 | 新分析、写正文、原始图表设计 |
| html-report-renderer | `upstream/agents/html-report-renderer/` | 按 manifest 精确渲染、行宽回流、可拆装模块 | 新分析文案、改图表语义、改结论 |

每个子 Agent 的 `manifest.yaml` 里有它自己的温度与模型约束——按 manifest 执行，不自行改。

---

## 五、确定性校验器（能跑就跑，跑不了要说明）

| 校验器 | 校验对象 |
|---|---|
| `upstream/harness/plan_validator.py` | 分析计划结构与必填判定 |
| `upstream/harness/data_validator.py` | 数据完整性与口径 |
| `upstream/harness/agent_runtime_validator.py` | 子 Agent 运行契约（manifest/温度/输入输出） |
| `upstream/harness/chart_spec_validator.py` | 图表 spec 契约 |
| `upstream/harness/report_text_validator.py` | 报告文本包契约 |
| `upstream/harness/report_assembly_validator.py` | 装配包契约 |
| `upstream/harness/output_validator.py` | 最终输出完整性 |
| `upstream/harness/run_observability_validator.py` | 运行可观测记录 |

校验器只做确定性校验，**不调用任何模型 API、不发网络请求、不读凭据**。

---

## 六、硬性规则

- 案例业务含义不许写进流程层：阈值、字段含义、行业假设只能放 `cases/<case-id>/`。
- 一个数据集 + 一个决策问题 = 一个主分析上下文；分析轮次是逻辑阶段，不是「每个分支开一个 subagent」。
- 不重算已有证据；不为了好看改指标口径；不把相关关系写成因果。
- 每个结论要么有证据链，要么标「待补证据」并说明补什么。
- 报告文字先过治理再进 HTML；跳过文本治理直接排版视为不合格。
- 不在技能目录内生成报告产物与临时依赖。

## 七、输出规范

报告默认结构：**一句话结论 → 核心发现（按影响排序，每条带证据）→ 归因链 → 风险与不确定 → 建议动作（可执行、带负责人/口径）→ 数据与口径附录**。

材料包字段对齐 `analysis_material_pack_contract.md`，运行记录对齐 `analysis_run_observability_contract.md`，示例见 `upstream/examples/`。

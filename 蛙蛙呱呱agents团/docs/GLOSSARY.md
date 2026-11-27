# 术语表（GLOSSARY）

> 只收「一说就混」的词。字段名的唯一出处是代码，本文只给定义与指向。
> **新代码禁止再写裸 `card`**：必须写清是任务卡、探测卡、ClaimCard、体验卡还是技能卡。

## 一、卡

| 术语 | 定义 | 唯一出处 |
|---|---|---|
| **任务卡（Task）** | R01 拆解意图后下发给执行角色的最小单元：`owner / inputs / outputs / deps / status`。卡是信封，不写验收明细。 | `core/base/protocol.py` |
| **CardBundle** | 任务卡 + `expert_brief` 的合成体。验收只由 brief 派生（`brief_version` + `acceptance_checks`）；卡里出现 acceptance 明细即拒收。 | `core/cards/pipeline.py` |
| **expert_brief** | 七层内容：决策语境 / 定义口径 / 结构分解 / 机制归因 / 判断情景 / 行动可逆 / 反证不确定。 | `docs/REPORT-LINES.md` |
| **探测卡（probe）** | 收卡前的可行性测试：每个格子「要采什么 / 有没有源 / 质量够不够」，三态 none/partial/full。schema `dsh.probe/v1`。 | `core/cards/pipeline.py` |
| **ClaimCard** | 一张卡的规范形状：顶层 `CARD_KEYS`、每条数字 `NUMBER_KEYS`。按卡交（v2）与按格交（v3）历史版共存，现统一发 v4；schema 字符串只在 `core/claims/contract.py` 声明一次。 | `core/claims/contract.py` |
| **ExperienceCard（经验卡）** | 「上次错法 → 正确做法」的可检索记忆：`trigger / wrong_once / do_instead / boundary / last_verified`。缺 boundary 或 last_verified 拒收。 | `shared/experience_cards.py` |
| **SkillCard（技能卡）** | 一个技能包 = 一个目录：L1 `SKILL.md`（按需触发）+ L2 `references/`（按需加载）+ L3 `scripts/`（确定性校验）。有 scripts 必须有 tests。 | `docs/SKILL-LAYER-SPEC.md` |

## 二、数据与断言

| 术语 | 定义 | 唯一出处 |
|---|---|---|
| **格子（cell）** | 拆卡网格中「单元 × 维度 × 度量」的一个采集格；角色按格交数字，不交段落。 | `core/cards/pipeline.py` |
| **Observation** | 清洗后、唯一可比较的指标单元：metric / entity / period / value / unit，另带归一值 `value_base`。图表必须读 `base_value()`。 | `core/data/data_standard.py` |
| **number** | 报告里的一条数字：`id / name / value / unit / entity / period / measure_id / grain_id / caliber / value_from / source_file / grade`。 | `core/claims/contract.py` |
| **claim** | 由数字得出的可检验判断。同一指标同期两个值必须在 `conflicts` 写明口径差，沉默即拦。 | `core/claims/claims.py` |
| **section** | 报告的节：`title / question / answers / refs / boundary / reading / chart / falsifier`。 | `core/claims/contract.py` |

## 三、产线与门禁

| 术语 | 定义 | 唯一出处 |
|---|---|---|
| **拆卡线** | 默认出报告路径：`clarify → brief --plan --confirm → collect → run-line --claims`。 | `docs/REPORT-LINES.md` |
| **发卡门禁 S1–S12** | 拆卡前必须全过的硬门；不过不发卡，失败项写 `plan/pre_issue_gates.json`。 | `core/cards/pipeline.py` |
| **收卡门禁 G1–G25** | 收卡后验覆盖率 / 来源 / 质量 / 缺口；降级与缺口一路带到 manifest。 | `core/cards/card_upgrade.py` |
| **F1–F12** | 成品报告门禁编号，唯一索引见 `docs/GATES.md`。 | `scripts/check_report_flow.py` |
| **门禁锁** | 门禁脚本的 sha256 锁；改门禁必须 `check_gate_lock.py --write` 并单独提交。 | `scripts/check_gate_lock.py` |
| **wiring truth** | 模块接线真相：LIVE / TEST_ONLY / DOC_ONLY / UNWIRED，外加文档死链。 | `scripts/wiring_truth.py` |
| **分析链（chain）** | R06 的六段分析链：frame → plan → profile → explore → explain → test；每段一个工件 + 一个确定性门禁。 | `r06-wadeqing-analyst/analysis_chain/` |
| **预注册（preregistration）** | 先写指标/窗口/维度/检验/停止条件，再看数；`data_read_before_plan=false` 是硬门禁。 | `analysis_chain/plan.py` |
| **驱动树** | 指标变化按分段贡献分解，并对头号驱动做量价拆解；加总误差 ≤5%。 | `analysis_chain/explain.py` |
| **可拆卸模块（bounded modules）** | 证据不足的单元不进入主结论，可独立渲染；T8b 落地，T8a 预留 `bounded` 语义。 | `core/report/`（T8b） |
| **报告链（T8b）** | R06 的 verify → chart → write → deliver；产物是待 R01 签发的报告草稿。 | `analysis_chain/report_runner.py` |
| **结论可追率** | 正文数字能回到 material pack 的比例；要求 100%。 | `analysis_chain/deliver.py` |
| **run_events** | 每次交付的阶段事件账本（verify/chart/write/deliver）。 | `report/run_events.jsonl` |
| **内容链（content_chain）** | R11 的 7 段写作生产线：topic → research → outline → draft → review → rewrite → final；每段一门禁。 | `r11-wadianti-copy/content_chain/` |
| **研究链（research_chain）** | R05 的 8 段研究链：scope → source → collect → verify → triangulate → size → compete → report。 | `r05-washenyuan-research/research_chain/` |
| **产品工作流（pm_workflows）** | R07 的 5 条工作流（discovery/prd/priority/acceptance/briefing）+ 经验 RAG 门。 | `r07-wademing-pm/pm_workflows/` |
| **增长链（growth_chain）** | R12 的 7 段增长链：diagnose → experiment → attribution → retention → paid → selfmedia → mmm。 | `r12-wayingliu-growth/growth_chain/` |
| **工程链（eng_chain）** | R09 的 10 段工程链：adr → api → feature → testing → debug → release → security → performance → incident → review。 | `r09-wawenma-engineer/eng_chain/` |
| **经验门（experience gate）** | 经验卡检索与写回：L0 不检索 / L1 只读索引 / L2 3–5 卡；五查 + 冲突优先级 + 状态机。 | `r07-wademing-pm/pm_workflows/experience.py` |
| **设计契约 P1–P12** | 报告呈现的 12 条可测规则（无斜体、A4、对比度、字阶、图四件套、主题、版心、容器、断行、表格、反模式、标题层级）。 | `docs/REPORT-DESIGN-CONTRACT.md` |
| **风格包** | 一套可切换的版式与文风：`page_style.yaml` + `global_prompt.md` + `sample.html`。 | `styles/<style-id>/` |
| **图表六维审计** | 每张图检查 data_drawable / chart_fit / calc_correct / labels_clear / visual_professional / return_contract。 | `core/charts/audit.py` |
| **quick / guided** | 图表难度分级：quick 用于教学与快报，guided 用于生产报告；目录每型带 `level`。 | `core/charts/chart_capabilities.py` |

## 四、产物

| 术语 | 含义 |
|---|---|
| `plan/` | 拆卡计划：`issue_tree / dispatch / grid / supply / derivation` |
| `claims` | 收卡合并后的断言文档：`numbers / sources / sections / conflicts` |
| `manifest.json` | 一次出报告的审计单：producer、门禁结论、降级、文件清单 |
| `result.json` | 执行角色的证据出口；执行角色不出报告，只交数字与证据 |

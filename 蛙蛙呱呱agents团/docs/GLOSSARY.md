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

## 四、产物

| 术语 | 含义 |
|---|---|
| `plan/` | 拆卡计划：`issue_tree / dispatch / grid / supply / derivation` |
| `claims` | 收卡合并后的断言文档：`numbers / sources / sections / conflicts` |
| `manifest.json` | 一次出报告的审计单：producer、门禁结论、降级、文件清单 |
| `result.json` | 执行角色的证据出口；执行角色不出报告，只交数字与证据 |

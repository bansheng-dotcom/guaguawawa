---
name: prd-authoring
description: PRD 撰写技能包。把产品想法写成两层可交付的 PRD：战略层说清问题、价值主张、范围与指标，执行层给每个 P0 功能补齐触发/规则/结果/状态四段并标注来源枚举，产出可被门禁校验、可一键渲染为 Markdown 的结构化规范。当需要写 PRD、拆用户故事与验收标准、做优先级排序、或判断一份 PRD 是否可直接进入开发时使用。不负责写生产代码、不做技术方案选型、不替研发估工期。
license: MIT
compatibility: 通用。门禁在角色根目录 harness.py（战略层）与 agent.py prdguard（执行层），Python 3.10+、零第三方依赖；无 Python 环境时按 §8 转人工十二项核对，此时不得标记「可进入开发」。
metadata:
  owner: r07
  version: "2.0.0"
  kind: skill
  triggers: "写PRD,需求文档,用户故事,验收标准,优先级,RICE,范围界定"
  verify: python agent.py prdguard check --input <PRD规范.json>
  entry: "python agent.py prdguard render --input <PRD规范.json> --out <PRD.md>"
  consumers: "r08,r09,r10,r04"
  supersedes: README.md
---

# PRD 撰写（PRD Authoring）

> 一句话定位：**这个技能存在的意义，是防止"一份看起来很像 PRD 的文档，谁也不知道要做什么"**。
> PRD 的失败很少是写得不漂亮，而是三件事：**问题没说清就写方案、P0 只写名字不写边界、
> 把假设当成事实**。前两件让开发无法开工，第三件让上线后无法复盘。

## §1 何时用 / 何时不用

**该用（用户真实会这么说）**
- 「写个 PRD」「这个需求怎么定义」「帮我把想法整理成需求文档」
- 「这几个功能先做哪个」「怎么排优先级」
- 「PRD 写得够不够开发了」

**不该用，转给谁**

| 用户其实想要 | 转给 | 理由 |
|---|---|---|
| 技术方案 / 架构选型 / 工期估算 | `r09` 工程官 | PRD 写"要什么"，不写"怎么实现" |
| 直接做出原型或页面 | `r08` MVP | 本技能只出规范，不产出可运行物 |
| 判断这份 PRD 合不合格 | `r04` 评审官 | 质量结论归 R04，作者不自评 |
| 市场该不该做这个方向 | `r05` / `r01` | 那是方向判断，不是需求定义 |

**最小可开工输入**：一句话说明**要解决谁的什么问题**（如"新用户注册后不知道从哪开始"）。

---

## §2 前置输入与最省追问

| 输入 | 是否必需 | 缺失时怎么办 |
|---|---|---|
| 要解决的问题（一句话） | 必需 | 无法推断，必须问 |
| 目标用户 | 必需 | 按同类产品假设补全，标"待确认" |
| 成功指标或基线 | 建议 | 给建议值与口径，写入关键假设清单 |
| 已有方案 / 竞品参考 | 可选 | 缺则跳过对标，标注"未做对标" |
| 技术约束 | 可选 | 缺则写进 `open_questions` 交 r09 |

**追问纪律**
- 最多一轮，合并 ≤ 4 问一次问清，每问附 2–3 个候选。
- **不追问"你想要什么功能"**——那是让用户替你做产品设计。问"什么问题最痛、现在怎么绕过去的"。
- 其余按同类产品默认补全，写进关键假设清单，随 PRD 给出。

---

## §3 执行流水线（Workflow）

### Step 1 · 问题与用户（战略层起点）
三件套写清：**谁**（用户/场景）、**现在怎么凑合**（替代方案）、**代价多大**（action_cost）。
写不出"用户现在怎么凑合的"，说明这个问题可能不真实存在。

- **产出**：`users[]` + `problem_statement`
- **过关条件**：每个用户段都带 `scenario` 与 `alternative`（不能只写人群标签）

### Step 2 · 价值主张（before / how / after）
用一句话描述改变：`before` 现状 → `how` 我们怎么变 → `after` 变成什么。
`after` 必须是**可观察的状态**，不是"体验更好"。

- **产出**：`value_proposition{before, how, after, alternatives}`
- **过关条件**：`after` 可被观测或计量

### Step 3 · 范围界定（P0/P1/P2 + 明确不做）
- `p0`：不做就不能上线的功能；
- `p1`／`p2`：可延后；
- **`non_goals` ≥ 2 条**：明确不做什么。

> "不做"清单是 PRD 里性价比最高的部分。没有它，范围会在开发过程中自动膨胀。

- **产出**：`scope{p0,p1,p2,non_goals}`
- **过关条件**：`non_goals` ≥ 2 且每条都有理由

### Step 4 · P0 深度化（四个必填段，这一步决定能不能开发）
每个 P0 功能必须写满四段，缺一段即 BLOCKER：

| 段 | 含义 | 反例 → 正例 |
|---|---|---|
| `trigger` | 什么条件下触发 | ~~"用户需要时"~~ → "首次进入工作台且项目数为 0" |
| `rule` | 具体规则/步骤 | ~~"引导用户"~~ → "选模板 → 填名称 → 导入示例数据，每步可跳过" |
| `result` | 达到什么结果 | ~~"完成引导"~~ → "项目看板可见且至少一条示例数据" |
| `state` | 有哪些状态 | ~~"正常/异常"~~ → "未开始/进行中/已完成/已跳过" |

同时每个 P0 必须标 `source` ∈ **`evidence`**（有数据/访谈依据）/ **`assumption`**（假设待验证）/ **`judgment`**（经验判断）——
**三选一，写别的都不认**。

- **产出**：`p0_features[]`（每项含四段 + source）
- **过关条件**：P0 ≥ 2 且**每项四段齐全、source 在枚举内**

### Step 5 · 假设与待验证问题（禁止把假设当事实）
只要写了 `assumptions`，就必须同时写 `open_questions`——**假设必须有人负责验证**。
这是门禁的硬配对：有假设无问题 → 判"把假设当事实"。

- **产出**：`assumptions[]` + `open_questions[]`（成对出现）
- **过关条件**：两者数量关系成立（有假设则问题非空）

### Step 6 · 验收标准与边界（AC + 边界场景）
- `acceptance_criteria`：每条 `{given, when, then}` 三件套；
- `edge_cases` ≥ 1，且必须覆盖**空 / 错 / 取消 / 重试**中的至少一项。

> 注意区分 **AC（这条需求怎样算完成）** 与 **DoD（团队通用的完成定义）**，详见 `references/two-layer-prd.md`。

- **产出**：`acceptance_criteria[]` + `edge_cases[]`
- **过关条件**：AC 每条可判定；`edge_cases` ≥ 1

### Step 7 · 指标与基线（战略层收口）
`north_star` + `input_metrics`（≤3）+ `guardrail`（护栏指标，防止按下葫芦浮起瓢）+ `baseline` / `target` / `data_source`。
**没有 baseline 的目标值是口号**。

- **产出**：`metrics{}`
- **过关条件**：`baseline` 与 `data_source` 均非空

### Step 8 · 跑门禁并渲染
```bash
# 执行层（结构最严，12 项检查）
python agent.py prdguard check  --input <PRD规范.json>
# 渲染成人读版
python agent.py prdguard render --input <PRD规范.json> --out <PRD.md>
# 战略层（问题/用户/价值/范围/指标/AC/风险 结构）
python harness.py prd --input <战略层.json>
```

- **过关条件**：两条 check 退出码 0，且 `prdguard` 的 `checks_failed = 0`

---

## §4 交付物清单

| # | 交付物 | 载体 | 骨架出处 |
|---|---|---|---|
| 1 | PRD 规范（两层字段全量） | `.json` | `tests/spec-pass.json`（可直接当模板） |
| 2 | 人读版 PRD | `.md` | `prdguard render` 生成 |
| 3 | 门禁报告 | 终端 JSON | `prdguard` / `harness` 输出 |
| 4 | 优先级表（可选，>3 个候选时） | `.md` | `references/two-layer-prd.md` §三 RICE |

- 命名：`prd_<产品短码>_<YYYYMMDD>.json` / `.md`，两者版本号一致
- **`.json` 是唯一可被下游消费的载体**；`r08` / `r09` 只认 JSON 不认聊天

---

## §5 质量门（一票否决，不过不给交付）

1. **标题非空**，且能看出做的是什么（不是"优化一下"）；
2. **产品契约四要素齐全**：`user` / `trigger` / `job` / `completion`；
3. **P0 ≥ 2**，且**每项四段齐全**（trigger / rule / result / state）；
4. **每个 P0 的 `source` 在枚举内**（`assumption` / `evidence` / `judgment`）；
5. **`non_goals` ≥ 2**，每条带理由；
6. **`edge_cases` ≥ 1**（空/错/取消/重试至少一项）；
7. **有假设必有待验证问题**（禁止把假设当事实）；
8. **战略层 `baseline` 与 `data_source` 非空**。

> 验收命令：`python agent.py prdguard check --input <PRD规范.json>`（12 项）+ `python harness.py prd --input <战略层.json>`
> 命中任一项不过 → 回 §3 对应 Step 重做，**不允许只改标题或补一句 summary**。

---

## §6 交付前自检清单

- [ ] 问题句写的是"谁的什么痛"，不是"我们要做什么功能"
- [ ] 每个用户段都写了"现在怎么凑合的"和"代价多大"
- [ ] `after` 是可观察状态，不是"体验更好"
- [ ] P0 每一项都写满四段（触发/规则/结果/状态），没有一项只写名字
- [ ] 每个 P0 的 `source` 都标了，且标的是真实依据（`evidence` 要能指到数据或访谈）
- [ ] `non_goals` ≥ 2 条，每条都有"为什么不做"
- [ ] 有 `assumptions` 就有对应的 `open_questions`，且每条问题有验证方式
- [ ] AC 全是 `{given, when, then}` 三件套，能判真假
- [ ] `edge_cases` 至少覆盖空/错/取消/重试之一
- [ ] 指标有 `baseline` + `target` + `data_source`，护栏指标没漏
- [ ] 没有写技术实现方案（那是 r09 的事）
- [ ] `prdguard check` 与 `harness prd` 均退出码 0，且渲染出的 `.md` 能打开

---

## §7 易犯错误对照表

| # | 易犯错法 | 正确做法 |
|---|---|---|
| EX-01 | P0 只写功能名（"做引导流程"） | 四段齐全：什么条件触发、按什么规则、达到什么结果、有哪些状态 |
| EX-02 | `source` 写"我觉得"/"行业惯例" | 只能是 `assumption` / `evidence` / `judgment`；`evidence` 要能指到数据或访谈编号 |
| EX-03 | 只写做什么，不写不做什么 | `non_goals` ≥ 2 条并给理由，否则范围必然膨胀 |
| EX-04 | 写了假设，没写谁去验证 | 假设与 `open_questions` 必须成对；有假设无问题即"把假设当事实" |
| EX-05 | `after` 写"体验更好""更顺畅" | 写成可观察状态："10 分钟内完成首个项目" |
| EX-06 | 指标只有 target 没有 baseline | 没 baseline 的目标值是口号；必须给基线+口径+数据源 |
| EX-07 | 把 AC 写成 DoD（"代码通过评审、有单测"） | AC 是**这条需求**怎样算完成；DoD 是团队通用完成定义，两者分开写 |
| EX-08 | 边界只写"异常情况需处理" | 明确列举：空/错/取消/重试，至少一项写具体行为 |
| EX-09 | 在 PRD 里写技术方案与工期 | 只写要什么与验收标准；实现方案交 r09，工期交 r02 |
| EX-10 | 让用户回答"你想要什么功能" | 问"什么问题最痛、现在怎么绕过去"，需求由你提炼 |
| EX-11 | 用战略层 JSON 去跑 `prdguard`（或反过来） | 两层 schema 不同：战略层走 `harness prd`，执行层走 `prdguard check` |
| EX-12 | 手写渲染版 `.md` 而不跑 render | 渲染必须由 `prdguard render` 生成，否则字段与规范脱钩 |

---

## §8 降级与边界

| 触发情况 | 处置 |
|---|---|
| `prdguard` / `harness.py` 跑不了 | 按 §6 人工逐项核对，标注「未跑门禁」；**此时不得标记"可进入开发"**，最多标"待门禁复核" |
| 用户只给一句话 | 按同类产品假设补全用户/范围/指标，全部写入关键假设清单，不追问超过一轮 |
| 没有基线数据 | `baseline` 写"暂无，需 r06 提供"，并在 `open_questions` 加一条"补基线" |
| 用户要 PRD 里包含技术方案 | 明确切分：PRD 写要什么，技术方案另出，交 `r09` |
| 用户拒绝写"不做什么" | 仍强制列 ≥2 条，可由你提出让用户否决——否决也要留下记录 |
| 需求其实是方向问题 | 转 `r05` / `r01`，先判方向再写需求 |
| 需求涉违规（如伪造数据、诱导分享） | 明确拒绝，并给合规替代方案 |

**明确不做**
- 不写生产代码、不做技术选型、不估工期（分别归 `r09` / `r02`）；
- 不产出可运行原型（归 `r08`）；
- 不出质量结论（归 `r04`）；
- 不替用户做方向判断（归 `r05` / `r01`）。

---

## §9 资源地图（按需读取，禁止全量加载）

> 本技能包**不自建门禁**：执行层用根目录 `agent.py prdguard`（12 项检查 + 渲染），
> 战略层用根目录 `harness.py prd`。本包只声明、给模板、做自检。

| 什么时候需要 | 读哪个文件 |
|---|---|
| 两层 PRD 的分工、AC vs DoD、RICE 算例、十二项审批清单 | `references/two-layer-prd.md` |
| 执行层 PRD 骨架（可直接改） | `tests/spec-pass.json` |
| 反例（用来对齐"什么算不合格"） | `tests/spec-fail.json` |
| 门禁是否还有效（正/反例 fixture） | `scripts/gate_selftest.py` |
| 负向用例 | `tests/misuse.md` |
| 战略层示例 | `../../../examples/prd.json`（及 `_dirty`） |

**脚本清单**

| 脚本 | 用途 | 入口 |
|---|---|---|
| `scripts/gate_selftest.py` | 断言 `prdguard check` 与 `harness prd` 对正/反例的退出码 | `--verbose` |

---

## §10 变更记录

- **v2.0.0（2026-11-11）**：按 `docs/SKILL-LAYER-SPEC.md` v1.0 重构为十节技能包。
  新增：§1 转交表、§2 最小可开工输入、§3 八步流水线（含 P0 深度化四段与 source 枚举）、
  §7 十二条错误表（含两层 schema 混用）、§8 七种降级、`references/two-layer-prd.md`、
  `scripts/gate_selftest.py`、`tests/spec-pass.json` / `spec-fail.json` / `misuse.md`。
  门禁复用 `prdguard` 与 `harness prd`，未新增判定实现。
- v1.0（此前）：能力卡形态（`README.md`，约 916 字节；kind=skill，入口 `prdguard check/render`，但卡内未写四段与 source 枚举）。

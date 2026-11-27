# 蛙蛙呱呱（Guaguawawa）· 20 角色智能体公司

> 专为**一人公司**打造的全栈商业与技术智能体协作系统。
> 用「组织语义 + 契约化端口 + 生成与校验分离」把 20 个专业角色组织成一家可运行的公司，而不是 20 个互不相干的聊天机器人。

**版本：v2.9 · 2026-11-27**（20 角色厚度升级 + 五条生产线；P4 物理分包 / P5 逻辑收敛；报告产线 v14）

> **默认只走拆卡线**（2026-11-22 起为硬门）：
> `clarify → intake → clarify --confirm --user-said → brief --plan（把卡摊给用户看）→
> brief --confirm --ack-cards --user-said → preflight → collect → run-line --claims`。
> 没有 `coverage/issued.json` 的项目，`report collect` 直接拒收；
> `report run-line --claims` 只认收卡产物；手写单人稿必须 `--solo-claims --allow-solo`，
> 且过 50 条唯一 URL 门槛，产物标 `solo_no_dispatch`。
> 默认版式 `flow`（一条内容流，PDF 自动分页）；`--layout paper` 已于 2026-11-21 下线。
> 产线地图见 [`docs/REPORT-LINES.md`](蛙蛙呱呱agents团/docs/REPORT-LINES.md)，
> 拆卡 SOP 见 [`docs/archive/交付/拆卡升级-SOP-2026-11-21.md`](蛙蛙呱呱agents团/docs/archive/交付/拆卡升级-SOP-2026-11-21.md)，
> 预检实现见 [`scripts/preflight.py`](蛙蛙呱呱agents团/scripts/preflight.py)。

**统一入口：** [`guagua.py`](蛙蛙呱呱agents团/guagua.py) ｜ **完整命令手册：** [`使用指南.md`](蛙蛙呱呱agents团/使用指南.md) ｜ **更新日志：** [`CHANGELOG.md`](蛙蛙呱呱agents团/CHANGELOG.md)

---

## 目录

- [一、这套系统是什么](#一这套系统是什么)
- [二、60 秒上手](#二60-秒上手)
- [三、组织全景](#三组织全景)
- [四、三种合作形式](#四三种合作形式)
- [五、20 个智能体详解](#五20-个智能体详解)
- [六、可复用协作流水线](#六可复用协作流水线报告产线--六条协作链)
- [七、统一入口与全部功能调用](#七统一入口与全部功能调用)
- [八、目录结构与文档索引](#八目录结构与文档索引)
- [九、运行、验收与能力边界](#九运行验收与能力边界)
- [十、版本与更新记录](#十版本与更新记录)

---

## 一、这套系统是什么

蛙蛙呱呱是一套**可本地运行、可审计、可编排**的 AI 公司操作系统。它把一家公司拆成 20 个职责清晰的角色，并用三层机制把它们连接起来：

1. **组织语义层**：谁负责什么、向谁汇报、与谁交接、什么不能做。权威文件是 [`ORG.md`](蛙蛙呱呱agents团/ORG.md)。
2. **协同协议层**：任务卡怎么开、失败怎么移交、多角色怎么按波次执行。权威文件是 [`PROTOCOL.md`](蛙蛙呱呱agents团/PROTOCOL.md)。
3. **确定性执行层**：每个角色都有可执行的 `agent.py`、输入/输出契约、门禁（harness）、案例库和回归测试。入口在 [`core/registry.py`](蛙蛙呱呱agents团/core/registry.py)。

它适合这些场景：

- 你有一个经营目标，需要拆成研究、产品、数据、实现、评审等多角色任务；
- 你需要一个角色替你把一件事做深，而不是泛泛聊天；
- 你需要「谁生成、谁校验」分离，避免自己写、自己夸；
- 你想把内容、增长、交易、供应链、人事、自动化、数仓、模型、SRE 等职能串成一条可追溯的流水线。

**三个核心数字：** 20 个角色、6 大事业群、3 种合作形式。

### 本次升级了什么（v2.6）

- **拆卡线成为唯一默认**：报告不再允许「一个人写完 claims 就出稿」。默认路径是
  R01 拆卡 → 子智能体按 `nonce + HMAC 签名` 各写各的 → R01 只做合并与判断。
  没有 `coverage/issued.json` 的项目，`collect` 直接拒收。
- **人必须在环里**：12 问必须问给用户（`user_answers ≥ 10` 才签得了 brief）；
  澄清确认必须带 `--user-said` 原话；发卡前必须 `brief --plan` 把卡片清单摊给用户，
  确认时带 `--ack-cards`。`preflight` 的 P8/P9 就是查这三件事。
- **来源门槛收紧**：`collect` 默认 `--min-sources 50`，按**唯一 URL** 计数，逐条回抓 quote；
  关回抓或关严格核验必须显式 `--allow-degraded`，降级写进 manifest。
- **单人稿降级有痕**：`run-line --claims` 只接受收卡产物；手写稿必须
  `--solo-claims --allow-solo`，同样过 50 源门槛，产物标 `solo_no_dispatch`。
- **封面与 KPI 固化**：渲染器优先取 `meta.title / meta.subtitle / meta.metrics`，
  报告标题、副题、关键指标不再被首节标题覆盖。
- **清理**：工作区历史试跑产物（`workspace/`、`_attic/`、`z/`）与无关赛道调研残留已清除；
  2026-11-25 起项目交付物整体迁出工具仓库，仓库只保留工具与文档。

---

## 二、60 秒上手

以下命令默认在智能体管理目录执行：

```bash
cd "D:\蛙蛙呱呱\蛙蛙呱呱agents团"
```

### 第 1 步：体检

```bash
python guagua.py doctor
```

它会检查 Python 版本、20 个角色文件是否存在，并逐个执行 `agent.py --help`，最后给出 `20/20` 体检结果。

### 第 2 步：看花名册

```bash
python guagua.py roles
python guagua.py info r06
```

`roles` 列出 20 个角色的 ID、代号、职位、输入/输出端口；`info` 查看某个角色的完整能力与推荐入口。

### 第 3 步：调用一个角色

```bash
# 看某个角色支持的全部子命令
python guagua.py call r06 --help

# 跑一个确定性的数据语义校验
python guagua.py call r06 semantics validate --input examples/semantic_model.json

# 让角色生成自己的示例工件
python guagua.py demo r06
```

`call` 会把参数**原样转发**给对应角色的 `agent.py`，所以角色支持什么，就能调用什么。

### 第 4 步：让 R01 拆一个经营目标

```bash
python guagua.py plan "停车场一年营收最大化"
python guagua.py status
```

`plan` 让 R01 蛙全局把意图拆成任务卡；`status` 查看任务依赖、负责人和执行状态。

### 第 5 步：执行与验收

```bash
python guagua.py dispatch --all
```

`dispatch` 让 R01 按依赖顺序执行任务，并在每张卡完成后做验收。建议先在副本或测试分支运行，因为部分角色会写入 `workspace/artifacts/`。

### 第 6 步：生成知识注入 Prompt

```bash
python guagua.py chat --role r06 --intent "分析订单漏斗、留存和渠道归因"
```

`chat` 会把该角色的知识域、案例、规则和你的意图组装成一份可直接交给 LLM 的 Prompt。

### 第 7 步：出一条报告（拆卡线，唯一默认）

```bash
# 0) 接活：把 12 问问给用户，回答落盘（至少 10 条），再由用户确认
python guagua.py report clarify --intent "<你的课题>" --out <项目>
python guagua.py report intake --dir <项目> --answer I1=… --answer I2=…
python guagua.py report clarify --dir <项目> --confirm --user-said "用户原话"

# 1) 出卡给用户看（只出清单，不发卡）
python guagua.py report brief --dir <项目> --plan
# 2) 用户点头后确认发卡（nonce + HMAC 签名，写 coverage/issued.json）
python guagua.py report brief --dir <项目> --plan --confirm --ack-cards --user-said "用户原话"
# 3) 子智能体按卡执行，交 cards/<role>/claims.json（不写长文、不画图）

# 4) 预检 P1–P9：澄清/签字/发卡/回卡/nonce/唯一来源/语义层/用户确认/看过卡
python guagua.py report preflight --dir <项目>
# 5) 收卡：50 条唯一 URL + 逐条回抓 quote → claims_merged.json
python guagua.py report collect --dir <项目> --out <项目>/out
# 6) 出报告（只认收卡产物）
python guagua.py report run-line --intent "…" --claims <项目>/out/claims_merged.json \
  --out <项目>/out/report --pdf

# 只想先看研究方案（不产报告）
python guagua.py report research-plan --intent "内蒙古调味料市场怎么做" --out <项目>/plan
# 已有干净数据时走 A 数据驱动（不拆卡，边界见第九节）
python guagua.py report "这批数据说明什么" --dir <数据项目> --out <项目>/out --pdf
# 验一份成品（九条 flow 门禁 + 深度门禁）
python guagua.py report check --html <项目>/out/report/report.html
```

产物固定为 `report.html`（正式版）+ `report.md`（快读版）+ `report.pdf`（带页码）+ `manifest.json`（门禁与证据）。
完整清单见 [`docs/REPORT-LINES.md`](蛙蛙呱呱agents团/docs/REPORT-LINES.md)。

### 样例与更新日志

仓库只放工具，不放项目交付物：样例报告（含客户数据与遮蔽后的竞品名）属于项目资产，
2026-11-25 起不再随工具仓库分发；需要时用拆卡线在你自己的项目根里重新生成。

能力变化按日期记在 [`CHANGELOG.md`](蛙蛙呱呱agents团/CHANGELOG.md)：新增能力、门禁变化、
迁移与不兼容点、已知遗留。渲染器的验收样张约定不变：封面取 `meta.title/subtitle/metrics`，
每节 11 字段，图带来源与单位，最后一节是「口径与分数」。

---

## 三、组织全景

系统遵循**生成与校验分离**和**单一主责**原则：

```text
                              ┌─────────────────────────┐
                              │      创始人（用户）       │
                              │  最终裁决 · 不可逆签字   │
                              └────────────┬────────────┘
                         ┌─────────────────┴─────────────────┐
                         │  R01 蛙全局 · CEO 主理人 / 编排器  │←─ 汇总汇报
                         │  意图分级 · 拆解 · 决策 · 收口     │
                         └─────────────────┬─────────────────┘
                                           │ 下发 task_cards
        ┌──────────┬──────────┬────────────┼────────────┬──────────┬──────────┐
        ▼          ▼          ▼            ▼            ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐  ┌────────┐  ┌────────┐ ┌────────┐ ┌────────┐
   │决策治理 │ │战略数据 │ │产品技术 │  │市场客户 │  │交易组织 │ │自动化可 │ │  R04   │
   │ R02 COO│ │ R05 研究│ │ R07 产品│  │ R11 内容│  │ R14 交易│ │ R17 自动│ │蛙挑刺  │
   │ R03 CFO│ │ R06 分析│ │ R08 MVP │  │ R12 增长│  │ R15 供应│ │ R20 值守│ │独立评审│
   │        │ │ R18 数仓│ │ R09 工程│  │ R13 客成│  │ R16 人事│ │        │ │(旁路)  │
   │        │ │ R19 智模│ │ R10 设计│  │        │  │        │ │        │ │        │
   └────────┘ └────────┘ └────────┘  └────────┘  └────────┘ └────────┘ └────┬───┘
                                                                             │
                    ┌────────────────────────────────────────────────────────┘
                    │  R04 拥有旁路通道，不经 R01 拦截，独立向创始人汇报 pass/fail
                    ▼
```

### 两条汇报线

1. **执行主线**：R02～R20 → R01 汇总 → 创始人。
2. **独立评审线**：R04 蛙挑刺直接向创始人输出 `pass/fail` 与审查报告，执行线不能拦截、不能改写。

### 六大事业群

| 事业群 | 角色 | 回答的问题 |
|---|---|---|
| 决策与治理 | R01 CEO、R02 COO、R03 CFO/合规、R04 评审 | 做什么、谁来做、有什么风险、能不能交付 |
| 战略、数据与智能 | R05 研究、R06 分析、R18 数仓、R19 智模 | 方向是否成立、数字说明什么、数据怎么流动、模型怎么可控 |
| 产品与技术 | R07 产品、R08 MVP、R09 工程、R10 设计 | 做什么、怎样快速验证、怎样工程化、看起来怎样 |
| 市场与客户 | R11 内容、R12 增长、R13 客成 | 怎样表达、怎样获客、怎样成交后留住客户 |
| 交易与组织运营 | R14 交易、R15 供应、R16 人事 | 怎样下单收款、怎样采购履约、怎样管人和薪酬 |
| 自动化与可靠性 | R17 自动化、R20 SRE | 系统怎样协同、故障怎样发现、资产怎样恢复 |

---

## 四、三种合作形式

### 形式 A：单角色直接调用（你只找一个人）

适用于「这件事就在一个角色职责内」的情况。角色按五步自展开：

```text
① 澄清 Clarify → ② 自查 Self-check → ③ 展开 Expand → ④ 自评 Self-assess → ⑤ 汇报 Report
```

- **澄清**：只问真正缺的事（六项骨架 + 最多 2 个场景补充，总问数 ≤ 8）——交付物、目标/成功标准、边界、输入、验收判据、时限/依赖。
- **自查**：我的哪个技能域能覆盖？契约输入齐不齐？有没有越界？
- **展开**：走技能子命令；运行物写 `workspace/artifacts/{task_id}/`，
  带 `--project` 时项目产物写 `<项目>/artifacts/`。
- **自评**：过 harness 门禁；脏数据、缺证据、超边界都不许硬交。
- **汇报**：输出 `.md` 快读版 + `.html` 正式版，不吐裸 JSON。

```bash
# 例：只找 R06 做数据分析
python guagua.py call r06 quality audit --input ../workspace/r06-wadeqing-analyst/_loop_clean.csv

# 例：只找 R04 做独立验收
python guagua.py call r04 artifact inventory --input examples/artifact_inventory.json
```

### 形式 B：失败与越界移交（做不下去时）

任务卡无法推进到 `done` 时，**不许沉默、不许硬凑**，按分类移交：

| 触发条件 | 移交给谁 | 典型场景 |
|---|---|---|
| 输入不足 / 口径不明 / 需求矛盾 | 回上游或 R01 澄清 | 数据缺列、指标没定义 |
| 超出本角色边界 | `ORG.md` 边界表指定的邻角色 | 产品经理被要求写生产代码 |
| 需要独立质量判断 | R04 | 成品验收、门禁复核 |
| 命中 2 个以上职能域 | R01 重拆 | 既要内容又要投放又要数据归因 |
| 不可逆 / 资金 / 合同 / 大额 | 创始人 | 裁员、关停、签约、付款 |
| 依赖的上游任务 failed | R01 重排依赖 | 研究失败导致产品无法立项 |

移交必须带：`from / to / reason / task_id / artifacts / acceptance / context_summary / call_chain`。禁止自调用，最大调用深度 2，同一任务移交超过 3 次升级 R01 重拆。

### 形式 C：多角色编排（跨域方案）

R01 按 **GSD 五相环**组织：

```text
Discuss 澄清 → Plan 拆卡 → Execute 按波次执行 → Verify 独立复核 → Ship 收口归档
```

一张合格的任务卡包含六段：

```text
## 任务 <名>        （title + owner，单一主责）
### 目标            1-2 句要构建什么
### 拥有文件         独占文件清单（一个文件一个 owner）
### 需求            具体交付 1..n
### 接口契约        导出:<本流提供> / 导入:<从别流消费>
### 验收标准        可机器测的准则
### 明确不做        非目标（空 = 门禁不通过）
```

执行时按依赖划分波次：无依赖进第 1 波，依赖第 1 波进第 2 波，最大波深 6；共享状态用原子锁。每张卡完成后由 R01 验收，关键交付再走 R04 独立评审。

```bash
python guagua.py plan "停车场一年营收最大化"
python guagua.py status
python guagua.py dispatch --all
```

### 三条协作铁律

1. **单一主责**：一个任务、一个文件、一个职能，有且只有一个 owner。「共同负责」等于没人负责。
2. **编排器要瘦**：R01 只做加载上下文、派发角色、回收结果、更新状态；不替执行角色生产业务。
3. **生成与校验分离**：谁生成谁负责，R04 独立评审；`reviewer == producer` 直接判 FAIL。

---

## 五、20 个智能体详解

每个角色按同一模板介绍：**定位 → 核心能力 → 契约 → 常用命令 → 协作位置 → 边界**。

---

### 决策与治理

#### R01 · 蛙全局｜CEO 主理人 / 编排器

**定位**：公司的总入口和总收口。把创始人的模糊意图变成可执行任务卡，决定谁来做、按什么顺序做、什么时候停。

**核心能力**：意图识别与任务分级 · 跨部门拆解 · 经营与硬决策 · 反方质询 · 公司 OS 与治理 · 决策留痕与复盘 · 高层汇报与创始人陪练 · 编排与验收

**契约**：`intent` + `decision_memo` → `task_cards` + `decision_log` + `board_report`

```bash
python guagua.py call r01 intent brief --input examples/brief.json
python guagua.py call r01 decompose taskcard --input examples/taskcard.json
python guagua.py call r01 decide card --input examples/decision_card.json
python guagua.py call r01 boardroom memo --input examples/board.json
python guagua.py plan "停车场一年营收最大化"
python guagua.py dispatch --all
```

**协作位置**：编排中枢。接收创始人意图，给 R02～R20 发任务卡；汇总执行线结果；不可逆事项升级创始人。R04 不经过它，直接向创始人汇报。

**边界**：不替专业部门生产业务，不签质量结论，不签合同、不动资金；不可逆动作必须创始人授权。

---

#### R02 · 蛙排布｜COO 首席运营官

**定位**：把 R01 的任务卡变成可执行的排期、容量计划和交接包，并跟踪验收与复盘。

**核心能力**：工作拆解与排期 · 容量与委派 · 交接与验收追踪 · 复盘与事故分析 · 流程与 SOP · 知识运营 · 项目群与 Agent 编排

**契约**：`goal` + `task_cards` → `sprint_plan` + `handoff_pkg`

```bash
python guagua.py call r02 demo
python guagua.py call r02 schedule wbs --input examples/wbs.json
python guagua.py call r02 capacity check --input examples/capacity.json
python guagua.py call r02 handoff package --input examples/handoff.json
python guagua.py call r02 retro postmortem --input examples/incident.json
```

**协作位置**：R01 拿到目标后，R02 负责 WBS、关键路径、容量检查、交接包和事故复盘；排期冲突回 R01。

**边界**：不实现自动化（R17）、不生产业务、不定公司方向。

---

#### R03 · 蛙守线｜财务合规官 / 红线负责人

**定位**：守住钱、合同、税务、隐私、AI 治理、审计和金融风险的红线。它给结论，但不替创始人签字。

**核心能力**：报表月结 · CFO 诊断 · 税务边界 · 合同政策 · 隐私数据安全 · AI 治理 · 审计留痕 · 广告/KYC-AML/投资风控

**契约**：`financials` + `contracts` + `data_flows` → `compliance_review` + `risk_register`

```bash
python guagua.py call r03 --help
python guagua.py call r03 aigov aiclassify --input examples/aigov_aiclassify.json
python guagua.py call r03 financial rollforward --input examples/financial_rollforward.json
python guagua.py call r03 cfo runway --input examples/cfo_runway.json
python guagua.py call r03 contract scan --input examples/contract_scan.json
python guagua.py call r03 risk kyc --input examples/risk_kyc.json
```

**协作位置**：R06 的统计口径、R14 的支付与退款、R15 的采购库存、R16 的薪酬输入、R11/R12 的广告文案，都要经过 R03 复核。重大红线事项直接升级创始人。

**边界**：不出具持牌法律/投资定论，不执行支付/签约。**注意**：R03 目前以专家技能命令直接调用为主，没有 `run --task` 子命令；通过 `guagua.py call r03 ...` 使用，或由 R01/R02 以产物交接方式接入。

---

#### R04 · 蛙挑刺｜独立评审官

**定位**：公司的质检哨兵。只看成品和验收判据，不生产、不改稿、不猜。

**核心能力**：成品核验 · 硬门禁复核 · 外置判据 · 质量评价 · 事实来源检查 · 保留优点复评 · 人工评审工作流

**契约**：`artifact` + `acceptance_criteria` → `pass_fail` + `critique_report`

```bash
python guagua.py call r04 demo
python guagua.py call r04 artifact inventory --input examples/artifact_inventory.json
python guagua.py call r04 criteria review --input examples/criteria_review.json
python guagua.py call r04 quality critique --input examples/quality_critique.json
python guagua.py call r04 human package --input examples/human_package.json
```

**协作位置**：旁路直通创始人。任何角色交付的关键成品都可以送到 R04；R04 的 `pass/fail` 不被 R01 拦截。`reviewer == producer` 直接 FAIL。

**边界**：不生产、不改稿；没有成品不做猜测评价；自评不算数。

---

### 战略、数据与智能

#### R05 · 蛙深远｜战略研究官

**定位**：把「这个方向靠不靠谱」拆成有证据链的研究报告，而不是拍脑袋的行业八卦。

**核心能力**：深度研究 · 行业扫描 · 竞品情报 · 商业模式 · 市场规模测算 · 宏观情景 · 研究自动化

**契约**：`topic` + `scope` → `research_report` + `evidence_ledger`

```bash
python guagua.py call r05 demo
python guagua.py call r05 research report --input examples/research_report.json
python guagua.py call r05 competitor matrix --input examples/competitor_matrix.json
python guagua.py call r05 sizing size --input examples/sizing_size.json
python guagua.py call r05 scenario premortem --input examples/scenario_premortem.json
```

**协作位置**：研究结论交给 R07 做产品决策；涉及数据口径的结论交 R06；涉及合规/牌照的交 R03。

**边界**：不替创始人拍板；无来源的结论必须标「待核实」；不把行业观点写成确定事实。

---

#### R06 · 蛙得清｜数据分析师

**定位**：把业务问题变成可复算、可验证的数字结论。能吃 CSV、算指标、做漏斗/留存/RFM、跑统计检验、生成经营报告。

**核心能力**：指标语义建模 · 数据清洗质量 · 探索与产品分析 · 根因贡献度 · 统计因果实验 · 科学计算 NLP · 专业领域分析 · 可视化报告 · 自媒体数据运营

**契约**：`dataset` + `metrics_spec` → `dataset` + `analysis_report`

```bash
python guagua.py call r06 demo
python guagua.py call r06 semantics validate --input examples/semantic_model.json
python guagua.py call r06 quality audit --input ../workspace/r06-wadeqing-analyst/_loop_clean.csv
python guagua.py call r06 explore funnel --input ../workspace/r06-wadeqing-analyst/_loop_clean.csv --stage status
python guagua.py call r06 abtest --input ../workspace/r06-wadeqing-analyst/parking_ab.csv --group group \
  --control A --treatment B --metric revenue
python guagua.py call r06 deep --series ../workspace/r06-wadeqing-analyst/parking_profit_12m.csv \
  --cross ../workspace/r06-wadeqing-analyst/parking_profit.csv --before 2025-09 --after 2025-10 \
  --intent "停车场利润结构诊断"
```

**协作位置**：R07 出假设，R06 只验证假设、不发明方案；验证推翻假设时回 R07 改假设。R06 的图表/报告交给 R08 渲染，正式财务口径交 R03。

**边界**：数据不足不制造确定性；相关不写成因果；未观测混杂必须声明；正式财务/统计意见交 R03。

---

#### R18 · 蛙数仓｜数据工程与管道官

**定位**：让数据「稳定到达」——连接、ELT、数仓建模、调度、质量门禁、增量/回填、目录与血缘。

**核心能力**：数据连接 ELT · 数仓转换 · 管道调度 · 数据质量门禁 · 批流增量 · 数据目录 · 人工审批运维

**契约**：`source` + `metrics_spec` → `dataset` + `data_catalog`

```bash
python guagua.py call r18 demo
python guagua.py call r18 elt connection --input examples/connection.json
python guagua.py call r18 transform model --input examples/model.json
python guagua.py call r18 pipeline dag --input examples/dag.json
python guagua.py call r18 quality check --input examples/quality_check.json
python guagua.py call r18 catalog lineage --input examples/lineage.json
```

**协作位置**：把干净数据交给 R06 分析、R19 建模；数据新鲜度/管道告警接 R20；数据口径争议回 R06。

**边界**：不越权得出业务洞察；不解释数字含义；只保证数据稳定到达与可追溯。

---

#### R19 · 蛙智模｜模型工程与 AI 评估官

**定位**：让模型实验可复现、版本可追溯、评估可比较、发布有证据。

**核心能力**：实验追踪 · 模型注册与版本 · 评估数据集与评分器 · Agent Trace 与调试 · 回归与发布候选 · 模型监控接口 · 模型资产说明

**契约**：`dataset` + `model` → `experiment_log` + `evaluation`

```bash
python guagua.py call r19 demo
python guagua.py call r19 tracking experiment --input examples/tracking_experiment.json
python guagua.py call r19 registry register --input examples/registry_register.json
python guagua.py call r19 evaluation dataset --input examples/evaluation_dataset.json
python guagua.py call r19 release candidate --input examples/release_candidate.json
python guagua.py call r19 modelcard card --input examples/modelcard_card.json
```

**协作位置**：R18 供数、R06 做探索分析、R19 做模型实验与评估；模型监控接口交 R20；模型风险直接向创始人预警。

**边界**：不把实验结果包装成业务结论；模型监控接口归 R20；高风险模型必须披露限制与已知偏差。

---

### 产品与技术

#### R07 · 蛙得明｜产品经理

**定位**：把模糊需求变成可评审、可执行、可验收的产品决策。

**核心能力**：产品发现 JTBD · 机会树用户研究 · 用户故事 PRD · 优先级 Backlog · 路线图发布 · 愿景指标 · 技术翻译代码反推 · 经验检索决策汇报

**契约**：`research_report` + `voc` → `prd` + `backlog`

```bash
python guagua.py call r07 demo
python guagua.py call r07 discover jobstory --input examples/jobstory.json
python guagua.py call r07 prd prd --input examples/prd.json
python guagua.py call r07 priority rice --input examples/backlog.json
python guagua.py call r07 metrics northstar --input examples/northstar.json
python guagua.py call r07 techbrief techbrief --input examples/techbrief.json
```

**协作位置**：R05 研究 → R07 产品 → R08 快速实现 → R09 工程化 → R04 评审。R06 的数据结论可以推翻 R07 的假设，此时回 R07 重拟，不硬凑。

**边界**：不写生产工程代码（交 R09）；不替设计做品牌决策（R10）；不替创始人拍板。

---

#### R08 · 蛙建成｜产品实现官（MVP）

**定位**：用最快速度把 PRD 变成可演示的 MVP、落地页、脚手架或跨平台原型。

**核心能力**：产品切片 MVP · Spec 转仓库 · 落地页 H5 · SaaS 邮件脚手架 · 跨平台原型 · 组件设计实现 · 质量验证交接

**契约**：`prd` + `ui_brief` → `mvp` + `page_assets`

```bash
python guagua.py call r08 demo
python guagua.py call r08 slice slice --input examples/slice.json
python guagua.py call r08 scaffold scaffold --input examples/scaffold.json
python guagua.py call r08 landing landing --input examples/landing.json
python guagua.py call r08 prototype prototype --input examples/prototype.json
python guagua.py call r08 qa handoff --input examples/handoff.json
```

**协作位置**：R07 → R08；需要生产级质量时交 R09；需要视觉资产时接 R10；交付前可送 R04 验收。

**边界**：不承担生产级高可用工程；外部发布、生产部署、真实集成未接入时明确标为 simulated/blocked，不宣称已执行。

---

#### R09 · 蛙稳码｜代码工程官

**定位**：把 MVP 或技术规格做成生产级代码，并交付测试报告、迁移/安全/CI 方案。

**核心能力**：技术规格架构 · 数据库 API · 前后端全栈 · 跨端生产工程 · 测试浏览器验证 · 调试性能重构 · 迁移 CI/CD 安全 · 特殊技术载体

**契约**：`mvp` + `spec` → `production_code` + `test_report`

```bash
python guagua.py call r09 demo
python guagua.py call r09 spec spec --input examples/spec_spec.json
python guagua.py call r09 data_api api --input examples/data_api_api.json
python guagua.py call r09 testing suites --input examples/testing_suites.json
python guagua.py call r09 local-verify --project . --kind unittest --command python
```

**协作位置**：R08 → R09；R09 的 `test_report` 交 R04；拓扑交 R20 做监控；不可逆线上操作必须授权。

**边界**：不做监控备份（R20）、不做快速原型（R08）；破坏性变更（drop/truncate/force push）无授权即拦。

---

#### R10 · 蛙成美｜视觉设计官

**定位**：把品牌简报和内容变成可交付的视觉规范、Logo/VI、UI/UX、动效、图片/视频处理任务单。

**核心能力**：AI 生图插画 · Logo 图标 VI · 产品 UI/UX · 交互原型动效 · 修图图像工程 · 视频音频处理 · 转写字幕 · 数据视觉营销物料

**契约**：`brand_brief` + `content` → `visual_assets` + `vi`

```bash
python guagua.py call r10 demo
python guagua.py call r10 imagegen prompt --input examples/prompt.json
python guagua.py call r10 logo logo --input examples/logo.json
python guagua.py call r10 uiux screen --input examples/screen.json
python guagua.py call r10 brand vi --input examples/vi.json
python guagua.py call r10 render poster --input examples/poster.json
```

**协作位置**：R11 文案 → R10 配图/视觉；R08/R09 实现时使用 R10 的设计令牌与组件规格；品牌决策升级创始人。

**边界**：不写代码逻辑；图像生成、转码、转写、外部发布未接入时属于 simulated 或 blocked；不冒充已生成真实资产。

---

### 市场与客户

#### R11 · 蛙点题｜内容主笔

**定位**：把主题变成有策略、有钩子、有平台适配的内容，并对文本格式和长度做本地校验。

**核心能力**：内容策略选题 · SEO/AEO · 钩子提纲 · 文案长文 · 品牌语调编辑 · 广告公关 · 多平台适配 · 持续本地化

**契约**：`topic` + `audience` → `content_draft` + `publish_list`

```bash
python guagua.py call r11 demo
python guagua.py call r11 topic plan --input examples/plan.json
python guagua.py call r11 copy article --input examples/article.json
python guagua.py call r11 seo audit --input examples/keyword.json
python guagua.py call r11 platform adapt --input examples/adapt.json
python guagua.py call r11 localize term --input examples/term.json
```

**协作位置**：R11 成稿 → R10 配图 → R12 投放 → R06 复盘归因；广告/公关合规交 R03。

**边界**：不负责渠道投放执行（R12）；真实翻译服务、SEO 平台数据、发布排期未接入时明确降级，不宣称已发布。

---

#### R12 · 蛙引流｜增长运营官

**定位**：把内容或产品变成可执行的获客、激活、留存、推荐和归因方案。

**核心能力**：增长诊断基线 · 增长循环自然获客 · 冷启动外联 · 红人合作增长 · ASO 发布 · 付费投放 CRO · 激活留存推荐 · 归因 RevOps · 自媒体运营

**契约**：`content_draft` + `product` → `growth_plan` + `channel_assets`

```bash
python guagua.py call r12 demo
python guagua.py call r12 diagnose diagnose --input examples/diagnose.json
python guagua.py call r12 loops flywheel --input examples/flywheel.json
python guagua.py call r12 outreach coldemail --input examples/coldemail.json
python guagua.py call r12 paid cro --input examples/cro.json
python guagua.py call r12 revops roi --input examples/roi.json
```

**协作位置**：接 R11 内容、R07 产品；增长实验结论交 R06 复核；广告合规交 R03；转化链路接 R13/R14。

**边界**：不写稿（R11）；不处理支付/履约（R14/R15）；广告文案合规必须 R03 复核。

---

#### R13 · 蛙客成｜客户成功与销售运营官

**定位**：管客户、联系人、销售管道、跟进活动、客服工单、VOC、健康分和续约风险。

**核心能力**：客户与联系人管理 · 销售管道 · 销售活动与跟进 · 全渠道客服 · 客户反馈 VOC · 客户健康续约 · 服务知识与升级 · 客户运营自动化接口

**契约**：`lead` + `order_status` → `crm_record` + `voc`

```bash
python guagua.py call r13 demo
python guagua.py call r13 crm person --input examples/person.json
python guagua.py call r13 pipeline pipeline --input examples/pipeline.json
python guagua.py call r13 support inbox --input examples/inbox.json
python guagua.py call r13 health health --input examples/health.json
python guagua.py call r13 voc survey --input examples/survey.json
```

**协作位置**：VOC 反哺 R07/R11；订单状态来自 R14/R15；客户红线升级 R01；自动化需求交 R17。

**边界**：不处理支付/履约（R14/R15）；不涉及底层支付账务；客户数据使用遵守隐私红线（R03）。

---

### 交易与组织运营

#### R14 · 蛙交易｜交易与收入履约官

**定位**：管商品、订单、订阅计费、支付、电子签、预约、交易状态机和收入事件。

**核心能力**：商品电商后端 · 订阅计量计费 · 支付集成 · 电子签审计 · 服务预约 · 交易状态编排 · 收入数据接口 · 交易自动化接口

**契约**：`package` + `quotation` → `order` + `payment_status`

```bash
python guagua.py call r14 demo
python guagua.py call r14 catalog product --input examples/product.json
python guagua.py call r14 order cart --input examples/cart.json
python guagua.py call r14 billing invoice --input examples/invoice.json
python guagua.py call r14 payment payment_intent --input examples/payment_intent.json
python guagua.py call r14 signature signing --input examples/signing.json
python guagua.py call r14 workflow transition --input examples/transition.json
```

**协作位置**：R14 订单 → R15 履约；收入数据交 R03/R06；退款争议交 R03；高风险交易动作需人工授权。

**边界**：不出财务意见（R03）；不代替创始人签约/退款；支付、签名、预约的真实外部集成未接入时只做本地契约校验。

---

#### R15 · 蛙供应｜ERP 与供应链运营官

**定位**：管采购、供应商、库存、仓库、销售履约、生产资源、财务业务接口和主数据权限。

**核心能力**：采购供应商 · 库存仓库 · 销售履约记录 · 生产服务资源 · ERP 财务接口 · 主数据权限 · 运营报表

**契约**：`order` + `sop` → `purchase_order` + `inventory_ledger`

```bash
python guagua.py call r15 demo
python guagua.py call r15 procurement purchase_order --input examples/purchase_order.json
python guagua.py call r15 inventory bin --input examples/bin.json
python guagua.py call r15 fulfillment sales_order --input examples/sales_order.json
python guagua.py call r15 production bom --input examples/bom.json
python guagua.py call r15 masterdata permission --input examples/permission.json
```

**协作位置**：R14 订单 → R15 采购/库存/履约；财务业务接口交 R03；库存风险升级 R01；履约状态回 R13/R14。

**边界**：不出财务意见；不代付款；大额库存/供应风险必须上报。

---

#### R16 · 蛙人事｜人员与组织运营官

**定位**：管招聘、入职、人员档案、考勤休假、绩效目标、薪酬准备、费用福利和组织报表。

**核心能力**：招聘与入职 · 人员与合同档案 · 考勤与休假 · 绩效与目标 · 薪酬准备 · 费用与福利业务 · 组织运营报表

**契约**：`org_decision` + `roles` → `roster` + `payroll_input`

```bash
python guagua.py call r16 demo
python guagua.py call r16 recruit offer --input examples/offer.json
python guagua.py call r16 people employee --input examples/employee.json
python guagua.py call r16 attendance leave --input examples/leave.json
python guagua.py call r16 performance goal --input examples/goal.json
python guagua.py call r16 payroll calc --input examples/payroll_calc.json
```

**协作位置**：组织决策来自 R01；薪酬输入交 R03 复核；招聘需求接 R07/R02；人事数据的使用受隐私红线约束。

**边界**：薪酬输入必须 R03 复核；劳动合规严格交 R03；PII 最小化，禁止把身份证/银行卡/住址等敏感字段写入工件。

---

### 自动化与可靠性

#### R17 · 蛙织网｜自动化与集成工程师

**定位**：做跨系统胶水层——API 集成、Webhook、字段映射、定时批处理、人工审批、失败重试、AI 工作流和审计。

**核心能力**：SaaS/API 集成 · Webhook 事件 · 字段身份映射 · 定时批处理 · 人工审批 · 失败重试 · AI 工作流 · 审计

**契约**：`rules` + `fields` → `workflow` + `audit_log`

```bash
python guagua.py call r17 demo
python guagua.py call r17 integration workflow --input examples/workflow.json
python guagua.py call r17 webhook event --input examples/event.json
python guagua.py call r17 mapping table --input examples/table.json
python guagua.py call r17 approval publish --input examples/publish.json
python guagua.py call r17 aiworkflow model --input examples/model.json
```

**协作位置**：把 R14/R15/R16/R18 的系统动作串起来；高危动作必须人工审批；审计日志交 R04/R20。

**边界**：不内嵌复杂业务逻辑（R09）；不直接执行高风险动作；发布/上线必须有显式请求或 live run 证据。

---

#### R20 · 蛙值守｜可靠性与恢复官

**定位**：让系统可监控、可告警、可沟通、可备份、可恢复、可复盘。

**核心能力**：可用性监控 · 告警升级 · 状态页沟通 · 加密增量备份 · 恢复演练 · 灾难恢复回滚 · 运行复盘

**契约**：`topology` + `asset_list` → `monitor_config` + `backup_repo`

```bash
python guagua.py call r20 demo
python guagua.py call r20 monitor monitor --input examples/monitor.json
python guagua.py call r20 alert escalation --input examples/escalation.json
python guagua.py call r20 backup backup --input examples/backup.json
python guagua.py call r20 restore drill --input examples/drill.json
python guagua.py call r20 postmortem postmortem --input examples/postmortem.json
```

**协作位置**：R09 提供拓扑；R02 提供事故流程；R19 提供模型监控接口；重大事故直通 R01/创始人。

**边界**：不做应用实现（R09）；不擅自删除快照、修改生产告警或执行灾难切换；**备份存在 ≠ 恢复成功，必须演练**。

---

## 六、可复用协作流水线（报告产线 + 六条协作链）

| # | 流水线 | 链路 | 适用场景 | 入口 |
|---|---|---|---|---|
| 0 | 报告产线（默认） | R01 拆卡 → 子智能体按 nonce 交 `claims.json` → R01 合并 → R04 验收 | 调研报告、经营分析（当前唯一默认） | `report clarify → brief --plan --confirm → preflight → collect → run-line --claims` |
| 1 | 从想法到上线 | R05 研究 → R07 产品 → R08 MVP → R09 工程 → R04 评审 | 新产品、新功能 | `plan` + `dispatch` |
| 2 | 数据驱动经营 | R07 假设 → R06 验证 → R08 渲染 → R04 复核 | 营收、定价、增长方案 | `plan` + `dispatch` |
| 3 | 内容增长 | R11 成稿 → R10 视觉 → R12 投放 → R06 归因 | 内容营销、获客 | `call` 逐段执行 |
| 4 | 合规闭环 | 任一产出 → R03 合规复核 → R04 独立评审 | 涉钱、合同、隐私、广告 | `call r03` + `call r04` |
| 5 | 交易履约 | R14 交易 → R15 供应链 → R03 财务复核 → R04 验收 | 订单、收款、交付 | `call r14` → `call r15` |
| 6 | 可靠性值守 | R09 拓扑 → R20 监控/备份 → R02 事故流程 → R01 收口 | 上线后运维、事故复盘 | `call r20` + `call r02` |

### 示例：数据驱动经营（已验证的最小闭环）

```bash
# 1) R01 拆卡：识别为营收/利润优化场景
python guagua.py plan "停车场一年营收最大化"

# 2) 看任务依赖
python guagua.py status

# 3) 按依赖执行并验收
python guagua.py dispatch --all
```

这条链会按 R07 → R06 → R08 → R04 的顺序走：产品经理出假设，数据分析师验证，MVP 角色渲染报告，评审官独立复核。若 R06 推翻 R07 的假设，协议要求回 R07 重拟，不允许硬凑结论。

### 示例：只用一个角色

```bash
# 数据分析
python guagua.py call r06 explore funnel --input ../workspace/r06-wadeqing-analyst/_loop_clean.csv --stage status

# 独立验收
python guagua.py call r04 criteria review --input examples/criteria_review.json

# 财务红线
python guagua.py call r03 financial rollforward --input examples/financial_rollforward.json
```

---

## 七、统一入口与全部功能调用

### 7.1 为什么需要统一入口

20 个角色分散在 20 个目录，每个角色又有 7～9 个技能组。`guagua.py` 提供一层薄封装：

- **不复制业务逻辑**：它只负责找角色、切目录、转发参数、汇总结果。
- **不限制功能**：`call <role> <任意参数>` 原样转发，角色以后新增子命令也自动可用。
- **不破坏老用法**：你仍然可以直接 `python r06-wadeqing-analyst/agent.py ...`。

### 7.2 命令总表

| 命令 | 作用 | 示例 |
|---|---|---|
| `roles` | 列出 20 个角色 | `python guagua.py roles` |
| `info <role>` | 查看角色能力、契约、入口 | `python guagua.py info r06` |
| `call <role> ...` | 调用角色任意子命令 | `python guagua.py call r06 --help` |
| `chat --role ... --intent ...` | 生成知识注入 Prompt | `python guagua.py chat --role r06 --intent "分析留存"` |
| `plan "<意图>"` | R01 拆任务卡 | `python guagua.py plan "营收最大化"` |
| `status` | 查看任务状态 | `python guagua.py status` |
| `dispatch --all` | R01 执行并验收 | `python guagua.py dispatch --all` |
| `dispatch --task <id>` | 执行单张任务卡 | `python guagua.py dispatch --task a1b2c3d4` |
| `demo <role>` | 运行角色 demo | `python guagua.py demo r06` |
| `demo --all` | 依次运行全部 demo | `python guagua.py demo --all` |
| `check` | 体检 20 个入口 | `python guagua.py check` |
| `doctor` | 环境诊断 + 体检 | `python guagua.py doctor` |
| `report clarify` | 接活澄清：意图/问句/假设/待确认项 | `python guagua.py report clarify --intent "…" --out <项目>` |
| `report intake` | 记录用户对 12 问的回答（≥10 条才可签 brief） | `python guagua.py report intake --dir <项目> --answer I1=…` |
| `report brief --plan` | 出「问题→角色」映射与卡片清单（不发卡） | `python guagua.py report brief --dir <项目> --plan` |
| `report brief --plan --confirm` | 用户点头后确认发卡（需 `--ack-cards --user-said`） | `python guagua.py report brief --dir <项目> --plan --confirm --ack-cards --user-said "确认"` |
| `report preflight` | 拆卡线九项预检 P1–P9 | `python guagua.py report preflight --dir <项目>` |
| `report collect` | 收卡：nonce/来源/回抓 → `claims_merged.json` | `python guagua.py report collect --dir <项目> --out <项目>/out` |
| `report run-line`（或 `report "…"`） | 报告执行入口：唯一 HTML 渲染 + 门禁 | `python guagua.py report run-line --intent "…" --claims <项目>/out/claims_merged.json --out <项目>/out/report --pdf` |
| `report research-plan` | 一句话 → 研究方案（8 模块 / 专家 / 数据通道），不产报告 | `python guagua.py report research-plan --intent "…" --out <项目>/plan` |
| `report flow` | 项目化 flow 报告（facts + charts） | `python guagua.py report flow --project <项目> --out <目录> --pdf` |
| `report check` | 验成品报告：九条 flow 门禁 + 深度门禁 | `python guagua.py report check --html report.html` |
| `report attest` | 交付口径：门禁/来源/核验/降级（从 manifest 回填） | `python guagua.py report attest --out <目录>` |
| `report charts` | 48 型图表能力盘点 | `python guagua.py report charts` |
| `capabilities` | 能力目录：谁拥有 / 谁能用 / 形态 | `python guagua.py capabilities` |
| `skills` | 技能包索引（SKILL.md 选型） | `python guagua.py skills` |

### 7.3 如何调用「全部功能」

```bash
# 1) 先看角色支持哪些子命令
python guagua.py call r06 --help

# 2) 再逐层下钻
python guagua.py call r06 explore --help
python guagua.py call r06 explore funnel --help

# 3) 直接执行
python guagua.py call r06 explore funnel \
  --input ../workspace/r06-wadeqing-analyst/_loop_clean.csv --stage status
```

`call` 的规则只有一条：**第一个参数是角色，后面的参数全部交给该角色的 `agent.py`**。因此角色支持的任何技能、动作、参数、`--help`、`demo`、`run --task` 都可以通过这一个入口调用。

### 7.4 推荐阅读顺序

1. 本 README（组织与角色全貌）
2. [`使用指南.md`](蛙蛙呱呱agents团/使用指南.md)（逐角色命令、流水线、排错）
3. [`ORG.md`](蛙蛙呱呱agents团/ORG.md)（组织章程与红线）
4. [`PROTOCOL.md`](蛙蛙呱呱agents团/PROTOCOL.md)（任务卡与移交协议）
5. [`REPORT-STANDARD.md`](蛙蛙呱呱agents团/REPORT-STANDARD.md)（汇报格式）
6. [`docs/REPORT-LINES.md`](蛙蛙呱呱agents团/docs/REPORT-LINES.md)（报告产线地图与门禁）

---

## 八、目录结构与文档索引

```text
蛙蛙呱呱/                        # 仓库根（git 仓库）
├─ README.md                     # 本文件：总览 + 20 角色详解 + 协作方式
├─ 蛙蛙呱呱agents团/             # ★ 智能体公司本体（20 角色）
│  ├─ guagua.py                  # 统一入口（project / prompt / plan / report / run）
│  ├─ chat.py                    # [已废弃] 兼容壳；提示词入口是 guagua.py prompt
│  ├─ CHANGELOG.md               # 智能体更新日志（按日期记录能力与迁移）
│  ├─ SKILL.md                   # Trae 技能入口（拆卡线默认 + 人环门禁）
│  ├─ ORG.md / PROTOCOL.md       # 组织章程 / 协同协议
│  ├─ REPORT-STANDARD.md         # 汇报标准（唯一产线：R01 出具）
│  ├─ REPORT-BRIDGE-GUIDE.md     # 接入唯一产线（角色只交 result）
│  ├─ core/                      # paths / project / dispatch / card_bundle / card_issue / report_cli…
│  ├─ configs/                   # 卡片契约 / 流程 / 覆盖阈值 / core_files 登记
│  ├─ r01-… r20-…                # 20 个角色（agent.py + skills/ + harness + tests + references）
│  ├─ agent-packs/               # 宿主可直接加载的角色包
│  ├─ shared/                    # 共享能力（运行时、治理、方法、knowledge/brief）
│  ├─ docs/                      # 产线地图、版式、门禁契约（索引见 docs/README.md）
│  ├─ 交付/                      # 仅剩 generic_semantics_v1.yaml（运行时依赖，勿删）
│  ├─ tests/                     # pytest 单测 + 回归 + prompt 回归（不是缓存）
│  └─ scripts/                   # CI 门禁、preflight、生成器、Trae 镜像同步
├─ projects/                     # ★ 项目资产根（数据/brief/卡/claims/报告；不入库）
├─ workspace/                    # 运行物根（events/lock/runlog/traces；不入库）
├─ traeskills/                   # Trae 侧其它技能镜像（3 个）
├─ workbuddy专家团/              # WorkBuddy 侧专家团镜像（4 个子团队）
└─ .dsh/skills/                  # DSH 侧技能镜像
```

> **打包分发**：`python "蛙蛙呱呱agents团/scripts/make_package.py"` 会生成
> `蛙蛙呱呱agents团.zip` 到仓库根（排除 `workspace/`、缓存与日志，内置
> `PACKAGE_INFO.json` 记录版本、时间、git commit 与文件数）。zip 不入库，
> 需要时随时重打包。

> **产物分两类，都不写进 `蛙蛙呱呱agents团/`**：运行物（事件/锁/trace/runlog）在
> `<仓库根>/workspace`；项目资产（数据/brief/卡/claims/报告）在 `<项目根>`，
> 默认 `<仓库根>/projects/<slug>`。写团内会被 [`core/paths.py`](蛙蛙呱呱agents团/core/paths.py)
> 拒绝（退出码 2）。说明见 [`使用指南.md`](蛙蛙呱呱agents团/使用指南.md) §2.7/§6.2.1。

### 关键文档

| 文档 | 作用 |
|---|---|
| [`ORG.md`](蛙蛙呱呱agents团/ORG.md) | 组织架构、汇报线、权力与红线、角色边界 |
| [`PROTOCOL.md`](蛙蛙呱呱agents团/PROTOCOL.md) | 单角色五步、失败移交、多角色 GSD 编排、验收协议 |
| [`TEAM.md`](蛙蛙呱呱agents团/TEAM.md) | 「营收最大化」编排实例 |
| [`REPORT-STANDARD.md`](蛙蛙呱呱agents团/REPORT-STANDARD.md) | 交付报告的统一结构与文风 |
| [`REPORT-BRIDGE-GUIDE.md`](蛙蛙呱呱agents团/REPORT-BRIDGE-GUIDE.md) | 报告桥接指南 |
| [`SKILL.md`](蛙蛙呱呱agents团/SKILL.md) | Trae 技能入口：唯一的拆卡默认线、人环规则、能力边界 |
| [`docs/REPORT-LINES.md`](蛙蛙呱呱agents团/docs/REPORT-LINES.md) | 报告产线地图：拆卡默认 / A 数据 / B 应急，门禁与保留零件 |
| [`CHANGELOG.md`](蛙蛙呱呱agents团/CHANGELOG.md) | 专家团（智能体）更新日志：按日期记录能力、门禁、迁移与不兼容 |
| [`docs/REPORT-DISPATCH.md`](蛙蛙呱呱agents团/docs/REPORT-DISPATCH.md) | 拆卡与防代写：nonce、签名、收卡校验 |
| [`docs/REPORT-FLOW.md`](蛙蛙呱呱agents团/docs/REPORT-FLOW.md) | flow 版式规范：一条内容流、PDF 分页、摘要必填、文笔门禁 |
| [`docs/archive/交付/拆卡升级-SOP-2026-11-21.md`](蛙蛙呱呱agents团/docs/archive/交付/拆卡升级-SOP-2026-11-21.md) | 拆卡五个 SOP 版本与卡片契约（历史，被 docs 引用） |
| [`docs/archive/交付/协作层-SOP-2026-11-21.md`](蛙蛙呱呱agents团/docs/archive/交付/协作层-SOP-2026-11-21.md) | 卡间协商、R02 交接包与波次（历史） |
| [`scripts/preflight.py`](蛙蛙呱呱agents团/scripts/preflight.py) | 九项预检 P1–P9（唯一可执行判据） |
| [`docs/actions_catalog.json`](蛙蛙呱呱agents团/docs/actions_catalog.json) | 全角色动作目录（机器可读） |
| [`core/registry.py`](蛙蛙呱呱agents团/core/registry.py) | 20 角色能力与端口注册表 |
| [`core/protocol.py`](蛙蛙呱呱agents团/core/protocol.py) | 任务卡、事件、端口字段契约 |

### `交付/` 与归档引用关系（2026-11-25 核查）

> 历史 SOP 与模板已归档到 `docs/archive/交付/`；团内 `交付/` 只剩 `generic_semantics_v1.yaml`。

| 文件 | 状态 | 被谁引用 |
|---|---|---|
| `交付/generic_semantics_v1.yaml` | **代码依赖（勿删）** | [`core/card_upgrade.py`](蛙蛙呱呱agents团/core/card_upgrade.py#L160) 读取；`semantic_layer.template.yaml` 继承 |
| `docs/archive/交付/semantic_layer.template.yaml` | 模板 | `card_issue.py` 内置同名模板并写入项目；归档副本供参考 |
| `docs/archive/交付/perspectives.template.yaml` | 模板 | `docs/archive/交付/拆卡升级-SOP-2026-11-21.md` |
| `docs/archive/交付/agent_card.template.yaml` | 模板 | 暂无引用（保留作交付样例） |
| `docs/archive/交付/handoff_contract.template.yaml` | 模板 | 暂无引用（保留作交付样例） |
| `docs/archive/交付/拆卡升级-SOP-2026-11-21.md` | 历史 SOP | [`docs/REPORT-LINES.md`](蛙蛙呱呱agents团/docs/REPORT-LINES.md) |
| `docs/archive/交付/协作层-SOP-2026-11-21.md` | 历史 SOP | `拆卡升级-SOP-2026-11-21.md` |
| `docs/archive/交付/报告系统升级SOP-2026-11-21.md` | 过程记录 | `50材料核验` 与两份设计稿互引 |
| `docs/archive/交付/50材料核验-2026-11-21.md` | 证据附件 | `报告系统升级SOP-2026-11-21.md` |
| 专家团升级 SOP v1 / v2.1 / v3 / v4 / v5 + 计划 v5 | 版本链 | 仅内部互引，最新为 v5 |
| 调研结论 / 系统升级执行报告 / 验收报告 / 修复设计 html | 过程记录 | 无引用 |

> 结论：**团内只有 `交付/generic_semantics_v1.yaml` 是运行时依赖**，其余是归档模板与过程文档。
> 要删任何一份，先按上表改引用；`tests/` 不是缓存，是 547 个 pytest 用例与 evals 夹具，必须保留。

---

## 九、运行、验收与能力边界

### 环境

- Python **3.10+**（当前验证环境为 3.12）
- Git
- 统一入口、`chat.py`、大部分确定性校验只依赖标准库
- 部分角色（数据分析、图像、媒体、模型）需要可选的第三方库；缺依赖时角色会返回 `blocked` 或 `simulated`，不会假装成功

### 自检

```bash
cd "D:\蛙蛙呱呱\蛙蛙呱呱agents团"

# 1) 入口与环境
python guagua.py doctor
python guagua.py check

# 2) 单测（当前基线：547 passed / 3 skipped）
python -m pytest tests -q -p no:cacheprovider

# 3) 拆卡线项目预检（项目根在团外，默认 projects/<slug>）
python scripts/preflight.py --dir "../projects/<slug>"

# 4) 收敛门禁与 Trae 镜像
python scripts/check_convergence.py --baseline .convergence-baseline.json
python scripts/sync_trae_skill.py --check
```

> 全量自检清单（角色端到端、图表、技能卡、许可等）见 [`AGENTS.md`](蛙蛙呱呱agents团/AGENTS.md)。

### 单角色测试

```bash
cd r06-wadeqing-analyst
python run_tests.py
python verify_loop.py
```

不同角色的测试入口略有差异：大多数有 `run_tests.py`，部分有 `verify_loop.py`、`tests/`。以各角色目录内文件为准，不要假设 20 个角色测试命令完全一致。

### 产物位置

专家团是**工具**，项目是**资产**，两类产物分开放：

- **运行物**（事件流、锁、trace、runlog）：`workspace/`（仓库根；`GUAGUA_WORKSPACE` 可改）
- **项目资产**（数据、知识快照、brief、卡、claims、报告）：`<PROJECT_ROOT>`，
  默认 `projects/<slug>`，可用 `--project` 或 `GUAGUA_PROJECT` 覆盖
- **任务账本**：带 `--project` 时落 `<项目>/runs/tasks/`，否则落 `workspace/tasks/`
- **写团内一律被拒**：越界返回退出码 2（守门在 [`core/paths.py`](蛙蛙呱呱agents团/core/paths.py)）

```bash
python guagua.py project init ../projects/<slug> --industry "你的行业"
python guagua.py plan "你的经营目标" --project ../projects/<slug>
```

说明见 [`使用指南.md`](蛙蛙呱呱agents团/使用指南.md) 的 §2.7 与 §6.2.1。

### 能力边界（重要）

1. **本地确定性 ≠ 线上已执行**：很多角色能验证契约、生成工件、跑本地计算，但外部发布、支付、部署、真实 CRM/ERP 写入未接入时会标为 `simulated` 或 `blocked`。
2. **R03 的入口差异**：R03 蛙守线没有 `run --task` 子命令，使用 `guagua.py call r03 ...` 直接调用专家技能；其余 19 个角色均支持任务卡入口。
3. **不可逆动作必须人工授权**：裁员、关停、签约、付款、删除快照、灾难切换、生产恢复等，任何角色都不能自动执行。
4. **质量结论只归 R04**：其他角色可以自检，但不能给自己签 `pass`。
5. **数据与隐私**：不要把真实密钥、身份证、银行卡、生产凭据写入工件；R03/R16/R20 都有相应红线检查。
6. **A 数据驱动仍可绕过拆卡**：`report "…" --dir <有 CSV/JSON 的项目> --out …` 走 `decision_report`，
   不经过 `preflight / issued / nonce`。它是「已有干净数据」的快捷路，不是调研报告默认；
   需要可审计的调研必须走拆卡线。
7. **单人稿是应急降级**：`--solo-claims --allow-solo` 只解决「确实只有一个作者」的场景，
   产物会标 `solo_no_dispatch`，且仍要过 50 条唯一 URL。
8. **paper 版式已下线**：`--layout paper` 会直接报错；需要分页由 PDF 导出器做。

---

## 十、版本与更新记录

### v2.9（2026-11-27）· 20 角色厚度升级 + 五条生产线 + 架构收敛

- **能力厚度**：完成 20 角色能力升级，五条业务生产线全部打通（决策/研究、产品/工程、
  内容/增长、交易/供应链、数据/模型/SRE）；角色的 `SKILL.md`、引擎、经验层与验收同步加厚。
- **P4 物理分包**：`core/` 按域迁入 `core/base`、`core/data`、`core/sources`、`core/charts`、
  `core/claims`、`core/cards`、`core/report`、`core/prose`，退役兼容 shim。
- **P5 逻辑收敛**（同类只留一个实现）：
  - claims 契约单一出处，契约版本统一 `v4`，mapping 层并入 claims；两套交付形态统一字段形状；
  - prose 五合一：`prose_spec/style/candidates/report_prose_gen` → `prose_contract` + `prose_render`；
  - cards 唯一编排入口 `core/cards/pipeline.py`（合并 plan/bundle/probe/card_issue/report_dispatch/dispatch）；
  - `report` CLI 后端统一走 `report_line` 门面；移除 `core` 零使用懒加载分组。
- **接线与索引**：`wiring_truth` 接线真相表（LIVE 31 / 未接线 0 / 文档死链 0）；新增导航层
  `GLOSSARY` / `ENTRYPOINTS` / `GATES` / `couplings`，文档收敛为 10 篇现行 + 5 篇根入口，其余归档 `docs/archive/`；
  断舍离 12 个未接模块。
- **门禁与测试**：F12 结构检查只作用于作者草稿；导航入口锁定、退役死 smoke 脚本；
  新增 27 条合并后 pipeline 直连回归 + card-line 回归（`CI_CARDS_SAMPLE` 门禁）；数据线样例三意图过 CI。
- **WorkBuddy 同步**：镜像改为严格对齐源（清理 337 个已删残留，`source/` 与源零漂移）。
- 全量条目见 [`CHANGELOG.md`](蛙蛙呱呱agents团/CHANGELOG.md)。

### v2.8（2026-11-25）· 项目边界 + expert_brief v2

- **工具与资产分离**：新增 [`core/paths.py`](蛙蛙呱呱agents团/core/paths.py)（团/项目/运行三个根 + 写入守卫）
  与 [`core/project.py`](蛙蛙呱呱agents团/core/project.py)（`project.yaml` + 10 个标准子目录）；
  写团内、写运行根一律拒绝（退出码 2）。
- **卡 = bundle**：每张卡下发时带 `expert_brief`（v2 七层：决策语境 / 定义口径 / 结构分解 /
  机制归因 / 判断情景 / 行动可逆 / 反证不确定）；每条必答过五道门槛
  （answerable_by / evidence / owner / failure_impact / check）；单卡上限 18 条，超出进 `parking_lot`。
  卡只管 owner/deps/inputs/outputs/non_goals，**验收只由 brief 派生**。
- **收卡校验契约**：`dispatch.collect()` 校验 `brief_version` 一致、卡里无 acceptance 明细；
  报告拆卡线把 brief 问题写进 `issued.json.brief_issues`，不静默。
- **入口收敛**：`guagua.py prompt` 成为唯一提示词入口；`chat.py` / `guagua.py chat` 标废弃
  （保留一个版本）；新增 `guagua.py project init/show`。
- **门禁 12 → 15 项**：新增 `check_project_boundary`（团内无项目资产）、
  `check_brief_contract`（七层/五门槛/18 条不回退）、`check_report_isolation`（报告层不读知识库与 brief）。
- **迁移**：历史项目产物（如 `projects/consulting`）移出工具仓库；未带 `--project` 的 `plan`
  仍可运行但会提示迁移，下一版本项目根必填；老卡仍可 `--allow-legacy` 收，但不再享受 brief 契约校验。
- 全量条目见 [`CHANGELOG.md`](蛙蛙呱呱agents团/CHANGELOG.md)。

### v2.7（2026-11-24）· 统一入口路由器（D+）与报告线收口

- `guagua.py run` 路由器：默认只打印建议命令，`--execute` 才执行；
  按 `--role / --dir+--out / --intent` 选单角色、报告线或拆卡线。
- `report run-line --source data|cards` 明确「报告层算」还是「收卡编译」；
  `call --as-task` 只写 `workspace/traces` 并标 `trace_only`，不混入项目账本。
- P0–P2 收口：报告线门禁修复、依赖声明、死接线与孤立模块、历史文档归档到 `docs/archive/`、
  新增 `guagua.py audit`（快检 + `--full`）、`.gitignore` 补齐运行产物。
- 报告产线统一到 v14，新增文档一致性门禁。

### v2.6（2026-11-22）· 拆卡线唯一默认 + 人环门禁 + 50 源硬门槛

- **默认路线唯一化**：报告默认只走拆卡线（`clarify → intake → brief --plan → --confirm --ack-cards
  → preflight → collect → run-line --claims`）；没有 `coverage/issued.json` 的项目 `collect` 直接拒收，
  老卡只有显式 `--allow-legacy` 才放行并标 `legacy_no_issued`。
- **防代写接线**：每张卡带 `nonce + HMAC 签名`，`claims.dispatch.by` 不能是 `r01/solo/orchestrator`；
  `collect` 与 `preflight` 都会校验，对不上整卡拒收。
- **人必须在环里**：`intake` 记录 `user_answers`（≥10 才能签 brief）；`clarify --confirm` 必须带
  `--user-said` 原话；发卡必须 `--ack-cards`，并把 `acknowledged_at/by` 写进 `plan.json`；
  `preflight` 新增 P8/P9 专查这三件事。
- **来源门槛**：`collect` 默认 `--min-sources 50`，按唯一 URL 计数，默认逐条回抓 quote；
  关回抓/关严格必须 `--allow-degraded`，降级写 manifest。
- **单人稿显式降级**：`run-line --claims` 只认收卡产物；手写稿必须 `--solo-claims --allow-solo`，
  过 50 源门槛，产物标 `solo_no_dispatch`。
- **渲染固化**：封面与 KPI 优先取 `meta.title / subtitle / metrics`，不再被首节标题覆盖。
- **公开样例**：当时在 `showcase/` 放了一份脱敏报告（竞品/店铺/供应商名以 `████` 遮蔽）；
  2026-11-25 起项目产物迁出工具仓库，样例不再随仓库分发，改为按需生成。
- **仓净**：删除 `workspace/`（191.8 MB 历史试跑）、`_attic/`（34 MB 留档）、`z/` 与无关赛道调研残留；
  技能包降到约 30 MB；`tests/`（104 个用例与 evals 夹具）保留不动。

### 历史版本（摘要）

| 版本 | 日期 | 主要变化 |
|---|---|---|
| v2.6 | 2026-11-22 | 拆卡线唯一默认；nonce + HMAC 防代写；人环门禁（intake/clarify/ack-cards）；50 源硬门槛 |
| v2.5 | 2026-11-19 | 报告产线收敛为单入口；`flow` 成为默认版式；`collect` 默认 50 源并逐条回抓 quote |
| v2.2 | 2026-11-17 | 报告判据唯一（F10 深度判据）；20 角色自检转绿；真实/模拟/阻塞三态归位 |
| v2.1 | 2026-11-12 | 仓库瘦身（删除 11736 个历史文件）；固化 `make_package.py` 打包入口 |
| v2.0 | 2026-11-10 | 重写 README；新增 `guagua.py` 统一入口与 20 角色介绍 |

> 全量、按日期的智能体更新记录见 [`CHANGELOG.md`](蛙蛙呱呱agents团/CHANGELOG.md)；
> 本节只保留仍影响当前使用的版本，逐条提交历史用 `git log` 查。
> 已被后续版本推翻的口径（如 `--layout paper`、A/B 双路）不再在正文重复。

### 维护约定

- 新增角色：先更新 [`core/registry.py`](蛙蛙呱呱agents团/core/registry.py)，再建角色目录、`agent.py`、`SKILL.md`、测试，最后同步本 README 与使用指南。
- 新增技能：更新角色 `SKILL.md` 与 `contracts.py`，并补一条可复现的测试或夹具。
- 修改协作规则：以 [`ORG.md`](蛙蛙呱呱agents团/ORG.md) 和 [`PROTOCOL.md`](蛙蛙呱呱agents团/PROTOCOL.md) 为准，不要在 README 里另造一套规则。
- 分发打包：统一用 `python 蛙蛙呱呱agents团/scripts/make_package.py`，不要手工压 zip，也不要把 zip 提交进仓库。

---

> 一句话记住这套系统：**R01 负责把事拆对，专业角色负责把事做深，R04 负责把事验真，创始人负责不可逆的决定。**

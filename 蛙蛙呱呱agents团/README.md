# 蛙蛙呱呱（Guaguawawa）· 20 角色智能体公司

> 专为**一人公司**打造的全栈商业与技术智能体协作系统。
> 用「组织语义 + 契约化端口 + 生成与校验分离」把 20 个专业角色组织成一家可运行的公司，而不是 20 个互不相干的聊天机器人。

**版本：v2.0 · 2026-11-10**

**统一入口：** [`guagua.py`](蛙蛙呱呱agents团/guagua.py) ｜ **完整命令手册：** [`使用指南.md`](使用指南.md)

---

## 目录

- [一、这套系统是什么](#一这套系统是什么)
- [二、60 秒上手](#二60-秒上手)
- [三、组织全景](#三组织全景)
- [四、三种合作形式](#四三种合作形式)
- [五、20 个智能体详解](#五20-个智能体详解)
- [六、六条可复用协作流水线](#六六条可复用协作流水线)
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

### 本次升级了什么

- 重写了本 README，**逐个介绍 20 个角色**：定位、能力、输入/输出、常用命令、协作位置、边界。
- 新增 [`使用指南.md`](使用指南.md)：从 60 秒上手到 20 角色命令速查、协作流水线、产物路径与排错。
- 新增统一入口 [`guagua.py`](蛙蛙呱呱agents团/guagua.py)：一个命令调用全部角色和全部技能动作。
- 明确标注「真实执行 / 模拟 / 阻塞」边界，避免把本地校验说成线上已执行。

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

- **澄清**：只问真正缺的六件事——交付物、目标/成功标准、边界、输入、验收判据、时限/依赖。
- **自查**：我的哪个技能域能覆盖？契约输入齐不齐？有没有越界？
- **展开**：走技能子命令，产物写入 `workspace/artifacts/{task_id}/`。
- **自评**：过 harness 门禁；脏数据、缺证据、超边界都不许硬交。
- **汇报**：输出 `.md` 快读版 + `.html` 正式版，不吐裸 JSON。

```bash
# 例：只找 R06 做数据分析
python guagua.py call r06 quality audit --input workspace/_loop_clean.csv

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
python guagua.py call r06 quality audit --input workspace/_loop_clean.csv
python guagua.py call r06 explore funnel --input workspace/_loop_clean.csv --stage status
python guagua.py call r06 abtest --input workspace/parking_ab.csv --group group \
  --control A --treatment B --metric revenue
python guagua.py call r06 deep --series workspace/parking_profit_12m.csv \
  --cross workspace/parking_profit.csv --before 2025-09 --after 2025-10 \
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

**核心能力**：产品切片 MVP · Spec 转仓库 · 落地页 H5 · SaaS 邮件脚手架 · 跨平台原型 · 组件设计实现 · 质量验证交接 · **单文件 HTML deck**

**契约**：`prd` + `ui_brief` → `mvp` + `page_assets`

```bash
python guagua.py call r08 demo
python guagua.py call r08 slice slice --input examples/slice.json
python guagua.py call r08 scaffold scaffold --input examples/scaffold.json
python guagua.py call r08 landing landing --input examples/landing.json
python guagua.py call r08 prototype prototype --input examples/prototype.json
python guagua.py call r08 qa handoff --input examples/handoff.json
# 单文件 HTML 幻灯片：结构门禁 + 渲染
python guagua.py call r08 deck plan --input deck.json
python guagua.py call r08 deck html --input deck.json --out deck.html
# 直接吃 R10 落盘的品牌 DESIGN.md，转成设计令牌并过本角色门禁
python guagua.py call r08 design from-md --input DESIGNS/linear/DESIGN.md --out DESIGNS/linear/design_tokens.json
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

**核心能力**：AI 生图插画 · Logo 图标 VI · 产品 UI/UX · 交互原型动效 · 修图图像工程 · 视频音频处理 · 转写字幕 · 数据视觉营销物料 · **品牌设计系统库（31 套 DESIGN.md）** · **真实生图（Nano Banana Pro）** · **H3 视频提示词** · **品牌一致性检查**

**契约**：`brand_brief` + `content` → `visual_assets` + `vi`

```bash
python guagua.py call r10 demo
python guagua.py call r10 imagegen prompt --input examples/prompt.json
python guagua.py call r10 logo logo --input examples/logo.json
python guagua.py call r10 uiux screen --input examples/screen.json
python guagua.py call r10 brand vi --input examples/vi.json
python guagua.py call r10 render poster --input examples/poster.json
# 设计系统库：查库 → 推荐 → 落盘 → 门禁
python guagua.py call r10 designsys list --category devtools
python guagua.py call r10 designsys recommend --project ai
python guagua.py call r10 designsys show --brand linear.app
python guagua.py call r10 designsys apply --brand linear.app --out DESIGNS/linear
python guagua.py call r10 designsys audit --brand claude
# 品牌一致性检查：颜色/字体/对比度对 DESIGN.md 令牌
python guagua.py call r10 brandcheck check --input artifact.json
# 真实生图（需 AI_HIVE_API_KEY / ~/.ai-hive/config.json；generate 会扣费）
python guagua.py call r10 aihive probe
python guagua.py call r10 aihive preview --prompt "高级商业摄影风格的产品主视觉" --batch 2
python guagua.py call r10 aihive generate --prompt "..." --yes
# H3 视频提示词（T2VA/I2VA/FL2VA/L2VA/Ref2VA）
python guagua.py call r10 h3prompt build --input h3_spec.json --out prompt.txt
```

**设计系统库与生成能力归属**（31 套品牌规范 + 真实生图 + H3 视频提示词）：

| 角色 | 用法 |
|---|---|
| **R10 蛙成美** | 主用：`designsys` 检索/推荐/落盘/门禁；`aihive` 真实出图；`h3prompt` 装配视频提示词 |
| **R08 蛙建成** | 消费：`design from-md` 把 `DESIGN.md` 转成组件与令牌契约；落地页素材用 `aihive` 产物而非占位图 |
| **R09 蛙稳码** | 消费：拿 `design_tokens.json` 落生产前端，颜色/字阶/间距不再自造 |
| **R11 蛙点题** | 消费：视频/口播脚本交 `h3prompt` 装配成可投喂提示词；内容页配色对齐 `designsys` 基线 |
| **R12 蛙引流** | 消费：投放素材（KV/信息流/短视频）走 R10 的 `aihive` + `h3prompt`，不自己编画面 |
| R07 蛙得明 | 参考：PRD 的 UI Brief 直接引用某个设计系统 slug，避免"看着办" |

**协作位置**：R11 文案 → R10 配图/视觉；R08/R09 实现时使用 R10 的设计令牌与组件规格；品牌决策升级创始人。

**边界**：不写代码逻辑；图像生成、转码、转写、外部发布未接入时属于 simulated 或 blocked；不冒充已生成真实资产。

---

### 市场与客户

#### R11 · 蛙点题｜内容主笔

**定位**：把主题变成有策略、有钩子、有平台适配的内容，并对文本格式和长度做本地校验。

**核心能力**：内容策略选题 · SEO/AEO · 钩子提纲 · 文案长文 · 品牌语调编辑 · 广告公关 · 多平台适配 · 持续本地化 · **小红书发布包（评分/合规）**

**契约**：`topic` + `audience` → `content_draft` + `publish_list`

```bash
python guagua.py call r11 demo
python guagua.py call r11 topic plan --input examples/plan.json
python guagua.py call r11 copy article --input examples/article.json
python guagua.py call r11 seo audit --input examples/keyword.json
python guagua.py call r11 platform adapt --input examples/adapt.json
python guagua.py call r11 localize term --input examples/term.json
# 小红书：四要素校验 → 8 项快检 → 发布前合规扫描
python guagua.py call r11 xhs note --input note.json
python guagua.py call r11 xhs score --input note.json
python guagua.py call r11 xhs compliance --input note.json
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

**核心能力**：商品电商后端 · 订阅计量计费 · 支付集成 · 电子签审计 · 服务预约 · 交易状态编排 · 收入数据接口 · 交易自动化接口 · **选品评分与利润红线**

**契约**：`package` + `quotation` → `order` + `payment_status`

```bash
python guagua.py call r14 demo
python guagua.py call r14 catalog product --input examples/product.json
python guagua.py call r14 order cart --input examples/cart.json
python guagua.py call r14 billing invoice --input examples/invoice.json
python guagua.py call r14 payment payment_intent --input examples/payment_intent.json
python guagua.py call r14 signature signing --input examples/signing.json
python guagua.py call r14 workflow transition --input examples/transition.json
# 选品：五维加权（上游 120% 权重已归一化）+ 利润红线 + 假设卡门禁
python guagua.py call r14 selection score --input selection.json
python guagua.py call r14 selection profit --input profit.json
```

**协作位置**：R14 订单 → R15 履约；收入数据交 R03/R06；退款争议交 R03；高风险交易动作需人工授权。

**边界**：不出财务意见（R03）；不代替创始人签约/退款；支付、签名、预约的真实外部集成未接入时只做本地契约校验。

---

#### R15 · 蛙供应｜ERP 与供应链运营官

**定位**：管采购、供应商、库存、仓库、销售履约、生产资源、财务业务接口和主数据权限。

**核心能力**：采购供应商 · 库存仓库 · 销售履约记录 · 生产服务资源 · ERP 财务接口 · 主数据权限 · 运营报表 · **采购 TCO / landed cost**

**契约**：`order` + `sop` → `purchase_order` + `inventory_ledger`

```bash
python guagua.py call r15 demo
python guagua.py call r15 procurement purchase_order --input examples/purchase_order.json
python guagua.py call r15 inventory bin --input examples/bin.json
python guagua.py call r15 fulfillment sales_order --input examples/sales_order.json
python guagua.py call r15 production bom --input examples/bom.json
python guagua.py call r15 masterdata permission --input examples/permission.json
# 采购总拥有成本：landed cost 对比 + 生命周期 TCO
python guagua.py call r15 tco compare --input quotes.json
python guagua.py call r15 tco lifecycle --input lifecycle.json
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

## 六、六条可复用协作流水线

| # | 流水线 | 链路 | 适用场景 | 入口 |
|---|---|---|---|---|
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
python guagua.py call r06 explore funnel --input workspace/_loop_clean.csv --stage status

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
| `doctor` | 环境诊断 + 体检（含记忆池体积） | `python guagua.py doctor` |
| `gc` | 记忆池护栏：裁剪过期快照 / 隔离超限文件 | `python guagua.py gc --dry-run` |
| `capabilities` | 能力目录：谁负责 / 谁能用 / 形态 | `python guagua.py capabilities --role r11` |

### 7.3 如何调用「全部功能」

```bash
# 1) 先看角色支持哪些子命令
python guagua.py call r06 --help

# 2) 再逐层下钻
python guagua.py call r06 explore --help
python guagua.py call r06 explore funnel --help

# 3) 直接执行
python guagua.py call r06 explore funnel \
  --input workspace/_loop_clean.csv --stage status
```

`call` 的规则只有一条：**第一个参数是角色，后面的参数全部交给该角色的 `agent.py`**。因此角色支持的任何技能、动作、参数、`--help`、`demo`、`run --task` 都可以通过这一个入口调用。

### 7.4 推荐阅读顺序

1. 本 README（组织与角色全貌）
2. [`使用指南.md`](使用指南.md)（逐角色命令、流水线、排错）
3. [`ORG.md`](蛙蛙呱呱agents团/ORG.md)（组织章程与红线）
4. [`PROTOCOL.md`](蛙蛙呱呱agents团/PROTOCOL.md)（任务卡与移交协议）
5. [`REPORT-STANDARD.md`](蛙蛙呱呱agents团/REPORT-STANDARD.md)（汇报格式）

### 7.5 能力库（自有 22 项）

团队把值得内化的方法论写成了**自有能力**：能确定性执行的落成代码技能，不能的落成能力卡（规范）。
能力卡在各角色 `references/capabilities/<id>/README.md`，登记表在
[`shared/capabilities/catalog.json`](蛙蛙呱呱agents团/shared/capabilities/catalog.json)。

```bash
python guagua.py capabilities                    # 全部能力 + 形态（代码/规范）
python guagua.py capabilities --role r11         # 某角色负责或可消费
python guagua.py capabilities --q 小红书
python guagua.py capabilities --id xhs-content-skills
```

| 负责 | 能力（id） |
|---|---|
| R01 | `strategic-growth-compass` |
| R02 | `business-ops-analysis` |
| R05 | `tashan-research-skills`、`industry-panorama-research`、`market-intelligence-radar` |
| R06 | `build-web-data-visualization`、`data-processing` |
| R07 | `user-research-toolkit` |
| R08 | `rapid-prototype-craft`、`ppt-generator` |
| R09 | `web-app-development`、`frontend-design` |
| R10 | `design-system`、`whiteboard`、`brand-guardian`、`ecommerce-designer` |
| R11 | `rednote-post`、`xhs-content-skills` |
| R12 | `marketing-toolkit` |
| R14 | `omnichannel-commerce-assistant`、`smart-product-selector` |
| R15 | `analyze-procurement` |

形态说明：`代码` = 有确定性命令与门禁（`xhs`、`selection`、`tco` 等）；`规范` = 按能力卡规则执行，
产物仍走角色 harness 验收。不存在"外部接口"依赖，也不需要任何第三方客户端。


---

## 八、目录结构与文档索引

```text
蛙蛙呱呱/
├─ README.md                     # 本文件：总览 + 20 角色详解 + 协作方式
├─ 使用指南.md                   # 统一入口、全部命令、流水线、排错
├─ 蛙蛙呱呱agents团/
│  ├─ guagua.py                  # 统一入口（本次新增）
│  ├─ chat.py                    # 知识注入 / Prompt 构建
│  ├─ ORG.md                     # 组织章程（谁负责什么）
│  ├─ PROTOCOL.md                # 协同协议（任务怎么流动）
│  ├─ TEAM.md                    # 编排实例
│  ├─ REPORT-STANDARD.md         # 汇报标准
│  ├─ core/                      # registry / protocol / runner / workspace
│  ├─ r01-waquanju-ceo/          # R01 蛙全局
│  ├─ r02-wapaibu-coo/           # R02 蛙排布
│  ├─ ...                        # R03 ~ R19
│  ├─ r20-washouzhi-sre/         # R20 蛙值守
│  ├─ shared/                    # 报告引擎、共享能力
│  ├─ docs/                      # SOP、能力地图、字段语义
│  ├─ scripts/                   # 批量生成、基准、演练脚本
│  └─ workspace/                 # 任务卡、事件流、产物
└─ 蛙蛙呱呱.zip                  # 历史打包快照
```

### 关键文档

| 文档 | 作用 |
|---|---|
| [`ORG.md`](蛙蛙呱呱agents团/ORG.md) | 组织架构、汇报线、权力与红线、角色边界 |
| [`PROTOCOL.md`](蛙蛙呱呱agents团/PROTOCOL.md) | 单角色五步、失败移交、多角色 GSD 编排、验收协议、会话记忆与快照契约 |
| [`TEAM.md`](蛙蛙呱呱agents团/TEAM.md) | 「营收最大化」编排实例 |
| [`REPORT-STANDARD.md`](蛙蛙呱呱agents团/REPORT-STANDARD.md) | 交付报告的统一结构与文风 |
| [`REPORT-BRIDGE-GUIDE.md`](蛙蛙呱呱agents团/REPORT-BRIDGE-GUIDE.md) | 报告桥接指南 |
| [`SOP_AGENT_EVOLUTION_UNIVERSAL.md`](SOP_AGENT_EVOLUTION_UNIVERSAL.md) | 智能体演进方法论 |
| [`docs/SOP_BUSINESS_ANALYSIS_AND_REPORTING.md`](蛙蛙呱呱agents团/docs/SOP_BUSINESS_ANALYSIS_AND_REPORTING.md) | 商业分析与决策级报告标准 |
| [`docs/actions_catalog.json`](蛙蛙呱呱agents团/docs/actions_catalog.json) | 全角色动作目录（机器可读） |
| [`core/registry.py`](蛙蛙呱呱agents团/core/registry.py) | 20 角色能力与端口注册表 |
| [`core/protocol.py`](蛙蛙呱呱agents团/core/protocol.py) | 任务卡、事件、端口字段契约 |

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
python guagua.py doctor
python guagua.py check
```

### 单角色测试

```bash
cd r06-wadeqing-analyst
python run_tests.py
python verify_loop.py
```

不同角色的测试入口略有差异：大多数有 `run_tests.py`，部分有 `verify_loop.py`、`tests/`。以各角色目录内文件为准，不要假设 20 个角色测试命令完全一致。

### 产物位置

- 任务卡与事件：`workspace/tasks/`、`workspace/events.jsonl`、`workspace/runlog.jsonl`
- 单次任务产物：`workspace/artifacts/{task_id}/`
- 角色自己的工作区：`rXX-*/workspace/`
- 报告：通常为 `.md` 快读版 + `.html` 正式版

### 会话记忆与快照（L09 层）

- **位置**：`rXX-*/workspace/session_state.json`，一角色一份，属运行时状态，不是源码资产。
- **作用**：记住「上次聊到哪」——当前业务实体、已确认槽位、轮次轨迹，供「按刚才第二套方案」这类代词消歧使用。
- **快照只存业务态**：`state_dump` 只含业务实体 + `slots` + 场景/焦点等标量字段，**不含 `history` 与 `snapshots`**
  （历史只记 `history_len`，回滚按长度截断）；因此体积随快照数线性增长（实测 80 次快照 < 100 KB，25 次 ≈ 18 KB）。
- **回滚**：只恢复目标快照的业务态，同时保留完整快照列表，回滚后仍可继续回滚到更早版本。
- **容错**：文件缺失或损坏时角色从默认状态启动，不阻塞运行；删除快照 / 清空记忆属不可逆动作，需人工授权。
- **体积护栏**（`core/memory_guard.py`）：加载前 >100 MB 直接隔离为 `*.oversize-<时间>.bak`、**不解析**；
  文件超 2 MB 时自动裁到最近 50 条快照；`python guagua.py gc` 可对全部角色统一巡检与清理，`doctor` 会报最大记忆池体积。
- **打包**：归档包可保留该文件，精简包 / 对外交付包应排除（重新运行会从默认起点重建）。
- 协议细节见 [`PROTOCOL.md` 第六节](蛙蛙呱呱agents团/PROTOCOL.md)。

### 能力边界（重要）

1. **本地确定性 ≠ 线上已执行**：很多角色能验证契约、生成工件、跑本地计算，但外部发布、支付、部署、真实 CRM/ERP 写入未接入时会标为 `simulated` 或 `blocked`。
2. **R03 的入口差异**：R03 蛙守线没有 `run --task` 子命令，使用 `guagua.py call r03 ...` 直接调用专家技能；其余 19 个角色均支持任务卡入口。
3. **不可逆动作必须人工授权**：裁员、关停、签约、付款、删除快照、灾难切换、生产恢复等，任何角色都不能自动执行。
4. **质量结论只归 R04**：其他角色可以自检，但不能给自己签 `pass`。
5. **数据与隐私**：不要把真实密钥、身份证、银行卡、生产凭据写入工件；R03/R16/R20 都有相应红线检查。

---

## 十、版本与更新记录

### v2.0.6（2026-11-11）

- **把能力真正做成可执行技能**（不再只是目录登记）：
  - R11 `xhs`：`note`/`score`/`compliance`——标题 ≤20 字、正文 550–650、标签埋词闭环、8 项快检 ≥7、CES 基准、
    CTA 黑名单与四类诱导互动、绝对化/收入/联系方式拦截、AI 标注。
  - R14 `selection`：`score`/`profit`——五维加权（上游 120% 权重**归一化**并提示）、推荐四档、
    SP-09 假设卡门禁、毛利率 30%/15% 红线、数据来源类型校验。
  - R15 `tco`：`compare`/`lifecycle`——landed cost 九项加总、可用数量与资金占用折算、MOQ/交期/不良率旗标、
    TCO 至少 3 类成本。
- 三个技能均接入各角色 harness 门禁与契约（r14 19 动作、r15 20 动作、r11 9 技能），
  新增 `tests/test_capability_fusions.py`（8 例，跑真实 CLI）。
- 文档：各角色 `references/capabilities/` 增能力卡，记录上游权重 120% 的口径问题。

### v2.1.0（2026-11-11）

- **能力全部内化**：`shared/capabilities/catalog.json` 收录 22 项自有能力，能力卡在
  各角色 `references/capabilities/<id>/README.md`；不再依赖任何外部客户端、路径或插件。
- **新增两个可执行技能**：
  - R08 `deck`：`plan`/`html` —— 6–30 页、一页一个观点、标题 ≤20 字不重复、封面/行动页齐全；
    渲染单文件 HTML（内联样式、无外部资源、含打印分页）。
  - R10 `brandcheck`：`check` —— 颜色/字体对 `DESIGN.md` 令牌、正文对比度 ≥4.5、单页主色 ≤8。
- 目录命令改为 `python guagua.py capabilities`：显示形态（代码/规范）、能力卡与规则要点。
- 新增 `tests/test_capabilities.py`（目录完整性、能力卡、无外部痕迹、可执行技能真实存在）。

### v2.0.5（2026-11-11）

- 第一版能力目录（26 项登记 + 文档入库），后续已被 v2.1.0 的自有化方案取代。

### v2.0.4（2026-11-11）

- 新增 **S12 `aihive`（真实生图）**：Nano Banana Pro 裸接口外壳——`probe`/`preview`/`generate`/`task`，
  默认 COST_FIRST、`generate` 必须 `--yes`、batch ≤4、缺 Key 即 `blocked`、超时只留 `taskId` 不重复扣费；
  上游脚本 vendor 到 `r10-wachengmei-design/vendor/aihive/imagegen.py`。
- 新增 **S13 `h3prompt`（MiniMax H3 视频提示词）**：T2VA/I2VA/FL2VA/L2VA/Ref2VA 结构装配 +
  时长 4–15s、时间戳递增、参考标签、对白语言标签、屏幕文字引号等硬门禁。
- 文档：r10 SKILL.md 增 S12/S13 与生成纪律；新增[模块J](蛙蛙呱呱agents团/r10-wachengmei-design/references/10-ai-generation.md)；
  README 归属表补 R11/R12 消费关系；新增 `tests/test_ai_generation.py`（14 例）。

### v2.0.3（2026-11-11）

- 新增 **设计系统库**：31 套品牌 DESIGN.md 落入 [`r10-wachengmei-design/references/design-systems/`](蛙蛙呱呱agents团/r10-wachengmei-design/references/design-systems/)，
  解析/门禁/令牌转换在 [`shared/design_systems.py`](蛙蛙呱呱agents团/shared/design_systems.py)（纯标准库）。
- R10 新增 `designsys` 技能（`list/recommend/show/apply/audit`）：按分类或项目类型选基线，
  落盘 `DESIGN.md` + `design_tokens.json`，九段式门禁 31/31 PASS；契约与 `run_tests` 同步到 10 技能。
- R08 新增 `design from-md`：直接吃 R10 落盘的品牌 DESIGN.md → 令牌契约 → 过组件/令牌门禁。
- 新增 `tests/test_design_systems.py`（7 例，含 R10→R08 跨角色接力）；README 增补「设计系统库归属」表。

### v2.0.2（2026-11-10）

- 新增 **记忆池体积护栏** [`core/memory_guard.py`](蛙蛙呱呱agents团/core/memory_guard.py)：加载前 100 MB 硬熔断（隔离为 `.bak`、不解析）、
  2 MB 软上限自动裁到最近 50 条快照、`python guagua.py gc` 全局巡检；`doctor` 增报最大记忆池并在越限时 WARN/FAIL。
- 修掉 **R14 快照的二次膨胀源**：`state_dump` 不再复制 `history`，改记 `history_len`，回滚按长度截断；
  与之前的「不复制 `snapshots`」合并后，体积严格线性（80 次快照 < 100 KB）。
- 修掉 **R05 快照 O(n²)**：`ResearchSessionStore` 同样改成只存业务字段 + `history_len`，
  回滚按长度截断时间线。实测 300 轮从按平方推算的 ~42 MB 降到 285 KB（快照恒定 50 条）。
- 回归测试：`tests/test_memory_guard.py`（13 例，含 doctor 哨兵阈值）、
  `r14-*/tests/test_memory_guard.py`（5 例）、`r05-*/tests/test_memory_guard.py`（5 例）。

### v2.0.1（2026-11-10）

- 修复 **R14 快照体积指数膨胀**：`create_snapshot` 不再把整个 `state`（含 `snapshots`）拷进
  `state_dump`，改为只存业务态。历史事故：19 次快照 → 966 MB / 52 万次嵌套；修复后 25 次快照 ≈ 18 KB。
- 清理 R14 的 966 MB `workspace/session_state.json`，记忆池重置为干净起点。
- 文档对齐：`PROTOCOL.md` 新增第六节「会话记忆与快照」，README 第九节新增「会话记忆与快照（L09 层）」。

### v2.0（2026-11-10）

- 重写 README：新增 20 个角色的完整介绍、三种合作形式、六条协作流水线、统一入口说明。
- 新增 [`guagua.py`](蛙蛙呱呱agents团/guagua.py)：`roles / info / call / chat / plan / dispatch / status / demo / check / doctor`。
- 新增 [`使用指南.md`](使用指南.md)：面向读者的完整操作手册。
- 明确 R03 的入口差异、各角色的真实/模拟/阻塞边界。
- 保留原有 `chat.py` 和每个角色的 `agent.py` 直接入口，不破坏旧用法。

### 维护约定

- 新增角色：先更新 [`core/registry.py`](蛙蛙呱呱agents团/core/registry.py)，再建角色目录、`agent.py`、`SKILL.md`、测试，最后同步本 README 与使用指南。
- 新增技能：更新角色 `SKILL.md` 与 `contracts.py`，并补一条可复现的测试或夹具。
- 修改协作规则：以 [`ORG.md`](蛙蛙呱呱agents团/ORG.md) 和 [`PROTOCOL.md`](蛙蛙呱呱agents团/PROTOCOL.md) 为准，不要在 README 里另造一套规则。

---

> 一句话记住这套系统：**R01 负责把事拆对，专业角色负责把事做深，R04 负责把事验真，创始人负责不可逆的决定。**
